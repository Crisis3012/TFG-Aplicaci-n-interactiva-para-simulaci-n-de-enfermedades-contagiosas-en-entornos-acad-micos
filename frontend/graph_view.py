from typing import Optional

from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Qt, QPoint, Signal
import math

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
        self.node_positions = {}

        self.min_zoom = 0.2
        self.max_zoom = 4.0

        self._panning = False
        self._last_mouse_pos = QPoint()

        # NUEVO: controla si en el siguiente render
        # se deben ignorar las posiciones actuales.
        self._force_relayout = False

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

        # Solo preservamos posiciones si NO estamos forzando re-layout.
        if not self._force_relayout:
            for node_uuid, item in self.nodes_by_uuid.items():
                self.node_positions[node_uuid] = (item.scenePos().x(), item.scenePos().y())

        self.scene_obj.clear()
        self.nodes_by_uuid.clear()

        nodes = graph_data["nodes"]
        edges = graph_data["edges"]

        default_positions = self._calculate_standard_layout(nodes, edges)

        for node in nodes:
            item = create_graph_node_item(
                node_uuid=node["uuid"],
                name=node["name"],
                node_type=node["type"],
                size=node.get("size", 100),
            )

            x, y = self.node_positions.get(
                node["uuid"],
                default_positions[node["uuid"]]
            )

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

        # Ya hemos recalculado el layout, así que quitamos la bandera.
        self._force_relayout = False

        self.scene_obj.blockSignals(False)

    def forget_node_positions(self, node_uuids: list[str]) -> None:
        for node_uuid in node_uuids:
            self.node_positions.pop(node_uuid, None)

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

    def reset_layout(self):
        self.node_positions.clear()
        self._force_relayout = True

    def _calculate_standard_layout(self, nodes: list[dict], edges: list[dict]):
        if not nodes:
            return {}

        children_by_parent = {}
        targets = set()
        type_by_uuid = {node["uuid"]: node.get("type", "") for node in nodes}

        for edge in edges:
            children_by_parent.setdefault(edge["source"], []).append(edge["target"])
            targets.add(edge["target"])

        root_candidates = [
            node["uuid"]
            for node in nodes
            if node["uuid"] not in targets
        ]

        root_uuid = root_candidates[0] if root_candidates else nodes[0]["uuid"]

        subtree_size_cache = {}

        def subtree_size(node_uuid: str) -> int:
            if node_uuid in subtree_size_cache:
                return subtree_size_cache[node_uuid]

            children = children_by_parent.get(node_uuid, [])
            if not children:
                subtree_size_cache[node_uuid] = 1
                return 1

            total = sum(subtree_size(child_uuid) for child_uuid in children)
            subtree_size_cache[node_uuid] = max(1, total)
            return subtree_size_cache[node_uuid]

        def is_container(node_uuid: str) -> bool:
            return type_by_uuid.get(node_uuid, "") in {
                "group", "spacegroup", "career", "course", "coursegroup"
            }

        def sort_children(child_ids: list[str]) -> list[str]:
            return sorted(
                child_ids,
                key=lambda uid: (
                    0 if is_container(uid) else 1,
                    -subtree_size(uid),
                    uid,
                )
            )

        def required_radius_for_children(child_count: int, usable_span: float) -> float:
            """
            Calcula un radio mínimo para que los hermanos no se monten entre sí.
            usable_span está en radianes.
            """
            if child_count <= 1:
                return 0.0

            min_arc_per_node = 190.0  # separación mínima deseada entre nodos
            min_angle = max(usable_span / child_count, 0.10)

            return min_arc_per_node / min_angle

        positions = {}
        positions[root_uuid] = (0, 0)

        base_radius = 320
        angle_padding = math.radians(10)
        min_child_span = math.radians(26)

        def place_subtree(
            node_uuid: str,
            depth: int,
            center_angle: float,
            angle_span: float,
            forced_radius: float | None = None,
        ):
            if depth == 0:
                positions[node_uuid] = (0, 0)
                current_radius = 0
            else:
                current_radius = forced_radius if forced_radius is not None else base_radius * depth
                x = math.cos(center_angle) * current_radius
                y = math.sin(center_angle) * current_radius
                positions[node_uuid] = (x, y)

            children = sort_children(children_by_parent.get(node_uuid, []))
            if not children:
                return

            if depth == 0:
                usable_span = (2 * math.pi) - angle_padding
            else:
                usable_span = max(angle_span - angle_padding, min_child_span * len(children))
                usable_span = min(usable_span, angle_span)

            total_weight = sum(subtree_size(child_uuid) for child_uuid in children)

            # Radio dinámico: si hay muchos hijos en poco arco, alejarlos más
            child_depth = depth + 1
            default_child_radius = base_radius * child_depth
            spacing_child_radius = required_radius_for_children(len(children), usable_span)
            child_radius = max(default_child_radius, spacing_child_radius)

            cursor = center_angle - (usable_span / 2)

            for child_uuid in children:
                child_weight = subtree_size(child_uuid)
                child_span = usable_span * (child_weight / total_weight)
                child_center = cursor + (child_span / 2)

                next_span = max(child_span * 0.82, min_child_span)

                place_subtree(
                    node_uuid=child_uuid,
                    depth=child_depth,
                    center_angle=child_center,
                    angle_span=next_span,
                    forced_radius=child_radius,
                )

                cursor += child_span

        place_subtree(
            node_uuid=root_uuid,
            depth=0,
            center_angle=-math.pi / 2,
            angle_span=(2 * math.pi) - angle_padding,
        )

        return positions