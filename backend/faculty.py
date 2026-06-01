from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, List, Optional
import csv
import uuid


# ============================================================
# OPCIONES DEL BUILDER
# ============================================================

TIME_OPTIONS = [
    "06:00", "07:00", "08:00", "09:00", "10:00", "11:00",
    "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
    "18:00", "19:00", "20:00", "21:00", "22:00"
]

SLOT_MINUTE_OPTIONS = [15, 30, 60]

CALENDAR_DAY_OPTIONS = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]


# ============================================================
# HORARIOS
# ============================================================

@dataclass
class ScheduleBlock:
    uuid: str
    day_of_week: str
    start_time: str
    end_time: str
    space_uuid: Optional[str] = None


# ============================================================
# MODELO DE NODOS
# ============================================================

@dataclass
class Node:
    uuid: str
    name: str
    parent_uuid: Optional[str] = None
    size: float = 1.0

    def is_root(self) -> bool:
        return False

    def is_container(self) -> bool:
        return False

    def is_space(self) -> bool:
        return False

    def is_space_group(self) -> bool:
        return False

    def is_career(self) -> bool:
        return False

    def is_course(self) -> bool:
        return False

    def is_course_group(self) -> bool:
        return False


@dataclass
class ContainerNode(Node):
    children_uuids: List[str] = field(default_factory=list)
    expanded: bool = True

    def is_container(self) -> bool:
        return True


@dataclass
class Root(ContainerNode):
    opening_time: str = "08:00"
    closing_time: str = "20:00"
    schedule_slot_minutes: int = 30
    default_ventilated: bool = False
    calendar_days: List[str] = field(
        default_factory=lambda: ["monday", "tuesday", "wednesday", "thursday", "friday"]
    )

    def is_root(self) -> bool:
        return True


@dataclass
class SpaceGroup(ContainerNode):
    default_ventilated: bool = False
    opening_time_override: Optional[str] = None
    closing_time_override: Optional[str] = None

    def is_space_group(self) -> bool:
        return True


@dataclass
class Space(Node):
    capacity: Optional[int] = None

    space_type_uuid: Optional[str] = None
    ventilated: bool = False
    opening_time_override: Optional[str] = None
    closing_time_override: Optional[str] = None

    position_x: float = 0.0
    position_y: float = 0.0

    def is_space(self) -> bool:
        return True


@dataclass
class Career(ContainerNode):
    students_by_year: Optional[int] = None
    default_attendance_rate: Optional[float] = None
    mean_age: Optional[float] = None
    std_age: Optional[float] = None
    sex_ratio: Optional[float] = None

    def is_career(self) -> bool:
        return True


@dataclass
class Course(ContainerNode):
    career_uuid: Optional[str] = None

    number_of_students: Optional[int] = None
    attendance_rate: Optional[float] = None
    mean_age: Optional[float] = None
    std_age: Optional[float] = None
    sex_ratio: Optional[float] = None

    base_schedule: List[ScheduleBlock] = field(default_factory=list)

    def is_course(self) -> bool:
        return True


@dataclass
class CourseGroup(ContainerNode):
    course_uuid: Optional[str] = None

    number_of_students: Optional[int] = None
    attendance_rate: Optional[float] = None
    mean_age: Optional[float] = None
    std_age: Optional[float] = None
    sex_ratio: Optional[float] = None

    schedule_overrides: List[ScheduleBlock] = field(default_factory=list)

    def is_course_group(self) -> bool:
        return True


@dataclass
class SpaceType:
    uuid: str
    name: str
    contact_level: float = 1.0
    duration_relevance: float = 1.0
    is_transit_type: bool = False
    is_recreation_type: bool = False
    default_ventilated: bool = False
    mask_effect_relevance: float = 1.0
    ventilation_effect_relevance: float = 1.0


# ============================================================
# FACULTY / ESCENARIO
# ============================================================

