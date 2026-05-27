from __future__ import annotations

from dataclasses import dataclass, field
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
# MODELO DE NODOS
# ============================================================

@dataclass
class Node:
    uuid: str
    name: str
    parent_uuid: Optional[str] = None
    size: float = 1.0

    def is_group(self) -> bool:
        return False

    def is_space(self) -> bool:
        return False

    def is_root(self) -> bool:
        return False


@dataclass
class Group(Node):
    children_uuids: List[str] = field(default_factory=list)
    expanded: bool = True

    default_ventilated: bool = False
    opening_time_override: Optional[str] = None
    closing_time_override: Optional[str] = None

    def is_group(self) -> bool:
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
class Root(Node):
    children_uuids: List[str] = field(default_factory=list)

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
    """
    Controlador principal del escenario.
    Mantiene:
    - índice global de nodos por UUID
    - nodo raíz "Pasillo"
    - utilidades de carga y consulta
    """

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

    def _add_node(self, node: Node) -> None:
        if node.uuid in self.nodes:
            raise ValueError(f"Ya existe un nodo con UUID {node.uuid}")
        self.nodes[node.uuid] = node

    def _get_node(self, node_uuid: str) -> Node:
        if node_uuid not in self.nodes:
            raise KeyError(f"No existe el nodo con UUID {node_uuid}")
        return self.nodes[node_uuid]

    def _get_container(self, node_uuid: str) -> Root | Group:
        node = self._get_node(node_uuid)

        if not isinstance(node, (Root, Group)):
            raise TypeError(f"El nodo {node_uuid} no puede contener hijos")

        return node


    def _attach_child(self, parent_uuid: str, child_uuid: str) -> None:
        parent = self._get_container(parent_uuid)
        child = self._get_node(child_uuid)

        if child_uuid not in parent.children_uuids:
            parent.children_uuids.append(child_uuid)

        child.parent_uuid = parent_uuid

    def _iter_nodes_for_saving(self) -> list[Node]:
        """
        Devuelve los nodos en orden jerárquico desde la raíz.
        Útil para que el CSV sea legible y estable.
        """

        ordered_nodes: list[Node] = []

        def visit(node_uuid: str) -> None:
            node = self._get_node(node_uuid)
            ordered_nodes.append(node)

            if isinstance(node, (Root, Group)):
                for child_uuid in node.children_uuids:
                    if child_uuid in self.nodes:
                        visit(child_uuid)

        visit(self.root_uuid)
        return ordered_nodes

    def _is_descendant(self, possible_descendant_uuid: str, possible_ancestor_uuid: str) -> bool:
        """
        Devuelve True si possible_descendant_uuid está dentro de la jerarquía
        de possible_ancestor_uuid.
        """

        current_uuid = possible_descendant_uuid

        while current_uuid is not None:
            if current_uuid == possible_ancestor_uuid:
                return True

            current_node = self._get_node(current_uuid)
            current_uuid = current_node.parent_uuid

        return False
    
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

    def update_group_properties(
        self,
        group_uuid: str,
        name: Optional[str] = None,
        default_ventilated: Optional[bool] = None,
        opening_time_override: Optional[str] = None,
        closing_time_override: Optional[str] = None,
    ) -> None:
        node = self._get_node(group_uuid)

        if not isinstance(node, Group):
            raise ValueError("Solo los grupos pueden tener propiedades de grupo.")

        if name is not None:
            node.name = name.strip()

        if default_ventilated is not None:
            node.default_ventilated = default_ventilated

        if opening_time_override is not None:
            node.opening_time_override = opening_time_override

        if closing_time_override is not None:
            node.closing_time_override = closing_time_override

    # -------------------------
    # API pública básica
    # -------------------------

    def create_group(self, name: str, parent_uuid: Optional[str] = None, node_uuid: Optional[str] = None) -> Group:
        if node_uuid is None:
            node_uuid = self._generate_uuid()

        if parent_uuid is None:
            parent_uuid = self.root_uuid

        group = Group(uuid=node_uuid, name=name, parent_uuid=None)
        self._add_node(group)
        self._attach_child(parent_uuid, group.uuid)
        return group

    def create_space(self, name: str, parent_uuid: Optional[str] = None, node_uuid: Optional[str] = None) -> Space:
        if node_uuid is None:
            node_uuid = self._generate_uuid()

        if parent_uuid is None:
            parent_uuid = self.root_uuid

        space = Space(uuid=node_uuid, name=name, parent_uuid=None)
        self._add_node(space)
        self._attach_child(parent_uuid, space.uuid)
        return space

    def get_root(self) -> Root:
        return self._get_node(self.root_uuid)

    def get_children(self, node_uuid: str) -> List[Node]:
        node = self._get_node(node_uuid)

        if not isinstance(node, (Root, Group)):
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

        if isinstance(node, (Group, Root)):
            children_to_move = list(node.children_uuids)
        else:
            children_to_move = []

        # Buscar posición del nodo eliminado dentro del padre
        try:
            insert_index = parent.children_uuids.index(node_uuid)
        except ValueError:
            insert_index = len(parent.children_uuids)

        # Quitar nodo del padre
        if node_uuid in parent.children_uuids:
            parent.children_uuids.remove(node_uuid)

        # Mover hijos al padre del nodo eliminado
        for offset, child_uuid in enumerate(children_to_move):
            child = self._get_node(child_uuid)
            child.parent_uuid = parent_uuid
            parent.children_uuids.insert(insert_index + offset, child_uuid)

        # Vaciar hijos del nodo eliminado
        if isinstance(node, Group):
            node.children_uuids.clear()

        self.selected_node = None

        # Eliminar nodo
        del self.nodes[node_uuid]
    
    def move_node(self, node_uuid: str, new_parent_uuid: str) -> None:
        """
        Mueve un nodo a un nuevo padre.

        Parámetros:
        - node_uuid: nodo que queremos mover.
        - new_parent_uuid: nuevo padre. Debe ser Root o Group.
        - index: posición opcional dentro de la lista de hijos del nuevo padre.

        Reglas:
        - Root no se puede mover.
        - El nuevo padre no puede ser un Space.
        - Un nodo no puede moverse dentro de sí mismo.
        - Un grupo no puede moverse dentro de uno de sus descendientes.
        """

        node = self._get_node(node_uuid)
        new_parent = self._get_node(new_parent_uuid)

        if isinstance(node, Root):
            raise ValueError("No se puede mover el nodo raíz.")

        if not isinstance(new_parent, (Root, Group)):
            raise ValueError("El nuevo padre debe ser la raíz o un grupo.")

        if node_uuid == new_parent_uuid:
            raise ValueError("Un nodo no puede moverse dentro de sí mismo.")

        if isinstance(node, Group):
            if self._is_descendant(
                possible_descendant_uuid=new_parent_uuid,
                possible_ancestor_uuid=node_uuid,
            ):
                raise ValueError("No se puede mover un grupo dentro de uno de sus descendientes.")

        old_parent_uuid = node.parent_uuid

        if old_parent_uuid is not None:
            old_parent = self._get_container(old_parent_uuid)

            if node_uuid in old_parent.children_uuids:
                old_parent.children_uuids.remove(node_uuid)

        new_parent_container = self._get_container(new_parent_uuid)

        new_parent_container.children_uuids.append(node_uuid)

        node.parent_uuid = new_parent_uuid
    
    def get_valid_parents(self, node_uuid: str) -> list[Node]:
        """
        Devuelve los nodos que pueden actuar como nuevo padre del nodo indicado.
        Válidos:
        - Root
        - Group

        Excluye:
        - el propio nodo
        - sus descendientes
        - espacios
        """

        node = self._get_node(node_uuid)

        if isinstance(node, Root):
            return []

        valid_parents: list[Node] = []

        for candidate in self.nodes.values():
            if not isinstance(candidate, (Root, Group)):
                continue

            if candidate.uuid == node_uuid:
                continue

            if self._is_descendant(
                possible_descendant_uuid=candidate.uuid,
                possible_ancestor_uuid=node_uuid,
            ):
                continue

            valid_parents.append(candidate)

        return valid_parents
    
    def get_visible_nodes(self) -> list[Node]:
        """
        Devuelve los nodos visibles en la vista central según el estado
        expanded/contracted de los grupos.

        Root no se devuelve como nodo visual normal.
        """

        visible_nodes: list[Node] = []

        def visit(node_uuid: str) -> None:
            node = self._get_node(node_uuid)

            if not isinstance(node, Root):
                visible_nodes.append(node)

            if isinstance(node, Root):
                for child_uuid in node.children_uuids:
                    visit(child_uuid)

            elif isinstance(node, Group) and node.expanded:
                for child_uuid in node.children_uuids:
                    visit(child_uuid)

        visit(self.root_uuid)

        return visible_nodes
    
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
        """
        Actualiza propiedades específicas de un Space.
        """
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

    def update_node_size(self, node_uuid: str, size: float) -> None:
        """
        Actualiza el tamaño visual de un nodo.
        """

        node = self._get_node(node_uuid)

        if size < self.MIN_NODE_SIZE:
            size = self.MIN_NODE_SIZE

        if size > self.MAX_NODE_SIZE:
            size = self.MAX_NODE_SIZE

        node.size = size

    def set_group_expanded(self, group_uuid: str, expanded: bool) -> None:
        node = self._get_node(group_uuid)

        if not isinstance(node, Group):
            raise ValueError("Solo los grupos pueden expandirse o contraerse.")

        node.expanded = expanded

    def toggle_group_expanded(self, group_uuid: str) -> None:
        node = self._get_node(group_uuid)

        if not isinstance(node, Group):
            raise ValueError("Solo los grupos pueden expandirse o contraerse.")

        node.expanded = not node.expanded
    
    def select_node(self, node_uuid: str) -> None:
        node = self._get_node(node_uuid)

        self.selected_node = node

    def get_time_options(self) -> list[str]:
        return TIME_OPTIONS


    def get_schedule_slot_options(self) -> list[int]:
        return SLOT_MINUTE_OPTIONS


    def get_calendar_day_options(self) -> list[str]:
        return CALENDAR_DAY_OPTIONS


    def get_space_types(self) -> list[SpaceType]:
        return self.space_types

    # -------------------------
    # Carga desde CSV
    # -------------------------

    @classmethod
    def load_from_csv(cls, csv_path: str | Path) -> "Faculty":
        """
        Carga el escenario en dos pasadas.

        Columnas mínimas esperadas:
        - uuid
        - node_type   ("group" o "space")
        - name
        - parent_uuid

        Reglas:
        - si falta uuid, se genera uno
        - si falta parent_uuid o es inválido, se conecta al Pasillo
        - si el padre existe pero no es Group, se conecta al Pasillo
        """
        faculty = cls()
        csv_path = Path(csv_path)

        raw_rows: List[dict] = []

        # -------------------------
        # Primera pasada:
        # leer filas y crear nodos
        # -------------------------
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)

            required_columns = {"uuid", "node_type", "name", "parent_uuid"}
            missing = required_columns - set(reader.fieldnames or [])
            if missing:
                raise ValueError(
                    f"Faltan columnas obligatorias en el CSV: {sorted(missing)}"
                )

            for line_number, row in enumerate(reader, start=2):
                raw_rows.append(row)

                node_uuid = (row.get("uuid") or "").strip()
                node_type = (row.get("node_type") or "").strip().lower()
                name = (row.get("name") or "").strip()
                parent_uuid = (row.get("parent_uuid") or "").strip() or None

                if not name:
                    faculty.warnings.append(
                        f"Línea {line_number}: nombre vacío. Se omite la fila."
                    )
                    continue

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

                if node_type == "group":
                    node = Group(uuid=node_uuid, name=name, parent_uuid=parent_uuid)
                elif node_type == "space":
                    node = Space(uuid=node_uuid, name=name, parent_uuid=parent_uuid)
                else:
                    faculty.warnings.append(
                        f"Línea {line_number}: node_type inválido '{node_type}' en '{name}'. Se omite la fila."
                    )
                    continue

                faculty._add_node(node)

        # -------------------------
        # Segunda pasada:
        # resolver parentescos
        # -------------------------
        for node_uuid, node in list(faculty.nodes.items()):
            if node_uuid == faculty.root_uuid:
                continue

            desired_parent_uuid = node.parent_uuid

            # Sin padre -> Pasillo
            if desired_parent_uuid is None:
                faculty._attach_child(faculty.root_uuid, node_uuid)
                faculty.warnings.append(
                    f"Nodo '{node.name}' ({node.uuid}) sin padre. Conectado a Pasillo."
                )
                continue

            # Padre inexistente -> Pasillo
            parent = faculty.find_node(desired_parent_uuid)
            if parent is None:
                faculty._attach_child(faculty.root_uuid, node_uuid)
                faculty.warnings.append(
                    f"Nodo '{node.name}' ({node.uuid}) con padre inexistente ({desired_parent_uuid}). "
                    f"Conectado a Pasillo."
                )
                continue

            # Padre no es grupo -> Pasillo
            if not isinstance(parent, Group):
                faculty._attach_child(faculty.root_uuid, node_uuid)
                faculty.warnings.append(
                    f"Nodo '{node.name}' ({node.uuid}) tenía como padre un Space ({desired_parent_uuid}). "
                    f"Conectado a Pasillo."
                )
                continue

            # Evitar autorreferencia
            if desired_parent_uuid == node_uuid:
                faculty._attach_child(faculty.root_uuid, node_uuid)
                faculty.warnings.append(
                    f"Nodo '{node.name}' ({node.uuid}) apuntaba a sí mismo como padre. "
                    f"Conectado a Pasillo."
                )
                continue

            faculty._attach_child(desired_parent_uuid, node_uuid)

        return faculty
    
    # -------------------------
    # Guardado en CSV
    # -------------------------

    def save_to_csv(self, csv_path: str | Path, mode: str = "autosave") -> list[str]:
        """
        Guarda el escenario actual en CSV.

        mode:
        - "autosave": guarda el estado actual aunque haya nodos incompletos.
        - "manual": valida antes de guardar y devuelve errores si faltan datos.

        Devuelve una lista de errores de validación.
        Si la lista está vacía, el guardado se ha realizado correctamente.
        """

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

            if isinstance(node, Group):
                node_type = "group"
                capacity = ""

            elif isinstance(node, Space):
                node_type = "space"
                capacity = "" if node.capacity is None else node.capacity

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
        """
        Comprueba si el escenario tiene la información mínima
        necesaria para poder simular.

        De momento:
        - todos los nodos deben tener nombre
        - todos los espacios deben tener capacidad
        - la capacidad debe ser mayor que 0
        """

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
        elif isinstance(node, Group):
            node_type = "GROUP"
        elif isinstance(node, Space):
            node_type = "SPACE"
        else:
            node_type = "NODE"

        print(f"{prefix}- [{node_type}] {node.name} ({node.uuid})")

        if isinstance(node, (Root, Group)):
            for child_uuid in node.children_uuids:
                if child_uuid in self.nodes:
                    self.print_tree(child_uuid, indent + 1)
                else:
                    print(f"{prefix}  - [MISSING] Nodo inexistente ({child_uuid})")
    
    def debug_select_node(self) -> Node:
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
    faculty = Faculty.load_from_csv("Facultades/Pruebas/escenario_facultad_ejemplo.csv")

    faculty.print_tree()

    print("\nWarnings:")
    for warning in faculty.warnings:
        print("-", warning)

    faculty.save_to_csv("proba.csv")