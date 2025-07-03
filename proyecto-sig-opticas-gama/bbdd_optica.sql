-- 1. Crear la base de datos si no existe y seleccionarla
CREATE DATABASE IF NOT EXISTS bbdd_optica;
USE bbdd_optica;

-- 2. Desactivar temporalmente la revisión de llaves foráneas para poder borrar las tablas sin problemas de orden
SET FOREIGN_KEY_CHECKS=0;

-- 3. Borrar todas las tablas si ya existen para empezar de cero
DROP TABLE IF EXISTS Clientes;
DROP TABLE IF EXISTS Compras;
DROP TABLE IF EXISTS DetalleCompra;
DROP TABLE IF EXISTS DetalleOrden;
DROP TABLE IF EXISTS Examenes;
DROP TABLE IF EXISTS Ordenes;
DROP TABLE IF EXISTS Productos;
DROP TABLE IF EXISTS Proveedores;

-- 4. Reactivar la revisión de llaves foráneas
SET FOREIGN_KEY_CHECKS=1;

-- 5. Crear todas las tablas con la estructura final y correcta

CREATE TABLE Clientes (
    id_cliente INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    rut VARCHAR(15) NOT NULL UNIQUE,
    telefono VARCHAR(20),
    correo VARCHAR(100),
    direccion VARCHAR(255)
);

CREATE TABLE Proveedores (
    id_proveedor INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    contacto VARCHAR(100),
    telefono VARCHAR(20),
    direccion VARCHAR(255)
);

CREATE TABLE Productos (
    id_producto INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    tipo VARCHAR(50) NOT NULL,
    marca VARCHAR(100),
    stock INT NOT NULL,
    precio_compra INT NOT NULL,  -- CAMBIADO A INT
    precio_venta INT NOT NULL   -- CAMBIADO A INT
);

CREATE TABLE Ordenes (
    id_orden INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    fecha DATE NOT NULL,
    total INT,  -- CAMBIADO A INT
    vendedor VARCHAR(100),
    estado ENUM('Pendiente', 'Pagada', 'Entregada') DEFAULT 'Pendiente',
    FOREIGN KEY (id_cliente) REFERENCES Clientes(id_cliente)
);

CREATE TABLE DetalleOrden (
    id_detalle INT AUTO_INCREMENT PRIMARY KEY,
    id_orden INT NOT NULL,
    id_producto INT NOT NULL,
    cantidad INT NOT NULL,
    precio INT NOT NULL,  -- CAMBIADO A INT
    FOREIGN KEY (id_orden) REFERENCES Ordenes(id_orden) ON DELETE CASCADE,
    FOREIGN KEY (id_producto) REFERENCES Productos(id_producto)
);

CREATE TABLE Compras (
    id_compra INT AUTO_INCREMENT PRIMARY KEY,
    id_proveedor INT NOT NULL,
    fecha DATE NOT NULL,
    total INT,  -- CAMBIADO A INT
    FOREIGN KEY (id_proveedor) REFERENCES Proveedores(id_proveedor)
);

CREATE TABLE DetalleCompra (
    id_detalle INT AUTO_INCREMENT PRIMARY KEY,
    id_compra INT NOT NULL,
    id_producto INT NOT NULL,
    cantidad INT NOT NULL,
    precio_unitario INT NOT NULL,  -- CAMBIADO A INT
    FOREIGN KEY (id_compra) REFERENCES Compras(id_compra) ON DELETE CASCADE,
    FOREIGN KEY (id_producto) REFERENCES Productos(id_producto)
);

CREATE TABLE Examenes (
    id_examen INT AUTO_INCREMENT PRIMARY KEY,
    id_cliente INT NOT NULL,
    fecha DATE NOT NULL,
    diagnostico TEXT,
    receta TEXT,
    observaciones TEXT,
    FOREIGN KEY (id_cliente) REFERENCES Clientes(id_cliente)
);
