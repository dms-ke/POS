import sqlite3
import logging # Add this import

class ProductManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.conn = self.db_manager.get_connection()
        self.cursor = self.db_manager.get_cursor()

    def add_product(self, product_id, name, price, stock):
        try:
            self.cursor.execute("INSERT INTO products (product_id, name, price, stock) VALUES (?, ?, ?, ?)",
                                (product_id, name, price, stock))
            self.conn.commit()
            logging.info(f"Product '{name}' (ID: {product_id}) added successfully.")
            return True
        except sqlite3.IntegrityError:
            logging.warning(f"Attempted to add existing Product ID: {product_id}")
            # Do not show messagebox from manager, let GUI handle it if needed
            return False
        except sqlite3.Error as e:
            logging.error(f"Error adding product {product_id}: {e}")
            return False

    def get_all_products(self):
        try:
            self.cursor.execute("SELECT product_id, name, price, stock FROM products ORDER BY name")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error getting all products: {e}")
            return []

    def get_product_by_id(self, product_id):
        try:
            self.cursor.execute("SELECT product_id, name, price, stock FROM products WHERE product_id = ?", (product_id,))
            return self.cursor.fetchone()
        except sqlite3.Error as e:
            logging.error(f"Error getting product by ID {product_id}: {e}")
            return None

    def search_products(self, query):
        try:
            search_pattern = f"%{query}%"
            self.cursor.execute("SELECT product_id, name, price, stock FROM products WHERE name LIKE ? OR product_id LIKE ? ORDER BY name",
                                (search_pattern, search_pattern))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error searching products with query '{query}': {e}")
            return []

    def update_product(self, product_id, new_name, new_price, new_stock):
        try:
            self.cursor.execute("UPDATE products SET name = ?, price = ?, stock = ? WHERE product_id = ?",
                                (new_name, new_price, new_stock, product_id))
            self.conn.commit()
            if self.cursor.rowcount > 0:
                logging.info(f"Product '{product_id}' updated to name '{new_name}', price {new_price}, stock {new_stock}.")
                return True
            else:
                logging.warning(f"Update failed for product ID {product_id}: no rows affected (product not found?).")
                return False
        except sqlite3.Error as e:
            logging.error(f"Error updating product {product_id}: {e}")
            return False

    def decrease_product_stock(self, product_id, quantity):
        try:
            # Note: This method should ideally be called within a transaction context by the caller (POSApp.checkout)
            self.cursor.execute("UPDATE products SET stock = stock - ? WHERE product_id = ? AND stock >= ?",
                                (quantity, product_id, quantity))
            # No commit here; the transaction will be committed/rolled back by the caller (checkout function)
            if self.cursor.rowcount > 0:
                logging.info(f"Decreased stock for product {product_id} by {quantity}.")
                return True
            else:
                logging.warning(f"Failed to decrease stock for {product_id} by {quantity}. Possibly insufficient stock or product not found.")
                return False
        except sqlite3.Error as e:
            logging.error(f"Error decreasing product stock for {product_id} by {quantity}: {e}")
            return False

    def delete_product(self, product_id):
        try:
            self.cursor.execute("DELETE FROM products WHERE product_id = ?", (product_id,))
            self.conn.commit()
            if self.cursor.rowcount > 0:
                logging.info(f"Product '{product_id}' deleted successfully.")
                return True
            else:
                logging.warning(f"Delete failed for product ID {product_id}: no rows affected (product not found?).")
                return False
        except sqlite3.Error as e:
            logging.error(f"Error deleting product {product_id}: {e}")
            return False