from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Union

from backend.faculty import Faculty
from backend.simulation.batch_runner import BatchRunner
from backend.simulation.config import (
    BatchConfig,
    InitialInfectionConfig,
    SimulationConfig,
)
from backend.simulation.disease import (
    DiseaseConfig,
    get_default_disease_presets,
)
from backend.simulation.engine import SimulationEngine
from backend.simulation.results import BatchResult, SimulationResult
from backend.simulation.storage import SimulationStorage


ProgressCallback = Callable[[int, int], None]

SimulationOutput = Union[SimulationResult, BatchResult]


@dataclass
class SimulationExecutionResponse:
    """
    Respuesta estándar para la UI después de ejecutar una simulación.

    Permite que la interfaz sepa:
    - si la ejecución ha ido bien;
    - si era una simulación individual o un batch;
    - dónde se han guardado los resultados;
    - qué objeto de resultado se ha generado;
    - qué mensaje mostrar al usuario.
    """

    success: bool
    is_batch: bool = False

    result: Optional[SimulationOutput] = None
    saved_path: Optional[Path] = None

    message: str = ""
    warnings: list[str] = None

    def __post_init__(self) -> None:
        if self.warnings is None:
            self.warnings = []


class SimulationController:
    """
    Controlador de simulación.

    Actúa como puente entre:
    - la futura SimulationPage de la UI;
    - la facultad activa del BuilderController;
    - el motor matemático de simulación;
    - el sistema de guardado de resultados.

    No implementa lógica epidemiológica directamente.
    """

    def __init__(self, builder_controller) -> None:
        self.builder_controller = builder_controller

    # ========================================================
    # Acceso a facultad activa
    # ========================================================

    @property
    def faculty(self) -> Faculty:
        return self.builder_controller.faculty

    @property
    def active_faculty_name(self) -> Optional[str]:
        return self.builder_controller.active_faculty_name

    def get_active_faculty_folder(self) -> Path:
        if not self.active_faculty_name:
            raise ValueError("No hay ninguna facultad activa.")

        project_manager = self.builder_controller.project_manager

        return project_manager.get_faculty_path(
            self.active_faculty_name
        )

    def get_storage(self) -> SimulationStorage:
        return SimulationStorage(
            faculty_folder=self.get_active_faculty_folder()
        )

    # ========================================================
    # Enfermedades y configuración base
    # ========================================================

    def get_disease_presets(self) -> dict[str, DiseaseConfig]:
        """
        Devuelve una copia de las enfermedades predeterminadas.

        Se usa deepcopy para evitar que la UI modifique accidentalmente
        los presets globales.
        """

        return deepcopy(get_default_disease_presets())

    def get_default_simulation_config(self) -> SimulationConfig:
        """
        Crea una configuración inicial razonable para la UI.

        La UI podrá modificar estos valores antes de ejecutar.
        """

        presets = self.get_disease_presets()
        disease = presets.get("COVID-like")

        if disease is None:
            disease = next(iter(presets.values()))

        return SimulationConfig(
            name="Nueva simulación",
            duration_days=5,
            seed=None,
            disease=disease,
            initial_infections=InitialInfectionConfig(
                count=1,
            ),
            batch=BatchConfig(
                enabled=False,
                runs=1,
                batch_seed=None,
            ),
        )

    # ========================================================
    # Ejecución principal
    # ========================================================

    def run_simulation(
        self,
        config: SimulationConfig,
        progress_callback: Optional[ProgressCallback] = None,
        save_results: bool = True,
        save_individual_runs: bool = True,
        generate_visual_trace: bool = False,
    ) -> SimulationExecutionResponse:
        """
        Ejecuta una simulación individual o un batch según config.batch.

        La comparación de resultados no se hace aquí.
        Este controlador solo ejecuta y guarda resultados.
        """

        try:
            self._ensure_active_faculty_exists()

            if self._should_run_batch(config):
                return self._run_batch(
                    config=config,
                    progress_callback=progress_callback,
                    save_results=save_results,
                    save_individual_runs=save_individual_runs,
                )

            return self._run_single(
                config=config,
                save_results=save_results,
                generate_visual_trace=generate_visual_trace,
            )

        except Exception as exc:
            return SimulationExecutionResponse(
                success=False,
                is_batch=False,
                result=None,
                saved_path=None,
                message=f"No se ha podido ejecutar la simulación: {exc}",
                warnings=[],
            )

    # ========================================================
    # Simulación individual
    # ========================================================

    def _run_single(
        self,
        config: SimulationConfig,
        save_results: bool,
        generate_visual_trace: bool = False,
    ) -> SimulationExecutionResponse:
        single_config = deepcopy(config)

        # Si por cualquier motivo viene un batch activado pero el controlador
        # ha decidido ejecutar single, lo desactivamos aquí.
        single_config.batch.enabled = False
        single_config.batch.runs = 1
        single_config.batch.batch_seed = None

        engine = SimulationEngine(
            faculty=self.faculty,
            config=single_config,
            generate_visual_trace=generate_visual_trace,
        )

        result = engine.run()

        saved_path = None

        if save_results:
            storage = self.get_storage()
            saved_path = storage.save_run(result)

        warnings = result.final_summary.get("warnings", [])

        return SimulationExecutionResponse(
            success=True,
            is_batch=False,
            result=result,
            saved_path=saved_path,
            message="Simulación ejecutada correctamente.",
            warnings=warnings,
        )

    # ========================================================
    # Batch
    # ========================================================

    def _run_batch(
        self,
        config: SimulationConfig,
        progress_callback: Optional[ProgressCallback],
        save_results: bool,
        save_individual_runs: bool,
    ) -> SimulationExecutionResponse:
        batch_config = deepcopy(config)

        runner = BatchRunner(
            faculty=self.faculty,
            config=batch_config,
        )

        result = runner.run(
            progress_callback=progress_callback,
        )

        saved_path = None

        if save_results:
            storage = self.get_storage()
            saved_path = storage.save_batch(
                batch_result=result,
                save_individual_runs=save_individual_runs,
            )

        return SimulationExecutionResponse(
            success=True,
            is_batch=True,
            result=result,
            saved_path=saved_path,
            message="Batch ejecutado correctamente.",
            warnings=[],
        )

    # ========================================================
    # Resultados guardados
    # ========================================================

    def list_saved_results(self) -> list[Path]:
        """
        Devuelve las carpetas de resultados guardadas para la facultad activa.
        Más adelante lo usará el menú de visualización.
        """

        storage = self.get_storage()
        return storage.list_result_folders()

    def delete_saved_result(self, folder_name: str) -> SimulationExecutionResponse:
        """
        Borra una carpeta de resultados.

        Se deja preparado para que más adelante la página de visualización
        permita eliminar simulaciones antiguas.
        """

        try:
            storage = self.get_storage()
            storage.delete_result_folder(folder_name)

            return SimulationExecutionResponse(
                success=True,
                message=f"Resultado '{folder_name}' eliminado correctamente.",
            )

        except Exception as exc:
            return SimulationExecutionResponse(
                success=False,
                message=f"No se ha podido eliminar el resultado: {exc}",
            )

    # ========================================================
    # Helpers
    # ========================================================

    def _should_run_batch(
        self,
        config: SimulationConfig,
    ) -> bool:
        return bool(
            config.batch.enabled
            and config.batch.runs > 1
        )

    def _ensure_active_faculty_exists(self) -> None:
        if self.faculty is None:
            raise ValueError("No hay ninguna facultad cargada.")

        if not self.active_faculty_name:
            raise ValueError("No hay ninguna facultad activa.")

        folder = self.get_active_faculty_folder()

        if not folder.exists():
            raise ValueError(
                f"No existe la carpeta de la facultad activa: {folder}"
            )