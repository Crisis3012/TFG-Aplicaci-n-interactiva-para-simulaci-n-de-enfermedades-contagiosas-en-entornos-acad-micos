from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


@dataclass
class VisualEvent:
    """
    Evento visualizable ocurrido durante una franja de simulación.

    No tiene por qué representar un evento epidemiológico nuevo.
    Es una versión preparada para la visualización.

    Ejemplos:
    - infection
    - state_change
    - enter_faculty
    - leave_faculty
    - space_indirect_infection, en una versión futura
    """

    event_type: str

    slot: int
    visual_offset: float = 0.5

    space_uuid: Optional[str] = None

    source_agent_id: Optional[str] = None
    target_agent_id: Optional[str] = None

    related_event_id: Optional[str] = None

    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VisualAgentLocation:
    """
    Indica dónde se encuentra un agente durante un intervalo lógico.

    El motor solo registra la ubicación lógica.
    El visualizador decidirá cómo animar el movimiento entre ubicaciones.
    """

    agent_id: str

    start_slot: int
    end_slot: int

    space_uuid: Optional[str]

    event_id: Optional[str] = None
    activity_type: Optional[str] = None

    academic_group_id: Optional[str] = None
    course_uuid: Optional[str] = None
    career_uuid: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VisualAgentState:
    """
    Estado epidemiológico y académico de un agente en una franja concreta.
    """

    agent_id: str
    state: str

    is_isolated: bool = False

    academic_group_id: Optional[str] = None
    course_uuid: Optional[str] = None
    career_uuid: Optional[str] = None

    infection_slot: Optional[int] = None
    infected_by: Optional[str] = None
    infection_chain_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VisualSpaceSummary:
    """
    Resumen visual de un espacio en una franja.

    Esto será la base de las burbujas junto a los nodos.
    """

    space_uuid: str
    space_name: Optional[str] = None

    space_type_uuid: Optional[str] = None
    space_type_name: Optional[str] = None

    present_agents: int = 0

    susceptible: int = 0
    exposed: int = 0
    infectious: int = 0
    recovered: int = 0
    isolated: int = 0

    new_infections: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VisualFrame:
    """
    Fotograma lógico de la simulación.

    No representa un frame gráfico real.
    Representa el estado de la simulación en un slot/franja concreta.
    """

    slot: int
    day_index: int

    start_slot: int
    end_slot: int

    agent_states: dict[str, VisualAgentState] = field(default_factory=dict)
    space_summaries: dict[str, VisualSpaceSummary] = field(default_factory=dict)
    events: list[VisualEvent] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "slot": self.slot,
            "day_index": self.day_index,
            "start_slot": self.start_slot,
            "end_slot": self.end_slot,
            "agent_states": {
                agent_id: state.to_dict()
                for agent_id, state in self.agent_states.items()
            },
            "space_summaries": {
                space_uuid: summary.to_dict()
                for space_uuid, summary in self.space_summaries.items()
            },
            "events": [
                event.to_dict()
                for event in self.events
            ],
        }


@dataclass
class SimulationVisualTrace:
    """
    Traza visual completa de una simulación individual.

    Esta estructura es independiente de PySide6.
    El backend la genera y la guarda.
    El frontend la carga y la convierte en animación.
    """

    run_id: str
    simulation_name: str
    seed: Optional[int]

    slot_minutes: int
    slots_per_day: int
    duration_days: int

    locations: list[VisualAgentLocation] = field(default_factory=list)
    frames: list[VisualFrame] = field(default_factory=list)
    events: list[VisualEvent] = field(default_factory=list)

    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "simulation_name": self.simulation_name,
            "seed": self.seed,
            "slot_minutes": self.slot_minutes,
            "slots_per_day": self.slots_per_day,
            "duration_days": self.duration_days,
            "locations": [
                location.to_dict()
                for location in self.locations
            ],
            "frames": [
                frame.to_dict()
                for frame in self.frames
            ],
            "events": [
                event.to_dict()
                for event in self.events
            ],
            "metadata": dict(self.metadata),
        }