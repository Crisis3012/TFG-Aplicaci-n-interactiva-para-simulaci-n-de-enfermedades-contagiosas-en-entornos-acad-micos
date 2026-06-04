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
)
from backend.simulation.transmission_model import TransmissionModel


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
    ) -> None:
        self.faculty = faculty
        self.config = config

        self.run_id = str(uuid.uuid4())
        self.seed = self._resolve_seed(config.seed)
        self.rng = random.Random(self.seed)

        self.adapter = FacultySimulationAdapter(faculty)
        self.behavior_model = AgentBehaviorModel()
        self.contact_model = ContactModel()
        self.transmission_model = TransmissionModel()

        self.data: Optional[FacultySimulationData] = None

        self.agents_by_id: dict[str, SimulationAgent] = {}
        self.agents_by_group: dict[str, list[SimulationAgent]] = defaultdict(list)

        self.infection_events: list[InfectionEvent] = []
        self.time_series: list[TimeSeriesRow] = []

        self.group_peak_infectious: dict[str, int] = defaultdict(int)

        self.initial_infected_agent_ids: list[str] = []
        self.warnings: list[str] = []

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

                for planned_event in planned_events:
                    event_infections = self._process_planned_event(planned_event)
                    self.infection_events.extend(event_infections)
                    new_infections += len(event_infections)

                self._record_time_series(
                    slot=start_slot,
                    new_infections=new_infections,
                )

            day_end_slot = (day_index + 1) * self.data.slots_per_day
            self._update_agent_states(current_slot=day_end_slot)
            self._record_time_series(
                slot=day_end_slot,
                new_infections=0,
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

        return infection_events

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
    # CONSTRUCCIÓN DE RESULTADOS
    # ========================================================

    def _build_result(
        self,
        started_at: str,
        finished_at: str,
        execution_time_seconds: float,
    ) -> SimulationResult:
        final_counts = self._count_states()

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
            space_summary=self._build_space_summary(),
            group_summary=self._build_group_summary(),
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