import sqlite3
from datetime import datetime, timedelta
import logging

class SalesManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.conn = self.db_manager.get_connection()
        self.cursor = self.db_manager.get_cursor()

    def record_sale(self, total_amount, payment_method, cashier_id):
        try:
            sale_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute("""
                INSERT INTO sales (total_amount, payment_method, sale_date, cashier_id)
                VALUES (?, ?, ?, ?)
            """, (total_amount, payment_method, sale_date, cashier_id))
            # No commit here; it's part of the larger transaction in pos_gui
            logging.info(f"Sale recorded (ID: {self.cursor.lastrowid}, Total: {total_amount}, Method: {payment_method}). Awaiting commit.")
            return self.cursor.lastrowid
        except sqlite3.Error as e:
            logging.error(f"Error recording sale (total: {total_amount}, method: {payment_method}): {e}")
            return None

    def record_sale_item(self, sale_id, product_id, product_name, price_at_sale, quantity, subtotal):
        try:
            self.cursor.execute("""
                INSERT INTO sale_items (sale_id, product_id, product_name, price_at_sale, quantity, subtotal)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (sale_id, product_id, product_name, price_at_sale, quantity, subtotal))
            # No commit here; it's part of the larger transaction in pos_gui
            logging.info(f"Sale item recorded for Sale ID {sale_id}: Product {product_name}, Quantity {quantity}.")
            return True
        except sqlite3.Error as e:
            logging.error(f"Error recording sale item for sale_id {sale_id}, product {product_id}: {e}")
            return False

    def get_sale_details(self, sale_id):
        """
        Retrieves comprehensive details for a specific sale, including all its items.
        :param sale_id: The ID of the sale to retrieve.
        :return: A dictionary containing sale details and a list of sale items, or None if not found.
        """
        try:
            self.cursor.execute("SELECT sale_id, total_amount, payment_method, sale_date, cashier_id FROM sales WHERE sale_id = ?", (sale_id,))
            sale_header = self.cursor.fetchone()

            if not sale_header:
                logging.warning(f"Sale with ID {sale_id} not found.")
                return None

            # Fetch sale items for the given sale_id
            self.cursor.execute("""
                SELECT product_name, price_at_sale, quantity, subtotal
                FROM sale_items
                WHERE sale_id = ?
                ORDER BY product_name
            """, (sale_id,))
            sale_items = self.cursor.fetchall()

            # Convert sale_header tuple to dictionary for better readability
            sale_details = {
                "sale_id": sale_header[0],
                "total_amount": sale_header[1],
                "payment_method": sale_header[2],
                "sale_date": sale_header[3],
                "cashier_id": sale_header[4],
                "items": [
                    {"product_name": item[0], "price_at_sale": item[1], "quantity": item[2], "subtotal": item[3]}
                    for item in sale_items
                ]
            }
            logging.info(f"Retrieved details for Sale ID {sale_id}.")
            return sale_details
        except sqlite3.Error as e:
            logging.error(f"Error getting sale details for ID {sale_id}: {e}")
            return None

    def get_sales_report(self, start_date=None, end_date=None):
        try:
            query = "SELECT sale_id, total_amount, payment_method, sale_date, cashier_id FROM sales"
            params = []
            conditions = []

            if start_date:
                conditions.append("sale_date >= ?")
                params.append(start_date)
            if end_date:
                conditions.append("sale_date <= ?")
                params.append(end_date)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            query += " ORDER BY sale_date DESC"

            self.cursor.execute(query, tuple(params))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error getting sales report: {e}")
            return []

    def get_top_selling_products(self, limit=10, start_date_str=None, end_date_str=None):
        try:
            query = """
                SELECT si.product_name, SUM(si.quantity) as total_quantity_sold
                FROM sale_items si
                JOIN sales s ON si.sale_id = s.sale_id
            """
            params = []
            where_clauses = []

            if start_date_str:
                where_clauses.append("s.sale_date >= ?")
                params.append(start_date_str + " 00:00:00")
            if end_date_str:
                where_clauses.append("s.sale_date <= ?")
                # To include the entire end_date, set the end time to the last microsecond of the day
                end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d") + timedelta(days=1) - timedelta(microseconds=1)
                params.append(end_date_obj.strftime("%Y-%m-%d %H:%M:%S"))


            if where_clauses:
                query += " WHERE " + " AND ".join(where_clauses)

            query += """
                GROUP BY si.product_name
                ORDER BY total_quantity_sold DESC
                LIMIT ?
            """
            params.append(limit)

            self.cursor.execute(query, tuple(params))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error getting top selling products: {e}")
            return []

    def get_daily_sales_summary(self, date_str): #
        """
        Retrieves the total sales amount and number of sales for a specific date.
        Date string format: 'YYYY-MM-DD'.
        """
        try:
            # Use LIKE to match any sale_date that starts with the given date_str
            # because sale_date is stored as 'YYYY-MM-DD HH:MM:SS'
            query = """
                SELECT SUM(total_amount), COUNT(sale_id)
                FROM sales
                WHERE sale_date LIKE ? || '%'
            """
            self.cursor.execute(query, (date_str,))
            result = self.cursor.fetchone()

            total_amount = result[0] if result[0] is not None else 0.0
            num_sales = result[1] if result[1] is not None else 0

            logging.info(f"Retrieved daily sales summary for {date_str}: Total: {total_amount}, Count: {num_sales}")
            return total_amount, num_sales
        except sqlite3.Error as e:
            logging.error(f"Error getting daily sales summary for date {date_str}: {e}")
            return 0.0, 0 # Return default values on error