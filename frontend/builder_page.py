from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter
from PySide6.QtCore import Qt
from PySide6.QtGui import QShortcut, QKeySequence

from frontend.builder_tree_panel import BuilderTreePanel
from frontend.builder_properties_panel import BuilderPropertiesPanel
from frontend.graph_view import GraphView


class BuilderPage(QWidget):
    def __init__(self, stacked_widget, builder_controller):
        super().__init__()

        self.stacked_widget = stacked_widget
        self.controller = builder_controller
        self.controller.attach_ui(self)

        self.current_node = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self):
        escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        escape_shortcut.activated.connect(lambda: self.stacked_widget.setCurrentIndex(0))

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        self.tree_panel = BuilderTreePanel()
        self.graph_view = GraphView()
        self.properties_panel = BuilderPropertiesPanel()

        self.tree_panel.setMinimumWidth(180)
        self.graph_view.setMinimumWidth(250)
        self.properties_panel.setMinimumWidth(220)

        self.splitter.addWidget(self.tree_panel)
        self.splitter.addWidget(self.graph_view)
        self.splitter.addWidget(self.properties_panel)

        self.splitter.setSizes([240, 620, 280])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setStretchFactor(2, 0)

        main_layout.addWidget(self.splitter)
        self.setLayout(main_layout)

    def _connect_signals(self):
        # Árbol izquierdo
        self.tree_panel.node_selected.connect(self.controller.select_node)
        self.tree_panel.create_group_requested.connect(self._create_group_from_current_selection)
        self.tree_panel.create_space_requested.connect(self._create_space_from_current_selection)
        self.tree_panel.delete_requested.connect(self.controller.delete_selected_node)
        self.tree_panel.toggle_group_requested.connect(self._toggle_current_group)

        # Grafo central
        self.graph_view.node_selected.connect(self.controller.select_node)
        self.graph_view.node_deselected.connect(self.controller.clear_selection)
        self.graph_view.node_double_clicked.connect(self.controller.toggle_group)

        # Panel derecho
        self.properties_panel.name_changed.connect(self.controller.rename_selected_node)
        self.properties_panel.size_changed.connect(self.controller.update_selected_node_size)
        self.properties_panel.capacity_changed.connect(self.controller.update_selected_space_capacity)
        self.properties_panel.delete_requested.connect(self.controller.delete_selected_node)

    # ============================================================
    # Métodos llamados por BuilderController
    # ============================================================

    def render_tree(self, root):
        self.tree_panel.render_tree(
            root=root,
            get_children_func=self.controller.faculty.get_children,
        )

    def render_graph(self, graph_data):
        self.graph_view.render_graph(graph_data)

    def select_node_visual(self, node_uuid):
        self.graph_view.select_node_visual(node_uuid)
        self.tree_panel.select_node(node_uuid)

    def show_node_properties(self, node, valid_parents):
        self.current_node = node
        self.properties_panel.show_node(node, valid_parents)

    def clear_properties_panel(self):
        self.current_node = None
        self.properties_panel.clear()

    def show_error(self, message):
        print(f"[UI error] {message}")

    # ============================================================
    # Acciones auxiliares
    # ============================================================

    def _create_group_from_current_selection(self):
        parent_uuid = self._get_selected_parent_uuid()
        self.controller.create_group("Nuevo grupo", parent_uuid=parent_uuid)

    def _create_space_from_current_selection(self):
        parent_uuid = self._get_selected_parent_uuid()
        self.controller.create_space("Nuevo espacio", parent_uuid=parent_uuid)

    def _toggle_current_group(self):
        if self.current_node is not None:
            self.controller.toggle_group(self.current_node.uuid)

    def _get_selected_parent_uuid(self):
        if self.current_node is None:
            return None

        node_type = self.current_node.__class__.__name__.lower()

        if node_type in ["root", "group"]:
            return self.current_node.uuid

        return None