import sqlite3
import hashlib
import logging

class UserManager:
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.conn = self.db_manager.get_connection()
        self.cursor = self.db_manager.get_cursor()
        # REMOVED: self.create_users_table() # This will now be called explicitly once by app.py

    def create_users_table(self):
        try:
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'cashier' -- e.g., 'cashier', 'admin'
                );
            """)
            self.conn.commit()
            logging.info("Users table checked/created successfully.")
            # Do NOT add default admin here. This will be done in app.py once.
        except sqlite3.Error as e:
            logging.critical(f"Error creating users table: {e}")
            raise RuntimeError(f"Database users table creation failed: {e}")

    def hash_password(self, password):
        # Using SHA256 for password hashing
        return hashlib.sha256(password.encode()).hexdigest()

    def add_user(self, user_id, username, password, role='cashier'):
        password_hash = self.hash_password(password)
        try:
            self.cursor.execute("INSERT INTO users (user_id, username, password_hash, role) VALUES (?, ?, ?, ?)",
                                (user_id, username, password_hash, role))
            self.conn.commit() # Commit here as this is a standalone operation
            logging.info(f"User '{username}' ({user_id}) added successfully with role {role}.")
            return True
        except sqlite3.IntegrityError:
            logging.warning(f"Attempted to add existing User ID/Username: {user_id}/{username}")
            return False
        except sqlite3.Error as e:
            logging.error(f"Error adding user {username}: {e}")
            return False

    def verify_user(self, username, password):
        password_hash = self.hash_password(password)
        try:
            self.cursor.execute("SELECT user_id, username, role FROM users WHERE username = ? AND password_hash = ?",
                                (username, password_hash))
            user = self.cursor.fetchone()
            if user:
                logging.info(f"User '{username}' logged in successfully (Role: {user[2]}).")
                return {"user_id": user[0], "username": user[1], "role": user[2]}
            else:
                logging.warning(f"Failed login attempt for username: {username}.")
                return None
        except sqlite3.Error as e:
            logging.error(f"Database error during user verification for {username}: {e}")
            return None

    def get_all_users(self):
        try:
            self.cursor.execute("SELECT user_id, username, role FROM users ORDER BY username")
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logging.error(f"Error getting all users: {e}")
            return []

    def add_default_admin_if_empty(self):
        # This function will now be called from app.py
        try:
            self.cursor.execute("SELECT COUNT(*) FROM users")
            if self.cursor.fetchone()[0] == 0:
                logging.info("No users found, adding default admin user 'admin'.")
                # Use the self.add_user method, but no commit here, as it's part of initial setup flow.
                # The add_user method itself commits, so this is fine.
                self.add_user("ADMIN001", "admin", "adminpass", "admin")
                logging.info("Default admin user 'admin' created (password: 'adminpass').")
                return True
            return False
        except sqlite3.Error as e:
            logging.critical(f"Error checking/adding default admin: {e}")
            return False