from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from typing import Optional
import random
import uuid
from datetime import datetime
import time

from backend.faculty import Faculty
from backend.simulation.agent import SimulationAgent
from backend.simulation.behavior_model import AgentBehaviorModel
from backend.simulation.config import (
    SimulationConfig,
    InitialInfectionMode,
)
from backend.simulation.contact import InfectionEvent
from backend.simulation.contact_model import ContactModel
from backend.simulation.disease import DiseaseState
from backend.simulation.event import SimulationEvent, ActivityType
from backend.simulation.event_planner import EventPlanner, IdlePeriod
from backend.simulation.faculty_adapter import (
    FacultySimulationAdapter,
    FacultySimulationData,
    AcademicGroupContext,
)
from backend.simulation.results import (
    SimulationResult,
    TimeSeriesRow,
    SpaceSummaryRow,
    GroupSummaryRow,
    OccupancyRow,
    SpaceOccupancyRow,
)
from backend.simulation.transmission_model import TransmissionModel
from backend.simulation.visual_trace import (
    SimulationVisualTrace,
    VisualAgentLocation,
    VisualAgentState,
    VisualEvent,
    VisualFrame,
    VisualSpaceSummary,
)


@dataclass
class PlannedSimulationEvent:
    """
    Evento listo para ser procesado por el motor.

    Puede venir de:
    - un evento académico real del horario;
    - un evento derivado de hora muerta.
    """

    event: SimulationEvent
    agent_ids: list[str]


