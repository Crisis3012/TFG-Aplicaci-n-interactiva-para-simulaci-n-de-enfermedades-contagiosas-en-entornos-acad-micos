from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from backend.simulation.results import (
    SimulationResult,
    BatchResult,
)


class SimulationStorage:
    """
    Guarda resultados de simulaciones en formato mixto JSON + CSV.

    Estructura para una simulación individual:

    simulation_results/
    └── sim_YYYYMMDD_HHMMSS_nombre/
        ├── metadata.json
        ├── config.json
        ├── summary.json
        ├── time_series.csv
        ├── infection_events.csv
        ├── space_summary.csv
        └── group_summary.csv

    Estructura para batch:

    simulation_results/
    └── batch_YYYYMMDD_HHMMSS_nombre/
        ├── metadata.json
        ├── config.json
        ├── summary.json
        ├── batch_summary.csv
        └── runs/
            ├── run_001/
            ├── run_002/
            └── ...
    """

    def __init__(self, faculty_folder: str | Path) -> None:
        self.faculty_folder = Path(faculty_folder)
        self.results_folder = self.faculty_folder / "simulation_results"
        self.results_folder.mkdir(parents=True, exist_ok=True)

    # ========================================================
    # Guardado de simulación individual
    # ========================================================

    def save_run(
        self,
        result: SimulationResult,
        folder_name: Optional[str] = None,
    ) -> Path:
        if folder_name is None:
            folder_name = self._build_run_folder_name(result)

        run_folder = self.results_folder / folder_name
        run_folder = self._ensure_unique_folder(run_folder)
        run_folder.mkdir(parents=True, exist_ok=True)

        self._save_run_files(
            result=result,
            run_folder=run_folder,
        )

        return run_folder

    def _save_run_files(
        self,
        result: SimulationResult,
        run_folder: Path,
    ) -> None:
        run_folder.mkdir(parents=True, exist_ok=True)

        self._write_json(
            run_folder / "metadata.json",
            self._build_run_metadata(result),
        )

        self._write_json(
            run_folder / "config.json",
            result.config_snapshot,
        )

        self._write_json(
            run_folder / "summary.json",
            result.to_summary_dict(),
        )

        self._write_csv(
            run_folder / "time_series.csv",
            result.time_series_as_dicts(),
            fieldnames=[
                "slot",
                "day_index",
                "susceptible",
                "exposed",
                "infectious",
                "recovered",
                "new_infections",
                "isolated",
            ],
        )

        self._write_csv(
            run_folder / "infection_events.csv",
            result.infection_events_as_dicts(),
            fieldnames=[
                "infection_id",
                "source_agent_id",
                "infected_agent_id",
                "event_id",
                "space_uuid",
                "slot",
                "transmission_probability",
                "infection_chain_id",

                "source_group_uuid",
                "source_group_name",
                "source_course_uuid",
                "source_course_name",
                "source_career_uuid",
                "source_career_name",

                "infected_group_uuid",
                "infected_group_name",
                "infected_course_uuid",
                "infected_course_name",
                "infected_career_uuid",
                "infected_career_name",

                "space_name",
                "space_type_uuid",
                "space_type_name",
            ],
        )

        self._write_csv(
            run_folder / "occupancy_by_slot.csv",
            result.occupancy_by_slot_as_dicts(),
            fieldnames=[
                "slot",
                "day_index",
                "present_agents",
                "susceptible_present",
                "exposed_present",
                "infectious_present",
                "recovered_present",
                "isolated_present",
                "new_infections",
            ],
        )

        self._write_csv(
            run_folder / "space_occupancy_by_slot.csv",
            result.space_occupancy_by_slot_as_dicts(),
            fieldnames=[
                "slot",
                "day_index",
                "space_uuid",
                "space_name",
                "space_type_uuid",
                "space_type_name",
                "present_agents",
                "susceptible_present",
                "exposed_present",
                "infectious_present",
                "recovered_present",
                "isolated_present",
                "new_infections",
            ],
        )

        self._write_csv(
            run_folder / "space_summary.csv",
            result.space_summary_as_dicts(),
            fieldnames=[
                "space_uuid",
                "space_name",
                "space_type_uuid",
                "space_type_name",
                "infection_count",
                "event_count_with_infections",
            ],
        )

        self._write_csv(
            run_folder / "group_summary.csv",
            result.group_summary_as_dicts(),
            fieldnames=[
                "group_uuid",
                "group_name",
                "course_uuid",
                "course_name",
                "career_uuid",
                "career_name",
                "infection_count",
                "peak_infectious",
            ],
        )

        visual_trace = result.visual_trace_as_dict()

        if visual_trace is not None:
            self._write_json(
                run_folder / "visual_trace.json",
                visual_trace,
            )

    # ========================================================
    # Guardado de batch
    # ========================================================

    def save_batch(
        self,
        batch_result: BatchResult,
        folder_name: Optional[str] = None,
        save_individual_runs: bool = True,
    ) -> Path:
        if folder_name is None:
            folder_name = self._build_batch_folder_name(batch_result)

        batch_folder = self.results_folder / folder_name
        batch_folder = self._ensure_unique_folder(batch_folder)
        batch_folder.mkdir(parents=True, exist_ok=True)

        self._write_json(
            batch_folder / "metadata.json",
            self._build_batch_metadata(batch_result),
        )

        self._write_json(
            batch_folder / "config.json",
            batch_result.config_snapshot,
        )

        self._write_json(
            batch_folder / "summary.json",
            batch_result.aggregated_summary,
        )

        self._write_csv(
            batch_folder / "batch_summary.csv",
            batch_result.run_summaries_as_dicts(),
            fieldnames=[
                "run_id",
                "seed",
                "started_at",
                "finished_at",
                "execution_time_seconds",
                "total_infections",
                "peak_infectious",
                "final_susceptible",
                "final_exposed",
                "final_infectious",
                "final_recovered",
            ],
        )

        if save_individual_runs:
            runs_folder = batch_folder / "runs"
            runs_folder.mkdir(parents=True, exist_ok=True)

            for index, run_result in enumerate(batch_result.runs, start=1):
                run_folder_name = f"run_{index:03d}"
                self._save_run_files(
                    result=run_result,
                    run_folder=runs_folder / run_folder_name,
                )

        return batch_folder

    # ========================================================
    # Listado y borrado
    # ========================================================

    def list_result_folders(self) -> list[Path]:
        if not self.results_folder.exists():
            return []

        return sorted(
            [
                path
                for path in self.results_folder.iterdir()
                if path.is_dir()
            ],
            key=lambda path: path.name,
        )

    def delete_result_folder(self, folder_name: str) -> None:
        """
        Borra una carpeta de resultados dentro de simulation_results.

        Protección básica: no permite borrar rutas externas.
        """

        target = (self.results_folder / folder_name).resolve()
        base = self.results_folder.resolve()

        if base not in target.parents:
            raise ValueError("La carpeta indicada no pertenece a simulation_results.")

        if not target.exists():
            raise FileNotFoundError(f"No existe la carpeta de resultados: {folder_name}")

        if not target.is_dir():
            raise ValueError("El resultado indicado no es una carpeta.")

        self._delete_folder_recursive(target)

    # ========================================================
    # Metadata
    # ========================================================

    def _build_run_metadata(
        self,
        result: SimulationResult,
    ) -> dict[str, Any]:
        files = {
            "metadata": "metadata.json",
            "config": "config.json",
            "summary": "summary.json",
            "time_series": "time_series.csv",
            "infection_events": "infection_events.csv",
            "occupancy_by_slot": "occupancy_by_slot.csv",
            "space_occupancy_by_slot": "space_occupancy_by_slot.csv",
            "space_summary": "space_summary.csv",
            "group_summary": "group_summary.csv",
        }

        if result.visual_trace is not None:
            files["visual_trace"] = "visual_trace.json"

        return {
            "type": "simulation_run",
            "created_at": self._now_iso(),
            "run_id": result.run_id,
            "simulation_name": result.simulation_name,
            "seed": result.seed,
            "started_at": result.started_at,
            "finished_at": result.finished_at,
            "execution_time_seconds": result.execution_time_seconds,
            "files": files,
        }

    def _build_batch_metadata(
        self,
        batch_result: BatchResult,
    ) -> dict[str, Any]:
        return {
            "type": "simulation_batch",
            "created_at": self._now_iso(),
            "batch_id": batch_result.batch_id,
            "simulation_name": batch_result.simulation_name,
            "batch_seed": batch_result.batch_seed,
            "number_of_runs": len(batch_result.runs),
            "started_at": batch_result.started_at,
            "finished_at": batch_result.finished_at,
            "execution_time_seconds": batch_result.execution_time_seconds,
            "files": {
                "metadata": "metadata.json",
                "config": "config.json",
                "summary": "summary.json",
                "batch_summary": "batch_summary.csv",
                "runs": "runs/",
            },
        }

    # ========================================================
    # Helpers de escritura
    # ========================================================

    def _write_json(
        self,
        path: Path,
        data: dict[str, Any],
    ) -> None:
        with path.open("w", encoding="utf-8") as file:
            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=4,
            )

    def _write_csv(
        self,
        path: Path,
        rows: list[dict[str, Any]],
        fieldnames: list[str],
    ) -> None:
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
                extrasaction="ignore",
            )
            writer.writeheader()

            for row in rows:
                writer.writerow(row)

    # ========================================================
    # Helpers de nombres/rutas
    # ========================================================

    def _build_run_folder_name(
        self,
        result: SimulationResult,
    ) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = self._safe_filename(result.simulation_name)
        return f"sim_{timestamp}_{safe_name}"

    def _build_batch_folder_name(
        self,
        batch_result: BatchResult,
    ) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_name = self._safe_filename(batch_result.simulation_name)
        return f"batch_{timestamp}_{safe_name}"

    def _ensure_unique_folder(
        self,
        folder_path: Path,
    ) -> Path:
        if not folder_path.exists():
            return folder_path

        base_name = folder_path.name
        parent = folder_path.parent

        index = 1

        while True:
            candidate = parent / f"{base_name}_{index}"
            if not candidate.exists():
                return candidate

            index += 1

    @staticmethod
    def _safe_filename(value: str) -> str:
        value = value.strip().lower()

        replacements = {
            " ": "_",
            "/": "_",
            "\\": "_",
            ":": "_",
            "*": "_",
            "?": "_",
            '"': "_",
            "<": "_",
            ">": "_",
            "|": "_",
            "á": "a",
            "é": "e",
            "í": "i",
            "ó": "o",
            "ú": "u",
            "à": "a",
            "è": "e",
            "ï": "i",
            "ü": "u",
            "ñ": "n",
            "ç": "c",
        }

        for old, new in replacements.items():
            value = value.replace(old, new)

        value = "".join(
            char
            for char in value
            if char.isalnum() or char in {"_", "-"}
        )

        return value or "simulation"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now().isoformat(timespec="seconds")

    def _delete_folder_recursive(
        self,
        folder_path: Path,
    ) -> None:
        for child in folder_path.iterdir():
            if child.is_dir():
                self._delete_folder_recursive(child)
            else:
                child.unlink()

        folder_path.rmdir()