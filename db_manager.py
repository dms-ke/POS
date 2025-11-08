import sqlite3
import os
import logging # Add this import

class DBManager:
    def __init__(self, db_name="pos_database.db"):
        self.db_name = db_name
        self.conn = None
        self.cursor = None
        self.connect()
        # The self.create_tables() call is already within self.connect()'s logic now
        # to ensure it runs if the DB didn't exist before connecting.

    def connect(self):
        try:
            db_exists = os.path.exists(self.db_name)
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            logging.info(f"Connected to database: {self.db_name}")

            if not db_exists:
                logging.info("Database file did not exist, attempting to create tables.")
                self.create_tables()

        except sqlite3.Error as e:
            logging.critical(f"Database connection error: {e}") # Log critical error
            raise ConnectionError(f"Failed to connect to database: {e}")

    def close(self):
        if self.conn:
            self.conn.close()
            logging.info("Database connection closed.")

    def get_connection(self):
        return self.conn

    def get_cursor(self):
        return self.cursor

    def create_tables(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    product_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    price REAL NOT NULL,
                    stock INTEGER NOT NULL
                );
            """)
            logging.info("Products table checked/created successfully.")

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales (
                    sale_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    total_amount REAL NOT NULL,
                    payment_method TEXT NOT NULL,
                    sale_date TEXT NOT NULL,
                    cashier_id TEXT
                );
            """)
            logging.info("Sales table checked/created successfully.")

            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS sale_items (
                    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sale_id INTEGER NOT NULL,
                    product_id TEXT NOT NULL,
                    product_name TEXT NOT NULL,
                    price_at_sale REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    subtotal REAL NOT NULL,
                    FOREIGN KEY (sale_id) REFERENCES sales(sale_id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
                );
            """)
            logging.info("Sale_items table checked/created successfully.")
            self.conn.commit()
            logging.info("Database schema committed.")
        except sqlite3.Error as e:
            logging.critical(f"Error creating tables: {e}") # Log critical error
            raise RuntimeError(f"Database table creation failed: {e}")