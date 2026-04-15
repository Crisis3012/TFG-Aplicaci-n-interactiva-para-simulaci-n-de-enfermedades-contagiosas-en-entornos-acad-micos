from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget

from frontend.menu_page import MenuPage
from frontend.builder_page import BuilderPage
from frontend.styles import MAIN_STYLE


class MainWindow(QWidget):
    def __init__(self, builder_controller):
        super().__init__()

        self.builder_controller = builder_controller

        self.setWindowTitle("TFG")
        self.resize(1200, 760)

        self.stacked = QStackedWidget()

        self.menu_page = MenuPage(
            stacked_widget=self.stacked,
            builder_controller=self.builder_controller,
        )

        self.builder_page = BuilderPage(
            stacked_widget=self.stacked,
            builder_controller=self.builder_controller,
        )

        self.stacked.addWidget(self.menu_page)      # index 0
        self.stacked.addWidget(self.builder_page)   # index 1

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stacked)

        self.setLayout(layout)
        self.setStyleSheet(MAIN_STYLE)