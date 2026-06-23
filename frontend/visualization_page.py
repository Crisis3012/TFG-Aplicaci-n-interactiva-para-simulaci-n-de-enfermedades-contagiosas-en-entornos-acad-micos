from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QFrame,
    QComboBox,
    QTextEdit,
    QMessageBox,
)


class VisualizationPage(QWidget):
    """
    Página de visualización estática/análisis.

    Esta página no reproduce la simulación animada.
    Sirve para cargar resultados guardados y mostrar análisis:
    - información de facultad;
    - curva SEIR;
    - rankings;
    - contagios por espacios;
    - relaciones entre grupos.
    """

    def __init__(
        self,
        stacked_widget,
        simulation_controller,
        menu_page_index: int = 0,
    ) -> None:
        super().__init__()

        self.stacked_widget = stacked_widget
        self.simulation_controller = simulation_controller
        self.menu_page_index = menu_page_index

        self.result_folders: list[Path] = []
        self.current_result_folder: Optional[Path] = None

        self._build_ui()

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 14, 16, 16)
        main_layout.setSpacing(10)

        header_layout = QHBoxLayout()

        self.back_button = QPushButton("← Volver")
        self.back_button.setFixedWidth(120)
        self.back_button.clicked.connect(self.go_back)

        title = QLabel("Visualización de resultados")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")

        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.setFixedWidth(120)
        self.refresh_button.clicked.connect(self.load_page)

        header_layout.addWidget(self.back_button)
        header_layout.addStretch()
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_button)

        main_layout.addLayout(header_layout)

        self.active_faculty_label = QLabel()
        self.active_faculty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.active_faculty_label.setStyleSheet("font-size: 13px; color: #555;")
        main_layout.addWidget(self.active_faculty_label)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        self.faculty_panel = QFrame()
        self.faculty_panel.setMinimumWidth(330)
        self.faculty_panel.setStyleSheet("""
            QFrame {
                background-color: #f5f7fa;
                border: 1px solid #d0d7de;
                border-radius: 8px;
            }
        """)

        faculty_layout = QVBoxLayout(self.faculty_panel)
        faculty_layout.setContentsMargins(12, 12, 12, 12)
        faculty_layout.setSpacing(8)

        faculty_title = QLabel("Análisis de facultad")
        faculty_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        faculty_layout.addWidget(faculty_title)

        self.faculty_summary_text = QTextEdit()
        self.faculty_summary_text.setReadOnly(True)
        faculty_layout.addWidget(self.faculty_summary_text)

        self.results_panel = QFrame()
        self.results_panel.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #d0d7de;
                border-radius: 8px;
            }
        """)

        results_layout = QVBoxLayout(self.results_panel)
        results_layout.setContentsMargins(12, 12, 12, 12)
        results_layout.setSpacing(8)

        results_header = QHBoxLayout()

        results_title = QLabel("Resultados de simulación")
        results_title.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.result_selector = QComboBox()
        self.result_selector.currentIndexChanged.connect(self._on_result_selected)

        results_header.addWidget(results_title)
        results_header.addStretch()
        results_header.addWidget(QLabel("Simulación:"))
        results_header.addWidget(self.result_selector)

        results_layout.addLayout(results_header)

        self.result_summary_text = QTextEdit()
        self.result_summary_text.setReadOnly(True)
        results_layout.addWidget(self.result_summary_text)

        self.splitter.addWidget(self.faculty_panel)
        self.splitter.addWidget(self.results_panel)
        self.splitter.setSizes([380, 820])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self.splitter)

        self.setLayout(main_layout)

    def load_page(self) -> None:
        self._refresh_active_faculty_label()
        self._render_faculty_summary()
        self._load_result_folders()

    def go_back(self) -> None:
        self.stacked_widget.setCurrentIndex(self.menu_page_index)

    def _refresh_active_faculty_label(self) -> None:
        active_name = self.simulation_controller.active_faculty_name

        if active_name:
            self.active_faculty_label.setText(f"Facultad activa: {active_name}")
        else:
            self.active_faculty_label.setText("No hay ninguna facultad activa.")

    def _render_faculty_summary(self) -> None:
        try:
            faculty = self.simulation_controller.faculty
        except Exception:
            self.faculty_summary_text.setPlainText("No hay ninguna facultad cargada.")
            return

        root = faculty.get_root()
        spaces = faculty.get_all_spaces()

        careers = [
            node for node in faculty.nodes.values()
            if node.__class__.__name__.lower() == "career"
        ]

        courses = [
            node for node in faculty.nodes.values()
            if node.__class__.__name__.lower() == "course"
        ]

        course_groups = [
            node for node in faculty.nodes.values()
            if node.__class__.__name__.lower() == "coursegroup"
        ]

        total_students = 0

        for group in course_groups:
            if getattr(group, "number_of_students", None) is not None:
                total_students += int(group.number_of_students)

        if total_students == 0:
            for course in courses:
                if getattr(course, "number_of_students", None) is not None:
                    total_students += int(course.number_of_students)

        lines = [
            f"Nombre: {root.name}",
            f"Horario: {root.opening_time} - {root.closing_time}",
            f"Slot horario: {root.schedule_slot_minutes} min",
            f"Días activos: {', '.join(root.calendar_days)}",
            "",
            f"Espacios: {len(spaces)}",
            f"Carreras: {len(careers)}",
            f"Cursos: {len(courses)}",
            f"Grupos académicos: {len(course_groups)}",
            f"Estudiantes configurados: {total_students}",
            "",
            "En el siguiente paso añadiremos aquí:",
            "- ranking de espacios más usados",
            "- grafo coloreado por uso semanal",
            "- espacios sin uso",
            "- uso por tipo de espacio",
        ]

        self.faculty_summary_text.setPlainText("\n".join(lines))

    def _load_result_folders(self) -> None:
        self.result_selector.blockSignals(True)
        self.result_selector.clear()
        self.result_folders = []
        self.current_result_folder = None

        try:
            folders = self.simulation_controller.list_saved_results()
        except Exception as exc:
            self.result_summary_text.setPlainText(
                f"No se han podido cargar los resultados:\n{exc}"
            )
            self.result_selector.blockSignals(False)
            return

        self.result_folders = list(folders)

        if not self.result_folders:
            self.result_selector.addItem("No hay resultados guardados")
            self.result_summary_text.setPlainText(
                "Todavía no hay simulaciones guardadas para esta facultad."
            )
            self.result_selector.blockSignals(False)
            return

        for folder in self.result_folders:
            self.result_selector.addItem(folder.name)

        self.result_selector.blockSignals(False)
        self.result_selector.setCurrentIndex(0)
        self._load_result_folder(self.result_folders[0])

    def _on_result_selected(self, index: int) -> None:
        if index < 0 or index >= len(self.result_folders):
            return

        self._load_result_folder(self.result_folders[index])

    def _load_result_folder(self, folder: Path) -> None:
        self.current_result_folder = folder

        metadata = self._read_json(folder / "metadata.json")
        summary = self._read_json(folder / "summary.json")

        if metadata is None or summary is None:
            QMessageBox.warning(
                self,
                "Resultado incompleto",
                f"No se ha podido leer metadata.json o summary.json en:\n{folder}",
            )
            return

        result_type = metadata.get("type", "desconocido")

        lines = [
            f"Carpeta: {folder.name}",
            f"Tipo: {result_type}",
            f"Nombre: {metadata.get('simulation_name', 'N/D')}",
            f"Creado: {metadata.get('created_at', 'N/D')}",
            f"Seed: {metadata.get('seed', metadata.get('batch_seed', 'N/D'))}",
            f"Tiempo de ejecución: {metadata.get('execution_time_seconds', 'N/D')} s",
            "",
            "Resumen:",
        ]

        for key, value in summary.items():
            if key == "warnings":
                continue
            lines.append(f"- {key}: {value}")

        warnings = summary.get("warnings", [])

        if warnings:
            lines.append("")
            lines.append("Avisos:")
            for warning in warnings:
                lines.append(f"- {warning}")

        lines.append("")
        lines.append("En el siguiente paso añadiremos aquí:")
        lines.append("- curva SEIR")
        lines.append("- nuevas infecciones por slot")
        lines.append("- ranking de espacios con contagios")
        lines.append("- matriz de transmisión entre grupos")

        self.result_summary_text.setPlainText("\n".join(lines))

    def _read_json(self, path: Path) -> Optional[dict]:
        if not path.exists():
            return None

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return None