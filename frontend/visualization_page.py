from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
import csv
from collections import defaultdict

from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtCore import QRectF
from PySide6.QtWidgets import QScrollArea
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import QPoint
from PySide6.QtGui import QBrush, QPainterPath

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSplitter,
    QFrame,
    QComboBox,
    QTextEdit,
    QMessageBox,
    QSizePolicy,
)
from frontend.graph_items import (
    BaseGraphNodeItem,
    GraphEdgeItem,
    create_graph_node_item,
)


def _safe_int(value, default: int = 0) -> int:
    try:
        if value in (None, ""):
            return default
        return int(float(value))
    except (TypeError, ValueError):
        return default
    
def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
    
def _metric_color(value: float, max_value: float) -> QColor:
    if max_value <= 0:
        return QColor("#1e3a8a")

    ratio = min(1.0, max(0.0, value / max_value))

    red = int(30 + ratio * 225)
    green = int(58 + (1.0 - abs(ratio - 0.5) * 2.0) * 80)
    blue = int(138 - ratio * 90)

    return QColor(red, green, blue)


class LineChartWidget(QWidget):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.title = title
        self.series: dict[str, list[tuple[int, int]]] = {}
        self.setMinimumHeight(220)

    def set_series(self, series: dict[str, list[tuple[int, int]]]) -> None:
        self.series = series
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(12, 12, -12, -12)
        painter.fillRect(rect, QColor("#ffffff"))

        painter.setPen(QPen(QColor("#111827")))
        title_font = QFont("Arial", 11)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(rect.left(), rect.top(), rect.width(), 22, Qt.AlignmentFlag.AlignLeft, self.title)

        chart_rect = rect.adjusted(44, 36, -16, -34)

        all_points = [point for values in self.series.values() for point in values]

        if not all_points:
            painter.setPen(QPen(QColor("#6b7280")))
            painter.drawText(chart_rect, Qt.AlignmentFlag.AlignCenter, "Sin datos")
            return

        min_x = min(x for x, _ in all_points)
        max_x = max(x for x, _ in all_points)
        max_y = max(y for _, y in all_points)
        min_y = 0

        if max_x == min_x:
            max_x += 1

        if max_y <= 0:
            max_y = 1

        y_guides = self._build_guides(max_y)
        x_guides = self._build_x_guides(min_x, max_x)

        painter.setFont(QFont("Arial", 8))

        for guide in y_guides:
            y = chart_rect.bottom() - ((guide - min_y) / (max_y - min_y)) * chart_rect.height()

            painter.setPen(QPen(QColor("#e5e7eb"), 1))
            painter.drawLine(chart_rect.left(), y, chart_rect.right(), y)

            painter.setPen(QPen(QColor("#111827")))
            painter.drawText(
                rect.left(),
                y - 8,
                38,
                16,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                self._format_axis_value(guide),
            )

        for guide in x_guides:
            x = chart_rect.left() + ((guide - min_x) / (max_x - min_x)) * chart_rect.width()

            painter.setPen(QPen(QColor("#f3f4f6"), 1))
            painter.drawLine(x, chart_rect.top(), x, chart_rect.bottom())

            painter.setPen(QPen(QColor("#111827")))
            painter.drawText(
                x - 28,
                chart_rect.bottom() + 8,
                56,
                16,
                Qt.AlignmentFlag.AlignCenter,
                self._format_axis_value(guide),
            )

        painter.setPen(QPen(QColor("#d1d5db"), 1))
        painter.drawLine(chart_rect.bottomLeft(), chart_rect.bottomRight())
        painter.drawLine(chart_rect.bottomLeft(), chart_rect.topLeft())

        colors = {
            "Susceptibles": QColor("#2563eb"),
            "Expuestos": QColor("#f59e0b"),
            "Infecciosos": QColor("#dc2626"),
            "Recuperados": QColor("#16a34a"),
            "Contagios": QColor("#dc2626"),
            "Presencia media": QColor("#2563eb"),
            "Riesgo / 100 presentes": QColor("#7c3aed"),
            "Infecciones totales": QColor("#dc2626"),
            "Pico infeccioso": QColor("#7c3aed"),
        }

        for name, values in self.series.items():
            if len(values) < 2:
                continue

            color = colors.get(name, QColor("#374151"))
            painter.setPen(QPen(color, 2))

            previous = None

            for x, y in values:
                px = chart_rect.left() + ((x - min_x) / (max_x - min_x)) * chart_rect.width()
                py = chart_rect.bottom() - ((y - min_y) / (max_y - min_y)) * chart_rect.height()

                if previous is not None:
                    painter.drawLine(previous[0], previous[1], px, py)

                previous = (px, py)

        legend_x = chart_rect.left()
        legend_y = chart_rect.bottom() + 10

        painter.setFont(QFont("Arial", 8))

        for name in self.series.keys():
            color = colors.get(name, QColor("#374151"))
            painter.setPen(QPen(color, 8))
            painter.drawPoint(legend_x, legend_y + 6)
            painter.setPen(QPen(QColor("#111827")))
            painter.drawText(legend_x + 10, legend_y, 100, 16, Qt.AlignmentFlag.AlignLeft, name)
            legend_x += 105

    def _build_guides(self, max_value: float) -> list[float]:
        if max_value <= 0:
            return [0.0, 1.0]

        return [
            0.0,
            max_value / 3,
            (max_value * 2) / 3,
            max_value,
        ]


    def _build_x_guides(self, min_value: float, max_value: float) -> list[float]:
        if max_value <= min_value:
            return [min_value]

        min_int = int(round(min_value))
        max_int = int(round(max_value))

        values_are_integer_like = (
            abs(min_value - min_int) < 0.001
            and abs(max_value - max_int) < 0.001
        )

        if values_are_integer_like:
            span = max_int - min_int

            if span <= 8:
                return list(range(min_int, max_int + 1))

            step = max(1, round(span / 5))
            guides = list(range(min_int, max_int + 1, step))

            if guides[-1] != max_int:
                guides.append(max_int)

            return guides

        guides: list[float] = []
        steps = 5

        for index in range(steps + 1):
            value = min_value + ((max_value - min_value) * index / steps)
            guides.append(value)

        return guides


    def _format_axis_value(self, value: float) -> str:
        if abs(value - round(value)) < 0.001:
            return str(int(round(value)))

        return f"{value:.1f}"

class CumulativeInfectionsChartWidget(QWidget):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.title = title
        self.values: list[tuple[int, int]] = []
        self.setMinimumHeight(260)
        self.x_ticks: list[tuple[int, str]] = []

    def set_values(self, values: list[tuple[int, int]]) -> None:
        self.values = values
        self.update()

    def set_x_ticks(self, ticks: list[tuple[int, str]]) -> None:
        self.x_ticks = ticks
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(12, 12, -12, -12)
        painter.fillRect(rect, QColor("#ffffff"))

        painter.setPen(QPen(QColor("#111827")))
        title_font = QFont("Arial", 11)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(
            rect.left(),
            rect.top(),
            rect.width(),
            22,
            Qt.AlignmentFlag.AlignLeft,
            self.title,
        )

        chart_rect = rect.adjusted(54, 42, -22, -42)

        if not self.values:
            painter.setFont(QFont("Arial", 9))
            painter.setPen(QPen(QColor("#6b7280")))
            painter.drawText(chart_rect, Qt.AlignmentFlag.AlignCenter, "Sin datos")
            return

        min_slot = min(slot for slot, _ in self.values)
        max_slot = max(slot for slot, _ in self.values)
        max_value = max(value for _, value in self.values)

        if max_slot == min_slot:
            max_slot += 1

        if max_value <= 0:
            max_value = 1

        y_axis_max = max_value
        y_guides = self._build_y_guides(y_axis_max)

        # Guías horizontales y etiquetas Y
        painter.setFont(QFont("Arial", 8))

        for guide in y_guides:
            y = self._map_y(
                value=guide,
                max_value=y_axis_max,
                chart_rect=chart_rect,
            )

            painter.setPen(QPen(QColor("#e5e7eb"), 1))
            painter.drawLine(chart_rect.left(), y, chart_rect.right(), y)

            painter.setPen(QPen(QColor("#111827")))
            painter.drawText(
                rect.left(),
                y - 8,
                44,
                16,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                str(guide),
            )

        # Ejes
        painter.setPen(QPen(QColor("#9ca3af"), 1))
        painter.drawLine(chart_rect.bottomLeft(), chart_rect.bottomRight())
        painter.drawLine(chart_rect.bottomLeft(), chart_rect.topLeft())

        # Línea acumulada
        painter.setPen(QPen(QColor("#dc2626"), 2))

        previous_point = None

        for slot, value in self.values:
            x = self._map_x(
                slot=slot,
                min_slot=min_slot,
                max_slot=max_slot,
                chart_rect=chart_rect,
            )
            y = self._map_y(
                value=value,
                max_value=y_axis_max,
                chart_rect=chart_rect,
            )

            if previous_point is not None:
                painter.drawLine(previous_point[0], previous_point[1], x, y)

            previous_point = (x, y)

        # Puntos
        # painter.setBrush(QColor("#dc2626"))
        # painter.setPen(QPen(QColor("#991b1b"), 1))

        # for slot, value in self.values:
        #     x = self._map_x(
        #         slot=slot,
        #         min_slot=min_slot,
        #         max_slot=max_slot,
        #         chart_rect=chart_rect,
        #     )
        #     y = self._map_y(
        #         value=value,
        #         max_value=y_axis_max,
        #         chart_rect=chart_rect,
        #     )
        #     painter.drawEllipse(QRectF(x - 2.5, y - 2.5, 5, 5))

        # Marcas temporales del eje X
        painter.setFont(QFont("Arial", 8))

        for tick_slot, tick_label in self.x_ticks:
            if tick_slot < min_slot or tick_slot > max_slot:
                continue

            x = self._map_x(
                slot=tick_slot,
                min_slot=min_slot,
                max_slot=max_slot,
                chart_rect=chart_rect,
            )

            painter.setPen(QPen(QColor("#e5e7eb"), 1))
            painter.drawLine(x, chart_rect.top(), x, chart_rect.bottom())

            painter.setPen(QPen(QColor("#111827")))
            painter.drawText(
                x - 34,
                chart_rect.bottom() + 10,
                68,
                18,
                Qt.AlignmentFlag.AlignCenter,
                tick_label,
            )

        painter.drawText(
            chart_rect.left(),
            rect.bottom() - 18,
            chart_rect.width(),
            18,
            Qt.AlignmentFlag.AlignCenter,
            "Tiempo de simulación (slots)",
        )

        painter.save()
        painter.translate(rect.left() + 4, chart_rect.center().y() + 60)
        painter.rotate(-90)
        painter.drawText(
            0,
            0,
            130,
            18,
            Qt.AlignmentFlag.AlignCenter,
            "Infecciones acumuladas",
        )
        painter.restore()

    def _build_y_guides(self, max_value: int) -> list[int]:
        if max_value <= 0:
            return [0, 1]

        raw_guides = [
            0,
            round(max_value / 3),
            round((max_value * 2) / 3),
            max_value,
        ]

        guides: list[int] = []

        for value in raw_guides:
            value = int(value)

            if value not in guides:
                guides.append(value)

        if guides[-1] != max_value:
            guides.append(max_value)

        return guides

    def _map_x(
        self,
        slot: int,
        min_slot: int,
        max_slot: int,
        chart_rect,
    ) -> float:
        return chart_rect.left() + (
            (slot - min_slot) / (max_slot - min_slot)
        ) * chart_rect.width()

    def _map_y(
        self,
        value: int,
        max_value: int,
        chart_rect,
    ) -> float:
        bottom_padding_ratio = 0.03

        usable_height = chart_rect.height() * (1.0 - bottom_padding_ratio)
        bottom = chart_rect.bottom() - (chart_rect.height() * bottom_padding_ratio)

        return bottom - (value / max_value) * usable_height

