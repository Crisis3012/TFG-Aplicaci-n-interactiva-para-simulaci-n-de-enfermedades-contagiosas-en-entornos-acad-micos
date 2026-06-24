from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QInputDialog, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QMessageBox


class MenuPage(QWidget):
    def __init__(
        self,
        stacked_widget,
        builder_controller,
        simulation_page_index: int = 2,
        visualization_page_index: int = 4,
    ):
        super().__init__()

        self.stacked_widget = stacked_widget
        self.builder_controller = builder_controller
        self.simulation_page_index = simulation_page_index
        self.visualization_page_index = visualization_page_index
        self._updating_faculty_selector = False

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 15, 20, 20)
        main_layout.setSpacing(18)

        top_layout = QHBoxLayout()

        top_layout.addStretch()

        self.faculty_selector = QComboBox()
        self.faculty_selector.setFixedWidth(220)
        self.faculty_selector.currentTextChanged.connect(self._on_faculty_selected)

        self.new_faculty_button = QPushButton("+ Nueva facultad")
        self.new_faculty_button.setFixedSize(150, 35)
        self.new_faculty_button.clicked.connect(self._create_new_faculty)

        self.delete_faculty_button = QPushButton("Borrar facultad")
        self.delete_faculty_button.setFixedSize(150, 35)
        self.delete_faculty_button.setStyleSheet("""
            QPushButton {
                background-color: #c62828;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)
        self.delete_faculty_button.clicked.connect(self._delete_selected_faculty)

        top_layout.addWidget(QLabel("Facultad:"))
        top_layout.addWidget(self.faculty_selector)
        top_layout.addWidget(self.new_faculty_button)
        top_layout.addWidget(self.delete_faculty_button)

        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.setSpacing(18)

        title = QLabel("TFG")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 30, QFont.Weight.Bold))

        self.btn_builder = QPushButton("Builder")
        self.btn_simular = QPushButton("Simular")
        self.btn_visualizar = QPushButton("Visualizar")
        self.btn_salir = QPushButton("Salir")

        for button in [
            self.btn_builder,
            self.btn_simular,
            self.btn_visualizar,
            self.btn_salir,
        ]:
            button.setFixedSize(220, 45)

        self.btn_builder.clicked.connect(self.open_builder)
        self.btn_simular.clicked.connect(self.open_simulation)
        self.btn_visualizar.clicked.connect(self.open_visualization)
        self.btn_salir.clicked.connect(QApplication.instance().quit)

        center_layout.addWidget(title)
        center_layout.addSpacing(25)
        center_layout.addWidget(self.btn_builder, alignment=Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.btn_simular, alignment=Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.btn_visualizar, alignment=Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(self.btn_salir, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addLayout(top_layout)
        main_layout.addStretch()
        main_layout.addLayout(center_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

        self.refresh_faculty_selector()

    def open_builder(self):
        self.stacked_widget.setCurrentIndex(1)
        self.builder_controller.load_builder()

    def open_simulation(self):
        simulation_page = self.stacked_widget.widget(self.simulation_page_index)

        if hasattr(simulation_page, "load_page"):
            simulation_page.load_page()

        self.stacked_widget.setCurrentIndex(self.simulation_page_index)

    def open_visualization(self):
        visualization_page = self.stacked_widget.widget(self.visualization_page_index)

        if hasattr(visualization_page, "load_page"):
            visualization_page.load_page()

        self.stacked_widget.setCurrentIndex(self.visualization_page_index)

    def refresh_faculty_selector(self):
        self._updating_faculty_selector = True

        self.faculty_selector.clear()

        faculty_names = self.builder_controller.get_faculty_names()
        active_name = self.builder_controller.get_active_faculty_name()

        self.faculty_selector.addItems(faculty_names)

        if active_name:
            index = self.faculty_selector.findText(active_name)
            if index >= 0:
                self.faculty_selector.setCurrentIndex(index)

        self._updating_faculty_selector = False

    def _on_faculty_selected(self, faculty_name: str):
        if self._updating_faculty_selector:
            return

        if not faculty_name:
            return

        self.builder_controller.select_faculty(faculty_name)

    def _create_new_faculty(self):
        name, ok = QInputDialog.getText(
            self,
            "Nueva facultad",
            "Nombre de la nueva facultad:"
        )

        if not ok:
            return

        name = name.strip()

        if not name:
            self.builder_controller._show_error(
                "El nombre de la facultad no puede estar vacío."
            )
            return

        self.builder_controller.create_new_faculty_project(name)
        self.refresh_faculty_selector()

    def _delete_selected_faculty(self):
        faculty_name = self.faculty_selector.currentText().strip()

        if not faculty_name:
            return

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        box.setWindowTitle("Borrar facultad")
        box.setText(f"¿Seguro que quieres borrar la facultad '{faculty_name}'?")
        box.setInformativeText("Esta acción eliminará la facultad y sus resultados guardados.")
        box.setStandardButtons(QMessageBox.StandardButton.No)

        yes_button = box.addButton("Sí, borrar", QMessageBox.ButtonRole.DestructiveRole)
        yes_button.setStyleSheet("""
            QPushButton {
                background-color: #c62828;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #b71c1c;
            }
        """)

        box.exec()

        if box.clickedButton() != yes_button:
            return

        self.builder_controller.delete_faculty_project(faculty_name)
        self.refresh_faculty_selector()