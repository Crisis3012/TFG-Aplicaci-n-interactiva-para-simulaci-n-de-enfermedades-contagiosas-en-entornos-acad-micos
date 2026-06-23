from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
import math

from backend.faculty import (
    Faculty,
    Root,
    Space,
    SpaceType,
    Career,
    Course,
    CourseGroup,
    ScheduleBlock,
)

from backend.simulation.agent import SimulationAgent
from backend.simulation.event import SimulationEvent, SpaceContext, ActivityType


# ============================================================
# CONTEXTOS AUXILIARES PARA LA SIMULACIÓN
# ============================================================

@dataclass
class AcademicGroupContext:
    """
    Información resumida de un grupo académico para la simulación.

    Puede representar un CourseGroup real del Builder o, si un curso no tiene
    grupos, un grupo virtual asociado directamente al curso.
    """

    academic_group_id: str
    group_name: str

    course_uuid: Optional[str] = None
    course_name: Optional[str] = None

    career_uuid: Optional[str] = None
    career_name: Optional[str] = None

    number_of_students: int = 0
    attendance_rate: float = 1.0

    is_virtual_group: bool = False


@dataclass
class FacultySimulationData:
    """
    Resultado de adaptar una Faculty al formato que entiende la simulación.
    """

    agents: list[SimulationAgent] = field(default_factory=list)
    events: list[SimulationEvent] = field(default_factory=list)

    space_contexts: dict[str, SpaceContext] = field(default_factory=dict)
    group_contexts: dict[str, AcademicGroupContext] = field(default_factory=dict)

    slots_per_day: int = 0
    slot_minutes: int = 30

    warnings: list[str] = field(default_factory=list)


# ============================================================
# ADAPTADOR PRINCIPAL
# ============================================================

