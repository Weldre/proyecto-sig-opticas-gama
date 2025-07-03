# optica_manager_v7.py

import sys
import json
import datetime
import mysql.connector
from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton, QVBoxLayout, QHBoxLayout,
    QMessageBox, QMainWindow, QDialog, QGridLayout, QSpinBox,
    QDateEdit, QComboBox, QTabWidget, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QTextEdit, QDialogButtonBox, QGroupBox
)
from PySide6.QtCore import QDate, Qt, Signal, QTimer

def is_valid_rut(rut: str) -> bool:
    """Valida el formato de un RUT chileno (sin puntos y con guion)."""
    import re
    return re.match(r'^\d{7,8}-[\dkK]$', rut.strip())

class CustomSpinBox(QSpinBox):
    """
    Un QSpinBox personalizado que selecciona todo su contenido cuando
    el usuario hace clic en él, para una edición más rápida.
    """
    def focusInEvent(self, event):
        super().focusInEvent(event)
        QTimer.singleShot(0, self.selectAll)

class Database:
    """
    Gestiona todas las interacciones con la base de datos MySQL para la óptica.
    """
    def __init__(self):
        self.connection = None

    def connect(self, user, password, host="localhost", db_name="bbdd_optica"):
        try:
            self.connection = mysql.connector.connect(host=host, user=user, password=password, database=db_name)
            return True
        except mysql.connector.Error as err:
            QMessageBox.critical(None, "Error de Conexión", f"No se pudo conectar.\nError: {err}"); return False

    def _execute_query(self, query, params=None, fetch=None):
        if not self.connection or not self.connection.is_connected(): return None
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(query, params or ()); is_transactional = any(cmd in query.strip().upper() for cmd in ["INSERT", "UPDATE", "DELETE"])
            if is_transactional: self.connection.commit(); return cursor.lastrowid if "INSERT" in query.strip().upper() else cursor.rowcount
            if fetch: return cursor.fetchall() if fetch == 'all' else cursor.fetchone()
            return None
        except mysql.connector.Error as err:
            QMessageBox.critical(None, "Error de Base de Datos", f"No se pudo ejecutar la operación.\n\nError: {err}"); self.connection.rollback(); return None
        finally: cursor.close()

    def _generic_delete(self, table_name, id_col, item_id, success_msg="Registro eliminado."):
        query = f"DELETE FROM {table_name} WHERE {id_col} = %s"
        try:
            rows_affected = self._execute_query(query, (item_id,))
            if rows_affected > 0: return {"success": True, "message": success_msg}
            else: return {"success": False, "message": "No se encontró el registro para eliminar."}
        except Exception as e: return {"success": False, "message": f"No se puede eliminar.\nError: {e}"}

    def get_clients(self, search_term: str = "") -> list:
        query = "SELECT id_cliente, nombre, apellido, rut, telefono, correo, direccion FROM Clientes"
        if search_term: query += " WHERE nombre LIKE %s OR apellido LIKE %s OR rut LIKE %s"
        return self._execute_query(query, (f"%{search_term}%",)*3 if search_term else None, fetch='all')

    def add_client(self, data: dict):
        if self._execute_query("SELECT 1 FROM Clientes WHERE rut = %s", (data['rut'],), fetch='one'):
            QMessageBox.warning(None, "RUT Duplicado", f"El RUT '{data['rut']}' ya está registrado."); return None
        return self._execute_query("INSERT INTO Clientes (nombre, apellido, rut, telefono, correo, direccion) VALUES (%s, %s, %s, %s, %s, %s)", tuple(data.values()))
    
    def update_client(self, client_id: int, data: dict):
        if self._execute_query("SELECT id_cliente FROM Clientes WHERE rut = %s AND id_cliente != %s", (data['rut'], client_id), fetch='one'):
            QMessageBox.warning(None, "RUT Duplicado", f"El RUT '{data['rut']}' ya pertenece a otro cliente."); return None
        return self._execute_query("UPDATE Clientes SET nombre=%s, apellido=%s, rut=%s, telefono=%s, correo=%s, direccion=%s WHERE id_cliente=%s", tuple(data.values()) + (client_id,))
    
    def delete_client(self, client_id: int):
        if self._execute_query("SELECT 1 FROM Examenes WHERE id_cliente = %s", (client_id,), fetch='one'): return {"success": False, "message": "No se puede eliminar. El cliente tiene recetas médicas asociadas."}
        if self._execute_query("SELECT 1 FROM Ordenes WHERE id_cliente = %s", (client_id,), fetch='one'): return {"success": False, "message": "No se puede eliminar. El cliente tiene ventas asociadas."}
        return self._generic_delete("Clientes", "id_cliente", client_id)

    def get_products(self, search_term: str = "") -> list:
        query = "SELECT id_producto, nombre, tipo, marca, stock, precio_compra, precio_venta FROM Productos"
        if search_term: query += " WHERE nombre LIKE %s OR tipo LIKE %s OR marca LIKE %s"
        return self._execute_query(query, (f"%{search_term}%",)*3 if search_term else None, fetch='all')

    def add_product(self, data: dict):
        return self._execute_query("INSERT INTO Productos (nombre, tipo, marca, stock, precio_compra, precio_venta) VALUES (%s, %s, %s, %s, %s, %s)", tuple(data.values()))

    def update_product(self, product_id: int, data: dict):
        return self._execute_query("UPDATE Productos SET nombre=%s, tipo=%s, marca=%s, stock=%s, precio_compra=%s, precio_venta=%s WHERE id_producto=%s", tuple(data.values()) + (product_id,))

    def delete_product(self, product_id: int):
        if self._execute_query("SELECT 1 FROM DetalleOrden WHERE id_producto = %s", (product_id,), fetch='one'): return {"success": False, "message": "No se puede eliminar. El producto está incluido en ventas registradas."}
        if self._execute_query("SELECT 1 FROM DetalleCompra WHERE id_producto = %s", (product_id,), fetch='one'): return {"success": False, "message": "No se puede eliminar. El producto está incluido en compras registradas."}
        return self._generic_delete("Productos", "id_producto", product_id)

    def get_suppliers(self, search_term: str = "") -> list:
        query = "SELECT id_proveedor, nombre, contacto, telefono, direccion FROM Proveedores"
        if search_term: query += " WHERE nombre LIKE %s OR contacto LIKE %s"
        return self._execute_query(query, (f"%{search_term}%",)*2 if search_term else None, fetch='all')
        
    def add_supplier(self, data: dict): return self._execute_query("INSERT INTO Proveedores (nombre, contacto, telefono, direccion) VALUES (%s, %s, %s, %s)", tuple(data.values()))
    def update_supplier(self, supplier_id: int, data: dict): return self._execute_query("UPDATE Proveedores SET nombre=%s, contacto=%s, telefono=%s, direccion=%s WHERE id_proveedor=%s", tuple(data.values()) + (supplier_id,))
    def delete_supplier(self, supplier_id: int):
        if self._execute_query("SELECT 1 FROM Compras WHERE id_proveedor = %s", (supplier_id,), fetch='one'): return {"success": False, "message": "No se puede eliminar. El proveedor tiene compras asociadas."}
        return self._generic_delete("Proveedores", "id_proveedor", supplier_id)

    def get_exams_for_client(self, client_id: int) -> list: return self._execute_query("SELECT id_examen, fecha, diagnostico, observaciones FROM Examenes WHERE id_cliente = %s ORDER BY fecha DESC", (client_id,), fetch='all')
    def get_exam_details(self, exam_id: int) -> dict: return self._execute_query("SELECT * FROM Examenes WHERE id_examen = %s", (exam_id,), fetch='one')
    def add_exam(self, data: dict): return self._execute_query("INSERT INTO Examenes (id_cliente, fecha, diagnostico, receta, observaciones) VALUES (%s, %s, %s, %s, %s)", tuple(data.values()))
    def update_exam(self, exam_id: int, data: dict): return self._execute_query("UPDATE Examenes SET id_cliente=%s, fecha=%s, diagnostico=%s, receta=%s, observaciones=%s WHERE id_examen=%s", tuple(data.values()) + (exam_id,))
    def delete_exam(self, exam_id: int): return self._generic_delete("Examenes", "id_examen", exam_id, "Receta eliminada.")

    def create_sale(self, client_id: int, total: int, vendedor: str, details: list):
        if not self.connection or not self.connection.is_connected(): return None
        cursor = self.connection.cursor()
        try:
            query = "INSERT INTO Ordenes (id_cliente, fecha, total, vendedor, estado) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(query, (client_id, datetime.datetime.now().date(), total, vendedor, 'Pagada'))
            order_id = cursor.lastrowid
            for detail in details:
                cursor.execute("INSERT INTO DetalleOrden (id_orden, id_producto, cantidad, precio) VALUES (%s, %s, %s, %s)", (order_id, detail['id_producto'], detail['cantidad'], detail['precio_venta']))
                cursor.execute("UPDATE Productos SET stock = stock - %s WHERE id_producto = %s", (detail['cantidad'], detail['id_producto']))
            self.connection.commit(); return order_id
        except mysql.connector.Error as err:
            self.connection.rollback(); QMessageBox.critical(None, "Error en Venta", f"No se pudo completar la transacción.\n{err}"); return None
        finally: cursor.close()
    
    def create_purchase(self, supplier_id: int, total: int, details: list):
        if not self.connection or not self.connection.is_connected(): return None
        cursor = self.connection.cursor()
        try:
            query = "INSERT INTO Compras (id_proveedor, fecha, total) VALUES (%s, %s, %s)"
            cursor.execute(query, (supplier_id, datetime.datetime.now().date(), total))
            purchase_id = cursor.lastrowid
            for detail in details:
                cursor.execute("INSERT INTO DetalleCompra (id_compra, id_producto, cantidad, precio_unitario) VALUES (%s, %s, %s, %s)", (purchase_id, detail['id_producto'], detail['cantidad'], detail['precio_compra']))
                cursor.execute("UPDATE Productos SET stock = stock + %s WHERE id_producto = %s", (detail['cantidad'], detail['id_producto']))
            self.connection.commit(); return purchase_id
        except mysql.connector.Error as err:
            self.connection.rollback(); QMessageBox.critical(None, "Error en Compra", f"No se pudo completar la transacción.\n{err}"); return None
        finally: cursor.close()

    def get_transactions_by_date(self, type: str, start_date, end_date) -> list:
        if type == 'Venta': query = "SELECT o.id_orden, o.fecha, c.nombre, c.apellido, o.vendedor, o.total FROM Ordenes o JOIN Clientes c ON o.id_cliente = c.id_cliente WHERE o.fecha BETWEEN %s AND %s ORDER BY o.fecha DESC"
        else: query = "SELECT c.id_compra, c.fecha, p.nombre, c.total FROM Compras c JOIN Proveedores p ON c.id_proveedor = p.id_proveedor WHERE c.fecha BETWEEN %s AND %s ORDER BY c.fecha DESC"
        return self._execute_query(query, (start_date, end_date), fetch='all')

    def delete_transaction(self, type: str, transaction_id: int):
        if not self.connection or not self.connection.is_connected(): return {"success": False, "message": "Sin conexión."}
        cursor = self.connection.cursor(dictionary=True)
        detail_table, main_table, id_col_main, stock_op = ("DetalleOrden", "Ordenes", "id_orden", "+") if type == 'Venta' else ("DetalleCompra", "Compras", "id_compra", "-")
        try:
            cursor.execute(f"SELECT id_producto, cantidad FROM {detail_table} WHERE {id_col_main} = %s", (transaction_id,)); details_to_revert = cursor.fetchall()
            for detail in details_to_revert: cursor.execute(f"UPDATE Productos SET stock = stock {stock_op} %s WHERE id_producto = %s", (detail['cantidad'], detail['id_producto']))
            cursor.execute(f"DELETE FROM {detail_table} WHERE {id_col_main} = %s", (transaction_id,)); cursor.execute(f"DELETE FROM {main_table} WHERE {id_col_main} = %s", (transaction_id,))
            self.connection.commit(); return {"success": True}
        except mysql.connector.Error as err:
            self.connection.rollback(); return {"success": False, "message": f"No se pudo eliminar la transacción.\n{err}"}
        finally: cursor.close()

    def get_unique_sellers(self) -> list:
        query = "SELECT DISTINCT vendedor FROM Ordenes WHERE vendedor IS NOT NULL AND vendedor != '' ORDER BY vendedor"
        return self._execute_query(query, fetch='all')

    def get_sales_by_month(self, year: int, month: int, vendedor: str = None) -> list:
        query = "SELECT fecha, id_orden, vendedor, total FROM Ordenes WHERE YEAR(fecha) = %s AND MONTH(fecha) = %s"
        params = [year, month]
        if vendedor:
            query += " AND vendedor = %s"
            params.append(vendedor)
        query += " ORDER BY fecha ASC"
        return self._execute_query(query, params, fetch='all')
        
    def close(self):
        if self.connection and self.connection.is_connected(): self.connection.close()

