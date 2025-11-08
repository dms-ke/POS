import csv
import os
import sys

# Add the directory containing product_manager.py to the system path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

from product_manager import ProductManager

def import_products_from_csv(csv_filepath, db_name="pos_database.db"):
    """
    Reads product data from a CSV file and imports it into the database.

    :param csv_filepath: The path to the CSV file containing product data.
    :param db_name: The name of the SQLite database file.
    """
    pm = None
    imported_count = 0
    skipped_count = 0
    error_count = 0

    try:
        pm = ProductManager(db_name) # Initialize ProductManager (connects to DB)

        with open(csv_filepath, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile) # Use DictReader to read rows as dictionaries

            # Verify expected headers
            expected_headers = ['P_ID', 'Name', 'Price', 'Stock']
            if not all(header in reader.fieldnames for header in expected_headers):
                print(f"Error: CSV file missing one or more required headers. Expected: {expected_headers}, Found: {reader.fieldnames}")
                return

            print(f"Starting import from {csv_filepath} into {db_name}...")
            for row_num, row in enumerate(reader, start=2): # Start from 2 for row number (1 for header)
                try:
                    product_id = row['P_ID'].strip()
                    name = row['Name'].strip()
                    price = float(row['Price'].strip())
                    stock = int(row['Stock'].strip())

                    if not product_id or not name:
                        print(f"Skipping row {row_num}: Product ID or Name is empty. Row: {row}")
                        skipped_count += 1
                        continue
                    if price <= 0:
                        print(f"Skipping row {row_num}: Price must be positive. Row: {row}")
                        skipped_count += 1
                        continue
                    if stock < 0:
                        print(f"Warning for row {row_num}: Stock is negative. Setting to 0. Row: {row}")
                        stock = 0

                    if pm.add_product(product_id, name, price, stock):
                        imported_count += 1
                    else:
                        # add_product already prints the specific error (e.g., duplicate ID)
                        skipped_count += 1

                except ValueError as ve:
                    print(f"Error converting data in row {row_num}: {ve}. Row: {row}")
                    error_count += 1
                except KeyError as ke:
                    print(f"Error: Missing expected column '{ke}' in row {row_num}. Check CSV headers. Row: {row}")
                    error_count += 1
                except Exception as e:
                    print(f"An unexpected error occurred processing row {row_num}: {e}. Row: {row}")
                    error_count += 1

    except FileNotFoundError:
        print(f"Error: CSV file not found at '{csv_filepath}'")
        error_count += 1
    except Exception as e:
        print(f"An error occurred during import setup: {e}")
        error_count += 1
    finally:
        if pm:
            pm.close() # Ensure database connection is closed
        print("\n--- Import Summary ---")
        print(f"Successfully imported: {imported_count} products.")
        print(f"Skipped (e.g., duplicates, missing data): {skipped_count} products.")
        print(f"Errors encountered (malformed rows): {error_count} rows.")
        print("Import process finished.")


if __name__ == "__main__":
    # You can change 'products.csv' to the actual name of your CSV file
    # and 'pos_database.db' to your database file name if they are different.
    csv_file = "products.csv"
    database_file = "pos_database.db"

    # Make sure the CSV file exists for testing
    if not os.path.exists(csv_file):
        print(f"Warning: '{csv_file}' not found. Creating a sample CSV for demonstration.")
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            f.write("P_ID,Name,Price,Stock\n")
            f.write("SAMPLE001,Demo Product A,100.00,50\n")
            f.write("SAMPLE002,Demo Product B,250.50,20\n")
            f.write("SAMPLE003,Demo Product C,50.00,100\n")
            f.write("P001,Laptop,120000.00,10\n") # Will be skipped if P001 already exists
            print(f"Sample '{csv_file}' created. You can edit it or create your own.")

    import_products_from_csv(csv_file, database_file)

    # After running the import, you can open your POS_GUI.py and see the new products.
    print("\nTo see imported products, run your POS GUI application:")
    print("python pos_gui.py")