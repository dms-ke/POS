import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import os
import sys
from datetime import datetime, timedelta
import logging
import hashlib

# Add the directory containing manager files to the system path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

# Import the manager classes
from db_manager import DBManager
from product_manager import ProductManager
from sales_manager import SalesManager
from user_manager import UserManager

# --- Logging Configuration (NEW) ---
logging.basicConfig(
    filename='pos_application.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Calendar widget helper (minimal for date input)
class DatePickerDialog(tk.Toplevel):
    def __init__(self, parent, current_date=None):
        super().__init__(parent)
        self.title("Select Date")
        self.transient(parent)
        self.grab_set()
        self.result_date = None

        self.date_var = tk.StringVar(self)
        if current_date:
            self.date_var.set(current_date.strftime("%Y-%m-%d"))
        else:
            self.date_var.set(datetime.now().strftime("%Y-%m-%d"))

        ttk.Label(self, text="Enter Date (YYYY-MM-DD):").pack(pady=10)
        self.date_entry = ttk.Entry(self, textvariable=self.date_var)
        self.date_entry.pack(padx=10, pady=5)
        self.date_entry.focus_set()

        button_frame = ttk.Frame(self)
        button_frame.pack(pady=10)

        ttk.Button(button_frame, text="Select", command=self._on_select).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)

        self.bind("<Return>", lambda event: self._on_select())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.wait_window(self)

    def _on_select(self):
        date_str = self.date_entry.get()
        try:
            self.result_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            self.destroy()
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter date in YYYY-MM-DD format.", parent=self)
            self.date_entry.focus_set()

# --- NEW: Login Application Class ---
class LoginApp:
    def __init__(self, root):
        self.root = root
        self.root.title("DMS.ATEK POS SYSTEM - Login")
        self.root.geometry("400x250")
        self.root.resizable(False, False)

        # Center the login window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (self.root.winfo_width() // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.root.winfo_height() // 2)
        self.root.geometry(f"+{x}+{y}")

        self.root.configure(bg="#F0F0F0")
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background="#F0F0F0")
        self.style.configure('TLabel', background="#F0F0F0", foreground="#333333", font=("Arial", 10))
        self.style.configure('TEntry', fieldbackground="white", foreground="#333333")
        self.style.configure('TButton', font=("Arial", 10), padding=6, background="#4CAF50", foreground="white")
        self.style.map('TButton', background=[('active', '#45a049')])
        self.style.configure('Accent.TButton', background="#007BFF", foreground="white", font=("Arial", 11, "bold"))
        self.style.map('Accent.TButton', background=[('active', '#0056b3')])

        try:
            self.db_manager = DBManager("pos_database.db")
            logging.info("LoginApp: DatabaseManager initialized.")
            self.user_manager = UserManager(self.db_manager)
            logging.info("LoginApp: UserManager initialized.")
        except (ConnectionError, RuntimeError) as e:
            logging.critical(f"LoginApp: FATAL: Failed to initialize database: {e}. Application will exit.")
            messagebox.showerror("Database Error", f"Failed to initialize database: {e}\nApplication will exit.")
            root.destroy()
            sys.exit(1)

        self.create_widgets()

    def create_widgets(self):
        login_frame = ttk.Frame(self.root, padding="20")
        login_frame.pack(expand=True)

        ttk.Label(login_frame, text="DMS.ATEK POS System", font=("Arial", 14, "bold")).pack(pady=10)

        ttk.Label(login_frame, text="Username:").pack(anchor="w", pady=5)
        self.username_entry = ttk.Entry(login_frame, width=30)
        self.username_entry.pack(pady=5)
        self.username_entry.focus_set()

        ttk.Label(login_frame, text="Password:").pack(anchor="w", pady=5)
        self.password_entry = ttk.Entry(login_frame, show="*", width=30)
        self.password_entry.pack(pady=5)
        self.password_entry.bind("<Return>", self.attempt_login_event)

        login_button = ttk.Button(login_frame, text="Login", style="Accent.TButton", command=self.attempt_login)
        login_button.pack(pady=10)

        # For initial setup: a hint for the default admin user
        ttk.Label(login_frame, text="Default Admin: username 'admin', password 'adminpass'", font=("Arial", 8), foreground="gray").pack(pady=5)


    def attempt_login_event(self, event):
        self.attempt_login()

    def attempt_login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("Login Error", "Please enter both username and password.")
            logging.warning("Login attempt: Empty username or password.")
            return

        user_info = self.user_manager.verify_user(username, password)

        if user_info:
            logging.info(f"User '{username}' logged in successfully. Role: {user_info['role']}")
            self.root.destroy() # Close the login window
            # Launch the main POS application
            main_root = tk.Tk()
            # Pass the logged-in user information to POSApp
            POSApp(main_root, logged_in_user=user_info)
            main_root.mainloop()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.")
            logging.warning(f"Login failed for username: {username}.")
            self.password_entry.delete(0, tk.END) # Clear password field for retry
            self.username_entry.focus_set()


