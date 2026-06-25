from PySide6.QtWidgets import QWidget, QVBoxLayout, QStackedWidget
from PySide6.QtGui import QGuiApplication

from frontend.menu_page import MenuPage
from frontend.builder_page import BuilderPage
from frontend.simulation_page import SimulationPage
from frontend.visualization_page import VisualizationPage
from frontend.simulation_visualization_page import SimulationVisualizationPage
from frontend.styles import MAIN_STYLE

from controller.simulation_controller import SimulationController


class MainWindow(QWidget):
    def __init__(self, builder_controller):
        super().__init__()

        self.builder_controller = builder_controller
        self.simulation_controller = SimulationController(
            builder_controller=self.builder_controller
        )

        self.setWindowTitle("TFG")
        screen = QGuiApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None

        if available is not None:
            width = min(1200, int(available.width() * 0.95))
            height = min(760, int(available.height() * 0.90))
            self.resize(width, height)

            x = available.x() + (available.width() - width) // 2
            y = available.y() + (available.height() - height) // 2
            self.move(x, y)
        else:
            self.resize(1100, 700)

        self.setMinimumSize(900, 560)

        self.stacked = QStackedWidget()

        self.menu_page = MenuPage(
            stacked_widget=self.stacked,
            builder_controller=self.builder_controller,
            simulation_page_index=2,
            visualization_page_index=4,
        )

        self.builder_page = BuilderPage(
            stacked_widget=self.stacked,
            builder_controller=self.builder_controller,
        )

        self.simulation_visualization_page = SimulationVisualizationPage(
            stacked_widget=self.stacked,
            simulation_controller=self.simulation_controller,
            simulation_page_index=2,
        )

        self.simulation_page = SimulationPage(
            stacked_widget=self.stacked,
            simulation_controller=self.simulation_controller,
            visualization_page=self.simulation_visualization_page,
            visualization_page_index=3,
        )

        self.visualization_page = VisualizationPage(
            stacked_widget=self.stacked,
            simulation_controller=self.simulation_controller,
            menu_page_index=0,
        )

        self.stacked.addWidget(self.menu_page)           # index 0
        self.stacked.addWidget(self.builder_page)        # index 1
        self.stacked.addWidget(self.simulation_page)     # index 2
        self.stacked.addWidget(self.simulation_visualization_page)  # index 3
        self.stacked.addWidget(self.visualization_page)  # index 4

        self.menu_page.refresh_faculty_selector()

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stacked)

        self.setLayout(layout)
        self.setStyleSheet(MAIN_STYLE)