from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional
import random

from backend.simulation.disease import DiseaseConfig, DiseaseState


@dataclass
class SimulationAgent:
    """
    Agente individual de la simulación.

    Representa una persona de la facultad, normalmente un estudiante.
    """

    agent_id: str
    academic_group_id: str

    course_uuid: Optional[str] = None
    career_uuid: Optional[str] = None

    state: DiseaseState = DiseaseState.SUSCEPTIBLE

    infection_slot: Optional[int] = None
    infectious_start_slot: Optional[int] = None
    recovery_slot: Optional[int] = None

    infected_by: Optional[str] = None
    infection_chain_id: Optional[str] = None

    is_isolated: bool = False

    def infect(
        self,
        current_slot: int,
        disease: DiseaseConfig,
        source_agent_id: Optional[str] = None,
        infection_chain_id: Optional[str] = None,
        initial_state: DiseaseState = DiseaseState.EXPOSED,
    ) -> bool:
        """
        Infecta al agente si está susceptible.

        Devuelve True si la infección se ha aplicado y False si el agente
        no podía infectarse.
        """

        if self.state != DiseaseState.SUSCEPTIBLE:
            return False

        if initial_state not in {DiseaseState.EXPOSED, DiseaseState.INFECTIOUS}:
            raise ValueError("initial_state debe ser EXPOSED o INFECTIOUS.")

        self.state = initial_state
        self.infection_slot = current_slot
        self.infected_by = source_agent_id
        self.infection_chain_id = infection_chain_id or self.agent_id

        if initial_state == DiseaseState.EXPOSED:
            self.infectious_start_slot = current_slot + disease.incubation_slots
        else:
            self.infectious_start_slot = current_slot

        self.recovery_slot = self.infectious_start_slot + disease.infectious_duration_slots

        return True

    def update_state(self, current_slot: int) -> None:
        """
        Actualiza el estado epidemiológico según el slot actual.
        """

        if self.state == DiseaseState.EXPOSED:
            if self.infectious_start_slot is not None and current_slot >= self.infectious_start_slot:
                self.state = DiseaseState.INFECTIOUS

        elif self.state == DiseaseState.INFECTIOUS:
            if self.recovery_slot is not None and current_slot >= self.recovery_slot:
                self.state = DiseaseState.RECOVERED
                self.is_isolated = False

    def get_infectiousness_multiplier(
        self,
        current_slot: int,
        disease: DiseaseConfig,
    ) -> float:
        """
        Devuelve el multiplicador de infectividad del agente en el momento actual.
        """

        if self.state != DiseaseState.INFECTIOUS:
            return 0.0

        if self.infectious_start_slot is None:
            return 0.0

        slots_since_infectious = current_slot - self.infectious_start_slot

        if slots_since_infectious < 0:
            return 0.0

        if slots_since_infectious <= disease.high_infectiousness_duration_slots:
            return disease.high_infectiousness_multiplier

        return disease.low_infectiousness_multiplier

    def should_attend_event(
        self,
        rng: random.Random,
        disease: DiseaseConfig,
        base_attendance_rate: Optional[float] = None,
    ) -> bool:
        """
        Decide si el agente asiste a un evento.

        - Si está aislado, no asiste.
        - Si tiene una asistencia base del grupo/curso, se aplica.
        - Si está infectado, puede faltar adicionalmente por enfermedad.
        """

        if self.is_isolated:
            return False

        if base_attendance_rate is not None:
            if not 0 <= base_attendance_rate <= 1:
                raise ValueError("base_attendance_rate debe estar entre 0 y 1.")

            if rng.random() > base_attendance_rate:
                return False

        if self.state in {DiseaseState.EXPOSED, DiseaseState.INFECTIOUS}:
            if rng.random() < disease.absenteeism_probability:
                return False

        return True

    def isolate(self) -> None:
        self.is_isolated = True

    def release_from_isolation(self) -> None:
        self.is_isolated = False

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["state"] = self.state.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationAgent":
        data = dict(data)
        data["state"] = DiseaseState(data["state"])
        return cls(**data)