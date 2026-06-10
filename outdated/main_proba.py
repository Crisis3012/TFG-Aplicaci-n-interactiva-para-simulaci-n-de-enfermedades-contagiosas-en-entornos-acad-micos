import sys
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel,
    QStackedWidget, QSplitter, QFrame, QTreeWidget, QTreeWidgetItem,
    QLineEdit, QSlider, QSpinBox,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsLineItem, QGraphicsTextItem
)
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QFont, QBrush, QPen, QShortcut, QKeySequence

# Ajusta estos imports a tu estructura real
from backend.faculty import Faculty
from controller.builder_controller import BuilderController


# ============================================================
# GRAPH VIEW
# ============================================================

class GraphEdgeItem(QGraphicsLineItem):
    def __init__(self, source_node, target_node):
        super().__init__()
        self.source_node = source_node
        self.target_node = target_node

        self.setPen(QPen(Qt.GlobalColor.darkGray, 2))
        self.setZValue(-1)

        self.update_position()

    def update_position(self):
        p1 = self.source_node.scenePos()
        p2 = self.target_node.scenePos()
        self.setLine(p1.x(), p1.y(), p2.x(), p2.y())


class GraphNodeItem(QGraphicsRectItem):
    def __init__(self, node_uuid: str, name: str, node_type: str, size: float = 100):
        half = size / 2
        super().__init__(-half, -half, size, size)

        self.node_uuid = node_uuid
        self.name = name
        self.node_type = node_type
        self.connected_edges = []

        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsRectItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

        self.default_pen = QPen(Qt.GlobalColor.darkBlue, 3)
        self.selected_pen = QPen(Qt.GlobalColor.red, 4)

        if node_type == "root":
            self.setBrush(QBrush(Qt.GlobalColor.darkCyan))
        elif node_type == "group":
            self.setBrush(QBrush(Qt.GlobalColor.cyan))
        else:
            self.setBrush(QBrush(Qt.GlobalColor.lightGray))

        self.setPen(self.default_pen)

        self.label = QGraphicsTextItem(name, self)
        self.label.setDefaultTextColor(Qt.GlobalColor.black)
        self.label.setFont(QFont("Arial", 10))

        text_rect = self.label.boundingRect()
        self.label.setPos(-text_rect.width() / 2, -text_rect.height() / 2)

    def add_edge(self, edge):
        self.connected_edges.append(edge)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.connected_edges:
                edge.update_position()

        if change == QGraphicsRectItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.setPen(self.selected_pen if self.isSelected() else self.default_pen)

        return super().itemChange(change, value)


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
            if hasattr(item, "node_uuid"):
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

        self.setStyleSheet("""
            QGraphicsView {
                background-color: #eaecee;
                border: none;
            }
        """)

    def render_graph(self, graph_data: dict):
        self.scene_obj.blockSignals(True)
        self.scene_obj.clear()
        self.nodes_by_uuid.clear()

        nodes = graph_data["nodes"]
        edges = graph_data["edges"]

        positions = self._calculate_standard_layout(nodes, edges)

        for node in nodes:
            item = GraphNodeItem(
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

        if hasattr(item, "node_uuid"):
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
            node["uuid"] for node in nodes
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


# ============================================================
# FRONTEND PAGES
# ============================================================

class MenuPage(QWidget):
    def __init__(self, stacked_widget, controller: BuilderController):
        super().__init__()

        self.stacked_widget = stacked_widget
        self.controller = controller

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(18)

        title = QLabel("TFG")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 30, QFont.Weight.Bold))

        btn_builder = QPushButton("Builder")
        btn_simular = QPushButton("Simular")
        btn_visualizar = QPushButton("Visualizar")
        btn_salir = QPushButton("Salir")

        for btn in [btn_builder, btn_simular, btn_visualizar, btn_salir]:
            btn.setFixedSize(220, 45)

        btn_builder.clicked.connect(self.open_builder)
        btn_salir.clicked.connect(self.window().close)

        layout.addWidget(title)
        layout.addSpacing(25)
        layout.addWidget(btn_builder, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn_simular, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn_visualizar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn_salir, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def open_builder(self):
        self.stacked_widget.setCurrentIndex(1)
        self.controller.load_builder()


class BuilderPage(QWidget):
    def __init__(self, stacked_widget, controller: BuilderController):
        super().__init__()

        self.stacked_widget = stacked_widget
        self.controller = controller
        self.controller.attach_ui(self)

        self.current_node = None

        escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        escape_shortcut.activated.connect(lambda: self.stacked_widget.setCurrentIndex(0))

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Panel izquierdo
        left_panel = QFrame()
        left_panel.setMinimumWidth(180)
        left_panel.setStyleSheet("QFrame { background-color: #3b4048; border: none; }")

        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(8)

        left_title = QLabel("Facultad")
        left_title.setFont(QFont("Arial", 13, QFont.Weight.Bold))

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)

        btn_add_group = QPushButton("Crear grupo")
        btn_add_space = QPushButton("Crear espacio")
        btn_delete = QPushButton("Eliminar")
        btn_toggle = QPushButton("Expandir/contraer")

        btn_add_group.clicked.connect(self._create_group)
        btn_add_space.clicked.connect(self._create_space)
        btn_delete.clicked.connect(self.controller.delete_selected_node)
        btn_toggle.clicked.connect(self._toggle_selected_group)

        left_layout.addWidget(left_title)
        left_layout.addWidget(self.tree)
        left_layout.addWidget(btn_add_group)
        left_layout.addWidget(btn_add_space)
        left_layout.addWidget(btn_toggle)
        left_layout.addWidget(btn_delete)

        # Centro
        self.graph_view = GraphView()
        self.graph_view.setMinimumWidth(250)

        self.graph_view.node_selected.connect(self.controller.select_node)
        self.graph_view.node_deselected.connect(self.controller.clear_selection)
        self.graph_view.node_double_clicked.connect(self.controller.toggle_group)

        # Panel derecho
        right_panel = QFrame()
        right_panel.setMinimumWidth(220)
        right_panel.setStyleSheet("QFrame { background-color: #3b4048; border: none; }")

        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(10, 10, 10, 10)
        right_layout.setSpacing(8)

        self.selected_title = QLabel("Sin selección")
        self.selected_title.setFont(QFont("Arial", 13, QFont.Weight.Bold))

        self.type_label = QLabel("Tipo: -")
        self.uuid_label = QLabel("UUID: -")
        self.uuid_label.setWordWrap(True)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nombre")
        self.name_input.editingFinished.connect(self._on_name_edited)

        self.size_label = QLabel("Tamaño del nodo")
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(50, 220)
        self.size_slider.valueChanged.connect(self._on_size_changed)

        self.capacity_label = QLabel("Capacidad")
        self.capacity_input = QSpinBox()
        self.capacity_input.setRange(0, 10000)
        self.capacity_input.valueChanged.connect(self._on_capacity_changed)

        right_layout.addWidget(self.selected_title)
        right_layout.addWidget(self.type_label)
        right_layout.addWidget(self.uuid_label)
        right_layout.addSpacing(12)
        right_layout.addWidget(QLabel("Nombre"))
        right_layout.addWidget(self.name_input)
        right_layout.addSpacing(12)
        right_layout.addWidget(self.size_label)
        right_layout.addWidget(self.size_slider)
        right_layout.addSpacing(12)
        right_layout.addWidget(self.capacity_label)
        right_layout.addWidget(self.capacity_input)
        right_layout.addStretch()

        splitter.addWidget(left_panel)
        splitter.addWidget(self.graph_view)
        splitter.addWidget(right_panel)

        splitter.setSizes([240, 620, 280])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    # Métodos que llama el controller

    def render_graph(self, graph_data):
        self.graph_view.render_graph(graph_data)

    def select_node_visual(self, node_uuid):
        self.graph_view.select_node_visual(node_uuid)
        self._select_tree_item(node_uuid)

    def render_tree(self, root):
        self.tree.clear()
        root_item = self._create_tree_item(root)
        self.tree.addTopLevelItem(root_item)
        self._add_tree_children(root_item, root)
        self.tree.expandAll()

    def show_node_properties(self, node, valid_parents):
        self.current_node = node

        self.selected_title.setText(node.name)
        self.type_label.setText(f"Tipo: {node.__class__.__name__}")
        self.uuid_label.setText(f"UUID: {node.uuid}")

        self.name_input.blockSignals(True)
        self.name_input.setText(node.name)
        self.name_input.blockSignals(False)

        self.size_slider.blockSignals(True)
        self.size_slider.setValue(int(getattr(node, "size", 100)))
        self.size_slider.blockSignals(False)

        is_space = node.__class__.__name__.lower() == "space"

        self.capacity_label.setEnabled(is_space)
        self.capacity_input.setEnabled(is_space)

        self.capacity_input.blockSignals(True)
        self.capacity_input.setValue(getattr(node, "capacity", 0))
        self.capacity_input.blockSignals(False)

    def clear_properties_panel(self):
        self.current_node = None

        self.selected_title.setText("Sin selección")
        self.type_label.setText("Tipo: -")
        self.uuid_label.setText("UUID: -")

        self.name_input.blockSignals(True)
        self.name_input.clear()
        self.name_input.blockSignals(False)

        self.size_slider.blockSignals(True)
        self.size_slider.setValue(100)
        self.size_slider.blockSignals(False)

        self.capacity_input.blockSignals(True)
        self.capacity_input.setValue(0)
        self.capacity_input.blockSignals(False)

        self.capacity_label.setEnabled(False)
        self.capacity_input.setEnabled(False)

    def show_error(self, message):
        print(f"[UI error] {message}")

    

    # Eventos UI

    def _on_tree_item_clicked(self, item, column):
        node_uuid = item.data(0, Qt.ItemDataRole.UserRole)
        if node_uuid:
            self.controller.select_node(node_uuid)

    def _create_group(self):
        parent_uuid = self._get_selected_parent_uuid()
        self.controller.create_group("Nuevo grupo", parent_uuid=parent_uuid)

    def _create_space(self):
        parent_uuid = self._get_selected_parent_uuid()
        self.controller.create_space("Nuevo espacio", parent_uuid=parent_uuid)

    def _toggle_selected_group(self):
        if self.current_node is not None:
            self.controller.toggle_group(self.current_node.uuid)

    def _on_name_edited(self):
        if self.current_node is not None:
            self.controller.rename_selected_node(self.name_input.text())

    def _on_size_changed(self, value):
        if self.current_node is not None:
            self.controller.update_selected_node_size(float(value))

    def _on_capacity_changed(self, value):
        if self.current_node is not None:
            self.controller.update_selected_space_capacity(value)

    # Helpers

    def _get_selected_parent_uuid(self):
        if self.current_node is None:
            return None

        node_type = self.current_node.__class__.__name__.lower()

        if node_type in ["root", "group"]:
            return self.current_node.uuid

        return None

    def _create_tree_item(self, node):
        label = f"{node.name} ({node.__class__.__name__})"
        item = QTreeWidgetItem([label])
        item.setData(0, Qt.ItemDataRole.UserRole, node.uuid)
        return item

    def _add_tree_children(self, parent_item, parent_node):
        for child in self.controller.faculty.get_children(parent_node.uuid):
            child_item = self._create_tree_item(child)
            parent_item.addChild(child_item)
            self._add_tree_children(child_item, child)

    def _select_tree_item(self, node_uuid):
        if node_uuid is None:
            self.tree.clearSelection()
            return

        queue = [
            self.tree.topLevelItem(i)
            for i in range(self.tree.topLevelItemCount())
        ]

        while queue:
            item = queue.pop(0)

            if item.data(0, Qt.ItemDataRole.UserRole) == node_uuid:
                self.tree.setCurrentItem(item)
                return

            for i in range(item.childCount()):
                queue.append(item.child(i))


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("TFG")
        self.resize(1200, 760)

        self.faculty = Faculty.load_from_csv("Facultades\Pruebas\escenario_facultad_ejemplo.csv")
        self.faculty.print_tree()
        self.controller = BuilderController(self.faculty)

        self.stacked = QStackedWidget()

        self.builder_page = BuilderPage(self.stacked, self.controller)
        self.menu_page = MenuPage(self.stacked, self.controller)

        self.stacked.addWidget(self.menu_page)
        self.stacked.addWidget(self.builder_page)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stacked)
        self.setLayout(layout)

        self.setStyleSheet("""
            QWidget {
                background-color: #2c2f33;
                color: white;
            }

            QLabel {
                color: white;
            }

            QPushButton {
                background-color: #7289da;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                padding: 8px;
            }

            QPushButton:hover {
                background-color: #5b6eae;
            }

            QPushButton:pressed {
                background-color: #4e5d94;
            }

            QLineEdit, QSpinBox, QTreeWidget {
                background-color: #f4f6f7;
                color: #1f2933;
                border-radius: 5px;
                padding: 4px;
            }

            QSlider {
                background-color: transparent;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())