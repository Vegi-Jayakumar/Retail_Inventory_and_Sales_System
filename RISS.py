'''
Retail Inventory and Sales System

Classes
    1.Product
    2.Inventory
    3.Category
    4.Sale
    5.TXT Storage

'''

from datetime import datetime
import os

PRODUCT_FILE = "C:/Users/vegij/OneDrive/Desktop/CG/CG_Python/Projects/RetailInventoryandSalesSystem/Data/products.txt"
CATEGORY_FILE = "C:/Users/vegij/OneDrive/Desktop/CG/CG_Python/Projects/RetailInventoryandSalesSystem/Data/categories.txt"
SALES_FILE = "C:/Users/vegij/OneDrive/Desktop/CG/CG_Python/Projects/RetailInventoryandSalesSystem/Data/sales.txt"
LOW_STOCK_LIMIT = 5


# -------------------- PRODUCT CLASS --------------------

class Product:
    def __init__(self, product_id, name, category, price, quantity):
        self.product_id = product_id
        self.name = name
        self.category = category
        self.price = price
        self.quantity = quantity

    def display(self):
        print(
            f"{self.product_id:<10}"
            f"{self.name:<20}"
            f"{self.category:<18}"
            f"{self.price:>12.2f}"
            f"{self.quantity:>12}"
        )

    def to_line(self):
        return (
            f"{self.product_id}|{self.name}|{self.category}|"
            f"{self.price}|{self.quantity}\n"
        )

    @classmethod
    def from_line(cls, line):
        parts = line.strip().split("|")

        if len(parts) != 5:
            raise ValueError("Invalid product record.")

        return cls(
            parts[0],
            parts[1],
            parts[2],
            float(parts[3]),
            int(parts[4])
        )


# -------------------- CATEGORY CLASS --------------------

class CategoryManager:
    def __init__(self):
        self.categories = set()
        self.load_categories()

    def load_categories(self):
        try:
            with open(CATEGORY_FILE, "r") as file:
                for line in file:
                    category = line.strip()
                    if category:
                        self.categories.add(category)
        except FileNotFoundError:
            pass

    def save_categories(self):
        with open(CATEGORY_FILE, "w") as file:
            for category in sorted(self.categories):
                file.write(category + "\n")

    def add_category(self):
        name = input("Enter category name: ").strip()

        if not name or "|" in name:
            print("Enter a valid category name.")
            return

        if name in self.categories:
            print("Category already exists.")
            return

        self.categories.add(name)
        self.save_categories()
        print("Category added successfully.")

    def view_categories(self):
        print("\n--- AVAILABLE CATEGORIES ---")

        if not self.categories:
            print("No categories available.")
            return

        for category in sorted(self.categories):
            print("-", category)


# -------------------- FILE MANAGER CLASS --------------------

class FileManager:
    """Handles basic TXT file reading and writing."""

    @staticmethod
    def load_products():
        products = {}

        try:
            with open(PRODUCT_FILE, "r") as file:
                for line in file:
                    try:
                        product = Product.from_line(line)
                        products[product.product_id] = product
                    except ValueError:
                        print("Skipping invalid product record.")
        except FileNotFoundError:
            pass

        return products

    @staticmethod
    def save_products(products):
        with open(PRODUCT_FILE, "w") as file:
            for product in products.values():
                file.write(product.to_line())

    @staticmethod
    def load_sales():
        sales = []

        try:
            with open(SALES_FILE, "r") as file:
                for line in file:
                    parts = line.strip().split("|")

                    if len(parts) != 7:
                        print("Skipping invalid sales record.")
                        continue

                    try:
                        sales.append({
                            "product_id": parts[0],
                            "product_name": parts[1],
                            "quantity": int(parts[2]),
                            "unit_price": float(parts[3]),
                            "total": float(parts[4]),
                            "date": parts[5],
                            "time": parts[6]
                        })
                    except ValueError:
                        print("Skipping invalid sales record.")

        except FileNotFoundError:
            pass

        return sales

    @staticmethod
    def save_sales(sales):
        with open(SALES_FILE, "w") as file:
            for sale in sales:
                file.write(
                    f"{sale['product_id']}|"
                    f"{sale['product_name']}|"
                    f"{sale['quantity']}|"
                    f"{sale['unit_price']}|"
                    f"{sale['total']}|"
                    f"{sale['date']}|"
                    f"{sale['time']}\n"
                )


