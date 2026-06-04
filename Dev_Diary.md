- Versión 0.0.1:
    Primera versión preeliminar con pequeños sistemas de UI, una ventana funcional e interactividad mínima. En esta versión se ha empezado a aprender a usar las funciones básicas de la librería Qt de Python.

- Versión 0.0.2:
    Se han añadido las primeras clases de datos que actuarán como nodos y la clase facultad que se encargará de interactuar con el entorno visual para modificar la estructura interna del escenario. Se ha acordado que se identificara a los nodos con códigos UUID y que estos se cargarán y guardarán en un archivo CSV. También se ha creado un primer entorno de pruebas para probar el backend inicial sin empezar una facultad desde 0 y sin necesidad de uso del UI.

- Versión 0.0.3:
    Se han incorporado las funciones de movimiento, renombramiento y eliminación de nodos y se ha creado una interfaz por consola que permite comprobar el correcto funcionamiento de todas las funciones de backend añadidas hasta el momento. También se ha termiando de añadir las funciones de backend bases previstas y se deja preparado el entorno para empezar a ligar las llamadas de la UI con la API del backend. Nota: después de la adición de las últimas funciones por el momento, parece necesario un reordenamiento de la estructura de la clase Facultad (API), con el objetivo de que en un futuro sea más fácil encontrar las funciones creadas en caso de que necesiten cambios o actualizaciones

- Versión 0.04:
    Cambio mínimo en el funcionamiento de la UI actual. Ahora la camara de la visión de la facultad se mueve usando el botón central del ratón en vez del izquierdo para evitar errores al clickar sobre objetos movibles.

- Versión 0.0.5:
    Se han realizado grandes cambios al codigo. Primero de todo se ha formalizado la estructura de los módulos por carpetas con el objetivo de organizar mejor las llamadas, dependencias y estructura general de los archivos de la aplicación. Se ha escrito una documentación detallada sobre las funciones actuales de la aplicación. Se ha creado todo el apartado de frontend inicial de la aplicación y se a conectado al backend a través de una clase controladora que hace de contacto entre los eventos del frontend y las llamadas al backend. Ya se tiene una primera versión semifuncional del Builder a la que le hace falta mucho debugging, adición de funciones y pulimiento de la interfaz.

- Versión 0.0.6:
    Se ha mejorado la UI haciendo que los nodos se vean con las formas correctas, que sus posiciones no se reinicien cada vez que se redibuja el grafo al hacer una acción (expandir/contraer un grupo, eliminar un nodo, crear un nodo, etc.) y se ha cambiado la eliminación de nodos para que sus posiciones no se queden guardadas en memoria y la vayan sobrecargando de información que ya no es útil

- Versión 0.0.7:
    Se ha terminado el Space Builder con los parámetros acordados (opcionales y obligatorios), además de con el panel izquierdo funcional. Tambien funcionan ya todas las funciones de modificacion de parámetros y modificación de la visualización. Queda incorporar el Agent Builder para las carreras y horarios y entonces podemos empezar con la simulación.

- Versión 0.0.8: 
    Casi terminado el builder, queda arreglar la introducción de los horarios que se ha roto y luego hacer fine tunning y debugging. En general lo que se ha hecho es añadir un botón en el builder que cambia la vista entre el builder de espacios y el builder de carreras. En el builder de espacios se ha arreglado el panel derecho e izquierdo (aunque en el izquierdo habría que modificar el color del fondo o del texto) y ya quedan todas las funcionalidades teóricamente terminadas. En el bilder de carreras todo funciona correctamente menos los horarios. Cuando se arregle esto y tengamos el builder totalmente funcional pasamos a la version 0.1.0 y empezamos a trabajar en la simulación.

- Versión 0.1.0:
    Builder funcional terminado. Ahora ya funcionan las funcionalidades añadidas en la última versión y se han añadido un método de guardado, selección y creado de facultades nuevas. Con esto cerramos las funcionalidades de la primera parte del programa y tenemos una base cerrada y totalmente funcional para empezar con la parte de la simulación.

- Versión 0.1.1:
    Se ha terminado prácticamente la simulación. Simplemente se han seguido los acuerdos establecidos y se ha enlazado con la UI de manera muy básica. Como posibles mejoras quedan revisiones de algunas tablas internas y de los calculos efectuados con ellas, así como la introducción de redes sociales funcionales dentro de los alumnos de la facultad. Para terminar con la versión 0.1.x solo queda pulir la pantalla de simulación con parámetros introducibles que tengan más sentido y luego hacer la simulación visual. 

- Versión 0.1.2:
    Remodulación del layout de los nodos para construir escenarios con más claridad, también se ha añadido un botón de reordenación para cambiar el layout completo de los nodos a mitad de la sesión. Tambien se ha cambiado el color de las letras del tree panel para mayor legibilidad.

- Versión 0.1.3:
    Solo se ha arreglado el botón de salir de la app, ahora siq ue cierra la ventana.