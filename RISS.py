from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import math
import os
import tempfile

DATA_DIR = Path(__file__).resolve().parent / "Data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
PRODUCT_FILE = DATA_DIR / "products.txt"
CATEGORY_FILE = DATA_DIR / "categories.txt"
SALES_FILE = DATA_DIR / "sales.txt"
LOW_STOCK_LIMIT = 5
CENT = Decimal("0.01")


def money(value):
    """Parse finite money and consistently round half up to cents."""
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Invalid monetary value.")
    if not amount.is_finite():
        raise ValueError("Monetary values must be finite.")
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="", dir=path.parent,
                                         prefix=path.name + ".", suffix=".tmp", delete=False) as stream:
            temp_name = stream.name
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
        raise


def atomic_many(contents):
    """Replace several files, restoring their original bytes if any replacement fails."""
    originals = {}
    for path in contents:
        path = Path(path)
        originals[path] = path.read_bytes() if path.exists() else None
    written = []
    try:
        for path, content in contents.items():
            atomic_write(path, content)
            written.append(Path(path))
    except Exception:
        for path in reversed(written):
            previous = originals[path]
            if previous is None:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
            else:
                atomic_write(path, previous.decode("utf-8"))
        raise


class Product:
    def __init__(self, product_id, name, category, price, quantity):
        self.product_id, self.name, self.category = product_id, name, category
        self.price, self.quantity = money(price), quantity

    def display(self):
        print(f"{self.product_id:<10}{self.name:<20}{self.category:<18}{self.price:>12.2f}{self.quantity:>12}")

    def to_line(self):
        return f"{self.product_id}|{self.name}|{self.category}|{self.price:.2f}|{self.quantity}\n"

    @classmethod
    def from_line(cls, line):
        parts = line.rstrip("\r\n").split("|")
        if len(parts) != 5 or any(not item for item in parts[:3]):
            raise ValueError("Invalid product record.")
        price = money(parts[3])
        quantity = int(parts[4])
        if price <= 0 or str(quantity) != parts[4] or quantity < 0:
            raise ValueError("Product price and stock are invalid.")
        return cls(parts[0], parts[1], parts[2], price, quantity)


class CategoryManager:
    def __init__(self):
        self.categories = self.load_categories()

    @staticmethod
    def load_categories():
        if not CATEGORY_FILE.exists():
            return set()
        categories = set()
        for line_no, line in enumerate(CATEGORY_FILE.read_text(encoding="utf-8").splitlines(), 1):
            category = line.strip()
            if not category or "|" in category or category in categories:
                raise ValueError(f"Invalid or duplicate category at line {line_no}; file left unchanged.")
            categories.add(category)
        return categories

    def save_categories(self):
        atomic_write(CATEGORY_FILE, "".join(c + "\n" for c in sorted(self.categories)))

    def add_category(self):
        name = input("Enter category name: ").strip()
        if not name or "|" in name or "\n" in name:
            print("Enter a valid category name."); return
        if name in self.categories:
            print("Category already exists."); return
        self.categories.add(name)
        try:
            self.save_categories()
        except Exception:
            self.categories.remove(name)
            raise
        print("Category added successfully.")

    def view_categories(self):
        print("\n--- AVAILABLE CATEGORIES ---")
        if not self.categories:
            print("No categories available."); return
        for category in sorted(self.categories): print("-", category)