# -------------------- INVENTORY CLASS --------------------

class Inventory:
    def __init__(self, category_manager):
        self.products = FileManager.load_products()
        self.category_manager = category_manager

    def add_product(self):
        print("\n--- ADD PRODUCT ---")

        product_id = input("Enter product ID: ").strip()

        if not product_id or "|" in product_id:
            print("Enter a valid product ID.")
            return

        if product_id in self.products:
            print("Product ID already exists.")
            return

        name = input("Enter product name: ").strip()

        if not name or "|" in name:
            print("Enter a valid product name.")
            return

        self.category_manager.view_categories()

        category = input("Enter category: ").strip()

        if category not in self.category_manager.categories:
            print("Invalid category. Create the category first.")
            return

        price = self.get_number("Enter selling price: ", 0.01)
        quantity = int(
            self.get_number("Enter initial stock quantity: ", 0)
        )

        product = Product(
            product_id, name, category, price, quantity
        )

        self.products[product_id] = product
        self.save()
        print("Product added successfully.")

    @staticmethod
    def get_number(message, minimum):
        while True:
            try:
                value = float(input(message))

                if value < minimum:
                    print(f"Value must be at least {minimum}.")
                    continue

                return value

            except ValueError:
                print("Invalid input. Enter a valid number.")

    def view_products(self):
        print("\n--- PRODUCT INVENTORY ---")

        if not self.products:
            print("No products available.")
            return

        print("-" * 72)
        print(
            f"{'ID':<10}{'Name':<20}{'Category':<18}"
            f"{'Price':>12}{'Quantity':>12}"
        )
        print("-" * 72)

        for product in self.products.values():
            product.display()

        print("-" * 72)

    def stock_entry(self):
        print("\n--- STOCK ENTRY ---")

        product_id = input("Enter product ID: ").strip()
        product = self.products.get(product_id)

        if product is None:
            print("Product not found.")
            return

        quantity = int(
            self.get_number("Enter quantity to add: ", 1)
        )

        product.quantity += quantity
        self.save()

        print("Stock updated successfully.")
        print("Available quantity:", product.quantity)

    def low_stock_report(self):
        print("\n--- LOW-STOCK REPORT ---")

        found = False

        for product in self.products.values():
            if product.quantity <= LOW_STOCK_LIMIT:
                print(
                    f"{product.product_id} | {product.name} | "
                    f"Stock: {product.quantity}"
                )
                found = True

        if not found:
            print("No low-stock products.")

    def save(self):
        FileManager.save_products(self.products)


# -------------------- SALES CLASS --------------------

