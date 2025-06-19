import json
import os
import csv
from datetime import datetime
from enum import Enum
import uuid
from typing import Dict, List, Union, Optional
import tkinter as tk
from tkinter import ttk, messagebox


# Enum for product types
class ProductType(Enum):
    PHYSICAL = "physical"
    DIGITAL = "digital"


# Custom exception for inventory management
class InventoryError(Exception):
    pass


class Product:
    def __init__(self, product_id: str, name: str, price: float, quantity_available: int):
        self._product_id = product_id
        self._name = name
        self._price = price
        self._quantity_available = max(0, quantity_available)

    @property
    def product_id(self) -> str:
        return self._product_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def price(self) -> float:
        return self._price

    @property
    def quantity_available(self) -> int:
        return self._quantity_available

    @quantity_available.setter
    def quantity_available(self, value: int):
        if value < 0:
            raise ValueError("Quantity cannot be negative")
        self._quantity_available = value

    def decrease_quantity(self, amount: int) -> bool:
        if amount <= 0:
            return False
        if self._quantity_available < amount:
            return False
        self._quantity_available -= amount
        return True

    def increase_quantity(self, amount: int):
        if amount <= 0:
            raise ValueError("Amount must be positive")
        self._quantity_available += amount

    def display_details(self) -> str:
        return (f"ID: {self._product_id}\n"
                f"Name: {self._name}\n"
                f"Price: ₹{self._price:,.2f}\n"
                f"Available: {self._quantity_available}")

    def to_dict(self) -> dict:
        return {
            "type": "generic",
            "product_id": self._product_id,
            "name": self._name,
            "price": self._price,
            "quantity_available": self._quantity_available
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Product':
        ptype = data.get("type", "generic")
        if ptype == ProductType.PHYSICAL.value:
            return PhysicalProduct.from_dict(data)
        elif ptype == ProductType.DIGITAL.value:
            return DigitalProduct.from_dict(data)
        else:
            return cls(
                data["product_id"],
                data["name"],
                data["price"],
                data["quantity_available"]
            )


class PhysicalProduct(Product):
    def __init__(self, product_id: str, name: str, price: float, quantity_available: int, weight: float):
        super().__init__(product_id, name, price, quantity_available)
        self._weight = weight

    @property
    def weight(self) -> float:
        return self._weight

    def display_details(self) -> str:
        base_details = super().display_details()
        return f"{base_details}\nWeight: {self._weight} kg\nType: Physical Product"

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({"type": ProductType.PHYSICAL.value, "weight": self._weight})
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'PhysicalProduct':
        return cls(
            data["product_id"],
            data["name"],
            data["price"],
            data["quantity_available"],
            data["weight"]
        )


class DigitalProduct(Product):
    def __init__(self, product_id: str, name: str, price: float, quantity_available: int, download_link: str):
        super().__init__(product_id, name, price, quantity_available)
        self._download_link = download_link

    @property
    def download_link(self) -> str:
        return self._download_link

    def display_details(self) -> str:
        base_details = super().display_details()
        return f"{base_details}\nDownload: {self._download_link}\nType: Digital Product"

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({"type": ProductType.DIGITAL.value, "download_link": self._download_link})
        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'DigitalProduct':
        return cls(
            data["product_id"],
            data["name"],
            data["price"],
            data["quantity_available"],
            data["download_link"]
        )


class CartItem:
    def __init__(self, product: Product, quantity: int):
        self._product = product
        self._quantity = max(0, quantity)

    @property
    def product(self) -> Product:
        return self._product

    @property
    def quantity(self) -> int:
        return self._quantity

    @quantity.setter
    def quantity(self, value: int):
        if value < 0:
            raise ValueError("Quantity cannot be negative")
        self._quantity = value

    def calculate_subtotal(self) -> float:
        return self._product.price * self._quantity

    def __str__(self) -> str:
        return (f"Item: {self._product.name}, Quantity: {self._quantity}, "
                f"Price: ₹{self._product.price:,.2f}, Subtotal: ₹{self.calculate_subtotal():,.2f}")

    def to_dict(self) -> dict:
        return {"product_id": self._product.product_id, "quantity": self._quantity}


class ShoppingCart:
    def __init__(self, product_catalog_file='product_catalog.json',
                 cart_state_file='cart_state.json',
                 transaction_log_file='transactions.csv'):
        self._items: Dict[str, CartItem] = {}
        self._product_catalog_file = product_catalog_file
        self._cart_state_file = cart_state_file
        self._transaction_log_file = transaction_log_file
        self._product_catalog: Dict[str, Product] = {}
        self._initialize_files()
        self._load_catalog()
        self._load_cart_state()
        self._init_transaction_log()

    def _initialize_files(self):
        # Create directories if they don't exist
        for file_path in [self._product_catalog_file, self._cart_state_file, self._transaction_log_file]:
            dir_path = os.path.dirname(file_path)
            if dir_path and not os.path.exists(dir_path):
                os.makedirs(dir_path)

        # Initialize files if they don't exist
        if not os.path.exists(self._product_catalog_file):
            with open(self._product_catalog_file, 'w') as f:
                json.dump([], f)
        if not os.path.exists(self._cart_state_file):
            with open(self._cart_state_file, 'w') as f:
                json.dump([], f)
        if not os.path.exists(self._transaction_log_file):
            with open(self._transaction_log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "action", "product_id", "product_name", "quantity", "details"])

    def _init_transaction_log(self):
        if os.path.exists(self._transaction_log_file) and os.stat(self._transaction_log_file).st_size == 0:
            with open(self._transaction_log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "action", "product_id", "product_name", "quantity", "details"])

    def _log_transaction(self, action, product_id, product_name, quantity, details=""):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self._transaction_log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, action, product_id, product_name, quantity, details])

    def _load_catalog(self) -> Dict[str, Product]:
        try:
            with open(self._product_catalog_file, 'r') as f:
                data = json.load(f)
                self._product_catalog = {}
                for item in data:
                    try:
                        product = Product.from_dict(item)
                        self._product_catalog[product.product_id] = product
                    except (KeyError, ValueError) as e:
                        print(f"Error loading product: {e}")
                        continue
            return self._product_catalog
        except (FileNotFoundError, json.JSONDecodeError):
            self._product_catalog = {}
            return {}

    def _load_cart_state(self):
        try:
            with open(self._cart_state_file, 'r') as f:
                cart_data = json.load(f)
                self._items = {}
                for item in cart_data:
                    try:
                        product_id = item["product_id"]
                        quantity = item["quantity"]
                        if product_id in self._product_catalog:
                            product = self._product_catalog[product_id]
                            self._items[product_id] = CartItem(product, quantity)
                    except (KeyError, ValueError) as e:
                        print(f"Error loading cart item: {e}")
                        continue
        except (FileNotFoundError, json.JSONDecodeError):
            self._items = {}

    def _save_catalog(self):
        data = [product.to_dict() for product in self._product_catalog.values()]
        with open(self._product_catalog_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _save_cart_state(self):
        data = [item.to_dict() for item in self._items.values()]
        with open(self._cart_state_file, 'w') as f:
            json.dump(data, f, indent=2)

    def add_item(self, product_id: str, quantity: int) -> bool:
        if product_id not in self._product_catalog:
            return False
        product = self._product_catalog[product_id]
        if quantity <= 0:
            return False
        if product.quantity_available < quantity:
            raise InventoryError(f"Insufficient stock for {product.name}. Available: {product.quantity_available}")

        if not product.decrease_quantity(quantity):
            return False

        if product_id in self._items:
            self._items[product_id].quantity += quantity
        else:
            self._items[product_id] = CartItem(product, quantity)

        self._save_catalog()
        self._save_cart_state()
        self._log_transaction("ADD", product_id, product.name, quantity)
        return True

    def remove_item(self, product_id: str) -> bool:
        if product_id not in self._items:
            return False
        cart_item = self._items[product_id]
        product = cart_item.product
        product.increase_quantity(cart_item.quantity)
        del self._items[product_id]
        self._save_catalog()
        self._save_cart_state()
        self._log_transaction("REMOVE", product_id, product.name, cart_item.quantity)
        return True

    def get_total(self) -> float:
        return sum(item.calculate_subtotal() for item in self._items.values())

    def initialize_sample_catalog(self):
        if self._product_catalog:
            return
        products = [
            PhysicalProduct("001A", "Tata Salt 1kg", 28.0, 100, 1.0),
            PhysicalProduct("002A", "Amul Butter 100g", 50.0, 50, 0.1),
            DigitalProduct("006A", "Bollywood Movie - Sholay", 99.0, 1000, "https://store.example.com/download/sholay"),
            DigitalProduct("007A", "Hindi Learning Course", 799.0, 500, "https://courses.example.com/hindi-basic")
        ]
        self._product_catalog = {p.product_id: p for p in products}
        self._save_catalog()


class ShoppingCartGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Indian Online Bazaar - Shopping Cart")
        self.root.geometry("800x600")
        self.cart = ShoppingCart()
        self.cart.initialize_sample_catalog()

        # Main container
        main_frame = tk.Frame(root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Products frame
        products_frame = tk.LabelFrame(main_frame, text="Available Products")
        products_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # Treeview with scrollbars
        tree_frame = tk.Frame(products_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Vertical scrollbar
        y_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Horizontal scrollbar
        x_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.product_tree = ttk.Treeview(tree_frame, columns=("ID", "Name", "Price", "Qty"),
                                         show="headings", yscrollcommand=y_scroll.set,
                                         xscrollcommand=x_scroll.set)
        self.product_tree.pack(fill=tk.BOTH, expand=True)

        # Configure scrollbars
        y_scroll.config(command=self.product_tree.yview)
        x_scroll.config(command=self.product_tree.xview)

        # Configure tree columns
        self.product_tree.heading("ID", text="Product ID")
        self.product_tree.heading("Name", text="Name")
        self.product_tree.heading("Price", text="Price (₹)")
        self.product_tree.heading("Qty", text="Available Qty")

        self.product_tree.column("ID", width=100, anchor=tk.CENTER)
        self.product_tree.column("Name", width=200, anchor=tk.W)
        self.product_tree.column("Price", width=100, anchor=tk.E)
        self.product_tree.column("Qty", width=100, anchor=tk.CENTER)

        self.load_products()

        # Control frame
        control_frame = tk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=5)

        # Product ID entry
        tk.Label(control_frame, text="Product ID:").pack(side=tk.LEFT, padx=5)
        self.product_id_entry = tk.Entry(control_frame, width=15)
        self.product_id_entry.pack(side=tk.LEFT, padx=5)

        # Quantity entry
        tk.Label(control_frame, text="Quantity:").pack(side=tk.LEFT, padx=5)
        self.quantity_entry = tk.Entry(control_frame, width=5)
        self.quantity_entry.pack(side=tk.LEFT, padx=5)

        # Buttons
        tk.Button(control_frame, text="Add to Cart", command=self.add_to_cart).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="View Cart", command=self.view_cart).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Checkout", command=self.checkout).pack(side=tk.LEFT, padx=5)
        tk.Button(control_frame, text="Exit", command=self.root.quit).pack(side=tk.RIGHT, padx=5)

    def load_products(self):
        for row in self.product_tree.get_children():
            self.product_tree.delete(row)
        for p in self.cart._product_catalog.values():
            self.product_tree.insert("", tk.END, values=(
                p.product_id,
                p.name,
                f"{p.price:,.2f}",
                p.quantity_available
            ))

    def add_to_cart(self):
        pid = self.product_id_entry.get().strip()
        qty_str = self.quantity_entry.get().strip()

        if not pid or not qty_str:
            messagebox.showerror("Error", "Please enter both Product ID and Quantity")
            return

        try:
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError("Quantity must be positive")

            success = self.cart.add_item(pid, qty)
            if success:
                messagebox.showinfo("Success", f"Added {qty} of {pid} to cart")
                self.load_products()
                self.product_id_entry.delete(0, tk.END)
                self.quantity_entry.delete(0, tk.END)
            else:
                messagebox.showerror("Error", "Product ID not found or invalid quantity")
        except ValueError as ve:
            messagebox.showerror("Invalid Input", str(ve))
        except InventoryError as ie:
            messagebox.showerror("Inventory Error", str(ie))

    def view_cart(self):
        if not self.cart._items:
            messagebox.showinfo("Cart", "Your cart is empty.")
            return

        cart_win = tk.Toplevel(self.root)
        cart_win.title("Your Shopping Cart")
        cart_win.geometry("500x400")

        # Frame for cart items
        items_frame = tk.Frame(cart_win)
        items_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Scrollable text widget
        scrollbar = tk.Scrollbar(items_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        cart_text = tk.Text(items_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
        cart_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=cart_text.yview)

        # Add cart items to text widget
        for item in self.cart._items.values():
            cart_text.insert(tk.END, f"{item}\n")

        # Add total
        cart_text.insert(tk.END, f"\n{'=' * 50}\n")
        cart_text.insert(tk.END, f"Total: ₹{self.cart.get_total():,.2f}")
        cart_text.config(state=tk.DISABLED)  # Make it read-only

        # Buttons frame
        buttons_frame = tk.Frame(cart_win)
        buttons_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Button(buttons_frame, text="Close", command=cart_win.destroy).pack(side=tk.RIGHT)

    def checkout(self):
        total = self.cart.get_total()
        if total > 0:
            response = messagebox.askyesno(
                "Confirm Checkout",
                f"Total amount: ₹{total:,.2f}\nProceed with checkout?"
            )
            if response:
                self.cart._items = {}
                self.cart._save_cart_state()
                messagebox.showinfo(
                    "Checkout Complete",
                    f"Thank you for your purchase!\nTotal: ₹{total:,.2f}"
                )
                self.load_products()
        else:
            messagebox.showinfo("Cart Empty", "Your cart is empty. Please add items before checkout.")


if __name__ == "__main__":
    root = tk.Tk()
    app = ShoppingCartGUI(root)
    root.mainloop()