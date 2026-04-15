# Documentación temporal: arquitectura del Builder UI

Este documento resume la estructura propuesta para organizar el frontend del Builder y su conexión con el backend mediante un controlador. La idea general es mantener una separación clara entre datos, lógica de coordinación e interfaz gráfica.

```text
Backend  ←  Controller  →  Frontend
```

- El **backend** guarda y modifica los datos reales de la facultad.
- El **controller** recibe acciones del frontend, llama al backend y ordena refrescar la interfaz.
- El **frontend** muestra la información y detecta las interacciones del usuario.

---

## Estructura general de carpetas

```text
project/
│
├── main.py
│
├── backend/
│   └── faculty.py
│
├── controller/
│   └── builder_controller.py
│
└── frontend/
    ├── __init__.py
    ├── main_window.py
    ├── menu_page.py
    ├── builder_page.py
    ├── builder_tree_panel.py
    ├── builder_properties_panel.py
    ├── graph_view.py
    ├── graph_items.py
    └── styles.py
```

---

# 1. `main.py`

Archivo encargado de arrancar la aplicación.

## Clases usadas

```python
QApplication
MainWindow
Faculty
BuilderController
```

## Funciones principales

```python
main()
```

## Responsabilidades

- Crear la aplicación de Qt.
- Crear el objeto `Faculty` del backend.
- Crear el `BuilderController`.
- Crear la ventana principal `MainWindow`.
- Mostrar la ventana.
- Ejecutar el bucle principal de la aplicación.

## Flujo básico

```text
main.py
↓
crea Faculty
↓
crea BuilderController
↓
crea MainWindow
↓
muestra la app
```

---

# 2. `backend/faculty.py`

Archivo donde está la lógica de datos de la facultad.

## Clases esperadas

```python
Faculty
Node
Root
Group
Space
```

## Funciones principales de `Faculty`

```python
create_group(name, parent_uuid=None, node_uuid=None)
create_space(name, parent_uuid=None, node_uuid=None)
get_root()
get_children(node_uuid)
find_node(node_uuid)
rename_node(node_uuid, new_name)
rename_faculty(new_name)
delete_node(node_uuid)
move_node(node_uuid, new_parent_uuid)
toggle_group_expanded(group_uuid)
get_valid_parents(node_uuid)
get_visible_nodes()
update_space_properties(node_uuid, capacity=None)
update_node_size(node_uuid, size)
set_group_expanded(group_uuid, expanded)
```

## Responsabilidades

- Guardar la estructura real de la facultad.
- Crear grupos y espacios.
- Eliminar nodos.
- Renombrar nodos.
- Mover nodos entre padres.
- Controlar qué grupos están expandidos o contraídos.
- Devolver los nodos visibles para el grafo.
- Actualizar propiedades de nodos y espacios.

## Nota importante

El backend no debería depender de PySide6 ni conocer nada de la interfaz gráfica.

---

# 3. `controller/builder_controller.py`

Archivo que conecta el backend con el frontend.

## Clase principal

```python
class BuilderController:
```

## Atributos principales

```python
self.faculty
self.ui
self.selected_node_uuid
```

## Funciones principales

```python
attach_ui(ui)
load_builder()
refresh_all()

select_node(node_uuid)
clear_selection()

create_group(name, parent_uuid=None)
create_space(name, parent_uuid=None)

rename_selected_node(new_name)
delete_selected_node()
move_selected_node(new_parent_uuid)

toggle_group(group_uuid)
set_group_expanded(group_uuid, expanded)

update_selected_node_size(size)
update_selected_space_capacity(capacity)

_build_graph_data()
```

## Responsabilidades

- Recibir acciones del usuario desde el frontend.
- Llamar a las funciones correctas del backend.
- Mantener qué nodo está seleccionado.
- Convertir el modelo del backend en datos simples para el grafo.
- Ordenar al frontend que refresque:
  - el árbol izquierdo,
  - el grafo central,
  - el panel derecho de propiedades.

## Ejemplo de flujo

```text
Usuario selecciona nodo
↓
GraphView emite node_selected(uuid)
↓
BuilderController.select_node(uuid)
↓
Faculty.find_node(uuid)
↓
BuilderPage actualiza selección y propiedades
```

## Nota sobre `_build_graph_data()`

El frontend no debería depender directamente de las clases internas del backend. Por eso el controller genera una estructura como esta:

```python
{
    "nodes": [
        {
            "uuid": "...",
            "name": "Aula 1",
            "type": "space",
            "size": 100,
        }
    ],
    "edges": [
        {
            "source": "uuid_padre",
            "target": "uuid_hijo",
        }
    ]
}
```