# --- Modified POSApp Class ---
class POSApp:
    # Added logged_in_user parameter
    def __init__(self, root, logged_in_user=None):
        self.root = root
        self.logged_in_user = logged_in_user # Store logged in user info
        self.root.title(f"DMS.ATEK POS SYSTEM - Wote, Makueni County (Logged in as: {self.logged_in_user['username']})")
        self.root.geometry("1024x768")

        try:
            # Re-initialize DBManager, or better, pass it from LoginApp if structure allows
            # For simplicity now, let's re-initialize, but for larger apps, you'd pass it.
            self.db_manager = DBManager("pos_database.db")
            logging.info("POSApp: DatabaseManager initialized successfully.")
            self.product_manager = ProductManager(self.db_manager)
            logging.info("POSApp: ProductManager initialized.")
            self.sales_manager = SalesManager(self.db_manager)
            logging.info("POSApp: SalesManager initialized.")
        except (ConnectionError, RuntimeError) as e:
            logging.critical(f"POSApp: FATAL: Failed to initialize database: {e}. Application will exit.")
            messagebox.showerror("Database Error", f"Failed to initialize database: {e}\nApplication will exit.")
            root.destroy()
            sys.exit(1)

        self._seed_products_if_empty()
        logging.info("Products seeded if database was empty.")

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.root.configure(bg="#F0F0F0")

        self.style.configure('TLabelFrame', background="#EAEAEA", relief="groove")
        self.style.configure('TLabelFrame.Label', foreground="#333333", font=("Arial", 12, "bold"))

        self.style.configure('TButton',
                             font=("Arial", 10),
                             padding=6,
                             background="#4CAF50",
                             foreground="white")
        self.style.map('TButton',
                       background=[('active', '#45a049')])

        self.style.configure('Accent.TButton',
                             background="#007BFF",
                             foreground="white",
                             font=("Arial", 11, "bold"))
        self.style.map('Accent.TButton',
                       background=[('active', '#0056b3')])

        self.style.configure("Treeview",
                             background="#FFFFFF",
                             foreground="#333333",
                             rowheight=25,
                             fieldbackground="#FFFFFF")
        self.style.map('Treeview',
                       background=[('selected', '#C0E0FF')])

        self.style.configure("Treeview.Heading",
                             font=("Arial", 10, "bold"),
                             background="#ADD8E6",
                             foreground="#333333",
                             relief="raised")
        self.style.map("Treeview.Heading",
                       background=[('active', '#90C0D6')])

        self.style.configure('TLabel', background="#EAEAEA", foreground="#333333")
        self.style.configure('TEntry', fieldbackground="white", foreground="#333333")

        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=3)
        self.root.grid_columnconfigure(1, weight=1)

        self.cart_items = {}
        self.total_amount = 0.0
        self.subtotal_amount = 0.0

        self.create_widgets()
        self.load_products_to_treeview()
        self.update_cart_display()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        logging.info("POSApp GUI initialized and ready.")

    def on_closing(self):
        """Called when the window is closed. Ensures database connections are closed."""
        if messagebox.askokcancel("Quit", "Do you want to quit the POS system?"):
            self.db_manager.close() # Ensure DB connection is closed
            logging.info("Application closing. Database connection closed.")
            self.root.destroy()
        else:
            logging.info("Application close cancelled by user.")

    def _seed_products_if_empty(self):
        products = self.product_manager.get_all_products()
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
                self.product_manager.add_product(prod_id, name, price, stock)
            logging.info(f"{len(default_products)} default products seeded.")
        else:
            logging.info("Products already exist, skipping seeding.")

    def create_widgets(self):
        # Left Panel (Product Search and List)
        left_panel = ttk.LabelFrame(self.root, text="Products & Search", padding="10")
        left_panel.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        left_panel.grid_rowconfigure(2, weight=1)
        left_panel.grid_columnconfigure(0, weight=1)

        search_frame = ttk.Frame(left_panel)
        search_frame.grid(row=0, column=0, columnspan=2, pady=5, sticky="ew")
        self.search_entry = ttk.Entry(search_frame, font=("Arial", 12))
        self.search_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))
        self.search_entry.bind("<KeyRelease>", self.filter_products)
        ttk.Button(search_frame, text="Search", command=self.filter_products).pack(side=tk.LEFT)

        # Product Treeview
        self.product_tree = ttk.Treeview(left_panel, columns=("ID", "Name", "Price", "Stock"), show="headings")
        self.product_tree.heading("ID", text="Product ID", anchor=tk.W)
        self.product_tree.heading("Name", text="Name", anchor=tk.W)
        self.product_tree.heading("Price", text="Price (KES)", anchor=tk.E)
        self.product_tree.heading("Stock", text="Stock", anchor=tk.E)

        self.product_tree.column("ID", width=100, anchor=tk.W)
        self.product_tree.column("Name", width=250, anchor=tk.W)
        self.product_tree.column("Price", width=100, anchor=tk.E)
        self.product_tree.column("Stock", width=80, anchor=tk.E)
        self.product_tree.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=5)

        # Scrollbar for product tree
        product_scrollbar = ttk.Scrollbar(left_panel, orient="vertical", command=self.product_tree.yview)
        product_scrollbar.grid(row=2, column=2, sticky="ns")
        self.product_tree.configure(yscrollcommand=product_scrollbar.set)

        # Product management buttons
        product_buttons_frame = ttk.Frame(left_panel)
        product_buttons_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky="ew")
        ttk.Button(product_buttons_frame, text="Add Product", command=self.open_add_product_dialog).pack(side=tk.LEFT, expand=True, padx=2)
        ttk.Button(product_buttons_frame, text="Edit Product", command=self.open_edit_product_dialog).pack(side=tk.LEFT, expand=True, padx=2)
        ttk.Button(product_buttons_frame, text="Delete Product", command=self.delete_selected_product).pack(side=tk.LEFT, expand=True, padx=2)

        # Right Panel (Cart, Checkout, Reports)
        right_panel = ttk.LabelFrame(self.root, text="Cart & Checkout", padding="10")
        right_panel.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        right_panel.grid_rowconfigure(2, weight=1) # Makes cart_treeview expand vertically
        right_panel.grid_columnconfigure(0, weight=1)

        # Cart management
        cart_actions_frame = ttk.Frame(right_panel)
        cart_actions_frame.grid(row=0, column=0, pady=5, sticky="ew")
        self.qty_entry = ttk.Entry(cart_actions_frame, width=5, font=("Arial", 12))
        self.qty_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.qty_entry.insert(0, "1") # Default quantity
        ttk.Button(cart_actions_frame, text="Add to Cart", command=self.add_to_cart).pack(side=tk.LEFT, padx=2)
        ttk.Button(cart_actions_frame, text="Remove Selected", command=self.remove_from_cart).pack(side=tk.LEFT, padx=2)
        ttk.Button(cart_actions_frame, text="Clear Cart", command=self.clear_cart).pack(side=tk.LEFT, padx=2)


        # Cart Treeview
        self.cart_tree = ttk.Treeview(right_panel, columns=("Product", "Price", "Qty", "Total"), show="headings")
        self.cart_tree.heading("Product", text="Product", anchor=tk.W)
        self.cart_tree.heading("Price", text="Price", anchor=tk.E)
        self.cart_tree.heading("Qty", text="Qty", anchor=tk.E)
        self.cart_tree.heading("Total", text="Total", anchor=tk.E)

        self.cart_tree.column("Product", width=150, anchor=tk.W)
        self.cart_tree.column("Price", width=60, anchor=tk.E)
        self.cart_tree.column("Qty", width=40, anchor=tk.E)
        self.cart_tree.column("Total", width=70, anchor=tk.E)
        self.cart_tree.grid(row=2, column=0, sticky="nsew", pady=5)

        # Scrollbar for cart tree
        cart_scrollbar = ttk.Scrollbar(right_panel, orient="vertical", command=self.cart_tree.yview)
        cart_scrollbar.grid(row=2, column=1, sticky="ns")
        self.cart_tree.configure(yscrollcommand=cart_scrollbar.set)

        # Totals Display
        total_frame = ttk.Frame(right_panel)
        total_frame.grid(row=3, column=0, sticky="ew", pady=5)
        ttk.Label(total_frame, text="Subtotal:").pack(side=tk.LEFT)
        self.subtotal_label = ttk.Label(total_frame, text="KES 0.00", font=("Arial", 12, "bold"))
        self.subtotal_label.pack(side=tk.RIGHT)

        ttk.Label(total_frame, text="Total:").pack(side=tk.LEFT)
        self.total_label = ttk.Label(total_frame, text="KES 0.00", font=("Arial", 14, "bold"), foreground="blue")
        self.total_label.pack(side=tk.RIGHT, padx=(0, 10))

        # Payment and Checkout Buttons
        checkout_frame = ttk.Frame(right_panel, padding="5")
        checkout_frame.grid(row=4, column=0, sticky="ew", pady=10)
        ttk.Button(checkout_frame, text="Cash Payment", command=lambda: self.open_payment_dialog("Cash"), style="Accent.TButton").pack(fill=tk.X, pady=2)
        ttk.Button(checkout_frame, text="M-Pesa Payment", command=lambda: self.open_payment_dialog("M-Pesa"), style="Accent.TButton").pack(fill=tk.X, pady=2)
        ttk.Button(checkout_frame, text="Card Payment", command=lambda: self.open_payment_dialog("Card"), style="Accent.TButton").pack(fill=tk.X, pady=2)

        # Reports Button
        ttk.Button(right_panel, text="View Reports", command=self.open_reports_window).grid(row=5, column=0, sticky="ew", pady=10)

    def load_products_to_treeview(self, products=None):
        for item in self.product_tree.get_children():
            self.product_tree.delete(item)

        if products is None:
            products = self.product_manager.get_all_products()

        for product in products:
            # Format price and stock for display
            formatted_price = f"{product[2]:.2f}"
            formatted_stock = f"{int(product[3])}"
            self.product_tree.insert("", "end", values=(product[0], product[1], formatted_price, formatted_stock))
        logging.info("Products loaded into treeview.")


    def filter_products(self, event=None):
        query = self.search_entry.get().strip()
        if query:
            filtered_products = self.product_manager.search_products(query)
            self.load_products_to_treeview(filtered_products)
            logging.info(f"Products filtered with query: '{query}'. Found {len(filtered_products)} results.")
        else:
            self.load_products_to_treeview()
            logging.info("Search query cleared, all products reloaded.")


    def add_to_cart(self):
        selected_item_id = self.product_tree.focus()
        if not selected_item_id:
            messagebox.showinfo("No Selection", "Please select a product from the list to add to cart.")
            logging.warning("Attempted to add to cart without selecting a product.")
            return

        product_values = self.product_tree.item(selected_item_id, 'values')
        product_id = product_values[0]
        product_name = product_values[1]
        price = float(product_values[2])
        current_stock = int(product_values[3])

        qty_input = self.qty_entry.get().strip()
        try:
            quantity = int(qty_input)
            if quantity <= 0:
                messagebox.showerror("Invalid Quantity", "Quantity must be a positive number.")
                logging.warning(f"Invalid quantity entered for product {product_id}: '{qty_input}' (must be > 0)")
                return
        except ValueError:
            messagebox.showerror("Invalid Quantity", "Please enter a valid number for quantity.")
            logging.warning(f"Invalid quantity entered for product {product_id}: '{qty_input}'")
            return

        if quantity > current_stock:
            messagebox.showwarning("Insufficient Stock", f"Only {current_stock} units of {product_name} available.")
            logging.warning(f"Insufficient stock for {product_name} (ID: {product_id}). Requested: {quantity}, Available: {current_stock}.")
            return

        if product_id in self.cart_items:
            # Update existing item quantity
            new_qty = self.cart_items[product_id]['qty'] + quantity
            if new_qty > current_stock:
                 messagebox.showwarning("Insufficient Stock", f"Adding {quantity} more to cart would exceed available stock ({current_stock} for {product_name}). Current cart: {self.cart_items[product_id]['qty']}.")
                 logging.warning(f"Attempted to add to cart beyond stock for {product_name} (ID: {product_id}). Current cart: {self.cart_items[product_id]['qty']}, Add: {quantity}, Total would be: {new_qty}, Stock: {current_stock}.")
                 return
            self.cart_items[product_id]['qty'] = new_qty
            self.cart_items[product_id]['total'] = new_qty * price
            logging.info(f"Updated quantity for {product_name} (ID: {product_id}) in cart to {new_qty}.")
        else:
            # Add new item to cart
            self.cart_items[product_id] = {
                'name': product_name,
                'price': price,
                'qty': quantity,
                'total': quantity * price
            }
            logging.info(f"Added {quantity} x {product_name} (ID: {product_id}) to cart.")

        messagebox.showinfo("Item Added", f"{quantity} x {product_name} added to cart.")
        self.update_cart_display()


    def remove_from_cart(self):
        selected_item_id = self.cart_tree.focus()
        if not selected_item_id:
            messagebox.showinfo("No Selection", "Please select an item from the cart to remove.")
            logging.warning("Attempted to remove from cart without selecting an item.")
            return

        # Get the product_id from the selected item's values (assuming first column is product name, and we need the original ID)
        # We need to map back to product_id using the 'name' from the treeview to the 'name' in self.cart_items
        # A more robust way would be to store product_id directly in the treeview item's `iid` or `tags`
        # For now, let's just use the product name to find it in the cart_items (less efficient but works for simple case)
        item_values = self.cart_tree.item(selected_item_id, 'values')
        product_name_in_cart = item_values[0]

        # Find the product_id in self.cart_items based on product_name_in_cart
        product_id_to_remove = None
        for p_id, item_data in self.cart_items.items():
            if item_data['name'] == product_name_in_cart:
                product_id_to_remove = p_id
                break

        if product_id_to_remove:
            confirm = messagebox.askyesno("Remove Item", f"Are you sure you want to remove {product_name_in_cart} from the cart?")
            if confirm:
                del self.cart_items[product_id_to_remove]
                messagebox.showinfo("Item Removed", f"{product_name_in_cart} removed from cart.")
                logging.info(f"Removed {product_name_in_cart} (ID: {product_id_to_remove}) from cart.")
                self.update_cart_display()
        else:
            logging.error(f"Could not find product '{product_name_in_cart}' in cart_items for removal (Treeview item selected but not found in dict).")
            messagebox.showerror("Error", "Could not remove item. Please try again or clear cart.")


    def clear_cart(self):
        if self.cart_items:
            confirm = messagebox.askyesno("Clear Cart", "Are you sure you want to clear the entire cart?")
            if confirm:
                self.cart_items = {}
                self.update_cart_display()
                messagebox.showinfo("Cart Cleared", "The cart has been emptied.")
                logging.info("Cart cleared by user.")
        else:
            messagebox.showinfo("Cart Empty", "The cart is already empty.")
            logging.info("Attempted to clear an already empty cart.")


    def update_cart_display(self):
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)

        self.subtotal_amount = 0.0
        for product_id, item_data in self.cart_items.items():
            self.cart_tree.insert("", "end", values=(
                item_data['name'],
                f"{item_data['price']:.2f}",
                item_data['qty'],
                f"{item_data['total']:.2f}"
            ))
            self.subtotal_amount += item_data['total']

        self.total_amount = self.subtotal_amount # No discounts/taxes implemented yet
        self.subtotal_label.config(text=f"KES {self.subtotal_amount:.2f}")
        self.total_label.config(text=f"KES {self.total_amount:.2f}")
        logging.debug(f"Cart display updated. Subtotal: {self.subtotal_amount:.2f}, Total: {self.total_amount:.2f}")


    def open_add_product_dialog(self):
        add_window = tk.Toplevel(self.root)
        add_window.title("Add New Product")
        add_window.transient(self.root)
        add_window.grab_set()

        form_frame = ttk.Frame(add_window, padding="15")
        form_frame.pack(expand=True, fill="both")

        labels = ["Product ID:", "Name:", "Price:", "Stock:"]
        entries = {}

        for i, text in enumerate(labels):
            ttk.Label(form_frame, text=text).grid(row=i, column=0, sticky="w", pady=5)
            entry = ttk.Entry(form_frame, width=30)
            entry.grid(row=i, column=1, sticky="ew", pady=5)
            entries[text.replace(":", "").strip().lower().replace(" ", "_")] = entry

        def save_product():
            product_id = entries['product_id'].get().strip().upper() # Ensure ID is uppercase
            name = entries['name'].get().strip()
            price_str = entries['price'].get().strip()
            stock_str = entries['stock'].get().strip()

            if not all([product_id, name, price_str, stock_str]):
                messagebox.showwarning("Input Error", "All fields are required.", parent=add_window)
                return

            try:
                price = float(price_str)
                stock = int(stock_str)
                if price <= 0:
                    messagebox.showerror("Validation Error", "Price must be greater than zero.", parent=add_window)
                    return
                if stock < 0:
                    messagebox.showerror("Validation Error", "Stock cannot be negative.", parent=add_window)
                    return
            except ValueError:
                messagebox.showerror("Input Error", "Price must be a number and Stock must be an integer.", parent=add_window)
                return

            if self.product_manager.add_product(product_id, name, price, stock):
                messagebox.showinfo("Success", "Product added successfully!", parent=add_window)
                logging.info(f"Product added: ID={product_id}, Name={name}")
                self.load_products_to_treeview()
                add_window.destroy()
            else:
                messagebox.showerror("Error", f"Failed to add product. Product ID '{product_id}' might already exist.", parent=add_window)
                logging.error(f"Failed to add product: ID '{product_id}' already exists or DB error.")


        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=len(labels), column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Save Product", command=save_product, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=add_window.destroy).pack(side=tk.RIGHT, padx=5)

        add_window.protocol("WM_DELETE_WINDOW", add_window.destroy)
        add_window.wait_window(add_window)

    def open_edit_product_dialog(self):
        selected_item_id = self.product_tree.focus()
        if not selected_item_id:
            messagebox.showinfo("No Selection", "Please select a product to edit.")
            return

        product_values = self.product_tree.item(selected_item_id, 'values')
        original_product_id = product_values[0]

        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"Edit Product: {original_product_id}")
        edit_window.transient(self.root)
        edit_window.grab_set()

        form_frame = ttk.Frame(edit_window, padding="15")
        form_frame.pack(expand=True, fill="both")

        labels = ["Product ID:", "Name:", "Price:", "Stock:"]
        entries = {}
        initial_values = {
            "product_id": product_values[0],
            "name": product_values[1],
            "price": product_values[2],
            "stock": product_values[3]
        }

        for i, text in enumerate(labels):
            ttk.Label(form_frame, text=text).grid(row=i, column=0, sticky="w", pady=5)
            entry = ttk.Entry(form_frame, width=30)
            entry.grid(row=i, column=1, sticky="ew", pady=5)
            entries[text.replace(":", "").strip().lower().replace(" ", "_")] = entry
            entry.insert(0, initial_values[text.replace(":", "").strip().lower().replace(" ", "_")])
            if text == "Product ID:": # Product ID should not be editable after creation
                entry.config(state='readonly')

        def save_product_changes():
            product_id = original_product_id # Keep original ID
            name = entries['name'].get().strip()
            price_str = entries['price'].get().strip()
            stock_str = entries['stock'].get().strip()

            if not all([product_id, name, price_str, stock_str]):
                messagebox.showwarning("Input Error", "All fields are required.", parent=edit_window)
                return

            try:
                price = float(price_str)
                stock = int(stock_str)
                if price <= 0:
                    messagebox.showerror("Validation Error", "Price must be greater than zero.", parent=edit_window)
                    return
                if stock < 0:
                    messagebox.showerror("Validation Error", "Stock cannot be negative.", parent=edit_window)
                    return
            except ValueError:
                messagebox.showerror("Input Error", "Price must be a number and Stock must be an integer.", parent=edit_window)
                return

            if self.product_manager.update_product(product_id, name, price, stock):
                messagebox.showinfo("Success", "Product updated successfully!", parent=edit_window)
                logging.info(f"Product updated: ID={product_id}, New Name={name}, Price={price}, Stock={stock}")
                self.load_products_to_treeview()
                self.update_cart_display() # Update cart in case price/name changed
                edit_window.destroy()
            else:
                messagebox.showerror("Error", "Failed to update product.", parent=edit_window)
                logging.error(f"Failed to update product ID {product_id}.")

        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=len(labels), column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Save Changes", command=save_product_changes, style="Accent.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=edit_window.destroy).pack(side=tk.RIGHT, padx=5)

        edit_window.protocol("WM_DELETE_WINDOW", edit_window.destroy)
        edit_window.wait_window(edit_window)

    def delete_selected_product(self):
        selected_item_id = self.product_tree.focus()
        if not selected_item_id:
            messagebox.showinfo("No Selection", "Please select a product to delete.")
            return

        product_values = self.product_tree.item(selected_item_id, 'values')
        product_id = product_values[0]
        product_name = product_values[1]

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {product_name} (ID: {product_id})? This action cannot be undone.", icon='warning')
        if confirm:
            if self.product_manager.delete_product(product_id):
                messagebox.showinfo("Success", f"{product_name} deleted successfully.")
                logging.info(f"Product deleted: ID={product_id}, Name={product_name}")
                self.load_products_to_treeview()
                # Also remove from cart if it was there
                if product_id in self.cart_items:
                    del self.cart_items[product_id]
                    self.update_cart_display()
            else:
                messagebox.showerror("Error", f"Failed to delete {product_name}.")
                logging.error(f"Failed to delete product ID {product_id}.")

    def open_payment_dialog(self, payment_method):
        if not self.cart_items:
            messagebox.showwarning("Empty Cart", "Please add items to the cart before proceeding to checkout.")
            logging.warning("Attempted to open payment dialog with empty cart.")
            return

        payment_window = tk.Toplevel(self.root)
        payment_window.title(f"Complete {payment_method} Payment")
        payment_window.transient(self.root)
        payment_window.grab_set()

        total = self.total_amount

        ttk.Label(payment_window, text=f"Total Amount: KES {total:.2f}", font=("Arial", 14, "bold")).pack(pady=10)
        ttk.Label(payment_window, text=f"Payment Method: {payment_method}", font=("Arial", 10)).pack(pady=5)

        ttk.Label(payment_window, text="Amount Tendered (KES):").pack(pady=5)
        amount_entry = ttk.Entry(payment_window, font=("Arial", 12))
        amount_entry.pack(pady=5)
        amount_entry.focus_set()

        change_label = ttk.Label(payment_window, text="Change Due: KES 0.00", font=("Arial", 12, "bold"), foreground="green")
        change_label.pack(pady=10)

        def calculate_change(event=None):
            try:
                tendered = float(amount_entry.get())
                change = tendered - total
                change_label.config(text=f"Change Due: KES {change:.2f}")
                if change >= 0:
                    checkout_button.config(state=tk.NORMAL)
                    change_label.config(foreground="green")
                else:
                    checkout_button.config(state=tk.DISABLED)
                    change_label.config(foreground="red")
            except ValueError:
                change_label.config(text="Change Due: Invalid amount", foreground="red")
                checkout_button.config(state=tk.DISABLED)

        amount_entry.bind("<KeyRelease>", calculate_change)

        def proceed_checkout():
            try:
                tendered_amount = float(amount_entry.get())
                if tendered_amount < total:
                    messagebox.showerror("Payment Error", "Amount tendered is less than the total.", parent=payment_window)
                    logging.warning(f"Payment error: Tendered {tendered_amount:.2f} less than total {total:.2f}.")
                    return
                change = tendered_amount - total
                self.checkout(payment_method, tendered_amount, change)
                payment_window.destroy()
            except ValueError:
                messagebox.showerror("Input Error", "Please enter a valid amount for tendered.", parent=payment_window)
                logging.warning("Payment input error: Invalid tendered amount entered.")


        checkout_button = ttk.Button(payment_window, text="Complete Sale", command=proceed_checkout, style="Accent.TButton")
        checkout_button.pack(pady=10)
        checkout_button.config(state=tk.DISABLED) # Disable until enough money is tendered

        payment_window.protocol("WM_DELETE_WINDOW", payment_window.destroy)
        payment_window.wait_window(payment_window)

    def checkout(self, payment_method, amount_tendered, change_due):
        """
        Processes the final checkout, performs stock deduction, records sale, and generates receipt.
        All operations are part of a single database transaction.
        """
        conn = self.db_manager.get_connection()
        sale_successful = False
        sale_id = None

        try:
            conn.execute("BEGIN TRANSACTION") # Start transaction
            logging.info("Starting checkout transaction.")

            stock_deductions_successful = True
            failed_deductions = []
            for product_id, item_data in self.cart_items.items():
                qty_to_deduct = item_data['qty']
                product_name = item_data['name']

                current_db_product = self.product_manager.get_product_by_id(product_id)
                if current_db_product:
                    db_stock = current_db_product[3]
                    if qty_to_deduct > db_stock:
                         stock_deductions_successful = False
                         failed_deductions.append(f"{product_name} (Requested: {qty_to_deduct}, Available: {db_stock})")
                         logging.warning(f"Insufficient stock for {product_name} (ID: {product_id}). Requested: {qty_to_deduct}, Available: {db_stock}")
                         break
                else:
                    logging.error(f"Product {product_id} not found in DB during checkout stock check. This indicates data inconsistency.")
                    stock_deductions_successful = False
                    failed_deductions.append(product_name + " (Product Not Found in Database)")
                    break

                if not self.product_manager.decrease_product_stock(product_id, qty_to_deduct):
                    stock_deductions_successful = False
                    failed_deductions.append(item_data['name'])
                    logging.error(f"Failed to decrease stock for {product_name} (ID: {product_id}) during checkout.")
                    break

            if not stock_deductions_successful:
                conn.rollback() # Rollback the transaction
                logging.warning(f"Checkout failed due to stock issues. Transaction rolled back. Items: {', '.join(failed_deductions)}")
                messagebox.showwarning(
                    "Checkout Failed",
                    f"Could not complete checkout for the following items due to insufficient stock or product issues:\n"
                    f"{', '.join(failed_deductions)}\n\nTransaction rolled back."
                )
                return

            # Pass the logged-in username as cashier_id
            sale_id = self.sales_manager.record_sale(self.total_amount, payment_method, self.logged_in_user['username'])

            if sale_id is None:
                raise Exception("Failed to record main sale (database error).")
            logging.info(f"Main sale record created with Sale ID: {sale_id}")

            for product_id, item_data in self.cart_items.items():
                if not self.sales_manager.record_sale_item(
                    sale_id,
                    product_id,
                    item_data['name'],
                    item_data['price'],
                    item_data['qty'],
                    item_data['total']
                ):
                    raise Exception(f"Failed to record sale item: {item_data['name']}")
                logging.info(f"Sale item recorded: Sale ID {sale_id}, Product ID {product_id}, Qty {item_data['qty']}")

            conn.commit() # Commit the transaction only if all steps succeed
            sale_successful = True
            logging.info(f"Checkout transaction committed successfully for Sale ID: {sale_id}")
            messagebox.showinfo("Checkout Successful", f"Payment received. Total: KES {self.total_amount:.2f}\nSale ID: {sale_id}")

        except Exception as e:
            conn.rollback() # Rollback on any exception
            logging.error(f"Checkout error for Sale ID {sale_id}: {e}. Transaction rolled back.")
            messagebox.showerror("Checkout Error", f"An error occurred during checkout: {e}\nTransaction rolled back.")
            print(f"Transaction rolled back due to error: {e}") # Keep for immediate console feedback during dev
        finally:
            self.load_products_to_treeview() # Always reload products to reflect latest stock
            if sale_successful and sale_id is not None:
                self.show_receipt_window(sale_id, payment_method, amount_tendered, change_due)
                self.cart_items = {} # Clear cart after successful checkout
                self.update_cart_display()

    def show_receipt_window(self, sale_id, payment_method, amount_tendered, change_due):
        receipt_window = tk.Toplevel(self.root)
        receipt_window.title(f"Receipt - Sale ID: {sale_id}")
        receipt_window.transient(self.root)
        receipt_window.grab_set()

        receipt_text = tk.Text(receipt_window, wrap="word", width=40, height=20, font=("Consolas", 10))
        receipt_text.pack(padx=10, pady=10)

        # Retrieve sale details and items
        sale = self.sales_manager.get_sale_by_id(sale_id)
        sale_items = self.sales_manager.get_sale_items_by_sale_id(sale_id)

        if not sale or not sale_items:
            receipt_text.insert(tk.END, "Error: Could not retrieve sale details.\n")
            logging.error(f"Failed to retrieve sale details for receipt generation for Sale ID {sale_id}.")
            return

        receipt_content = self.generate_receipt_content(sale, sale_items, payment_method, amount_tendered, change_due)
        receipt_text.insert(tk.END, receipt_content)
        receipt_text.config(state="disabled") # Make text read-only

        ttk.Button(receipt_window, text="Close", command=receipt_window.destroy).pack(pady=5)
        logging.info(f"Receipt displayed for Sale ID: {sale_id}.")


    def generate_receipt_content(self, sale, sale_items, payment_method, amount_tendered, change_due):
        sale_id, total_amount, _, sale_date, cashier_id = sale
        receipt = f"""
-------------------------------------
     DMS.ATEK POS SYSTEM
    Wote, Makueni County
-------------------------------------
Date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Sale ID: {sale_id}
Cashier: {cashier_id}
--------------------------------------
Item                Qty  Price    Total
--------------------------------------
"""
        for item in sale_items:
            product_name = item[1]
            price = item[2]
            quantity = item[3]
            subtotal = item[4]
            # Format to align columns
            receipt += f"{product_name:<18.18s} {quantity:<4} {price:>6.2f} {subtotal:>8.2f}\n"

        receipt += f"""
------------------------------------
Subtotal:                    KES {total_amount:.2f}
Total:                       KES {total_amount:.2f}
------------------------------------
Payment Method: {payment_method}
Amount Tendered:             KES {amount_tendered:.2f}
Change Due:                  KES {change_due:.2f}
------------------------------------
THANK YOU FOR YOUR PURCHASE!
------------------------------------
"""
        return receipt


    def open_reports_window(self):
        reports_window = tk.Toplevel(self.root)
        reports_window.title("Sales Reports")
        reports_window.geometry("800x600")
        reports_window.transient(self.root)
        reports_window.grab_set()

        notebook = ttk.Notebook(reports_window)
        notebook.pack(expand=True, fill="both", padx=10, pady=10)

        # --- Daily Sales Report Tab ---
        daily_sales_frame = ttk.Frame(notebook, padding=10)
        notebook.add(daily_sales_frame, text="Daily Sales")

        ttk.Label(daily_sales_frame, text="Select Date:").pack(pady=5)
        self.daily_date_entry = ttk.Entry(daily_sales_frame, width=15)
        self.daily_date_entry.pack(pady=5)
        self.daily_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        ttk.Button(daily_sales_frame, text="Select Date", command=lambda: self._open_date_picker(self.daily_date_entry)).pack(pady=5)
        ttk.Button(daily_sales_frame, text="Generate Daily Report", command=self.generate_daily_sales_report).pack(pady=10)

        self.daily_report_text = tk.Text(daily_sales_frame, wrap="word", font=("Consolas", 10))
        self.daily_report_text.pack(expand=True, fill="both", pady=5)
        self.daily_report_text.config(state="disabled")

        # --- Sales History Tab ---
        sales_history_frame = ttk.Frame(notebook, padding=10)
        notebook.add(sales_history_frame, text="Sales History")

        # IMPORTANT: Configure grid for sales_history_frame to allow treeview to expand
        sales_history_frame.grid_rowconfigure(3, weight=1) # The row containing sales_history_tree
        # Removed: sales_history_frame.grid_rowconfigure(5, weight=1) # The row containing sale_items_text
        sales_history_frame.grid_columnconfigure(0, weight=1) # The column containing sales_history_tree and sale_items_text

        date_range_frame = ttk.Frame(sales_history_frame)
        date_range_frame.grid(row=0, column=0, columnspan=2, pady=5, sticky="ew") # Use grid for date_range_frame
        ttk.Label(date_range_frame, text="Start Date (YYYY-MM-DD):").pack(side=tk.LEFT, padx=5)
        self.start_date_entry = ttk.Entry(date_range_frame, width=15)
        self.start_date_entry.pack(side=tk.LEFT, padx=5)
        self.start_date_entry.insert(0, (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"))
        ttk.Button(date_range_frame, text="Pick", command=lambda: self._open_date_picker(self.start_date_entry)).pack(side=tk.LEFT)

        ttk.Label(date_range_frame, text="End Date (YYYY-MM-DD):").pack(side=tk.LEFT, padx=5)
        self.end_date_entry = ttk.Entry(date_range_frame, width=15)
        self.end_date_entry.pack(side=tk.LEFT, padx=5)
        self.end_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        ttk.Button(date_range_frame, text="Pick", command=lambda: self._open_date_picker(self.end_date_entry)).pack(side=tk.LEFT)

        ttk.Button(sales_history_frame, text="Load Sales History", command=self.load_sales_history).grid(row=1, column=0, columnspan=2, pady=10) # Use grid

        self.sales_history_tree = ttk.Treeview(sales_history_frame, columns=("Sale ID", "Total", "Method", "Date", "Cashier"), show="headings")
        self.sales_history_tree.heading("Sale ID", text="Sale ID", anchor=tk.W)
        self.sales_history_tree.heading("Total", text="Total (KES)", anchor=tk.E)
        self.sales_history_tree.heading("Method", text="Method", anchor=tk.W)
        self.sales_history_tree.heading("Date", text="Date", anchor=tk.W)
        self.sales_history_tree.heading("Cashier", text="Cashier", anchor=tk.W)

        self.sales_history_tree.column("Sale ID", width=80, anchor=tk.W)
        self.sales_history_tree.column("Total", width=100, anchor=tk.E)
        self.sales_history_tree.column("Method", width=100, anchor=tk.W)
        self.sales_history_tree.column("Date", width=150, anchor=tk.W)
        self.sales_history_tree.column("Cashier", width=100, anchor=tk.W)
        self.sales_history_tree.grid(row=3, column=0, sticky="nsew", pady=5) # Use grid here, in row 3

        # Scrollbar for sales history tree
        history_scrollbar = ttk.Scrollbar(sales_history_frame, orient="vertical", command=self.sales_history_tree.yview)
        history_scrollbar.grid(row=3, column=1, sticky="ns") # Place scrollbar in column 1 of row 3
        self.sales_history_tree.configure(yscrollcommand=history_scrollbar.set)
        self.sales_history_tree.bind("<<TreeviewSelect>>", self.display_selected_sale_items)


        ttk.Label(sales_history_frame, text="Sale Items:").grid(row=4, column=0, sticky="w", pady=(10,0)) # Use grid
        # The height=5 for sale_items_text will make it 5 lines tall, not expand.
        self.sale_items_text = tk.Text(sales_history_frame, wrap="word", height=5, font=("Consolas", 9))
        self.sale_items_text.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=5) # Use grid and span columns
        self.sale_items_text.config(state="disabled")

        # --- Top Selling Products Tab ---
        top_selling_frame = ttk.Frame(notebook, padding=10)
        notebook.add(top_selling_frame, text="Top Products")

        top_selling_frame.grid_rowconfigure(2, weight=1) # Assuming Treeview is in row 2
        top_selling_frame.grid_columnconfigure(0, weight=1)

        top_date_range_frame = ttk.Frame(top_selling_frame)
        top_date_range_frame.grid(row=0, column=0, columnspan=3, pady=5, sticky="ew") # Use grid here

        ttk.Label(top_date_range_frame, text="Start Date:").pack(side=tk.LEFT, padx=5)
        self.top_start_date_entry = ttk.Entry(top_date_range_frame, width=15)
        self.top_start_date_entry.pack(side=tk.LEFT, padx=5)
        self.top_start_date_entry.insert(0, (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"))
        ttk.Button(top_date_range_frame, text="Pick", command=lambda: self._open_date_picker(self.top_start_date_entry)).pack(side=tk.LEFT)

        ttk.Label(top_date_range_frame, text="End Date:").pack(side=tk.LEFT, padx=5)
        self.top_end_date_entry = ttk.Entry(top_date_range_frame, width=15)
        self.top_end_date_entry.pack(side=tk.LEFT, padx=5)
        self.top_end_date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        ttk.Button(top_date_range_frame, text="Pick", command=lambda: self._open_date_picker(self.top_end_date_entry)).pack(side=tk.LEFT)

        top_limit_frame = ttk.Frame(top_selling_frame)
        top_limit_frame.grid(row=1, column=0, sticky="w", pady=5) # New frame for limit entry
        ttk.Label(top_limit_frame, text="Limit:").pack(side=tk.LEFT, padx=5)
        self.top_limit_entry = ttk.Entry(top_limit_frame, width=5)
        self.top_limit_entry.pack(side=tk.LEFT, padx=5)
        self.top_limit_entry.insert(0, "10")

        ttk.Button(top_selling_frame, text="Generate Top Products Report", command=self.generate_top_selling_products_report).grid(row=1, column=1, columnspan=2, sticky="ew", pady=10) # Use grid for button

        self.top_products_tree = ttk.Treeview(top_selling_frame, columns=("Product Name", "Units Sold"), show="headings")
        self.top_products_tree.heading("Product Name", text="Product Name", anchor=tk.W)
        self.top_products_tree.heading("Units Sold", text="Units Sold", anchor=tk.E)
        self.top_products_tree.column("Units Sold", width=100, anchor=tk.E)
        self.top_products_tree.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=5) # Use grid here

        top_products_scrollbar = ttk.Scrollbar(top_selling_frame, orient="vertical", command=self.top_products_tree.yview)
        top_products_scrollbar.grid(row=2, column=2, sticky="ns") # Place scrollbar in column 2 of row 2
        self.top_products_tree.configure(yscrollcommand=top_products_scrollbar.set)


    def _open_date_picker(self, entry_widget):
        # Helper to open date picker and update entry widget
        current_date_str = entry_widget.get()
        current_date_obj = None
        try:
            current_date_obj = datetime.strptime(current_date_str, "%Y-%m-%d").date()
        except ValueError:
            pass # Use default current date in dialog if invalid

        dialog = DatePickerDialog(self.root, current_date=current_date_obj)
        if dialog.result_date:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, dialog.result_date.strftime("%Y-%m-%d"))
            logging.info(f"Date picker updated entry with: {dialog.result_date.strftime('%Y-%m-%d')}")


    def generate_daily_sales_report(self):
        date_str = self.daily_date_entry.get().strip()
        try:
            datetime.strptime(date_str, "%Y-%m-%d") # Validate date format
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter a valid date in YYYY-MM-DD format.", parent=self.daily_report_text.master)
            logging.warning(f"Invalid date format for daily sales report: '{date_str}'")
            return

        total_amount, num_sales = self.sales_manager.get_daily_sales_summary(date_str)

        self.daily_report_text.config(state="normal")
        self.daily_report_text.delete(1.0, tk.END)
        report_content = f"""
------------------------------------------------
DAILY SALES SUMMARY FOR {date_str}
------------------------------------------------
Total Sales Amount: KES {total_amount:.2f}
Number of Sales:    {num_sales}
------------------------------------------------
"""
        self.daily_report_text.insert(tk.END, report_content)
        self.daily_report_text.config(state="disabled")
        logging.info(f"Daily sales report generated for {date_str}. Total: {total_amount:.2f}, Sales Count: {num_sales}.")


    def load_sales_history(self):
        for item in self.sales_history_tree.get_children():
            self.sales_history_tree.delete(item)

        start_date_str = self.start_date_entry.get().strip()
        end_date_str = self.end_date_entry.get().strip()

        try:
            start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d")
            if start_date_obj > end_date_obj:
                messagebox.showerror("Date Error", "Start date cannot be after end date.", parent=self.sales_history_tree.master)
                logging.warning(f"Sales history date error: Start date {start_date_str} after end date {end_date_str}.")
                return
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter valid dates in YYYY-MM-DD format.", parent=self.sales_history_tree.master)
            logging.warning(f"Invalid date format for sales history: Start='{start_date_str}', End='{end_date_str}'")
            return

        sales = self.sales_manager.get_sales_by_date_range(start_date_str, end_date_str)
        if not sales:
            self.sales_history_tree.insert("", "end", values=("", "No sales found for this period", "", "", ""))
            logging.info(f"No sales found for date range: {start_date_str} to {end_date_str}.")
        else:
            for sale in sales:
                sale_id, total_amount, payment_method, sale_date, cashier_id = sale
                self.sales_history_tree.insert("", "end", values=(sale_id, f"{total_amount:.2f}", payment_method, sale_date, cashier_id))
            logging.info(f"Sales history loaded for {start_date_str} to {end_date_str}. Found {len(sales)} sales.")
        self.sale_items_text.config(state="normal")
        self.sale_items_text.delete(1.0, tk.END)
        self.sale_items_text.config(state="disabled")


    def display_selected_sale_items(self, event):
        selected_item = self.sales_history_tree.focus()
        if not selected_item:
            return

        sale_id = self.sales_history_tree.item(selected_item, 'values')[0]
        if sale_id == "No sales found for this period": # Handle dummy entry
            self.sale_items_text.config(state="normal")
            self.sale_items_text.delete(1.0, tk.END)
            self.sale_items_text.insert(tk.END, "No sale selected or no items available.")
            self.sale_items_text.config(state="disabled")
            return

        try:
            sale_id = int(sale_id) # Convert to int for manager method
        except ValueError:
            logging.error(f"Invalid Sale ID selected in history treeview: '{sale_id}'")
            return

        sale_items = self.sales_manager.get_sale_items_by_sale_id(sale_id)

        self.sale_items_text.config(state="normal")
        self.sale_items_text.delete(1.0, tk.END)

        if not sale_items:
            self.sale_items_text.insert(tk.END, f"No items found for Sale ID: {sale_id}")
            logging.info(f"No sale items found for Sale ID {sale_id}.")
        else:
            header = "{:<18} {:<5} {:<8} {:<8}\n".format("Product", "Qty", "Price", "Total")
            separator = "-" * 40 + "\n"
            self.sale_items_text.insert(tk.END, header)
            self.sale_items_text.insert(tk.END, separator)
            for item in sale_items:
                product_name = item[1]
                qty = item[3]
                price = item[2]
                subtotal = item[4]
                self.sale_items_text.insert(tk.END, "{:<18.18s} {:<5} {:<8.2f} {:<8.2f}\n".format(product_name, qty, price, subtotal))
            logging.info(f"Displayed {len(sale_items)} items for Sale ID {sale_id}.")

        self.sale_items_text.config(state="disabled")

    def generate_top_selling_products_report(self):
        for item in self.top_products_tree.get_children():
            self.top_products_tree.delete(item)

        start_date_str = self.top_start_date_entry.get().strip()
        end_date_str = self.top_end_date_entry.get().strip()
        limit_str = self.top_limit_entry.get().strip()

        try:
            limit = int(limit_str)
            if limit <= 0:
                messagebox.showerror("Input Error", "Limit must be a positive integer.", parent=self.top_products_tree.master)
                return
        except ValueError:
            messagebox.showerror("Input Error", "Limit must be a valid integer.", parent=self.top_products_tree.master)
            return

        try:
            start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d")
            if start_date_obj > end_date_obj:
                messagebox.showerror("Date Error", "Start date cannot be after end date.", parent=self.top_products_tree.master)
                return
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter valid dates in YYYY-MM-DD format.", parent=self.top_products_tree.master)
            return

        top_products = self.sales_manager.get_top_selling_products(limit=limit, start_date_str=start_date_str, end_date_str=end_date_str)

        if not top_products:
            self.top_products_tree.insert("", "end", values=("No top selling products found for this period.", ""))
            logging.info(f"No top selling products found for {start_date_str} to {end_date_str} with limit {limit}.")
        else:
            for product_name, total_quantity_sold in top_products:
                self.top_products_tree.insert("", "end", values=(product_name, int(total_quantity_sold)))
            logging.info(f"Top {len(top_products)} selling products generated for {start_date_str} to {end_date_str}.")


# --- Main execution block ---
if __name__ == "__main__":
    root = tk.Tk()
    login_app = LoginApp(root)
    root.mainloop()