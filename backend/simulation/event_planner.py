from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Optional

from backend.simulation.event import SimulationEvent, SpaceContext, ActivityType


@dataclass
class IdlePeriod:
    """
    Hueco entre dos eventos académicos de un mismo grupo.

    No representa todavía un evento concreto en un espacio. Primero indica que
    existe un hueco. Después, los agentes que decidan quedarse se asignarán
    aleatoriamente a pasillos o salas comunes.
    """

    idle_id: str

    day_index: int
    day_of_week: str

    start_slot: int
    end_slot: int
    duration_slots: int

    academic_group_id: str
    course_uuid: Optional[str] = None
    career_uuid: Optional[str] = None

    previous_event_id: Optional[str] = None
    next_event_id: Optional[str] = None

    candidate_space_uuids: list[str] = field(default_factory=list)


@dataclass
class PlannedIdleEvent:
    """
    Evento derivado ya asociado a un espacio y a una lista de agentes.

    El Engine podrá pasarlo directamente al ContactModel.
    """

    event: SimulationEvent
    agent_ids: list[str]


class EventPlanner:
    """
    Planifica eventos derivados a partir de eventos académicos.

    En la primera versión se usa para generar huecos entre clases. Estos huecos
    pueden ocupar pasillos o salas comunes.
    """

    def __init__(
        self,
        space_contexts: dict[str, SpaceContext],
    ) -> None:
        self.space_contexts = space_contexts

    # ========================================================
    # Huecos entre eventos
    # ========================================================

    def build_idle_periods(
        self,
        academic_events: list[SimulationEvent],
    ) -> list[IdlePeriod]:
        """
        Detecta huecos entre eventos académicos de un mismo grupo y día.
        """

        candidate_space_uuids = self.get_idle_candidate_space_uuids()

        if not candidate_space_uuids:
            return []

        grouped_events = self._group_events_by_day_and_group(academic_events)

        idle_periods: list[IdlePeriod] = []

        for (day_index, academic_group_id), events in grouped_events.items():
            ordered_events = sorted(
                events,
                key=lambda event: (event.start_slot, event.end_slot, event.event_id),
            )

            for previous_event, next_event in zip(ordered_events, ordered_events[1:]):
                if next_event.start_slot <= previous_event.end_slot:
                    continue

                start_slot = previous_event.end_slot
                end_slot = next_event.start_slot
                duration_slots = end_slot - start_slot

                idle_id = (
                    f"idle_{day_index}_"
                    f"{self._safe_id(academic_group_id)}_"
                    f"{start_slot}_{end_slot}"
                )

                idle_periods.append(
                    IdlePeriod(
                        idle_id=idle_id,
                        day_index=day_index,
                        day_of_week=previous_event.day_of_week,
                        start_slot=start_slot,
                        end_slot=end_slot,
                        duration_slots=duration_slots,
                        academic_group_id=academic_group_id,
                        course_uuid=previous_event.course_uuid,
                        career_uuid=previous_event.career_uuid,
                        previous_event_id=previous_event.event_id,
                        next_event_id=next_event.event_id,
                        candidate_space_uuids=list(candidate_space_uuids),
                    )
                )

        idle_periods.sort(
            key=lambda idle: (
                idle.day_index,
                idle.start_slot,
                idle.end_slot,
                idle.academic_group_id,
            )
        )

        return idle_periods

    def get_idle_candidate_space_uuids(self) -> list[str]:
        """
        Devuelve espacios válidos para horas muertas.

        Incluye:
        - pasillos;
        - salas comunes.

        No prioriza uno sobre otro. La elección concreta será aleatoria.
        """

        candidates: list[str] = []

        for space_uuid, context in self.space_contexts.items():
            if self._is_idle_candidate_space(context):
                candidates.append(space_uuid)

        return sorted(candidates)

    def choose_idle_space(
        self,
        idle_period: IdlePeriod,
        rng: random.Random,
    ) -> Optional[str]:
        """
        Escoge aleatoriamente un espacio para un agente que se queda en un hueco.
        """

        if not idle_period.candidate_space_uuids:
            return None

        return rng.choice(idle_period.candidate_space_uuids)

    # ========================================================
    # Creación de eventos derivados
    # ========================================================

    def create_idle_event(
        self,
        idle_period: IdlePeriod,
        space_uuid: str,
    ) -> SimulationEvent:
        """
        Crea un SimulationEvent derivado para un hueco en un espacio concreto.
        """

        context = self.space_contexts.get(space_uuid)
        activity_type = self._activity_type_for_space_context(context)

        event_id = (
            f"{idle_period.idle_id}_"
            f"{self._safe_id(space_uuid)}"
        )

        return SimulationEvent(
            event_id=event_id,
            source_schedule_block_uuid=idle_period.idle_id,
            day_index=idle_period.day_index,
            day_of_week=idle_period.day_of_week,
            start_slot=idle_period.start_slot,
            end_slot=idle_period.end_slot,
            duration_slots=idle_period.duration_slots,
            space_uuid=space_uuid,
            academic_group_id=idle_period.academic_group_id,
            course_uuid=idle_period.course_uuid,
            career_uuid=idle_period.career_uuid,
            activity_type=activity_type,
        )

    def build_planned_idle_events_from_assignments(
        self,
        idle_period: IdlePeriod,
        assignments_by_space: dict[str, list[str]],
    ) -> list[PlannedIdleEvent]:
        """
        Convierte asignaciones de agentes por espacio en eventos derivados.

        assignments_by_space:
            {
                "space_uuid_1": ["agent_1", "agent_2"],
                "space_uuid_2": ["agent_5"],
            }
        """

        planned_events: list[PlannedIdleEvent] = []

        for space_uuid, agent_ids in assignments_by_space.items():
            if not agent_ids:
                continue

            event = self.create_idle_event(
                idle_period=idle_period,
                space_uuid=space_uuid,
            )

            planned_events.append(
                PlannedIdleEvent(
                    event=event,
                    agent_ids=list(agent_ids),
                )
            )

        return planned_events

    # ========================================================
    # Helpers
    # ========================================================

    def _group_events_by_day_and_group(
        self,
        events: list[SimulationEvent],
    ) -> dict[tuple[int, str], list[SimulationEvent]]:
        grouped: dict[tuple[int, str], list[SimulationEvent]] = {}

        for event in events:
            key = (event.day_index, event.academic_group_id)
            grouped.setdefault(key, []).append(event)

        return grouped

    def _is_idle_candidate_space(
        self,
        context: SpaceContext,
    ) -> bool:
        if context.is_transit_type:
            return True

        if context.is_recreation_type:
            return True

        if context.space_type_uuid in {"corridor", "common_space"}:
            return True

        return False

    def _activity_type_for_space_context(
        self,
        context: Optional[SpaceContext],
    ) -> ActivityType:
        if context is None:
            return ActivityType.OTHER

        if context.is_transit_type or context.space_type_uuid == "corridor":
            return ActivityType.CORRIDOR

        if context.is_recreation_type or context.space_type_uuid == "common_space":
            return ActivityType.COMMON_SPACE

        return ActivityType.OTHER

    @staticmethod
    def _safe_id(raw_id: str) -> str:
        return (
            raw_id
            .replace(" ", "_")
            .replace("-", "_")
            .replace(":", "_")
            .replace("/", "_")
        )