class FacultySimulationAdapter:
    """
    Convierte una Faculty creada con el Builder en datos de simulación.

    Responsabilidades:
    - generar agentes a partir de cursos/grupos;
    - generar eventos a partir de horarios;
    - crear contexto resumido de espacios;
    - crear contexto resumido de grupos académicos.
    """

    DEFAULT_STUDENTS_PER_GROUP = 30
    DEFAULT_ATTENDANCE_RATE = 1.0

    def __init__(self, faculty: Faculty) -> None:
        self.faculty = faculty
        self.warnings: list[str] = []

    # ========================================================
    # API PRINCIPAL
    # ========================================================

    def build_simulation_data(self, duration_days: int) -> FacultySimulationData:
        """
        Construye todos los datos necesarios para ejecutar una simulación.

        duration_days no tiene por qué representar días naturales completos;
        representa repeticiones del calendario académico definido en la facultad.
        """

        if duration_days <= 0:
            raise ValueError("duration_days debe ser mayor que 0.")

        root = self.faculty.get_root()
        slot_minutes = int(root.schedule_slot_minutes)
        slots_per_day = self._calculate_slots_per_day(root)

        space_contexts = self.build_space_contexts()
        group_contexts = self.build_group_contexts()

        agents = self.build_agents(group_contexts)
        events = self.build_events(
            duration_days=duration_days,
            group_contexts=group_contexts,
        )

        return FacultySimulationData(
            agents=agents,
            events=events,
            space_contexts=space_contexts,
            group_contexts=group_contexts,
            slots_per_day=slots_per_day,
            slot_minutes=slot_minutes,
            warnings=list(self.warnings),
        )

    # ========================================================
    # ESPACIOS
    # ========================================================

    def build_space_contexts(self) -> dict[str, SpaceContext]:
        """
        Crea un SpaceContext por cada Space de la facultad.
        """

        contexts: dict[str, SpaceContext] = {}

        for node in self.faculty.nodes.values():
            if not isinstance(node, Space):
                continue

            context = self._build_space_context(node)
            contexts[node.uuid] = context

        return contexts

    def _build_space_context(self, space: Space) -> SpaceContext:
        root = self.faculty.get_root()
        space_type = self._find_space_type(space.space_type_uuid)

        space_type_uuid = space_type.uuid if space_type is not None else space.space_type_uuid
        space_type_name = space_type.name if space_type is not None else None

        ventilated = bool(space.ventilated)

        if space_type is not None and space_type.default_ventilated:
            ventilated = True

        if root.default_ventilated:
            ventilated = True

        return SpaceContext(
            space_uuid=space.uuid,
            space_name=space.name,
            space_type_uuid=space_type_uuid,
            space_type_name=space_type_name,
            capacity=space.capacity,
            ventilated=ventilated,
            contact_level=space_type.contact_level if space_type is not None else 1.0,
            duration_relevance=space_type.duration_relevance if space_type is not None else 1.0,
            mask_effect_relevance=space_type.mask_effect_relevance if space_type is not None else 1.0,
            ventilation_effect_relevance=space_type.ventilation_effect_relevance if space_type is not None else 1.0,
            is_transit_type=space_type.is_transit_type if space_type is not None else False,
            is_recreation_type=space_type.is_recreation_type if space_type is not None else False,
        )

    def _find_space_type(self, space_type_uuid: Optional[str]) -> Optional[SpaceType]:
        if not space_type_uuid:
            return None

        for space_type in self.faculty.get_space_types():
            if space_type.uuid == space_type_uuid:
                return space_type

        return None

    # ========================================================
    # GRUPOS ACADÉMICOS
    # ========================================================

    def build_group_contexts(self) -> dict[str, AcademicGroupContext]:
        """
        Crea contextos académicos a partir de los CourseGroup.

        Si un Course no tiene CourseGroup, se crea un grupo virtual para que
        ese curso también pueda participar en la simulación.
        """

        contexts: dict[str, AcademicGroupContext] = {}

        for course in self._get_courses():
            career = self._find_career_for_course(course)
            course_groups = self._get_course_groups_for_course(course)

            if course_groups:
                for group in course_groups:
                    context = self._build_context_for_course_group(
                        group=group,
                        course=course,
                        career=career,
                    )
                    contexts[context.academic_group_id] = context
            else:
                context = self._build_virtual_context_for_course(
                    course=course,
                    career=career,
                )
                contexts[context.academic_group_id] = context

        return contexts

    def _build_context_for_course_group(
        self,
        group: CourseGroup,
        course: Course,
        career: Optional[Career],
    ) -> AcademicGroupContext:
        number_of_students = self._resolve_number_of_students(
            group=group,
            course=course,
            career=career,
        )

        attendance_rate = self._resolve_attendance_rate(
            group=group,
            course=course,
            career=career,
        )

        return AcademicGroupContext(
            academic_group_id=group.uuid,
            group_name=group.name,
            course_uuid=course.uuid,
            course_name=course.name,
            career_uuid=career.uuid if career is not None else None,
            career_name=career.name if career is not None else None,
            number_of_students=number_of_students,
            attendance_rate=attendance_rate,
            is_virtual_group=False,
        )

    def _build_virtual_context_for_course(
        self,
        course: Course,
        career: Optional[Career],
    ) -> AcademicGroupContext:
        """
        Crea un grupo virtual para cursos que no tienen grupos definidos.

        Esto evita que un curso con horario pero sin CourseGroup quede fuera
        de la simulación.
        """

        virtual_group_id = self._get_virtual_group_id(course.uuid)

        number_of_students = self._resolve_number_of_students(
            group=None,
            course=course,
            career=career,
        )

        attendance_rate = self._resolve_attendance_rate(
            group=None,
            course=course,
            career=career,
        )

        return AcademicGroupContext(
            academic_group_id=virtual_group_id,
            group_name=f"{course.name} (grupo único)",
            course_uuid=course.uuid,
            course_name=course.name,
            career_uuid=career.uuid if career is not None else None,
            career_name=career.name if career is not None else None,
            number_of_students=number_of_students,
            attendance_rate=attendance_rate,
            is_virtual_group=True,
        )

    def _resolve_number_of_students(
        self,
        group: Optional[CourseGroup],
        course: Course,
        career: Optional[Career],
    ) -> int:
        if group is not None and group.number_of_students is not None:
            return max(0, int(group.number_of_students))

        if course.number_of_students is not None:
            return max(0, int(course.number_of_students))

        if career is not None and career.students_by_year is not None:
            return max(0, int(career.students_by_year))

        self.warnings.append(
            f"No se ha definido número de estudiantes para el curso '{course.name}'. "
            f"Se usará el valor por defecto: {self.DEFAULT_STUDENTS_PER_GROUP}."
        )

        return self.DEFAULT_STUDENTS_PER_GROUP

    def _resolve_attendance_rate(
        self,
        group: Optional[CourseGroup],
        course: Course,
        career: Optional[Career],
    ) -> float:
        if group is not None and group.attendance_rate is not None:
            return self._clamp_probability(float(group.attendance_rate))

        if course.attendance_rate is not None:
            return self._clamp_probability(float(course.attendance_rate))

        if career is not None and career.default_attendance_rate is not None:
            return self._clamp_probability(float(career.default_attendance_rate))

        return self.DEFAULT_ATTENDANCE_RATE

    # ========================================================
    # AGENTES
    # ========================================================

    def build_agents(
        self,
        group_contexts: Optional[dict[str, AcademicGroupContext]] = None,
    ) -> list[SimulationAgent]:
        """
        Genera agentes/estudiantes a partir de los grupos académicos.
        """

        if group_contexts is None:
            group_contexts = self.build_group_contexts()

        agents: list[SimulationAgent] = []

        for context in group_contexts.values():
            safe_group_id = self._safe_id(context.academic_group_id)

            for index in range(context.number_of_students):
                agent = SimulationAgent(
                    agent_id=f"agent_{safe_group_id}_{index + 1:04d}",
                    academic_group_id=context.academic_group_id,
                    course_uuid=context.course_uuid,
                    career_uuid=context.career_uuid,
                )
                agents.append(agent)

        return agents

    # ========================================================
    # EVENTOS
    # ========================================================

    def build_events(
        self,
        duration_days: int,
        group_contexts: Optional[dict[str, AcademicGroupContext]] = None,
    ) -> list[SimulationEvent]:
        """
        Convierte los horarios de la facultad en eventos de simulación.
        """

        if duration_days <= 0:
            raise ValueError("duration_days debe ser mayor que 0.")

        if group_contexts is None:
            group_contexts = self.build_group_contexts()

        root = self.faculty.get_root()
        calendar_days = list(root.calendar_days)

        if not calendar_days:
            raise ValueError("La facultad no tiene días de calendario definidos.")

        events: list[SimulationEvent] = []

        for day_index in range(duration_days):
            day_of_week = calendar_days[day_index % len(calendar_days)]

            for context in group_contexts.values():
                schedule_blocks = self._get_schedule_for_context(context)

                for block in schedule_blocks:
                    if block.day_of_week != day_of_week:
                        continue

                    event = self._build_event_from_schedule_block(
                        block=block,
                        context=context,
                        day_index=day_index,
                        day_of_week=day_of_week,
                    )

                    if event is not None:
                        events.append(event)

        events.sort(key=lambda event: (event.start_slot, event.end_slot, event.event_id))
        return events

    def _get_schedule_for_context(
        self,
        context: AcademicGroupContext,
    ) -> list[ScheduleBlock]:
        """
        Devuelve el horario que corresponde a un contexto académico.
        """

        if context.is_virtual_group:
            if context.course_uuid is None:
                return []

            course = self.faculty.find_node(context.course_uuid)
            if isinstance(course, Course):
                return list(course.base_schedule)

            return []

        group = self.faculty.find_node(context.academic_group_id)

        if isinstance(group, CourseGroup):
            return self.faculty.get_effective_schedule_for_course_group(group.uuid)

        return []

    def _build_event_from_schedule_block(
        self,
        block: ScheduleBlock,
        context: AcademicGroupContext,
        day_index: int,
        day_of_week: str,
    ) -> Optional[SimulationEvent]:
        root = self.faculty.get_root()

        try:
            start_offset = self._time_to_slot_offset(block.start_time, root)
            end_offset = self._time_to_slot_offset(block.end_time, root)
        except ValueError as exc:
            self.warnings.append(
                f"Horario inválido en grupo '{context.group_name}': {exc}"
            )
            return None

        if end_offset <= start_offset:
            self.warnings.append(
                f"Bloque horario inválido en grupo '{context.group_name}': "
                f"{block.start_time} - {block.end_time}."
            )
            return None

        slots_per_day = self._calculate_slots_per_day(root)

        start_slot = day_index * slots_per_day + start_offset
        end_slot = day_index * slots_per_day + end_offset
        duration_slots = end_slot - start_slot

        activity_type = self._infer_activity_type(block.space_uuid)

        event_id = (
            f"event_{day_index}_{self._safe_id(context.academic_group_id)}_"
            f"{self._safe_id(block.uuid)}"
        )

        return SimulationEvent(
            event_id=event_id,
            source_schedule_block_uuid=block.uuid,
            day_index=day_index,
            day_of_week=day_of_week,
            start_slot=start_slot,
            end_slot=end_slot,
            duration_slots=duration_slots,
            space_uuid=block.space_uuid,
            academic_group_id=context.academic_group_id,
            course_uuid=context.course_uuid,
            career_uuid=context.career_uuid,
            activity_type=activity_type,
        )

    # ========================================================
    # INFERENCIA DE TIPO DE ACTIVIDAD
    # ========================================================

    def _infer_activity_type(self, space_uuid: Optional[str]) -> ActivityType:
        if not space_uuid:
            return ActivityType.OTHER

        space = self.faculty.find_node(space_uuid)
        if not isinstance(space, Space):
            return ActivityType.OTHER

        space_type = self._find_space_type(space.space_type_uuid)

        raw_values = [
            space.name,
            space.space_type_uuid or "",
            space_type.name if space_type is not None else "",
        ]

        text = " ".join(raw_values).lower()

        if space_type is not None and space_type.is_transit_type:
            return ActivityType.CORRIDOR

        if space_type is not None and space_type.is_recreation_type:
            return ActivityType.CAFETERIA

        if "lab" in text or "laboratorio" in text or "laboratory" in text:
            return ActivityType.LAB

        if "pasillo" in text or "corridor" in text:
            return ActivityType.CORRIDOR

        if "biblioteca" in text or "library" in text:
            return ActivityType.LIBRARY

        if "cafeter" in text or "comedor" in text or "canteen" in text:
            return ActivityType.CAFETERIA

        if "class" in text or "aula" in text or "clase" in text or "classroom" in text:
            return ActivityType.CLASS

        return ActivityType.OTHER

    # ========================================================
    # HELPERS DE NODOS
    # ========================================================

    def _get_courses(self) -> list[Course]:
        return [
            node
            for node in self.faculty.nodes.values()
            if isinstance(node, Course)
        ]

    def _get_course_groups_for_course(self, course: Course) -> list[CourseGroup]:
        groups: list[CourseGroup] = []

        for child in self.faculty.get_children(course.uuid):
            if isinstance(child, CourseGroup):
                groups.append(child)

        return groups

    def _find_career_for_course(self, course: Course) -> Optional[Career]:
        if course.career_uuid:
            node = self.faculty.find_node(course.career_uuid)
            if isinstance(node, Career):
                return node

        if course.parent_uuid:
            node = self.faculty.find_node(course.parent_uuid)
            if isinstance(node, Career):
                return node

        return None

    # ========================================================
    # HELPERS DE TIEMPO
    # ========================================================

    def _calculate_slots_per_day(self, root: Root) -> int:
        opening_minutes = self._time_to_minutes(root.opening_time)
        closing_minutes = self._time_to_minutes(root.closing_time)

        if closing_minutes <= opening_minutes:
            raise ValueError("La hora de cierre debe ser posterior a la hora de apertura.")

        total_minutes = closing_minutes - opening_minutes
        slot_minutes = int(root.schedule_slot_minutes)

        if slot_minutes <= 0:
            raise ValueError("schedule_slot_minutes debe ser mayor que 0.")

        return math.ceil(total_minutes / slot_minutes)

    def _time_to_slot_offset(self, time_str: str, root: Root) -> int:
        opening_minutes = self._time_to_minutes(root.opening_time)
        target_minutes = self._time_to_minutes(time_str)
        slot_minutes = int(root.schedule_slot_minutes)

        if target_minutes < opening_minutes:
            raise ValueError(
                f"La hora {time_str} es anterior a la apertura ({root.opening_time})."
            )

        offset_minutes = target_minutes - opening_minutes

        if offset_minutes % slot_minutes != 0:
            raise ValueError(
                f"La hora {time_str} no coincide con slots de {slot_minutes} minutos."
            )

        return offset_minutes // slot_minutes

    @staticmethod
    def _time_to_minutes(time_str: str) -> int:
        try:
            hours, minutes = time_str.split(":")
            return int(hours) * 60 + int(minutes)
        except Exception as exc:
            raise ValueError(f"Formato de hora inválido: {time_str}") from exc

    # ========================================================
    # HELPERS GENERALES
    # ========================================================

    @staticmethod
    def _clamp_probability(value: float) -> float:
        if value < 0:
            return 0.0

        if value > 1:
            return 1.0

        return value

    @staticmethod
    def _get_virtual_group_id(course_uuid: str) -> str:
        return f"virtual_group_for_course_{course_uuid}"

    @staticmethod
    def _safe_id(raw_id: str) -> str:
        return (
            raw_id
            .replace(" ", "_")
            .replace("-", "_")
            .replace(":", "_")
            .replace("/", "_")
        )