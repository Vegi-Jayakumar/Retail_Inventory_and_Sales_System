# Retail Inventory and Sales System

A command-line Python application for managing product inventory, categories, stock entries, and sales. It also provides low-stock, revenue, product-wise, and daily sales reports.

## Requirements

- Python 3.8 or later
- No third-party packages are required

## Run the application

Open a terminal in the project directory and run:

```powershell
python RISS.py
```

On systems where Python is invoked as `python3`:

```bash
python3 RISS.py
```

## Menu

1. Add a product
2. View products
3. Manage categories
4. Add stock to a product
5. Record a sale
6. View the low-stock report
7. View total revenue
8. View product-wise sales
9. View sales for a date
10. Exit

Create categories before adding products. Each product needs a unique ID, name, category, selling price, and initial stock quantity.

## Data files

The application stores its text files in a `Data` folder beside `RISS.py`. It creates this folder when needed. The files are:

- `Data/categories.txt` — one category per line
- `Data/products.txt` — product records
- `Data/sales.txt` — sales records

Keep the files in this format if editing them manually. The application validates loaded records at startup and stops with an error if it finds malformed data, duplicate product IDs, unknown product categories, invalid values, or inconsistent sale totals. Correct the affected file before running the application again.

Writes use temporary files and replacement. If a sale cannot be saved, the application restores the previous stock and sales state. Prices are finite and stored to two decimal places (rounded half up); quantities must be whole numbers. Initial stock can be zero, while restock and sale quantities must be positive.
