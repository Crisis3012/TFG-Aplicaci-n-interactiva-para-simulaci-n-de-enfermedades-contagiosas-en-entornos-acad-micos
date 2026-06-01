import sys

from PySide6.QtWidgets import QApplication

from controller.builder_controller import BuilderController
from frontend.main_window import MainWindow
from backend.faculty_project_manager import FacultyProjectManager


def main():
    app = QApplication(sys.argv)

    project_manager = FacultyProjectManager(base_folder="Facultades")
    faculty, active_faculty_name = project_manager.load_active_or_create_default()

    builder_controller = BuilderController(
        faculty=faculty,
        project_manager=project_manager,
        active_faculty_name=active_faculty_name,
    )

    window = MainWindow(builder_controller)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()