class BarChartWidget(QWidget):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.title = title
        self.values: list[tuple[str, float]] = []
        self.setMinimumHeight(240)

    def set_values(self, values: list[tuple[str, float]]) -> None:
        self.values = values
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(12, 12, -12, -12)
        painter.fillRect(rect, QColor("#ffffff"))

        painter.setPen(QPen(QColor("#111827")))
        title_font = QFont("Arial", 11)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(rect.left(), rect.top(), rect.width(), 22, Qt.AlignmentFlag.AlignLeft, self.title)

        chart_rect = rect.adjusted(150, 38, -18, -18)

        if not self.values:
            painter.setFont(QFont("Arial", 9))
            painter.setPen(QPen(QColor("#6b7280")))
            painter.drawText(chart_rect, Qt.AlignmentFlag.AlignCenter, "Sin datos")
            return

        max_value = max(value for _, value in self.values) or 1
        bar_height = max(14, min(24, chart_rect.height() // max(1, len(self.values)) - 6))

        painter.setFont(QFont("Arial", 8))

        y = chart_rect.top()

        for label, value in self.values:
            usable_width = chart_rect.width()
            bar_width = int((value / max_value) * usable_width)

            painter.setPen(QPen(QColor("#111827")))
            painter.drawText(
                rect.left(),
                y,
                138,
                bar_height,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                label[:26],
            )

            painter.fillRect(
                QRectF(chart_rect.left(), y, bar_width, bar_height),
                QColor("#2563eb"),
            )

            painter.setPen(QPen(QColor("#111827")))
            painter.drawText(
                chart_rect.left() + bar_width + 6,
                y,
                60,
                bar_height,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                f"{value:.2f}" if isinstance(value, float) and not value.is_integer() else str(int(value)),
            )

            y += bar_height + 6

class VerticalBarChartWidget(QWidget):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.title = title
        self.values: list[tuple[str, float]] = []
        self.setMinimumHeight(260)

    def set_values(self, values: list[tuple[str, float]]) -> None:
        self.values = values
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(12, 12, -12, -12)
        painter.fillRect(rect, QColor("#ffffff"))

        painter.setPen(QPen(QColor("#111827")))
        title_font = QFont("Arial", 11)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(
            rect.left(),
            rect.top(),
            rect.width(),
            22,
            Qt.AlignmentFlag.AlignLeft,
            self.title,
        )

        chart_rect = rect.adjusted(46, 40, -18, -46)

        if not self.values:
            painter.setFont(QFont("Arial", 9))
            painter.setPen(QPen(QColor("#6b7280")))
            painter.drawText(chart_rect, Qt.AlignmentFlag.AlignCenter, "Sin datos")
            return

        max_value = max(value for _, value in self.values) or 1.0

        painter.setPen(QPen(QColor("#d1d5db"), 1))
        painter.drawLine(chart_rect.bottomLeft(), chart_rect.bottomRight())
        painter.drawLine(chart_rect.bottomLeft(), chart_rect.topLeft())

        guide_values = self._build_y_guides(max_value)
        painter.setFont(QFont("Arial", 8))

        for guide in guide_values:
            y = chart_rect.bottom() - (guide / max_value) * chart_rect.height()

            painter.setPen(QPen(QColor("#e5e7eb"), 1))
            painter.drawLine(chart_rect.left(), y, chart_rect.right(), y)

            painter.setPen(QPen(QColor("#111827")))
            painter.drawText(
                rect.left(),
                y - 8,
                38,
                16,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                self._format_value(guide),
            )

        count = len(self.values)
        slot_width = chart_rect.width() / max(1, count)
        bar_width = min(44, slot_width * 0.62)

        for index, (label, value) in enumerate(self.values):
            x_center = chart_rect.left() + slot_width * index + slot_width / 2
            bar_height = (value / max_value) * chart_rect.height()

            painter.fillRect(
                QRectF(
                    x_center - bar_width / 2,
                    chart_rect.bottom() - bar_height,
                    bar_width,
                    bar_height,
                ),
                QColor("#2563eb"),
            )

            painter.setPen(QPen(QColor("#111827")))
            painter.setFont(QFont("Arial", 8))

            painter.drawText(
                QRectF(
                    x_center - slot_width / 2,
                    chart_rect.bottom() + 8,
                    slot_width,
                    18,
                ),
                Qt.AlignmentFlag.AlignCenter,
                label[:10],
            )

            if value > 0:
                painter.drawText(
                    QRectF(
                        x_center - slot_width / 2,
                        chart_rect.bottom() - bar_height - 18,
                        slot_width,
                        16,
                    ),
                    Qt.AlignmentFlag.AlignCenter,
                    self._format_value(value),
                )

    def _build_y_guides(self, max_value: float) -> list[float]:
        if max_value <= 0:
            return [0.0, 1.0]

        return [
            0.0,
            max_value / 3,
            (max_value * 2) / 3,
            max_value,
        ]

    def _format_value(self, value: float) -> str:
        if abs(value - round(value)) < 0.001:
            return str(int(round(value)))

        return f"{value:.2f}"

class HeatmapMatrixWidget(QWidget):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.title = title
        self.labels: list[str] = []
        self.matrix: list[list[int]] = []
        self.setMinimumHeight(360)
        self.value_suffix = ""

    def set_matrix(self, labels, matrix, value_suffix: str = "") -> None:
        self.labels = labels
        self.matrix = matrix
        self.value_suffix = value_suffix
        self.setMinimumHeight(max(360, 120 + len(labels) * 28))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(12, 12, -12, -12)
        painter.fillRect(rect, QColor("#ffffff"))

        painter.setPen(QPen(QColor("#111827")))
        title_font = QFont("Arial", 11)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(
            rect.left(),
            rect.top(),
            rect.width(),
            22,
            Qt.AlignmentFlag.AlignLeft,
            self.title,
        )

        if not self.labels or not self.matrix:
            painter.setFont(QFont("Arial", 9))
            painter.setPen(QPen(QColor("#6b7280")))
            painter.drawText(
                rect.adjusted(0, 34, 0, 0),
                Qt.AlignmentFlag.AlignCenter,
                "Sin contagios entre grupos distintos",
            )
            return

        label_width = 120
        top_label_height = 62
        cell_size = min(
            32,
            max(
                18,
                int((rect.width() - label_width - 20) / max(1, len(self.labels))),
            ),
        )

        matrix_left = rect.left() + label_width
        matrix_top = rect.top() + top_label_height

        max_value = max(
            value
            for row in self.matrix
            for value in row
        ) or 1

        painter.setFont(QFont("Arial", 7))

        # Etiquetas columnas
        for col, label in enumerate(self.labels):
            x = matrix_left + col * cell_size

            painter.save()
            painter.translate(x + cell_size / 2, rect.top() + top_label_height - 6)
            painter.rotate(-45)
            painter.setPen(QPen(QColor("#111827")))
            painter.drawText(
                0,
                0,
                90,
                14,
                Qt.AlignmentFlag.AlignLeft,
                label[:18],
            )
            painter.restore()

        # Etiquetas filas y celdas
        for row_index, row_label in enumerate(self.labels):
            y = matrix_top + row_index * cell_size

            painter.setPen(QPen(QColor("#111827")))
            painter.drawText(
                rect.left(),
                y,
                label_width - 6,
                cell_size,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                row_label[:22],
            )

            for col_index, value in enumerate(self.matrix[row_index]):
                x = matrix_left + col_index * cell_size
                color = self._color_for_value(value, max_value)

                painter.fillRect(
                    QRectF(x, y, cell_size - 1, cell_size - 1),
                    color,
                )

                if value > 0:
                    painter.setPen(QPen(QColor("#111827")))
                    painter.drawText(
                        QRectF(x, y, cell_size - 1, cell_size - 1),
                        Qt.AlignmentFlag.AlignCenter,
                        self._format_value(value),
                    )

        painter.setPen(QPen(QColor("#6b7280")))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(
            matrix_left,
            matrix_top + len(self.labels) * cell_size + 12,
            rect.width() - label_width,
            18,
            Qt.AlignmentFlag.AlignLeft,
            "Filas: grupo origen · Columnas: grupo destino",
        )

    def _format_value(self, value: float) -> str:
        formatted = str(int(round(value))) if abs(value - round(value)) < 0.001 else f"{value:.1f}"
        return f"{formatted}{self.value_suffix}"

    def _color_for_value(self, value: int, max_value: int) -> QColor:
        if value <= 0:
            return QColor("#f3f4f6")

        ratio = min(1.0, value / max_value)

        red = 255
        green = int(245 - ratio * 170)
        blue = int(235 - ratio * 190)

        return QColor(red, green, blue)
    
class MetricGraphView(QGraphicsView):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.scene_obj = QGraphicsScene(self)
        self.setScene(self.scene_obj)

        self.scene_obj.setSceneRect(-5000, -5000, 10000, 10000)

        self.nodes_by_uuid = {}
        self.node_positions = {}

        self.min_zoom = 0.05
        self.max_zoom = 4.0

        self._panning = False
        self._last_mouse_pos = QPoint()

        self.setMinimumHeight(320)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def render_metric_graph(
        self,
        graph_data: dict,
        metric_by_uuid: dict[str, float],
    ) -> None:
        for node_uuid, item in self.nodes_by_uuid.items():
            self.node_positions[node_uuid] = (
                item.scenePos().x(),
                item.scenePos().y(),
            )

        self.scene_obj.clear()
        self.nodes_by_uuid.clear()

        nodes = graph_data.get("nodes", [])
        edges = graph_data.get("edges", [])

        default_positions = self._calculate_standard_layout(nodes, edges)

        max_space_metric = 0.0
        max_group_metric = 0.0

        for node in nodes:
            node_uuid = node["uuid"]
            value = metric_by_uuid.get(node_uuid)

            if value is None:
                continue

            node_type = node.get("type")

            if node_type == "space":
                max_space_metric = max(max_space_metric, value)
            elif node_type in {"group", "spacegroup"}:
                max_group_metric = max(max_group_metric, value)

        for node in nodes:
            item = create_graph_node_item(
                node_uuid=node["uuid"],
                name=node["name"],
                node_type=node["type"],
                size=node.get("size", 100),
                expanded=node.get("expanded", None),
            )

            node_type = node.get("type")

            if node_type == "space":
                max_value = max_space_metric
            elif node_type in {"group", "spacegroup"}:
                max_value = max_group_metric
            else:
                max_value = 0.0

            self._apply_metric_color(
                item=item,
                value=metric_by_uuid.get(node["uuid"]),
                max_value=max_value,
            )

            x, y = self.node_positions.get(
                node["uuid"],
                default_positions.get(node["uuid"], (0, 0)),
            )

            item.setPos(x, y)

            self.scene_obj.addItem(item)
            self.nodes_by_uuid[node["uuid"]] = item

        for edge in edges:
            source = self.nodes_by_uuid.get(edge["source"])
            target = self.nodes_by_uuid.get(edge["target"])

            if source is None or target is None:
                continue

            edge_item = GraphEdgeItem(source, target)
            self.scene_obj.addItem(edge_item)

            source.add_edge(edge_item)
            target.add_edge(edge_item)

    def _apply_metric_color(
        self,
        item,
        value: float,
        max_value: float,
    ) -> None:
        if value is None:
            return

        color = _metric_color(value, max_value)

        if hasattr(item, "fill_color"):
            item.fill_color = color.name()

        item.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.MiddleButton:
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
            if current_scale < self.max_zoom:
                factor = min(zoom_in_factor, self.max_zoom / current_scale)
                self.scale(factor, factor)
        else:
            if current_scale > self.min_zoom:
                factor = max(zoom_out_factor, self.min_zoom / current_scale)
                self.scale(factor, factor)

        event.accept()

    def _calculate_standard_layout(self, nodes: list[dict], edges: list[dict]):
        from frontend.graph_view import GraphView

        helper = GraphView()
        return helper._calculate_standard_layout(nodes, edges)

class ColorScaleLegendWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.left_label = "0"
        self.right_label = "Máx."
        self.setMinimumHeight(46)
        self.setMaximumHeight(54)

    def set_labels(self, left_label: str, right_label: str) -> None:
        self.left_label = left_label
        self.right_label = right_label
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(14, 10, -14, -18)
        steps = max(1, rect.width())

        for index in range(int(steps)):
            ratio = index / max(1, steps - 1)
            color = _metric_color(ratio, 1.0)

            x = rect.left() + index
            painter.setPen(QPen(color))
            painter.drawLine(x, rect.top(), x, rect.bottom())

        painter.setPen(QPen(QColor("#111827")))
        painter.drawRect(rect)

        painter.setFont(QFont("Arial", 8))

        painter.drawText(
            rect.left(),
            rect.bottom() + 4,
            80,
            14,
            Qt.AlignmentFlag.AlignLeft,
            self.left_label,
        )

        painter.drawText(
            rect.right() - 80,
            rect.bottom() + 4,
            80,
            14,
            Qt.AlignmentFlag.AlignRight,
            self.right_label,
        )

class CollapsibleSection(QWidget):
    def __init__(self, title: str, expanded: bool = True, parent=None) -> None:
        super().__init__(parent)

        self.expanded = expanded

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.header = QWidget()
        header_layout = QHBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.toggle_button = QPushButton("▼" if expanded else "▶")
        self.toggle_button.setFixedWidth(34)
        self.toggle_button.clicked.connect(self.toggle)

        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.toggle_button)

        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(10)

        layout.addWidget(self.header)
        layout.addWidget(self.content)

        self.content.setVisible(self.expanded)

    def toggle(self) -> None:
        self.expanded = not self.expanded
        self.content.setVisible(self.expanded)
        self.toggle_button.setText("▼" if self.expanded else "▶")

class BandLineChartWidget(QWidget):
    def __init__(self, title: str, parent=None) -> None:
        super().__init__(parent)
        self.title = title
        self.series: dict[str, dict[str, list[tuple[int, float]]]] = {}
        self.setMinimumHeight(270)

    def set_series(self, series: dict[str, dict[str, list[tuple[int, float]]]]) -> None:
        self.series = series
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(12, 12, -12, -12)
        painter.fillRect(rect, QColor("#ffffff"))

        painter.setPen(QPen(QColor("#111827")))
        title_font = QFont("Arial", 11)
        title_font.setBold(True)
        painter.setFont(title_font)
        painter.drawText(rect.left(), rect.top(), rect.width(), 22, Qt.AlignmentFlag.AlignLeft, self.title)

        chart_rect = rect.adjusted(52, 40, -18, -38)

        all_points = []
        for data in self.series.values():
            all_points.extend(data.get("min", []))
            all_points.extend(data.get("max", []))
            all_points.extend(data.get("mean", []))

        if not all_points:
            painter.setFont(QFont("Arial", 9))
            painter.setPen(QPen(QColor("#6b7280")))
            painter.drawText(chart_rect, Qt.AlignmentFlag.AlignCenter, "Sin datos")
            return

        min_x = min(x for x, _ in all_points)
        max_x = max(x for x, _ in all_points)
        max_y = max(y for _, y in all_points)
        min_y = 0.0

        if max_x == min_x:
            max_x += 1

        if max_y <= 0:
            max_y = 1.0

        colors = {
            "Susceptibles": QColor("#2563eb"),
            "Expuestos": QColor("#f59e0b"),
            "Infecciosos": QColor("#dc2626"),
            "Recuperados": QColor("#16a34a"),
            "Infecciones": QColor("#dc2626"),
        }

        self._draw_guides(painter, rect, chart_rect, min_x, max_x, min_y, max_y)

        for name, data in self.series.items():
            color = colors.get(name, QColor("#374151"))

            mean_points = data.get("mean", [])
            min_points = data.get("min", [])
            max_points = data.get("max", [])

            if mean_points and min_points and max_points:
                self._draw_band(
                    painter,
                    chart_rect,
                    min_x,
                    max_x,
                    min_y,
                    max_y,
                    min_points,
                    max_points,
                    color,
                )

            self._draw_line(
                painter,
                chart_rect,
                min_x,
                max_x,
                min_y,
                max_y,
                mean_points,
                color,
            )

        self._draw_legend(painter, chart_rect, colors)

    def _draw_guides(self, painter, rect, chart_rect, min_x, max_x, min_y, max_y) -> None:
        y_guides = [0.0, max_y / 3, (max_y * 2) / 3, max_y]
        x_guides = self._build_x_guides(min_x, max_x)

        painter.setFont(QFont("Arial", 8))

        for guide in y_guides:
            y = chart_rect.bottom() - ((guide - min_y) / (max_y - min_y)) * chart_rect.height()

            painter.setPen(QPen(QColor("#e5e7eb"), 1))
            painter.drawLine(chart_rect.left(), y, chart_rect.right(), y)

            painter.setPen(QPen(QColor("#111827")))
            painter.drawText(
                rect.left(),
                y - 8,
                42,
                16,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                self._format_value(guide),
            )

        for guide in x_guides:
            x = chart_rect.left() + ((guide - min_x) / (max_x - min_x)) * chart_rect.width()

            painter.setPen(QPen(QColor("#f3f4f6"), 1))
            painter.drawLine(x, chart_rect.top(), x, chart_rect.bottom())

            painter.setPen(QPen(QColor("#111827")))
            painter.drawText(
                x - 28,
                chart_rect.bottom() + 8,
                56,
                16,
                Qt.AlignmentFlag.AlignCenter,
                self._format_value(guide),
            )

        painter.setPen(QPen(QColor("#d1d5db"), 1))
        painter.drawLine(chart_rect.bottomLeft(), chart_rect.bottomRight())
        painter.drawLine(chart_rect.bottomLeft(), chart_rect.topLeft())

    def _draw_band(
        self,
        painter,
        chart_rect,
        min_x,
        max_x,
        min_y,
        max_y,
        min_points,
        max_points,
        color: QColor,
    ) -> None:
        if len(min_points) < 2 or len(max_points) < 2:
            return

        path = QPainterPath()

        first_x, first_y = self._map_point(max_points[0], chart_rect, min_x, max_x, min_y, max_y)
        path.moveTo(first_x, first_y)

        for point in max_points[1:]:
            x, y = self._map_point(point, chart_rect, min_x, max_x, min_y, max_y)
            path.lineTo(x, y)

        for point in reversed(min_points):
            x, y = self._map_point(point, chart_rect, min_x, max_x, min_y, max_y)
            path.lineTo(x, y)

        path.closeSubpath()

        band_color = QColor(color)
        band_color.setAlpha(45)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(band_color))
        painter.drawPath(path)

    def _draw_line(
        self,
        painter,
        chart_rect,
        min_x,
        max_x,
        min_y,
        max_y,
        points,
        color: QColor,
    ) -> None:
        if len(points) < 2:
            return

        painter.setPen(QPen(color, 2))
        previous = None

        for point in points:
            x, y = self._map_point(point, chart_rect, min_x, max_x, min_y, max_y)

            if previous is not None:
                painter.drawLine(previous[0], previous[1], x, y)

            previous = (x, y)

    def _draw_legend(self, painter, chart_rect, colors: dict[str, QColor]) -> None:
        legend_x = chart_rect.left()
        legend_y = chart_rect.bottom() + 24

        painter.setFont(QFont("Arial", 8))

        for name in self.series.keys():
            color = colors.get(name, QColor("#374151"))
            painter.setPen(QPen(color, 8))
            painter.drawPoint(legend_x, legend_y + 6)
            painter.setPen(QPen(QColor("#111827")))
            painter.drawText(legend_x + 10, legend_y, 105, 16, Qt.AlignmentFlag.AlignLeft, name)
            legend_x += 112

    def _map_point(self, point, chart_rect, min_x, max_x, min_y, max_y) -> tuple[float, float]:
        x_value, y_value = point

        x = chart_rect.left() + ((x_value - min_x) / (max_x - min_x)) * chart_rect.width()
        y = chart_rect.bottom() - ((y_value - min_y) / (max_y - min_y)) * chart_rect.height()

        return x, y

    def _build_x_guides(self, min_value: float, max_value: float) -> list[float]:
        min_int = int(round(min_value))
        max_int = int(round(max_value))

        if abs(min_value - min_int) < 0.001 and abs(max_value - max_int) < 0.001:
            span = max_int - min_int

            if span <= 8:
                return list(range(min_int, max_int + 1))

            step = max(1, round(span / 5))
            guides = list(range(min_int, max_int + 1, step))

            if guides[-1] != max_int:
                guides.append(max_int)

            return guides

        return [
            min_value + ((max_value - min_value) * index / 5)
            for index in range(6)
        ]

    def _format_value(self, value: float) -> str:
        if abs(value - round(value)) < 0.001:
            return str(int(round(value)))

        return f"{value:.1f}"