---

# 4. `frontend/main_window.py`

Archivo con la ventana principal de la aplicación.

## Clase principal

```python
class MainWindow(QWidget):
```

## Contiene

```python
QStackedWidget
MenuPage
BuilderPage
```

## Funciones principales

```python
__init__()
```

Opcionalmente, en una versión más avanzada:

```python
go_to_menu()
go_to_builder()
go_to_simulation()
go_to_visualization()
```

## Responsabilidades

- Crear la ventana principal.
- Crear el contenedor de páginas `QStackedWidget`.
- Añadir la página inicial.
- Añadir la página del Builder.
- Gestionar el cambio entre pantallas principales.

## Flujo

```text
MainWindow
↓
QStackedWidget
├── MenuPage
└── BuilderPage
```

---

# 5. `frontend/menu_page.py`

Archivo con la pantalla inicial de la aplicación.

## Clase principal

```python
class MenuPage(QWidget):
```

## Contiene

- Título provisional: `TFG`.
- Botón `Builder`.
- Botón `Simular`.
- Botón `Visualizar`.
- Botón `Salir`.

## Funciones principales

```python
__init__()
open_builder()
```

## Responsabilidades

- Mostrar el menú principal.
- Permitir entrar al Builder.
- Cerrar la aplicación con el botón `Salir`.

## Flujo

```text
Usuario pulsa Builder
↓
MenuPage.open_builder()
↓
QStackedWidget cambia a BuilderPage
↓
BuilderController.load_builder()
```

---

# 6. `frontend/builder_page.py`

Archivo con la página principal del Builder.

## Clase principal

```python
class BuilderPage(QWidget):
```

## Contiene

```python
QSplitter horizontal
BuilderTreePanel
GraphView
BuilderPropertiesPanel
```

## Funciones principales

```python
__init__()
_build_ui()
_connect_signals()

render_tree(root)
render_graph(graph_data)
select_node_visual(node_uuid)
show_node_properties(node, valid_parents)
clear_properties_panel()
show_error(message)
```

## Responsabilidades

- Construir la interfaz del Builder.
- Organizar los 3 paneles principales:
  - izquierda: árbol de facultad,
  - centro: grafo interactivo,
  - derecha: propiedades del nodo seleccionado.
- Conectar señales del frontend con métodos del controller.
- Actuar como interfaz visible que el controller puede refrescar.

## Distribución visual

```text
┌─────────────────────────────────────────────────────────────┐
│ BuilderPage                                                  │
│                                                             │
│ ┌──────────────┬──────────────────────────┬───────────────┐ │
│ │ Tree Panel   │ Graph View               │ Properties    │ │
│ │ izquierdo    │ centro                   │ Panel derecho │ │
│ └──────────────┴──────────────────────────┴───────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Flujo de señales

```text
TreePanel.node_selected
↓
BuilderController.select_node

GraphView.node_selected
↓
BuilderController.select_node

PropertiesPanel.name_changed
↓
BuilderController.rename_selected_node
```

---

# 7. `frontend/builder_tree_panel.py`

Archivo con el panel izquierdo del Builder.

## Clase principal

```python
class BuilderTreePanel(QFrame):
```

## Contiene

```python
QTreeWidget
QPushButton Crear grupo
QPushButton Crear espacio
QPushButton Expandir/contraer
QPushButton Eliminar
```

## Señales recomendadas

```python
node_selected = Signal(str)
create_group_requested = Signal()
create_space_requested = Signal()
delete_requested = Signal()
toggle_group_requested = Signal()
```

## Funciones principales

```python
render_tree(root, get_children_func)
select_node(node_uuid)
clear_selection()
_create_tree_item(node)
_add_children(parent_item, parent_node, get_children_func)
_on_item_clicked(item, column)
```

## Responsabilidades

- Mostrar la estructura jerárquica de la facultad.
- Mostrar nodos como si fuera un explorador de archivos.
- Permitir seleccionar nodos desde el árbol.
- Permitir crear grupos y espacios.
- Permitir eliminar nodos.
- Permitir expandir o contraer grupos.

## Ejemplo visual

```text
Facultad
├── Grupo A
│   ├── Aula 1
│   └── Aula 2
└── Grupo B
    └── Laboratorio 1
