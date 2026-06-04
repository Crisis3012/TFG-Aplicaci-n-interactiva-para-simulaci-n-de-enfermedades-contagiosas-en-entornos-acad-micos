from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from statistics import mean, pstdev
from typing import Callable, Optional
import random
import time
import uuid

from backend.faculty import Faculty
from backend.simulation.config import SimulationConfig
from backend.simulation.engine import SimulationEngine
from backend.simulation.results import (
    BatchResult,
    BatchRunSummary,
    SimulationResult,
)


ProgressCallback = Callable[[int, int], None]


class BatchRunner:
    """
    Ejecuta un conjunto de simulaciones reproducibles.

    La semilla del batch no se usa directamente en todas las simulaciones.
    Se usa para generar una semilla individual distinta para cada run.
    """

    def __init__(self, faculty: Faculty, config: SimulationConfig) -> None:
        self.faculty = faculty
        self.config = config

    def run(
        self,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> BatchResult:
        self.config.validate()

        start_perf = time.perf_counter()
        started_at = datetime.now().isoformat(timespec="seconds")

        number_of_runs = self._resolve_number_of_runs()
        batch_seed = self._resolve_batch_seed()

        run_seeds = self._generate_run_seeds(
            batch_seed=batch_seed,
            number_of_runs=number_of_runs,
        )

        batch_id = str(uuid.uuid4())
        run_results: list[SimulationResult] = []
        run_summaries: list[BatchRunSummary] = []

        for index, run_seed in enumerate(run_seeds, start=1):
            run_config = self._build_run_config(
                base_config=self.config,
                run_seed=run_seed,
                run_index=index,
            )

            engine = SimulationEngine(
                faculty=self.faculty,
                config=run_config,
            )

            result = engine.run()
            run_results.append(result)
            run_summaries.append(self._build_run_summary(result))

            if progress_callback is not None:
                progress_callback(index, number_of_runs)

        finished_at = datetime.now().isoformat(timespec="seconds")
        execution_time_seconds = time.perf_counter() - start_perf

        aggregated_summary = self._build_aggregated_summary(
            batch_id=batch_id,
            batch_seed=batch_seed,
            run_summaries=run_summaries,
            batch_execution_time_seconds=execution_time_seconds,
            started_at=started_at,
            finished_at=finished_at,
        )

        return BatchResult(
            batch_id=batch_id,
            simulation_name=self.config.name,
            batch_seed=batch_seed,
            started_at=started_at,
            finished_at=finished_at,
            execution_time_seconds=execution_time_seconds,
            config_snapshot=self.config.to_dict(),
            runs=run_results,
            run_summaries=run_summaries,
            aggregated_summary=aggregated_summary,
        )

    # ========================================================
    # Configuración de batch
    # ========================================================

    def _resolve_number_of_runs(self) -> int:
        if not self.config.batch.enabled:
            return 1

        return max(1, int(self.config.batch.runs))

    def _resolve_batch_seed(self) -> int:
        if self.config.batch.batch_seed is not None:
            return int(self.config.batch.batch_seed)

        if self.config.seed is not None:
            return int(self.config.seed)

        return random.SystemRandom().randint(0, 2**32 - 1)

    def _generate_run_seeds(
        self,
        batch_seed: int,
        number_of_runs: int,
    ) -> list[int]:
        batch_rng = random.Random(batch_seed)

        return [
            batch_rng.randint(0, 2**32 - 1)
            for _ in range(number_of_runs)
        ]

    def _build_run_config(
        self,
        base_config: SimulationConfig,
        run_seed: int,
        run_index: int,
    ) -> SimulationConfig:
        """
        Crea una copia independiente de la configuración para una ejecución.

        El batch se desactiva dentro de cada run individual para evitar que
        SimulationEngine trate esa ejecución como otro batch.
        """

        run_config = deepcopy(base_config)

        run_config.seed = run_seed
        run_config.name = f"{base_config.name} - run {run_index:03d}"

        run_config.batch.enabled = False
        run_config.batch.runs = 1
        run_config.batch.batch_seed = None

        return run_config

    # ========================================================
    # Summaries
    # ========================================================

    def _build_run_summary(
        self,
        result: SimulationResult,
    ) -> BatchRunSummary:
        summary = result.final_summary

        return BatchRunSummary(
            run_id=result.run_id,
            seed=int(result.seed) if result.seed is not None else -1,
            started_at=result.started_at,
            finished_at=result.finished_at,
            execution_time_seconds=result.execution_time_seconds,
            total_infections=int(summary.get("total_ever_infected", 0)),
            peak_infectious=int(summary.get("peak_infectious", 0)),
            final_susceptible=int(summary.get("final_susceptible", 0)),
            final_exposed=int(summary.get("final_exposed", 0)),
            final_infectious=int(summary.get("final_infectious", 0)),
            final_recovered=int(summary.get("final_recovered", 0)),
        )

    def _build_aggregated_summary(
        self,
        batch_id: str,
        batch_seed: int,
        run_summaries: list[BatchRunSummary],
        batch_execution_time_seconds: float,
        started_at: str,
        finished_at: str,
    ) -> dict:
        if not run_summaries:
            return {
                "batch_id": batch_id,
                "simulation_name": self.config.name,
                "batch_seed": batch_seed,
                "number_of_runs": 0,
                "started_at": started_at,
                "finished_at": finished_at,
                "batch_execution_time_seconds": batch_execution_time_seconds,
                "run_execution_time_mean": 0.0,
                "run_execution_time_min": 0.0,
                "run_execution_time_max": 0.0,
                "run_execution_time_std": 0.0,
            }

        total_infections = [
            item.total_infections
            for item in run_summaries
        ]

        peak_infectious = [
            item.peak_infectious
            for item in run_summaries
        ]

        final_susceptible = [
            item.final_susceptible
            for item in run_summaries
        ]

        final_exposed = [
            item.final_exposed
            for item in run_summaries
        ]

        final_infectious = [
            item.final_infectious
            for item in run_summaries
        ]

        final_recovered = [
            item.final_recovered
            for item in run_summaries
        ]

        run_times = [
            item.execution_time_seconds
            for item in run_summaries
            if item.execution_time_seconds is not None
        ]

        return {
            "batch_id": batch_id,
            "simulation_name": self.config.name,
            "batch_seed": batch_seed,
            "number_of_runs": len(run_summaries),

            "started_at": started_at,
            "finished_at": finished_at,
            "batch_execution_time_seconds": batch_execution_time_seconds,

            "run_execution_time_mean": self._safe_mean(run_times),
            "run_execution_time_min": min(run_times) if run_times else 0.0,
            "run_execution_time_max": max(run_times) if run_times else 0.0,
            "run_execution_time_std": self._safe_std(run_times),

            "total_infections_mean": self._safe_mean(total_infections),
            "total_infections_min": min(total_infections),
            "total_infections_max": max(total_infections),
            "total_infections_std": self._safe_std(total_infections),

            "peak_infectious_mean": self._safe_mean(peak_infectious),
            "peak_infectious_min": min(peak_infectious),
            "peak_infectious_max": max(peak_infectious),
            "peak_infectious_std": self._safe_std(peak_infectious),

            "final_susceptible_mean": self._safe_mean(final_susceptible),
            "final_exposed_mean": self._safe_mean(final_exposed),
            "final_infectious_mean": self._safe_mean(final_infectious),
            "final_recovered_mean": self._safe_mean(final_recovered),
        }

    @staticmethod
    def _safe_mean(values: list[int | float]) -> float:
        if not values:
            return 0.0

        return float(mean(values))

    @staticmethod
    def _safe_std(values: list[int | float]) -> float:
        if len(values) <= 1:
            return 0.0

        return float(pstdev(values))