class SimulationEngine:
    """
    Motor principal de simulación epidemiológica.

    Responsabilidades:
    - adaptar Faculty a datos de simulación;
    - generar infectados iniciales;
    - recorrer días, eventos académicos y horas muertas;
    - decidir asistencia y permanencia de agentes;
    - generar contactos efectivos;
    - calcular contagios;
    - producir un SimulationResult.
    """

    def __init__(
        self,
        faculty: Faculty,
        config: SimulationConfig,
        generate_visual_trace: bool = False,
    ) -> None:
        self.faculty = faculty
        self.config = config

        self.run_id = str(uuid.uuid4())
        self.seed = self._resolve_seed(config.seed)
        self.rng = random.Random(self.seed)

        self.generate_visual_trace = generate_visual_trace

        # RNG separado para decisiones puramente visuales.
        # Importante: no debe alterar el RNG epidemiológico de la simulación.
        self.visual_rng = random.Random(f"{self.seed}:visual")

        self.adapter = FacultySimulationAdapter(faculty)
        self.behavior_model = AgentBehaviorModel()
        self.contact_model = ContactModel()
        self.transmission_model = TransmissionModel()

        self.data: Optional[FacultySimulationData] = None

        self.agents_by_id: dict[str, SimulationAgent] = {}
        self.agents_by_group: dict[str, list[SimulationAgent]] = defaultdict(list)

        self.infection_events: list[InfectionEvent] = []
        self.time_series: list[TimeSeriesRow] = []

        self.occupancy_by_slot: list[OccupancyRow] = []
        self.space_occupancy_by_slot: list[SpaceOccupancyRow] = []

        self.group_peak_infectious: dict[str, int] = defaultdict(int)

        self.initial_infected_agent_ids: list[str] = []
        self.warnings: list[str] = []

        self.visual_locations: list[VisualAgentLocation] = []
        self.visual_events: list[VisualEvent] = []
        self.visual_frames: list[VisualFrame] = []

    # ========================================================
    # API PRINCIPAL
    # ========================================================

    def run(self) -> SimulationResult:
        start_perf = time.perf_counter()
        started_at = datetime.now().isoformat(timespec="seconds")
        self.config.validate()

        self.data = self.adapter.build_simulation_data(
            duration_days=self.config.duration_days
        )

        self.warnings.extend(self.data.warnings)

        self._index_agents(self.data.agents)
        self._apply_initial_infections(current_slot=0)

        self._record_time_series(
            slot=0,
            new_infections=0,
        )

        self._record_occupancy(
            slot=start_slot,
            day_index=day_index,
            planned_events=planned_events,
            infection_events=slot_infection_events,
        )

        if self.generate_visual_trace:
            initial_visual_events = self._build_initial_visual_events(
                current_slot=0,
            )
            self.visual_events.extend(initial_visual_events)

            self._record_visual_frame(
                slot=0,
                planned_events=[],
                visual_events=initial_visual_events,
            )

        event_planner = EventPlanner(self.data.space_contexts)
        idle_periods = event_planner.build_idle_periods(self.data.events)

        academic_events_by_day_and_start = self._group_academic_events_by_day_and_start(
            self.data.events
        )

        idle_periods_by_day_and_start = self._group_idle_periods_by_day_and_start(
            idle_periods
        )

        for day_index in range(self.config.duration_days):
            self.behavior_model.start_day(
                day_index=day_index,
                agents=self.data.agents,
            )

            start_slots = self._get_day_start_slots(
                day_index=day_index,
                academic_events_by_day_and_start=academic_events_by_day_and_start,
                idle_periods_by_day_and_start=idle_periods_by_day_and_start,
            )

            for start_slot in start_slots:
                self._update_agent_states(current_slot=start_slot)

                planned_events: list[PlannedSimulationEvent] = []

                academic_events = academic_events_by_day_and_start.get(
                    (day_index, start_slot),
                    [],
                )

                for event in academic_events:
                    planned_event = self._plan_academic_event(event)
                    if planned_event.agent_ids:
                        planned_events.append(planned_event)

                idle_periods_at_slot = idle_periods_by_day_and_start.get(
                    (day_index, start_slot),
                    [],
                )

                for idle_period in idle_periods_at_slot:
                    planned_idle_events = self._plan_idle_period(
                        idle_period=idle_period,
                        event_planner=event_planner,
                    )
                    planned_events.extend(planned_idle_events)

                planned_events = self._merge_planned_events_if_needed(planned_events)

                new_infections = 0
                slot_infection_events: list[InfectionEvent] = []

                for planned_event in planned_events:
                    event_infections = self._process_planned_event(planned_event)
                    self.infection_events.extend(event_infections)
                    slot_infection_events.extend(event_infections)
                    new_infections += len(event_infections)

                self._record_time_series(
                    slot=start_slot,
                    new_infections=new_infections,
                )

                if self.generate_visual_trace:
                    slot_visual_events = self._build_visual_events_from_infections(
                        infection_events=slot_infection_events,
                    )

                    self.visual_events.extend(slot_visual_events)

                    self._record_visual_locations(
                        planned_events=planned_events,
                    )

                    self._record_visual_frame(
                        slot=start_slot,
                        planned_events=planned_events,
                        visual_events=slot_visual_events,
                    )

            day_end_slot = (day_index + 1) * self.data.slots_per_day
            self._update_agent_states(current_slot=day_end_slot)
            self._record_time_series(
                slot=day_end_slot,
                new_infections=0,
            )

            if self.generate_visual_trace:
                self._record_visual_frame(
                    slot=day_end_slot,
                    planned_events=[],
                    visual_events=[],
                )

            self.behavior_model.end_day()

        final_slot = self.config.duration_days * self.data.slots_per_day
        self._update_agent_states(current_slot=final_slot)

        finished_at = datetime.now().isoformat(timespec="seconds")
        execution_time_seconds = time.perf_counter() - start_perf

        return self._build_result(
            started_at=started_at,
            finished_at=finished_at,
            execution_time_seconds=execution_time_seconds,
        )

    # ========================================================
    # PLANIFICACIÓN DE EVENTOS
    # ========================================================

    def _plan_academic_event(
        self,
        event: SimulationEvent,
    ) -> PlannedSimulationEvent:
        if self.data is None:
            raise RuntimeError("No hay datos de simulación cargados.")

        group_context = self.data.group_contexts.get(event.academic_group_id)
        group_agents = self.agents_by_group.get(event.academic_group_id, [])

        attending_agent_ids: list[str] = []

        for agent in group_agents:
            attends = self.behavior_model.decide_academic_event_attendance(
                agent=agent,
                event=event,
                group_context=group_context,
                disease=self.config.disease,
                rng=self.rng,
            )

            if attends:
                attending_agent_ids.append(agent.agent_id)

        return PlannedSimulationEvent(
            event=event,
            agent_ids=attending_agent_ids,
        )

    def _plan_idle_period(
        self,
        idle_period: IdlePeriod,
        event_planner: EventPlanner,
    ) -> list[PlannedSimulationEvent]:
        group_agents = self.agents_by_group.get(idle_period.academic_group_id, [])

        assignments_by_space: dict[str, list[str]] = defaultdict(list)

        for agent in group_agents:
            stays = self.behavior_model.decide_idle_stay(
                agent=agent,
                idle_start_slot=idle_period.start_slot,
                idle_end_slot=idle_period.end_slot,
                rng=self.rng,
            )

            if not stays:
                continue

            chosen_space_uuid = event_planner.choose_idle_space(
                idle_period=idle_period,
                rng=self.rng,
            )

            if chosen_space_uuid is None:
                continue

            assignments_by_space[chosen_space_uuid].append(agent.agent_id)

        planned_idle_events = event_planner.build_planned_idle_events_from_assignments(
            idle_period=idle_period,
            assignments_by_space=dict(assignments_by_space),
        )

        return [
            PlannedSimulationEvent(
                event=planned.event,
                agent_ids=planned.agent_ids,
            )
            for planned in planned_idle_events
        ]

    def _merge_planned_events_if_needed(
        self,
        planned_events: list[PlannedSimulationEvent],
    ) -> list[PlannedSimulationEvent]:
        """
        Mezcla eventos simultáneos en el mismo espacio cuando son eventos
        de interacción general, como pasillos o salas comunes.

        No mezclamos clases o laboratorios académicos para conservar su
        identidad como eventos separados del horario.
        """

        if not planned_events:
            return []

        merged: dict[tuple, PlannedSimulationEvent] = {}
        output: list[PlannedSimulationEvent] = []

        mergeable_types = {
            ActivityType.CORRIDOR,
            ActivityType.COMMON_SPACE,
            ActivityType.CAFETERIA,
            ActivityType.LIBRARY,
        }

        for planned in planned_events:
            event = planned.event

            if event.activity_type not in mergeable_types:
                output.append(planned)
                continue

            key = (
                event.space_uuid,
                event.start_slot,
                event.end_slot,
                event.activity_type.value,
            )

            if key not in merged:
                merged[key] = planned
                continue

            existing = merged[key]
            existing_ids = set(existing.agent_ids)
            existing_ids.update(planned.agent_ids)
            existing.agent_ids = list(existing_ids)

        output.extend(merged.values())

        return output

    # ========================================================
    # PROCESAMIENTO DE EVENTOS
    # ========================================================

    def _process_planned_event(
        self,
        planned_event: PlannedSimulationEvent,
    ) -> list[InfectionEvent]:
        if self.data is None:
            raise RuntimeError("No hay datos de simulación cargados.")

        if len(planned_event.agent_ids) < 2:
            return []

        event = planned_event.event
        space_context = None

        if event.space_uuid is not None:
            space_context = self.data.space_contexts.get(event.space_uuid)

        agents_in_event = [
            self.agents_by_id[agent_id]
            for agent_id in planned_event.agent_ids
            if agent_id in self.agents_by_id
        ]

        if len(agents_in_event) < 2:
            return []

        contacts = self.contact_model.generate_contacts(
            event=event,
            agents_in_event=agents_in_event,
            space_context=space_context,
            rng=self.rng,
        )

        infection_events = self.transmission_model.process_contacts(
            contacts=contacts,
            agents_by_id=self.agents_by_id,
            event=event,
            space_context=space_context,
            disease=self.config.disease,
            rng=self.rng,
            interventions=self.config.interventions,
        )

        return [
            self._enrich_infection_event(infection)
            for infection in infection_events
        ]
    
    def _enrich_infection_event(
        self,
        infection: InfectionEvent,
    ) -> InfectionEvent:
        if self.data is None:
            return infection

        source_agent = self.agents_by_id.get(infection.source_agent_id)
        infected_agent = self.agents_by_id.get(infection.infected_agent_id)

        source_context = None
        infected_context = None

        if source_agent is not None:
            source_context = self.data.group_contexts.get(source_agent.academic_group_id)

        if infected_agent is not None:
            infected_context = self.data.group_contexts.get(infected_agent.academic_group_id)

        space_context = None

        if infection.space_uuid is not None:
            space_context = self.data.space_contexts.get(infection.space_uuid)

        if source_context is not None:
            infection.source_group_uuid = source_context.academic_group_id
            infection.source_group_name = source_context.group_name
            infection.source_course_uuid = source_context.course_uuid
            infection.source_course_name = source_context.course_name
            infection.source_career_uuid = source_context.career_uuid
            infection.source_career_name = source_context.career_name

        if infected_context is not None:
            infection.infected_group_uuid = infected_context.academic_group_id
            infection.infected_group_name = infected_context.group_name
            infection.infected_course_uuid = infected_context.course_uuid
            infection.infected_course_name = infected_context.course_name
            infection.infected_career_uuid = infected_context.career_uuid
            infection.infected_career_name = infected_context.career_name

        if space_context is not None:
            infection.space_name = space_context.space_name
            infection.space_type_uuid = space_context.space_type_uuid
            infection.space_type_name = space_context.space_type_name

        return infection

    # ========================================================
    # INFECTADOS INICIALES
    # ========================================================

    def _apply_initial_infections(
        self,
        current_slot: int,
    ) -> None:
        candidates = self._get_initial_infection_candidates()

        if not candidates:
            self.warnings.append(
                "No se han podido aplicar infecciones iniciales: no hay candidatos."
            )
            return

        config = self.config.initial_infections

        if config.mode == InitialInfectionMode.MANUAL:
            selected_agents = candidates
        else:
            count = min(config.count, len(candidates))
            selected_agents = self.rng.sample(candidates, k=count)

            if config.count > len(candidates):
                self.warnings.append(
                    f"Se pidieron {config.count} infectados iniciales, "
                    f"pero solo había {len(candidates)} candidatos."
                )

        for agent in selected_agents:
            infection_chain_id = agent.agent_id

            was_infected = agent.infect(
                current_slot=current_slot,
                disease=self.config.disease,
                source_agent_id=None,
                infection_chain_id=infection_chain_id,
                initial_state=config.initial_state,
            )

            if was_infected:
                self.initial_infected_agent_ids.append(agent.agent_id)

    def _get_initial_infection_candidates(self) -> list[SimulationAgent]:
        config = self.config.initial_infections

        if config.mode == InitialInfectionMode.RANDOM:
            return list(self.agents_by_id.values())

        if config.mode == InitialInfectionMode.BY_GROUP:
            if not config.target_group_uuids:
                self.warnings.append(
                    "Modo BY_GROUP sin grupos objetivo. Se usará toda la población."
                )
                return list(self.agents_by_id.values())

            candidates: list[SimulationAgent] = []
            target_groups = set(config.target_group_uuids)

            for agent in self.agents_by_id.values():
                if agent.academic_group_id in target_groups:
                    candidates.append(agent)

            return candidates

        if config.mode == InitialInfectionMode.BY_COURSE:
            if not config.target_course_uuids:
                self.warnings.append(
                    "Modo BY_COURSE sin cursos objetivo. Se usará toda la población."
                )
                return list(self.agents_by_id.values())

            candidates = []
            target_courses = set(config.target_course_uuids)

            for agent in self.agents_by_id.values():
                if agent.course_uuid in target_courses:
                    candidates.append(agent)

            return candidates

        if config.mode == InitialInfectionMode.MANUAL:
            candidates = []

            for agent_id in config.manual_agent_ids:
                agent = self.agents_by_id.get(agent_id)
                if agent is not None:
                    candidates.append(agent)

            return candidates

        return list(self.agents_by_id.values())

    # ========================================================
    # ÍNDICES Y AGRUPACIONES
    # ========================================================

    def _index_agents(
        self,
        agents: list[SimulationAgent],
    ) -> None:
        self.agents_by_id = {
            agent.agent_id: agent
            for agent in agents
        }

        self.agents_by_group = defaultdict(list)

        for agent in agents:
            self.agents_by_group[agent.academic_group_id].append(agent)

    def _group_academic_events_by_day_and_start(
        self,
        events: list[SimulationEvent],
    ) -> dict[tuple[int, int], list[SimulationEvent]]:
        grouped: dict[tuple[int, int], list[SimulationEvent]] = defaultdict(list)

        for event in events:
            grouped[(event.day_index, event.start_slot)].append(event)

        return dict(grouped)

    def _group_idle_periods_by_day_and_start(
        self,
        idle_periods: list[IdlePeriod],
    ) -> dict[tuple[int, int], list[IdlePeriod]]:
        grouped: dict[tuple[int, int], list[IdlePeriod]] = defaultdict(list)

        for idle_period in idle_periods:
            grouped[(idle_period.day_index, idle_period.start_slot)].append(idle_period)

        return dict(grouped)

    def _get_day_start_slots(
        self,
        day_index: int,
        academic_events_by_day_and_start: dict[tuple[int, int], list[SimulationEvent]],
        idle_periods_by_day_and_start: dict[tuple[int, int], list[IdlePeriod]],
    ) -> list[int]:
        slots = set()

        for event_day_index, start_slot in academic_events_by_day_and_start.keys():
            if event_day_index == day_index:
                slots.add(start_slot)

        for idle_day_index, start_slot in idle_periods_by_day_and_start.keys():
            if idle_day_index == day_index:
                slots.add(start_slot)

        return sorted(slots)

    # ========================================================
    # ESTADOS Y RESULTADOS TEMPORALES
    # ========================================================

    def _update_agent_states(
        self,
        current_slot: int,
    ) -> None:
        for agent in self.agents_by_id.values():
            agent.update_state(current_slot)

    def _record_time_series(
        self,
        slot: int,
        new_infections: int,
    ) -> None:
        if self.data is None:
            raise RuntimeError("No hay datos de simulación cargados.")

        counts = self._count_states()
        day_index = slot // self.data.slots_per_day if self.data.slots_per_day > 0 else 0

        if self.time_series and self.time_series[-1].slot == slot:
            row = self.time_series[-1]
            row.susceptible = counts[DiseaseState.SUSCEPTIBLE]
            row.exposed = counts[DiseaseState.EXPOSED]
            row.infectious = counts[DiseaseState.INFECTIOUS]
            row.recovered = counts[DiseaseState.RECOVERED]
            row.isolated = self._count_isolated()
            row.new_infections += new_infections
        else:
            self.time_series.append(
                TimeSeriesRow(
                    slot=slot,
                    day_index=day_index,
                    susceptible=counts[DiseaseState.SUSCEPTIBLE],
                    exposed=counts[DiseaseState.EXPOSED],
                    infectious=counts[DiseaseState.INFECTIOUS],
                    recovered=counts[DiseaseState.RECOVERED],
                    new_infections=new_infections,
                    isolated=self._count_isolated(),
                )
            )

        self._update_group_peak_infectious()

    def _record_occupancy(
        self,
        slot: int,
        day_index: int,
        planned_events: list[PlannedSimulationEvent],
        infection_events: list[InfectionEvent],
    ) -> None:
        if self.data is None:
            raise RuntimeError("No hay datos de simulación cargados.")

        present_agent_ids: set[str] = set()

        for planned_event in planned_events:
            present_agent_ids.update(
                agent_id
                for agent_id in planned_event.agent_ids
                if agent_id in self.agents_by_id
            )

        global_counts = self._count_present_agent_states(present_agent_ids)

        self.occupancy_by_slot.append(
            OccupancyRow(
                slot=slot,
                day_index=day_index,
                present_agents=len(present_agent_ids),
                susceptible_present=global_counts["susceptible"],
                exposed_present=global_counts["exposed"],
                infectious_present=global_counts["infectious"],
                recovered_present=global_counts["recovered"],
                isolated_present=global_counts["isolated"],
                new_infections=len(infection_events),
            )
        )

        infections_by_space: dict[str, int] = defaultdict(int)

        for infection in infection_events:
            if infection.space_uuid:
                infections_by_space[infection.space_uuid] += 1

        agent_ids_by_space: dict[str, set[str]] = defaultdict(set)

        for planned_event in planned_events:
            space_uuid = planned_event.event.space_uuid

            if not space_uuid:
                continue

            agent_ids_by_space[space_uuid].update(
                agent_id
                for agent_id in planned_event.agent_ids
                if agent_id in self.agents_by_id
            )

        for space_uuid, space_agent_ids in agent_ids_by_space.items():
            space_context = self.data.space_contexts.get(space_uuid)
            space_counts = self._count_present_agent_states(space_agent_ids)

            self.space_occupancy_by_slot.append(
                SpaceOccupancyRow(
                    slot=slot,
                    day_index=day_index,
                    space_uuid=space_uuid,
                    space_name=space_context.space_name if space_context is not None else None,
                    space_type_uuid=space_context.space_type_uuid if space_context is not None else None,
                    space_type_name=space_context.space_type_name if space_context is not None else None,
                    present_agents=len(space_agent_ids),
                    susceptible_present=space_counts["susceptible"],
                    exposed_present=space_counts["exposed"],
                    infectious_present=space_counts["infectious"],
                    recovered_present=space_counts["recovered"],
                    isolated_present=space_counts["isolated"],
                    new_infections=infections_by_space.get(space_uuid, 0),
                )
            )


    def _count_present_agent_states(
        self,
        agent_ids: set[str],
    ) -> dict[str, int]:
        counts = {
            "susceptible": 0,
            "exposed": 0,
            "infectious": 0,
            "recovered": 0,
            "isolated": 0,
        }

        for agent_id in agent_ids:
            agent = self.agents_by_id.get(agent_id)

            if agent is None:
                continue

            if agent.state == DiseaseState.SUSCEPTIBLE:
                counts["susceptible"] += 1
            elif agent.state == DiseaseState.EXPOSED:
                counts["exposed"] += 1
            elif agent.state == DiseaseState.INFECTIOUS:
                counts["infectious"] += 1
            elif agent.state == DiseaseState.RECOVERED:
                counts["recovered"] += 1

            if agent.is_isolated:
                counts["isolated"] += 1

        return counts

    def _count_states(self) -> dict[DiseaseState, int]:
        counts = {
            DiseaseState.SUSCEPTIBLE: 0,
            DiseaseState.EXPOSED: 0,
            DiseaseState.INFECTIOUS: 0,
            DiseaseState.RECOVERED: 0,
        }

        for agent in self.agents_by_id.values():
            counts[agent.state] += 1

        return counts

    def _count_isolated(self) -> int:
        return sum(
            1
            for agent in self.agents_by_id.values()
            if agent.is_isolated
        )

    def _update_group_peak_infectious(self) -> None:
        infectious_by_group: dict[str, int] = defaultdict(int)

        for agent in self.agents_by_id.values():
            if agent.state == DiseaseState.INFECTIOUS:
                infectious_by_group[agent.academic_group_id] += 1

        for group_id, count in infectious_by_group.items():
            if count > self.group_peak_infectious[group_id]:
                self.group_peak_infectious[group_id] = count

    # ========================================================
    # TRAZA VISUAL
    # ========================================================

    def _build_initial_visual_events(
        self,
        current_slot: int,
    ) -> list[VisualEvent]:
        """
        Crea eventos visuales para los infectados iniciales.

        No representan contagios internos, pero ayudan a entender
        dónde empieza la simulación epidemiológica.
        """

        events: list[VisualEvent] = []

        for agent_id in sorted(self.initial_infected_agent_ids):
            agent = self.agents_by_id.get(agent_id)

            if agent is None:
                continue

            target_label = self._format_agent_academic_label(agent.agent_id)

            events.append(
                VisualEvent(
                    event_type="initial_infection",
                    slot=current_slot,
                    visual_offset=0.0,
                    target_agent_id=agent.agent_id,
                    data={
                        "display_text": f"Infección inicial: {target_label}",
                        "target_label": target_label,
                        "state": agent.state.value,
                        "academic_group_id": agent.academic_group_id,
                        "course_uuid": agent.course_uuid,
                        "career_uuid": agent.career_uuid,
                        "infection_chain_id": agent.infection_chain_id,
                    },
                )
            )

        return events

    def _build_visual_events_from_infections(
        self,
        infection_events: list[InfectionEvent],
    ) -> list[VisualEvent]:
        """
        Convierte InfectionEvent en VisualEvent.

        El visual_offset se genera con un RNG separado para no alterar
        el resultado epidemiológico de la simulación.
        """

        visual_events: list[VisualEvent] = []

        for infection in infection_events:
            source_label = self._format_agent_academic_label(
                infection.source_agent_id
            )
            target_label = self._format_agent_academic_label(
                infection.infected_agent_id
            )
            space_label = self._format_space_label(infection.space_uuid)

            visual_events.append(
                VisualEvent(
                    event_type="infection",
                    slot=infection.slot,
                    visual_offset=self.visual_rng.random(),
                    space_uuid=infection.space_uuid,
                    source_agent_id=infection.source_agent_id,
                    target_agent_id=infection.infected_agent_id,
                    related_event_id=infection.event_id,
                    data={
                        "display_text": (
                            f"{source_label} contagia a {target_label} "
                            f"en {space_label}"
                        ),
                        "source_label": source_label,
                        "target_label": target_label,
                        "space_label": space_label,
                        "infection_id": infection.infection_id,
                        "transmission_probability": infection.transmission_probability,
                        "infection_chain_id": infection.infection_chain_id,
                    },
                )
            )

        return visual_events

    def _format_agent_academic_label(
        self,
        agent_id: Optional[str],
    ) -> str:
        if not agent_id:
            return "Origen externo"

        agent = self.agents_by_id.get(agent_id)

        if agent is None:
            return str(agent_id)

        if self.data is None:
            return agent.agent_id

        group_context = self.data.group_contexts.get(agent.academic_group_id)

        if group_context is None:
            return agent.agent_id

        label_parts = [
            group_context.career_name,
            group_context.course_name,
        ]

        if not group_context.is_virtual_group:
            label_parts.append(group_context.group_name)

        clean_parts = [
            str(part)
            for part in label_parts
            if part is not None and str(part).strip()
        ]

        if not clean_parts:
            return agent.agent_id

        return ", ".join(clean_parts)

    def _format_space_label(
        self,
        space_uuid: Optional[str],
    ) -> str:
        if not space_uuid:
            return "espacio desconocido"

        if self.data is None:
            return str(space_uuid)

        space_context = self.data.space_contexts.get(space_uuid)

        if space_context is None:
            return str(space_uuid)

        return space_context.space_name or str(space_uuid)

    def _record_visual_locations(
        self,
        planned_events: list[PlannedSimulationEvent],
    ) -> None:
        """
        Registra intervalos lógicos de ubicación de agentes.

        El motor no calcula movimiento continuo.
        Solo indica que un agente está en un espacio durante cierto intervalo.
        """

        for planned_event in planned_events:
            event = planned_event.event

            if event.space_uuid is None:
                continue

            for agent_id in sorted(planned_event.agent_ids):
                agent = self.agents_by_id.get(agent_id)

                if agent is None:
                    continue

                self.visual_locations.append(
                    VisualAgentLocation(
                        agent_id=agent.agent_id,
                        start_slot=event.start_slot,
                        end_slot=event.end_slot,
                        space_uuid=event.space_uuid,
                        event_id=event.event_id,
                        activity_type=event.activity_type.value,
                        academic_group_id=agent.academic_group_id,
                        course_uuid=agent.course_uuid,
                        career_uuid=agent.career_uuid,
                    )
                )

    def _record_visual_frame(
        self,
        slot: int,
        planned_events: list[PlannedSimulationEvent],
        visual_events: list[VisualEvent],
    ) -> None:
        """
        Registra un fotograma lógico.

        Este frame sirve para:
        - actualizar burbujas;
        - actualizar paneles de estado;
        - saber qué eventos visuales ocurren en esta franja.
        """

        if self.data is None:
            raise RuntimeError("No hay datos de simulación cargados.")

        day_index = (
            slot // self.data.slots_per_day
            if self.data.slots_per_day > 0
            else 0
        )

        if planned_events:
            end_slot = max(
                planned_event.event.end_slot
                for planned_event in planned_events
            )
        else:
            end_slot = slot

        frame = VisualFrame(
            slot=slot,
            day_index=day_index,
            start_slot=slot,
            end_slot=end_slot,
            agent_states=self._build_visual_agent_states(),
            space_summaries=self._build_visual_space_summaries(
                planned_events=planned_events,
                visual_events=visual_events,
            ),
            events=list(visual_events),
        )

        self._append_or_replace_visual_frame(frame)

    def _append_or_replace_visual_frame(
        self,
        frame: VisualFrame,
    ) -> None:
        """
        Evita duplicar frames del mismo slot.

        Puede pasar con el slot 0:
        - primero registramos el estado inicial;
        - después puede haber eventos académicos que empiezan en slot 0.
        """

        for index, existing_frame in enumerate(self.visual_frames):
            if existing_frame.slot == frame.slot:
                self.visual_frames[index] = frame
                return

        self.visual_frames.append(frame)

    def _build_visual_agent_states(self) -> dict[str, VisualAgentState]:
        """
        Crea una foto del estado epidemiológico de todos los agentes.
        """

        states: dict[str, VisualAgentState] = {}

        for agent_id, agent in self.agents_by_id.items():
            states[agent_id] = VisualAgentState(
                agent_id=agent.agent_id,
                state=agent.state.value,
                is_isolated=agent.is_isolated,
                academic_group_id=agent.academic_group_id,
                course_uuid=agent.course_uuid,
                career_uuid=agent.career_uuid,
                infection_slot=agent.infection_slot,
                infected_by=agent.infected_by,
                infection_chain_id=agent.infection_chain_id,
            )

        return states

    def _build_visual_space_summaries(
        self,
        planned_events: list[PlannedSimulationEvent],
        visual_events: list[VisualEvent],
    ) -> dict[str, VisualSpaceSummary]:
        """
        Construye los datos de burbuja por espacio para una franja.

        Solo los agentes presentes en planned_events cuentan como presentes.
        Si un agente no está en ningún evento de la franja, se interpreta
        como fuera de espacios visualizables.
        """

        if self.data is None:
            raise RuntimeError("No hay datos de simulación cargados.")

        summaries: dict[str, VisualSpaceSummary] = {}

        for space_uuid, context in self.data.space_contexts.items():
            summaries[space_uuid] = VisualSpaceSummary(
                space_uuid=space_uuid,
                space_name=context.space_name,
                space_type_uuid=context.space_type_uuid,
                space_type_name=context.space_type_name,
            )

        agents_by_space: dict[str, set[str]] = defaultdict(set)

        for planned_event in planned_events:
            event = planned_event.event

            if event.space_uuid is None:
                continue

            agents_by_space[event.space_uuid].update(
                agent_id
                for agent_id in planned_event.agent_ids
                if agent_id in self.agents_by_id
            )

        for space_uuid, agent_ids in agents_by_space.items():
            if space_uuid not in summaries:
                summaries[space_uuid] = VisualSpaceSummary(
                    space_uuid=space_uuid,
                )

            summary = summaries[space_uuid]
            summary.present_agents = len(agent_ids)

            for agent_id in agent_ids:
                agent = self.agents_by_id.get(agent_id)

                if agent is None:
                    continue

                if agent.state == DiseaseState.SUSCEPTIBLE:
                    summary.susceptible += 1
                elif agent.state == DiseaseState.EXPOSED:
                    summary.exposed += 1
                elif agent.state == DiseaseState.INFECTIOUS:
                    summary.infectious += 1
                elif agent.state == DiseaseState.RECOVERED:
                    summary.recovered += 1

                if agent.is_isolated:
                    summary.isolated += 1

        for event in visual_events:
            if event.space_uuid is None:
                continue

            if event.space_uuid not in summaries:
                summaries[event.space_uuid] = VisualSpaceSummary(
                    space_uuid=event.space_uuid,
                )

            if event.event_type in {
                "infection",
                "space_indirect_infection",
            }:
                summaries[event.space_uuid].new_infections += 1

        return summaries

    def _build_visual_trace(self) -> SimulationVisualTrace:
        """
        Construye la traza visual final de la simulación.
        """

        if self.data is None:
            raise RuntimeError("No hay datos de simulación cargados.")

        return SimulationVisualTrace(
            run_id=self.run_id,
            simulation_name=self.config.name,
            seed=self.seed,
            slot_minutes=self.data.slot_minutes,
            slots_per_day=self.data.slots_per_day,
            duration_days=self.config.duration_days,
            locations=sorted(
                self.visual_locations,
                key=lambda location: (
                    location.start_slot,
                    location.end_slot,
                    location.space_uuid or "",
                    location.agent_id,
                ),
            ),
            frames=sorted(
                self.visual_frames,
                key=lambda frame: frame.slot,
            ),
            events=sorted(
                self.visual_events,
                key=lambda event: (
                    event.slot,
                    event.visual_offset,
                    event.event_type,
                    event.target_agent_id or "",
                ),
            ),
            metadata={
                "trace_version": "1.0",
                "generated_by": "SimulationEngine",
                "description": (
                    "Traza visual post-cálculo para reproducir una simulación "
                    "como animación sin recalcular la lógica epidemiológica."
                ),
            },
        )

    # ========================================================
    # CONSTRUCCIÓN DE RESULTADOS
    # ========================================================

    def _build_result(
        self,
        started_at: str,
        finished_at: str,
        execution_time_seconds: float,
    ) -> SimulationResult:
        final_counts = self._count_states()

        visual_trace = None

        if self.generate_visual_trace:
            visual_trace = self._build_visual_trace()

        result = SimulationResult(
            run_id=self.run_id,
            simulation_name=self.config.name,
            seed=self.seed,
            started_at=started_at,
            finished_at=finished_at,
            execution_time_seconds=execution_time_seconds,
            config_snapshot=self.config.to_dict(),
            time_series=list(self.time_series),
            infection_events=list(self.infection_events),
            occupancy_by_slot=list(self.occupancy_by_slot),
            space_occupancy_by_slot=list(self.space_occupancy_by_slot),
            space_summary=self._build_space_summary(),
            group_summary=self._build_group_summary(),
            visual_trace=visual_trace,
            final_summary=self._build_final_summary(final_counts),
        )

        return result

    def _build_final_summary(
        self,
        final_counts: dict[DiseaseState, int],
    ) -> dict:
        peak_infectious = 0

        for row in self.time_series:
            if row.infectious > peak_infectious:
                peak_infectious = row.infectious

        total_ever_infected = sum(
            1
            for agent in self.agents_by_id.values()
            if agent.infection_slot is not None
        )

        return {
            "run_id": self.run_id,
            "simulation_name": self.config.name,
            "seed": self.seed,
            "total_agents": len(self.agents_by_id),
            "initial_infections": len(self.initial_infected_agent_ids),
            "internal_infections": len(self.infection_events),
            "total_ever_infected": total_ever_infected,
            "peak_infectious": peak_infectious,
            "final_susceptible": final_counts[DiseaseState.SUSCEPTIBLE],
            "final_exposed": final_counts[DiseaseState.EXPOSED],
            "final_infectious": final_counts[DiseaseState.INFECTIOUS],
            "final_recovered": final_counts[DiseaseState.RECOVERED],
            "warnings": list(self.warnings),
        }

    def _build_space_summary(self) -> list[SpaceSummaryRow]:
        if self.data is None:
            raise RuntimeError("No hay datos de simulación cargados.")

        infections_by_space: dict[str, int] = defaultdict(int)
        events_with_infections_by_space: dict[str, set[str]] = defaultdict(set)

        for infection in self.infection_events:
            if infection.space_uuid is None:
                continue

            infections_by_space[infection.space_uuid] += 1
            events_with_infections_by_space[infection.space_uuid].add(infection.event_id)

        rows: list[SpaceSummaryRow] = []

        for space_uuid, context in self.data.space_contexts.items():
            rows.append(
                SpaceSummaryRow(
                    space_uuid=space_uuid,
                    space_name=context.space_name,
                    space_type_uuid=context.space_type_uuid,
                    space_type_name=context.space_type_name,
                    infection_count=infections_by_space.get(space_uuid, 0),
                    event_count_with_infections=len(
                        events_with_infections_by_space.get(space_uuid, set())
                    ),
                )
            )

        rows.sort(
            key=lambda row: (
                -row.infection_count,
                row.space_name,
            )
        )

        return rows

    def _build_group_summary(self) -> list[GroupSummaryRow]:
        if self.data is None:
            raise RuntimeError("No hay datos de simulación cargados.")

        ever_infected_by_group: dict[str, int] = defaultdict(int)

        for agent in self.agents_by_id.values():
            if agent.infection_slot is not None:
                ever_infected_by_group[agent.academic_group_id] += 1

        rows: list[GroupSummaryRow] = []

        for group_id, context in self.data.group_contexts.items():
            rows.append(
                GroupSummaryRow(
                    group_uuid=group_id,
                    group_name=context.group_name,
                    course_uuid=context.course_uuid,
                    course_name=context.course_name,
                    career_uuid=context.career_uuid,
                    career_name=context.career_name,
                    infection_count=ever_infected_by_group.get(group_id, 0),
                    peak_infectious=self.group_peak_infectious.get(group_id, 0),
                )
            )

        rows.sort(
            key=lambda row: (
                row.career_name or "",
                row.course_name or "",
                row.group_name,
            )
        )

        return rows

    # ========================================================
    # HELPERS
    # ========================================================

    @staticmethod
    def _resolve_seed(seed: Optional[int]) -> int:
        if seed is not None:
            return int(seed)

        return random.SystemRandom().randint(0, 2**32 - 1)
