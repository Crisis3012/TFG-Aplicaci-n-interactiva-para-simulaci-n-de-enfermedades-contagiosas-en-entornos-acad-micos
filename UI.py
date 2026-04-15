import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QLabel, QStackedWidget, QSplitter, QFrame,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem
)
from PySide6.QtCore import Qt, QRectF, QPoint
from PySide6.QtGui import QFont, QBrush, QPen


class GraphNode(QGraphicsRectItem):
    def __init__(self, x, y, size=120):
        super().__init__(-size / 2, -size / 2, size, size)

        self.setPos(x, y)
        self.setBrush(QBrush(Qt.GlobalColor.cyan))
        self.setPen(QPen(Qt.GlobalColor.darkBlue, 3))

        self.setFlags(
            QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable
        )


class GraphView(QGraphicsView):
    def __init__(self):
        super().__init__()

        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)

        # Escena grande: el "mapa"
        self.scene_obj.setSceneRect(-5000, -5000, 10000, 10000)

        # Un nodo de prueba
        node = GraphNode(0, 0, 120)
        self.scene_obj.addItem(node)

        # Ajustes visuales
        self.setStyleSheet("""
            QGraphicsView {
                background-color: #eaecee;
                border: none;
            }
        """)

        # El zoom se hace respecto al ratón
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

        # Ocultamos barras para que parezca una cámara libre
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Estado para pan con arrastre del fondo
        self._panning = False
        self._last_mouse_pos = QPoint()

        # Límites del zoom
        self.min_zoom = 0.2
        self.max_zoom = 4.0

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
            # item = self.itemAt(event.position().toPoint())

            # # Solo hacemos pan si se pulsa el fondo, no un nodo
            # if item is None:
                self._panning = True
                self._last_mouse_pos = event.position().toPoint()
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
                event.accept()
                return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            delta = event.position().toPoint() - self._last_mouse_pos
            self._last_mouse_pos = event.position().toPoint()

            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )

            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton and self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        zoom_in_factor = 1.15
        zoom_out_factor = 1 / zoom_in_factor

        current_scale = self.transform().m11()

        if event.angleDelta().y() > 0:
            target_scale = current_scale * zoom_in_factor
            if current_scale < self.max_zoom:
                factor = min(zoom_in_factor, self.max_zoom / current_scale)
                self.scale(factor, factor)
        else:
            target_scale = current_scale * zoom_out_factor
            if current_scale > self.min_zoom:
                factor = max(zoom_out_factor, self.min_zoom / current_scale)
                self.scale(factor, factor)

        event.accept()

class MenuPage(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget

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

        for btn in [btn_builder, btn_simular, btn_visualizar, btn_salir]:
            btn.setFixedSize(220, 45)

        btn_builder.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        btn_salir.clicked.connect(self.window().close)

        layout.addWidget(title)
        layout.addSpacing(25)
        layout.addWidget(btn_builder, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn_simular, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn_visualizar, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(btn_salir, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)


class BuilderPage(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        left_panel = QFrame()
        left_panel.setMinimumWidth(20)
        left_panel.setStyleSheet("""
            QFrame {
                background-color: #3b4048;
                border: none;
            }
        """)

        center_panel = GraphView()
        center_panel.setMinimumWidth(20)

        right_panel = QFrame()
        right_panel.setMinimumWidth(20)
        right_panel.setStyleSheet("""
            QFrame {
                background-color: #3b4048;
                border: none;
            }
        """)

        splitter.addWidget(left_panel)
        splitter.addWidget(center_panel)
        splitter.addWidget(right_panel)

        splitter.setSizes([220, 560, 260])
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.stacked_widget.setCurrentIndex(0)
        else:
            super().keyPressEvent(event)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("TFG")
        self.resize(1100, 700)

        self.stacked = QStackedWidget()
        self.menu_page = MenuPage(self.stacked)
        self.builder_page = BuilderPage(self.stacked)

        self.stacked.addWidget(self.menu_page)
        self.stacked.addWidget(self.builder_page)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.stacked)
        self.setLayout(layout)

        self.setStyleSheet("""
            QWidget {
                background-color: #2c2f33;
            }

            QLabel {
                color: white;
            }

            QPushButton {
                background-color: #7289da;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                padding: 8px;
            }

            QPushButton:hover {
                background-color: #5b6eae;
            }

            QPushButton:pressed {
                background-color: #4e5d94;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())