from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton,
    QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from frontend.styles import LEFT_PANEL_STYLE


class BuilderTreePanel(QFrame):
    node_selected = Signal(str)

    create_primary_requested = Signal()
    create_secondary_requested = Signal()
    create_tertiary_requested = Signal()

    delete_requested = Signal()
    toggle_container_requested = Signal()

    def __init__(self):
        super().__init__()

        self.current_mode = "space"

        self.setStyleSheet(LEFT_PANEL_STYLE)
        self._build_ui()
        self.set_mode("space")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.title = QLabel("Space Builder")
        self.title.setFont(QFont("Arial", 13, QFont.Weight.Bold))

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemClicked.connect(self._on_item_clicked)

        self.btn_primary = QPushButton()
        self.btn_secondary = QPushButton()
        self.btn_tertiary = QPushButton()
        self.btn_toggle = QPushButton("Expandir/contraer")
        self.btn_delete = QPushButton("Eliminar")

        self.btn_primary.clicked.connect(self.create_primary_requested.emit)
        self.btn_secondary.clicked.connect(self.create_secondary_requested.emit)
        self.btn_tertiary.clicked.connect(self.create_tertiary_requested.emit)
        self.btn_toggle.clicked.connect(self.toggle_container_requested.emit)
        self.btn_delete.clicked.connect(self.delete_requested.emit)

        layout.addWidget(self.title)
        layout.addWidget(self.tree)
        layout.addWidget(self.btn_primary)
        layout.addWidget(self.btn_secondary)
        layout.addWidget(self.btn_tertiary)
        layout.addWidget(self.btn_toggle)
        layout.addWidget(self.btn_delete)

    def set_mode(self, mode: str):
        self.current_mode = mode

        if mode == "space":
            self.title.setText("Space Builder")
            self.btn_primary.setText("Crear grupo")
            self.btn_secondary.setText("Crear espacio")
            self.btn_tertiary.hide()

        else:
            self.title.setText("Agent Builder")
            self.btn_primary.setText("Crear carrera")
            self.btn_secondary.setText("Crear curso")
            self.btn_tertiary.setText("Crear grupo de curso")
            self.btn_tertiary.show()

    def render_tree(self, root, get_children_func):
        self.tree.clear()

        root_item = self._create_tree_item(root)
        self.tree.addTopLevelItem(root_item)

        self._add_children(
            parent_item=root_item,
            parent_node=root,
            get_children_func=get_children_func,
        )

        self.tree.expandAll()

    def select_node(self, node_uuid):
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

    def clear_selection(self):
        self.tree.clearSelection()

    def _on_item_clicked(self, item, column):
        node_uuid = item.data(0, Qt.ItemDataRole.UserRole)

        if node_uuid:
            self.node_selected.emit(node_uuid)

    def _create_tree_item(self, node):
        label = f"{node.name} ({node.__class__.__name__})"

        item = QTreeWidgetItem([label])
        item.setData(0, Qt.ItemDataRole.UserRole, node.uuid)

        return item

    def _add_children(self, parent_item, parent_node, get_children_func):
        for child in get_children_func(parent_node.uuid):
            child_item = self._create_tree_item(child)
            parent_item.addChild(child_item)

            self._add_children(
                parent_item=child_item,
                parent_node=child,
                get_children_func=get_children_func,
            )