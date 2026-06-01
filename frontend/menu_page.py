from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QInputDialog
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class MenuPage(QWidget):
    def __init__(self, stacked_widget, builder_controller):
        super().__init__()

        self.stacked_widget = stacked_widget
        self.builder_controller = builder_controller
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

        top_layout.addWidget(QLabel("Facultad:"))
        top_layout.addWidget(self.faculty_selector)
        top_layout.addWidget(self.new_faculty_button)

        center_layout = QVBoxLayout()
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.setSpacing(18)

        title = QLabel("TFG")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 30, QFont.Weight.Bold))

        btn_builder = QPushButton("Builder")
        btn_simular = QPushButton("Simular")
        btn_visualizar = QPushButton("Visualizar")
        btn_salir = QPushButton("Salir")

        for button in [btn_builder, btn_simular, btn_visualizar, btn_salir]:
            button.setFixedSize(220, 45)

        btn_builder.clicked.connect(self.open_builder)
        btn_salir.clicked.connect(self.window().close)

        center_layout.addWidget(title)
        center_layout.addSpacing(25)
        center_layout.addWidget(btn_builder, alignment=Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(btn_simular, alignment=Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(btn_visualizar, alignment=Qt.AlignmentFlag.AlignCenter)
        center_layout.addWidget(btn_salir, alignment=Qt.AlignmentFlag.AlignCenter)

        main_layout.addLayout(top_layout)
        main_layout.addStretch()
        main_layout.addLayout(center_layout)
        main_layout.addStretch()

        self.setLayout(main_layout)

        self.refresh_faculty_selector()

    def open_builder(self):
        self.stacked_widget.setCurrentIndex(1)
        self.builder_controller.load_builder()

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
            self.builder_controller._show_error("El nombre de la facultad no puede estar vacío.")
            return

        self.builder_controller.create_new_faculty_project(name)
        self.refresh_faculty_selector()


    def open_builder(self):
        self.stacked_widget.setCurrentIndex(1)
        self.builder_controller.load_builder()