import json
import os
import csv
from datetime import datetime
from enum import Enum
import uuid
from typing import Dict, List, Union, Optional

# Enum for product types
class ProductType(Enum):
    PHYSICAL = "physical"
    DIGITAL = "digital"

# Custom exception for inventory management
class InventoryError(Exception):
    pass

class Product:
    """Base class for all products"""
    def __init__(self, product_id: str, name: str, price: float, quantity_available: int):
        self._product_id = product_id
        self._name = name
        self._price = price
        self._quantity_available = max(0, quantity_available)  # Ensure non-negative

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
    """Physical product with weight attribute"""
    def __init__(self, product_id: str, name: str, price: float, 
                 quantity_available: int, weight: float):
        super().__init__(product_id, name, price, quantity_available)
        self._weight = weight  # in kilograms

    @property
    def weight(self) -> float:
        return self._weight

    def display_details(self) -> str:
        base_details = super().display_details()
        return f"{base_details}\nWeight: {self._weight} kg\nType: Physical Product"

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "type": ProductType.PHYSICAL.value,
            "weight": self._weight
        })
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
    """Digital product with download link"""
    def __init__(self, product_id: str, name: str, price: float, 
                 quantity_available: int, download_link: str):
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
        data.update({
            "type": ProductType.DIGITAL.value,
            "download_link": self._download_link
        })
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
    """Represents an item in the shopping cart"""
    def __init__(self, product: Product, quantity: int):
        self._product = product
        self._quantity = max(0, quantity)  # Ensure non-negative

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
        return (f"Item: {self._product.name}, "
                f"Quantity: {self._quantity}, "
                f"Price: ₹{self._product.price:,.2f}, "
                f"Subtotal: ₹{self.calculate_subtotal():,.2f}")

    def to_dict(self) -> dict:
        return {
            "product_id": self._product.product_id,
            "quantity": self._quantity
        }


