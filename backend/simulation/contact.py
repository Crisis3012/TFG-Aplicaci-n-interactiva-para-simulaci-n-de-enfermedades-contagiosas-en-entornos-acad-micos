from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Optional


@dataclass
class Contact:
    """
    Contacto efectivo entre un agente infeccioso y otro agente.

    No todos los contactos terminarán en contagio.
    """

    source_agent_id: str
    target_agent_id: str

    event_id: str
    space_uuid: Optional[str]

    start_slot: int
    duration_slots: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InfectionEvent:
    """
    Contagio real ocurrido durante la simulación.
    """

    infection_id: str

    source_agent_id: str
    infected_agent_id: str

    event_id: str
    space_uuid: Optional[str]

    slot: int
    transmission_probability: float

    infection_chain_id: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InfectionEvent":
        return cls(**data)