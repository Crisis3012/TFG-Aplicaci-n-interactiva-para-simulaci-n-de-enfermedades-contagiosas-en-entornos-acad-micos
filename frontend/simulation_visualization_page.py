from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QSlider,
    QDoubleSpinBox,
    QMessageBox,
    QSplitter,
    QFrame,
    QScrollArea,
)

from frontend.simulation_graph_view import SimulationGraphView


class SimulationVisualizationPage(QWidget):
    """
    Página de visualización post-cálculo.

    Esta versión ya muestra:
    - controles de reproducción;
    - día/hora lógica;
    - grafo espacial de la facultad;
    - burbujas por espacio o grupo contraído;
    - panel textual de apoyo/debug.
    """

    def __init__(
        self,
        stacked_widget,
        simulation_controller=None,
        simulation_page_index: int = 2,
    ) -> None:
        super().__init__()

        self.stacked_widget = stacked_widget
        self.simulation_controller = simulation_controller
        self.simulation_page_index = simulation_page_index

        self.trace_path: Optional[Path] = None
        self.trace_data: dict[str, Any] = {}
        self.frames: list[dict[str, Any]] = []
        self.current_frame_index: int = 0

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance_playback)

        self._build_ui()

    # ========================================================
    # UI
    # ========================================================

    def _build_ui(self) -> None:
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 8, 10, 10)
        main_layout.setSpacing(6)

        # -------------------------
        # Barra superior compacta
        # -------------------------

        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        self.back_button = QPushButton("← Volver")
        self.back_button.setFixedHeight(32)
        self.back_button.setFixedWidth(110)
        self.back_button.clicked.connect(self.go_back)

        self.current_time_label = QLabel("Día/hora: N/D")
        self.current_time_label.setFixedHeight(32)
        self.current_time_label.setMinimumWidth(230)
        self.current_time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.current_time_label.setStyleSheet("""
            QLabel {
                background-color: #3b4048;
                color: white;
                border-radius: 8px;
                padding: 4px 10px;
                font-size: 13px;
                font-weight: 600;
            }
        """)

        self.trace_info_label = QLabel("No hay ninguna traza cargada.")
        self.trace_info_label.setFixedHeight(32)
        self.trace_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.trace_info_label.setStyleSheet("""
            QLabel {
                color: #cfd4dc;
                font-size: 11px;
            }
        """)

        self.previous_button = QPushButton("◀")
        self.previous_button.setFixedHeight(32)
        self.previous_button.setFixedWidth(42)
        self.previous_button.clicked.connect(self.previous_frame)

        self.play_pause_button = QPushButton("▶ Play")
        self.play_pause_button.setFixedHeight(32)
        self.play_pause_button.setFixedWidth(78)
        self.play_pause_button.clicked.connect(self.toggle_playback)

        self.next_button = QPushButton("▶")
        self.next_button.setFixedHeight(32)
        self.next_button.setFixedWidth(42)
        self.next_button.clicked.connect(self.next_frame)

        self.restart_button = QPushButton("Reiniciar")
        self.restart_button.setFixedHeight(32)
        self.restart_button.setFixedWidth(86)
        self.restart_button.clicked.connect(self.restart)

        self.speed_spin = QDoubleSpinBox()
        self.speed_spin.setRange(0.25, 20.0)
        self.speed_spin.setSingleStep(0.25)
        self.speed_spin.setDecimals(2)
        self.speed_spin.setValue(1.0)
        self.speed_spin.setSuffix(" fps")
        self.speed_spin.setFixedHeight(32)
        self.speed_spin.setFixedWidth(96)
        self.speed_spin.valueChanged.connect(self._update_timer_interval)

        self.frame_label = QLabel("Frame 0/0")
        self.frame_label.setFixedHeight(32)
        self.frame_label.setFixedWidth(100)
        self.frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.frame_label.setStyleSheet("font-size: 12px; color: #ddd;")

        top_bar.addWidget(self.back_button)
        top_bar.addWidget(self.current_time_label)
        top_bar.addWidget(self.trace_info_label, 1)
        top_bar.addWidget(self.previous_button)
        top_bar.addWidget(self.play_pause_button)
        top_bar.addWidget(self.next_button)
        top_bar.addWidget(self.restart_button)
        top_bar.addWidget(QLabel("Velocidad:"))
        top_bar.addWidget(self.speed_spin)
        top_bar.addWidget(self.frame_label)

        main_layout.addLayout(top_bar)

        # -------------------------
        # Slider temporal
        # -------------------------

        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setMinimum(0)
        self.timeline_slider.setMaximum(0)
        self.timeline_slider.valueChanged.connect(self._on_slider_changed)
        main_layout.addWidget(self.timeline_slider)

        # -------------------------
        # Zona principal: grafo + panel derecho
        # -------------------------

        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setChildrenCollapsible(False)

        self.graph_view = SimulationGraphView()

        self.details_panel = QFrame()
        self.details_panel.setMinimumWidth(330)
        self.details_panel.setStyleSheet("""
            QFrame {
                background-color: #3b4048;
                border-radius: 10px;
            }
        """)

        details_layout = QVBoxLayout(self.details_panel)
        details_layout.setContentsMargins(10, 10, 10, 10)
        details_layout.setSpacing(8)

        details_title = QLabel("Detalles del frame")
        details_title.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: bold;
                color: white;
            }
        """)
        details_layout.addWidget(details_title)

        self.details_scroll = QScrollArea()
        self.details_scroll.setWidgetResizable(True)
        self.details_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)

        self.details_content = QWidget()
        self.details_content.setStyleSheet("background-color: transparent;")
        self.details_content_layout = QVBoxLayout(self.details_content)
        self.details_content_layout.setContentsMargins(0, 0, 0, 0)
        self.details_content_layout.setSpacing(8)

        self.details_scroll.setWidget(self.details_content)
        details_layout.addWidget(self.details_scroll)

        self.content_splitter.addWidget(self.graph_view)
        self.content_splitter.addWidget(self.details_panel)
        self.content_splitter.setSizes([840, 340])
        self.content_splitter.setStretchFactor(0, 1)
        self.content_splitter.setStretchFactor(1, 0)

        main_layout.addWidget(self.content_splitter)

        self.setLayout(main_layout)
        self._set_controls_enabled(False)

    # ========================================================
    # Carga de traza
    # ========================================================

    def load_trace(self, trace_path: str | Path) -> None:
        path = Path(trace_path)

        if not path.exists():
            QMessageBox.critical(
                self,
                "Traza no encontrada",
                f"No existe el archivo de traza visual:\n{path}",
            )
            return

        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Error cargando traza",
                f"No se ha podido cargar la traza visual:\n{exc}",
            )
            return

        frames = data.get("frames", [])

        if not isinstance(frames, list) or not frames:
            QMessageBox.warning(
                self,
                "Traza vacía",
                "La traza visual no contiene frames reproducibles.",
            )
            return

        self.trace_path = path
        self.trace_data = data
        self.frames = frames
        self.current_frame_index = 0

        self.timeline_slider.blockSignals(True)
        self.timeline_slider.setMinimum(0)
        self.timeline_slider.setMaximum(max(0, len(self.frames) - 1))
        self.timeline_slider.setValue(0)
        self.timeline_slider.blockSignals(False)

        self._set_controls_enabled(True)
        self._stop_playback()
        self._update_timer_interval()
        self._update_trace_info()
        self._render_current_frame()

    def _update_trace_info(self) -> None:
        simulation_name = self.trace_data.get("simulation_name", "Simulación")
        seed = self.trace_data.get("seed", "N/D")
        slot_minutes = self.trace_data.get("slot_minutes", "N/D")
        duration_days = self.trace_data.get("duration_days", "N/D")

        self.trace_info_label.setText(
            f"{simulation_name} | Seed: {seed} | "
            f"Duración: {duration_days} días | Slot: {slot_minutes} min"
        )

    # ========================================================
    # Navegación
    # ========================================================

    def go_back(self) -> None:
        self._stop_playback()
        self.stacked_widget.setCurrentIndex(self.simulation_page_index)

    # ========================================================
    # Reproducción
    # ========================================================

    def toggle_playback(self) -> None:
        if not self.frames:
            return

        if self.timer.isActive():
            self._stop_playback()
        else:
            self._start_playback()

    def _start_playback(self) -> None:
        self._update_timer_interval()
        self.timer.start()
        self.play_pause_button.setText("⏸ Pausa")

    def _stop_playback(self) -> None:
        self.timer.stop()
        self.play_pause_button.setText("▶ Play")

    def _advance_playback(self) -> None:
        if not self.frames:
            self._stop_playback()
            return

        if self.current_frame_index >= len(self.frames) - 1:
            self._stop_playback()
            return

        self.set_frame_index(self.current_frame_index + 1)

    def _update_timer_interval(self) -> None:
        frames_per_second = max(0.25, float(self.speed_spin.value()))
        interval_ms = int(1000 / frames_per_second)
        self.timer.setInterval(interval_ms)

    def _get_graph_animation_duration_ms(self) -> int:
        frames_per_second = max(0.25, float(self.speed_spin.value()))
        frame_interval_ms = int(1000 / frames_per_second)

        # La animación ocupa casi todo el intervalo entre frames,
        # dejando un pequeño margen para que el usuario perciba el estado final.
        return max(500, int(frame_interval_ms * 0.90))

    def previous_frame(self) -> None:
        self._stop_playback()
        self.set_frame_index(self.current_frame_index - 1)

    def next_frame(self) -> None:
        self._stop_playback()
        self.set_frame_index(self.current_frame_index + 1)

    def restart(self) -> None:
        self._stop_playback()
        self.set_frame_index(0)

    def set_frame_index(self, index: int) -> None:
        if not self.frames:
            return

        index = max(0, min(index, len(self.frames) - 1))
        self.current_frame_index = index

        self.timeline_slider.blockSignals(True)
        self.timeline_slider.setValue(index)
        self.timeline_slider.blockSignals(False)

        self._render_current_frame()

    def _on_slider_changed(self, value: int) -> None:
        self._stop_playback()
        self.set_frame_index(value)

    # ========================================================
    # Render
    # ========================================================

    def _render_current_frame(self) -> None:
        if not self.frames:
            self.frame_label.setText("Frame 0/0")
            self.current_time_label.setText("Día/hora: N/D")
            self._clear_details_panel()
            return

        frame = self.frames[self.current_frame_index]
        time_label = self._format_frame_time_label(frame)

        self.frame_label.setText(
            f"Frame {self.current_frame_index + 1}/{len(self.frames)}"
        )

        self.current_time_label.setText(time_label)

        faculty = self._get_faculty()

        previous_frame = None

        if self.current_frame_index > 0:
            previous_frame = self.frames[self.current_frame_index - 1]

        if faculty is not None:
            self.graph_view.render_frame(
                faculty=faculty,
                frame=frame,
                trace_data=self.trace_data,
                previous_frame=previous_frame,
                animation_duration_ms=self._get_graph_animation_duration_ms(),
            )

        self._update_details_panel(frame, time_label)

    def _format_frame(
        self,
        frame: dict[str, Any],
        time_label: str,
    ) -> str:
        slot = frame.get("slot")
        day_index = frame.get("day_index")
        start_slot = frame.get("start_slot")
        end_slot = frame.get("end_slot")

        lines: list[str] = []

        lines.append("=== TIEMPO ACTUAL ===")
        lines.append(time_label)
        lines.append(f"Día lógico: {day_index}")
        lines.append(f"Slot: {slot}")
        lines.append(f"Intervalo lógico: {start_slot} → {end_slot}")
        lines.append("")

        events = frame.get("events", [])
        lines.append("=== EVENTOS VISUALES DE ESTA FRANJA ===")

        if events:
            for event in events:
                lines.append(self._format_event(event))
        else:
            lines.append("No hay eventos visuales en esta franja.")

        lines.append("")
        lines.append("=== ESPACIOS CON ACTIVIDAD ===")

        active_spaces = self._get_active_spaces(frame)

        if active_spaces:
            for summary in active_spaces:
                lines.append(self._format_space_summary(summary))
        else:
            lines.append("No hay agentes presentes en espacios visualizables en este frame.")

        lines.append("")
        lines.append("=== RESUMEN DE AGENTES ===")
        agent_states = frame.get("agent_states", {})
        lines.extend(self._format_global_agent_state_summary(agent_states))

        return "\n".join(lines)
    

    # ========================================================
    # Panel derecho vistoso
    # ========================================================

    def _clear_details_panel(self) -> None:
        while self.details_content_layout.count():
            item = self.details_content_layout.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.deleteLater()

    def _update_details_panel(
        self,
        frame: dict[str, Any],
        time_label: str,
    ) -> None:
        self._clear_details_panel()

        slot = frame.get("slot")
        start_slot = frame.get("start_slot")
        end_slot = frame.get("end_slot")

        self._add_detail_card(
            title="Tiempo",
            lines=[
                time_label,
                f"Slot: {slot}",
                f"Intervalo lógico: {start_slot} → {end_slot}",
            ],
        )

        agent_states = frame.get("agent_states", {})
        state_counts = self._get_global_agent_state_counts(agent_states)

        self._add_detail_card(
            title="Estado global",
            lines=[
                f"Susceptibles: {state_counts['susceptible']}",
                f"Expuestos: {state_counts['exposed']}",
                f"Infecciosos: {state_counts['infectious']}",
                f"Recuperados: {state_counts['recovered']}",
                f"Aislados: {state_counts['isolated']}",
            ],
        )

        events = frame.get("events", [])
        event_lines: list[str] = []

        if events:
            for event in events[:8]:
                event_lines.append(self._format_event_compact(event))

            if len(events) > 8:
                event_lines.append(f"... y {len(events) - 8} eventos más")
        else:
            event_lines.append("No hay eventos visuales en esta franja.")

        self._add_detail_card(
            title="Eventos",
            lines=event_lines,
            highlight=bool(events),
        )

        active_spaces = self._get_active_spaces(frame)
        space_lines: list[str] = []

        if active_spaces:
            for summary in active_spaces[:10]:
                name = summary.get("space_name") or summary.get("space_uuid")
                space_lines.append(
                    f"{name}: "
                    f"P={summary.get('present_agents', 0)} | "
                    f"S={summary.get('susceptible', 0)} "
                    f"E={summary.get('exposed', 0)} "
                    f"I={summary.get('infectious', 0)} "
                    f"R={summary.get('recovered', 0)}"
                )

            if len(active_spaces) > 10:
                space_lines.append(f"... y {len(active_spaces) - 10} espacios más")
        else:
            space_lines.append("No hay espacios activos en este frame.")

        self._add_detail_card(
            title="Espacios activos",
            lines=space_lines,
        )

        self.details_content_layout.addStretch()

    def _add_detail_card(
        self,
        title: str,
        lines: list[str],
        highlight: bool = False,
    ) -> None:
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {'#4a3b3b' if highlight else '#f4f6f7'};
                border-radius: 10px;
                border: 1px solid {'#e74c3c' if highlight else '#d0d7de'};
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            QLabel {{
                color: {'#ffffff' if highlight else '#1f2933'};
                font-size: 13px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(title_label)

        for line in lines:
            label = QLabel(str(line))
            label.setWordWrap(True)
            label.setStyleSheet(f"""
                QLabel {{
                    color: {'#f5f5f5' if highlight else '#1f2933'};
                    font-size: 12px;
                }}
            """)
            layout.addWidget(label)

        self.details_content_layout.addWidget(card)

    def _format_event_compact(
        self,
        event: dict[str, Any],
    ) -> str:
        event_type = event.get("event_type", "event")

        if event_type == "infection":
            space_uuid = event.get("space_uuid")
            source = event.get("source_agent_id")
            target = event.get("target_agent_id")
            offset = float(event.get("visual_offset", 0.0) or 0.0)

            return f"Infección en {space_uuid} · {source} → {target} · offset {offset:.2f}"

        if event_type == "initial_infection":
            target = event.get("target_agent_id")
            return f"Infección inicial: {target}"

        return str(event_type)

    def _get_global_agent_state_counts(
        self,
        agent_states: dict[str, Any],
    ) -> dict[str, int]:
        counts = {
            "susceptible": 0,
            "exposed": 0,
            "infectious": 0,
            "recovered": 0,
            "other": 0,
            "isolated": 0,
        }

        if not isinstance(agent_states, dict):
            return counts

        for state_data in agent_states.values():
            if not isinstance(state_data, dict):
                counts["other"] += 1
                continue

            state = str(state_data.get("state", "")).lower()

            if state in counts:
                counts[state] += 1
            else:
                counts["other"] += 1

            if state_data.get("is_isolated"):
                counts["isolated"] += 1

        return counts

    # ========================================================
    # Día y hora
    # ========================================================

    def _format_frame_time_label(
        self,
        frame: dict[str, Any],
    ) -> str:
        slot = int(frame.get("slot", 0) or 0)

        slot_minutes = int(self.trace_data.get("slot_minutes", 30) or 30)
        slots_per_day = int(self.trace_data.get("slots_per_day", 0) or 0)

        if slots_per_day <= 0:
            day_index = int(frame.get("day_index", 0) or 0)
            return f"Día {day_index + 1} | Slot {slot}"

        day_index = int(frame.get("day_index", slot // slots_per_day) or 0)
        slot_in_day = slot % slots_per_day

        opening_time = "08:00"
        day_name = None

        faculty = self._get_faculty()

        if faculty is not None:
            try:
                root = faculty.get_root()
                opening_time = root.opening_time

                if root.calendar_days:
                    raw_day = root.calendar_days[day_index % len(root.calendar_days)]
                    day_name = self._translate_day_name(raw_day)
            except Exception:
                pass

        start_minutes = self._time_to_minutes(opening_time) + (
            slot_in_day * slot_minutes
        )

        end_minutes = start_minutes + slot_minutes

        start_time = self._minutes_to_time(start_minutes)
        end_time = self._minutes_to_time(end_minutes)

        if day_name:
            return f"Día {day_index + 1} ({day_name}) · {start_time} - {end_time}"

        return f"Día {day_index + 1} · {start_time} - {end_time}"

    def _translate_day_name(
        self,
        day: str,
    ) -> str:
        translations = {
            "monday": "lunes",
            "tuesday": "martes",
            "wednesday": "miércoles",
            "thursday": "jueves",
            "friday": "viernes",
            "saturday": "sábado",
            "sunday": "domingo",
        }

        return translations.get(day.lower(), day)

    @staticmethod
    def _time_to_minutes(
        time_str: str,
    ) -> int:
        hours, minutes = time_str.split(":")
        return int(hours) * 60 + int(minutes)

    @staticmethod
    def _minutes_to_time(
        minutes: int,
    ) -> str:
        minutes = minutes % (24 * 60)
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"

    # ========================================================
    # Formato textual
    # ========================================================

    def _format_event(self, event: dict[str, Any]) -> str:
        event_type = event.get("event_type", "event")
        visual_offset = event.get("visual_offset", 0.0)
        space_uuid = event.get("space_uuid")
        source_agent_id = event.get("source_agent_id")
        target_agent_id = event.get("target_agent_id")

        if event_type == "infection":
            return (
                f"- Infección | offset={visual_offset:.2f} | "
                f"espacio={space_uuid} | "
                f"{source_agent_id} → {target_agent_id}"
            )

        if event_type == "initial_infection":
            return (
                f"- Infección inicial | "
                f"agente={target_agent_id}"
            )

        return (
            f"- {event_type} | offset={visual_offset:.2f} | "
            f"espacio={space_uuid} | "
            f"origen={source_agent_id} | destino={target_agent_id}"
        )

    def _get_active_spaces(
        self,
        frame: dict[str, Any],
    ) -> list[dict[str, Any]]:
        summaries = frame.get("space_summaries", {})

        if not isinstance(summaries, dict):
            return []

        active = [
            summary
            for summary in summaries.values()
            if int(summary.get("present_agents", 0) or 0) > 0
            or int(summary.get("new_infections", 0) or 0) > 0
        ]

        active.sort(
            key=lambda item: (
                -int(item.get("new_infections", 0) or 0),
                -int(item.get("present_agents", 0) or 0),
                item.get("space_name") or item.get("space_uuid") or "",
            )
        )

        return active

    def _format_space_summary(self, summary: dict[str, Any]) -> str:
        name = summary.get("space_name") or summary.get("space_uuid")
        space_type = (
            summary.get("space_type_name")
            or summary.get("space_type_uuid")
            or "N/D"
        )

        return (
            f"- {name} ({space_type}) | "
            f"presentes={summary.get('present_agents', 0)} | "
            f"S={summary.get('susceptible', 0)} "
            f"E={summary.get('exposed', 0)} "
            f"I={summary.get('infectious', 0)} "
            f"R={summary.get('recovered', 0)} | "
            f"aislados={summary.get('isolated', 0)} | "
            f"nuevas infecciones={summary.get('new_infections', 0)}"
        )

    def _format_global_agent_state_summary(
        self,
        agent_states: dict[str, Any],
    ) -> list[str]:
        counts = {
            "susceptible": 0,
            "exposed": 0,
            "infectious": 0,
            "recovered": 0,
            "other": 0,
            "isolated": 0,
        }

        for state_data in agent_states.values():
            state = str(state_data.get("state", "")).lower()

            if state in counts:
                counts[state] += 1
            else:
                counts["other"] += 1

            if state_data.get("is_isolated"):
                counts["isolated"] += 1

        return [
            f"Susceptibles: {counts['susceptible']}",
            f"Expuestos: {counts['exposed']}",
            f"Infecciosos: {counts['infectious']}",
            f"Recuperados: {counts['recovered']}",
            f"Aislados: {counts['isolated']}",
            f"Otros/desconocidos: {counts['other']}",
        ]

    # ========================================================
    # Helpers
    # ========================================================

    def _get_faculty(self):
        if self.simulation_controller is None:
            return None

        try:
            return self.simulation_controller.faculty
        except Exception:
            return None

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.previous_button.setEnabled(enabled)
        self.play_pause_button.setEnabled(enabled)
        self.next_button.setEnabled(enabled)
        self.restart_button.setEnabled(enabled)
        self.timeline_slider.setEnabled(enabled)
        self.speed_spin.setEnabled(enabled)