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