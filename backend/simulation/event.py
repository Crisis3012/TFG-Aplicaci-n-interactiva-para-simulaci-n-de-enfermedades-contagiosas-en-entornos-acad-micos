from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
from typing import Any, Optional


class ActivityType(Enum):
    CLASS = "class"
    LAB = "lab"
    CORRIDOR = "corridor"
    LIBRARY = "library"
    CAFETERIA = "cafeteria"
    COMMON_SPACE = "common_space"
    OTHER = "other"


@dataclass
class SimulationEvent:
    """
    Evento usado por el motor de simulación.

    Se genera a partir de los ScheduleBlock del Builder, pero no es
    exactamente lo mismo: aquí ya usamos slots numéricos.
    """

    event_id: str

    source_schedule_block_uuid: str

    day_index: int
    day_of_week: str

    start_slot: int
    end_slot: int
    duration_slots: int

    space_uuid: Optional[str]

    academic_group_id: str
    course_uuid: Optional[str] = None
    career_uuid: Optional[str] = None

    activity_type: ActivityType = ActivityType.CLASS

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["activity_type"] = self.activity_type.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SimulationEvent":
        data = dict(data)
        data["activity_type"] = ActivityType(data["activity_type"])
        return cls(**data)


@dataclass
class SpaceContext:
    """
    Información resumida de un espacio para la simulación.
    """

    space_uuid: str
    space_name: str
    space_type_uuid: Optional[str] = None
    space_type_name: Optional[str] = None

    capacity: Optional[int] = None
    ventilated: bool = False

    contact_level: float = 1.0
    duration_relevance: float = 1.0
    mask_effect_relevance: float = 1.0
    ventilation_effect_relevance: float = 1.0

    is_transit_type: bool = False
    is_recreation_type: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)