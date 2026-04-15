from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QLineEdit,
    QSlider, QSpinBox, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from frontend.styles import RIGHT_PANEL_STYLE


class BuilderPropertiesPanel(QFrame):
    name_changed = Signal(str)
    size_changed = Signal(float)
    capacity_changed = Signal(int)
    delete_requested = Signal()

    def __init__(self):
        super().__init__()

        self.current_node = None

        self.setStyleSheet(RIGHT_PANEL_STYLE)
        self._build_ui()
        self.clear()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.selected_title = QLabel("Sin selección")
        self.selected_title.setFont(QFont("Arial", 13, QFont.Weight.Bold))

        self.type_label = QLabel("Tipo: -")
        self.uuid_label = QLabel("UUID: -")
        self.uuid_label.setWordWrap(True)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nombre")
        self.name_input.editingFinished.connect(self._emit_name_changed)

        self.size_label = QLabel("Tamaño del nodo")
        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setRange(50, 220)
        self.size_slider.valueChanged.connect(self._emit_size_changed)

        self.capacity_label = QLabel("Capacidad")
        self.capacity_input = QSpinBox()
        self.capacity_input.setRange(0, 10000)
        self.capacity_input.valueChanged.connect(self._emit_capacity_changed)

        self.delete_button = QPushButton("Eliminar nodo")
        self.delete_button.clicked.connect(self.delete_requested.emit)

        layout.addWidget(self.selected_title)
        layout.addWidget(self.type_label)
        layout.addWidget(self.uuid_label)

        layout.addSpacing(12)
        layout.addWidget(QLabel("Nombre"))
        layout.addWidget(self.name_input)

        layout.addSpacing(12)
        layout.addWidget(self.size_label)
        layout.addWidget(self.size_slider)

        layout.addSpacing(12)
        layout.addWidget(self.capacity_label)
        layout.addWidget(self.capacity_input)

        layout.addSpacing(12)
        layout.addWidget(self.delete_button)

        layout.addStretch()

    def show_node(self, node, valid_parents):
        self.current_node = node

        node_type = node.__class__.__name__.lower()
        is_space = node_type == "space"

        self.selected_title.setText(node.name)
        self.type_label.setText(f"Tipo: {node.__class__.__name__}")
        self.uuid_label.setText(f"UUID: {node.uuid}")

        self.name_input.blockSignals(True)
        self.name_input.setText(node.name)
        self.name_input.blockSignals(False)

        self.size_slider.blockSignals(True)
        self.size_slider.setValue(int(getattr(node, "size", 100)))
        self.size_slider.blockSignals(False)

        self.capacity_label.setEnabled(is_space)
        self.capacity_input.setEnabled(is_space)

        self.capacity_input.blockSignals(True)
        self.capacity_input.setValue(getattr(node, "capacity", 0))
        self.capacity_input.blockSignals(False)

        self.delete_button.setEnabled(node_type != "root")

    def clear(self):
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
        self.delete_button.setEnabled(False)

    def _emit_name_changed(self):
        if self.current_node is not None:
            self.name_changed.emit(self.name_input.text())

    def _emit_size_changed(self, value):
        if self.current_node is not None:
            self.size_changed.emit(float(value))

    def _emit_capacity_changed(self, value):
        if self.current_node is not None:
            self.capacity_changed.emit(value)