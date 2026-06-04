from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Optional

from backend.simulation.disease import DiseaseConfig, DiseaseState


class InitialInfectionMode(Enum):
    RANDOM = "random"
    BY_GROUP = "by_group"
    BY_COURSE = "by_course"
    MANUAL = "manual"


class InterventionEffectType(Enum):
    TRANSMISSION_MODIFIER = "transmission_modifier"
    CONTACT_MODIFIER = "contact_modifier"
    ATTENDANCE_MODIFIER = "attendance_modifier"
    SPACE_CLOSURE = "space_closure"
    ISOLATION_RULE = "isolation_rule"


@dataclass
class InitialInfectionConfig:
    """
    Configuración de infectados iniciales.

    En la primera versión se usará principalmente RANDOM.
    """

    mode: InitialInfectionMode = InitialInfectionMode.RANDOM
    count: int = 1

    initial_state: DiseaseState = DiseaseState.EXPOSED

    target_group_uuids: list[str] = field(default_factory=list)
    target_course_uuids: list[str] = field(default_factory=list)
    manual_agent_ids: list[str] = field(default_factory=list)

    def validate(self) -> None:
        if self.count < 0:
            raise ValueError("El número de infectados iniciales no puede ser negativo.")

        if self.initial_state not in {DiseaseState.EXPOSED, DiseaseState.INFECTIOUS}:
            raise ValueError("El estado inicial debe ser EXPOSED o INFECTIOUS.")

        if self.mode == InitialInfectionMode.MANUAL and not self.manual_agent_ids:
            raise ValueError("El modo MANUAL requiere manual_agent_ids.")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["mode"] = self.mode.value
        data["initial_state"] = self.initial_state.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InitialInfectionConfig":
        data = dict(data)
        data["mode"] = InitialInfectionMode(data["mode"])
        data["initial_state"] = DiseaseState(data["initial_state"])
        return cls(**data)


@dataclass
class InterventionConfig:
    """
    Configuración básica de una intervención.

    De momento es una estructura genérica.
    La lógica concreta se implementará más adelante.
    """

    name: str
    effect_type: InterventionEffectType
    value: float

    start_slot: Optional[int] = None
    end_slot: Optional[int] = None

    target_type: str = "whole_faculty"
    target_uuids: list[str] = field(default_factory=list)

    def is_active(self, current_slot: int) -> bool:
        if self.start_slot is not None and current_slot < self.start_slot:
            return False

        if self.end_slot is not None and current_slot > self.end_slot:
            return False

        return True

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["effect_type"] = self.effect_type.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InterventionConfig":
        data = dict(data)
        data["effect_type"] = InterventionEffectType(data["effect_type"])
        return cls(**data)


@dataclass
class BatchConfig:
    enabled: bool = False
    runs: int = 1
    batch_seed: Optional[int] = None

    def validate(self) -> None:
        if self.runs <= 0:
            raise ValueError("El número de ejecuciones del batch debe ser mayor que 0.")

        if not self.enabled and self.runs != 1:
            self.runs = 1

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BatchConfig":
        return cls(**data)


@dataclass
class SimulationConfig:
    """
    Configuración completa de una simulación.

    La comparación de simulaciones no forma parte de esta configuración.
    Los resultados se guardarán siempre y se compararán desde visualización.
    """

    name: str
    duration_days: int
    disease: DiseaseConfig

    seed: Optional[int] = None

    initial_infections: InitialInfectionConfig = field(
        default_factory=InitialInfectionConfig
    )

    interventions: list[InterventionConfig] = field(default_factory=list)

    batch: BatchConfig = field(default_factory=BatchConfig)

    slot_minutes: int = 30

    def validate(self) -> None:
        if not self.name.strip():
            raise ValueError("El nombre de la simulación no puede estar vacío.")

        if self.duration_days <= 0:
            raise ValueError("duration_days debe ser mayor que 0.")

        if self.slot_minutes <= 0:
            raise ValueError("slot_minutes debe ser mayor que 0.")

        self.disease.validate()
        self.initial_infections.validate()
        self.batch.validate()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "duration_days": self.duration_days,
            "seed": self.seed,
            "slot_minutes": self.slot_minutes,
            "disease": self.disease.to_dict(),
            "initial_infections": self.initial_infections.to_dict(),
            "interventions": [
                intervention.to_dict()
                for intervention in self.interventions
            ],
            "batch": self.batch.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationConfig":
        return cls(
            name=data["name"],
            duration_days=int(data["duration_days"]),
            seed=data.get("seed"),
            slot_minutes=int(data.get("slot_minutes", 30)),
            disease=DiseaseConfig.from_dict(data["disease"]),
            initial_infections=InitialInfectionConfig.from_dict(
                data["initial_infections"]
            ),
            interventions=[
                InterventionConfig.from_dict(item)
                for item in data.get("interventions", [])
            ],
            batch=BatchConfig.from_dict(data.get("batch", {})),
        )