class LoginWindow(QDialog):
    def __init__(self, db_instance):
        super().__init__(); self.db = db_instance; self.setWindowTitle("Conexión a la Base de Datos"); self.setModal(True)
        layout = QGridLayout(self); self.host_input = QLineEdit("localhost"); self.user_input = QLineEdit("root"); self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText("Contraseña"); self.pass_input.setEchoMode(QLineEdit.Password); connect_btn = QPushButton("Conectar")
        connect_btn.clicked.connect(self.try_connect); layout.addWidget(QLabel("Host:"), 0, 0); layout.addWidget(self.host_input, 0, 1)
        layout.addWidget(QLabel("Usuario:"), 1, 0); layout.addWidget(self.user_input, 1, 1); layout.addWidget(QLabel("Contraseña:"), 2, 0)
        layout.addWidget(self.pass_input, 2, 1); layout.addWidget(connect_btn, 3, 1)
    def try_connect(self):
        if self.db.connect(user=self.user_input.text(), password=self.pass_input.text(), host=self.host_input.text()): self.accept()

def populate_table(table: QTableWidget, data: list, hidden_id_col=True):
    table.clear(); table.setRowCount(0); table.setColumnCount(0)
    if not data: return
    headers = list(data[0].keys()); table.setColumnCount(len(headers)); table.setHorizontalHeaderLabels([h.replace('_',' ').title() for h in headers]); table.setRowCount(len(data))
    for r, row_data in enumerate(data):
        for c, h in enumerate(headers):
            value = row_data[h]; item = QTableWidgetItem()
            if isinstance(value, datetime.date): value = value.strftime('%Y-%m-%d')
            item.setData(Qt.DisplayRole, str(value) if value is not None else ""); 
            if h.startswith('id_'): item.setData(Qt.UserRole, value)
            table.setItem(r, c, item)
    table.resizeColumnsToContents(); table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    if hidden_id_col and headers and headers[0].startswith('id_'): table.hideColumn(0)

