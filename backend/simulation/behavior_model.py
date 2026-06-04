from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Optional

from backend.simulation.agent import SimulationAgent
from backend.simulation.disease import DiseaseConfig
from backend.simulation.event import SimulationEvent
from backend.simulation.faculty_adapter import AcademicGroupContext


@dataclass
class DailyAgentStatus:
    """
    Estado diario de un agente dentro de la facultad.

    No representa el estado epidemiológico, sino el comportamiento diario:
    si ya ha entrado, si ya se ha ido, etc.
    """

    agent_id: str
    day_index: int

    has_entered_faculty: bool = False
    has_left_faculty: bool = False

    first_entry_slot: Optional[int] = None
    last_seen_slot: Optional[int] = None
    exit_slot: Optional[int] = None


class AgentBehaviorModel:
    """
    Decide el comportamiento de asistencia y permanencia de los agentes.

    Reglas principales:
    - Un agente puede no asistir a sus primeras clases y aparecer más tarde.
    - Una vez ha asistido a una clase, si deja de asistir a una clase posterior,
      se considera que ha salido de la facultad y no vuelve ese día.
    - Durante huecos entre clases puede quedarse o irse.
    - Si se queda en un hueco, el EventPlanner decidirá el espacio concreto.
    - Al final del día todos los agentes quedan fuera de la facultad.
    """

    def __init__(
        self,
        base_idle_stay_probability: float = 0.95,
        idle_stay_decay: float = 0.25,
    ) -> None:
        self.base_idle_stay_probability = self._clamp_probability(
            base_idle_stay_probability
        )
        self.idle_stay_decay = max(0.0, idle_stay_decay)

        self.current_day_index: Optional[int] = None
        self.daily_status_by_agent: dict[str, DailyAgentStatus] = {}

    # ========================================================
    # Gestión del día
    # ========================================================

    def start_day(
        self,
        day_index: int,
        agents: list[SimulationAgent],
    ) -> None:
        """
        Inicializa el comportamiento diario.

        Debe llamarse al empezar cada día de simulación.
        """

        self.current_day_index = day_index
        self.daily_status_by_agent = {
            agent.agent_id: DailyAgentStatus(
                agent_id=agent.agent_id,
                day_index=day_index,
            )
            for agent in agents
        }

    def end_day(self) -> None:
        """
        Cierra el día.

        Garantiza que todos los agentes quedan fuera de la facultad.
        """

        for status in self.daily_status_by_agent.values():
            if status.has_entered_faculty and not status.has_left_faculty:
                status.has_left_faculty = True
                status.exit_slot = status.last_seen_slot

        self.current_day_index = None
        self.daily_status_by_agent = {}

    def get_status(self, agent_id: str) -> DailyAgentStatus:
        if agent_id not in self.daily_status_by_agent:
            if self.current_day_index is None:
                raise RuntimeError(
                    "No hay un día activo. Llama a start_day antes de evaluar agentes."
                )

            self.daily_status_by_agent[agent_id] = DailyAgentStatus(
                agent_id=agent_id,
                day_index=self.current_day_index,
            )

        return self.daily_status_by_agent[agent_id]

    # ========================================================
    # Asistencia a eventos académicos
    # ========================================================

    def decide_academic_event_attendance(
        self,
        agent: SimulationAgent,
        event: SimulationEvent,
        group_context: Optional[AcademicGroupContext],
        disease: DiseaseConfig,
        rng: random.Random,
    ) -> bool:
        """
        Decide si un agente asiste a una clase/evento académico.

        Si el agente todavía no había entrado ese día, puede fallar este evento
        y aparecer en uno posterior.

        Si el agente ya había entrado y falla un evento académico posterior,
        se considera que ha abandonado la facultad y no vuelve ese día.
        """

        self._ensure_day_matches_event(event)

        status = self.get_status(agent.agent_id)

        if status.has_left_faculty:
            return False

        base_attendance_rate = None
        if group_context is not None:
            base_attendance_rate = group_context.attendance_rate

        attends = agent.should_attend_event(
            rng=rng,
            disease=disease,
            base_attendance_rate=base_attendance_rate,
        )

        if attends:
            self.mark_agent_inside(
                agent_id=agent.agent_id,
                entry_slot=event.start_slot,
                last_seen_slot=event.end_slot,
            )
            return True

        # Si todavía no había entrado, simplemente no aparece en este evento,
        # pero puede aparecer más tarde.
        if not status.has_entered_faculty:
            return False

        # Si ya había entrado, faltar a un evento posterior implica salida.
        self.mark_agent_left(
            agent_id=agent.agent_id,
            exit_slot=event.start_slot,
        )
        return False

    # ========================================================
    # Permanencia en horas muertas
    # ========================================================

    def decide_idle_stay(
        self,
        agent: SimulationAgent,
        idle_start_slot: int,
        idle_end_slot: int,
        rng: random.Random,
    ) -> bool:
        """
        Decide si un agente se queda en la facultad durante una hora muerta.

        Solo puede quedarse si ya estaba dentro y no se había ido.
        Si decide no quedarse, se considera que abandona la facultad y no vuelve
        ese día.
        """

        status = self.get_status(agent.agent_id)

        if status.has_left_faculty:
            return False

        if not status.has_entered_faculty:
            return False

        idle_duration_slots = max(1, idle_end_slot - idle_start_slot)
        stay_probability = self.calculate_idle_stay_probability(
            idle_duration_slots=idle_duration_slots
        )

        if rng.random() < stay_probability:
            status.last_seen_slot = idle_end_slot
            return True

        self.mark_agent_left(
            agent_id=agent.agent_id,
            exit_slot=idle_start_slot,
        )
        return False

    def calculate_idle_stay_probability(
        self,
        idle_duration_slots: int,
    ) -> float:
        """
        Calcula la probabilidad de quedarse durante un hueco.

        La probabilidad disminuye cuanto más largo es el hueco.

        Fórmula:
            P = base / (1 + decay * (slots - 1))

        Así, un hueco de 1 slot mantiene la probabilidad base, y huecos más
        largos la reducen progresivamente.
        """

        idle_duration_slots = max(1, idle_duration_slots)

        probability = self.base_idle_stay_probability / (
            1.0 + self.idle_stay_decay * (idle_duration_slots - 1)
        )

        return self._clamp_probability(probability)

    # ========================================================
    # Marcadores de estado diario
    # ========================================================

    def mark_agent_inside(
        self,
        agent_id: str,
        entry_slot: int,
        last_seen_slot: Optional[int] = None,
    ) -> None:
        status = self.get_status(agent_id)

        if status.has_left_faculty:
            return

        if not status.has_entered_faculty:
            status.has_entered_faculty = True
            status.first_entry_slot = entry_slot

        status.last_seen_slot = last_seen_slot if last_seen_slot is not None else entry_slot

    def mark_agent_left(
        self,
        agent_id: str,
        exit_slot: int,
    ) -> None:
        status = self.get_status(agent_id)

        status.has_left_faculty = True
        status.exit_slot = exit_slot
        status.last_seen_slot = exit_slot

    def is_agent_inside(self, agent_id: str) -> bool:
        status = self.get_status(agent_id)
        return status.has_entered_faculty and not status.has_left_faculty

    def has_agent_left(self, agent_id: str) -> bool:
        return self.get_status(agent_id).has_left_faculty

    # ========================================================
    # Helpers
    # ========================================================

    def _ensure_day_matches_event(self, event: SimulationEvent) -> None:
        if self.current_day_index is None:
            raise RuntimeError(
                "No hay un día activo. Llama a start_day antes de procesar eventos."
            )

        if event.day_index != self.current_day_index:
            raise ValueError(
                f"El evento pertenece al día {event.day_index}, "
                f"pero el día activo es {self.current_day_index}."
            )

    @staticmethod
    def _clamp_probability(value: float) -> float:
        return max(0.0, min(1.0, value))