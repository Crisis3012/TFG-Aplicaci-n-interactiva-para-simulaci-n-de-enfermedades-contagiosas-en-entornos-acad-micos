from __future__ import annotations

from typing import Any, Optional
import math

from PySide6.QtCore import (
    Qt,
    QPoint,
    QPointF,
    QRectF,
    Property,
    QPropertyAnimation,
    QEasingCurve,
)
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsObject, QGraphicsItem
from PySide6.QtGui import QBrush, QPen, QColor, QFont

from backend.faculty import (
    Faculty,
    Root,
    Space,
    SpaceGroup,
    ContainerNode,
)

from frontend.graph_items import (
    BaseGraphNodeItem,
    GraphEdgeItem,
    create_graph_node_item,
)
from frontend.styles import GRAPH_VIEW_STYLE


class SimulationBubbleItem(QGraphicsObject):
    """
    Burbuja informativa junto a un nodo.

    Se usa para:
    - espacios visibles;
    - grupos contraídos con información agregada.
    """

    def __init__(
        self,
        text: str,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.text = text
        self.width = 138
        self.height = 78

        self.background = QColor("#ffffff")
        self.border = QColor("#34495e")
        self.text_color = QColor("#1f2933")

        self.font = QFont("Arial", 8)
        self.font.setBold(False)

        self.setZValue(20)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter, option, widget=None) -> None:
        painter.setRenderHint(painter.RenderHint.Antialiasing)

        rect = self.boundingRect()

        painter.setBrush(QBrush(self.background))
        painter.setPen(QPen(self.border, 2))
        painter.drawRoundedRect(rect, 10, 10)

        painter.setPen(QPen(self.text_color))
        painter.setFont(self.font)
        painter.drawText(
            rect.adjusted(8, 6, -8, -6),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self.text,
        )