class Sales:
    def __init__(self, inventory):
        self.inventory = inventory
        self.records = FileManager.load_sales()

    def record_sale(self):
        print("\n--- SALES ENTRY ---")

        product_id = input("Enter product ID: ").strip()
        product = self.inventory.products.get(product_id)

        if product is None:
            print("Product not found.")
            return

        print("Product:", product.name)
        print(f"Price: Rs. {product.price:.2f}")
        print("Available stock:", product.quantity)

        quantity = int(
            Inventory.get_number("Enter quantity to sell: ", 1)
        )

        if quantity > product.quantity:
            print("Insufficient stock. Sale cancelled.")
            return

        total = round(quantity * product.price, 2)
        now = datetime.now()

        sale = {
            "product_id": product.product_id,
            "product_name": product.name,
            "quantity": quantity,
            "unit_price": product.price,
            "total": total,
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H:%M:%S")
        }

        # Update inventory only after validation
        product.quantity -= quantity
        self.records.append(sale)

        self.inventory.save()
        FileManager.save_sales(self.records)

        print("\nSale completed successfully!")
        print("Product:", product.name)
        print("Quantity sold:", quantity)
        print(f"Total amount: Rs. {total:.2f}")
        print("Remaining stock:", product.quantity)

    def revenue_report(self):
        revenue = sum(sale["total"] for sale in self.records)

        print("\n--- REVENUE REPORT ---")
        print("Total sale entries:", len(self.records))
        print(f"Total revenue: Rs. {revenue:.2f}")

    def product_sales_summary(self):
        print("\n--- PRODUCT-WISE SALES SUMMARY ---")

        if not self.records:
            print("No sales recorded.")
            return

        summary = {}

        for sale in self.records:
            product_id = sale["product_id"]

            if product_id not in summary:
                summary[product_id] = {
                    "name": sale["product_name"],
                    "quantity": 0,
                    "revenue": 0.0
                }

            summary[product_id]["quantity"] += sale["quantity"]
            summary[product_id]["revenue"] += sale["total"]

        for data in summary.values():
            print(
                f"{data['name']} | "
                f"Quantity sold: {data['quantity']} | "
                f"Revenue: Rs. {data['revenue']:.2f}"
            )

    def daily_sales_summary(self):
        print("\n--- DAILY SALES SUMMARY ---")

        date = input(
            "Enter date (YYYY-MM-DD), or press Enter for today: "
        ).strip()

        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            print("Invalid date. Use YYYY-MM-DD.")
            return

        daily = [
            sale for sale in self.records
            if sale["date"] == date
        ]

        if not daily:
            print("No sales found for", date)
            return

        total_quantity = sum(sale["quantity"] for sale in daily)
        total_revenue = sum(sale["total"] for sale in daily)

        print("Date:", date)
        print("Sale entries:", len(daily))
        print("Items sold:", total_quantity)
        print(f"Total revenue: Rs. {total_revenue:.2f}")

        for sale in daily:
            print(
                f"{sale['time']} | {sale['product_name']} | "
                f"Qty: {sale['quantity']} | "
                f"Amount: Rs. {sale['total']:.2f}"
            )


# -------------------- MAIN APPLICATION CLASS --------------------

class RetailInventorySystem:
    def __init__(self):
        self.category_manager = CategoryManager()
        self.inventory = Inventory(self.category_manager)
        self.sales = Sales(self.inventory)

    def run(self):
        while True:
            print("\n" + "=" * 42)
            print(" RETAIL INVENTORY AND SALES SYSTEM")
            print("=" * 42)
            print("1. Add Product")
            print("2. View Products")
            print("3. Manage Categories")
            print("4. Stock Entry")
            print("5. Sales Entry")
            print("6. Low-Stock Report")
            print("7. Revenue Report")
            print("8. Product-Wise Sales Summary")
            print("9. Daily Sales Summary")
            print("10. Exit")
            print("=" * 42)

            choice = input("Enter your choice: ").strip()

            try:
                if choice == "1":
                    self.inventory.add_product()

                elif choice == "2":
                    self.inventory.view_products()

                elif choice == "3":
                    self.category_menu()

                elif choice == "4":
                    self.inventory.stock_entry()

                elif choice == "5":
                    self.sales.record_sale()

                elif choice == "6":
                    self.inventory.low_stock_report()

                elif choice == "7":
                    self.sales.revenue_report()

                elif choice == "8":
                    self.sales.product_sales_summary()

                elif choice == "9":
                    self.sales.daily_sales_summary()

                elif choice == "10":
                    print("Thank you for using the system!")
                    break

                else:
                    print("Invalid choice. Select 1-10.")

            except (OSError, ValueError) as error:
                print("Operation failed:", error)

    def category_menu(self):
        while True:
            print("\n--- CATEGORY MANAGEMENT ---")
            print("1. Add Category")
            print("2. View Categories")
            print("3. Back")

            choice = input("Enter your choice: ").strip()

            if choice == "1":
                self.category_manager.add_category()
            elif choice == "2":
                self.category_manager.view_categories()
            elif choice == "3":
                break
            else:
                print("Invalid choice.")


# -------------------- PROGRAM --------------------

if __name__ == "__main__":
    try:
        app = RetailInventorySystem()
        app.run()
    except OSError as error:
        print("Unable to access a required file:", error)
