from typing import Optional

from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Qt, QPoint, Signal

from frontend.graph_items import (
    BaseGraphNodeItem,
    GraphEdgeItem,
    create_graph_node_item,
)
from frontend.styles import GRAPH_VIEW_STYLE


class GraphScene(QGraphicsScene):
    node_double_clicked = Signal(str)
    right_clicked = Signal()

    def mouseDoubleClickEvent(self, event):
        view = self.views()[0] if self.views() else None
        transform = view.transform() if view else None

        item = self.itemAt(event.scenePos(), transform)
        node_item = self._get_node_item(item)

        if event.button() == Qt.MouseButton.LeftButton and node_item is not None:
            self.node_double_clicked.emit(node_item.node_uuid)
            event.accept()
            return

        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.clearSelection()
            self.right_clicked.emit()
            event.accept()
            return

        super().mousePressEvent(event)

    def _get_node_item(self, item):
        while item is not None:
            if isinstance(item, BaseGraphNodeItem):
                return item

            item = item.parentItem()

        return None


class GraphView(QGraphicsView):
    node_selected = Signal(str)
    node_deselected = Signal()
    node_double_clicked = Signal(str)

    def __init__(self):
        super().__init__()

        self.scene_obj = GraphScene(self)
        self.setScene(self.scene_obj)

        self.scene_obj.setSceneRect(-5000, -5000, 10000, 10000)

        self.nodes_by_uuid = {}

        self.min_zoom = 0.2
        self.max_zoom = 4.0

        self._panning = False
        self._last_mouse_pos = QPoint()

        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.scene_obj.selectionChanged.connect(self._on_selection_changed)
        self.scene_obj.right_clicked.connect(self.node_deselected.emit)
        self.scene_obj.node_double_clicked.connect(self.node_double_clicked.emit)

        self.setStyleSheet(GRAPH_VIEW_STYLE)

    def render_graph(self, graph_data: dict):
        self.scene_obj.blockSignals(True)
        self.scene_obj.clear()
        self.nodes_by_uuid.clear()

        nodes = graph_data["nodes"]
        edges = graph_data["edges"]

        positions = self._calculate_standard_layout(nodes, edges)

        for node in nodes:
            item = create_graph_node_item(
                node_uuid=node["uuid"],
                name=node["name"],
                node_type=node["type"],
                size=node.get("size", 100),
            )

            x, y = positions[node["uuid"]]
            item.setPos(x, y)

            self.scene_obj.addItem(item)
            self.nodes_by_uuid[node["uuid"]] = item

        for edge in edges:
            source = self.nodes_by_uuid.get(edge["source"])
            target = self.nodes_by_uuid.get(edge["target"])

            if source is None or target is None:
                continue

            edge_item = GraphEdgeItem(source, target)
            self.scene_obj.addItem(edge_item)

            source.add_edge(edge_item)
            target.add_edge(edge_item)

        self.scene_obj.blockSignals(False)

    def select_node_visual(self, node_uuid: Optional[str]):
        self.scene_obj.blockSignals(True)
        self.scene_obj.clearSelection()

        if node_uuid is not None and node_uuid in self.nodes_by_uuid:
            self.nodes_by_uuid[node_uuid].setSelected(True)

        self.scene_obj.blockSignals(False)

    def _on_selection_changed(self):
        selected_items = self.scene_obj.selectedItems()

        if not selected_items:
            self.node_deselected.emit()
            return

        item = selected_items[0]

        if isinstance(item, BaseGraphNodeItem):
            self.node_selected.emit(item.node_uuid)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._last_mouse_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position().toPoint() - self._last_mouse_pos
            self._last_mouse_pos = event.position().toPoint()

            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )

            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton and self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        current_scale = self.transform().m11()

        if event.angleDelta().y() > 0:
            if current_scale < self.max_zoom:
                factor = min(zoom_in_factor, self.max_zoom / current_scale)
                self.scale(factor, factor)
        else:
            if current_scale > self.min_zoom:
                factor = max(zoom_out_factor, self.min_zoom / current_scale)
                self.scale(factor, factor)

        event.accept()

    def _calculate_standard_layout(self, nodes: list[dict], edges: list[dict]):
        if not nodes:
            return {}

        children_by_parent = {}
        targets = set()

        for edge in edges:
            children_by_parent.setdefault(edge["source"], []).append(edge["target"])
            targets.add(edge["target"])

        root_candidates = [
            node["uuid"]
            for node in nodes
            if node["uuid"] not in targets
        ]

        root_uuid = root_candidates[0] if root_candidates else nodes[0]["uuid"]

        levels = {}
        queue = [(root_uuid, 0)]

        while queue:
            node_uuid, depth = queue.pop(0)

            if node_uuid in levels:
                continue

            levels[node_uuid] = depth

            for child_uuid in children_by_parent.get(node_uuid, []):
                queue.append((child_uuid, depth + 1))

        by_level = {}

        for node in nodes:
            depth = levels.get(node["uuid"], 0)
            by_level.setdefault(depth, []).append(node["uuid"])

        positions = {}

        x_spacing = 280
        y_spacing = 180

        for depth, node_ids in by_level.items():
            total = len(node_ids)

            for index, node_uuid in enumerate(node_ids):
                x = depth * x_spacing
                y = (index - (total - 1) / 2) * y_spacing
                positions[node_uuid] = (x, y)

        return positions