class FileManager:
    @staticmethod
    def load_products(categories):
        if not PRODUCT_FILE.exists(): return {}
        products = {}
        for line_no, line in enumerate(PRODUCT_FILE.read_text(encoding="utf-8").splitlines(), 1):
            try:
                product = Product.from_line(line)
                if product.product_id in products: raise ValueError("Duplicate product ID.")
                if product.category not in categories: raise ValueError("Unknown category.")
                products[product.product_id] = product
            except Exception as exc:
                raise ValueError(f"Invalid product record on line {line_no}: {exc} File left unchanged.") from exc
        return products

    @staticmethod
    def product_text(products): return "".join(p.to_line() for p in products.values())

    @staticmethod
    def save_products(products): atomic_write(PRODUCT_FILE, FileManager.product_text(products))

    @staticmethod
    def load_sales(products):
        if not SALES_FILE.exists(): return []
        sales = []
        for line_no, line in enumerate(SALES_FILE.read_text(encoding="utf-8").splitlines(), 1):
            parts = line.split("|")
            try:
                if len(parts) != 7 or not parts[0] or not parts[1]: raise ValueError("Invalid sales record.")
                qty = int(parts[2]); unit = money(parts[3]); total = money(parts[4])
                datetime.strptime(parts[5] + " " + parts[6], "%Y-%m-%d %H:%M:%S")
                if str(qty) != parts[2] or qty <= 0 or unit <= 0 or total != money(unit * qty):
                    raise ValueError("Invalid quantity, price, or calculated total.")
                if parts[0] not in products: raise ValueError("Sale references an unknown product ID.")
                sales.append({"product_id":parts[0], "product_name":parts[1], "quantity":qty,
                              "unit_price":unit, "total":total, "date":parts[5], "time":parts[6]})
            except Exception as exc:
                raise ValueError(f"Invalid sales record on line {line_no}: {exc} File left unchanged.") from exc
        return sales

    @staticmethod
    def sales_text(sales):
        return "".join(f"{s['product_id']}|{s['product_name']}|{s['quantity']}|{s['unit_price']:.2f}|{s['total']:.2f}|{s['date']}|{s['time']}\n" for s in sales)

    @staticmethod
    def save_sales(sales): atomic_write(SALES_FILE, FileManager.sales_text(sales))


class Inventory:
    def __init__(self, category_manager):
        self.products = FileManager.load_products(category_manager.categories)
        self.category_manager = category_manager

    @staticmethod
    def get_number(message, minimum):
        while True:
            try:
                value = float(input(message))
                if not math.isfinite(value): raise ValueError
                value = money(value)
                if value < money(minimum):
                    print(f"Value must be at least {minimum}."); continue
                return value
            except (ValueError, InvalidOperation): print("Invalid input. Enter a finite number.")

    @staticmethod
    def get_integer(message, minimum):
        while True:
            raw = input(message).strip()
            try:
                if not raw or any(ch not in "0123456789" for ch in raw): raise ValueError
                value = int(raw)
                if value < minimum:
                    print(f"Quantity must be at least {minimum}."); continue
                return value
            except ValueError: print("Invalid input. Enter a whole-number quantity.")

    def add_product(self):
        print("\n--- ADD PRODUCT ---")
        product_id = input("Enter product ID: ").strip()
        if not product_id or "|" in product_id or product_id in self.products: print("Enter a valid, unused product ID."); return
        name = input("Enter product name: ").strip()
        if not name or "|" in name: print("Enter a valid product name."); return
        self.category_manager.view_categories()
        category = input("Enter category: ").strip()
        if category not in self.category_manager.categories: print("Invalid category. Create the category first."); return
        price = self.get_number("Enter selling price: ", 0.01)
        quantity = self.get_integer("Enter initial stock quantity: ", 0)
        product = Product(product_id, name, category, price, quantity)
        self.products[product_id] = product
        try: self.save()
        except Exception:
            del self.products[product_id]
            raise
        print("Product added successfully.")

    def view_products(self):
        print("\n--- PRODUCT INVENTORY ---")
        if not self.products: print("No products available."); return
        print("-" * 72); print(f"{'ID':<10}{'Name':<20}{'Category':<18}{'Price':>12}{'Quantity':>12}"); print("-" * 72)
        for product in self.products.values(): product.display()
        print("-" * 72)

    def stock_entry(self):
        print("\n--- STOCK ENTRY ---")
        product = self.products.get(input("Enter product ID: ").strip())
        if product is None: print("Product not found."); return
        quantity = self.get_integer("Enter quantity to add: ", 1)
        product.quantity += quantity
        try: self.save()
        except Exception:
            product.quantity -= quantity
            raise
        print("Stock updated successfully."); print("Available quantity:", product.quantity)

    def low_stock_report(self):
        print("\n--- LOW-STOCK REPORT ---")
        found = False
        for p in self.products.values():
            if p.quantity <= LOW_STOCK_LIMIT:
                print(f"{p.product_id} | {p.name} | Stock: {p.quantity}"); found = True
        if not found: print("No low-stock products.")

    def save(self): FileManager.save_products(self.products)


