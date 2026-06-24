from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QSpinBox,
    QCheckBox,
    QGroupBox,
    QProgressBar,
    QTextEdit,
    QMessageBox,
    QApplication,
)

from backend.simulation.config import (
    SimulationConfig,
    InitialInfectionConfig,
    BatchConfig,
)
from backend.simulation.disease import DiseaseState


class SimulationPage(QWidget):
    def __init__(
        self,
        stacked_widget,
        simulation_controller,
        visualization_page=None,
        visualization_page_index: Optional[int] = None,
    ):
        super().__init__()

        self.stacked_widget = stacked_widget
        self.simulation_controller = simulation_controller
        self.visualization_page = visualization_page
        self.visualization_page_index = visualization_page_index

        self.disease_presets = {}

        self._build_ui()
        self.load_page()

    # ========================================================
    # Construcción de UI
    # ========================================================

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)

        # -------------------------
        # Cabecera
        # -------------------------

        header_layout = QHBoxLayout()

        self.back_button = QPushButton("← Volver")
        self.back_button.setFixedWidth(120)
        self.back_button.clicked.connect(self.go_back)

        title = QLabel("Simulación")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")

        header_layout.addWidget(self.back_button)
        header_layout.addStretch()
        header_layout.addWidget(title)
        header_layout.addStretch()

        placeholder = QLabel("")
        placeholder.setFixedWidth(120)
        header_layout.addWidget(placeholder)

        main_layout.addLayout(header_layout)

        # -------------------------
        # Facultad activa
        # -------------------------

        self.active_faculty_label = QLabel()
        self.active_faculty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.active_faculty_label.setStyleSheet("font-size: 14px; color: #555;")
        main_layout.addWidget(self.active_faculty_label)

        # -------------------------
        # Configuración
        # -------------------------

        config_group = QGroupBox("Configuración de la simulación")
        config_layout = QGridLayout()
        config_layout.setHorizontalSpacing(16)
        config_layout.setVerticalSpacing(12)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nombre de la simulación")

        self.disease_combo = QComboBox()

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 365)
        self.duration_spin.setValue(5)
        self.duration_spin.setSuffix(" días")

        self.initial_infections_spin = QSpinBox()
        self.initial_infections_spin.setRange(0, 100000)
        self.initial_infections_spin.setValue(1)

        self.initial_state_combo = QComboBox()
        self.initial_state_combo.addItem("Expuestos", DiseaseState.EXPOSED)
        self.initial_state_combo.addItem("Infecciosos", DiseaseState.INFECTIOUS)

        self.seed_input = QLineEdit()
        self.seed_input.setPlaceholderText("Opcional, ej. 1234")

        config_layout.addWidget(QLabel("Nombre:"), 0, 0)
        config_layout.addWidget(self.name_input, 0, 1)

        config_layout.addWidget(QLabel("Enfermedad:"), 1, 0)
        config_layout.addWidget(self.disease_combo, 1, 1)

        config_layout.addWidget(QLabel("Duración:"), 2, 0)
        config_layout.addWidget(self.duration_spin, 2, 1)

        config_layout.addWidget(QLabel("Infectados iniciales:"), 3, 0)
        config_layout.addWidget(self.initial_infections_spin, 3, 1)

        config_layout.addWidget(QLabel("Estado inicial:"), 4, 0)
        config_layout.addWidget(self.initial_state_combo, 4, 1)

        config_layout.addWidget(QLabel("Semilla:"), 5, 0)
        config_layout.addWidget(self.seed_input, 5, 1)

        config_group.setLayout(config_layout)
        main_layout.addWidget(config_group)

        # -------------------------
        # Visualización
        # -------------------------

        visualization_group = QGroupBox("Visualización")
        visualization_layout = QVBoxLayout()
        visualization_layout.setSpacing(8)

        self.generate_visual_trace_checkbox = QCheckBox(
            "Generar visualización animada al finalizar"
        )
        self.generate_visual_trace_checkbox.setChecked(False)

        visualization_help_label = QLabel(
            "Disponible solo para simulaciones individuales. "
            "La simulación se calculará primero y después se guardará una traza visual "
            "para reproducirla como animación."
        )
        visualization_help_label.setWordWrap(True)
        visualization_help_label.setStyleSheet("font-size: 12px; color: #666;")

        visualization_layout.addWidget(self.generate_visual_trace_checkbox)
        visualization_layout.addWidget(visualization_help_label)

        visualization_group.setLayout(visualization_layout)
        main_layout.addWidget(visualization_group)

        # -------------------------
        # Batch
        # -------------------------

        batch_group = QGroupBox("Batch")
        batch_layout = QGridLayout()
        batch_layout.setHorizontalSpacing(16)
        batch_layout.setVerticalSpacing(12)

        self.batch_enabled_checkbox = QCheckBox("Ejecutar varias simulaciones")
        self.batch_enabled_checkbox.stateChanged.connect(self._update_batch_controls)

        self.batch_runs_spin = QSpinBox()
        self.batch_runs_spin.setRange(1, 10000)
        self.batch_runs_spin.setValue(5)

        self.batch_seed_input = QLineEdit()
        self.batch_seed_input.setPlaceholderText("Opcional, ej. 3012")

        # self.save_individual_runs_checkbox = QCheckBox("Guardar ejecuciones individuales")
        # self.save_individual_runs_checkbox.setChecked(True)

        batch_layout.addWidget(self.batch_enabled_checkbox, 0, 0, 1, 2)

        batch_layout.addWidget(QLabel("Número de ejecuciones:"), 1, 0)
        batch_layout.addWidget(self.batch_runs_spin, 1, 1)

        batch_layout.addWidget(QLabel("Semilla del batch:"), 2, 0)
        batch_layout.addWidget(self.batch_seed_input, 2, 1)

        # batch_layout.addWidget(self.save_individual_runs_checkbox, 3, 0, 1, 2)

        batch_group.setLayout(batch_layout)
        main_layout.addWidget(batch_group)

        # -------------------------
        # Botones ejecución
        # -------------------------

        actions_layout = QHBoxLayout()

        self.run_button = QPushButton("Ejecutar simulación")
        self.run_button.setFixedHeight(42)
        self.run_button.clicked.connect(self.run_simulation)

        self.clear_output_button = QPushButton("Limpiar salida")
        self.clear_output_button.setFixedHeight(42)
        self.clear_output_button.clicked.connect(self.clear_output)

        actions_layout.addStretch()
        actions_layout.addWidget(self.run_button)
        actions_layout.addWidget(self.clear_output_button)
        actions_layout.addStretch()

        main_layout.addLayout(actions_layout)

        # -------------------------
        # Progreso y salida
        # -------------------------

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setMinimumHeight(180)

        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.output_text)

        self.setLayout(main_layout)

        self._update_batch_controls()

    # ========================================================
    # Carga/refresco de página
    # ========================================================

    def load_page(self) -> None:
        self._refresh_active_faculty_label()
        self._load_disease_presets()

        default_config = self.simulation_controller.get_default_simulation_config()

        self.name_input.setText(default_config.name)
        self.duration_spin.setValue(default_config.duration_days)
        self.initial_infections_spin.setValue(default_config.initial_infections.count)

        if default_config.seed is not None:
            self.seed_input.setText(str(default_config.seed))
        else:
            self.seed_input.clear()

        self.batch_enabled_checkbox.setChecked(False)
        self.batch_runs_spin.setValue(5)
        self.batch_seed_input.clear()
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.generate_visual_trace_checkbox.setChecked(False)

    def _refresh_active_faculty_label(self) -> None:
        active_name = self.simulation_controller.active_faculty_name

        if active_name:
            self.active_faculty_label.setText(f"Facultad activa: {active_name}")
        else:
            self.active_faculty_label.setText("No hay ninguna facultad activa.")

    def _load_disease_presets(self) -> None:
        current_text = self.disease_combo.currentText()

        self.disease_presets = self.simulation_controller.get_disease_presets()

        self.disease_combo.clear()

        for preset_name in self.disease_presets.keys():
            self.disease_combo.addItem(preset_name)

        if current_text:
            index = self.disease_combo.findText(current_text)
            if index >= 0:
                self.disease_combo.setCurrentIndex(index)

    # ========================================================
    # Navegación
    # ========================================================

    def go_back(self) -> None:
        self.stacked_widget.setCurrentIndex(0)

    def _open_visualization_page(self, visual_trace_path: Path) -> None:
        """
        Abre la página de visualización con la traza generada.

        De momento carga una vista textual/reproductor básico.
        Más adelante esta página contendrá el grafo animado.
        """

        if self.visualization_page is None or self.visualization_page_index is None:
            self._append_output(
                "Aviso: la página de visualización no está conectada todavía."
            )
            return

        if hasattr(self.visualization_page, "load_trace"):
            self.visualization_page.load_trace(visual_trace_path)

        self.stacked_widget.setCurrentIndex(self.visualization_page_index)

    # ========================================================
    # Ejecución
    # ========================================================

    def run_simulation(self) -> None:
        try:
            config = self._build_config_from_form()
        except ValueError as exc:
            QMessageBox.warning(
                self,
                "Configuración incorrecta",
                str(exc),
            )
            return

        self.run_button.setEnabled(False)
        self.progress_bar.setValue(0)

        if config.batch.enabled and config.batch.runs > 1:
            self.progress_bar.setVisible(True)
            self.progress_bar.setMaximum(config.batch.runs)
        else:
            self.progress_bar.setVisible(False)

        self._append_output("Ejecutando simulación...")

        generate_visual_trace = (
            self.generate_visual_trace_checkbox.isChecked()
            and not config.batch.enabled
        )

        response = self.simulation_controller.run_simulation(
            config=config,
            progress_callback=self._on_batch_progress,
            save_results=True,
            save_individual_runs=True,
            generate_visual_trace=generate_visual_trace,
        )

        self.run_button.setEnabled(True)

        if not response.success:
            self._append_output("")
            self._append_output("ERROR:")
            self._append_output(response.message)

            QMessageBox.critical(
                self,
                "Error de simulación",
                response.message,
            )
            return

        self._append_output("")
        self._append_output(response.message)

        if response.saved_path is not None:
            self._append_output(f"Resultados guardados en: {response.saved_path}")

        if generate_visual_trace and response.saved_path is not None:
            visual_trace_path = response.saved_path / "visual_trace.json"

            if visual_trace_path.exists():
                self._append_output(f"Traza visual guardada en: {visual_trace_path}")
                self._open_visualization_page(visual_trace_path)
            else:
                self._append_output(
                    "Aviso: se pidió traza visual, pero no se ha encontrado visual_trace.json."
                )

        if response.is_batch:
            self._show_batch_result(response.result)
        else:
            self._show_single_result(response.result)

    def _on_batch_progress(self, current: int, total: int) -> None:
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self._append_output(f"Batch: {current}/{total}")
        QApplication.processEvents()

    # ========================================================
    # Crear configuración desde la UI
    # ========================================================

    def _build_config_from_form(self) -> SimulationConfig:
        simulation_name = self.name_input.text().strip()

        if not simulation_name:
            raise ValueError("El nombre de la simulación no puede estar vacío.")

        disease_name = self.disease_combo.currentText()

        if disease_name not in self.disease_presets:
            raise ValueError("No se ha seleccionado una enfermedad válida.")

        disease = self.disease_presets[disease_name]

        seed = self._parse_optional_int(
            value=self.seed_input.text(),
            field_name="Semilla",
        )

        batch_seed = self._parse_optional_int(
            value=self.batch_seed_input.text(),
            field_name="Semilla del batch",
        )

        initial_state = self.initial_state_combo.currentData()

        return SimulationConfig(
            name=simulation_name,
            duration_days=self.duration_spin.value(),
            seed=seed,
            disease=disease,
            initial_infections=InitialInfectionConfig(
                count=self.initial_infections_spin.value(),
                initial_state=initial_state,
            ),
            batch=BatchConfig(
                enabled=self.batch_enabled_checkbox.isChecked(),
                runs=self.batch_runs_spin.value(),
                batch_seed=batch_seed,
            ),
        )

    def _parse_optional_int(
        self,
        value: str,
        field_name: str,
    ) -> Optional[int]:
        value = value.strip()

        if not value:
            return None

        try:
            parsed = int(value)
        except ValueError:
            raise ValueError(f"{field_name} debe ser un número entero.")

        if parsed < 0:
            raise ValueError(f"{field_name} no puede ser negativa.")

        return parsed

    # ========================================================
    # Mostrar resultados
    # ========================================================

    def _show_single_result(self, result) -> None:
        if result is None:
            return

        summary = result.final_summary

        self._append_output("")
        self._append_output("Resumen de simulación individual:")
        self._append_output(f"- Agentes totales: {summary.get('total_agents')}")
        self._append_output(f"- Infectados iniciales: {summary.get('initial_infections')}")
        self._append_output(f"- Contagios internos: {summary.get('internal_infections')}")
        self._append_output(f"- Total infectados alguna vez: {summary.get('total_ever_infected')}")
        self._append_output(f"- Pico de infecciosos: {summary.get('peak_infectious')}")
        self._append_output(f"- Susceptibles finales: {summary.get('final_susceptible')}")
        self._append_output(f"- Expuestos finales: {summary.get('final_exposed')}")
        self._append_output(f"- Infecciosos finales: {summary.get('final_infectious')}")
        self._append_output(f"- Recuperados finales: {summary.get('final_recovered')}")

        if result.execution_time_seconds is not None:
            self._append_output(
                f"- Tiempo de ejecución: {result.execution_time_seconds:.4f} s"
            )

        warnings = summary.get("warnings", [])

        if warnings:
            self._append_output("")
            self._append_output("Avisos:")
            for warning in warnings:
                self._append_output(f"- {warning}")

    def _show_batch_result(self, result) -> None:
        if result is None:
            return

        summary = result.aggregated_summary

        self._append_output("")
        self._append_output("Resumen de batch:")
        self._append_output(f"- Ejecuciones: {summary.get('number_of_runs')}")
        self._append_output(f"- Semilla de batch: {summary.get('batch_seed')}")
        self._append_output(f"- Media de infectados totales: {summary.get('total_infections_mean')}")
        self._append_output(f"- Mínimo de infectados totales: {summary.get('total_infections_min')}")
        self._append_output(f"- Máximo de infectados totales: {summary.get('total_infections_max')}")
        self._append_output(f"- Media de pico infeccioso: {summary.get('peak_infectious_mean')}")

        batch_time = summary.get("batch_execution_time_seconds")

        if batch_time is not None:
            self._append_output(f"- Tiempo total del batch: {batch_time:.4f} s")

        run_time_mean = summary.get("run_execution_time_mean")

        if run_time_mean is not None:
            self._append_output(f"- Tiempo medio por ejecución: {run_time_mean:.4f} s")

    def clear_output(self) -> None:
        self.output_text.clear()

    def _append_output(self, text: str) -> None:
        self.output_text.append(text)

    # ========================================================
    # Batch controls
    # ========================================================

    def _update_batch_controls(self) -> None:
        batch_enabled = self.batch_enabled_checkbox.isChecked()

        self.batch_runs_spin.setEnabled(batch_enabled)
        self.batch_seed_input.setEnabled(batch_enabled)
        #self.save_individual_runs_checkbox.setEnabled(batch_enabled)

        if hasattr(self, "generate_visual_trace_checkbox"):
            self.generate_visual_trace_checkbox.setEnabled(not batch_enabled)

            if batch_enabled:
                self.generate_visual_trace_checkbox.setChecked(False)

        if batch_enabled:
            self.run_button.setText("Ejecutar batch")
        else:
            self.run_button.setText("Ejecutar simulación")