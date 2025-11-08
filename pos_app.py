# app.py
from flask import Flask, request, jsonify, g, render_template  # ADDED 'render_template'
from flask_cors import CORS
import os
import sys
import logging
from datetime import datetime, timedelta
import sqlite3

# Add the directory containing manager files to the system path
script_dir = os.path.dirname(os.path.abspath(__file__))
# Check if the 'manager_files' directory exists and add it to the path
manager_files_path = os.path.join(script_dir, "manager_files")
if os.path.exists(manager_files_path):
    sys.path.append(manager_files_path)

# Import the manager classes
from db_manager import DBManager
from product_manager import ProductManager
from sales_manager import SalesManager
from user_manager import UserManager

app = Flask(__name__)
CORS(app)

# --- Logging Configuration (for Flask app) ---
logging.basicConfig(
    filename='pos_backend.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

DATABASE_NAME = "pos_database.db"

# --- One-time Database Setup on App Startup ---
def setup_database_once():
    """
    Performs initial database setup, table creation, and data seeding once
    when the Flask application starts.
    """
    logging.info("Backend: Starting one-time database setup.")
    try:
        # Use a temporary DBManager for this one-time setup
        temp_db_manager = DBManager(DATABASE_NAME)

        # Initialize managers with the temporary DBManager
        temp_user_manager = UserManager(temp_db_manager)
        temp_product_manager = ProductManager(temp_db_manager)
        # SalesManager doesn't create tables in its init, so it's fine

        # Create all tables (users, products, sales, sale_items)
        # DBManager.create_tables() also creates products, sales, sale_items
        temp_db_manager.create_tables() # This also creates products/sales tables

        # Create users table and add default admin (if no users exist)
        temp_user_manager.create_users_table() # This only creates the users table
        # add_default_admin_if_empty is now called after create_users_table to ensure it has a table to check
        temp_user_manager.add_default_admin_if_empty()

        # Seed default products (if no products exist)
        # This function now uses the product manager passed to it
        _seed_products_if_empty(temp_product_manager)

        temp_db_manager.close()
        logging.info("Backend: One-time database setup completed successfully.")
    except Exception as e:
        logging.critical(f"Backend: FATAL: Failed during one-time database setup: {e}. Exiting.")
        sys.exit(1) # Critical error, cannot proceed

def _seed_products_if_empty(product_mgr):
    """Seeds default products if the product table is empty."""
    products = product_mgr.get_all_products()
    if not products:
        logging.info("No products found, seeding default products.")
        default_products = [
            ("P001", "Coca-Cola (500ml)", 60.00, 100),
            ("P002", "Dairyland Milk (500ml)", 70.00, 50),
            ("P003", "Broadways Bread (400g)", 65.00, 30),
            ("P004", "Blue Band Margarine (250g)", 150.00, 25),
            ("P005", "Kimbo Cooking Oil (1L)", 350.00, 20),
            ("P006", "Omo Washing Powder (500g)", 200.00, 40),
            ("P007", "Colgate Toothpaste (100g)", 120.00, 35),
            ("P008", "Geisha Soap", 80.00, 60),
            ("P009", "Salt (1kg)", 50.00, 80),
            ("P010", "Sugar (1kg)", 180.00, 70),
            ("P011", "Tea Leaves (250g)", 100.00, 45),
            ("P012", "Unga (2kg)", 250.00, 30),
            ("P013", "Rice (1kg)", 220.00, 25),
            ("P014", "Baraka Cooking Oil (2L)", 680.00, 15),
            ("P015", "Exe Flour (1kg)", 160.00, 50),
        ]
        for prod_id, name, price, stock in default_products:
            product_mgr.add_product(prod_id, name, price, stock)
        logging.info(f"{len(default_products)} default products seeding attempt completed.")
    else:
        logging.info("Products already exist, skipping default seeding.")


# --- Per-Request Database Connection Management (Thread-Safe) ---
def get_db_manager():
    """
    Returns a DBManager instance for the current request.
    If it doesn't exist, it creates and stores one in Flask's 'g' object.
    """
    if 'db_manager' not in g:
        try:
            g.db_manager = DBManager(DATABASE_NAME)
            logging.info("Backend: New DBManager created for current request context.")
            # Initialize other managers here, passing the current request's db_manager
            g.product_manager = ProductManager(g.db_manager)
            g.sales_manager = SalesManager(g.db_manager)
            g.user_manager = UserManager(g.db_manager)
        except (ConnectionError, RuntimeError) as e:
            logging.critical(f"Backend: FATAL: Failed to initialize database in request context: {e}.")
            raise ConnectionError(f"Database connection failed: {e}")
        except Exception as e:
            logging.critical(f"Backend: An unexpected error occurred during manager initialization: {e}.")
            raise RuntimeError(f"Manager initialization failed: {e}")
    return g.db_manager

@app.before_request
def before_request_hook():
    """Ensure db_manager and other managers are available on 'g' before each request."""
    try:
        get_db_manager() # This will create and attach managers to g if they don't exist for the current request
    except (ConnectionError, RuntimeError) as e:
        logging.error(f"Failed to establish database connection for request: {e}")
        return jsonify({"message": f"Server error: Could not connect to database. {e}"}), 500
    except Exception as e:
        logging.error(f"Unexpected error in before_request: {e}")
        return jsonify({"message": f"Server error: An unexpected issue occurred. {e}"}), 500

@app.teardown_appcontext
def close_db_connection(exception):
    db_manager_instance = g.pop('db_manager', None)
    if db_manager_instance is not None:
        db_manager_instance.close()
        logging.info("Backend: DBManager connection closed for current request context.")


# --- API Endpoints ---
# MODIFIED THIS ROUTE TO SERVE THE HTML FILE
@app.route('/')
def home():
    return render_template('dms_pos.html')

@app.route('/login', methods=['POST'])
def login():
    user_manager = g.user_manager
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        logging.warning("Login attempt: Missing username or password.")
        return jsonify({"message": "Username and password are required"}), 400

    user_info = user_manager.verify_user(username, password)

    if user_info:
        logging.info(f"User '{username}' logged in successfully.")
        return jsonify({"message": "Login successful", "user": user_info}), 200
    else:
        logging.warning(f"Login failed for username: {username}.")
        return jsonify({"message": "Invalid username or password"}), 401

@app.route('/products', methods=['GET'])
def get_products():
    product_manager = g.product_manager
    products = product_manager.get_all_products()
    product_list = [
        {"product_id": p[0], "name": p[1], "price": p[2], "stock": p[3]}
        for p in products
    ]
    logging.info(f"Retrieved {len(product_list)} products.")
    return jsonify(product_list), 200

@app.route('/products/search', methods=['GET'])
def search_products():
    product_manager = g.product_manager
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({"message": "Search query 'q' is required"}), 400

    products = product_manager.search_products(query)
    product_list = [
        {"product_id": p[0], "name": p[1], "price": p[2], "stock": p[3]}
        for p in products
    ]
    logging.info(f"Searched products with query '{query}'. Found {len(product_list)} results.")
    return jsonify(product_list), 200

@app.route('/products', methods=['POST'])
def add_product():
    product_manager = g.product_manager
    data = request.get_json()
    product_id = data.get('product_id', '').strip().upper()
    name = data.get('name', '').strip()
    price = data.get('price')
    stock = data.get('stock')

    if not all([product_id, name, price is not None, stock is not None]):
        logging.warning("Add product: Missing data fields.")
        return jsonify({"message": "Product ID, Name, Price, and Stock are required"}), 400

    try:
        price = float(price)
        stock = int(stock)
        if price <= 0:
            return jsonify({"message": "Price must be positive"}), 400
        if stock < 0:
            return jsonify({"message": "Stock cannot be negative"}), 400
    except ValueError:
        logging.warning(f"Add product: Invalid price or stock format. Price: {price}, Stock: {stock}")
        return jsonify({"message": "Price must be a number and Stock an integer"}), 400

    if product_manager.add_product(product_id, name, price, stock):
        logging.info(f"Product '{name}' (ID: {product_id}) added via API.")
        return jsonify({"message": "Product added successfully", "product_id": product_id}), 201
    else:
        logging.warning(f"Failed to add product '{product_id}' via API (might exist).")
        return jsonify({"message": "Failed to add product. Product ID might already exist."}), 409 # Conflict

@app.route('/products/<product_id>', methods=['PUT'])
def update_product(product_id):
    product_manager = g.product_manager
    data = request.get_json()
    name = data.get('name', '').strip()
    price = data.get('price')
    stock = data.get('stock')

    if not all([name, price is not None, stock is not None]):
        logging.warning(f"Update product {product_id}: Missing data fields.")
        return jsonify({"message": "Name, Price, and Stock are required"}), 400

    try:
        price = float(price)
        stock = int(stock)
        if price <= 0:
            return jsonify({"message": "Price must be positive"}), 400
        if stock < 0:
            return jsonify({"message": "Stock cannot be negative"}), 400
    except ValueError:
        logging.warning(f"Update product {product_id}: Invalid price or stock format. Price: {price}, Stock: {stock}")
        return jsonify({"message": "Price must be a number and Stock an integer"}), 400

    if product_manager.update_product(product_id, name, price, stock):
        logging.info(f"Product '{product_id}' updated via API.")
        return jsonify({"message": "Product updated successfully"}), 200
    else:
        logging.warning(f"Failed to update product '{product_id}' via API (not found?).")
        return jsonify({"message": "Failed to update product. Product not found."}), 404

@app.route('/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    product_manager = g.product_manager
    if product_manager.delete_product(product_id):
        logging.info(f"Product '{product_id}' deleted via API.")
        return jsonify({"message": "Product deleted successfully"}), 200
    else:
        logging.warning(f"Failed to delete product '{product_id}' via API (not found?).")
        return jsonify({"message": "Failed to delete product. Product not found."}), 404

@app.route('/sales/checkout', methods=['POST'])
def checkout_sale():
    db_manager = g.db_manager
    product_manager = g.product_manager
    sales_manager = g.sales_manager

    data = request.get_json()
    cart_items_data = data.get('cart_items')
    payment_method = data.get('payment_method')
    amount_tendered = data.get('amount_tendered')
    change_due = data.get('change_due')
    cashier_id = data.get('cashier_id')

    if not all([cart_items_data, payment_method, amount_tendered is not None, change_due is not None, cashier_id]):
        logging.warning("Checkout: Missing data fields.")
        return jsonify({"message": "Missing cart items, payment method, amount tendered, change due, or cashier ID"}), 400

    if not cart_items_data:
        return jsonify({"message": "Cart is empty"}), 400

    conn = db_manager.get_connection()
    sale_id = None
    try:
        conn.execute("BEGIN TRANSACTION")
        logging.info("Backend: Starting checkout transaction.")

        calculated_total_amount = 0.0
        for item in cart_items_data:
            product_id = item.get('product_id')
            qty = item.get('qty')

            db_product = product_manager.get_product_by_id(product_id)
            if not db_product:
                conn.rollback()
                logging.warning(f"Checkout failed: Product {product_id} not found in DB.")
                return jsonify({"message": f"Product {product_id} not found."}), 404

            db_price = db_product[2]
            db_stock = db_product[3]

            if qty > db_stock:
                conn.rollback()
                logging.warning(f"Checkout failed: Insufficient stock for {item.get('name')} (ID: {product_id}). Requested: {qty}, Available: {db_stock}.")
                return jsonify({"message": f"Insufficient stock for {item.get('name')} (Available: {db_stock})."}), 400

            calculated_total_amount += db_price * qty

            if not product_manager.decrease_product_stock(product_id, qty):
                conn.rollback()
                logging.error(f"Failed to decrease stock for {product_id} during checkout.")
                return jsonify({"message": f"Failed to update stock for {item.get('name')}."}), 500

        sale_id = sales_manager.record_sale(calculated_total_amount, payment_method, cashier_id)

        if sale_id is None:
            raise Exception("Failed to record main sale (database error).")
        logging.info(f"Backend: Main sale record created with Sale ID: {sale_id}")

        for item in cart_items_data:
            if not sales_manager.record_sale_item(
                sale_id,
                item['product_id'],
                item['name'],
                item['price'],
                item['qty'],
                item['total']
            ):
                raise Exception(f"Failed to record sale item: {item['name']}")
            logging.info(f"Backend: Sale item recorded: Sale ID {sale_id}, Product ID {item['product_id']}, Qty {item['qty']}")

        conn.commit()
        logging.info(f"Backend: Checkout transaction committed successfully for Sale ID: {sale_id}")
        return jsonify({
            "message": "Checkout successful",
            "sale_id": sale_id,
            "total_amount": calculated_total_amount,
            "payment_method": payment_method,
            "amount_tendered": amount_tendered,
            "change_due": change_due
        }), 200

    except Exception as e:
        conn.rollback()
        logging.error(f"Backend: Checkout error for Sale ID {sale_id}: {e}. Transaction rolled back.")
        return jsonify({"message": f"An error occurred during checkout: {str(e)}", "details": "Transaction rolled back."}), 500

@app.route('/reports/daily_sales', methods=['GET'])
def get_daily_sales_report():
    sales_manager = g.sales_manager
    date_str = request.args.get('date', datetime.now().strftime("%Y-%m-%d")).strip()
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format. UseYYYY-MM-DD."}), 400

    total_amount, num_sales = sales_manager.get_daily_sales_summary(date_str)
    logging.info(f"Generated daily sales report for {date_str}. Total: {total_amount}, Count: {num_sales}.")
    return jsonify({"date": date_str, "total_sales_amount": total_amount, "number_of_sales": num_sales}), 200

@app.route('/reports/sales_history', methods=['GET'])
def get_sales_history():
    sales_manager = g.sales_manager
    start_date_str = request.args.get('start_date', (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")).strip()
    end_date_str = request.args.get('end_date', datetime.now().strftime("%Y-%m-%d")).strip()

    try:
        start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d")
        if start_date_obj > end_date_obj:
            return jsonify({"message": "Start date cannot be after end date."}), 400
    except ValueError:
        return jsonify({"message": "Invalid date format. UseYYYY-MM-DD."}), 400

    sales = sales_manager.get_sales_report(start_date=start_date_str + " 00:00:00", end_date=end_date_str + " 23:59:59")
    sales_list = [
        {"sale_id": s[0], "total_amount": s[1], "payment_method": s[2], "sale_date": s[3], "cashier_id": s[4]}
        for s in sales
    ]
    logging.info(f"Generated sales history for {start_date_str} to {end_date_str}. Found {len(sales_list)} sales.")
    return jsonify(sales_list), 200

@app.route('/reports/sale_items/<int:sale_id>', methods=['GET'])
def get_sale_items(sale_id):
    sales_manager = g.sales_manager
    # sales_manager.get_sale_details already fetches items, can reuse or create a specific one
    sale_details = sales_manager.get_sale_details(sale_id)
    if sale_details and "items" in sale_details:
        logging.info(f"Retrieved {len(sale_details['items'])} sale items for Sale ID {sale_id}.")
        return jsonify(sale_details["items"]), 200
    elif sale_details is None:
        logging.warning(f"Sale with ID {sale_id} not found when trying to get items.")
        return jsonify({"message": f"Sale with ID {sale_id} not found."}), 404
    else: # Sale found but no items, or other issue
        logging.warning(f"Could not retrieve sale items for Sale ID {sale_id}.")
        return jsonify({"message": f"Could not retrieve sale items for Sale ID {sale_id}."}), 500


@app.route('/reports/top_products', methods=['GET'])
def get_top_selling_products_report():
    sales_manager = g.sales_manager
    limit_str = request.args.get('limit', '10').strip()
    start_date_str = request.args.get('start_date', (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")).strip()
    end_date_str = request.args.get('end_date', datetime.now().strftime("%Y-%m-%d")).strip()

    try:
        limit = int(limit_str)
        if limit <= 0:
            return jsonify({"message": "Limit must be a positive integer."}), 400
    except ValueError:
        return jsonify({"message": "Invalid limit format. Must be an integer."}), 400

    try:
        start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d")
        if start_date_obj > end_date_obj:
            return jsonify({"message": "Start date cannot be after end date."}), 400
    except ValueError:
        return jsonify({"message": "Invalid date format. UseYYYY-MM-DD."}), 400

    top_products = sales_manager.get_top_selling_products(limit=limit, start_date_str=start_date_str, end_date_str=end_date_str)
    top_products_list = [
        {"product_name": p[0], "units_sold": p[1]}
        for p in top_products
    ]
    logging.info(f"Generated top selling products report for {start_date_str} to {end_date_str} with limit {limit}.")
    return jsonify(top_products_list), 200

# Run one-time database setup when the application starts
if __name__ == '__main__':
    setup_database_once() # Call this ONCE before running the app
    app.run(debug=True, host='0.0.0.0', port=5000)