```

---

# 8. `frontend/builder_properties_panel.py`

Archivo con el panel derecho del Builder.

## Clase principal

```python
class BuilderPropertiesPanel(QFrame):
```

## Contiene

```python
QLabel título del nodo
QLabel tipo del nodo
QLabel uuid del nodo
QLineEdit nombre
QSlider tamaño
QSpinBox capacidad
QPushButton eliminar nodo
```

## Señales recomendadas

```python
name_changed = Signal(str)
size_changed = Signal(float)
capacity_changed = Signal(int)
delete_requested = Signal()
```

## Funciones principales

```python
show_node(node, valid_parents)
clear()
_emit_name_changed()
_emit_size_changed(value)
_emit_capacity_changed(value)
```

## Responsabilidades

- Mostrar las propiedades del nodo seleccionado.
- Permitir editar el nombre.
- Permitir modificar el tamaño visual del nodo.
- Permitir modificar la capacidad si el nodo es un espacio.
- Desactivar campos que no aplican según el tipo de nodo.

## Comportamiento por tipo de nodo

| Tipo de nodo | Nombre editable | Tamaño editable | Capacidad editable | Eliminable |
|---|---|---|---|---|
| Root | Sí | Sí | No | No |
| Group | Sí | Sí | No | Sí |
| Space | Sí | Sí | Sí | Sí |

---

# 9. `frontend/graph_view.py`

Archivo con la vista central del grafo.

## Clase principal

```python
class GraphView(QGraphicsView):
```

## Clase auxiliar

```python
class GraphScene(QGraphicsScene):
```

## Contiene

```python
QGraphicsScene
nodos visuales
aristas visuales
control de pan
control de zoom
selección
```

## Señales

```python
node_selected = Signal(str)
node_deselected = Signal()
node_double_clicked = Signal(str)
```

## Funciones principales

```python
render_graph(graph_data)
select_node_visual(node_uuid)
_on_selection_changed()

mousePressEvent(event)
mouseMoveEvent(event)
mouseReleaseEvent(event)
wheelEvent(event)

