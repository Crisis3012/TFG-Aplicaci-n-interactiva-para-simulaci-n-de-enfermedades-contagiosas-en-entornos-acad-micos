from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class MenuPage(QWidget):
    def __init__(self, stacked_widget, builder_controller):
        super().__init__()

        self.stacked_widget = stacked_widget
        self.builder_controller = builder_controller

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(18)

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

        layout.addWidget(title)
        layout.addSpacing(25)
        layout.addWidget(btn_builder, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn_simular, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn_visualizar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn_salir, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def open_builder(self):
        self.stacked_widget.setCurrentIndex(1)
        self.builder_controller.load_builder()