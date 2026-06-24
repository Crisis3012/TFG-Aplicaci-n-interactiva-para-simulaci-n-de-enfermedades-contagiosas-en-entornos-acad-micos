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
    def __init__(
        self,
        node_uuid: str,
        name: str,
        size: float = 100,
        expanded=None,
    ):
        super().__init__()

        self.node_uuid = node_uuid
        self.name = name
        self.size = max(float(size), 90.0)
        self.expanded = expanded

        self.connected_edges = []

        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )

        self.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)

        self.default_pen = QPen(QColor("#1f3a5f"), 3)
        self.collapsed_pen = QPen(QColor("#f39c12"), 4)
        self.selected_pen = QPen(QColor("#e74c3c"), 4)
        self.text_pen = QPen(QColor("#111827"))

        self.font = QFont("Arial", 15, QFont.Weight.Bold)

    def boundingRect(self):
        return QRectF(-50, -50, 100, 100)

    def add_edge(self, edge):
        self.connected_edges.append(edge)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for edge in self.connected_edges:
                edge.update_position()

        self.update()
        return super().itemChange(change, value)

    def _current_pen(self):
        if self.isSelected():
            return self.selected_pen

        if self.expanded is False:
            return self.collapsed_pen

        return self.default_pen

    def _draw_centered_text(self, painter, rect: QRectF):
        painter.setPen(self.text_pen)
        painter.setFont(self.font)

        text_rect = rect.adjusted(10, 10, -10, -10)

        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            self.name,
        )


class RootNodeItem(BaseGraphNodeItem):
    def __init__(self, node_uuid: str, name: str, size: float = 100, expanded=None):
        super().__init__(node_uuid, name, size, expanded=expanded)
        self.width = self.size * 1.8
        self.height = self.size * 0.9
        self.fill_color = "#4fa3a5"

    def boundingRect(self):
        return QRectF(
            -self.width / 2,
            -self.height / 2,
            self.width,
            self.height,
        )

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(painter.RenderHint.Antialiasing)

        rect = self.boundingRect()

        painter.setBrush(QBrush(QColor(self.fill_color)))
        painter.setPen(self._current_pen())
        painter.drawRect(rect)

        self._draw_centered_text(painter, rect)


class GroupNodeItem(BaseGraphNodeItem):
    def __init__(
        self,
        node_uuid: str,
        name: str,
        size: float = 100,
        color: str = "#75d7e0",
        expanded=None,
    ):
        super().__init__(node_uuid, name, size, expanded=expanded)
        self.diameter = self.size
        self.fill_color = color

    def boundingRect(self):
        return QRectF(
            -self.diameter / 2,
            -self.diameter / 2,
            self.diameter,
            self.diameter,
        )

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(painter.RenderHint.Antialiasing)

        rect = self.boundingRect()

        painter.setBrush(QBrush(QColor(self.fill_color)))
        painter.setPen(self._current_pen())
        painter.drawEllipse(rect)

        self._draw_centered_text(painter, rect)


class SpaceNodeItem(BaseGraphNodeItem):
    def __init__(self, node_uuid: str, name: str, size: float = 100, expanded=None):
        super().__init__(node_uuid, name, size, expanded=expanded)
        self.width = self.size * 1.7
        self.height = self.size * 0.85
        self.fill_color = "#d7dde5"

    def boundingRect(self):
        return QRectF(
            -self.width / 2,
            -self.height / 2,
            self.width,
            self.height,
        )

    def paint(self, painter, option, widget=None):
        painter.setRenderHint(painter.RenderHint.Antialiasing)

        rect = self.boundingRect()

        painter.setBrush(QBrush(QColor(self.fill_color)))
        painter.setPen(self._current_pen())
        painter.drawRoundedRect(rect, 16, 16)

        self._draw_centered_text(painter, rect)


def create_graph_node_item(
    node_uuid: str,
    name: str,
    node_type: str,
    size: float = 100,
    expanded=None,
):
    node_type = node_type.lower()

    if node_type == "root":
        return RootNodeItem(
            node_uuid=node_uuid,
            name=name,
            size=size,
            expanded=expanded,
        )

    if node_type in {"group", "spacegroup"}:
        return GroupNodeItem(
            node_uuid=node_uuid,
            name=name,
            size=size,
            color="#75d7e0",
            expanded=expanded,
        )

    if node_type == "career":
        return GroupNodeItem(
            node_uuid=node_uuid,
            name=name,
            size=size,
            color="#8bd17c",
            expanded=expanded,
        )

    if node_type == "course":
        return GroupNodeItem(
            node_uuid=node_uuid,
            name=name,
            size=size,
            color="#f2c46d",
            expanded=expanded,
        )

    if node_type == "coursegroup":
        return GroupNodeItem(
            node_uuid=node_uuid,
            name=name,
            size=size,
            color="#c6a4ff",
            expanded=expanded,
        )

    if node_type == "space":
        return SpaceNodeItem(
            node_uuid=node_uuid,
            name=name,
            size=size,
            expanded=expanded,
        )

    return SpaceNodeItem(
        node_uuid=node_uuid,
        name=name,
        size=size,
        expanded=expanded,
    )