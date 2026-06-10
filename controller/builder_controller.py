from __future__ import annotations

from typing import Optional, Any

from pathlib import Path
from backend.faculty import Faculty
from backend.faculty_project_manager import FacultyProjectManager


class BuilderController:
    def __init__(
        self,
        faculty: Faculty,
        ui: Optional[Any] = None,
        project_manager: Optional[FacultyProjectManager] = None,
        active_faculty_name: Optional[str] = None,
    ):
        self.faculty = faculty
        self.ui = ui
        self.selected_node_uuid: Optional[str] = None
        self.builder_mode: str = "space"

        self.project_manager = project_manager or FacultyProjectManager()
        self.active_faculty_name = active_faculty_name
        
    def attach_ui(self, ui: Any) -> None:
        self.ui = ui

    # -------------------------
    # MODO DE BUILDER
    # -------------------------

    def get_builder_mode(self) -> str:
        return self.builder_mode

    def set_builder_mode(self, mode: str) -> None:
        if mode not in {"space", "agent"}:
            return

        if self.builder_mode == mode:
            if self.ui is not None and hasattr(self.ui, "update_builder_mode"):
                self.ui.update_builder_mode(mode)
            return

        self.builder_mode = mode
        self.selected_node_uuid = None
        self.refresh_all()

    def toggle_builder_mode(self) -> None:
        if self.builder_mode == "space":
            self.set_builder_mode("agent")
        else:
            self.set_builder_mode("space")

    # -------------------------
    # CARGA Y REFRESCO GENERAL
    # -------------------------

    def load_builder(self) -> None:
        self.refresh_all()

    def refresh_all(self) -> None:
        if self.ui is None:
            return

        root = self.faculty.get_root()
        graph_data = self._build_graph_data()

        if hasattr(self.ui, "update_builder_mode"):
            self.ui.update_builder_mode(self.builder_mode)

        self.ui.render_tree(root)
        self.ui.render_graph(graph_data)

        if self.selected_node_uuid is not None:
            selected_node = self.faculty.find_node(self.selected_node_uuid)

            if selected_node is None or not self._node_belongs_to_active_builder(selected_node):
                self.selected_node_uuid = None
                self.ui.select_node_visual(None)
                self.ui.clear_properties_panel()
                return

            self.ui.select_node_visual(self.selected_node_uuid)
            self._refresh_selected_node_panel()
        else:
            self.ui.select_node_visual(None)
            self.ui.clear_properties_panel()

    def _refresh_selected_node_panel(self) -> None:
        if self.ui is None or self.selected_node_uuid is None:
            return

        node = self.faculty.find_node(self.selected_node_uuid)

        if node is None or not self._node_belongs_to_active_builder(node):
            self.selected_node_uuid = None
            self.ui.select_node_visual(None)
            self.ui.clear_properties_panel()
            return

        valid_parents = self.faculty.get_valid_parents(self.selected_node_uuid)
        form_options = self._build_form_options(node)

        self.ui.show_node_properties(node, valid_parents, form_options)

    def _build_graph_data(self) -> dict:
        root = self.faculty.get_root()
        visible_nodes = self.faculty.get_visible_nodes()

        visible_by_uuid = {node.uuid: node for node in visible_nodes if self._node_belongs_to_active_builder(node)}
        visible_by_uuid[root.uuid] = root

        visible_nodes = list(visible_by_uuid.values())
        visible_uuids = set(visible_by_uuid.keys())

        nodes = []
        edges = []

        for node in visible_nodes:
            node_type = self._get_node_type(node)

            nodes.append({
                "uuid": node.uuid,
                "name": node.name,
                "type": node_type,
                "size": getattr(node, "size", 100),
            })

        for node in visible_nodes:
            if node.uuid == root.uuid:
                continue

            parent_uuid = getattr(node, "parent_uuid", None)
            if parent_uuid is None:
                parent_uuid = root.uuid

            if parent_uuid in visible_uuids:
                edges.append({
                    "source": parent_uuid,
                    "target": node.uuid,
                })

        return {
            "nodes": nodes,
            "edges": edges,
        }

    def _build_form_options(self, node=None) -> dict:
        options = {
            "time_options": self.faculty.get_time_options(),
            "slot_options": self.faculty.get_schedule_slot_options(),
            "calendar_day_options": self.faculty.get_calendar_day_options(),
            "space_type_options": [
                {"uuid": item.uuid, "name": item.name}
                for item in self.faculty.get_space_types()
            ],
            "space_options": [
                {"uuid": item.uuid, "name": item.name}
                for item in self.faculty.get_all_spaces()
            ],
            "schedule_days": list(self.faculty.get_root().calendar_days),
            "schedule_rows": self._build_schedule_rows(),
        }

        if node is not None and self._get_node_type(node) == "coursegroup":
            parent_course = self.faculty.find_node(getattr(node, "course_uuid", None))
            if parent_course is not None:
                options["course_base_schedule"] = list(getattr(parent_course, "base_schedule", []))
            else:
                options["course_base_schedule"] = []

        return options
    
    def _time_to_minutes(self, time_str: str) -> int:
        hours, minutes = time_str.split(":")
        return int(hours) * 60 + int(minutes)


    def _minutes_to_time(self, total_minutes: int) -> str:
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"


    def _build_schedule_rows(self) -> list[dict]:
        root = self.faculty.get_root()

        start_minutes = self._time_to_minutes(root.opening_time)
        end_minutes = self._time_to_minutes(root.closing_time)
        slot_minutes = root.schedule_slot_minutes

        rows = []
        current = start_minutes

        while current + slot_minutes <= end_minutes:
            row_start = self._minutes_to_time(current)
            row_end = self._minutes_to_time(current + slot_minutes)

            rows.append({
                "start_time": row_start,
                "end_time": row_end,
                "label": f"{row_start} - {row_end}",
            })

            current += slot_minutes

        return rows


    def _build_schedule_blocks_from_values(self, block_dicts: list[dict]) -> list:
        blocks = []

        for item in block_dicts:
            block = self.faculty.create_schedule_block(
                day_of_week=item["day_of_week"],
                start_time=item["start_time"],
                end_time=item["end_time"],
                space_uuid=item["space_uuid"],
            )
            blocks.append(block)

        return blocks

    def get_children_for_current_mode(self, node_uuid: str):
        children = self.faculty.get_children(node_uuid)
        return [child for child in children if self._node_belongs_to_active_builder(child)]
    
    def load_active_faculty(self) -> None:
        faculty, faculty_name = self.project_manager.load_active_or_create_default()

        self.faculty = faculty
        self.active_faculty_name = faculty_name
        self.selected_node_uuid = None

        self.refresh_all()


    def get_faculty_names(self) -> list[str]:
        return self.project_manager.list_faculties()


    def get_active_faculty_name(self) -> Optional[str]:
        return self.active_faculty_name


    def select_faculty(self, faculty_name: str) -> None:
        if not faculty_name:
            return

        try:
            faculty = self.project_manager.load_faculty(faculty_name)
        except Exception as exc:
            self._show_error(f"No se ha podido cargar la facultad '{faculty_name}': {exc}")
            return

        self.faculty = faculty
        self.active_faculty_name = faculty_name
        self.selected_node_uuid = None

        folder_path = self.project_manager.get_faculty_path(faculty_name)
        self.project_manager.set_active_faculty_path(folder_path)

        self.refresh_all()


    def create_new_faculty_project(self, faculty_name: str) -> None:
        try:
            folder_path = self.project_manager.create_faculty(faculty_name)
        except Exception as exc:
            self._show_error(str(exc))
            return

        self.faculty = Faculty.load_from_folder(folder_path)
        self.active_faculty_name = faculty_name
        self.selected_node_uuid = None

        self.refresh_all()


    def save_active_faculty(self) -> None:
        if not self.active_faculty_name:
            self._show_error("No hay ninguna facultad activa.")
            return

        # Fuerza aplicar los cambios del nodo seleccionado antes de guardar.
        if self.ui is not None and hasattr(self.ui, "apply_current_properties"):
            self.ui.apply_current_properties()

        try:
            self.project_manager.save_faculty(
                faculty=self.faculty,
                faculty_name=self.active_faculty_name,
            )
        except Exception as exc:
            self._show_error(f"No se ha podido guardar la facultad: {exc}")
            return

        if self.ui is not None and hasattr(self.ui, "show_info"):
            self.ui.show_info("Facultad guardada correctamente.")

    # -------------------------
    # SELECCIÓN
    # -------------------------

    def select_node(self, node_uuid: str) -> None:
        node = self.faculty.find_node(node_uuid)

        if node is None:
            self._show_error(f"No se ha encontrado el nodo con uuid: {node_uuid}")
            return

        if not self._node_belongs_to_active_builder(node):
            return

        self.selected_node_uuid = node_uuid

        if self.ui is not None:
            self.ui.select_node_visual(node_uuid)
            valid_parents = self.faculty.get_valid_parents(node_uuid)
            form_options = self._build_form_options(node)
            self.ui.show_node_properties(node, valid_parents, form_options)

    def clear_selection(self) -> None:
        self.selected_node_uuid = None

        if self.ui is not None:
            self.ui.select_node_visual(None)
            self.ui.clear_properties_panel()

    # -------------------------
    # CREACIÓN DE NODOS
    # -------------------------

    def create_group(
        self,
        name: str,
        parent_uuid: Optional[str] = None,
        node_uuid: Optional[str] = None,
        select_after_create: bool = True,
    ) -> None:
        group = self.faculty.create_group(
            name=name,
            parent_uuid=parent_uuid,
            node_uuid=node_uuid,
        )

        self.faculty.set_group_expanded(group.uuid, True)

        if select_after_create:
            self.selected_node_uuid = group.uuid

        self.refresh_all()

    def create_space(
        self,
        name: str,
        parent_uuid: Optional[str] = None,
        node_uuid: Optional[str] = None,
        select_after_create: bool = True,
    ) -> None:
        space = self.faculty.create_space(
            name=name,
            parent_uuid=parent_uuid,
            node_uuid=node_uuid,
        )

        if select_after_create:
            self.selected_node_uuid = space.uuid

        self.refresh_all()

    def create_career(self, name: str = "Nueva carrera", select_after_create: bool = True) -> None:
        career = self.faculty.create_career(name=name)

        if select_after_create:
            self.selected_node_uuid = career.uuid

        self.refresh_all()

    def create_course(self, name: str = "Nuevo curso", career_uuid: Optional[str] = None, select_after_create: bool = True) -> None:
        if career_uuid is None:
            self._show_error("Selecciona una carrera para crear un curso.")
            return

        course = self.faculty.create_course(name=name, career_uuid=career_uuid)

        if select_after_create:
            self.selected_node_uuid = course.uuid

        self.refresh_all()

    def create_course_group(self, name: str = "Nuevo grupo", course_uuid: Optional[str] = None, select_after_create: bool = True) -> None:
        if course_uuid is None:
            self._show_error("Selecciona un curso para crear un grupo.")
            return

        group = self.faculty.create_course_group(name=name, course_uuid=course_uuid)

        if select_after_create:
            self.selected_node_uuid = group.uuid

        self.refresh_all()

    def create_primary_node(self) -> None:
        if self.builder_mode == "space":
            parent_uuid = self._get_selected_space_parent_uuid()
            self.create_group("Nuevo grupo", parent_uuid=parent_uuid)
        else:
            self.create_career("Nueva carrera")

    def create_secondary_node(self) -> None:
        if self.builder_mode == "space":
            parent_uuid = self._get_selected_space_parent_uuid()
            self.create_space("Nuevo espacio", parent_uuid=parent_uuid)
        else:
            career_uuid = self._get_selected_career_uuid_for_course_creation()
            self.create_course("Nuevo curso", career_uuid=career_uuid)

    def create_tertiary_node(self) -> None:
        if self.builder_mode == "space":
            return

        course_uuid = self._get_selected_course_uuid_for_group_creation()
        self.create_course_group("Nuevo grupo", course_uuid=course_uuid)

    # -------------------------
    # EDICIÓN DE NODOS
    # -------------------------

    def rename_selected_node(self, new_name: str) -> None:
        if self.selected_node_uuid is None:
            return

        new_name = new_name.strip()

        if not new_name:
            self._show_error("El nombre no puede estar vacío.")
            self.refresh_all()
            return

        node = self.faculty.find_node(self.selected_node_uuid)

        if node is None:
            self.clear_selection()
            return

        if self._is_root(node):
            self.faculty.rename_faculty(new_name)
        else:
            self.faculty.rename_node(self.selected_node_uuid, new_name)

        self.refresh_all()

    def delete_selected_node(self) -> None:
        if self.selected_node_uuid is None:
            return

        node = self.faculty.find_node(self.selected_node_uuid)

        if node is None:
            self.clear_selection()
            return

        if self._is_root(node):
            self._show_error("No se puede eliminar la raíz de la facultad.")
            return

        node_uuid = self.selected_node_uuid
        deleted_uuids = self._collect_subtree_uuids(node_uuid)

        self.selected_node_uuid = None

        self.faculty.delete_node(node_uuid)
        self.refresh_all()

        if self.ui is not None and hasattr(self.ui, "forget_graph_nodes"):
            self.ui.forget_graph_nodes(deleted_uuids)

    def move_selected_node(self, new_parent_uuid: str) -> None:
        if self.selected_node_uuid is None:
            return

        self.move_node(self.selected_node_uuid, new_parent_uuid)

    def move_node(self, node_uuid: str, new_parent_uuid: str) -> None:
        node = self.faculty.find_node(node_uuid)

        if node is None:
            self._show_error(f"No se ha encontrado el nodo con uuid: {node_uuid}")
            return

        if self._is_root(node):
            self._show_error("No se puede mover la raíz de la facultad.")
            return

        valid_parents = self.faculty.get_valid_parents(node_uuid)
        valid_parent_uuids = {parent.uuid for parent in valid_parents}

        if new_parent_uuid not in valid_parent_uuids:
            self._show_error("El nuevo padre seleccionado no es válido.")
            return

        self.faculty.move_node(node_uuid, new_parent_uuid)
        self.refresh_all()

    def update_selected_builder_properties(self, values: dict) -> None:
        if self.selected_node_uuid is None:
            return

        node = self.faculty.find_node(self.selected_node_uuid)

        if node is None:
            self.clear_selection()
            return

        node_type = self._get_node_type(node)

        if node_type == "root":
            self.faculty.update_faculty_properties(
                name=values.get("name"),
                opening_time=values.get("opening_time"),
                closing_time=values.get("closing_time"),
                schedule_slot_minutes=values.get("schedule_slot_minutes"),
                default_ventilated=values.get("default_ventilated"),
                calendar_days=values.get("calendar_days"),
            )

        elif node_type in {"group", "spacegroup"}:
            if hasattr(self.faculty, "update_space_group_properties"):
                self.faculty.update_space_group_properties(
                    group_uuid=node.uuid,
                    name=values.get("name"),
                    default_ventilated=values.get("default_ventilated"),
                    opening_time_override=values.get("opening_time_override"),
                    closing_time_override=values.get("closing_time_override"),
                )
            else:
                self.faculty.update_group_properties(
                    group_uuid=node.uuid,
                    name=values.get("name"),
                    default_ventilated=values.get("default_ventilated"),
                    opening_time_override=values.get("opening_time_override"),
                    closing_time_override=values.get("closing_time_override"),
                )

        elif node_type == "space":
            self.faculty.update_space_properties(
                node_uuid=node.uuid,
                name=values.get("name"),
                capacity=values.get("capacity"),
                space_type_uuid=values.get("space_type_uuid"),
                ventilated=values.get("ventilated"),
                opening_time_override=values.get("opening_time_override"),
                closing_time_override=values.get("closing_time_override"),
            )

        elif node_type == "career":
            self.faculty.update_career_properties(
                career_uuid=node.uuid,
                name=values.get("name"),
                students_by_year=values.get("students_by_year"),
                default_attendance_rate=values.get("default_attendance_rate"),
                mean_age=values.get("mean_age"),
                std_age=values.get("std_age"),
                sex_ratio=values.get("sex_ratio"),
            )

        elif node_type == "course":
            self.faculty.update_course_properties(
                course_uuid=node.uuid,
                name=values.get("name"),
                number_of_students=values.get("number_of_students"),
                attendance_rate=values.get("attendance_rate"),
                mean_age=values.get("mean_age"),
                std_age=values.get("std_age"),
                sex_ratio=values.get("sex_ratio"),
            )

            if "base_schedule_blocks" in values:
                blocks = self._build_schedule_blocks_from_values(values["base_schedule_blocks"])
                self.faculty.set_course_base_schedule(node.uuid, blocks)

        elif node_type == "coursegroup":
            self.faculty.update_course_group_properties(
                group_uuid=node.uuid,
                name=values.get("name"),
                number_of_students=values.get("number_of_students"),
                attendance_rate=values.get("attendance_rate"),
                mean_age=values.get("mean_age"),
                std_age=values.get("std_age"),
                sex_ratio=values.get("sex_ratio"),
            )

            if "schedule_override_blocks" in values:
                blocks = self._build_schedule_blocks_from_values(values["schedule_override_blocks"])
                self.faculty.set_course_group_schedule_overrides(node.uuid, blocks)

        self.refresh_all()

    # -------------------------
    # CONTENEDORES / EXPANSIÓN
    # -------------------------

    def toggle_group(self, node_uuid: str) -> None:
        node = self.faculty.find_node(node_uuid)

        if node is None:
            self._show_error(f"No se ha encontrado el nodo con uuid: {node_uuid}")
            return

        if not self._is_expandable_container(node):
            return

        if hasattr(self.faculty, "toggle_container_expanded"):
            self.faculty.toggle_container_expanded(node_uuid)
        else:
            self.faculty.toggle_group_expanded(node_uuid)

        self.refresh_all()

    def toggle_selected_group(self) -> None:
        if self.selected_node_uuid is None:
            return

        self.toggle_group(self.selected_node_uuid)

    # -------------------------
    # HELPERS
    # -------------------------

    def _get_selected_space_parent_uuid(self) -> Optional[str]:
        if self.selected_node_uuid is None:
            return None

        selected_node = self.faculty.find_node(self.selected_node_uuid)

        if selected_node is None:
            return None

        node_type = self._get_node_type(selected_node)

        if node_type in {"root", "group", "spacegroup"}:
            return selected_node.uuid

        if node_type == "space":
            return selected_node.parent_uuid

        return None

    def _get_selected_career_uuid_for_course_creation(self) -> Optional[str]:
        if self.selected_node_uuid is None:
            return None

        node = self.faculty.find_node(self.selected_node_uuid)
        if node is None:
            return None

        if self._get_node_type(node) == "career":
            return node.uuid

        return None

    def _get_selected_course_uuid_for_group_creation(self) -> Optional[str]:
        if self.selected_node_uuid is None:
            return None

        node = self.faculty.find_node(self.selected_node_uuid)
        if node is None:
            return None

        node_type = self._get_node_type(node)

        if node_type == "course":
            return node.uuid

        if node_type == "coursegroup":
            return getattr(node, "course_uuid", None)

        return None

    def _node_belongs_to_active_builder(self, node: Any) -> bool:
        node_type = self._get_node_type(node)

        if self.builder_mode == "space":
            return node_type in {"root", "group", "spacegroup", "space"}

        return node_type in {"root", "career", "course", "coursegroup"}

    def _get_node_type(self, node: Any) -> str:
        return node.__class__.__name__.lower()

    def _is_root(self, node: Any) -> bool:
        return self._get_node_type(node) == "root"

    def _is_expandable_container(self, node: Any) -> bool:
        return self._get_node_type(node) in {
            "group", "spacegroup", "career", "course"
        }

    def _show_error(self, message: str) -> None:
        if self.ui is not None:
            self.ui.show_error(message)
        else:
            print(f"[BuilderController error] {message}")

    def _collect_subtree_uuids(self, node_uuid: str) -> list[str]:
        uuids = [node_uuid]

        for child in self.faculty.get_children(node_uuid):
            uuids.extend(self._collect_subtree_uuids(child.uuid))

        return uuids