class Sales:
    def __init__(self, inventory):
        self.inventory = inventory
        self.records = FileManager.load_sales(inventory.products)

    def record_sale(self):
        print("\n--- SALES ENTRY ---")
        product = self.inventory.products.get(input("Enter product ID: ").strip())
        if product is None: print("Product not found."); return
        print("Product:", product.name); print(f"Price: Rs. {product.price:.2f}"); print("Available stock:", product.quantity)
        quantity = Inventory.get_integer("Enter quantity to sell: ", 1)
        if quantity > product.quantity: print("Insufficient stock. Sale cancelled."); return
        total = money(product.price * quantity); now = datetime.now()
        sale = {"product_id":product.product_id, "product_name":product.name, "quantity":quantity,
                "unit_price":product.price, "total":total, "date":now.strftime("%Y-%m-%d"), "time":now.strftime("%H:%M:%S")}
        old_quantity = product.quantity
        self.records.append(sale); product.quantity -= quantity
        try:
            atomic_many({PRODUCT_FILE:FileManager.product_text(self.inventory.products), SALES_FILE:FileManager.sales_text(self.records)})
        except Exception:
            product.quantity = old_quantity; self.records.pop()
            raise
        print("\nSale completed successfully!"); print("Product:", product.name); print("Quantity sold:", quantity)
        print(f"Total amount: Rs. {total:.2f}"); print("Remaining stock:", product.quantity)

    def revenue_report(self):
        revenue = sum((s["total"] for s in self.records), Decimal("0.00"))
        print("\n--- REVENUE REPORT ---"); print("Total sale entries:", len(self.records)); print(f"Total revenue: Rs. {revenue:.2f}")

    def product_sales_summary(self):
        print("\n--- PRODUCT-WISE SALES SUMMARY ---")
        if not self.records: print("No sales recorded."); return
        summary = {}
        for sale in self.records:
            item = summary.setdefault(sale["product_id"], {"name":sale["product_name"], "quantity":0, "revenue":Decimal("0.00")})
            item["quantity"] += sale["quantity"]; item["revenue"] += sale["total"]
        for data in summary.values(): print(f"{data['name']} | Quantity sold: {data['quantity']} | Revenue: Rs. {data['revenue']:.2f}")

    def daily_sales_summary(self):
        print("\n--- DAILY SALES SUMMARY ---")
        date = input("Enter date (YYYY-MM-DD), or press Enter for today: ").strip() or datetime.now().strftime("%Y-%m-%d")
        try: datetime.strptime(date, "%Y-%m-%d")
        except ValueError: print("Invalid date. Use YYYY-MM-DD."); return
        daily = [s for s in self.records if s["date"] == date]
        if not daily: print("No sales found for", date); return
        print("Date:", date); print("Sale entries:", len(daily)); print("Items sold:", sum(s["quantity"] for s in daily))
        print(f"Total revenue: Rs. {sum((s['total'] for s in daily), Decimal('0.00')):.2f}")
        for s in daily: print(f"{s['time']} | {s['product_name']} | Qty: {s['quantity']} | Amount: Rs. {s['total']:.2f}")


class RetailInventorySystem:
    def __init__(self):
        self.category_manager = CategoryManager()
        self.inventory = Inventory(self.category_manager)
        self.sales = Sales(self.inventory)

    def run(self):
        while True:
            print("\n" + "=" * 42); print(" RETAIL INVENTORY AND SALES SYSTEM"); print("=" * 42)
            for line in ("1. Add Product", "2. View Products", "3. Manage Categories", "4. Stock Entry", "5. Sales Entry", "6. Low-Stock Report", "7. Revenue Report", "8. Product-Wise Sales Summary", "9. Daily Sales Summary", "10. Exit"): print(line)
            print("=" * 42); choice = input("Enter your choice: ").strip()
            try:
                actions = {"1":self.inventory.add_product, "2":self.inventory.view_products, "3":self.category_menu,
                           "4":self.inventory.stock_entry, "5":self.sales.record_sale, "6":self.inventory.low_stock_report,
                           "7":self.sales.revenue_report, "8":self.sales.product_sales_summary, "9":self.sales.daily_sales_summary}
                if choice == "10": print("Thank you for using the system!"); break
                if choice in actions: actions[choice]()
                else: print("Invalid choice. Select 1-10.")
            except (OSError, ValueError) as error: print("Operation failed:", error)

    def category_menu(self):
        while True:
            print("\n--- CATEGORY MANAGEMENT ---\n1. Add Category\n2. View Categories\n3. Back")
            choice = input("Enter your choice: ").strip()
            if choice == "1": self.category_manager.add_category()
            elif choice == "2": self.category_manager.view_categories()
            elif choice == "3": break
            else: print("Invalid choice.")


if __name__ == "__main__":
    try: RetailInventorySystem().run()
    except (OSError, ValueError) as error: print("Unable to load required data:", error)