class Faculty:
    ROOT_NAME = "Pasillo"
    MIN_NODE_SIZE = 0.5
    MAX_NODE_SIZE = 3.0

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.warnings: List[str] = []
        self.selected_node = None

        self.root_uuid = self._generate_uuid()
        root = Root(
            uuid=self.root_uuid,
            name=self.ROOT_NAME,
            parent_uuid=None,
            expanded=True,
        )
        self.nodes[self.root_uuid] = root

        self.space_types: List[SpaceType] = [
            SpaceType(uuid="classroom", name="Classroom"),
            SpaceType(uuid="lab", name="Laboratory"),
            SpaceType(uuid="office", name="Office"),
            SpaceType(uuid="corridor", name="Corridor", is_transit_type=True),
        ]

    # -------------------------
    # Utilidades internas
    # -------------------------

    @staticmethod
    def _generate_uuid() -> str:
        return str(uuid.uuid4())

    def _generate_schedule_block_uuid(self) -> str:
        return self._generate_uuid()

    def _add_node(self, node: Node) -> None:
        if node.uuid in self.nodes:
            raise ValueError(f"Ya existe un nodo con UUID {node.uuid}")
        self.nodes[node.uuid] = node

    def _get_node(self, node_uuid: str) -> Node:
        if node_uuid not in self.nodes:
            raise KeyError(f"No existe el nodo con UUID {node_uuid}")
        return self.nodes[node_uuid]

    def _get_container(self, node_uuid: str) -> ContainerNode:
        node = self._get_node(node_uuid)
        if not isinstance(node, ContainerNode):
            raise TypeError(f"El nodo {node_uuid} no puede contener hijos")
        return node

    def _attach_child(self, parent_uuid: str, child_uuid: str) -> None:
        parent = self._get_container(parent_uuid)
        child = self._get_node(child_uuid)

        if child_uuid not in parent.children_uuids:
            parent.children_uuids.append(child_uuid)

        child.parent_uuid = parent_uuid

    def _iter_nodes_for_saving(self) -> list[Node]:
        ordered_nodes: list[Node] = []

        def visit(node_uuid: str) -> None:
            node = self._get_node(node_uuid)
            ordered_nodes.append(node)

            if isinstance(node, ContainerNode):
                for child_uuid in node.children_uuids:
                    if child_uuid in self.nodes:
                        visit(child_uuid)

        visit(self.root_uuid)
        return ordered_nodes

    def _is_descendant(self, possible_descendant_uuid: str, possible_ancestor_uuid: str) -> bool:
        current_uuid = possible_descendant_uuid

        while current_uuid is not None:
            if current_uuid == possible_ancestor_uuid:
                return True

            current_node = self._get_node(current_uuid)
            current_uuid = current_node.parent_uuid

        return False

    def _can_parent_accept_child(self, parent: Node, child: Node) -> bool:
        if isinstance(parent, Root):
            return isinstance(child, (SpaceGroup, Space, Career))

        if isinstance(parent, SpaceGroup):
            return isinstance(child, (SpaceGroup, Space))

        if isinstance(parent, Career):
            return isinstance(child, Course)

        if isinstance(parent, Course):
            return isinstance(child, CourseGroup)

        if isinstance(parent, CourseGroup):
            return False

        return False

    def _schedule_block_key(self, block: ScheduleBlock) -> tuple[str, str, str]:
        return (block.day_of_week, block.start_time, block.end_time)

    def _clone_schedule_blocks(self, blocks: List[ScheduleBlock]) -> List[ScheduleBlock]:
        cloned: List[ScheduleBlock] = []
        for block in blocks:
            cloned.append(
                ScheduleBlock(
                    uuid=self._generate_schedule_block_uuid(),
                    day_of_week=block.day_of_week,
                    start_time=block.start_time,
                    end_time=block.end_time,
                    space_uuid=block.space_uuid,
                )
            )
        return cloned

    def _sort_schedule_blocks(self, blocks: List[ScheduleBlock]) -> List[ScheduleBlock]:
        day_order = {day: i for i, day in enumerate(CALENDAR_DAY_OPTIONS)}
        return sorted(
            blocks,
            key=lambda block: (
                day_order.get(block.day_of_week, 999),
                block.start_time,
                block.end_time,
            ),
        )

    def _value_to_csv(self, value):
        if value is None:
            return ""
        if isinstance(value, bool):
            return "1" if value else "0"
        return str(value)


    @staticmethod
    def _csv_to_optional_str(value: str):
        value = (value or "").strip()
        return value if value != "" else None


    @staticmethod
    def _csv_to_optional_int(value: str):
        value = (value or "").strip()
        return int(value) if value != "" else None


    @staticmethod
    def _csv_to_optional_float(value: str):
        value = (value or "").strip()
        return float(value) if value != "" else None


    @staticmethod
    def _csv_to_bool(value: str, default: bool = False):
        value = (value or "").strip().lower()

        if value in {"1", "true", "yes", "sí", "si"}:
            return True

        if value in {"0", "false", "no"}:
            return False

        return default

    # -------------------------
    # Propiedades generales
    # -------------------------

    def update_faculty_properties(
        self,
        name: Optional[str] = None,
        opening_time: Optional[str] = None,
        closing_time: Optional[str] = None,
        schedule_slot_minutes: Optional[int] = None,
        default_ventilated: Optional[bool] = None,
        calendar_days: Optional[List[str]] = None,
    ) -> None:
        root = self._get_node(self.root_uuid)

        if not isinstance(root, Root):
            raise ValueError("La raíz de la facultad no es válida.")

        if name is not None:
            root.name = name.strip()

        if opening_time is not None:
            root.opening_time = opening_time

        if closing_time is not None:
            root.closing_time = closing_time

        if schedule_slot_minutes is not None:
            root.schedule_slot_minutes = schedule_slot_minutes

        if default_ventilated is not None:
            root.default_ventilated = default_ventilated

        if calendar_days is not None:
            root.calendar_days = list(calendar_days)

    def update_space_group_properties(
        self,
        group_uuid: str,
        name: Optional[str] = None,
        default_ventilated: Optional[bool] = None,
        opening_time_override: Optional[str] = None,
        closing_time_override: Optional[str] = None,
    ) -> None:
        node = self._get_node(group_uuid)

        if not isinstance(node, SpaceGroup):
            raise ValueError("Solo los grupos espaciales pueden tener propiedades de grupo espacial.")

        if name is not None:
            node.name = name.strip()

        if default_ventilated is not None:
            node.default_ventilated = default_ventilated

        if opening_time_override is not None:
            node.opening_time_override = opening_time_override

        if closing_time_override is not None:
            node.closing_time_override = closing_time_override

    def update_space_properties(
        self,
        node_uuid: str,
        name: Optional[str] = None,
        capacity: Optional[int] = None,
        space_type_uuid: Optional[str] = None,
        ventilated: Optional[bool] = None,
        opening_time_override: Optional[str] = None,
        closing_time_override: Optional[str] = None,
        position_x: Optional[float] = None,
        position_y: Optional[float] = None,
    ) -> None:
        node = self._get_node(node_uuid)

        if not isinstance(node, Space):
            raise ValueError("Solo los espacios pueden tener propiedades de espacio.")

        if name is not None:
            node.name = name.strip()

        if capacity is not None:
            node.capacity = capacity

        node.space_type_uuid = space_type_uuid

        if ventilated is not None:
            node.ventilated = ventilated

        node.opening_time_override = opening_time_override
        node.closing_time_override = closing_time_override

        if position_x is not None:
            node.position_x = position_x

        if position_y is not None:
            node.position_y = position_y

    def update_career_properties(
        self,
        career_uuid: str,
        name: Optional[str] = None,
        students_by_year: Optional[int] = None,
        default_attendance_rate: Optional[float] = None,
        mean_age: Optional[float] = None,
        std_age: Optional[float] = None,
        sex_ratio: Optional[float] = None,
    ) -> None:
        node = self._get_node(career_uuid)

        if not isinstance(node, Career):
            raise ValueError("Solo las carreras pueden tener propiedades de carrera.")

        if name is not None:
            node.name = name.strip()

        if students_by_year is not None:
            node.students_by_year = students_by_year

        if default_attendance_rate is not None:
            node.default_attendance_rate = default_attendance_rate

        if mean_age is not None:
            node.mean_age = mean_age

        if std_age is not None:
            node.std_age = std_age

        if sex_ratio is not None:
            node.sex_ratio = sex_ratio

    def update_course_properties(
        self,
        course_uuid: str,
        name: Optional[str] = None,
        number_of_students: Optional[int] = None,
        attendance_rate: Optional[float] = None,
        mean_age: Optional[float] = None,
        std_age: Optional[float] = None,
        sex_ratio: Optional[float] = None,
    ) -> None:
        node = self._get_node(course_uuid)

        if not isinstance(node, Course):
            raise ValueError("Solo los cursos pueden tener propiedades de curso.")

        if name is not None:
            node.name = name.strip()

        if number_of_students is not None:
            node.number_of_students = number_of_students

        if attendance_rate is not None:
            node.attendance_rate = attendance_rate

        if mean_age is not None:
            node.mean_age = mean_age

        if std_age is not None:
            node.std_age = std_age

        if sex_ratio is not None:
            node.sex_ratio = sex_ratio

    def update_course_group_properties(
        self,
        group_uuid: str,
        name: Optional[str] = None,
        number_of_students: Optional[int] = None,
        attendance_rate: Optional[float] = None,
        mean_age: Optional[float] = None,
        std_age: Optional[float] = None,
        sex_ratio: Optional[float] = None,
    ) -> None:
        node = self._get_node(group_uuid)

        if not isinstance(node, CourseGroup):
            raise ValueError("Solo los grupos de curso pueden tener propiedades de grupo de curso.")

        if name is not None:
            node.name = name.strip()

        if number_of_students is not None:
            node.number_of_students = number_of_students

        if attendance_rate is not None:
            node.attendance_rate = attendance_rate

        if mean_age is not None:
            node.mean_age = mean_age

        if std_age is not None:
            node.std_age = std_age

        if sex_ratio is not None:
            node.sex_ratio = sex_ratio

    def update_node_size(self, node_uuid: str, size: float) -> None:
        node = self._get_node(node_uuid)

        if size < self.MIN_NODE_SIZE:
            size = self.MIN_NODE_SIZE
        if size > self.MAX_NODE_SIZE:
            size = self.MAX_NODE_SIZE

        node.size = size

    # -------------------------
    # Creación de nodos
    # -------------------------

    def create_space_group(
        self,
        name: str,
        parent_uuid: Optional[str] = None,
        node_uuid: Optional[str] = None,
    ) -> SpaceGroup:
        if node_uuid is None:
            node_uuid = self._generate_uuid()
        if parent_uuid is None:
            parent_uuid = self.root_uuid

        parent = self._get_node(parent_uuid)
        group = SpaceGroup(uuid=node_uuid, name=name, parent_uuid=None)

        if not self._can_parent_accept_child(parent, group):
            raise ValueError("Ese nodo no puede contener grupos espaciales.")

        self._add_node(group)
        self._attach_child(parent_uuid, group.uuid)
        return group

    def create_group(self, name: str, parent_uuid: Optional[str] = None, node_uuid: Optional[str] = None) -> SpaceGroup:
        return self.create_space_group(name=name, parent_uuid=parent_uuid, node_uuid=node_uuid)

    def create_space(
        self,
        name: str,
        parent_uuid: Optional[str] = None,
        node_uuid: Optional[str] = None,
    ) -> Space:
        if node_uuid is None:
            node_uuid = self._generate_uuid()
        if parent_uuid is None:
            parent_uuid = self.root_uuid

        parent = self._get_node(parent_uuid)
        space = Space(uuid=node_uuid, name=name, parent_uuid=None)

        if not self._can_parent_accept_child(parent, space):
            raise ValueError("Ese nodo no puede contener espacios.")

        self._add_node(space)
        self._attach_child(parent_uuid, space.uuid)
        return space

    def create_career(
        self,
        name: str,
        parent_uuid: Optional[str] = None,
        node_uuid: Optional[str] = None,
    ) -> Career:
        if node_uuid is None:
            node_uuid = self._generate_uuid()
        if parent_uuid is None:
            parent_uuid = self.root_uuid

        parent = self._get_node(parent_uuid)
        career = Career(uuid=node_uuid, name=name, parent_uuid=None)

        if not self._can_parent_accept_child(parent, career):
            raise ValueError("Ese nodo no puede contener carreras.")

        self._add_node(career)
        self._attach_child(parent_uuid, career.uuid)
        return career

    def create_course(
        self,
        name: str,
        career_uuid: str,
        node_uuid: Optional[str] = None,
    ) -> Course:
        if node_uuid is None:
            node_uuid = self._generate_uuid()

        parent = self._get_node(career_uuid)
        course = Course(
            uuid=node_uuid,
            name=name,
            parent_uuid=None,
            career_uuid=career_uuid,
        )

        if not self._can_parent_accept_child(parent, course):
            raise ValueError("Ese nodo no puede contener cursos.")

        self._add_node(course)
        self._attach_child(career_uuid, course.uuid)
        return course

    def create_course_group(
        self,
        name: str,
        course_uuid: str,
        node_uuid: Optional[str] = None,
        copy_course_schedule: bool = False,
    ) -> CourseGroup:
        if node_uuid is None:
            node_uuid = self._generate_uuid()

        parent = self._get_node(course_uuid)
        if not isinstance(parent, Course):
            raise ValueError("Los grupos de curso solo pueden crearse dentro de un curso.")

        group = CourseGroup(
            uuid=node_uuid,
            name=name,
            parent_uuid=None,
            course_uuid=course_uuid,
        )

        # No copiamos el horario del curso.
        # El grupo lo hereda visualmente desde course_base_schedule.
        group.schedule_overrides = []

        if not self._can_parent_accept_child(parent, group):
            raise ValueError("Ese nodo no puede contener grupos de curso.")

        self._add_node(group)
        self._attach_child(course_uuid, group.uuid)
        return group

    # -------------------------
    # API pública básica
    # -------------------------

    def get_root(self) -> Root:
        root = self._get_node(self.root_uuid)
        if not isinstance(root, Root):
            raise ValueError("La raíz no es válida.")
        return root

    def get_children(self, node_uuid: str) -> List[Node]:
        node = self._get_node(node_uuid)

        if not isinstance(node, ContainerNode):
            return []

        return [self._get_node(child_uuid) for child_uuid in node.children_uuids]

    def find_node(self, node_uuid: str) -> Optional[Node]:
        return self.nodes.get(node_uuid)

    def rename_node(self, node_uuid: str, new_name: str) -> None:
        node = self._get_node(node_uuid)
        node.name = new_name.strip()

    def rename_faculty(self, new_name: str) -> None:
        root = self._get_node(self.root_uuid)
        root.name = new_name.strip()

    def delete_node(self, node_uuid: str) -> None:
        node = self._get_node(node_uuid)

        if isinstance(node, Root):
            raise ValueError("No se puede borrar el nodo raíz.")

        parent_uuid = node.parent_uuid or self.root_uuid
        parent = self._get_container(parent_uuid)

        if isinstance(node, ContainerNode):
            children_to_move = list(node.children_uuids)
        else:
            children_to_move = []

        try:
            insert_index = parent.children_uuids.index(node_uuid)
        except ValueError:
            insert_index = len(parent.children_uuids)

        if node_uuid in parent.children_uuids:
            parent.children_uuids.remove(node_uuid)

        for offset, child_uuid in enumerate(children_to_move):
            child = self._get_node(child_uuid)
            child.parent_uuid = parent_uuid
            parent.children_uuids.insert(insert_index + offset, child_uuid)

        if isinstance(node, ContainerNode):
            node.children_uuids.clear()

        self.selected_node = None
        del self.nodes[node_uuid]

    def move_node(self, node_uuid: str, new_parent_uuid: str) -> None:
        node = self._get_node(node_uuid)
        new_parent = self._get_node(new_parent_uuid)

        if isinstance(node, Root):
            raise ValueError("No se puede mover el nodo raíz.")

        if not isinstance(new_parent, ContainerNode):
            raise ValueError("El nuevo padre debe ser un nodo contenedor.")

        if node_uuid == new_parent_uuid:
            raise ValueError("Un nodo no puede moverse dentro de sí mismo.")

        if isinstance(node, ContainerNode):
            if self._is_descendant(
                possible_descendant_uuid=new_parent_uuid,
                possible_ancestor_uuid=node_uuid,
            ):
                raise ValueError("No se puede mover un contenedor dentro de uno de sus descendientes.")

        if not self._can_parent_accept_child(new_parent, node):
            raise ValueError("Ese movimiento no es válido para la jerarquía del builder.")

        old_parent_uuid = node.parent_uuid
        if old_parent_uuid is not None:
            old_parent = self._get_container(old_parent_uuid)
            if node_uuid in old_parent.children_uuids:
                old_parent.children_uuids.remove(node_uuid)

        new_parent_container = self._get_container(new_parent_uuid)
        new_parent_container.children_uuids.append(node_uuid)
        node.parent_uuid = new_parent_uuid

        if isinstance(node, Course):
            node.career_uuid = new_parent_uuid if isinstance(new_parent, Career) else node.career_uuid

        if isinstance(node, CourseGroup):
            node.course_uuid = new_parent_uuid if isinstance(new_parent, Course) else node.course_uuid

    def get_valid_parents(self, node_uuid: str) -> list[Node]:
        node = self._get_node(node_uuid)

        if isinstance(node, Root):
            return []

        valid_parents: list[Node] = []

        for candidate in self.nodes.values():
            if not isinstance(candidate, ContainerNode):
                continue

            if candidate.uuid == node_uuid:
                continue

            if self._is_descendant(
                possible_descendant_uuid=candidate.uuid,
                possible_ancestor_uuid=node_uuid,
            ):
                continue

            if not self._can_parent_accept_child(candidate, node):
                continue

            valid_parents.append(candidate)

        return valid_parents

    def get_visible_nodes(self) -> list[Node]:
        visible_nodes: list[Node] = []

        def visit(node_uuid: str) -> None:
            node = self._get_node(node_uuid)

            if not isinstance(node, Root):
                visible_nodes.append(node)

            if isinstance(node, Root):
                for child_uuid in node.children_uuids:
                    visit(child_uuid)
            elif isinstance(node, ContainerNode) and node.expanded:
                for child_uuid in node.children_uuids:
                    visit(child_uuid)

        visit(self.root_uuid)
        return visible_nodes

    def set_container_expanded(self, node_uuid: str, expanded: bool) -> None:
        node = self._get_node(node_uuid)

        if not isinstance(node, ContainerNode):
            raise ValueError("Solo los nodos contenedores pueden expandirse o contraerse.")

        if isinstance(node, Root):
            raise ValueError("La raíz no debe expandirse ni contraerse.")

        node.expanded = expanded

    def toggle_container_expanded(self, node_uuid: str) -> None:
        node = self._get_node(node_uuid)

        if not isinstance(node, ContainerNode):
            raise ValueError("Solo los nodos contenedores pueden expandirse o contraerse.")

        if isinstance(node, Root):
            raise ValueError("La raíz no debe expandirse ni contraerse.")

        node.expanded = not node.expanded

    def set_group_expanded(self, group_uuid: str, expanded: bool) -> None:
        self.set_container_expanded(group_uuid, expanded)

    def toggle_group_expanded(self, group_uuid: str) -> None:
        self.toggle_container_expanded(group_uuid)

    def select_node(self, node_uuid: str) -> None:
        node = self._get_node(node_uuid)
        self.selected_node = node

    # -------------------------
    # Horarios
    # -------------------------

    def create_schedule_block(
        self,
        day_of_week: str,
        start_time: str,
        end_time: str,
        space_uuid: Optional[str] = None,
        block_uuid: Optional[str] = None,
    ) -> ScheduleBlock:
        if block_uuid is None:
            block_uuid = self._generate_schedule_block_uuid()

        return ScheduleBlock(
            uuid=block_uuid,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            space_uuid=space_uuid,
        )

    def set_course_base_schedule(self, course_uuid: str, blocks: List[ScheduleBlock]) -> None:
        node = self._get_node(course_uuid)

        if not isinstance(node, Course):
            raise ValueError("Solo los cursos tienen horario base.")

        node.base_schedule = self._sort_schedule_blocks(list(blocks))

    def set_course_group_schedule_overrides(self, group_uuid: str, blocks: List[ScheduleBlock]) -> None:
        node = self._get_node(group_uuid)

        if not isinstance(node, CourseGroup):
            raise ValueError("Solo los grupos de curso tienen schedule overrides.")

        node.schedule_overrides = self._sort_schedule_blocks(list(blocks))

    def add_course_schedule_block(
        self,
        course_uuid: str,
        day_of_week: str,
        start_time: str,
        end_time: str,
        space_uuid: Optional[str] = None,
    ) -> ScheduleBlock:
        course = self._get_node(course_uuid)

        if not isinstance(course, Course):
            raise ValueError("Solo los cursos pueden recibir bloques de horario base.")

        block = self.create_schedule_block(day_of_week, start_time, end_time, space_uuid)
        course.base_schedule.append(block)
        course.base_schedule = self._sort_schedule_blocks(course.base_schedule)
        return block

    def add_course_group_schedule_override(
        self,
        group_uuid: str,
        day_of_week: str,
        start_time: str,
        end_time: str,
        space_uuid: Optional[str] = None,
    ) -> ScheduleBlock:
        group = self._get_node(group_uuid)

        if not isinstance(group, CourseGroup):
            raise ValueError("Solo los grupos de curso pueden recibir overrides de horario.")

        block = self.create_schedule_block(day_of_week, start_time, end_time, space_uuid)
        group.schedule_overrides.append(block)
        group.schedule_overrides = self._sort_schedule_blocks(group.schedule_overrides)
        return block

    def remove_course_schedule_block(self, course_uuid: str, block_uuid: str) -> None:
        course = self._get_node(course_uuid)

        if not isinstance(course, Course):
            raise ValueError("Solo los cursos pueden eliminar bloques de su horario base.")

        course.base_schedule = [block for block in course.base_schedule if block.uuid != block_uuid]

    def remove_course_group_schedule_override(self, group_uuid: str, block_uuid: str) -> None:
        group = self._get_node(group_uuid)

        if not isinstance(group, CourseGroup):
            raise ValueError("Solo los grupos de curso pueden eliminar overrides de horario.")

        group.schedule_overrides = [block for block in group.schedule_overrides if block.uuid != block_uuid]

    def get_effective_schedule_for_course_group(self, group_uuid: str) -> List[ScheduleBlock]:
        node = self._get_node(group_uuid)

        if not isinstance(node, CourseGroup):
            raise ValueError("El nodo no es un grupo de curso.")

        parent = self._get_node(node.parent_uuid) if node.parent_uuid else None

        if isinstance(parent, Course):
            inherited_blocks = list(parent.base_schedule)
        elif isinstance(parent, CourseGroup):
            inherited_blocks = self.get_effective_schedule_for_course_group(parent.uuid)
        else:
            inherited_blocks = []

        merged_by_slot = {
            self._schedule_block_key(block): block
            for block in inherited_blocks
        }

        for block in node.schedule_overrides:
            merged_by_slot[self._schedule_block_key(block)] = block

        return self._sort_schedule_blocks(list(merged_by_slot.values()))

    # -------------------------
    # Opciones para formularios
    # -------------------------

    def get_time_options(self) -> list[str]:
        return TIME_OPTIONS

    def get_schedule_slot_options(self) -> list[int]:
        return SLOT_MINUTE_OPTIONS

    def get_calendar_day_options(self) -> list[str]:
        return CALENDAR_DAY_OPTIONS

    def get_space_types(self) -> list[SpaceType]:
        return self.space_types

    def get_all_spaces(self) -> list[Space]:
        return [node for node in self.nodes.values() if isinstance(node, Space)]

    # -------------------------
    # Carga desde CSV
    # -------------------------

    @classmethod
    def load_from_csv(cls, csv_path: str | Path) -> "Faculty":
        faculty = cls()
        csv_path = Path(csv_path)

        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            required_columns = {"uuid", "node_type", "name", "parent_uuid"}
            missing = required_columns - set(reader.fieldnames or [])
            if missing:
                raise ValueError(f"Faltan columnas obligatorias en el CSV: {sorted(missing)}")

            for line_number, row in enumerate(reader, start=2):
                node_uuid = (row.get("uuid") or "").strip()
                node_type = (row.get("node_type") or "").strip().lower()
                name = (row.get("name") or "").strip()
                parent_uuid = (row.get("parent_uuid") or "").strip() or None

                if not node_uuid:
                    node_uuid = faculty._generate_uuid()
                    faculty.warnings.append(
                        f"Línea {line_number}: UUID vacío para '{name}'. Se generó {node_uuid}."
                    )

                if node_uuid in faculty.nodes:
                    faculty.warnings.append(
                        f"Línea {line_number}: UUID duplicado ({node_uuid}) en '{name}'. Se omite la fila."
                    )
                    continue

                if node_type == "spacegroup":
                    node = SpaceGroup(uuid=node_uuid, name=name, parent_uuid=parent_uuid)
                elif node_type == "group":
                    node = SpaceGroup(uuid=node_uuid, name=name, parent_uuid=parent_uuid)
                elif node_type == "space":
                    node = Space(uuid=node_uuid, name=name, parent_uuid=parent_uuid)
                elif node_type == "career":
                    node = Career(uuid=node_uuid, name=name, parent_uuid=parent_uuid)
                elif node_type == "course":
                    node = Course(uuid=node_uuid, name=name, parent_uuid=parent_uuid, career_uuid=parent_uuid)
                elif node_type == "coursegroup":
                    node = CourseGroup(uuid=node_uuid, name=name, parent_uuid=parent_uuid, course_uuid=parent_uuid)
                else:
                    faculty.warnings.append(
                        f"Línea {line_number}: node_type inválido '{node_type}' en '{name}'. Se omite la fila."
                    )
                    continue

                faculty._add_node(node)

        for node_uuid, node in list(faculty.nodes.items()):
            if node_uuid == faculty.root_uuid:
                continue

            desired_parent_uuid = node.parent_uuid

            if desired_parent_uuid is None:
                faculty._attach_child(faculty.root_uuid, node_uuid)
                faculty.warnings.append(
                    f"Nodo '{node.name}' ({node.uuid}) sin padre. Conectado a Pasillo."
                )
                continue

            parent = faculty.find_node(desired_parent_uuid)
            if parent is None:
                faculty._attach_child(faculty.root_uuid, node_uuid)
                faculty.warnings.append(
                    f"Nodo '{node.name}' ({node.uuid}) con padre inexistente ({desired_parent_uuid}). Conectado a Pasillo."
                )
                continue

            if desired_parent_uuid == node_uuid:
                faculty._attach_child(faculty.root_uuid, node_uuid)
                faculty.warnings.append(
                    f"Nodo '{node.name}' ({node.uuid}) apuntaba a sí mismo como padre. Conectado a Pasillo."
                )
                continue

            if not isinstance(parent, ContainerNode):
                faculty._attach_child(faculty.root_uuid, node_uuid)
                faculty.warnings.append(
                    f"Nodo '{node.name}' ({node.uuid}) tenía como padre un nodo no contenedor ({desired_parent_uuid}). Conectado a Pasillo."
                )
                continue

            if not faculty._can_parent_accept_child(parent, node):
                faculty._attach_child(faculty.root_uuid, node_uuid)
                faculty.warnings.append(
                    f"Nodo '{node.name}' ({node.uuid}) tenía un padre incompatible ({desired_parent_uuid}). Conectado a Pasillo."
                )
                continue

            faculty._attach_child(desired_parent_uuid, node_uuid)

        return faculty
    
    @classmethod
    def load_from_folder(cls, folder_path: str | Path) -> "Faculty":
        folder_path = Path(folder_path)

        faculty = cls()
        faculty.nodes = {}
        faculty.warnings = []

        config_path = folder_path / "faculty_config.json"
        nodes_path = folder_path / "nodes.csv"
        schedules_path = folder_path / "schedules.csv"

        if not config_path.exists():
            raise FileNotFoundError(f"No existe faculty_config.json en {folder_path}")

        with config_path.open("r", encoding="utf-8") as f:
            config = json.load(f)

        root_uuid = config.get("root_uuid") or faculty._generate_uuid()
        faculty.root_uuid = root_uuid

        root = Root(
            uuid=root_uuid,
            name=config.get("name", cls.ROOT_NAME),
            parent_uuid=None,
            opening_time=config.get("opening_time", "08:00"),
            closing_time=config.get("closing_time", "20:00"),
            schedule_slot_minutes=int(config.get("schedule_slot_minutes", 30)),
            default_ventilated=bool(config.get("default_ventilated", False)),
            calendar_days=list(config.get("calendar_days", ["monday", "tuesday", "wednesday", "thursday", "friday"])),
            expanded=True,
        )

        faculty.nodes[root.uuid] = root

        if nodes_path.exists():
            faculty._load_nodes_csv(nodes_path)

        faculty._rebuild_parent_child_links()

        if schedules_path.exists():
            faculty._load_schedules_csv(schedules_path)

        return faculty
    
    def _load_nodes_csv(self, path: Path) -> None:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            for line_number, row in enumerate(reader, start=2):
                node_uuid = self._csv_to_optional_str(row.get("uuid"))
                node_type = (row.get("node_type") or "").strip().lower()
                name = self._csv_to_optional_str(row.get("name")) or "Sin nombre"
                parent_uuid = self._csv_to_optional_str(row.get("parent_uuid"))

                if not node_uuid:
                    node_uuid = self._generate_uuid()
                    self.warnings.append(
                        f"Línea {line_number}: nodo sin UUID. Se generó {node_uuid}."
                    )

                if node_uuid in self.nodes:
                    self.warnings.append(
                        f"Línea {line_number}: UUID duplicado {node_uuid}. Nodo omitido."
                    )
                    continue

                size = self._csv_to_optional_float(row.get("size")) or 1.0
                expanded = self._csv_to_bool(row.get("expanded"), default=True)

                if node_type in {"group", "spacegroup"}:
                    node = SpaceGroup(
                        uuid=node_uuid,
                        name=name,
                        parent_uuid=parent_uuid,
                        size=size,
                        expanded=expanded,
                        default_ventilated=self._csv_to_bool(row.get("default_ventilated"), default=False),
                        opening_time_override=self._csv_to_optional_str(row.get("opening_time_override")),
                        closing_time_override=self._csv_to_optional_str(row.get("closing_time_override")),
                    )

                elif node_type == "space":
                    node = Space(
                        uuid=node_uuid,
                        name=name,
                        parent_uuid=parent_uuid,
                        size=size,
                        capacity=self._csv_to_optional_int(row.get("capacity")),
                        space_type_uuid=self._csv_to_optional_str(row.get("space_type_uuid")),
                        ventilated=self._csv_to_bool(row.get("ventilated"), default=False),
                        opening_time_override=self._csv_to_optional_str(row.get("opening_time_override")),
                        closing_time_override=self._csv_to_optional_str(row.get("closing_time_override")),
                        position_x=self._csv_to_optional_float(row.get("position_x")) or 0.0,
                        position_y=self._csv_to_optional_float(row.get("position_y")) or 0.0,
                    )

                elif node_type == "career":
                    node = Career(
                        uuid=node_uuid,
                        name=name,
                        parent_uuid=parent_uuid,
                        size=size,
                        expanded=expanded,
                        students_by_year=self._csv_to_optional_int(row.get("students_by_year")),
                        default_attendance_rate=self._csv_to_optional_float(row.get("default_attendance_rate")),
                        mean_age=self._csv_to_optional_float(row.get("mean_age")),
                        std_age=self._csv_to_optional_float(row.get("std_age")),
                        sex_ratio=self._csv_to_optional_float(row.get("sex_ratio")),
                    )

                elif node_type == "course":
                    node = Course(
                        uuid=node_uuid,
                        name=name,
                        parent_uuid=parent_uuid,
                        size=size,
                        expanded=expanded,
                        career_uuid=self._csv_to_optional_str(row.get("career_uuid")) or parent_uuid,
                        number_of_students=self._csv_to_optional_int(row.get("number_of_students")),
                        attendance_rate=self._csv_to_optional_float(row.get("attendance_rate")),
                        mean_age=self._csv_to_optional_float(row.get("mean_age")),
                        std_age=self._csv_to_optional_float(row.get("std_age")),
                        sex_ratio=self._csv_to_optional_float(row.get("sex_ratio")),
                    )

                elif node_type == "coursegroup":
                    node = CourseGroup(
                        uuid=node_uuid,
                        name=name,
                        parent_uuid=parent_uuid,
                        size=size,
                        expanded=expanded,
                        course_uuid=self._csv_to_optional_str(row.get("course_uuid")) or parent_uuid,
                        number_of_students=self._csv_to_optional_int(row.get("number_of_students")),
                        attendance_rate=self._csv_to_optional_float(row.get("attendance_rate")),
                        mean_age=self._csv_to_optional_float(row.get("mean_age")),
                        std_age=self._csv_to_optional_float(row.get("std_age")),
                        sex_ratio=self._csv_to_optional_float(row.get("sex_ratio")),
                    )

                else:
                    self.warnings.append(
                        f"Línea {line_number}: node_type inválido '{node_type}'. Nodo omitido."
                    )
                    continue

                self.nodes[node.uuid] = node

    def _rebuild_parent_child_links(self) -> None:
        for node in self.nodes.values():
            if isinstance(node, ContainerNode):
                node.children_uuids.clear()

        for node_uuid, node in list(self.nodes.items()):
            if isinstance(node, Root):
                continue

            parent_uuid = node.parent_uuid or self.root_uuid

            if parent_uuid not in self.nodes:
                self.warnings.append(
                    f"Nodo '{node.name}' tenía padre inexistente {parent_uuid}. Se conecta al root."
                )
                parent_uuid = self.root_uuid

            parent = self.nodes[parent_uuid]

            if not isinstance(parent, ContainerNode):
                self.warnings.append(
                    f"Nodo '{node.name}' tenía padre no contenedor. Se conecta al root."
                )
                parent_uuid = self.root_uuid
                parent = self.nodes[parent_uuid]

            if not self._can_parent_accept_child(parent, node):
                self.warnings.append(
                    f"Nodo '{node.name}' tenía padre incompatible. Se conecta al root."
                )
                parent_uuid = self.root_uuid
                parent = self.nodes[parent_uuid]

            node.parent_uuid = parent_uuid
            parent.children_uuids.append(node_uuid)
    
    def _load_schedules_csv(self, path: Path) -> None:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            for line_number, row in enumerate(reader, start=2):
                block_uuid = self._csv_to_optional_str(row.get("uuid")) or self._generate_schedule_block_uuid()
                owner_uuid = self._csv_to_optional_str(row.get("owner_uuid"))
                schedule_type = self._csv_to_optional_str(row.get("schedule_type"))

                if not owner_uuid or owner_uuid not in self.nodes:
                    self.warnings.append(
                        f"Línea {line_number}: horario con owner_uuid inválido. Se omite."
                    )
                    continue

                block = ScheduleBlock(
                    uuid=block_uuid,
                    day_of_week=self._csv_to_optional_str(row.get("day_of_week")) or "monday",
                    start_time=self._csv_to_optional_str(row.get("start_time")) or "08:00",
                    end_time=self._csv_to_optional_str(row.get("end_time")) or "08:30",
                    space_uuid=self._csv_to_optional_str(row.get("space_uuid")),
                )

                owner = self.nodes[owner_uuid]

                if schedule_type == "course_base" and isinstance(owner, Course):
                    owner.base_schedule.append(block)

                elif schedule_type == "coursegroup_override" and isinstance(owner, CourseGroup):
                    owner.schedule_overrides.append(block)

                else:
                    self.warnings.append(
                        f"Línea {line_number}: tipo de horario incompatible con el nodo propietario."
                    )

        for node in self.nodes.values():
            if isinstance(node, Course):
                node.base_schedule = self._sort_schedule_blocks(node.base_schedule)

            elif isinstance(node, CourseGroup):
                node.schedule_overrides = self._sort_schedule_blocks(node.schedule_overrides)

    # -------------------------
    # Guardado en CSV
    # -------------------------

    def save_to_csv(self, csv_path: str | Path, mode: str = "autosave") -> list[str]:
        if mode not in {"autosave", "manual"}:
            raise ValueError("mode debe ser 'autosave' o 'manual'")

        csv_path = Path(csv_path)

        validation_errors: list[str] = []
        if mode == "manual":
            validation_errors = self.validate_for_simulation()
            if validation_errors:
                return validation_errors

        fieldnames = [
            "uuid",
            "node_type",
            "name",
            "parent_uuid",
            "parent_name",
            "capacity",
        ]

        rows = []

        for node in self._iter_nodes_for_saving():
            if isinstance(node, Root):
                continue

            parent_name = ""
            if node.parent_uuid and node.parent_uuid in self.nodes:
                parent_name = self.nodes[node.parent_uuid].name

            if isinstance(node, SpaceGroup):
                node_type = "spacegroup"
                capacity = ""
            elif isinstance(node, Space):
                node_type = "space"
                capacity = "" if node.capacity is None else node.capacity
            elif isinstance(node, Career):
                node_type = "career"
                capacity = ""
            elif isinstance(node, Course):
                node_type = "course"
                capacity = ""
            elif isinstance(node, CourseGroup):
                node_type = "coursegroup"
                capacity = ""
            else:
                continue

            rows.append({
                "uuid": node.uuid,
                "node_type": node_type,
                "name": node.name,
                "parent_uuid": node.parent_uuid or "",
                "parent_name": parent_name,
                "capacity": capacity,
            })

        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return []

    def validate_for_simulation(self) -> list[str]:
        errors: list[str] = []

        for node in self.nodes.values():
            if isinstance(node, Root):
                continue

            if not node.name.strip():
                errors.append(f"El nodo {node.uuid} no tiene nombre.")

            if isinstance(node, Space):
                if node.capacity is None:
                    errors.append(f"El espacio '{node.name}' no tiene capacidad definida.")
                elif node.capacity <= 0:
                    errors.append(f"El espacio '{node.name}' tiene una capacidad inválida.")

        return errors
    
    def save_to_folder(self, folder_path: str | Path) -> None:
        folder_path = Path(folder_path)
        folder_path.mkdir(parents=True, exist_ok=True)

        self._save_faculty_config(folder_path / "faculty_config.json")
        self._save_nodes_csv(folder_path / "nodes.csv")
        self._save_schedules_csv(folder_path / "schedules.csv")

    def _save_faculty_config(self, path: Path) -> None:
        root = self.get_root()

        data = {
            "root_uuid": root.uuid,
            "name": root.name,
            "opening_time": root.opening_time,
            "closing_time": root.closing_time,
            "schedule_slot_minutes": root.schedule_slot_minutes,
            "default_ventilated": root.default_ventilated,
            "calendar_days": root.calendar_days,
        }

        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def _save_nodes_csv(self, path: Path) -> None:
        fieldnames = [
            "uuid",
            "node_type",
            "name",
            "parent_uuid",
            "size",
            "expanded",
            "capacity",
            "space_type_uuid",
            "ventilated",
            "opening_time_override",
            "closing_time_override",
            "position_x",
            "position_y",
            "students_by_year",
            "default_attendance_rate",
            "number_of_students",
            "attendance_rate",
            "mean_age",
            "std_age",
            "sex_ratio",
            "career_uuid",
            "course_uuid",
        ]

        rows = []

        for node in self._iter_nodes_for_saving():
            if isinstance(node, Root):
                continue

            if isinstance(node, SpaceGroup):
                node_type = "spacegroup"
            elif isinstance(node, Space):
                node_type = "space"
            elif isinstance(node, Career):
                node_type = "career"
            elif isinstance(node, Course):
                node_type = "course"
            elif isinstance(node, CourseGroup):
                node_type = "coursegroup"
            else:
                continue

            rows.append({
                "uuid": node.uuid,
                "node_type": node_type,
                "name": node.name,
                "parent_uuid": node.parent_uuid or "",
                "size": self._value_to_csv(getattr(node, "size", None)),
                "expanded": self._value_to_csv(getattr(node, "expanded", None)),

                "capacity": self._value_to_csv(getattr(node, "capacity", None)),
                "space_type_uuid": self._value_to_csv(getattr(node, "space_type_uuid", None)),
                "ventilated": self._value_to_csv(getattr(node, "ventilated", None)),
                "opening_time_override": self._value_to_csv(getattr(node, "opening_time_override", None)),
                "closing_time_override": self._value_to_csv(getattr(node, "closing_time_override", None)),
                "position_x": self._value_to_csv(getattr(node, "position_x", None)),
                "position_y": self._value_to_csv(getattr(node, "position_y", None)),

                "students_by_year": self._value_to_csv(getattr(node, "students_by_year", None)),
                "default_attendance_rate": self._value_to_csv(getattr(node, "default_attendance_rate", None)),

                "number_of_students": self._value_to_csv(getattr(node, "number_of_students", None)),
                "attendance_rate": self._value_to_csv(getattr(node, "attendance_rate", None)),
                "mean_age": self._value_to_csv(getattr(node, "mean_age", None)),
                "std_age": self._value_to_csv(getattr(node, "std_age", None)),
                "sex_ratio": self._value_to_csv(getattr(node, "sex_ratio", None)),

                "career_uuid": self._value_to_csv(getattr(node, "career_uuid", None)),
                "course_uuid": self._value_to_csv(getattr(node, "course_uuid", None)),
            })

        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    def _save_schedules_csv(self, path: Path) -> None:
        fieldnames = [
            "uuid",
            "owner_uuid",
            "schedule_type",
            "day_of_week",
            "start_time",
            "end_time",
            "space_uuid",
        ]

        rows = []

        for node in self._iter_nodes_for_saving():
            if isinstance(node, Course):
                for block in node.base_schedule:
                    rows.append({
                        "uuid": block.uuid,
                        "owner_uuid": node.uuid,
                        "schedule_type": "course_base",
                        "day_of_week": block.day_of_week,
                        "start_time": block.start_time,
                        "end_time": block.end_time,
                        "space_uuid": block.space_uuid or "",
                    })

            elif isinstance(node, CourseGroup):
                for block in node.schedule_overrides:
                    rows.append({
                        "uuid": block.uuid,
                        "owner_uuid": node.uuid,
                        "schedule_type": "coursegroup_override",
                        "day_of_week": block.day_of_week,
                        "start_time": block.start_time,
                        "end_time": block.end_time,
                        "space_uuid": block.space_uuid or "",
                    })

        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    # -------------------------
    # Debug / inspección
    # -------------------------

    def print_tree(self, start_uuid: Optional[str] = None, indent: int = 0) -> None:
        if start_uuid is None:
            start_uuid = self.root_uuid

        node = self._get_node(start_uuid)
        prefix = "  " * indent

        if isinstance(node, Root):
            node_type = "ROOT"
        elif isinstance(node, SpaceGroup):
            node_type = "SPACE_GROUP"
        elif isinstance(node, Space):
            node_type = "SPACE"
        elif isinstance(node, Career):
            node_type = "CAREER"
        elif isinstance(node, Course):
            node_type = "COURSE"
        elif isinstance(node, CourseGroup):
            node_type = "COURSE_GROUP"
        else:
            node_type = "NODE"

        print(f"{prefix}- [{node_type}] {node.name} ({node.uuid})")

        if isinstance(node, ContainerNode):
            for child_uuid in node.children_uuids:
                if child_uuid in self.nodes:
                    self.print_tree(child_uuid, indent + 1)
                else:
                    print(f"{prefix}  - [MISSING] Nodo inexistente ({child_uuid})")

    def debug_select_node(self) -> Optional[str]:
        seleccion = list(self.nodes.keys())
        print("\nSelecciona uno de los nodos del grafo")
        for x, i in enumerate(seleccion):
            print(f"    {x+1}. {self.nodes[i].name}")
        print(f"    {len(seleccion) + 1}. Cancelar")
        elegido = int(input("\nEscribe aquí tu elección: "))
        if elegido == len(seleccion) + 1:
            return None
        return seleccion[elegido - 1]


if __name__ == "__main__":
    faculty = Faculty()

    career = faculty.create_career("Biotecnología")
    course1 = faculty.create_course("1º", career.uuid)
    g1 = faculty.create_course_group("Mañana", course1.uuid)
    g2 = faculty.create_course_group("Tarde", course1.uuid)

    sg = faculty.create_space_group("Bloque A")
    s1 = faculty.create_space("Aula 101", sg.uuid)

    faculty.add_course_schedule_block(course1.uuid, "monday", "08:00", "10:00", s1.uuid)
    faculty.add_course_group_schedule_override(g2.uuid, "monday", "08:00", "10:00", s1.uuid)

    faculty.print_tree()
    print("\nHorario efectivo grupo tarde:")
    for block in faculty.get_effective_schedule_for_course_group(g2.uuid):
        print(block)
