from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QFrame, QHBoxLayout, QPushButton
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
        self.update_builder_mode(self.controller.get_builder_mode())

    def _build_ui(self):
        escape_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        escape_shortcut.activated.connect(lambda: self.stacked_widget.setCurrentIndex(0))

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        self.tree_panel = BuilderTreePanel()
        self.properties_panel = BuilderPropertiesPanel()

        # Centro con botón de modo + grafo
        self.center_panel = QFrame()
        self.center_layout = QVBoxLayout(self.center_panel)
        self.center_layout.setContentsMargins(6, 6, 6, 6)
        self.center_layout.setSpacing(6)

        top_bar = QHBoxLayout()
        top_bar.addStretch()

        self.mode_button = QPushButton()
        self.mode_button.setFixedHeight(34)
        self.mode_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(114, 137, 218, 150);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(91, 110, 174, 180);
            }
        """)

        top_bar.addWidget(self.mode_button)

        self.graph_view = GraphView()

        self.center_layout.addLayout(top_bar)
        self.center_layout.addWidget(self.graph_view)

        self.tree_panel.setMinimumWidth(180)
        self.center_panel.setMinimumWidth(250)
        self.properties_panel.setMinimumWidth(220)

        self.splitter.addWidget(self.tree_panel)
        self.splitter.addWidget(self.center_panel)
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
        self.tree_panel.create_primary_requested.connect(self.controller.create_primary_node)
        self.tree_panel.create_secondary_requested.connect(self.controller.create_secondary_node)
        self.tree_panel.create_tertiary_requested.connect(self.controller.create_tertiary_node)
        self.tree_panel.delete_requested.connect(self.controller.delete_selected_node)
        self.tree_panel.toggle_container_requested.connect(self._toggle_current_group)

        # Grafo central
        self.graph_view.node_selected.connect(self.controller.select_node)
        self.graph_view.node_deselected.connect(self.controller.clear_selection)
        self.graph_view.node_double_clicked.connect(self.controller.toggle_group)

        # Botón modo
        self.mode_button.clicked.connect(self.controller.toggle_builder_mode)

        # Panel derecho
        self.properties_panel.properties_changed.connect(
            self.controller.update_selected_builder_properties
        )
        self.properties_panel.delete_requested.connect(
            self.controller.delete_selected_node
        )

    # ============================================================
    # Métodos llamados por BuilderController
    # ============================================================

    def update_builder_mode(self, mode: str):
        self.tree_panel.set_mode(mode)

        if mode == "space":
            self.mode_button.setText("Cambiar a Agent Builder")
        else:
            self.mode_button.setText("Cambiar a Space Builder")

    def render_tree(self, root):
        self.tree_panel.render_tree(
            root=root,
            get_children_func=self.controller.get_children_for_current_mode,
        )

    def render_graph(self, graph_data):
        self.graph_view.render_graph(graph_data)

    def select_node_visual(self, node_uuid):
        self.graph_view.select_node_visual(node_uuid)
        self.tree_panel.select_node(node_uuid)

    def show_node_properties(self, node, valid_parents, form_options):
        self.current_node = node
        self.properties_panel.show_node(node, valid_parents, form_options)

    def clear_properties_panel(self):
        self.current_node = None
        self.properties_panel.clear()

    def show_error(self, message):
        print(f"[UI error] {message}")

    # ============================================================
    # Acciones auxiliares
    # ============================================================

    def _toggle_current_group(self):
        if self.current_node is not None:
            self.controller.toggle_group(self.current_node.uuid)

    def forget_graph_nodes(self, node_uuids: list[str]) -> None:
        self.graph_view.forget_node_positions(node_uuids)