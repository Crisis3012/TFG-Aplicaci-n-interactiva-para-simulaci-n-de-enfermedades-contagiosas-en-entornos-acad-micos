from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import csv
import uuid


# ============================================================
# MODELO DE NODOS
# ============================================================

@dataclass
class Node:
    uuid: str
    name: str
    parent_uuid: Optional[str] = None

    def is_group(self) -> bool:
        return False

    def is_space(self) -> bool:
        return False

    def is_root(self) -> bool:
        return False


@dataclass
class Group(Node):
    children_uuids: List[str] = field(default_factory=list)
    expanded: bool = False

    def is_group(self) -> bool:
        return True


@dataclass
class Space(Node):
    def is_space(self) -> bool:
        return True
    

@dataclass
class Root(Node):
    children_uuids: List[str] = field(default_factory=list)

    def is_root(self) -> bool:
        return True


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

    def __init__(self) -> None:
        self.nodes: Dict[str, Node] = {}
        self.warnings: List[str] = []

        self.root_uuid = self._generate_uuid()

        root = Root(
            uuid=self.root_uuid,
            name=self.ROOT_NAME,
            parent_uuid=None,
        )

        self.nodes[self.root_uuid] = root

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

    def get_root(self) -> Group:
        return self._get_group(self.root_uuid)

    def get_children(self, node_uuid: str) -> List[Node]:
        node = self._get_node(node_uuid)
        if not isinstance(node, Group):
            return []
        return [self._get_node(child_uuid) for child_uuid in node.children_uuids]

    def find_node(self, node_uuid: str) -> Optional[Node]:
        return self.nodes.get(node_uuid)

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
    # Debug / inspección
    # -------------------------

    def print_tree(self, start_uuid: Optional[str] = None, indent: int = 0) -> None:
        if start_uuid is None:
            start_uuid = self.root_uuid

        node = self._get_node(start_uuid)
        prefix = "  " * indent

        node_type = "GROUP" if isinstance(node, Group) else "SPACE"
        print(f"{prefix}- [{node_type}] {node.name} ({node.uuid})")

        if isinstance(node, Group):
            for child_uuid in node.children_uuids:
                self.print_tree(child_uuid, indent + 1)

if __name__ == "__main__":
    faculty = Faculty.load_from_csv("Facultades/Pruebas/escenario_facultad_ejemplo.csv")

    faculty.print_tree()

    print("\nWarnings:")
    for warning in faculty.warnings:
        print("-", warning)