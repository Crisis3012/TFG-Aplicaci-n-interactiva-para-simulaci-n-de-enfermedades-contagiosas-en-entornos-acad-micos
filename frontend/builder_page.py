from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QSplitter, QFrame, QHBoxLayout,
    QPushButton, QMessageBox, QScrollArea
)
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

        self.properties_scroll = QScrollArea()
        self.properties_scroll.setWidgetResizable(True)
        self.properties_scroll.setWidget(self.properties_panel)
        self.properties_scroll.setMinimumWidth(220)
        self.properties_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        # Centro con barra superior + grafo
        self.center_panel = QFrame()
        self.center_layout = QVBoxLayout(self.center_panel)
        self.center_layout.setContentsMargins(6, 6, 6, 6)
        self.center_layout.setSpacing(6)

        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.back_button = QPushButton("Volver")
        self.back_button.setFixedHeight(34)
        self.back_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(90, 98, 108, 180);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: rgba(110, 118, 128, 210);
            }
        """)
        self.back_button.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))

        self.save_button = QPushButton("Guardar facultad")
        self.save_button.setFixedHeight(34)
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(67, 160, 71, 180);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(56, 142, 60, 220);
            }
        """)

        self.reset_layout_button = QPushButton("Reordenar grafo")
        self.reset_layout_button.setFixedHeight(34)
        self.reset_layout_button.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 167, 38, 180);
                color: white;
                border: none;
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(251, 140, 0, 220);
            }
        """)

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

        top_bar.addWidget(self.back_button)
        top_bar.addWidget(self.save_button)
        top_bar.addWidget(self.reset_layout_button)
        top_bar.addStretch()
        top_bar.addWidget(self.mode_button)

        self.graph_view = GraphView()

        self.center_layout.addLayout(top_bar)
        self.center_layout.addWidget(self.graph_view)

        self.tree_panel.setMinimumWidth(180)
        self.center_panel.setMinimumWidth(250)
        self.properties_panel.setMinimumWidth(220)
        self.properties_scroll.setMinimumWidth(240)

        self.properties_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.properties_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.splitter.addWidget(self.tree_panel)
        self.splitter.addWidget(self.center_panel)
        self.splitter.addWidget(self.properties_scroll)

        self.splitter.setSizes([210, 620, 320])
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

        # Botones superiores
        self.mode_button.clicked.connect(self.controller.toggle_builder_mode)
        self.save_button.clicked.connect(self.controller.save_active_faculty)
        self.reset_layout_button.clicked.connect(self._reset_graph_layout)

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
        QMessageBox.critical(self, "Error", str(message))

    def show_info(self, message):
        QMessageBox.information(self, "Información", str(message))

    def apply_current_properties(self):
        """
        Fuerza a aplicar los cambios visibles del panel derecho antes de guardar.

        Esto hace que si el usuario modifica el nodo seleccionado y pulsa
        directamente 'Guardar facultad', esos cambios también se vuelquen
        al modelo antes de escribir los archivos.
        """
        if self.current_node is None:
            return

        if hasattr(self.properties_panel, "apply_current_changes"):
            self.properties_panel.apply_current_changes()

    # ============================================================
    # Acciones auxiliares
    # ============================================================

    def _toggle_current_group(self):
        if self.current_node is not None:
            self.controller.toggle_group(self.current_node.uuid)

    def _reset_graph_layout(self):
        self.graph_view.reset_layout()
        self.controller.refresh_all()

    def forget_graph_nodes(self, node_uuids: list[str]) -> None:
        self.graph_view.forget_node_positions(node_uuids)