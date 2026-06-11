from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Optional

from backend.simulation.contact import InfectionEvent
from backend.simulation.visual_trace import SimulationVisualTrace


@dataclass
class TimeSeriesRow:
    slot: int
    day_index: int

    susceptible: int
    exposed: int
    infectious: int
    recovered: int

    new_infections: int = 0
    isolated: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SpaceSummaryRow:
    space_uuid: str
    space_name: str

    space_type_uuid: Optional[str] = None
    space_type_name: Optional[str] = None

    infection_count: int = 0
    event_count_with_infections: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GroupSummaryRow:
    group_uuid: str
    group_name: str

    course_uuid: Optional[str] = None
    course_name: Optional[str] = None

    career_uuid: Optional[str] = None
    career_name: Optional[str] = None

    infection_count: int = 0
    peak_infectious: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SimulationResult:
    """
    Resultado completo de una ejecución individual.
    """

    run_id: str
    simulation_name: str

    seed: Optional[int]

    config_snapshot: dict[str, Any]

    time_series: list[TimeSeriesRow] = field(default_factory=list)
    infection_events: list[InfectionEvent] = field(default_factory=list)

    space_summary: list[SpaceSummaryRow] = field(default_factory=list)
    group_summary: list[GroupSummaryRow] = field(default_factory=list)

    visual_trace: Optional[SimulationVisualTrace] = None

    final_summary: dict[str, Any] = field(default_factory=dict)

    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    execution_time_seconds: Optional[float] = None

    def to_metadata_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "simulation_name": self.simulation_name,
            "seed": self.seed,
        }

    def to_summary_dict(self) -> dict[str, Any]:
        return dict(self.final_summary)

    def time_series_as_dicts(self) -> list[dict[str, Any]]:
        return [row.to_dict() for row in self.time_series]

    def infection_events_as_dicts(self) -> list[dict[str, Any]]:
        return [event.to_dict() for event in self.infection_events]

    def space_summary_as_dicts(self) -> list[dict[str, Any]]:
        return [row.to_dict() for row in self.space_summary]

    def group_summary_as_dicts(self) -> list[dict[str, Any]]:
        return [row.to_dict() for row in self.group_summary]
    
    def visual_trace_as_dict(self) -> Optional[dict[str, Any]]:
        if self.visual_trace is None:
            return None

        return self.visual_trace.to_dict()


@dataclass
class BatchRunSummary:
    run_id: str
    seed: int

    total_infections: int
    peak_infectious: int
    final_susceptible: int
    final_exposed: int
    final_infectious: int
    final_recovered: int

    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    execution_time_seconds: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BatchResult:
    """
    Resultado de un batch completo.

    Guarda una lista de resultados individuales y un resumen agregado.
    """

    batch_id: str
    simulation_name: str
    batch_seed: Optional[int]

    config_snapshot: dict[str, Any]

    runs: list[SimulationResult] = field(default_factory=list)
    run_summaries: list[BatchRunSummary] = field(default_factory=list)

    aggregated_summary: dict[str, Any] = field(default_factory=dict)

    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    execution_time_seconds: Optional[float] = None

    def to_metadata_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "simulation_name": self.simulation_name,
            "batch_seed": self.batch_seed,
            "number_of_runs": len(self.runs),
        }

    def run_summaries_as_dicts(self) -> list[dict[str, Any]]:
        return [summary.to_dict() for summary in self.run_summaries]