_calculate_standard_layout(nodes, edges)
```

## Responsabilidades

- Mostrar el grafo interactivo.
- Dibujar nodos y conexiones.
- Detectar selección de nodos.
- Permitir mover nodos con click izquierdo y arrastre.
- Permitir mover la cámara con botón central y arrastre.
- Permitir zoom con la rueda del ratón.
- Aplicar límites de zoom.
- Emitir señales hacia el controller.

## Controles actuales del grafo

| Acción | Interacción | Resultado |
|---|---|---|
| Seleccionar nodo | Click izquierdo sobre nodo | Nodo seleccionado |
| Mover nodo | Click izquierdo mantenido + arrastre | Nodo cambia de posición visual |
| Mover cámara | Botón central mantenido + arrastre | Se desplaza la vista |
| Zoom | Rueda del ratón | Acerca o aleja la vista |
| Deseleccionar | Click derecho | Limpia selección |
| Expandir/contraer grupo | Doble click izquierdo en grupo | Toggle del grupo |

---

# 10. `frontend/graph_items.py`

Archivo con los elementos visuales del grafo.

## Clases principales

```python
GraphEdgeItem
BaseGraphNodeItem
RootNodeItem
GroupNodeItem
SpaceNodeItem
```

## Función fábrica

```python
create_graph_node_item(node_uuid, name, node_type, size)
```

## Responsabilidades

- Definir cómo se dibujan los nodos.
- Definir cómo se dibujan las conexiones.
- Actualizar las aristas cuando se mueve un nodo.
- Dibujar el texto centrado dentro del nodo.
- Cambiar el borde cuando el nodo está seleccionado.

## Apariencia de los nodos

| Tipo backend | Tipo visual | Forma | Texto |
|---|---|---|---|
| Root | `RootNodeItem` | Rectángulo con esquinas normales | Centrado dentro |
| Group | `GroupNodeItem` | Círculo | Centrado dentro |
| Space | `SpaceNodeItem` | Rectángulo con esquinas redondeadas | Centrado dentro |

## Nota importante

Los nodos del Builder no deben representarse como puntos. Deben ser formas visibles, con tamaño editable y texto dentro.

---

# 11. `frontend/styles.py`

Archivo opcional para centralizar estilos.

## Contenido esperado

```python
MAIN_STYLE
LEFT_PANEL_STYLE
RIGHT_PANEL_STYLE
GRAPH_VIEW_STYLE
```

## Responsabilidades

- Centralizar colores.
- Centralizar estilos de botones, inputs, paneles y grafo.
- Evitar llenar cada clase con bloques largos de CSS de Qt.

---

# Flujo general al abrir el Builder

```text
Usuario pulsa Builder
↓
MenuPage.open_builder()
↓
QStackedWidget muestra BuilderPage
↓
BuilderController.load_builder()
↓
BuilderController.refresh_all()
↓
Faculty.get_root()
Faculty.get_visible_nodes()
Faculty.get_children(...)
↓
BuilderController._build_graph_data()
↓
BuilderPage.render_tree(root)
BuilderPage.render_graph(graph_data)
BuilderPage.clear_properties_panel()
```

---

# Flujo al seleccionar un nodo

```text
Usuario hace click izquierdo sobre nodo
↓
GraphView detecta selección
↓
GraphView emite node_selected(uuid)
↓
BuilderController.select_node(uuid)
↓
Faculty.find_node(uuid)
Faculty.get_valid_parents(uuid)
↓
BuilderPage.select_node_visual(uuid)
BuilderPage.show_node_properties(node, valid_parents)
↓
Se actualizan:
- grafo central
- árbol izquierdo
- panel derecho
```

---

# Flujo al modificar una propiedad

```text
Usuario cambia campo en panel derecho
↓
BuilderPropertiesPanel emite señal
↓
BuilderController recibe cambio
↓
BuilderController llama al backend
↓
Faculty actualiza el dato
↓
BuilderController.refresh_all()
↓
Se refresca árbol, grafo y panel derecho
```

---

# Tabla general de eventos del Builder

| Acción | Interacción | Frontend | Controller | Backend | Resultado |
|---|---|---|---|---|---|
| Entrar al Builder | Click en botón Builder | `MenuPage.open_builder()` | `load_builder()` | `get_root()`, `get_visible_nodes()` | Carga árbol y grafo |
| Seleccionar nodo | Click izquierdo | `GraphView.node_selected` | `select_node()` | `find_node()` | Resalta nodo y carga propiedades |
| Seleccionar desde árbol | Click en árbol | `BuilderTreePanel.node_selected` | `select_node()` | `find_node()` | Sincroniza árbol, grafo y panel derecho |
| Deseleccionar | Click derecho | `GraphView.node_deselected` | `clear_selection()` | — | Limpia selección |
| Mover nodo | Click izquierdo + arrastre | `QGraphicsItem` | — | — | Cambia posición visual temporal |
| Mover cámara | Botón central + arrastre | `GraphView.mouseMoveEvent()` | — | — | Desplaza vista |
| Zoom | Rueda del ratón | `GraphView.wheelEvent()` | — | — | Acerca o aleja vista |
| Expandir grupo | Doble click en grupo | `GraphView.node_double_clicked` | `toggle_group()` | `toggle_group_expanded()` | Muestra u oculta hijos |
| Crear grupo | Botón izquierdo | `create_group_requested` | `create_group()` | `create_group()` | Añade grupo |
| Crear espacio | Botón izquierdo | `create_space_requested` | `create_space()` | `create_space()` | Añade espacio |
| Renombrar nodo | Editar texto | `name_changed` | `rename_selected_node()` | `rename_node()` / `rename_faculty()` | Cambia nombre |
| Cambiar tamaño | Slider | `size_changed` | `update_selected_node_size()` | `update_node_size()` | Cambia tamaño visual |
| Cambiar capacidad | SpinBox | `capacity_changed` | `update_selected_space_capacity()` | `update_space_properties()` | Cambia capacidad del espacio |
| Eliminar nodo | Botón eliminar | `delete_requested` | `delete_selected_node()` | `delete_node()` | Borra nodo |
| Volver al menú | Tecla Esc | `BuilderPage` | — | — | Muestra `MenuPage` |

---

# Decisiones actuales de diseño

## Separación de responsabilidades

```text
Backend:
    datos y lógica del modelo

Controller:
    coordinación entre backend y frontend

Frontend:
    visualización e interacción del usuario
```

## Visualización del grafo

- Se usa `QGraphicsView` como cámara.
- Se usa `QGraphicsScene` como mapa.
- Los nodos viven en coordenadas de escena, no en coordenadas de pantalla.
- El tamaño del panel central no debería cambiar la posición real de los nodos.
- La posición de los nodos todavía no se guarda en backend.
- Por ahora, al refrescar, se usa una visualización estándar calculada automáticamente.

## Apariencia obligatoria de nodos

```text
Root:
    rectángulo con esquinas normales
    texto centrado dentro

Group:
    círculo
    texto centrado dentro

Space:
    rectángulo con esquinas redondeadas
    texto centrado dentro
```

---

# Pendientes futuros

- Corregir fallos concretos de visualización.
- Añadir guardado de posición de nodos si se decide persistir layouts personalizados.
- Mejorar el layout automático del grafo.
- Añadir menú contextual con click derecho.
- Añadir selector de padre válido en el panel derecho.
- Mejorar estilos visuales.
- Añadir confirmación antes de eliminar nodos.
- Separar presets de simulación de la definición de la facultad.
