from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem, QGraphicsLineItem
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QBrush, QPen, QColor, QFont


class GraphEdgeItem(QGraphicsLineItem):
    def __init__(self, source_node, target_node):
        super().__init__()

        self.source_node = source_node
        self.target_node = target_node

        self.setPen(QPen(QColor("#606975"), 2))
        self.setZValue(-1)

        self.update_position()

    def update_position(self):
        source_position = self.source_node.scenePos()
        target_position = self.target_node.scenePos()

        self.setLine(
            source_position.x(),
            source_position.y(),
            target_position.x(),
            target_position.y(),
        )


class BaseGraphNodeItem(QGraphicsObject):
    def __init__(self, node_uuid: str, name: str, size: float = 100):
        super().__init__()

        self.node_uuid = node_uuid
        self.name = name
        self.size = float(size)
        self.connected_edges = []

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable |
            QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

        self.default_pen = QPen(QColor("#1f3a5f"), 3)
        self.selected_pen = QPen(QColor("#e74c3c"), 4)
        self.text_pen = QPen(QColor("#111827"))

        self.font = QFont("Arial", 10, QFont.Weight.Bold)

    def boundingRect(self):
        half = self.size / 2
        return QRectF(-half, -half, self.size, self.size)

    def add_edge(self, edge):
        self.connected_edges.append(edge)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.connected_edges:
                edge.update_position()

        return super().itemChange(change, value)

    def _current_pen(self):
        return self.selected_pen if self.isSelected() else self.default_pen

    def _draw_centered_text(self, painter):
        painter.setPen(self.text_pen)
        painter.setFont(self.font)

        text_rect = self.boundingRect().adjusted(8, 8, -8, -8)

        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            self.name,
        )


class RootNodeItem(BaseGraphNodeItem):
    """
    Raíz: rectángulo con esquinas normales.
    """

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(painter.RenderHint.Antialiasing)

        rect = self.boundingRect()

        painter.setBrush(QBrush(QColor("#4fa3a5")))
        painter.setPen(self._current_pen())
        painter.drawRect(rect)

        self._draw_centered_text(painter)


class GroupNodeItem(BaseGraphNodeItem):
    """
    Grupo: círculo.
    """

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(painter.RenderHint.Antialiasing)

        rect = self.boundingRect()

        painter.setBrush(QBrush(QColor("#75d7e0")))
        painter.setPen(self._current_pen())
        painter.drawEllipse(rect)

        self._draw_centered_text(painter)


class SpaceNodeItem(BaseGraphNodeItem):
    """
    Espacio/clase: rectángulo con esquinas redondeadas.
    """

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(painter.RenderHint.Antialiasing)

        rect = self.boundingRect()

        painter.setBrush(QBrush(QColor("#d7dde5")))
        painter.setPen(self._current_pen())
        painter.drawRoundedRect(rect, 16, 16)

        self._draw_centered_text(painter)


def create_graph_node_item(node_uuid: str, name: str, node_type: str, size: float = 100):
    node_type = node_type.lower()

    if node_type == "root":
        return RootNodeItem(node_uuid=node_uuid, name=name, size=size)

    if node_type == "group":
        return GroupNodeItem(node_uuid=node_uuid, name=name, size=size)

    if node_type == "space":
        return SpaceNodeItem(node_uuid=node_uuid, name=name, size=size)

    return SpaceNodeItem(node_uuid=node_uuid, name=name, size=size)