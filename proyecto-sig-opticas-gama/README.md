# \# Sistema de Gestión para Óptica - Proyecto ICN292

# 

# Este proyecto es un Sistema de Información para la Gestión (SIG) desarrollado en Python con PySide6. Permite administrar las operaciones clave de una óptica, incluyendo la gestión de clientes, productos, ventas, compras, recetas y reportes.

# 

# \## 1. Prerrequisitos

# 

# Para ejecutar esta aplicación, es necesario tener instalado lo siguiente:

# 

# \* \*\*Python 3.8 o superior.\*\*

# \* \*\*Un servidor de base de datos MySQL\*\* (o un sistema compatible como MariaDB).

# \* Las siguientes librerías de Python:

# 

# Puedes instalar todas las librerías necesarias ejecutando el siguiente comando en tu terminal:

# 

# ```bash

# pip install PySide6 mysql-connector-python

# ```

# 

# \## 2. Instalación y Configuración

# 

# Sigue estos pasos para poner en marcha la aplicación:

# 

# \### Paso 1: Configurar la Base de Datos

# 

# 1\.  Abre tu gestor de base de datos (por ejemplo, MySQL Workbench).

# 2\.  Ejecuta el script SQL incluido en este repositorio: `bbdd\_optica.sql`.

# 3\.  Esto creará la base de datos `bbdd\_optica` y todas las tablas necesarias con la estructura correcta.

# 

# \### Paso 2: Ejecutar la Aplicación

# 

# 1\.  Asegúrate de tener todas las librerías de los prerrequisitos instaladas.

# 2\.  Navega a la carpeta del proyecto en tu terminal.

# 3\.  Ejecuta el script principal con el siguiente comando:

# 

# &nbsp;   ```bash

# &nbsp;   python Proyecto.py

# &nbsp;   ```

# 

# \### Paso 3: Iniciar Sesión

# 

# 1\.  Al ejecutar el programa, aparecerá una ventana de inicio de sesión.

# 2\.  Ingresa las credenciales de tu servidor MySQL. Por defecto:

# &nbsp;   \* \*\*Host:\*\* `localhost`

# &nbsp;   \* \*\*Usuario:\*\* `root`

# &nbsp;   \* \*\*Contraseña:\*\* La contraseña que configuraste para tu usuario `root` de MySQL.

# 3\.  Haz clic en "Conectar" para acceder al menú principal de la aplicación.

# 

# \## 3. Funcionalidades Principales

# 

# El sistema cuenta con los siguientes módulos accesibles desde el menú principal:

# 

# \* \*\*Gestionar Clientes, Productos, Proveedores y Recetas:\*\* Módulos CRUD completos para añadir, ver, editar y eliminar registros.

# \* \*\*Registrar Venta y Compra:\*\* Interfaces dinámicas para registrar transacciones, con búsqueda de productos y actualización automática de stock.

# \* \*\*Historial de Transacciones:\*\* Visor de ventas y compras pasadas con filtro por fecha.

# \* \*\*Reporte Mensual de Ventas:\*\* Herramienta para visualizar las ventas de un mes y año específicos, con la opción de filtrar por vendedor y ver el total de ingresos.

# 