class GenericManagerWidget(QWidget):
    def __init__(self, db, entity_name, fields, get_method, add_method, update_method, delete_method, parent=None):
        super().__init__(parent); self.db, self.entity_name, self.fields = db, entity_name, fields
        self.get_method, self.add_method, self.update_method, self.delete_method = get_method, add_method, update_method, delete_method
        self.setWindowTitle(f"Gestionar {self.entity_name}"); self.setMinimumSize(800, 600)
        main_layout = QVBoxLayout(self); action_layout = QHBoxLayout()
        self.search_input = QLineEdit(); self.search_input.setPlaceholderText(f"Buscar..."); self.search_input.textChanged.connect(self.load_data)
        add_btn, self.edit_btn, self.delete_btn = QPushButton("➕ Agregar"), QPushButton("✏️ Editar"), QPushButton("🗑️ Eliminar")
        add_btn.clicked.connect(self.add_item); self.edit_btn.clicked.connect(self.edit_item); self.delete_btn.clicked.connect(self.delete_item)
        action_layout.addWidget(self.search_input); action_layout.addWidget(add_btn); action_layout.addWidget(self.edit_btn); action_layout.addWidget(self.delete_btn)
        self.table = QTableWidget(); self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self.update_button_state); main_layout.addLayout(action_layout); main_layout.addWidget(self.table)
        self.load_data(); self.update_button_state()
    def load_data(self): populate_table(self.table, getattr(self.db, self.get_method)(self.search_input.text())); self.update_button_state()
    def update_button_state(self): has_selection = bool(self.table.selectedItems()); self.edit_btn.setEnabled(has_selection); self.delete_btn.setEnabled(has_selection)
    def get_selected_id(self):
        selected_rows = self.table.selectionModel().selectedRows()
        if not selected_rows: return None, None
        return self.table.item(selected_rows[0].row(), 0).data(Qt.UserRole), selected_rows[0].row()
    def add_item(self):
        dialog = GenericEditDialog(self.entity_name, self.fields); 
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.validate_and_get_data()
            if new_data and getattr(self.db, self.add_method)(new_data): self.load_data()
    def edit_item(self):
        item_id, row_index = self.get_selected_id()
        if item_id is None: return
        current_data = {self.table.horizontalHeaderItem(i).text().lower().replace(' ', '_'): self.table.item(row_index, i).data(Qt.DisplayRole) for i in range(self.table.columnCount())}
        dialog = GenericEditDialog(self.entity_name, self.fields, current_data)
        if dialog.exec() == QDialog.Accepted:
            new_data = dialog.validate_and_get_data()
            if new_data and getattr(self.db, self.update_method)(item_id, new_data): self.load_data()
    def delete_item(self):
        item_id, _ = self.get_selected_id()
        if item_id is None: return
        if QMessageBox.question(self, "Confirmar", f"¿Seguro que quieres eliminar?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            result = getattr(self.db, self.delete_method)(item_id)
            if result['success']: QMessageBox.information(self, "Éxito", result['message']); self.load_data()
            else: QMessageBox.warning(self, "Error", result['message'])

class GenericEditDialog(QDialog):
    def __init__(self, entity_name, fields, current_data=None, parent=None):
        super().__init__(parent); self.setWindowTitle(f"{'Editar' if current_data else 'Agregar'} {entity_name}"); self.fields = fields; self.inputs = {}
        layout = QGridLayout(self)
        for i, (fname, ftype) in enumerate(fields.items()):
            label_text = "RUT (sin puntos y con guion):" if fname == 'rut' else fname.replace('_', ' ').title() + ":"
            label, widget = QLabel(label_text), None
            if ftype == str: widget = QLineEdit()
            elif ftype == int:
                widget = CustomSpinBox(); widget.setRange(0, 99999999)
                if 'precio' in fname: widget.setPrefix("$ ")
                else: widget.setPrefix("")
            if current_data:
                value = current_data.get(fname, ''); 
                if ftype == str: widget.setText(str(value))
                else:
                    try: widget.setValue(int(float(value)) if value is not None and str(value).strip() != '' else 0)
                    except (ValueError, TypeError): widget.setValue(0)
            layout.addWidget(label, i, 0); layout.addWidget(widget, i, 1); self.inputs[fname] = widget
        buttons = QDialogButtonBox(QDialogButtonBox.Save|QDialogButtonBox.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject); layout.addWidget(buttons, len(fields), 1)
    def validate_and_get_data(self):
        data = {}
        for name, widget in self.inputs.items():
            value = widget.text() if isinstance(widget, QLineEdit) else widget.value()
            if isinstance(widget, QLineEdit) and not value.strip():
                QMessageBox.warning(self, "Campo Vacío", f"El campo '{name.replace('_', ' ').title()}' no puede estar vacío."); return None
            if name == 'rut' and not is_valid_rut(value):
                QMessageBox.warning(self, "Formato Incorrecto", f"El RUT '{value}' no es válido.\nUse el formato: 12345678-9"); return None
            data[name] = value.strip() if isinstance(value, str) else value
        return data

class RecipeManagerWidget(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent); self.db = db; self.current_client_id = None
        self.setWindowTitle("Gestionar Recetas Médicas"); self.setMinimumSize(900, 700); main_layout = QVBoxLayout(self)
        search_layout = QHBoxLayout(); self.search_input = QLineEdit(); self.search_input.setPlaceholderText("Buscar cliente por nombre o RUT...")
        self.search_input.textChanged.connect(self.search_clients); search_layout.addWidget(QLabel("Buscar Cliente:")); search_layout.addWidget(self.search_input)
        self.clients_table = QTableWidget(); self.clients_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.clients_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.clients_table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.clients_table.itemSelectionChanged.connect(self.load_client_recipes)
        self.recipes_table = QTableWidget(); self.recipes_table.setEditTriggers(QAbstractItemView.NoEditTriggers); self.recipes_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.recipes_table.setSelectionMode(QAbstractItemView.SingleSelection); self.recipes_table.itemSelectionChanged.connect(self.update_button_state)
        action_layout = QHBoxLayout(); self.add_btn = QPushButton("➕ Agregar Receta"); self.edit_btn = QPushButton("✏️ Ver/Editar Receta"); self.delete_btn = QPushButton("🗑️ Eliminar Receta")
        self.add_btn.clicked.connect(self.add_recipe); self.edit_btn.clicked.connect(self.edit_recipe); self.delete_btn.clicked.connect(self.delete_recipe)
        action_layout.addStretch(); action_layout.addWidget(self.add_btn); action_layout.addWidget(self.edit_btn); action_layout.addWidget(self.delete_btn)
        main_layout.addLayout(search_layout); main_layout.addWidget(QLabel("Resultados de Búsqueda de Clientes:")); main_layout.addWidget(self.clients_table)
        main_layout.addWidget(QLabel("Recetas del Cliente Seleccionado:")); main_layout.addWidget(self.recipes_table); main_layout.addLayout(action_layout)
        self.update_button_state()
    def search_clients(self):
        search_term = self.search_input.text()
        if len(search_term) > 1: populate_table(self.clients_table, self.db.get_clients(search_term))
        else: self.clients_table.setRowCount(0)
    def load_client_recipes(self):
        selected_rows = self.clients_table.selectionModel().selectedRows()
        if not selected_rows: self.current_client_id = None; self.recipes_table.setRowCount(0); self.update_button_state(); return
        self.current_client_id = self.clients_table.item(selected_rows[0].row(), 0).data(Qt.UserRole)
        if self.current_client_id: populate_table(self.recipes_table, self.db.get_exams_for_client(self.current_client_id))
        else: self.recipes_table.setRowCount(0)
        self.update_button_state()
    def update_button_state(self):
        client_selected = self.current_client_id is not None; recipe_selected = bool(self.recipes_table.selectedItems())
        self.add_btn.setEnabled(client_selected); self.edit_btn.setEnabled(client_selected and recipe_selected); self.delete_btn.setEnabled(client_selected and recipe_selected)
    def get_selected_recipe_id(self): return self.recipes_table.item(self.recipes_table.selectionModel().selectedRows()[0].row(), 0).data(Qt.UserRole) if self.recipes_table.selectionModel().selectedRows() else None
    def add_recipe(self):
        dialog = RecipeDialog(self.db, self.current_client_id); 
        if dialog.exec() == QDialog.Accepted: self.load_client_recipes()
    def edit_recipe(self):
        recipe_id = self.get_selected_recipe_id()
        if recipe_id:
            dialog = RecipeDialog(self.db, self.current_client_id, recipe_id)
            if dialog.exec() == QDialog.Accepted: self.load_client_recipes()
    def delete_recipe(self):
        recipe_id = self.get_selected_recipe_id()
        if recipe_id and QMessageBox.question(self, "Confirmar", f"¿Seguro que quieres eliminar esta receta?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            result = self.db.delete_exam(recipe_id)
            if result['success']: QMessageBox.information(self, "Éxito", result['message']); self.load_client_recipes()
            else: QMessageBox.warning(self, "Error", result['message'])

class RecipeDialog(QDialog):
    def __init__(self, db, client_id, exam_id=None, parent=None):
        super().__init__(parent); self.db = db; self.client_id = client_id; self.exam_id = exam_id; self.is_edit_mode = exam_id is not None
        client_data = self.db._execute_query("SELECT nombre, apellido, rut FROM Clientes WHERE id_cliente = %s", (client_id,), fetch='one')
        client_name = f"{client_data['nombre']} {client_data['apellido']}" if client_data else "Desconocido"; self.setWindowTitle(f"{'Editar' if self.is_edit_mode else 'Nueva'} Receta para: {client_name}"); self.setMinimumWidth(600)
        main_layout = QVBoxLayout(self); form_layout = QGridLayout(); self.fecha_edit = QDateEdit(QDate.currentDate()); self.rp_combo = QComboBox(); self.rp_combo.addItems(["-- Seleccione Tipo --", "Lejos", "Cerca", "Ambos"]); self.observaciones_edit = QTextEdit()
        form_layout.addWidget(QLabel("Paciente:"), 0, 0); form_layout.addWidget(QLabel(f"<b>{client_name}</b> (RUT: {client_data['rut']})"), 0, 1); form_layout.addWidget(QLabel("Fecha:"), 1, 0); form_layout.addWidget(self.fecha_edit, 1, 1); form_layout.addWidget(QLabel("Tipo (Rp):"), 2, 0); form_layout.addWidget(self.rp_combo, 2, 1)
        self.group_lejos = self._create_prescription_group("Lejos"); self.group_cerca = self._create_prescription_group("Cerca"); self.rp_combo.currentIndexChanged.connect(self.update_visible_groups)
        form_layout.addWidget(self.group_lejos, 3, 0, 1, 2); form_layout.addWidget(self.group_cerca, 4, 0, 1, 2); form_layout.addWidget(QLabel("Observaciones:"), 5, 0); form_layout.addWidget(self.observaciones_edit, 6, 0, 1, 2)
        button_box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel); button_box.accepted.connect(self.save_recipe); button_box.rejected.connect(self.reject); main_layout.addLayout(form_layout); main_layout.addWidget(button_box)
        if self.is_edit_mode: self.load_exam_data()
        self.update_visible_groups()
    def _create_prescription_group(self, title):
        group_box = QGroupBox(title); layout = QGridLayout(group_box); layout.addWidget(QLabel("<b>ESF</b>"), 0, 2); layout.addWidget(QLabel("<b>CIL</b>"), 0, 3); layout.addWidget(QLabel("<b>EJE</b>"), 0, 4); layout.addWidget(QLabel("DP:"), 1, 0); dp_input = QSpinBox(); dp_input.setRange(40, 80); layout.addWidget(dp_input, 1, 1); layout.addWidget(QLabel("OD:"), 2, 0); layout.addWidget(QLabel("OI:"), 3, 0); group_box.inputs = { 'dp': dp_input, 'od': {}, 'oi': {} }
        for i, ojo in enumerate(['od', 'oi']):
            for j, val in enumerate(['esf', 'cil', 'eje']): line_edit = QLineEdit(); layout.addWidget(line_edit, i + 2, j + 2); group_box.inputs[ojo][val] = line_edit
        return group_box
    def update_visible_groups(self): selection = self.rp_combo.currentText(); self.group_lejos.setVisible(selection in ["Lejos", "Ambos"]); self.group_cerca.setVisible(selection in ["Cerca", "Ambos"])
    def load_exam_data(self):
        data = self.db.get_exam_details(self.exam_id)
        if not data: self.reject(); return
        self.fecha_edit.setDate(data['fecha']); self.rp_combo.setCurrentText(data['diagnostico']); self.observaciones_edit.setText(data['observaciones'])
        try:
            receta_json = json.loads(data['receta']) if data['receta'] else {}
            if 'lejos' in receta_json:
                for v in ['esf','cil','eje']: self.group_lejos.inputs['od'][v].setText(str(receta_json['lejos'].get('od',{}).get(v,''))); self.group_lejos.inputs['oi'][v].setText(str(receta_json['lejos'].get('oi',{}).get(v,'')))
                self.group_lejos.inputs['dp'].setValue(receta_json['lejos'].get('dp',0))
            if 'cerca' in receta_json:
                for v in ['esf','cil','eje']: self.group_cerca.inputs['od'][v].setText(str(receta_json['cerca'].get('od',{}).get(v,''))); self.group_cerca.inputs['oi'][v].setText(str(receta_json['cerca'].get('oi',{}).get(v,'')))
                self.group_cerca.inputs['dp'].setValue(receta_json['cerca'].get('dp',0))
        except (json.JSONDecodeError, TypeError): QMessageBox.warning(self, "Datos Corruptos", "Formato de receta inválido.")
    def save_recipe(self):
        selection = self.rp_combo.currentText()
        if selection == "-- Seleccione Tipo --": QMessageBox.warning(self, "Campo Requerido", "Seleccione un tipo de receta."); return
        receta_data = {}
        if self.group_lejos.isVisible(): receta_data['lejos'] = {'dp':self.group_lejos.inputs['dp'].value(),'od':{v:self.group_lejos.inputs['od'][v].text() for v in ['esf','cil','eje']},'oi':{v:self.group_lejos.inputs['oi'][v].text() for v in ['esf','cil','eje']}}
        if self.group_cerca.isVisible(): receta_data['cerca'] = {'dp':self.group_cerca.inputs['dp'].value(),'od':{v:self.group_cerca.inputs['od'][v].text() for v in ['esf','cil','eje']},'oi':{v:self.group_cerca.inputs['oi'][v].text() for v in ['esf','cil','eje']}}
        final_data = {'id_cliente':self.client_id,'fecha':self.fecha_edit.date().toString("yyyy-MM-dd"),'diagnostico':selection,'receta':json.dumps(receta_data),'observaciones':self.observaciones_edit.toPlainText()}
        result = self.db.update_exam(self.exam_id, final_data) if self.is_edit_mode else self.db.add_exam(final_data)
        if result is not None: QMessageBox.information(self, "Éxito", "Receta guardada."); self.accept()
        else: QMessageBox.critical(self, "Error", "No se pudo guardar la receta.")

class TransactionWidget(QWidget):
    def __init__(self, db, transaction_type, parent=None):
        super().__init__(parent); self.db = db; self.transaction_type = transaction_type; self.cart = []; self.selected_entity_id = None; self.all_products = self.db.get_products() or []
        self.entity_label = "Cliente" if self.transaction_type == "Venta" else "Proveedor"; self.setWindowTitle(f"Registrar Nueva {self.transaction_type}"); self.setMinimumSize(1000, 750)
        main_layout = QHBoxLayout(self); left_panel = QVBoxLayout(); right_panel = QVBoxLayout()
        entity_group = QGroupBox(f"1. Buscar y Seleccionar {self.entity_label}"); entity_layout = QVBoxLayout(); self.entity_search_input = QLineEdit()
        self.entity_search_input.setPlaceholderText(f"Buscar {self.entity_label.lower()} por nombre o RUT..."); self.entity_results_table = QTableWidget()
        self.entity_results_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.entity_results_table.setSelectionMode(QAbstractItemView.SingleSelection); self.entity_results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        entity_layout.addWidget(self.entity_search_input); entity_layout.addWidget(self.entity_results_table); entity_group.setLayout(entity_layout)
        product_group = QGroupBox("2. Buscar y Agregar Producto"); product_layout = QVBoxLayout(); self.product_search_input = QLineEdit()
        self.product_search_input.setPlaceholderText("Filtrar producto por nombre, tipo o marca..."); self.product_results_table = QTableWidget()
        self.product_results_table.setSelectionBehavior(QAbstractItemView.SelectRows); self.product_results_table.setSelectionMode(QAbstractItemView.SingleSelection); self.product_results_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        add_product_layout = QHBoxLayout(); add_product_layout.addWidget(QLabel("Cantidad:")); self.quantity_spin = CustomSpinBox(); self.quantity_spin.setRange(1, 999)
        self.add_to_cart_btn = QPushButton("➕ Agregar al Carrito"); add_product_layout.addWidget(self.quantity_spin); add_product_layout.addWidget(self.add_to_cart_btn)
        product_layout.addWidget(self.product_search_input); product_layout.addWidget(self.product_results_table); product_layout.addLayout(add_product_layout); product_group.setLayout(product_layout)
        left_panel.addWidget(entity_group); left_panel.addWidget(product_group)
        cart_group = QGroupBox("3. Carrito de la Transacción"); cart_layout = QVBoxLayout(); self.cart_table = QTableWidget(); self.cart_table.setColumnCount(5); self.cart_table.setHorizontalHeaderLabels(["ID Prod", "Nombre", "Cantidad", "Precio Unitario", "Subtotal"])
        self.cart_table.setEditTriggers(QAbstractItemView.NoEditTriggers); 
        
        finalize_layout = QGridLayout(); 
        if self.transaction_type == "Venta":
            self.vendedor_input = QLineEdit(); self.vendedor_input.setPlaceholderText("Nombre del vendedor...")
            self.total_input = CustomSpinBox(); self.total_input.setRange(0, 999999999); self.total_input.setPrefix("$ ")
            finalize_layout.addWidget(QLabel("Vendedor:"), 0, 0); finalize_layout.addWidget(self.vendedor_input, 0, 1)
            finalize_layout.addWidget(QLabel("<b>Total Final (Editable):</b>"), 1, 0); finalize_layout.addWidget(self.total_input, 1, 1)
        else:
            self.total_label = QLabel("Total: $ 0"); font = self.total_label.font(); font.setPointSize(16); self.total_label.setFont(font)
            finalize_layout.addWidget(self.total_label, 0, 0, 1, 2)
        
        self.finalize_btn = QPushButton(f"✅ Finalizar {self.transaction_type}"); finalize_layout.addWidget(self.finalize_btn, 2, 1, alignment=Qt.AlignRight)
        
        cart_layout.addWidget(self.cart_table); cart_layout.addLayout(finalize_layout); cart_group.setLayout(cart_layout)
        right_panel.addWidget(cart_group); main_layout.addLayout(left_panel, 1); main_layout.addLayout(right_panel, 1)
        self.entity_search_input.textChanged.connect(self.search_entity); self.entity_results_table.itemSelectionChanged.connect(self.update_selected_entity)
        self.product_search_input.textChanged.connect(self.filter_products_table); self.add_to_cart_btn.clicked.connect(self.add_to_cart); self.finalize_btn.clicked.connect(self.finalize_transaction)
        self.populate_product_table(); self.update_button_states()

    def search_entity(self):
        search_term = self.entity_search_input.text()
        if len(search_term) < 2: self.entity_results_table.setRowCount(0); return
        results = self.db.get_clients(search_term) if self.transaction_type == "Venta" else self.db.get_suppliers(search_term)
        populate_table(self.entity_results_table, results); self.entity_results_table.resizeColumnsToContents()
    def update_selected_entity(self):
        selected_rows = self.entity_results_table.selectionModel().selectedRows()
        self.selected_entity_id = self.entity_results_table.item(selected_rows[0].row(), 0).data(Qt.UserRole) if selected_rows else None
        self.update_button_states()
    def populate_product_table(self, products_to_show=None): populate_table(self.product_results_table, products_to_show if products_to_show is not None else self.all_products)
    def filter_products_table(self):
        search_term = self.product_search_input.text().lower()
        if not search_term: self.populate_product_table(self.all_products); return
        filtered = [p for p in self.all_products if search_term in p['nombre'].lower() or search_term in p['tipo'].lower() or (p['marca'] and search_term in p['marca'].lower())]
        self.populate_product_table(filtered)
    def add_to_cart(self):
        selected_rows = self.product_results_table.selectionModel().selectedRows()
        if not selected_rows: QMessageBox.warning(self, "Sin Selección", "Por favor, seleccione un producto de la tabla."); return
        product_id = self.product_results_table.item(selected_rows[0].row(), 0).data(Qt.UserRole); quantity_to_add = self.quantity_spin.value()
        product_info = next((p for p in self.all_products if p['id_producto'] == product_id), None)
        if not product_info: return
        if self.transaction_type == "Venta":
            quantity_in_cart = sum(item['cantidad'] for item in self.cart if item['id_producto'] == product_id)
            available_stock = product_info['stock'] - quantity_in_cart
            if quantity_to_add > available_stock:
                QMessageBox.warning(self, "Stock Insuficiente", f"No hay suficiente stock para '{product_info['nombre']}'.\nStock: {product_info['stock']}, En Carrito: {quantity_in_cart}, Puede Agregar: {available_stock}."); return
        
        price_key = 'precio_venta' if self.transaction_type == "Venta" else 'precio_compra'
        item = {"id_producto": product_id, "nombre": product_info['nombre'], "cantidad": quantity_to_add, "precio_venta": product_info['precio_venta'], "precio_compra": product_info['precio_compra'], "subtotal": quantity_to_add * product_info[price_key]}
        self.cart.append(item); self.update_cart_table()
    def update_cart_table(self):
        self.cart_table.setRowCount(len(self.cart)); total = 0
        for row, item in enumerate(self.cart):
            price_to_show = item['precio_venta'] if self.transaction_type == 'Venta' else item['precio_compra']
            self.cart_table.setItem(row, 0, QTableWidgetItem(str(item['id_producto']))); self.cart_table.setItem(row, 1, QTableWidgetItem(item['nombre'])); self.cart_table.setItem(row, 2, QTableWidgetItem(str(item['cantidad'])))
            self.cart_table.setItem(row, 3, QTableWidgetItem(f"${price_to_show:,}")); self.cart_table.setItem(row, 4, QTableWidgetItem(f"${item['subtotal']:,}")); total += item['subtotal']
        if self.transaction_type == "Venta": self.total_input.setValue(total)
        else: self.total_label.setText(f"Total: $ {total:,}")
        self.update_button_states()
    def update_button_states(self): self.finalize_btn.setEnabled(self.selected_entity_id is not None and bool(self.cart))
    def finalize_transaction(self):
        if not self.selected_entity_id: QMessageBox.warning(self, "Falta Información", f"Debe seleccionar un {self.entity_label.lower()}."); return
        if not self.cart: QMessageBox.warning(self, "Carrito Vacío", "Debe agregar productos."); return
        
        details_for_db = [{'id_producto':i['id_producto'], 'cantidad':i['cantidad'], 'precio_venta':i['precio_venta'], 'precio_compra':i['precio_compra']} for i in self.cart]
        if self.transaction_type == "Venta":
            final_total = self.total_input.value(); vendedor_name = self.vendedor_input.text().strip()
            if not vendedor_name: QMessageBox.warning(self, "Campo Requerido", "Por favor, ingrese el nombre del vendedor."); return
            result = self.db.create_sale(self.selected_entity_id, final_total, vendedor_name, details_for_db)
        else:
            total = sum(item['subtotal'] for item in self.cart)
            result = self.db.create_purchase(self.selected_entity_id, total, details_for_db)
        if result: QMessageBox.information(self, "Éxito", f"{self.transaction_type} registrada con ID: {result}"); self.close()

class TransactionViewerWidget(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent); self.db = db; self.setWindowTitle("Historial de Transacciones"); self.setMinimumSize(900, 700)
        main_layout = QVBoxLayout(self); self.tabs = QTabWidget(); self.tabs.addTab(self._create_tab("Venta"), "Ventas"); self.tabs.addTab(self._create_tab("Compra"), "Compras"); main_layout.addWidget(self.tabs)
    def _create_tab(self, type):
        tab = QWidget(); layout = QVBoxLayout(tab); date_layout = QHBoxLayout(); start_date = QDateEdit(QDate.currentDate().addMonths(-1)); end_date = QDateEdit(QDate.currentDate())
        search_btn = QPushButton("🔎 Buscar"); date_layout.addWidget(QLabel("Desde:")); date_layout.addWidget(start_date); date_layout.addWidget(QLabel("Hasta:")); date_layout.addWidget(end_date); date_layout.addWidget(search_btn); date_layout.addStretch()
        table = QTableWidget(); table.setEditTriggers(QAbstractItemView.NoEditTriggers); delete_btn = QPushButton("🗑️ Eliminar Transacción"); delete_btn.setEnabled(False)
        layout.addLayout(date_layout); layout.addWidget(table); btn_layout = QHBoxLayout(); btn_layout.addStretch(); btn_layout.addWidget(delete_btn); layout.addLayout(btn_layout)
        search_btn.clicked.connect(lambda: self.load_transactions(type, table, start_date.date(), end_date.date())); table.itemSelectionChanged.connect(lambda: delete_btn.setEnabled(bool(table.selectedItems())))
        delete_btn.clicked.connect(lambda: self.delete_transaction(type, table, start_date.date(), end_date.date())); self.load_transactions(type, table, start_date.date(), end_date.date()); return tab
    def load_transactions(self, type, table, start_date, end_date): populate_table(table, self.db.get_transactions_by_date(type, start_date.toString("yyyy-MM-dd"), end_date.toString("yyyy-MM-dd")))
    def delete_transaction(self, type, table, start_date, end_date):
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows: return
        item_id = table.item(selected_rows[0].row(), 0).data(Qt.UserRole)
        if QMessageBox.question(self, "Confirmar", f"¿Seguro que quieres eliminar esta {type.lower()}?\n¡El stock será revertido!", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            result = self.db.delete_transaction(type, item_id)
            if result['success']: QMessageBox.information(self, "Éxito", f"{type} eliminada."); self.load_transactions(type, table, start_date, end_date)
            else: QMessageBox.critical(self, "Error", result['message'])

class MonthlyReportWidget(QWidget):
    def __init__(self, db, parent=None):
        super().__init__(parent); self.db = db; self.setWindowTitle("📈 Reporte Mensual de Ventas"); self.setMinimumSize(800, 600)
        main_layout = QVBoxLayout(self); filter_layout = QHBoxLayout(); current_date = QDate.currentDate()
        self.year_spin = QSpinBox(); self.year_spin.setRange(2020, 2050); self.year_spin.setValue(current_date.year())
        self.month_combo = QComboBox(); self.month_combo.addItems(["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"])
        self.month_combo.setCurrentIndex(current_date.month() - 1)
        self.seller_combo = QComboBox()
        report_btn = QPushButton("📊 Generar Reporte"); report_btn.clicked.connect(self.generate_report)
        filter_layout.addWidget(QLabel("Año:")); filter_layout.addWidget(self.year_spin); filter_layout.addWidget(QLabel("Mes:")); filter_layout.addWidget(self.month_combo)
        filter_layout.addWidget(QLabel("Vendedor:")); filter_layout.addWidget(self.seller_combo); filter_layout.addWidget(report_btn); filter_layout.addStretch()
        self.report_table = QTableWidget(); self.total_label = QLabel("Total de Ventas del Mes: $ 0"); font = self.total_label.font(); font.setPointSize(16); font.setBold(True); self.total_label.setFont(font)
        main_layout.addLayout(filter_layout); main_layout.addWidget(self.report_table); main_layout.addWidget(self.total_label, 0, Qt.AlignRight)
        self.populate_sellers(); self.generate_report()

    def populate_sellers(self):
        self.seller_combo.clear(); self.seller_combo.addItem("Todos los vendedores")
        sellers = self.db.get_unique_sellers()
        if sellers: self.seller_combo.addItems([s['vendedor'] for s in sellers])

    def generate_report(self):
        year = self.year_spin.value(); month = self.month_combo.currentIndex() + 1
        seller = self.seller_combo.currentText() if self.seller_combo.currentIndex() > 0 else None
        sales_data = self.db.get_sales_by_month(year, month, seller); populate_table(self.report_table, sales_data)
        total_sales = sum(item['total'] for item in sales_data) if sales_data else 0
        self.total_label.setText(f"Total de Ventas del Período: $ {total_sales:,}")

class MainWindow(QMainWindow):
    def __init__(self, db_instance):
        super().__init__(); self.db = db_instance; self.setWindowTitle("Sistema de Gestión - Óptica"); self.setMinimumSize(800, 400)
        central_widget = QWidget(); self.setCentralWidget(central_widget); layout = QGridLayout(central_widget); layout.setSpacing(15)
        buttons = {
            "👥 Gestionar Clientes": self.open_client_manager, "👓 Gestionar Productos": self.open_product_manager,
            "📝 Gestionar Recetas": self.open_recipe_manager, "🚚 Gestionar Proveedores": self.open_supplier_manager,
            "🛒 Registrar Nueva Venta": self.open_sale_widget, "📦 Registrar Nueva Compra": self.open_purchase_widget,
            "🧾 Historial de Transacciones": self.open_transaction_viewer, "📈 Reporte Mensual de Ventas": self.open_monthly_report,
        }
        positions = [(i, j) for i in range(4) for j in range(2)]
        for (text, action), pos in zip(buttons.items(), positions):
            btn = QPushButton(text); btn.setMinimumHeight(60); btn.clicked.connect(action); layout.addWidget(btn, pos[0], pos[1])
        self.sub_windows = {}
    def closeEvent(self, event): self.db.close(); event.accept()
    def open_window(self, key, widget_class, *constructor_args):
        if key not in self.sub_windows or not self.sub_windows[key].isVisible():
            self.sub_windows[key] = widget_class(*constructor_args)
            self.sub_windows[key].show()
        else: self.sub_windows[key].activateWindow(); self.sub_windows[key].raise_()
    def open_client_manager(self): self.open_window('clients', GenericManagerWidget, self.db, "Clientes", {'nombre':str,'apellido':str,'rut':str,'telefono':str,'correo':str,'direccion':str},'get_clients','add_client','update_client','delete_client')
    def open_product_manager(self):
        fields = {'nombre':str, 'tipo':str, 'marca':str, 'stock':int, 'precio_compra':int, 'precio_venta':int}
        self.open_window('products', GenericManagerWidget, self.db, "Productos", fields, 'get_products', 'add_product', 'update_product', 'delete_product')
    def open_supplier_manager(self): self.open_window('suppliers', GenericManagerWidget, self.db, "Proveedores", {'nombre':str,'contacto':str,'telefono':str,'direccion':str},'get_suppliers','add_supplier','update_supplier','delete_supplier')
    def open_recipe_manager(self): self.open_window('recipes', RecipeManagerWidget, self.db)
    def open_transaction_viewer(self): self.open_window('viewer', TransactionViewerWidget, self.db)
    def open_sale_widget(self): self.open_window('sale', TransactionWidget, self.db, "Venta")
    def open_purchase_widget(self): self.open_window('purchase', TransactionWidget, self.db, "Compra")
    def open_monthly_report(self): self.open_window('monthly_report', MonthlyReportWidget, self.db)

if __name__ == "__main__":
    app = QApplication.instance(); 
    if not app: app = QApplication(sys.argv)
    db = Database()
    if LoginWindow(db).exec() == QDialog.Accepted:
        main_window = MainWindow(db)
        main_window.show()
        app.exec()
