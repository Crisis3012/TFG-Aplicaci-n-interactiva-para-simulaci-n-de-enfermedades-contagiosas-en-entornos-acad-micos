from backend.faculty import Faculty
from backend.faculty_project_manager import FacultyProjectManager
from controller.builder_controller import BuilderController
from controller.simulation_controller import SimulationController

from backend.simulation.config import SimulationConfig, InitialInfectionConfig, BatchConfig
from backend.simulation.disease import DiseaseConfig, DiseaseState


project_manager = FacultyProjectManager()
faculty, faculty_name = project_manager.load_active_or_create_default()

builder_controller = BuilderController(
    faculty=faculty,
    project_manager=project_manager,
    active_faculty_name=faculty_name,
)

simulation_controller = SimulationController(builder_controller)

presets = simulation_controller.get_disease_presets()
disease = presets["COVID-like"]

config = SimulationConfig(
    name="Prueba desde controller",
    duration_days=5,
    seed=1234,
    disease=disease,
    initial_infections=InitialInfectionConfig(
        count=1,
        initial_state=DiseaseState.INFECTIOUS,
    ),
    batch=BatchConfig(
        enabled=False,
        runs=1,
        batch_seed=None,
    ),
)

response = simulation_controller.run_simulation(config)

print("Success:", response.success)
print("Message:", response.message)
print("Saved path:", response.saved_path)

if response.result is not None:
    print(response.result.final_summary)

config.batch = BatchConfig(
    enabled=True,
    runs=5,
    batch_seed=3012,
)

def progress(current, total):
    print(f"Progreso batch: {current}/{total}")

response = simulation_controller.run_simulation(
    config=config,
    progress_callback=progress,
)

print("Success:", response.success)
print("Is batch:", response.is_batch)
print("Saved path:", response.saved_path)

if response.result is not None:
    print(response.result.aggregated_summary)