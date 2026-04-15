import sys

from PySide6.QtWidgets import QApplication

from backend.faculty import Faculty
from controller.builder_controller import BuilderController
from frontend.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    faculty = Faculty.load_from_csv("Facultades\Pruebas\escenario_facultad_ejemplo.csv")
    builder_controller = BuilderController(faculty)

    window = MainWindow(builder_controller)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()