# Simulador de enfermedades contagiosas en entornos académicos

Aplicación de escritorio desarrollada como Trabajo de Fin de Grado para construir
escenarios académicos personalizados, ejecutar simulaciones de propagación de
enfermedades contagiosas y analizar sus resultados desde una misma interfaz.

El sistema representa tanto la estructura física de una facultad como su
organización académica. Los agentes siguen los horarios definidos por el usuario,
se desplazan entre espacios y generan contactos de forma probabilística. A partir
de estas interacciones, el motor calcula la evolución de una enfermedad mediante
un modelo epidemiológico basado en estados SEIR.

La aplicación tiene una finalidad académica y exploratoria. Sus resultados permiten
comparar escenarios y estudiar patrones de exposición, pero no constituyen
predicciones epidemiológicas ni clínicas.

## Funcionalidades principales

- creación y gestión de diferentes facultades;
- construcción visual de la estructura física mediante grupos y espacios;
- configuración de aulas, laboratorios, pasillos y espacios comunes;
- definición de carreras, cursos, grupos académicos y horarios;
- configuración de capacidad, ventilación, asistencia y propiedades demográficas;
- simulación basada en agentes con estados susceptible, expuesto, infeccioso y
  recuperado;
- generación de contactos y contagios según el espacio, el horario y el tipo de
  actividad;
- ejecución de simulaciones individuales o lotes de varias ejecuciones;
- uso de semillas para reproducir simulaciones;
- almacenamiento automático de configuraciones, métricas y eventos;
- reproducción animada de simulaciones individuales;
- visualización de resultados globales, por espacio, grupo y día de la semana;
- análisis agregado de lotes mediante medias, distribuciones y bandas de
  variabilidad.

## Requisitos

- Python 3.10 o posterior;
- PySide6;
- un sistema de escritorio compatible con Qt 6.

El resto de dependencias utilizadas por el proyecto forman parte de la biblioteca
estándar de Python.

## Instalación

Clona el repositorio y accede a su directorio:

```bash
git clone https://github.com/Crisis3012/TFG-Aplicaci-n-interactiva-para-simulaci-n-de-enfermedades-contagiosas-en-entornos-acad-micos.git
cd TFG-Aplicaci-n-interactiva-para-simulaci-n-de-enfermedades-contagiosas-en-entornos-acad-micos
```

Crea un entorno virtual.

En Windows:

```powershell
py -m venv .venv
.venv\Scripts\activate
```

En Linux o macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Instala PySide6:

```bash
python -m pip install --upgrade pip
python -m pip install PySide6
```

## Ejecución

Ejecuta la aplicación desde la raíz del repositorio:

```bash
python main.py
```

La primera vez que se inicia, la aplicación crea la carpeta `Facultades` y un
escenario inicial si no encuentra ninguna facultad válida.

## Instrucciones de uso

### 1. Seleccionar o crear una facultad

Desde el menú principal se puede seleccionar una facultad existente, crear una
nueva o eliminarla. Cada facultad mantiene de forma independiente su estructura,
horarios y resultados.

### 2. Construir el escenario

El botón `Builder` abre el editor visual. El builder dispone de dos modos:

- `Space Builder`: permite crear grupos de espacios y espacios físicos, asignar
  tipos, capacidad, ventilación y horarios de apertura;
- `Agent Builder`: permite crear carreras, cursos y grupos académicos, definir su
  número de estudiantes, asistencia y horarios.

Los nodos pueden seleccionarse desde el árbol lateral o desde el grafo. Sus
propiedades se editan en el panel derecho. Tras completar los cambios, pulsa
`Guardar facultad`.

Para que una simulación represente correctamente el escenario, deben existir
espacios, cursos o grupos con estudiantes y horarios asociados a espacios válidos.

### 3. Ejecutar una simulación

Desde `Simular` se pueden configurar:

- nombre de la ejecución;
- enfermedad predefinida;
- duración en días;
- número y estado de los infectados iniciales;
- semilla aleatoria opcional;
- generación de una traza visual para una ejecución individual;
- ejecución por lotes, número de repeticiones y semilla del lote.

Al finalizar, la interfaz muestra un resumen y guarda los resultados
automáticamente. La traza animada solo está disponible para simulaciones
individuales.

### 4. Consultar los resultados

Desde `Visualizar` se puede seleccionar cualquiera de las ejecuciones guardadas.
La pantalla incluye, según el tipo de resultado:

- curva SEIR e infecciones acumuladas;
- contagios y riesgo relativo por espacio;
- grafo de la facultad coloreado según la métrica seleccionada;
- transmisión entre grupos académicos;
- análisis por día de la semana;
- distribuciones y resultados agregados de los lotes.

## Almacenamiento de datos

Cada facultad se guarda dentro de:

```text
Facultades/<nombre_facultad>/
|-- faculty_config.json
|-- nodes.csv
|-- schedules.csv
`-- simulation_results/
```

Las simulaciones individuales generan archivos JSON y CSV con la configuración,
el resumen, la serie temporal, la ocupación, los contagios y las métricas por
espacio y grupo. Cuando se solicita una animación, también se genera
`visual_trace.json`.

Los lotes incluyen un resumen agregado y una carpeta `runs` con los resultados de
cada ejecución:

```text
simulation_results/
`-- batch_<fecha>_<nombre>/
    |-- metadata.json
    |-- config.json
    |-- summary.json
    |-- batch_summary.csv
    `-- runs/
```

## Estructura del proyecto

```text
backend/
|-- faculty.py
|-- faculty_project_manager.py
`-- simulation/          # Motor, agentes, contactos y persistencia
controller/              # Coordinación entre la interfaz y el backend
frontend/                # Interfaz gráfica, builder y visualizaciones
Facultades/               # Escenarios y resultados locales
main.py                   # Punto de entrada de la aplicación
```

## Consideraciones sobre el modelo

El modelo utiliza franjas temporales configurables y representa la progresión de
la enfermedad mediante estados SEIR. Los contactos, la asistencia y la transmisión
incluyen componentes aleatorios, por lo que dos ejecuciones pueden producir
resultados diferentes. Las semillas permiten repetir una ejecución o generar un
lote reproducible.

Los parámetros de las enfermedades incluidas son configuraciones de trabajo y no
han sido calibrados para realizar predicciones sobre brotes reales. El alcance
actual se centra en la transmisión dentro de la facultad y no modela de forma
continua los contactos externos.

## Tecnologías

- Python;
- PySide6 y Qt 6;
- JSON para configuraciones y metadatos;
- CSV para horarios, series temporales y resultados agregados.

## Autor

Cristian Rey Márquez.

Trabajo de Fin de Grado de la Escola d'Enginyeria de la Universitat Autónoma de
Barcelona.
