from __future__ import annotations

from typing import Optional, Any

from backend.faculty import Faculty


class BuilderController:
    def __init__(self, faculty: Faculty, ui: Optional[Any] = None):
        self.faculty = faculty
        self.ui = ui
        self.selected_node_uuid: Optional[str] = None

    def attach_ui(self, ui: Any) -> None:
        self.ui = ui

    # -------------------------
    # CARGA Y REFRESCO GENERAL
    # -------------------------

    def load_builder(self) -> None:
        """
        Carga inicial del Builder.
        Se llamará al entrar en la pantalla de construcción.
        """
        self.refresh_all()

    def refresh_all(self) -> None:
        """
        Refresca toda la UI del Builder:
        - panel izquierdo: árbol
        - panel central: grafo
        - panel derecho: propiedades del nodo seleccionado
        """
        if self.ui is None:
            return

        root = self.faculty.get_root()
        graph_data = self._build_graph_data()

        self.ui.render_tree(root)
        self.ui.render_graph(graph_data)

        if self.selected_node_uuid is not None:
            selected_node = self.faculty.find_node(self.selected_node_uuid)

            if selected_node is None:
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

        if node is None:
            self.selected_node_uuid = None
            self.ui.select_node_visual(None)
            self.ui.clear_properties_panel()
            return

        valid_parents = self.faculty.get_valid_parents(self.selected_node_uuid)
        self.ui.show_node_properties(node, valid_parents)

    def _build_graph_data(self) -> dict:
        """
        Convierte el estado del backend en datos simples para el frontend.

        En vez de depender de get_children(), las aristas se construyen
        leyendo el parent_uuid de cada nodo visible.
        Eso es más robusto para la visualización del grafo.
        """
        root = self.faculty.get_root()
        visible_nodes = self.faculty.get_visible_nodes()

        # Aseguramos que root siempre esté incluida
        visible_by_uuid = {node.uuid: node for node in visible_nodes}
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

        # Construimos edges leyendo parent_uuid
        for node in visible_nodes:
            if node.uuid == root.uuid:
                continue

            parent_uuid = getattr(node, "parent_uuid", None)

            # Si no tiene padre explícito, lo conectamos a root
            if parent_uuid is None:
                parent_uuid = root.uuid

            # Solo dibujamos la arista si el padre también es visible
            if parent_uuid in visible_uuids:
                edges.append({
                    "source": parent_uuid,
                    "target": node.uuid,
                })

        print("NODES:")
        for n in nodes:
            print(n)

        print("EDGES:")
        for e in edges:
            print(e)

        print("PARENTS:")
        for node in visible_nodes:
            print(node.name, node.uuid, getattr(node, "parent_uuid", None))

        return {
            "nodes": nodes,
            "edges": edges,
        }

    # -------------------------
    # SELECCIÓN
    # -------------------------

    def select_node(self, node_uuid: str) -> None:
        node = self.faculty.find_node(node_uuid)

        if node is None:
            self._show_error(f"No se ha encontrado el nodo con uuid: {node_uuid}")
            return

        self.selected_node_uuid = node_uuid

        if self.ui is not None:
            self.ui.select_node_visual(node_uuid)
            valid_parents = self.faculty.get_valid_parents(node_uuid)
            self.ui.show_node_properties(node, valid_parents)

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

    def create_group_under_selected_parent(self, name: str = "Nuevo grupo") -> None:
        parent_uuid = self._get_selected_parent_uuid()
        self.create_group(name=name, parent_uuid=parent_uuid)

    def create_space_under_selected_parent(self, name: str = "Nuevo espacio") -> None:
        parent_uuid = self._get_selected_parent_uuid()
        self.create_space(name=name, parent_uuid=parent_uuid)

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

    def rename_node(self, node_uuid: str, new_name: str) -> None:
        new_name = new_name.strip()

        if not new_name:
            self._show_error("El nombre no puede estar vacío.")
            self.refresh_all()
            return

        node = self.faculty.find_node(node_uuid)

        if node is None:
            self._show_error(f"No se ha encontrado el nodo con uuid: {node_uuid}")
            return

        if self._is_root(node):
            self.faculty.rename_faculty(new_name)
        else:
            self.faculty.rename_node(node_uuid, new_name)

        self.refresh_all()

    def rename_faculty(self, new_name: str) -> None:
        new_name = new_name.strip()

        if not new_name:
            self._show_error("El nombre de la facultad no puede estar vacío.")
            self.refresh_all()
            return

        self.faculty.rename_faculty(new_name)
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

    def delete_node(self, node_uuid: str) -> None:
        node = self.faculty.find_node(node_uuid)

        if node is None:
            self._show_error(f"No se ha encontrado el nodo con uuid: {node_uuid}")
            return

        if self._is_root(node):
            self._show_error("No se puede eliminar la raíz de la facultad.")
            return

        deleted_uuids = self._collect_subtree_uuids(node_uuid)

        if self.selected_node_uuid == node_uuid:
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

    # -------------------------
    # GRUPOS
    # -------------------------

    def toggle_group(self, group_uuid: str) -> None:
        node = self.faculty.find_node(group_uuid)

        if node is None:
            self._show_error(f"No se ha encontrado el grupo con uuid: {group_uuid}")
            return

        if not self._is_group(node):
            return

        self.faculty.toggle_group_expanded(group_uuid)
        self.refresh_all()

    def toggle_selected_group(self) -> None:
        if self.selected_node_uuid is None:
            return

        self.toggle_group(self.selected_node_uuid)

    def set_group_expanded(self, group_uuid: str, expanded: bool) -> None:
        node = self.faculty.find_node(group_uuid)

        if node is None:
            self._show_error(f"No se ha encontrado el grupo con uuid: {group_uuid}")
            return

        if not self._is_group(node):
            return

        self.faculty.set_group_expanded(group_uuid, expanded)
        self.refresh_all()

    # -------------------------
    # PROPIEDADES VISUALES
    # -------------------------

    def update_selected_node_size(self, size: float) -> None:
        if self.selected_node_uuid is None:
            return

        self.update_node_size(self.selected_node_uuid, size)

    def update_node_size(self, node_uuid: str, size: float) -> None:
        node = self.faculty.find_node(node_uuid)

        if node is None:
            self._show_error(f"No se ha encontrado el nodo con uuid: {node_uuid}")
            return

        size = float(size)

        if size <= 0:
            self._show_error("El tamaño del nodo debe ser mayor que 0.")
            return

        self.faculty.update_node_size(node_uuid, size)
        self.refresh_all()

    # -------------------------
    # PROPIEDADES DE ESPACIOS
    # -------------------------

    def update_selected_space_capacity(self, capacity: Optional[int]) -> None:
        if self.selected_node_uuid is None:
            return

        self.update_space_capacity(self.selected_node_uuid, capacity)

    def update_space_capacity(self, node_uuid: str, capacity: Optional[int]) -> None:
        node = self.faculty.find_node(node_uuid)

        if node is None:
            self._show_error(f"No se ha encontrado el espacio con uuid: {node_uuid}")
            return

        if not self._is_space(node):
            return

        if capacity is not None and capacity < 0:
            self._show_error("La capacidad no puede ser negativa.")
            return

        self.faculty.update_space_properties(
            node_uuid=node_uuid,
            capacity=capacity,
        )

        self.refresh_all()

    # -------------------------
    # HELPERS
    # -------------------------

    def _get_selected_parent_uuid(self) -> Optional[str]:
        """
        Devuelve el uuid del padre donde se debería crear un nuevo nodo.

        Si no hay selección, el backend usará la raíz porque parent_uuid=None.
        Si la selección es Root o Group, se crea dentro de ese nodo.
        Si la selección es Space, se crea en la raíz por ahora.
        """
        if self.selected_node_uuid is None:
            return None

        selected_node = self.faculty.find_node(self.selected_node_uuid)

        if selected_node is None:
            return None

        if self._is_root(selected_node) or self._is_group(selected_node):
            return selected_node.uuid

        return None

    def _get_node_type(self, node: Any) -> str:
        """
        Devuelve el tipo de nodo como string estable para el frontend.

        El frontend espera:
        - root
        - group
        - space
        """
        return node.__class__.__name__.lower()

    def _is_root(self, node: Any) -> bool:
        return self._get_node_type(node) == "root"

    def _is_group(self, node: Any) -> bool:
        return self._get_node_type(node) == "group"

    def _is_space(self, node: Any) -> bool:
        return self._get_node_type(node) == "space"

    def _show_error(self, message: str) -> None:
        if self.ui is not None:
            self.ui.show_error(message)
        else:
            print(f"[BuilderController error] {message}")

    def _collect_subtree_uuids(self, node_uuid: str) -> list[str]:
        """
        Devuelve el uuid del nodo y de todos sus descendientes.
        Sirve para limpiar la caché visual del grafo al borrar nodos.
        """
        uuids = [node_uuid]

        for child in self.faculty.get_children(node_uuid):
            uuids.extend(self._collect_subtree_uuids(child.uuid))

        return uuids