class ShoppingCart:
    """Manages shopping cart operations and persistence"""
    def __init__(self, 
                 product_catalog_file: str = 'product_catalog.json',
                 cart_state_file: str = 'cart_state.json',
                 transaction_log_file: str = 'transactions.csv'):
        self._items: Dict[str, CartItem] = {}
        self._product_catalog_file = product_catalog_file
        self._cart_state_file = cart_state_file
        self._transaction_log_file = transaction_log_file
        self._product_catalog: Dict[str, Product] = {}
        
        # Initialize files if they don't exist
        self._initialize_files()
        
        # Load data
        self._load_catalog()
        self._load_cart_state()
        
        # Initialize transaction log
        self._init_transaction_log()

    def _initialize_files(self):
        """Create necessary files if they don't exist"""
        if not os.path.exists(self._product_catalog_file):
            with open(self._product_catalog_file, 'w') as f:
                json.dump([], f)
                
        if not os.path.exists(self._cart_state_file):
            with open(self._cart_state_file, 'w') as f:
                json.dump([], f)
                
        if not os.path.exists(self._transaction_log_file):
            with open(self._transaction_log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "action", "product_id", 
                                "product_name", "quantity", "details"])

    def _init_transaction_log(self):
        """Initialize transaction log with header if needed"""
        if os.path.exists(self._transaction_log_file) and os.stat(self._transaction_log_file).st_size == 0:
            with open(self._transaction_log_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "action", "product_id", 
                                "product_name", "quantity", "details"])

    def _log_transaction(self, action: str, product_id: str, 
                        product_name: str, quantity: int, details: str = ""):
        """Log a transaction to CSV file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self._transaction_log_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, action, product_id, 
                            product_name, quantity, details])

    def _load_catalog(self) -> Dict[str, Product]:
        """Load product catalog from JSON file"""
        try:
            with open(self._product_catalog_file, 'r') as f:
                data = json.load(f)
                self._product_catalog = {}
                for item in data:
                    product = Product.from_dict(item)
                    self._product_catalog[product.product_id] = product
            return self._product_catalog
        except (FileNotFoundError, json.JSONDecodeError):
            # Return empty catalog if file not found or invalid
            self._product_catalog = {}
            return {}

    def _load_cart_state(self):
        """Load cart state from JSON file"""
        try:
            with open(self._cart_state_file, 'r') as f:
                cart_data = json.load(f)
                self._items = {}
                for item in cart_data:
                    product_id = item["product_id"]
                    quantity = item["quantity"]
                    if product_id in self._product_catalog:
                        product = self._product_catalog[product_id]
                        self._items[product_id] = CartItem(product, quantity)
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            # Start with empty cart if there's an issue
            self._items = {}

    def _save_catalog(self):
        """Save product catalog to JSON file"""
        data = [product.to_dict() for product in self._product_catalog.values()]
        with open(self._product_catalog_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _save_cart_state(self):
        """Save cart state to JSON file"""
        data = [item.to_dict() for item in self._items.values()]
        with open(self._cart_state_file, 'w') as f:
            json.dump(data, f, indent=2)

    def add_item(self, product_id: str, quantity: int) -> bool:
        """Add item to cart with inventory validation"""
        if product_id not in self._product_catalog:
            return False
            
        product = self._product_catalog[product_id]
        
        if quantity <= 0:
            return False
            
        if product.quantity_available < quantity:
            raise InventoryError(f"Insufficient stock for {product.name}. Available: {product.quantity_available}")
        
        # Update product quantity
        product.decrease_quantity(quantity)
        
        # Add to cart
        if product_id in self._items:
            self._items[product_id].quantity += quantity
        else:
            self._items[product_id] = CartItem(product, quantity)
        
        # Save state
        self._save_catalog()
        self._save_cart_state()
        
        # Log transaction
        self._log_transaction("ADD", product_id, product.name, quantity)
        
        return True

    def remove_item(self, product_id: str) -> bool:
        """Remove item from cart and return stock"""
        if product_id not in self._items:
            return False
            
        cart_item = self._items[product_id]
        product = cart_item.product
        
        # Return stock
        product.increase_quantity(cart_item.quantity)
        
        # Remove from cart
        del self._items[product_id]
        
        # Save state
        self._save_catalog()
        self._save_cart_state()
        
        # Log transaction
        self._log_transaction("REMOVE", product_id, product.name, cart_item.quantity)
        
        return True

    def update_quantity(self, product_id: str, new_quantity: int) -> bool:
        """Update item quantity with inventory validation"""
        if product_id not in self._items:
            return False
            
        cart_item = self._items[product_id]
        product = cart_item.product
        current_quantity = cart_item.quantity
        
        if new_quantity < 0:
            return False
            
        if new_quantity == current_quantity:
            return True  # No change needed
            
        # Calculate quantity difference
        diff = new_quantity - current_quantity
        
        if diff > 0:  # Increasing quantity
            if product.quantity_available < diff:
                raise InventoryError(f"Insufficient stock for {product.name}. Available: {product.quantity_available}")
            product.decrease_quantity(diff)
        else:  # Decreasing quantity (diff is negative)
            product.increase_quantity(-diff)
        
        # Update cart
        cart_item.quantity = new_quantity
        
        # If quantity becomes zero, remove item
        if new_quantity == 0:
            del self._items[product_id]
        
        # Save state
        self._save_catalog()
        self._save_cart_state()
        
        # Log transaction
        action = "UPDATE"
        self._log_transaction(action, product_id, product.name, new_quantity, 
                             f"Previous quantity: {current_quantity}")
        
        return True

    def get_total(self) -> float:
        """Calculate grand total of all items in cart"""
        return sum(item.calculate_subtotal() for item in self._items.values())

    def display_cart(self):
        """Display cart contents with formatting"""
        if not self._items:
            print("Your shopping cart is empty.")
            return
            
        print("\n🛒 Your Shopping Cart:")
        print("-" * 60)
        for item in self._items.values():
            print(f"• {item}")
        print("-" * 60)
        print(f"GRAND TOTAL: ₹{self.get_total():,.2f}")
        print("-" * 60)

    def display_products(self):
        """Display available products with Indian context"""
        if not self._product_catalog:
            print("No products available at the moment.")
            return
            
        print("\n📦 Available Products:")
        for product in self._product_catalog.values():
            print("\n" + product.display_details())
            print("─" * 40)

    def get_product(self, product_id: str) -> Optional[Product]:
        """Get product by ID"""
        return self._product_catalog.get(product_id)

    def initialize_sample_catalog(self):
        """Initialize with sample Indian products"""
        if self._product_catalog:
            return  # Don't reinitialize if catalog exists
            
        products = [
            PhysicalProduct("001A", "Tata Salt 1kg", 28.0, 100, 1.0),
            PhysicalProduct("002A", "Amul Butter 100g", 50.0, 50, 0.1),
            PhysicalProduct("003A", "Parle-G Biscuits 100g", 10.0, 200, 0.1),
            PhysicalProduct("004A", "Maggi Noodles 70g", 12.0, 150, 0.07),
            PhysicalProduct("005A", "Dettol Soap 75g", 35.0, 80, 0.075),
            DigitalProduct("006A", "Bollywood Movie - Sholay", 99.0, 1000,
                          "https://store.example.com/download/sholay"),
            DigitalProduct("007A", "Hindi Learning Course", 799.0, 500,
                          "https://courses.example.com/hindi-basic"),
            DigitalProduct("007A", "Indian Classical Music Collection", 249.0, 300,
                          "https://music.example.com/classical-indian"),
            DigitalProduct("009A", "Yoga for Beginners", 499.0, 200,
                          "https://fitness.example.com/yoga-course")
        ]
        
        self._product_catalog = {p.product_id: p for p in products}
        self._save_catalog()


# Console Interface
def display_menu():
    print("\n🛍️  INDIAN ONLINE BAZAAR")
    print("1. View Products")
    print("2. Add Item to Cart")
    print("3. View Cart")
    print("4. Update Item Quantity")
    print("5. Remove Item from Cart")
    print("6. Checkout")
    print("7. Exit")


def main():
    cart = ShoppingCart()
    cart.initialize_sample_catalog()  # Initialize with sample products
    
    while True:
        display_menu()
        choice = input("\nEnter your choice: ")
        
        try:
            if choice == '1':
                cart.display_products()
                
            elif choice == '2':
                cart.display_products()
                product_id = input("Enter product ID: ").strip()
                quantity = int(input("Enter quantity: "))
                
                if quantity <= 0:
                    print("Quantity must be positive!")
                    continue
                    
                if cart.add_item(product_id, quantity):
                    print(f"✅ Added {quantity} item(s) to your cart")
                else:
                    print("❌ Failed to add item. Check product ID.")
            
            elif choice == '3':
                cart.display_cart()
            
            elif choice == '4':
                cart.display_cart()
                if not cart._items:
                    continue
                    
                product_id = input("Enter product ID to update: ").strip()
                new_quantity = int(input("Enter new quantity: "))
                
                if cart.update_quantity(product_id, new_quantity):
                    print("✅ Cart updated successfully")
                else:
                    print("❌ Product not found in cart")
            
            elif choice == '5':
                cart.display_cart()
                if not cart._items:
                    continue
                    
                product_id = input("Enter product ID to remove: ").strip()
                if cart.remove_item(product_id):
                    print("✅ Item removed from cart")
                else:
                    print("❌ Product not found in cart")
            
            elif choice == '6':
                total = cart.get_total()
                if total > 0:
                    print(f"\n💳 Checkout Complete! Total: ₹{total:,.2f}")
                    print("Thank you for shopping with us!")
                    # Clear cart after checkout
                    cart._items = {}
                    cart._save_cart_state()
                else:
                    print("Your cart is empty. Add items before checkout.")
            
            elif choice == '7':
                print("Thank you for shopping with us. Have a great day!")
                break
            
            else:
                print("Invalid choice. Please try again.")
        
        except ValueError:
            print("Invalid input. Please enter a valid number.")
        except InventoryError as e:
            print(f"⚠️ Inventory Error: {e}")


if __name__ == "__main__":
    main()