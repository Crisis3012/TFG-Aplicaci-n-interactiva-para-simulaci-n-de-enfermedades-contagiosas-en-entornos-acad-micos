from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QLineEdit, QPushButton,
    QCheckBox, QComboBox, QListWidget, QListWidgetItem,
    QTableWidget, QHeaderView, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from frontend.styles import RIGHT_PANEL_STYLE


class NoWheelComboBox(QComboBox):
    def wheelEvent(self, event):
        # Evita que la rueda cambie la opción del combo.
        # Así el scroll sigue funcionando en la tabla.
        event.ignore()


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
        elif node_type in ("group", "spacegroup"):
            self._build_space_group_form(node, form_options)
        elif node_type == "space":
            self._build_space_form(node, form_options)
        elif node_type == "career":
            self._build_career_form(node)
        elif node_type == "course":
            self._build_course_form(node, form_options)
        elif node_type == "coursegroup":
            self._build_course_group_form(node, form_options)

        self.delete_button.setEnabled(node_type != "root")

    def clear(self):
        self.current_node = None
        self.selected_title.setText("Sin selección")
        self.type_label.setText("Tipo: -")
        self.uuid_label.setText("UUID: -")
        self._clear_form()
        self.delete_button.setEnabled(False)

    # ============================================================
    # Formularios
    # ============================================================

    def _build_faculty_form(self, node, form_options):
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

        self._add_optional_title()
        self._add_checkbox(
            "default_ventilated",
            "Ventilación por defecto",
            getattr(node, "default_ventilated", False),
        )

    def _build_space_group_form(self, node, form_options):
        self._add_text("name", "Nombre", node.name)

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
        self._add_text("name", "Nombre", node.name)

        self._add_optional_title()

        self._add_number_text(
            "capacity",
            "Capacidad",
            getattr(node, "capacity", None),
        )

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

    def _build_career_form(self, node):
        self._add_text("name", "Nombre", node.name)
        self._add_number_text("students_by_year", "Estudiantes por año", getattr(node, "students_by_year", None))

        self._add_optional_title()
        self._add_float_text("default_attendance_rate", "Asistencia por defecto (0-100)", getattr(node, "default_attendance_rate", None))
        self._add_float_text("mean_age", "Edad media", getattr(node, "mean_age", None))
        self._add_float_text("std_age", "Desviación edad", getattr(node, "std_age", None))
        self._add_float_text("sex_ratio", "Sex ratio", getattr(node, "sex_ratio", None))

    def _build_course_form(self, node, form_options):
        self._add_text("name", "Nombre", node.name)

        self._add_optional_title()
        self._add_number_text("number_of_students", "Número de estudiantes", getattr(node, "number_of_students", None))
        self._add_float_text("attendance_rate", "Asistencia (0-100)", getattr(node, "attendance_rate", None))
        self._add_float_text("mean_age", "Edad media", getattr(node, "mean_age", None))
        self._add_float_text("std_age", "Desviación edad", getattr(node, "std_age", None))
        self._add_float_text("sex_ratio", "Sex ratio", getattr(node, "sex_ratio", None))

        self._add_schedule_table(
            key="base_schedule_blocks",
            label_text="Horario del curso",
            form_options=form_options,
            existing_blocks=getattr(node, "base_schedule", []),
            table_mode="base",
            inherited_blocks=[],
        )

    def _build_course_group_form(self, node, form_options):
        self._add_text("name", "Nombre", node.name)

        self._add_optional_title()
        self._add_number_text("number_of_students", "Número de estudiantes", getattr(node, "number_of_students", None))
        self._add_float_text("attendance_rate", "Asistencia (0-100)", getattr(node, "attendance_rate", None))
        self._add_float_text("mean_age", "Edad media", getattr(node, "mean_age", None))
        self._add_float_text("std_age", "Desviación edad", getattr(node, "std_age", None))
        self._add_float_text("sex_ratio", "Sex ratio", getattr(node, "sex_ratio", None))

        self._add_schedule_table(
            key="schedule_override_blocks",
            label_text="Horario del grupo",
            form_options=form_options,
            existing_blocks=getattr(node, "schedule_overrides", []),
            table_mode="override",
            inherited_blocks=form_options.get("course_base_schedule", []),
        )

    # ============================================================
    # Tabla de horarios
    # ============================================================

    def _get_schedule_combo_style(self, table_mode: str, has_value: bool) -> str:
        if not has_value:
            return """
                QComboBox {
                    background-color: #f4f6f7;
                    color: #1f2933;
                    border: 1px solid #c7ccd1;
                    border-radius: 4px;
                    padding: 2px 6px;
                }
            """

        if table_mode == "base":
            return """
                QComboBox {
                    background-color: #cfe8ff;
                    color: #102a43;
                    border: 1px solid #7fb3e6;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-weight: 600;
                }
            """

        return """
            QComboBox {
                background-color: #e4d4ff;
                color: #3d2466;
                border: 1px solid #ad8ee6;
                border-radius: 4px;
                padding: 2px 6px;
                font-weight: 600;
            }
        """


    def _update_schedule_combo_visual(self, combo, table_mode: str):
        current_data = combo.currentData()
        inherited_uuid = combo.property("inherited_uuid")

        if table_mode == "base":
            has_value = current_data is not None
            combo.setStyleSheet(self._get_schedule_combo_style("base", has_value))

            if current_data is None:
                combo.setToolTip("Sin asignación")
            else:
                combo.setToolTip(combo.currentText())
            return

        # Modo override (CourseGroup)
        if current_data == "__inherit__":
            combo.setStyleSheet("""
                QComboBox {
                    background-color: #cfe8ff;
                    color: #102a43;
                    border: 1px solid #7fb3e6;
                    border-radius: 4px;
                    padding: 2px 6px;
                    font-weight: 600;
                }
            """)
            combo.setToolTip("Bloque heredado del curso")
            return

        if current_data is None:
            combo.setStyleSheet(self._get_schedule_combo_style("empty", False))
            combo.setToolTip("Sin asignación")
            return

        combo.setStyleSheet("""
            QComboBox {
                background-color: #e4d4ff;
                color: #3d2466;
                border: 1px solid #ad8ee6;
                border-radius: 4px;
                padding: 2px 6px;
                font-weight: 600;
            }
        """)
        combo.setToolTip("Override del grupo")
    
    def _get_space_name_by_uuid(self, form_options, space_uuid):
        for item in form_options["space_options"]:
            if item["uuid"] == space_uuid:
                return item["name"]
        return "Espacio"

    def _add_schedule_table(
        self,
        key,
        label_text,
        form_options,
        existing_blocks,
        table_mode="base",
        inherited_blocks=None,
    ):
        label = QLabel(label_text)
        label.setFont(QFont("Arial", 11, QFont.Weight.Bold))
        legend = QLabel(
            "Azul = horario base asignado" if table_mode == "base"
            else "Azul = heredado | Morado = modificación del grupo"
        )
        legend.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 11px;
                font-weight: 600;
                padding-bottom: 2px;
            }
        """)

        days = form_options["schedule_days"]
        rows = form_options["schedule_rows"]
        spaces = form_options["space_options"]
        inherited_blocks = inherited_blocks or []

        table = QTableWidget(len(rows), len(days))
        table.setHorizontalHeaderLabels(days)
        table.setVerticalHeaderLabels([row["label"] for row in rows])

        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.setMinimumHeight(260)

        # Comportamiento más cómodo para esta tabla
        table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

        existing_map = {}
        for block in existing_blocks:
            existing_map[(block.day_of_week, block.start_time, block.end_time)] = block.space_uuid

        inherited_map = {}
        for block in inherited_blocks:
            inherited_map[(block.day_of_week, block.start_time, block.end_time)] = block.space_uuid

        for row_index, row in enumerate(rows):
            for col_index, day in enumerate(days):
                combo = NoWheelComboBox()
                combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)

                slot_key = (day, row["start_time"], row["end_time"])
                override_space_uuid = existing_map.get(slot_key, None)
                inherited_space_uuid = inherited_map.get(slot_key, None)

                if table_mode == "override" and inherited_space_uuid is not None:
                    inherited_name = self._get_space_name_by_uuid(form_options, inherited_space_uuid)
                    combo.addItem(f"Heredar ({inherited_name})", "__inherit__")
                else:
                    combo.addItem("-", None)

                for space in spaces:
                    combo.addItem(space["name"], space["uuid"])

                if override_space_uuid is not None:
                    selected_index = combo.findData(override_space_uuid)
                elif table_mode == "override" and inherited_space_uuid is not None:
                    selected_index = combo.findData("__inherit__")
                else:
                    selected_index = combo.findData(None)

                if selected_index >= 0:
                    combo.setCurrentIndex(selected_index)
                else:
                    combo.setCurrentIndex(0)

                combo.setProperty("table_mode", table_mode)
                combo.setProperty("inherited_uuid", inherited_space_uuid)

                combo.currentIndexChanged.connect(
                    lambda _=None, c=combo: self._update_schedule_combo_visual(
                        c,
                        c.property("table_mode"),
                    )
                )

                self._update_schedule_combo_visual(combo, table_mode)

                table.setCellWidget(row_index, col_index, combo)

        self.form_layout.addWidget(label)
        self.form_layout.addWidget(legend)
        self.form_layout.addWidget(table)
        self.field_widgets[key] = {
            "table": table,
            "days": days,
            "rows": rows,
        }

    def _extract_schedule_blocks_from_table(self, widget_info):
        table = widget_info["table"]
        days = widget_info["days"]
        rows = widget_info["rows"]

        blocks = []

        for row_index, row in enumerate(rows):
            for col_index, day in enumerate(days):
                combo = table.cellWidget(row_index, col_index)
                if combo is None:
                    continue

                space_uuid = combo.currentData()

                # "__inherit__" significa: no guardar override
                if space_uuid in (None, "__inherit__"):
                    continue

                blocks.append({
                    "day_of_week": day,
                    "start_time": row["start_time"],
                    "end_time": row["end_time"],
                    "space_uuid": space_uuid,
                })

        return blocks

    # ============================================================
    # Helpers UI
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

    def _add_text(self, key, label_text, value):
        label = QLabel(label_text)
        field = QLineEdit("" if value is None else str(value))

        self.form_layout.addWidget(label)
        self.form_layout.addWidget(field)
        self.field_widgets[key] = field

    def _add_number_text(self, key, label_text, value):
        self._add_text(key, label_text, "" if value is None else value)

    def _add_float_text(self, key, label_text, value):
        self._add_text(key, label_text, "" if value is None else value)

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

    def apply_current_changes(self):
        self._emit_properties_changed()

    def _emit_properties_changed(self):
        if self.current_node is None:
            return

        values = {}

        for key, widget in self.field_widgets.items():
            if isinstance(widget, QLineEdit):
                text = widget.text().strip()
                values[key] = text if text != "" else None

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

            elif isinstance(widget, dict) and "table" in widget:
                values[key] = self._extract_schedule_blocks_from_table(widget)

        if "schedule_slot_minutes" in values and values["schedule_slot_minutes"] is not None:
            values["schedule_slot_minutes"] = int(values["schedule_slot_minutes"])

        for int_key in ("students_by_year", "number_of_students", "capacity"):
            if int_key in values and values[int_key] is not None:
                values[int_key] = int(values[int_key])

        for float_key in ("default_attendance_rate", "mean_age", "std_age", "sex_ratio", "attendance_rate"):
            if float_key in values and values[float_key] is not None:
                values[float_key] = float(values[float_key])

        self.properties_changed.emit(values)