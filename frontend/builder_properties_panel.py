from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QComboBox, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from frontend.styles import RIGHT_PANEL_STYLE


class BuilderPropertiesPanel(QFrame):
    properties_changed = Signal(dict)
    delete_requested = Signal()

    def __init__(self):
        super().__init__()

        self.current_node = None
        self.field_widgets = {}

        self.setStyleSheet(RIGHT_PANEL_STYLE)
        self._build_ui()
        self.clear()

    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(8)

        self.selected_title = QLabel("Sin selección")
        self.selected_title.setFont(QFont("Arial", 13, QFont.Weight.Bold))

        self.type_label = QLabel("Tipo: -")
        self.uuid_label = QLabel("UUID: -")
        self.uuid_label.setWordWrap(True)

        self.form_layout = QVBoxLayout()
        self.form_layout.setSpacing(8)

        self.apply_button = QPushButton("Aplicar cambios")
        self.apply_button.clicked.connect(self._emit_properties_changed)

        self.delete_button = QPushButton("Eliminar nodo")
        self.delete_button.clicked.connect(self.delete_requested.emit)

        self.main_layout.addWidget(self.selected_title)
        self.main_layout.addWidget(self.type_label)
        self.main_layout.addWidget(self.uuid_label)
        self.main_layout.addSpacing(10)
        self.main_layout.addLayout(self.form_layout)
        self.main_layout.addSpacing(10)
        self.main_layout.addWidget(self.apply_button)
        self.main_layout.addWidget(self.delete_button)
        self.main_layout.addStretch()

    def show_node(self, node, valid_parents, form_options):
        self.current_node = node

        self.selected_title.setText(node.name)
        self.type_label.setText(f"Tipo: {node.__class__.__name__}")
        self.uuid_label.setText(f"UUID: {node.uuid}")

        self._clear_form()

        node_type = node.__class__.__name__.lower()

        if node_type == "root":
            self._build_faculty_form(node, form_options)
        elif node_type == "group":
            self._build_group_form(node, form_options)
        elif node_type == "space":
            self._build_space_form(node, form_options)

        self.delete_button.setEnabled(node_type != "root")

    def clear(self):
        self.current_node = None

        self.selected_title.setText("Sin selección")
        self.type_label.setText("Tipo: -")
        self.uuid_label.setText("UUID: -")

        self._clear_form()
        self.delete_button.setEnabled(False)

    # ============================================================
    # Construcción de formularios
    # ============================================================

    def _build_faculty_form(self, node, form_options):
        # No opcionales
        self._add_text("name", "Nombre", node.name)
        self._add_combo(
            "opening_time",
            "Hora de apertura",
            form_options["time_options"],
            getattr(node, "opening_time", None),
        )
        self._add_combo(
            "closing_time",
            "Hora de cierre",
            form_options["time_options"],
            getattr(node, "closing_time", None),
        )
        self._add_combo(
            "schedule_slot_minutes",
            "Duración del slot",
            [str(v) for v in form_options["slot_options"]],
            str(getattr(node, "schedule_slot_minutes", 30)),
        )
        self._add_multi_check(
            "calendar_days",
            "Días del calendario",
            form_options["calendar_day_options"],
            getattr(node, "calendar_days", []),
        )

        # Opcionales
        self._add_optional_title()
        self._add_checkbox(
            "default_ventilated",
            "Ventilación por defecto",
            getattr(node, "default_ventilated", False),
        )

    def _build_group_form(self, node, form_options):
        # No opcionales
        self._add_text("name", "Nombre", node.name)

        # Opcionales
        self._add_optional_title()
        self._add_checkbox(
            "default_ventilated",
            "Ventilación por defecto",
            getattr(node, "default_ventilated", False),
        )
        self._add_combo_with_none(
            "opening_time_override",
            "Override apertura",
            form_options["time_options"],
            getattr(node, "opening_time_override", None),
            none_label="Sin override",
        )
        self._add_combo_with_none(
            "closing_time_override",
            "Override cierre",
            form_options["time_options"],
            getattr(node, "closing_time_override", None),
            none_label="Sin override",
        )

    def _build_space_form(self, node, form_options):
        # No opcionales
        self._add_text("name", "Nombre", node.name)

        # Opcionales
        self._add_optional_title()
        self._add_combo_from_pairs_with_none(
            "space_type_uuid",
            "Tipo de espacio",
            form_options["space_type_options"],
            getattr(node, "space_type_uuid", None),
            none_label="Sin tipo",
        )
        self._add_checkbox(
            "ventilated",
            "Ventilado",
            getattr(node, "ventilated", False),
        )
        self._add_combo_with_none(
            "opening_time_override",
            "Override apertura",
            form_options["time_options"],
            getattr(node, "opening_time_override", None),
            none_label="Sin override",
        )
        self._add_combo_with_none(
            "closing_time_override",
            "Override cierre",
            form_options["time_options"],
            getattr(node, "closing_time_override", None),
            none_label="Sin override",
        )

    # ============================================================
    # Helpers de widgets
    # ============================================================

    def _clear_form(self):
        self.field_widgets = {}

        while self.form_layout.count():
            item = self.form_layout.takeAt(0)
            widget = item.widget()
            layout = item.layout()

            if widget is not None:
                widget.deleteLater()
            elif layout is not None:
                while layout.count():
                    child_item = layout.takeAt(0)
                    child_widget = child_item.widget()
                    if child_widget is not None:
                        child_widget.deleteLater()

    def _add_optional_title(self):
        label = QLabel("Opcionales:")
        label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        self.form_layout.addWidget(label)

    def _add_readonly(self, label_text, value):
        label = QLabel(label_text)
        field = QLineEdit(str(value))
        field.setReadOnly(True)

        self.form_layout.addWidget(label)
        self.form_layout.addWidget(field)

    def _add_text(self, key, label_text, value):
        label = QLabel(label_text)
        field = QLineEdit(str(value))

        self.form_layout.addWidget(label)
        self.form_layout.addWidget(field)
        self.field_widgets[key] = field

    def _add_checkbox(self, key, label_text, checked):
        field = QCheckBox(label_text)
        field.setChecked(bool(checked))

        self.form_layout.addWidget(field)
        self.field_widgets[key] = field

    def _add_combo(self, key, label_text, items, selected_value):
        label = QLabel(label_text)
        field = QComboBox()

        for item in items:
            field.addItem(str(item), str(item))

        index = field.findData(str(selected_value))
        if index >= 0:
            field.setCurrentIndex(index)

        self.form_layout.addWidget(label)
        self.form_layout.addWidget(field)
        self.field_widgets[key] = field

    def _add_combo_with_none(self, key, label_text, items, selected_value, none_label="Ninguno"):
        label = QLabel(label_text)
        field = QComboBox()

        field.addItem(none_label, None)

        for item in items:
            field.addItem(str(item), str(item))

        index = field.findData(selected_value)
        if index >= 0:
            field.setCurrentIndex(index)
        else:
            field.setCurrentIndex(0)

        self.form_layout.addWidget(label)
        self.form_layout.addWidget(field)
        self.field_widgets[key] = field

    def _add_combo_from_pairs_with_none(self, key, label_text, items, selected_value, none_label="Ninguno"):
        label = QLabel(label_text)
        field = QComboBox()

        field.addItem(none_label, None)

        for item in items:
            field.addItem(item["name"], item["uuid"])

        index = field.findData(selected_value)
        if index >= 0:
            field.setCurrentIndex(index)
        else:
            field.setCurrentIndex(0)

        self.form_layout.addWidget(label)
        self.form_layout.addWidget(field)
        self.field_widgets[key] = field

    def _add_multi_check(self, key, label_text, options, selected_values):
        label = QLabel(label_text)
        widget = QListWidget()

        selected_values = set(selected_values or [])

        for option in options:
            item = QListWidgetItem(option)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if option in selected_values else Qt.CheckState.Unchecked
            )
            widget.addItem(item)

        self.form_layout.addWidget(label)
        self.form_layout.addWidget(widget)
        self.field_widgets[key] = widget

    # ============================================================
    # Emisión de cambios
    # ============================================================

    def _emit_properties_changed(self):
        if self.current_node is None:
            return

        values = {}

        for key, widget in self.field_widgets.items():
            if isinstance(widget, QLineEdit):
                values[key] = widget.text()

            elif isinstance(widget, QCheckBox):
                values[key] = widget.isChecked()

            elif isinstance(widget, QComboBox):
                values[key] = widget.currentData()

            elif isinstance(widget, QListWidget):
                selected = []
                for i in range(widget.count()):
                    item = widget.item(i)
                    if item.checkState() == Qt.CheckState.Checked:
                        selected.append(item.text())
                values[key] = selected

        if "schedule_slot_minutes" in values and values["schedule_slot_minutes"] is not None:
            values["schedule_slot_minutes"] = int(values["schedule_slot_minutes"])

        self.properties_changed.emit(values)