class InfectionMarkerItem(QGraphicsObject):
    """
    Marcador pequeño para indicar que en ese frame hay una infección
    asociada al nodo/espacio.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.size = 26
        self.setZValue(30)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.size, self.size)

    def paint(self, painter, option, widget=None) -> None:
        painter.setRenderHint(painter.RenderHint.Antialiasing)

        rect = self.boundingRect()

        painter.setBrush(QBrush(QColor("#e74c3c")))
        painter.setPen(QPen(QColor("#922b21"), 2))
        painter.drawEllipse(rect)

        painter.setPen(QPen(QColor("#ffffff")))
        font = QFont("Arial", 12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            rect,
            Qt.AlignmentFlag.AlignCenter,
            "!",
        )


class AgentMovementItem(QGraphicsObject):
    """
    Círculo que representa un agente moviéndose entre nodos visibles.

    No representa posición física real calculada por el motor.
    Es una interpolación visual entre dos ubicaciones lógicas.
    """

    def __init__(
        self,
        path_points: list[QPointF],
        color: QColor,
        radius: float = 5.0,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.path_points = path_points
        self.color = color
        self.radius = radius
        self._progress = 0.0

        self.setZValue(40)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True)

        if self.path_points:
            self.setPos(self.path_points[0])

    def boundingRect(self) -> QRectF:
        r = self.radius + 2
        return QRectF(-r, -r, r * 2, r * 2)

    def paint(self, painter, option, widget=None) -> None:
        painter.setRenderHint(painter.RenderHint.Antialiasing)

        painter.setBrush(QBrush(self.color))
        painter.setPen(QPen(QColor("#1f2933"), 1))
        painter.drawEllipse(
            QPointF(0, 0),
            self.radius,
            self.radius,
        )

    def get_progress(self) -> float:
        return self._progress

    def set_progress(self, value: float) -> None:
        self._progress = max(0.0, min(1.0, float(value)))
        self.setPos(self._point_at_progress(self._progress))

    progress = Property(float, get_progress, set_progress)

    def _point_at_progress(self, progress: float) -> QPointF:
        if not self.path_points:
            return QPointF(0, 0)

        if len(self.path_points) == 1:
            return self.path_points[0]

        segments: list[tuple[QPointF, QPointF, float]] = []
        total_length = 0.0

        for start, end in zip(self.path_points, self.path_points[1:]):
            dx = end.x() - start.x()
            dy = end.y() - start.y()
            length = (dx * dx + dy * dy) ** 0.5

            if length <= 0:
                continue

            segments.append((start, end, length))
            total_length += length

        if total_length <= 0:
            return self.path_points[-1]

        target_length = total_length * progress
        traversed = 0.0

        for start, end, length in segments:
            if traversed + length >= target_length:
                local_progress = (target_length - traversed) / length

                x = start.x() + (end.x() - start.x()) * local_progress
                y = start.y() + (end.y() - start.y()) * local_progress

                return QPointF(x, y)

            traversed += length

        return self.path_points[-1]


class SimulationGraphScene(QGraphicsScene):
    def mouseDoubleClickEvent(self, event) -> None:
        view = self.views()[0] if self.views() else None
        transform = view.transform() if view else None

        item = self.itemAt(event.scenePos(), transform)
        node_item = self._get_node_item(item)

        if (
            event.button() == Qt.MouseButton.LeftButton
            and node_item is not None
            and hasattr(view, "toggle_node_expanded")
        ):
            view.toggle_node_expanded(node_item.node_uuid)
            event.accept()
            return

        super().mouseDoubleClickEvent(event)

    def _get_node_item(self, item):
        while item is not None:
            if isinstance(item, BaseGraphNodeItem):
                return item

            item = item.parentItem()

        return None


class SimulationGraphView(QGraphicsView):
    """
    Grafo visual de simulación.

    Primera versión:
    - dibuja árbol espacial de la facultad;
    - permite expandir/contraer grupos espaciales con doble clic;
    - muestra burbujas en espacios visibles;
    - muestra burbujas agregadas en grupos contraídos;
    - marca espacios con infecciones en el frame actual.
    """

    def __init__(self) -> None:
        super().__init__()

        self.scene_obj = SimulationGraphScene(self)
        self.setScene(self.scene_obj)

        self.scene_obj.setSceneRect(-5000, -5000, 10000, 10000)

        self.nodes_by_uuid: dict[str, BaseGraphNodeItem] = {}
        self.node_positions: dict[str, tuple[float, float]] = {}

        self.visible_edges: list[dict[str, str]] = []
        self.agent_animations: list[QPropertyAnimation] = []
        self.max_moving_agents = 120

        self.collapsed_node_uuids: set[str] = set()

        self.current_faculty: Optional[Faculty] = None
        self.current_frame: Optional[dict[str, Any]] = None

        self.min_zoom = 0.2
        self.max_zoom = 4.0

        self._panning = False
        self._last_mouse_pos = QPoint()

        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)

        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.setStyleSheet(GRAPH_VIEW_STYLE)

    # ========================================================
    # Render principal
    # ========================================================

    def render_frame(
        self,
        faculty: Faculty,
        frame: dict[str, Any],
        trace_data: Optional[dict[str, Any]] = None,
        previous_frame: Optional[dict[str, Any]] = None,
        animation_duration_ms: int = 350,
    ) -> None:
        self.current_faculty = faculty
        self.current_frame = frame

        self._preserve_current_positions()

        self.scene_obj.clear()
        self.nodes_by_uuid.clear()

        graph_data = self._build_visible_space_graph(faculty)
        nodes = graph_data["nodes"]
        edges = graph_data["edges"]
        self.visible_edges = list(edges)
        self._stop_agent_animations()

        default_positions = self._calculate_standard_layout(nodes, edges)

        for node in nodes:
            item = create_graph_node_item(
                node_uuid=node["uuid"],
                name=node["name"],
                node_type=node["type"],
                size=node.get("size", 100),
                expanded=node.get("expanded", None),
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

        self._add_bubbles_and_markers(
            faculty=faculty,
            frame=frame,
        )

        self._add_agent_movements(
            faculty=faculty,
            trace_data=trace_data,
            previous_frame=previous_frame,
            current_frame=frame,
            animation_duration_ms=animation_duration_ms,
        )

    def _preserve_current_positions(self) -> None:
        for node_uuid, item in self.nodes_by_uuid.items():
            self.node_positions[node_uuid] = (
                item.scenePos().x(),
                item.scenePos().y(),
            )

    # ========================================================
    # Expandir / contraer
    # ========================================================

    def toggle_node_expanded(self, node_uuid: str) -> None:
        if self.current_faculty is None or self.current_frame is None:
            return

        node = self.current_faculty.find_node(node_uuid)

        if not isinstance(node, ContainerNode):
            return

        if isinstance(node, Root):
            return

        if node_uuid in self.collapsed_node_uuids:
            self.collapsed_node_uuids.remove(node_uuid)
        else:
            self.collapsed_node_uuids.add(node_uuid)

        self.render_frame(
            faculty=self.current_faculty,
            frame=self.current_frame,
        )

    def _is_node_collapsed(
        self,
        faculty: Faculty,
        node_uuid: str,
    ) -> bool:
        node = faculty.find_node(node_uuid)

        if not isinstance(node, ContainerNode):
            return False

        if node_uuid in self.collapsed_node_uuids:
            return True

        return bool(getattr(node, "expanded", True) is False)

    # ========================================================
    # Construcción del grafo espacial visible
    # ========================================================

    def _build_visible_space_graph(
        self,
        faculty: Faculty,
    ) -> dict[str, list[dict[str, Any]]]:
        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, str]] = []

        root = faculty.get_root()

        def should_show_node(node) -> bool:
            return isinstance(node, (Root, SpaceGroup, Space))

        def node_type_for(node) -> str:
            if isinstance(node, Root):
                return "root"

            if isinstance(node, SpaceGroup):
                return "spacegroup"

            if isinstance(node, Space):
                return "space"

            return "space"

        def visit(node_uuid: str) -> None:
            node = faculty.find_node(node_uuid)

            if node is None or not should_show_node(node):
                return

            is_container = isinstance(node, ContainerNode)
            is_collapsed = self._is_node_collapsed(faculty, node.uuid)

            nodes.append(
                {
                    "uuid": node.uuid,
                    "name": node.name,
                    "type": node_type_for(node),
                    "size": max(90.0, float(getattr(node, "size", 1.0)) * 100.0),
                    "expanded": None if not is_container else not is_collapsed,
                }
            )

            if is_container and not is_collapsed:
                for child_uuid in node.children_uuids:
                    child = faculty.find_node(child_uuid)

                    if child is None or not should_show_node(child):
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

    # ========================================================
    # Burbujas y marcadores
    # ========================================================

    def _add_bubbles_and_markers(
        self,
        faculty: Faculty,
        frame: dict[str, Any],
    ) -> None:
        infection_space_uuids = self._get_infection_space_uuids(frame)

        for node_uuid, item in self.nodes_by_uuid.items():
            node = faculty.find_node(node_uuid)

            if node is None:
                continue

            summary = None
            node_should_show_infection_marker = False

            if isinstance(node, Space):
                summary = self._get_space_summary(frame, node.uuid)
                node_should_show_infection_marker = node.uuid in infection_space_uuids

            elif (
                isinstance(node, SpaceGroup)
                and self._is_node_collapsed(faculty, node.uuid)
            ):
                descendant_spaces = self._get_descendant_space_uuids(faculty, node.uuid)

                summary = self._aggregate_space_summaries(
                    frame=frame,
                    space_uuids=descendant_spaces,
                )

                node_should_show_infection_marker = any(
                    space_uuid in infection_space_uuids
                    for space_uuid in descendant_spaces
                )

            if summary is not None:
                bubble_text = self._format_bubble_text(summary)
                bubble = SimulationBubbleItem(bubble_text)

                node_rect = item.boundingRect()
                node_pos = item.scenePos()

                bubble.setPos(
                    node_pos.x() + node_rect.right() + 14,
                    node_pos.y() + node_rect.top() - 10,
                )

                self.scene_obj.addItem(bubble)

            if node_should_show_infection_marker:
                marker = InfectionMarkerItem()

                node_rect = item.boundingRect()
                node_pos = item.scenePos()

                marker.setPos(
                    node_pos.x() + node_rect.right() - 8,
                    node_pos.y() + node_rect.top() - 14,
                )

                self.scene_obj.addItem(marker)

    def _get_infection_space_uuids(
        self,
        frame: dict[str, Any],
    ) -> set[str]:
        output: set[str] = set()

        events = frame.get("events", [])

        if not isinstance(events, list):
            return output

        for event in events:
            if not isinstance(event, dict):
                continue

            if event.get("event_type") != "infection":
                continue

            space_uuid = event.get("space_uuid")

            if space_uuid:
                output.add(str(space_uuid))

        return output

    def _get_space_summary(
        self,
        frame: dict[str, Any],
        space_uuid: str,
    ) -> Optional[dict[str, Any]]:
        summaries = frame.get("space_summaries", {})

        if not isinstance(summaries, dict):
            return None

        summary = summaries.get(space_uuid)

        if not isinstance(summary, dict):
            return None

        return dict(summary)

    def _aggregate_space_summaries(
        self,
        frame: dict[str, Any],
        space_uuids: list[str],
    ) -> Optional[dict[str, Any]]:
        if not space_uuids:
            return None

        summaries = frame.get("space_summaries", {})

        if not isinstance(summaries, dict):
            return None

        aggregate = {
            "space_uuid": "aggregated",
            "space_name": "Grupo contraído",
            "space_type_name": "Agregado",
            "present_agents": 0,
            "susceptible": 0,
            "exposed": 0,
            "infectious": 0,
            "recovered": 0,
            "isolated": 0,
            "new_infections": 0,
        }

        found_any = False

        numeric_fields = [
            "present_agents",
            "susceptible",
            "exposed",
            "infectious",
            "recovered",
            "isolated",
            "new_infections",
        ]

        for space_uuid in space_uuids:
            summary = summaries.get(space_uuid)

            if not isinstance(summary, dict):
                continue

            found_any = True

            for field in numeric_fields:
                aggregate[field] += int(summary.get(field, 0) or 0)

        if not found_any:
            return None

        aggregate["hidden_spaces"] = len(space_uuids)

        return aggregate

    def _format_bubble_text(
        self,
        summary: dict[str, Any],
    ) -> str:
        hidden_spaces = summary.get("hidden_spaces")

        first_line = f"P: {summary.get('present_agents', 0)}"

        if hidden_spaces is not None:
            first_line += f" | Esp: {hidden_spaces}"

        return (
            f"{first_line}\n"
            f"S: {summary.get('susceptible', 0)}   "
            f"E: {summary.get('exposed', 0)}\n"
            f"I: {summary.get('infectious', 0)}   "
            f"R: {summary.get('recovered', 0)}\n"
            f"Aisl: {summary.get('isolated', 0)}  "
            f"Inf+: {summary.get('new_infections', 0)}"
        )

    def _get_descendant_space_uuids(
        self,
        faculty: Faculty,
        node_uuid: str,
    ) -> list[str]:
        output: list[str] = []

        def visit(current_uuid: str) -> None:
            node = faculty.find_node(current_uuid)

            if isinstance(node, Space):
                output.append(node.uuid)
                return

            if isinstance(node, ContainerNode):
                for child_uuid in node.children_uuids:
                    visit(child_uuid)

        visit(node_uuid)

        return output
    
    # ========================================================
    # Movimiento visual de agentes
    # ========================================================

    def _stop_agent_animations(self) -> None:
        for animation in self.agent_animations:
            animation.stop()

        self.agent_animations.clear()

    def _add_agent_movements(
        self,
        faculty: Faculty,
        trace_data: Optional[dict[str, Any]],
        previous_frame: Optional[dict[str, Any]],
        current_frame: dict[str, Any],
        animation_duration_ms: int,
    ) -> None:
        if not trace_data or previous_frame is None:
            return

        previous_slot = int(previous_frame.get("slot", 0) or 0)
        current_slot = int(current_frame.get("slot", 0) or 0)

        if previous_slot == current_slot:
            return

        previous_locations = self._get_agent_locations_for_slot(
            trace_data=trace_data,
            slot=previous_slot,
        )
        current_locations = self._get_agent_locations_for_slot(
            trace_data=trace_data,
            slot=current_slot,
        )

        agent_ids = sorted(set(previous_locations.keys()) | set(current_locations.keys()))

        movements: list[tuple[str, str, str]] = []

        for agent_id in agent_ids:
            previous_space = previous_locations.get(agent_id)
            current_space = current_locations.get(agent_id)

            if previous_space == current_space:
                continue

            source_node_uuid = self._resolve_visible_node_for_location(
                faculty=faculty,
                space_uuid=previous_space,
            )
            target_node_uuid = self._resolve_visible_node_for_location(
                faculty=faculty,
                space_uuid=current_space,
            )

            if source_node_uuid is None and target_node_uuid is not None:
                source_node_uuid = faculty.root_uuid

            if target_node_uuid is None and source_node_uuid is not None:
                target_node_uuid = faculty.root_uuid

            if source_node_uuid is None or target_node_uuid is None:
                continue

            if source_node_uuid == target_node_uuid:
                continue

            if source_node_uuid not in self.nodes_by_uuid:
                continue

            if target_node_uuid not in self.nodes_by_uuid:
                continue

            movements.append((agent_id, source_node_uuid, target_node_uuid))

        if not movements:
            return

        # Evitamos saturar la escena si hay muchísimos agentes moviéndose.
        movements = movements[: self.max_moving_agents]

        current_agent_states = current_frame.get("agent_states", {})

        for agent_id, source_node_uuid, target_node_uuid in movements:
            path_node_uuids = self._find_visible_path(
                source_node_uuid=source_node_uuid,
                target_node_uuid=target_node_uuid,
            )

            if not path_node_uuids:
                path_node_uuids = [source_node_uuid, target_node_uuid]

            path_points = self._path_points_from_node_uuids(path_node_uuids)

            if len(path_points) < 2:
                continue

            state = None

            if isinstance(current_agent_states, dict):
                agent_state_data = current_agent_states.get(agent_id)

                if isinstance(agent_state_data, dict):
                    state = agent_state_data.get("state")

            dot = AgentMovementItem(
                path_points=path_points,
                color=self._color_for_agent_state(state),
                radius=5.0,
            )

            self.scene_obj.addItem(dot)

            animation = QPropertyAnimation(dot, b"progress", self)
            animation.setStartValue(0.0)
            animation.setEndValue(1.0)
            animation.setDuration(max(80, int(animation_duration_ms)))
            animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

            animation.finished.connect(dot.deleteLater)

            self.agent_animations.append(animation)
            animation.start()

    def _get_agent_locations_for_slot(
        self,
        trace_data: dict[str, Any],
        slot: int,
    ) -> dict[str, Optional[str]]:
        locations = trace_data.get("locations", [])

        if not isinstance(locations, list):
            return {}

        output: dict[str, Optional[str]] = {}

        for location in locations:
            if not isinstance(location, dict):
                continue

            start_slot = int(location.get("start_slot", -1) or -1)
            end_slot = int(location.get("end_slot", -1) or -1)

            # El agente está en ese espacio durante [start_slot, end_slot).
            if start_slot <= slot < end_slot:
                agent_id = location.get("agent_id")

                if agent_id:
                    output[str(agent_id)] = location.get("space_uuid")

        return output

    def _resolve_visible_node_for_location(
        self,
        faculty: Faculty,
        space_uuid: Optional[str],
    ) -> Optional[str]:
        if space_uuid is None:
            return None

        if space_uuid in self.nodes_by_uuid:
            return space_uuid

        node = faculty.find_node(space_uuid)

        if node is None:
            return None

        parent_uuid = node.parent_uuid

        while parent_uuid is not None:
            parent = faculty.find_node(parent_uuid)

            if parent is None:
                return None

            if parent.uuid in self.nodes_by_uuid:
                return parent.uuid

            parent_uuid = parent.parent_uuid

        return None

    def _find_visible_path(
        self,
        source_node_uuid: str,
        target_node_uuid: str,
    ) -> list[str]:
        if source_node_uuid == target_node_uuid:
            return [source_node_uuid]

        adjacency: dict[str, list[str]] = {}

        for edge in self.visible_edges:
            source = edge.get("source")
            target = edge.get("target")

            if source is None or target is None:
                continue

            adjacency.setdefault(source, []).append(target)
            adjacency.setdefault(target, []).append(source)

        visited = {source_node_uuid}
        queue: list[tuple[str, list[str]]] = [
            (source_node_uuid, [source_node_uuid])
        ]

        while queue:
            current, path = queue.pop(0)

            for neighbor in adjacency.get(current, []):
                if neighbor in visited:
                    continue

                next_path = path + [neighbor]

                if neighbor == target_node_uuid:
                    return next_path

                visited.add(neighbor)
                queue.append((neighbor, next_path))

        return []

    def _path_points_from_node_uuids(
        self,
        node_uuids: list[str],
    ) -> list[QPointF]:
        points: list[QPointF] = []

        for node_uuid in node_uuids:
            item = self.nodes_by_uuid.get(node_uuid)

            if item is None:
                continue

            points.append(QPointF(item.scenePos().x(), item.scenePos().y()))

        return points

    def _color_for_agent_state(
        self,
        state: Optional[str],
    ) -> QColor:
        state = str(state or "").lower()

        if state == "susceptible":
            return QColor("#3498db")

        if state == "exposed":
            return QColor("#f1c40f")

        if state == "infectious":
            return QColor("#e74c3c")

        if state == "recovered":
            return QColor("#2ecc71")

        return QColor("#7f8c8d")

    # ========================================================
    # Navegación / zoom
    # ========================================================

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._last_mouse_pos = event.position().toPoint()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
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

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton and self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
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

    # ========================================================
    # Layout
    # ========================================================

    def _calculate_standard_layout(
        self,
        nodes: list[dict],
        edges: list[dict],
    ) -> dict[str, tuple[float, float]]:
        if not nodes:
            return {}

        children_by_parent: dict[str, list[str]] = {}
        targets = set()
        type_by_uuid = {node["uuid"]: node.get("type", "") for node in nodes}

        for edge in edges:
            children_by_parent.setdefault(edge["source"], []).append(edge["target"])
            targets.add(edge["target"])

        root_candidates = [
            node["uuid"]
            for node in nodes
            if node["uuid"] not in targets
        ]

        root_uuid = root_candidates[0] if root_candidates else nodes[0]["uuid"]

        subtree_size_cache: dict[str, int] = {}

        def subtree_size(node_uuid: str) -> int:
            if node_uuid in subtree_size_cache:
                return subtree_size_cache[node_uuid]

            children = children_by_parent.get(node_uuid, [])

            if not children:
                subtree_size_cache[node_uuid] = 1
                return 1

            total = sum(subtree_size(child_uuid) for child_uuid in children)
            subtree_size_cache[node_uuid] = max(1, total)
            return subtree_size_cache[node_uuid]

        def is_container(node_uuid: str) -> bool:
            return type_by_uuid.get(node_uuid, "") in {"root", "group", "spacegroup"}

        def sort_children(child_ids: list[str]) -> list[str]:
            return sorted(
                child_ids,
                key=lambda uid: (
                    0 if is_container(uid) else 1,
                    -subtree_size(uid),
                    uid,
                ),
            )

        def required_radius_for_children(
            child_count: int,
            usable_span: float,
        ) -> float:
            if child_count <= 1:
                return 0.0

            min_arc_per_node = 220.0
            min_angle = max(usable_span / child_count, 0.10)

            return min_arc_per_node / min_angle

        positions: dict[str, tuple[float, float]] = {}

        base_radius = 340
        angle_padding = math.radians(10)
        min_child_span = math.radians(26)

        def place_subtree(
            node_uuid: str,
            depth: int,
            center_angle: float,
            angle_span: float,
            forced_radius: Optional[float] = None,
        ) -> None:
            if depth == 0:
                positions[node_uuid] = (0, 0)
            else:
                current_radius = (
                    forced_radius
                    if forced_radius is not None
                    else base_radius * depth
                )
                x = math.cos(center_angle) * current_radius
                y = math.sin(center_angle) * current_radius
                positions[node_uuid] = (x, y)

            children = sort_children(children_by_parent.get(node_uuid, []))

            if not children:
                return

            if depth == 0:
                usable_span = (2 * math.pi) - angle_padding
            else:
                usable_span = max(
                    angle_span - angle_padding,
                    min_child_span * len(children),
                )
                usable_span = min(usable_span, angle_span)

            total_weight = sum(subtree_size(child_uuid) for child_uuid in children)

            child_depth = depth + 1
            default_child_radius = base_radius * child_depth
            spacing_child_radius = required_radius_for_children(
                len(children),
                usable_span,
            )
            child_radius = max(default_child_radius, spacing_child_radius)

            cursor = center_angle - (usable_span / 2)

            for child_uuid in children:
                child_weight = subtree_size(child_uuid)
                child_span = usable_span * (child_weight / total_weight)
                child_center = cursor + (child_span / 2)

                next_span = max(child_span * 0.82, min_child_span)

                place_subtree(
                    node_uuid=child_uuid,
                    depth=child_depth,
                    center_angle=child_center,
                    angle_span=next_span,
                    forced_radius=child_radius,
                )

                cursor += child_span

        place_subtree(
            node_uuid=root_uuid,
            depth=0,
            center_angle=-math.pi / 2,
            angle_span=(2 * math.pi) - angle_padding,
        )

        return positions