class VisualizationPage(QWidget):
    """
    Página de visualización estática/análisis.

    Esta página no reproduce la simulación animada.
    Sirve para cargar resultados guardados y mostrar análisis:
    - información de facultad;
    - curva SEIR;
    - rankings;
    - contagios por espacios;
    - relaciones entre grupos.
    """

    def __init__(
        self,
        stacked_widget,
        simulation_controller,
        menu_page_index: int = 0,
    ) -> None:
        super().__init__()

        self.stacked_widget = stacked_widget
        self.simulation_controller = simulation_controller
        self.menu_page_index = menu_page_index

        self.result_folders: list[Path] = []
        self.current_result_folder: Optional[Path] = None

        self.current_space_summary_rows: list[dict] = []
        self.current_space_occupancy_rows: list[dict] = []
        self.current_space_frequency_metric: dict[str, float] = {}
        self.current_group_transmission_rows: list[dict] = []
        self.current_group_transmission_frequency_rows: list[dict] = []

        self.batch_section_expanded = True

        self._build_ui()

    def _build_ui(self) -> None:
        self.setStyleSheet("""
            QWidget {
                color: #111827;
            }

            QLabel {
                color: #111827;
            }

            QTextEdit {
                color: #111827;
                background-color: #ffffff;
            }

            QComboBox {
                color: #111827;
                background-color: #ffffff;
            }

            QPushButton {
                color: #111827;
            }

            QGroupBox {
                color: #111827;
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 14, 16, 16)
        main_layout.setSpacing(10)

        # -------------------------
        # Cabecera
        # -------------------------

        header_layout = QHBoxLayout()

        self.back_button = QPushButton("← Volver")
        self.back_button.setFixedWidth(120)
        self.back_button.clicked.connect(self.go_back)

        title = QLabel("Visualización de resultados")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold;")

        self.refresh_button = QPushButton("Actualizar")
        self.refresh_button.setFixedWidth(120)
        self.refresh_button.clicked.connect(self.load_page)

        header_layout.addWidget(self.back_button)
        header_layout.addStretch()
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_button)

        main_layout.addLayout(header_layout)

        self.active_faculty_label = QLabel()
        self.active_faculty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.active_faculty_label.setStyleSheet("font-size: 13px; color: #555;")
        self.active_faculty_label.setWordWrap(False)
        self.active_faculty_label.setMaximumHeight(24)
        self.active_faculty_label.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed,
        )
        main_layout.addWidget(self.active_faculty_label)

        # -------------------------
        # Splitter principal
        # -------------------------

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setChildrenCollapsible(False)

        # ========================================================
        # Panel izquierdo: facultad
        # ========================================================

        self.faculty_panel = QFrame()
        self.faculty_panel.setMinimumWidth(360)
        self.faculty_panel.setStyleSheet("""
            QFrame {
                background-color: #f5f7fa;
                border: 1px solid #d0d7de;
                border-radius: 8px;
            }
        """)

        faculty_layout = QVBoxLayout(self.faculty_panel)
        faculty_layout.setContentsMargins(12, 12, 12, 12)
        faculty_layout.setSpacing(8)

        faculty_title = QLabel("Análisis de facultad")
        faculty_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        faculty_layout.addWidget(faculty_title)

        self.faculty_summary_text = QTextEdit()
        self.faculty_summary_text.setReadOnly(True)
        self.faculty_summary_text.setMaximumHeight(140)
        faculty_layout.addWidget(self.faculty_summary_text)

        self.faculty_usage_chart = VerticalBarChartWidget(
            "Espacios más usados por horas semanales"
        )
        faculty_layout.addWidget(self.faculty_usage_chart)

        faculty_layout.addWidget(QLabel("Grafo coloreado por uso semanal"))

        self.faculty_usage_graph = MetricGraphView()
        faculty_layout.addWidget(self.faculty_usage_graph)

        self.faculty_usage_legend = ColorScaleLegendWidget()
        faculty_layout.addWidget(self.faculty_usage_legend)

        unused_title = QLabel("Espacios sin uso en horarios")
        unused_title.setStyleSheet("font-size: 13px; font-weight: bold;")
        faculty_layout.addWidget(unused_title)

        self.unused_spaces_text = QTextEdit()
        self.unused_spaces_text.setReadOnly(True)
        self.unused_spaces_text.setMaximumHeight(150)
        faculty_layout.addWidget(self.unused_spaces_text)

        # ========================================================
        # Panel derecho: resultados
        # ========================================================

        self.results_panel = QFrame()
        self.results_panel.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #d0d7de;
                border-radius: 8px;
            }
        """)

        results_layout = QVBoxLayout(self.results_panel)
        results_layout.setContentsMargins(12, 12, 12, 12)
        results_layout.setSpacing(8)

        results_header = QHBoxLayout()

        results_title = QLabel("Resultados de simulación")
        results_title.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.result_selector = QComboBox()
        self.result_selector.currentIndexChanged.connect(self._on_result_selected)

        results_header.addWidget(results_title)
        results_header.addStretch()
        results_header.addWidget(QLabel("Simulación:"))
        results_header.addWidget(self.result_selector)

        results_layout.addLayout(results_header)

        self.result_summary_text = QTextEdit()
        self.result_summary_text.setReadOnly(True)
        self.result_summary_text.setMaximumHeight(190)
        results_layout.addWidget(self.result_summary_text)

        # -------------------------
        # Scroll de visualizaciones
        # -------------------------

        self.charts_scroll = QScrollArea()
        self.charts_scroll.setWidgetResizable(True)

        self.charts_container = QWidget()
        self.charts_layout = QVBoxLayout(self.charts_container)
        self.charts_layout.setContentsMargins(6, 6, 6, 6)
        self.charts_layout.setSpacing(12)

        # -------------------------
        # Widgets de gráficas
        # -------------------------

        self.seir_chart = LineChartWidget("Curva SEIR global")

        self.new_infections_chart = CumulativeInfectionsChartWidget(
            "Infecciones acumuladas por slot"
        )

        self.space_infections_chart = VerticalBarChartWidget(
            "Top espacios con más contagios"
        )

        self.batch_seir_band_chart = BandLineChartWidget(
            "Curva SEIR media con rango p25-p75"
        )

        self.batch_cumulative_band_chart = BandLineChartWidget(
            "Infecciones acumuladas medias con rango p25-p75"
        )

        self.space_risk_chart = VerticalBarChartWidget(
            "Top espacios por contagios / 100 presentes"
        )

        self.space_frequency_chart = VerticalBarChartWidget(
            "Top espacios recurrentes (% runs con contagios)"
        )

        self.simulation_graph_metric_selector = QComboBox()
        self.simulation_graph_metric_selector.addItem(
            "Contagios absolutos",
            "infections",
        )
        self.simulation_graph_metric_selector.addItem(
            "Riesgo relativo",
            "risk",
        )
        self.simulation_graph_metric_selector.addItem(
            "Frecuencia de contagio",
            "frequency",
        )
        self.simulation_graph_metric_selector.currentIndexChanged.connect(
            self._refresh_simulation_metric_graph
        )

        self.simulation_metric_graph = MetricGraphView()
        self.simulation_metric_legend = ColorScaleLegendWidget()

        self.source_groups_chart = VerticalBarChartWidget(
            "Grupos que más contagian a otros grupos"
        )

        self.target_groups_chart = VerticalBarChartWidget(
            "Grupos que más reciben contagios de otros grupos"
        )

        self.intergroup_spaces_chart = VerticalBarChartWidget(
            "Espacios con más contagios entre grupos"
        )

        self.transmission_matrix = HeatmapMatrixWidget("")
        self.group_matrix_metric_selector = QComboBox()
        self.group_matrix_metric_selector.addItem("Media de contagios", "mean")
        self.group_matrix_metric_selector.addItem("Frecuencia de transmisión", "frequency")
        self.group_matrix_metric_selector.currentIndexChanged.connect(
            self._refresh_group_transmission_matrix
        )

        self.daily_infections_chart = VerticalBarChartWidget(
            "Contagios por día de la semana"
        )

        self.daily_presence_chart = VerticalBarChartWidget(
            "Presencia media por día de la semana"
        )

        self.daily_risk_chart = VerticalBarChartWidget(
            "Riesgo por día de la semana / 100 presentes"
        )

        self.weekday_frequency_chart = VerticalBarChartWidget(
            "Días recurrentemente problemáticos (% runs en top 2 de riesgo)"
        )

        self.batch_total_infections_chart = LineChartWidget(
            "Infecciones totales por ejecución"
        )

        self.batch_peak_chart = LineChartWidget(
            "Pico de infecciosos por ejecución"
        )

        self.batch_distribution_chart = VerticalBarChartWidget(
            "Distribución de infecciones totales"
        )

        # -------------------------
        # Secciones plegables
        # -------------------------

        self.general_section = CollapsibleSection(
            "Información general",
            expanded=True,
        )

        self.spaces_section = CollapsibleSection(
            "Estudio de espacios",
            expanded=True,
        )

        self.groups_section = CollapsibleSection(
            "Estudio de grupos",
            expanded=False,
        )

        self.weekdays_section = CollapsibleSection(
            "Estudio por días de la semana",
            expanded=False,
        )

        self.batch_section = CollapsibleSection(
            "Análisis de batch",
            expanded=True,
        )

        # Información general
        self.general_section.content_layout.addWidget(self.seir_chart)
        self.general_section.content_layout.addWidget(self.new_infections_chart)
        self.general_section.content_layout.addWidget(self.batch_seir_band_chart)
        self.general_section.content_layout.addWidget(self.batch_cumulative_band_chart)

        self.batch_seir_band_chart.setVisible(False)
        self.batch_cumulative_band_chart.setVisible(False)

        # Estudio de espacios
        self.spaces_section.content_layout.addWidget(self.space_infections_chart)
        self.spaces_section.content_layout.addWidget(self.space_risk_chart)
        self.spaces_section.content_layout.addWidget(self.space_frequency_chart)

        simulation_graph_header = QHBoxLayout()
        simulation_graph_title = QLabel("Grafo espacial de la simulación")
        simulation_graph_title.setStyleSheet("font-size: 14px; font-weight: bold;")

        simulation_graph_header.addWidget(simulation_graph_title)
        simulation_graph_header.addStretch()
        simulation_graph_header.addWidget(QLabel("Métrica:"))
        simulation_graph_header.addWidget(self.simulation_graph_metric_selector)

        self.spaces_section.content_layout.addLayout(simulation_graph_header)
        self.spaces_section.content_layout.addWidget(self.simulation_metric_graph)
        self.spaces_section.content_layout.addWidget(self.simulation_metric_legend)

        # Estudio de grupos
        self.groups_section.content_layout.addWidget(self.source_groups_chart)
        self.groups_section.content_layout.addWidget(self.target_groups_chart)
        self.groups_section.content_layout.addWidget(self.intergroup_spaces_chart)
        group_matrix_header = QHBoxLayout()
        group_matrix_title = QLabel("Matriz de transmisión entre grupos")
        group_matrix_title.setStyleSheet("font-size: 14px; font-weight: bold;")

        group_matrix_header.addWidget(group_matrix_title)
        group_matrix_header.addStretch()
        group_matrix_header.addWidget(QLabel("Métrica:"))
        group_matrix_header.addWidget(self.group_matrix_metric_selector)

        self.groups_section.content_layout.addLayout(group_matrix_header)
        self.groups_section.content_layout.addWidget(self.transmission_matrix)

        # Estudio por días de la semana
        self.weekdays_section.content_layout.addWidget(self.daily_infections_chart)
        self.weekdays_section.content_layout.addWidget(self.daily_presence_chart)
        self.weekdays_section.content_layout.addWidget(self.daily_risk_chart)
        self.weekdays_section.content_layout.addWidget(self.weekday_frequency_chart)

        # Batch
        self.batch_section.content_layout.addWidget(self.batch_total_infections_chart)
        self.batch_section.content_layout.addWidget(self.batch_peak_chart)
        self.batch_section.content_layout.addWidget(self.batch_distribution_chart)

        # Añadir secciones al scroll
        self.charts_layout.addWidget(self.general_section)
        self.charts_layout.addWidget(self.spaces_section)
        self.charts_layout.addWidget(self.groups_section)
        self.charts_layout.addWidget(self.weekdays_section)
        self.charts_layout.addWidget(self.batch_section)
        self.charts_layout.addStretch()

        self.batch_section.setVisible(False)

        self.charts_scroll.setWidget(self.charts_container)
        results_layout.addWidget(self.charts_scroll)

        # -------------------------
        # Montaje final
        # -------------------------

        self.faculty_scroll = QScrollArea()
        self.faculty_scroll.setWidgetResizable(True)
        self.faculty_scroll.setWidget(self.faculty_panel)
        self.faculty_scroll.setMinimumWidth(360)
        self.faculty_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.faculty_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self.splitter.addWidget(self.faculty_scroll)
        self.splitter.addWidget(self.results_panel)
        self.splitter.setSizes([390, 810])
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        main_layout.addWidget(self.splitter)

        self.setLayout(main_layout)

    def _set_result_sections_for_type(self, result_type: str) -> None:
        is_batch = result_type == "simulation_batch"

        self.general_section.setVisible(True)
        self.spaces_section.setVisible(True)
        self.groups_section.setVisible(True)
        self.weekdays_section.setVisible(True)
        self.batch_section.setVisible(is_batch)

        self.seir_chart.setVisible(not is_batch)
        self.new_infections_chart.setVisible(not is_batch)

        self.batch_seir_band_chart.setVisible(is_batch)
        self.batch_cumulative_band_chart.setVisible(is_batch)
        self.space_frequency_chart.setVisible(is_batch)
        self.weekday_frequency_chart.setVisible(is_batch)

    def _toggle_batch_section(self) -> None:
        self.batch_section_expanded = not self.batch_section_expanded
        self._set_batch_charts_visible(True)

    def _read_csv_rows(self, path: Path) -> list[dict]:
        if not path.exists():
            return []

        try:
            with path.open("r", encoding="utf-8", newline="") as file:
                return list(csv.DictReader(file))
        except Exception:
            return []

    def _percentile(
        self,
        values: list[float],
        percentile: float,
    ) -> float:
        if not values:
            return 0.0

        sorted_values = sorted(values)

        if len(sorted_values) == 1:
            return sorted_values[0]

        position = (len(sorted_values) - 1) * percentile
        lower_index = int(position)
        upper_index = min(lower_index + 1, len(sorted_values) - 1)

        weight = position - lower_index

        return (
            sorted_values[lower_index] * (1.0 - weight)
            + sorted_values[upper_index] * weight
        )
        
    def _build_time_axis_ticks(self, rows: list[dict]) -> list[tuple[int, str]]:
        day_start_slots: dict[int, int] = {}

        for row in rows:
            day_index = _safe_int(row.get("day_index"))
            slot = _safe_int(row.get("slot"))

            if day_index not in day_start_slots:
                day_start_slots[day_index] = slot
            else:
                day_start_slots[day_index] = min(day_start_slots[day_index], slot)

        if not day_start_slots:
            return []

        max_day = max(day_start_slots.keys())

        ticks: list[tuple[int, str]] = []

        if max_day < 14:
            for day_index in sorted(day_start_slots.keys()):
                ticks.append(
                    (
                        day_start_slots[day_index],
                        f"Día {day_index + 1}",
                    )
                )
        else:
            for day_index in sorted(day_start_slots.keys()):
                if day_index % 7 != 0:
                    continue

                week_number = (day_index // 7) + 1
                ticks.append(
                    (
                        day_start_slots[day_index],
                        f"Sem.{week_number}",
                    )
                )

        return ticks
    
    def _build_space_graph_data(self) -> dict:
        faculty = self.simulation_controller.faculty
        root = faculty.get_root()

        nodes: list[dict] = []
        edges: list[dict] = []

        def is_space_tree_node(node) -> bool:
            node_type = node.__class__.__name__.lower()
            return node_type in {"root", "spacegroup", "space"}

        def node_type_for(node) -> str:
            node_type = node.__class__.__name__.lower()

            if node_type == "root":
                return "root"

            if node_type == "spacegroup":
                return "spacegroup"

            return "space"

        def visit(node_uuid: str) -> None:
            node = faculty.find_node(node_uuid)

            if node is None or not is_space_tree_node(node):
                return

            node_uuid = node.uuid

            nodes.append(
                {
                    "uuid": node_uuid,
                    "name": node.name,
                    "type": node_type_for(node),
                    "size": max(90.0, float(getattr(node, "size", 1.0)) * 100.0),
                    "expanded": getattr(node, "expanded", None),
                }
            )

            if hasattr(node, "children_uuids"):
                for child_uuid in node.children_uuids:
                    child = faculty.find_node(child_uuid)

                    if child is None or not is_space_tree_node(child):
                        continue

                    edges.append(
                        {
                            "source": node.uuid,
                            "target": child.uuid,
                        }
                    )

                    visit(child.uuid)

        visit(root.uuid)

        return {
            "nodes": nodes,
            "edges": edges,
        }


    def _aggregate_usage_for_space_groups(
        self,
        usage_by_space: dict[str, float],
    ) -> dict[str, float]:
        faculty = self.simulation_controller.faculty
        root = faculty.get_root()

        metric_by_uuid: dict[str, float] = dict(usage_by_space)

        def collect_descendant_usage(node_uuid: str) -> float:
            node = faculty.find_node(node_uuid)

            if node is None:
                return 0.0

            node_type = node.__class__.__name__.lower()

            if node_type == "space":
                return usage_by_space.get(node.uuid, 0.0)

            total = 0.0

            if hasattr(node, "children_uuids"):
                for child_uuid in node.children_uuids:
                    total += collect_descendant_usage(child_uuid)

            if node.uuid != root.uuid:
                metric_by_uuid[node.uuid] = total

            return total

        collect_descendant_usage(root.uuid)

        # El root queda fuera de la escala para no distorsionar los colores.
        metric_by_uuid.pop(root.uuid, None)

        return metric_by_uuid

    def load_page(self) -> None:
        self._refresh_active_faculty_label()
        self._render_faculty_summary()
        self._load_result_folders()

    def go_back(self) -> None:
        self.stacked_widget.setCurrentIndex(self.menu_page_index)

    def _refresh_active_faculty_label(self) -> None:
        active_name = self.simulation_controller.active_faculty_name

        if active_name:
            self.active_faculty_label.setText(f"Facultad activa: {active_name}")
        else:
            self.active_faculty_label.setText("No hay ninguna facultad activa.")

    def _render_faculty_summary(self) -> None:
        try:
            faculty = self.simulation_controller.faculty
        except Exception:
            self.faculty_summary_text.setPlainText("No hay ninguna facultad cargada.")
            return

        root = faculty.get_root()
        spaces = faculty.get_all_spaces()

        careers = [
            node for node in faculty.nodes.values()
            if node.__class__.__name__.lower() == "career"
        ]

        courses = [
            node for node in faculty.nodes.values()
            if node.__class__.__name__.lower() == "course"
        ]

        course_groups = [
            node for node in faculty.nodes.values()
            if node.__class__.__name__.lower() == "coursegroup"
        ]

        total_students = 0

        for group in course_groups:
            if getattr(group, "number_of_students", None) is not None:
                total_students += int(group.number_of_students)

        if total_students == 0:
            for course in courses:
                if getattr(course, "number_of_students", None) is not None:
                    total_students += int(course.number_of_students)

        lines = [
            f"Nombre: {root.name}",
            f"Horario: {root.opening_time} - {root.closing_time}",
            f"Slot horario: {root.schedule_slot_minutes} min",
            f"Días activos: {', '.join(root.calendar_days)}",
            "",
            f"Espacios: {len(spaces)}",
            f"Carreras: {len(careers)}",
            f"Cursos: {len(courses)}",
            f"Grupos académicos: {len(course_groups)}",
            f"Estudiantes configurados: {total_students}",
        ]

        self.faculty_summary_text.setPlainText("\n".join(lines))
        self._render_faculty_usage_charts()

    def _render_faculty_usage_charts(self) -> None:
        try:
            faculty = self.simulation_controller.faculty
        except Exception:
            self.faculty_usage_chart.set_values([])
            self.unused_spaces_text.setPlainText("No hay ninguna facultad cargada.")
            return

        usage_by_space = self._calculate_space_weekly_usage()
        spaces = faculty.get_all_spaces()

        space_names = {
            space.uuid: space.name
            for space in spaces
        }

        space_type_names = self._get_space_type_names_by_uuid()

        values = [
            (space_names.get(space_uuid, space_uuid), hours)
            for space_uuid, hours in usage_by_space.items()
            if hours > 0
        ]

        values.sort(key=lambda item: item[1], reverse=True)

        self.faculty_usage_chart.set_values(values[:10])

        graph_data = self._build_space_graph_data()
        metric_by_uuid = self._aggregate_usage_for_space_groups(usage_by_space)
        self.faculty_usage_graph.render_metric_graph(
            graph_data=graph_data,
            metric_by_uuid=metric_by_uuid,
        )
        max_space_usage = max(
            (
                value
                for space_uuid, value in usage_by_space.items()
                if value > 0
            ),
            default=0.0,
        )

        self.faculty_usage_legend.set_labels(
            "0 h",
            f"{max_space_usage:.1f} h"
        )

        used_space_uuids = {
            space_uuid
            for space_uuid, hours in usage_by_space.items()
            if hours > 0
        }

        unused_spaces = [
            space.name
            for space in spaces
            if space.uuid not in used_space_uuids
        ]

        if unused_spaces:
            self.unused_spaces_text.setPlainText(
                "\n".join(f"- {name}" for name in sorted(unused_spaces))
            )
        else:
            self.unused_spaces_text.setPlainText(
                "Todos los espacios aparecen al menos una vez en los horarios."
            )

    def _build_batch_time_series_stats(
        self,
        run_folders: list[Path],
    ) -> dict[int, dict[str, dict[str, float]]]:
        values_by_slot: dict[int, dict[str, list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )

        fields = [
            "susceptible",
            "exposed",
            "infectious",
            "recovered",
            "new_infections",
        ]

        for run_folder in run_folders:
            rows = self._read_csv_rows(run_folder / "time_series.csv")

            for row in rows:
                slot = _safe_int(row.get("slot"))

                for field in fields:
                    values_by_slot[slot][field].append(
                        _safe_float(row.get(field))
                    )

        stats_by_slot: dict[int, dict[str, dict[str, float]]] = {}

        for slot, values_by_field in values_by_slot.items():
            stats_by_slot[slot] = {}

            for field, values in values_by_field.items():
                if not values:
                    continue

                stats_by_slot[slot][field] = {
                    "mean": sum(values) / len(values),
                    "min": self._percentile(values, 0.25),
                    "max": self._percentile(values, 0.75),
                }

        return stats_by_slot
    
    def _build_batch_space_frequency_metric(
        self,
        run_folders: list[Path],
    ) -> dict[str, float]:
        run_count = len(run_folders)

        if run_count <= 0:
            return {}

        runs_with_infection_by_space: dict[str, int] = defaultdict(int)

        for run_folder in run_folders:
            rows = self._read_csv_rows(run_folder / "space_summary.csv")

            for row in rows:
                space_uuid = row.get("space_uuid")

                if not space_uuid:
                    continue

                infection_count = _safe_float(row.get("infection_count"))

                if infection_count > 0:
                    runs_with_infection_by_space[space_uuid] += 1

        return {
            space_uuid: (count / run_count) * 100
            for space_uuid, count in runs_with_infection_by_space.items()
        }
    
    def _render_space_frequency_chart(
        self,
        frequency_metric: dict[str, float],
    ) -> None:
        try:
            faculty = self.simulation_controller.faculty
            names_by_uuid = {
                space.uuid: space.name
                for space in faculty.get_all_spaces()
            }
        except Exception:
            names_by_uuid = {}

        values = [
            (
                names_by_uuid.get(space_uuid, space_uuid),
                frequency,
            )
            for space_uuid, frequency in frequency_metric.items()
            if frequency > 0
        ]

        values.sort(key=lambda item: item[1], reverse=True)

        self.space_frequency_chart.set_values(values[:10])


    def _render_batch_seir_band_chart(
        self,
        run_folders: list[Path],
    ) -> None:
        stats_by_slot = self._build_batch_time_series_stats(run_folders)

        mapping = {
            "Susceptibles": "susceptible",
            "Expuestos": "exposed",
            "Infecciosos": "infectious",
            "Recuperados": "recovered",
        }

        series: dict[str, dict[str, list[tuple[int, float]]]] = {}

        for label, field in mapping.items():
            series[label] = {
                "mean": [],
                "min": [],
                "max": [],
            }

            for slot in sorted(stats_by_slot.keys()):
                stats = stats_by_slot[slot].get(field)

                if not stats:
                    continue

                series[label]["mean"].append((slot, stats["mean"]))
                series[label]["min"].append((slot, stats["min"]))
                series[label]["max"].append((slot, stats["max"]))

        self.batch_seir_band_chart.set_series(series)


    def _render_batch_cumulative_band_chart(
        self,
        run_folders: list[Path],
    ) -> None:
        cumulative_by_run: list[dict[int, float]] = []
        all_slots: set[int] = set()

        for run_folder in run_folders:
            rows = sorted(
                self._read_csv_rows(run_folder / "time_series.csv"),
                key=lambda row: _safe_int(row.get("slot")),
            )

            cumulative = 0.0
            values_by_slot: dict[int, float] = {}

            for row in rows:
                slot = _safe_int(row.get("slot"))
                cumulative += _safe_float(row.get("new_infections"))
                values_by_slot[slot] = cumulative
                all_slots.add(slot)

            cumulative_by_run.append(values_by_slot)

        mean_points: list[tuple[int, float]] = []
        min_points: list[tuple[int, float]] = []
        max_points: list[tuple[int, float]] = []

        for slot in sorted(all_slots):
            values = [
                run_values.get(slot)
                for run_values in cumulative_by_run
                if run_values.get(slot) is not None
            ]

            if not values:
                continue

            mean_points.append((slot, sum(values) / len(values)))
            min_points.append((slot, self._percentile(values, 0.25)))
            max_points.append((slot, self._percentile(values, 0.75)))

        self.batch_cumulative_band_chart.set_series({
            "Infecciones": {
                "mean": mean_points,
                "min": min_points,
                "max": max_points,
            }
        })

    def _calculate_space_weekly_usage(self) -> dict[str, float]:
        faculty = self.simulation_controller.faculty
        root = faculty.get_root()

        used_blocks_by_space: dict[str, set[tuple[str, str, str]]] = defaultdict(set)

        courses = [
            node
            for node in faculty.nodes.values()
            if node.__class__.__name__.lower() == "course"
        ]

        for course in courses:
            course_groups = [
                child
                for child in faculty.get_children(course.uuid)
                if child.__class__.__name__.lower() == "coursegroup"
            ]

            if course_groups:
                for group in course_groups:
                    try:
                        schedule_blocks = faculty.get_effective_schedule_for_course_group(
                            group.uuid
                        )
                    except Exception:
                        schedule_blocks = []

                    self._collect_schedule_blocks_by_space(
                        used_blocks_by_space,
                        schedule_blocks,
                    )
            else:
                self._collect_schedule_blocks_by_space(
                    used_blocks_by_space,
                    list(getattr(course, "base_schedule", [])),
                )

        usage_by_space: dict[str, float] = {}

        for space_uuid, block_keys in used_blocks_by_space.items():
            total_minutes = 0

            for _day, start_time, end_time in block_keys:
                start_minutes = self._time_to_minutes(start_time)
                end_minutes = self._time_to_minutes(end_time)

                if end_minutes > start_minutes:
                    total_minutes += end_minutes - start_minutes

            usage_by_space[space_uuid] = total_minutes / 60.0

        for space in faculty.get_all_spaces():
            usage_by_space.setdefault(space.uuid, 0.0)

        return usage_by_space


    def _collect_schedule_blocks_by_space(
        self,
        used_blocks_by_space: dict[str, set[tuple[str, str, str]]],
        schedule_blocks,
    ) -> None:
        for block in schedule_blocks:
            space_uuid = getattr(block, "space_uuid", None)

            if not space_uuid:
                continue

            used_blocks_by_space[space_uuid].add(
                (
                    getattr(block, "day_of_week", ""),
                    getattr(block, "start_time", ""),
                    getattr(block, "end_time", ""),
                )
            )


    def _get_space_type_names_by_uuid(self) -> dict[str, str]:
        try:
            faculty = self.simulation_controller.faculty
        except Exception:
            return {}

        return {
            space_type.uuid: space_type.name
            for space_type in faculty.get_space_types()
        }


    def _time_to_minutes(self, time_str: str) -> int:
        hours, minutes = str(time_str).split(":")
        return int(hours) * 60 + int(minutes)

    def _load_result_folders(self) -> None:
        self.result_selector.blockSignals(True)
        self.result_selector.clear()
        self.result_folders = []
        self.current_result_folder = None

        try:
            folders = self.simulation_controller.list_saved_results()
        except Exception as exc:
            self.result_summary_text.setPlainText(
                f"No se han podido cargar los resultados:\n{exc}"
            )
            self.result_selector.blockSignals(False)
            return

        self.result_folders = list(folders)

        if not self.result_folders:
            self.result_selector.addItem("No hay resultados guardados")
            self.result_summary_text.setPlainText(
                "Todavía no hay simulaciones guardadas para esta facultad."
            )
            self.result_selector.blockSignals(False)
            return

        for folder in self.result_folders:
            self.result_selector.addItem(folder.name)

        self.result_selector.blockSignals(False)
        self.result_selector.setCurrentIndex(0)
        self._load_result_folder(self.result_folders[0])

    def _on_result_selected(self, index: int) -> None:
        if index < 0 or index >= len(self.result_folders):
            return

        self._load_result_folder(self.result_folders[index])

    def _load_result_folder(self, folder: Path) -> None:
        self.current_result_folder = folder

        metadata = self._read_json(folder / "metadata.json")
        summary = self._read_json(folder / "summary.json")

        if metadata is None or summary is None:
            QMessageBox.warning(
                self,
                "Resultado incompleto",
                f"No se ha podido leer metadata.json o summary.json en:\n{folder}",
            )
            return

        result_type = metadata.get("type", "desconocido")

        lines = [
            f"Carpeta: {folder.name}",
            f"Tipo: {result_type}",
            f"Nombre: {metadata.get('simulation_name', 'N/D')}",
            f"Creado: {metadata.get('created_at', 'N/D')}",
            f"Seed: {metadata.get('seed', metadata.get('batch_seed', 'N/D'))}",
            f"Tiempo de ejecución: {metadata.get('execution_time_seconds', 'N/D')} s",
            "",
            "Resumen:",
        ]

        for key, value in summary.items():
            if key == "warnings":
                continue
            lines.append(f"- {key}: {value}")

        warnings = summary.get("warnings", [])

        if warnings:
            lines.append("")
            lines.append("Avisos:")
            for warning in warnings:
                lines.append(f"- {warning}")

        self.result_summary_text.setPlainText("\n".join(lines))

        self._set_result_sections_for_type(result_type)

        if result_type == "simulation_batch":
            self._render_batch_aggregate_charts(folder)
            self._render_batch_charts(folder)
        else:
            self._render_result_charts(folder)
    
    def _get_batch_run_folders(self, batch_folder: Path) -> list[Path]:
        runs_folder = batch_folder / "runs"

        if not runs_folder.exists():
            return []

        return sorted(
            [
                path
                for path in runs_folder.iterdir()
                if path.is_dir()
            ],
            key=lambda path: path.name,
        )


    def _read_batch_run_rows(
        self,
        run_folders: list[Path],
        filename: str,
    ) -> list[dict]:
        rows: list[dict] = []

        for run_folder in run_folders:
            rows.extend(self._read_csv_rows(run_folder / filename))

        return rows
    
    def _render_batch_aggregate_charts(self, batch_folder: Path) -> None:
        run_folders = self._get_batch_run_folders(batch_folder)
        run_count = len(run_folders)

        if run_count <= 0:
            self._clear_single_result_charts()
            return
        
        self.current_space_frequency_metric = self._build_batch_space_frequency_metric(
            run_folders
        )

        time_series_rows = self._aggregate_batch_time_series(run_folders)
        space_summary_rows = self._aggregate_batch_space_summary(run_folders)
        infection_event_rows = self._aggregate_batch_infection_events(run_folders)
        self.current_group_transmission_rows = infection_event_rows
        self.current_group_transmission_frequency_rows = (
            self._build_batch_group_transmission_frequency_rows(run_folders)
        )

        occupancy_rows = self._read_batch_run_rows(
            run_folders,
            "occupancy_by_slot.csv",
        )

        space_occupancy_rows = self._read_batch_run_rows(
            run_folders,
            "space_occupancy_by_slot.csv",
        )

        self.current_space_summary_rows = space_summary_rows
        self.current_space_occupancy_rows = space_occupancy_rows

        self._render_batch_seir_band_chart(run_folders)
        self._render_batch_cumulative_band_chart(run_folders)
        self._render_space_infections_chart(space_summary_rows)
        self._render_space_risk_chart(space_occupancy_rows)
        self._render_space_frequency_chart(self.current_space_frequency_metric)
        self._render_group_transmission_charts(infection_event_rows)
        self._render_intergroup_spaces_chart(infection_event_rows)
        self._refresh_group_transmission_matrix()
        self._render_daily_temporal_charts(
            time_series_rows,
            occupancy_rows,
            run_count=run_count,
        )
        self._render_batch_weekday_frequency_chart(run_folders)
        self._refresh_simulation_metric_graph()
    
    def _clear_single_result_charts(self) -> None:
        self.seir_chart.set_series({})
        self.new_infections_chart.set_values([])
        self.space_infections_chart.set_values([])
        self.space_risk_chart.set_values([])
        self.source_groups_chart.set_values([])
        self.target_groups_chart.set_values([])
        self.intergroup_spaces_chart.set_values([])
        self.transmission_matrix.set_matrix([], [])
        self.daily_infections_chart.set_values([])
        self.daily_presence_chart.set_values([])
        self.daily_risk_chart.set_values([])
    
    def _aggregate_batch_time_series(
        self,
        run_folders: list[Path],
    ) -> list[dict]:
        sums_by_slot: dict[int, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        counts_by_slot: dict[int, int] = defaultdict(int)

        fields = [
            "susceptible",
            "exposed",
            "infectious",
            "recovered",
            "new_infections",
            "isolated",
        ]

        day_by_slot: dict[int, int] = {}

        for run_folder in run_folders:
            rows = self._read_csv_rows(run_folder / "time_series.csv")

            for row in rows:
                slot = _safe_int(row.get("slot"))
                day_index = _safe_int(row.get("day_index"))

                day_by_slot[slot] = day_index
                counts_by_slot[slot] += 1

                for field in fields:
                    sums_by_slot[slot][field] += _safe_float(row.get(field))

        output: list[dict] = []

        for slot in sorted(sums_by_slot.keys()):
            count = max(1, counts_by_slot[slot])

            item = {
                "slot": str(slot),
                "day_index": str(day_by_slot.get(slot, 0)),
            }

            for field in fields:
                item[field] = str(sums_by_slot[slot][field] / count)

            output.append(item)

        return output
    
    def _build_batch_group_transmission_frequency_rows(
        self,
        run_folders: list[Path],
    ) -> list[dict]:
        run_count = len(run_folders)

        if run_count <= 0:
            return []

        runs_with_pair: dict[tuple[str, str], int] = defaultdict(int)
        info_by_pair: dict[tuple[str, str], dict] = {}

        for run_folder in run_folders:
            rows = self._read_csv_rows(run_folder / "infection_events.csv")
            pairs_seen_in_run: set[tuple[str, str]] = set()

            for row in rows:
                source_group_uuid = row.get("source_group_uuid")
                infected_group_uuid = row.get("infected_group_uuid")

                if not source_group_uuid or not infected_group_uuid:
                    continue

                if source_group_uuid == infected_group_uuid:
                    continue

                pair = (source_group_uuid, infected_group_uuid)
                pairs_seen_in_run.add(pair)
                info_by_pair[pair] = row

            for pair in pairs_seen_in_run:
                runs_with_pair[pair] += 1

        output: list[dict] = []

        for pair, count in runs_with_pair.items():
            row = dict(info_by_pair.get(pair, {}))
            row["transmission_frequency"] = str((count / run_count) * 100)
            output.append(row)

        return output
    
    def _refresh_group_transmission_matrix(self) -> None:
        metric = self.group_matrix_metric_selector.currentData()

        if metric == "frequency":
            self._render_transmission_matrix(
                self.current_group_transmission_frequency_rows,
                value_field="transmission_frequency",
                empty_message="Sin transmisiones recurrentes entre grupos",
            )
        else:
            self._render_transmission_matrix(
                self.current_group_transmission_rows,
                value_field="transmission_count",
                empty_message="Sin contagios entre grupos distintos",
            )

    def _aggregate_batch_space_summary(
        self,
        run_folders: list[Path],
    ) -> list[dict]:
        sums_by_space: dict[str, dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )
        info_by_space: dict[str, dict] = {}

        run_count = max(1, len(run_folders))

        for run_folder in run_folders:
            rows = self._read_csv_rows(run_folder / "space_summary.csv")

            for row in rows:
                space_uuid = row.get("space_uuid")

                if not space_uuid:
                    continue

                info_by_space[space_uuid] = row
                sums_by_space[space_uuid]["infection_count"] += _safe_float(
                    row.get("infection_count")
                )
                sums_by_space[space_uuid]["event_count_with_infections"] += _safe_float(
                    row.get("event_count_with_infections")
                )

        output: list[dict] = []

        for space_uuid, sums in sums_by_space.items():
            info = info_by_space.get(space_uuid, {})

            output.append(
                {
                    "space_uuid": space_uuid,
                    "space_name": info.get("space_name"),
                    "space_type_uuid": info.get("space_type_uuid"),
                    "space_type_name": info.get("space_type_name"),
                    "infection_count": str(sums["infection_count"] / run_count),
                    "event_count_with_infections": str(
                        sums["event_count_with_infections"] / run_count
                    ),
                }
            )

        return output
    
    def _aggregate_batch_infection_events(
        self,
        run_folders: list[Path],
    ) -> list[dict]:
        run_count = max(1, len(run_folders))

        counts_by_key: dict[tuple, float] = defaultdict(float)
        info_by_key: dict[tuple, dict] = {}

        for run_folder in run_folders:
            rows = self._read_csv_rows(run_folder / "infection_events.csv")

            for row in rows:
                key = (
                    row.get("source_group_uuid"),
                    row.get("infected_group_uuid"),
                    row.get("space_uuid"),
                )

                counts_by_key[key] += 1
                info_by_key[key] = row

        output: list[dict] = []

        for key, total_count in counts_by_key.items():
            row = dict(info_by_key.get(key, {}))
            row["transmission_count"] = str(total_count / run_count)
            output.append(row)

        return output
    
    def _render_batch_weekday_frequency_chart(
        self,
        run_folders: list[Path],
    ) -> None:
        calendar_days = self._get_calendar_days()
        run_count = len(run_folders)

        if run_count <= 0:
            self.weekday_frequency_chart.set_values([])
            return

        top_counts_by_day: dict[str, int] = defaultdict(int)

        for run_folder in run_folders:
            day_risks = self._calculate_weekday_risk_for_run(
                run_folder=run_folder,
                calendar_days=calendar_days,
            )

            if not day_risks:
                continue

            top_days = sorted(
                day_risks.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:2]

            for day, risk in top_days:
                if risk <= 0:
                    continue

                top_counts_by_day[day] += 1

        values: list[tuple[str, float]] = []

        for day in calendar_days:
            frequency = (top_counts_by_day.get(day, 0) / run_count) * 100
            values.append((self._translate_day_name(day), frequency))

        self.weekday_frequency_chart.set_values(values)


    def _calculate_weekday_risk_for_run(
        self,
        run_folder: Path,
        calendar_days: list[str],
    ) -> dict[str, float]:
        time_series_rows = self._read_csv_rows(run_folder / "time_series.csv")
        occupancy_rows = self._read_csv_rows(run_folder / "occupancy_by_slot.csv")

        infections_by_day: dict[str, float] = defaultdict(float)
        present_sum_by_day: dict[str, float] = defaultdict(float)

        for row in time_series_rows:
            day_index = _safe_int(row.get("day_index"))
            day = self._calendar_day_from_index(day_index, calendar_days)
            infections_by_day[day] += _safe_float(row.get("new_infections"))

        for row in occupancy_rows:
            day_index = _safe_int(row.get("day_index"))
            day = self._calendar_day_from_index(day_index, calendar_days)
            present_sum_by_day[day] += _safe_float(row.get("present_agents"))

        risks: dict[str, float] = {}

        for day in calendar_days:
            present_sum = present_sum_by_day.get(day, 0.0)

            if present_sum <= 0:
                risks[day] = 0.0
            else:
                risks[day] = (
                    infections_by_day.get(day, 0.0) / present_sum
                ) * 100

        return risks
    
    def _render_batch_charts(self, folder: Path) -> None:
        rows = self._read_csv_rows(folder / "batch_summary.csv")

        if not rows:
            self.batch_total_infections_chart.set_series({})
            self.batch_peak_chart.set_series({})
            self.batch_distribution_chart.set_values([])
            return

        total_infections_series: list[tuple[int, int]] = []
        peak_series: list[tuple[int, int]] = []
        total_infections_values: list[int] = []

        for index, row in enumerate(rows, start=1):
            total_infections = _safe_int(row.get("total_infections"))
            peak_infectious = _safe_int(row.get("peak_infectious"))

            total_infections_series.append((index, total_infections))
            peak_series.append((index, peak_infectious))
            total_infections_values.append(total_infections)

        self.batch_total_infections_chart.set_series({
            "Infecciones totales": total_infections_series,
        })

        self.batch_peak_chart.set_series({
            "Pico infeccioso": peak_series,
        })

        self.batch_distribution_chart.set_values(
            self._build_histogram_values(total_infections_values)
        )


    def _build_histogram_values(
        self,
        values: list[int],
        bins: int = 6,
    ) -> list[tuple[str, float]]:
        if not values:
            return []

        min_value = min(values)
        max_value = max(values)

        if min_value == max_value:
            return [(str(min_value), float(len(values)))]

        bins = max(1, min(bins, len(set(values))))
        width = max(1, (max_value - min_value + 1) / bins)

        counts = [0 for _ in range(bins)]

        for value in values:
            index = int((value - min_value) / width)
            index = min(index, bins - 1)
            counts[index] += 1

        output: list[tuple[str, float]] = []

        for index, count in enumerate(counts):
            start = int(round(min_value + index * width))
            end = int(round(min_value + (index + 1) * width - 1))

            if index == bins - 1:
                end = max_value

            label = f"{start}-{end}" if start != end else str(start)
            output.append((label, float(count)))

        return output

    def _render_intergroup_spaces_chart(self, rows: list[dict]) -> None:
        counts_by_space: dict[str, int] = defaultdict(int)

        for row in rows:
            source_group_uuid = row.get("source_group_uuid")
            infected_group_uuid = row.get("infected_group_uuid")
            count = _safe_float(row.get("transmission_count"), default=1.0)

            if not source_group_uuid or not infected_group_uuid:
                continue

            if source_group_uuid == infected_group_uuid:
                continue

            space_name = (
                row.get("space_name")
                or row.get("space_uuid")
                or "Espacio desconocido"
            )

            counts_by_space[space_name] += count

        values = sorted(
            counts_by_space.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:10]

        self.intergroup_spaces_chart.set_values(values)

    def _render_daily_temporal_charts(
        self,
        time_series_rows: list[dict],
        occupancy_rows: list[dict],
        run_count: int = 1,
    ) -> None:
        calendar_days = self._get_calendar_days()

        infections_by_calendar_day: dict[str, int] = defaultdict(int)
        present_sum_by_calendar_day: dict[str, int] = defaultdict(int)
        slot_count_by_calendar_day: dict[str, int] = defaultdict(int)

        for row in time_series_rows:
            day_index = _safe_int(row.get("day_index"))
            calendar_day = self._calendar_day_from_index(day_index, calendar_days)

            infections_by_calendar_day[calendar_day] += _safe_float(
                row.get("new_infections")
            )

        for row in occupancy_rows:
            day_index = _safe_int(row.get("day_index"))
            calendar_day = self._calendar_day_from_index(day_index, calendar_days)

            present_sum_by_calendar_day[calendar_day] += _safe_int(
                row.get("present_agents")
            )
            slot_count_by_calendar_day[calendar_day] += 1

        ordered_days = [
            day
            for day in calendar_days
            if (
                day in infections_by_calendar_day
                or day in present_sum_by_calendar_day
            )
        ]

        infection_values: list[tuple[str, float]] = []
        presence_values: list[tuple[str, float]] = []
        risk_values: list[tuple[str, float]] = []

        for day in ordered_days:
            infections = infections_by_calendar_day.get(day, 0)
            present_sum = present_sum_by_calendar_day.get(day, 0)
            slot_count = slot_count_by_calendar_day.get(day, 0)

            average_presence = 0.0
            if slot_count > 0:
                average_presence = present_sum / slot_count

            risk_per_100 = 0.0
            if present_sum > 0:
                risk_per_100 = (infections / present_sum) * 100

            day_label = self._translate_day_name(day)

            infection_values.append((day_label, float(infections)))
            presence_values.append((day_label, average_presence))
            risk_values.append((day_label, risk_per_100))

        self.daily_infections_chart.set_values(infection_values)
        self.daily_presence_chart.set_values(presence_values)
        self.daily_risk_chart.set_values(risk_values)

    def _get_calendar_days(self) -> list[str]:
        try:
            faculty = self.simulation_controller.faculty
            root = faculty.get_root()
            days = list(root.calendar_days)

            if days:
                return days
        except Exception:
            pass

        return ["monday", "tuesday", "wednesday", "thursday", "friday"]


    def _calendar_day_from_index(
        self,
        day_index: int,
        calendar_days: list[str],
    ) -> str:
        if not calendar_days:
            return "unknown"

        return calendar_days[day_index % len(calendar_days)]


    def _translate_day_name(self, day: str) -> str:
        translations = {
            "monday": "lunes",
            "tuesday": "martes",
            "wednesday": "miércoles",
            "thursday": "jueves",
            "friday": "viernes",
            "saturday": "sábado",
            "sunday": "domingo",
            "unknown": "desconocido",
        }

        return translations.get(str(day).lower(), str(day))

    def _render_result_charts(self, folder: Path) -> None:
        time_series_rows = self._read_csv_rows(folder / "time_series.csv")
        space_summary_rows = self._read_csv_rows(folder / "space_summary.csv")
        infection_event_rows = self._read_csv_rows(folder / "infection_events.csv")
        space_occupancy_rows = self._read_csv_rows(folder / "space_occupancy_by_slot.csv")
        occupancy_rows = self._read_csv_rows(folder / "occupancy_by_slot.csv")

        self.current_space_summary_rows = space_summary_rows
        self.current_space_occupancy_rows = space_occupancy_rows

        self.current_group_transmission_rows = infection_event_rows
        self.current_group_transmission_frequency_rows = []

        self.weekday_frequency_chart.set_values([])

        self._render_seir_chart(time_series_rows)
        self._render_new_infections_chart(time_series_rows)
        self._render_space_infections_chart(space_summary_rows)
        self._render_space_risk_chart(space_occupancy_rows)
        self._render_group_transmission_charts(infection_event_rows)
        self._render_intergroup_spaces_chart(infection_event_rows)
        self._refresh_group_transmission_matrix()
        self._render_daily_temporal_charts(time_series_rows, occupancy_rows)
        self._refresh_simulation_metric_graph()

        self.current_space_frequency_metric = {}
        self.space_frequency_chart.set_values([])

    def _refresh_simulation_metric_graph(self) -> None:
        metric = self.simulation_graph_metric_selector.currentData()

        if metric == "frequency":
            metric_by_space = dict(self.current_space_frequency_metric)
            max_value = 100.0
            self.simulation_metric_legend.set_labels(
                "0%",
                "100%",
            )
        elif metric == "risk":
            metric_by_space = self._build_space_risk_metric()
            max_value = max(metric_by_space.values(), default=0.0)
            self.simulation_metric_legend.set_labels(
                "0",
                f"{max_value:.2f}",
            )
        else:
            metric_by_space = self._build_space_infection_metric()
            max_value = max(metric_by_space.values(), default=0.0)
            self.simulation_metric_legend.set_labels(
                "0",
                str(int(max_value)),
            )

        try:
            graph_data = self._build_space_graph_data()
            metric_by_uuid = self._aggregate_usage_for_space_groups(metric_by_space)

            self.simulation_metric_graph.render_metric_graph(
                graph_data=graph_data,
                metric_by_uuid=metric_by_uuid,
            )
        except Exception:
            self.simulation_metric_graph.scene().clear()


    def _build_space_infection_metric(self) -> dict[str, float]:
        metric_by_space: dict[str, float] = {}

        for row in self.current_space_summary_rows:
            space_uuid = row.get("space_uuid")

            if not space_uuid:
                continue

            metric_by_space[space_uuid] = float(_safe_int(row.get("infection_count")))

        return metric_by_space


    def _build_space_risk_metric(self) -> dict[str, float]:
        present_by_space: dict[str, int] = defaultdict(int)
        infections_by_space: dict[str, int] = defaultdict(int)

        for row in self.current_space_occupancy_rows:
            space_uuid = row.get("space_uuid")

            if not space_uuid:
                continue

            present_by_space[space_uuid] += _safe_int(row.get("present_agents"))
            infections_by_space[space_uuid] += _safe_int(row.get("new_infections"))

        metric_by_space: dict[str, float] = {}

        for space_uuid, present_agents in present_by_space.items():
            if present_agents <= 0:
                metric_by_space[space_uuid] = 0.0
                continue

            metric_by_space[space_uuid] = (
                infections_by_space.get(space_uuid, 0) / present_agents
            ) * 100

        return metric_by_space
        

    def _render_transmission_matrix(
        self,
        rows: list[dict],
        value_field: str = "transmission_count",
        empty_message: str = "Sin contagios entre grupos distintos",
    ) -> None:
        group_names_by_uuid: dict[str, str] = {}
        pair_counts: dict[tuple[str, str], int] = defaultdict(int)

        for row in rows:
            source_group_uuid = row.get("source_group_uuid")
            infected_group_uuid = row.get("infected_group_uuid")

            if not source_group_uuid or not infected_group_uuid:
                continue

            if source_group_uuid == infected_group_uuid:
                continue

            source_name = (
                row.get("source_group_name")
                or source_group_uuid
            )

            infected_name = (
                row.get("infected_group_name")
                or infected_group_uuid
            )

            group_names_by_uuid[source_group_uuid] = source_name
            group_names_by_uuid[infected_group_uuid] = infected_name

            count = _safe_float(row.get(value_field), default=1.0)

            if value_field == "transmission_frequency":
                count = _safe_float(row.get(value_field), default=0.0)

            pair_counts[(source_group_uuid, infected_group_uuid)] += count

        if not pair_counts:
            self.transmission_matrix.set_matrix([], [])
            return

        sorted_group_uuids = sorted(
            group_names_by_uuid.keys(),
            key=lambda uuid: group_names_by_uuid[uuid],
        )

        # Limitamos la matriz para que siga siendo legible.
        if len(sorted_group_uuids) > 14:
            total_activity = defaultdict(int)

            for (source_uuid, target_uuid), count in pair_counts.items():
                total_activity[source_uuid] += count
                total_activity[target_uuid] += count

            sorted_group_uuids = sorted(
                sorted_group_uuids,
                key=lambda uuid: total_activity[uuid],
                reverse=True,
            )[:14]

            sorted_group_uuids.sort(key=lambda uuid: group_names_by_uuid[uuid])

        labels = [
            group_names_by_uuid[group_uuid]
            for group_uuid in sorted_group_uuids
        ]

        matrix: list[list[int]] = []

        for source_uuid in sorted_group_uuids:
            row_values: list[int] = []

            for target_uuid in sorted_group_uuids:
                row_values.append(
                    pair_counts.get((source_uuid, target_uuid), 0.0)
                )

            matrix.append(row_values)

        suffix = "%" if value_field == "transmission_frequency" else ""
        self.transmission_matrix.set_matrix(labels, matrix, value_suffix=suffix)


    def _render_space_risk_chart(self, rows: list[dict]) -> None:
        present_by_space: dict[str, int] = defaultdict(int)
        infections_by_space: dict[str, int] = defaultdict(int)
        names_by_space: dict[str, str] = {}

        for row in rows:
            space_uuid = row.get("space_uuid")

            if not space_uuid:
                continue

            names_by_space[space_uuid] = (
                row.get("space_name")
                or space_uuid
            )

            present_by_space[space_uuid] += _safe_int(row.get("present_agents"))
            infections_by_space[space_uuid] += _safe_int(row.get("new_infections"))

        values: list[tuple[str, float]] = []

        for space_uuid, present_agents in present_by_space.items():
            if present_agents <= 0:
                continue

            infections = infections_by_space.get(space_uuid, 0)

            if infections <= 0:
                continue

            risk_per_100 = (infections / present_agents) * 100
            values.append((names_by_space.get(space_uuid, space_uuid), risk_per_100))

        values.sort(key=lambda item: item[1], reverse=True)

        self.space_risk_chart.set_values(values[:10])


    def _render_group_transmission_charts(self, rows: list[dict]) -> None:
        source_counts: dict[str, int] = defaultdict(int)
        target_counts: dict[str, int] = defaultdict(int)

        for row in rows:
            source_group_uuid = row.get("source_group_uuid")
            infected_group_uuid = row.get("infected_group_uuid")
            count = _safe_float(row.get("transmission_count"), default=1.0)

            if not source_group_uuid or not infected_group_uuid:
                continue

            if source_group_uuid == infected_group_uuid:
                continue

            source_name = (
                row.get("source_group_name")
                or source_group_uuid
            )

            target_name = (
                row.get("infected_group_name")
                or infected_group_uuid
            )

            source_counts[source_name] += count
            target_counts[target_name] += count

        source_values = sorted(
            source_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:10]

        target_values = sorted(
            target_counts.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:10]

        self.source_groups_chart.set_values(source_values)
        self.target_groups_chart.set_values(target_values)

    def _render_seir_chart(self, rows: list[dict]) -> None:
        series = {
            "Susceptibles": [],
            "Expuestos": [],
            "Infecciosos": [],
            "Recuperados": [],
        }

        for row in rows:
            slot = _safe_int(row.get("slot"))

            series["Susceptibles"].append((slot, _safe_int(row.get("susceptible"))))
            series["Expuestos"].append((slot, _safe_int(row.get("exposed"))))
            series["Infecciosos"].append((slot, _safe_int(row.get("infectious"))))
            series["Recuperados"].append((slot, _safe_int(row.get("recovered"))))

        self.seir_chart.set_series(series)


    def _render_new_infections_chart(self, rows: list[dict]) -> None:
        cumulative_values: list[tuple[int, int]] = []
        cumulative_total = 0

        sorted_rows = sorted(
            rows,
            key=lambda row: _safe_int(row.get("slot")),
        )

        if not sorted_rows:
            self.new_infections_chart.set_values([])
            return

        first_slot = _safe_int(sorted_rows[0].get("slot"))

        if first_slot > 0:
            cumulative_values.append((0, 0))

        for row in sorted_rows:
            slot = _safe_int(row.get("slot"))
            cumulative_total += _safe_int(row.get("new_infections"))
            cumulative_values.append((slot, cumulative_total))

        self.new_infections_chart.set_values(cumulative_values)
        self.new_infections_chart.set_x_ticks(
            self._build_time_axis_ticks(sorted_rows)
        )


    def _render_space_infections_chart(self, rows: list[dict]) -> None:
        values: list[tuple[str, float]] = []

        for row in rows:
            infection_count = _safe_float(row.get("infection_count"))

            if infection_count <= 0:
                continue

            name = row.get("space_name") or row.get("space_uuid") or "N/D"
            values.append((name, infection_count))

        values.sort(key=lambda item: item[1], reverse=True)

        self.space_infections_chart.set_values(values[:10])

    def _read_json(self, path: Path) -> Optional[dict]:
        if not path.exists():
            return None

        try:
            with path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return None