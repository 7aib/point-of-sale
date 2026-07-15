from django.core.management.base import BaseCommand

from products.models import Category, Product


class Command(BaseCommand):
    help = "Seed the database with sample categories and products"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding categories...")
        categories = self._seed_categories()

        self.stdout.write("Seeding products...")
        self._seed_products(categories)

        self.stdout.write(self.style.SUCCESS("Done! Database seeded successfully."))

    def _seed_categories(self):
        data = {
            "Electronics": {
                "description": "Electronic devices and gadgets",
                "children": ["Smartphones", "Laptops", "Tablets", "Accessories"],
            },
            "Clothing": {
                "description": "Apparel and fashion items",
                "children": ["Men", "Women", "Kids", "Footwear"],
            },
            "Groceries": {
                "description": "Food and household essentials",
                "children": ["Fruits", "Vegetables", "Dairy", "Beverages"],
            },
            "Home & Kitchen": {
                "description": "Furniture and kitchen appliances",
                "children": ["Furniture", "Kitchen Appliances", "Decor", "Lighting"],
            },
            "Sports": {
                "description": "Sports equipment and accessories",
                "children": ["Cricket", "Football", "Gym Equipment", "Outdoor"],
            },
        }

        categories = {}
        for name, info in data.items():
            parent, _ = Category.objects.get_or_create(
                slug=name.lower().replace(" & ", "-").replace(" ", "-"),
                defaults={
                    "name": name,
                    "description": info["description"],
                    "is_active": True,
                },
            )
            categories[name] = parent

            for child_name in info["children"]:
                child, _ = Category.objects.get_or_create(
                    slug=child_name.lower().replace(" ", "-"),
                    defaults={
                        "name": child_name,
                        "parent": parent,
                        "is_active": True,
                    },
                )
                categories[child_name] = child

        self.stdout.write(f"  Created {len(categories)} categories")
        return categories

    def _seed_products(self, categories):
        products = [
            # Electronics > Smartphones
            {"name": "iPhone 15 Pro", "sku": "ELEC-SP-001", "barcode": "5901234123457", "category": "Smartphones",
             "cost_price": 85000, "selling_price": 119999, "stock_quantity": 25, "low_stock_threshold": 5,
             "description": "Apple iPhone 15 Pro, 256GB, Natural Titanium"},
            {"name": "Samsung Galaxy S24", "sku": "ELEC-SP-002", "barcode": "5901234123458", "category": "Smartphones",
             "cost_price": 72000, "selling_price": 99999, "stock_quantity": 30, "low_stock_threshold": 5,
             "description": "Samsung Galaxy S24 Ultra, 512GB, Phantom Black"},
            {"name": "OnePlus 12", "sku": "ELEC-SP-003", "barcode": "5901234123459", "category": "Smartphones",
             "cost_price": 55000, "selling_price": 74999, "stock_quantity": 15, "low_stock_threshold": 5,
             "description": "OnePlus 12, 256GB, Silky Black"},

            # Electronics > Laptops
            {"name": "MacBook Air M3", "sku": "ELEC-LP-001", "barcode": "5901234123460", "category": "Laptops",
             "cost_price": 145000, "selling_price": 189999, "stock_quantity": 10, "low_stock_threshold": 3,
             "description": "Apple MacBook Air 15-inch M3, 16GB RAM, 512GB SSD"},
            {"name": "Dell XPS 15", "sku": "ELEC-LP-002", "barcode": "5901234123461", "category": "Laptops",
             "cost_price": 120000, "selling_price": 159999, "stock_quantity": 8, "low_stock_threshold": 3,
             "description": "Dell XPS 15, Intel i7, 16GB RAM, 512GB SSD"},
            {"name": "HP Pavilion 14", "sku": "ELEC-LP-003", "barcode": "5901234123462", "category": "Laptops",
             "cost_price": 65000, "selling_price": 84999, "stock_quantity": 2, "low_stock_threshold": 3,
             "description": "HP Pavilion 14, Intel i5, 8GB RAM, 256GB SSD"},

            # Electronics > Tablets
            {"name": "iPad Air", "sku": "ELEC-TB-001", "barcode": "5901234123463", "category": "Tablets",
             "cost_price": 60000, "selling_price": 79999, "stock_quantity": 12, "low_stock_threshold": 4,
             "description": "Apple iPad Air M2, 64GB, Wi-Fi, Space Gray"},
            {"name": "Samsung Tab S9", "sku": "ELEC-TB-002", "barcode": "5901234123464", "category": "Tablets",
             "cost_price": 55000, "selling_price": 74999, "stock_quantity": 0, "low_stock_threshold": 4,
             "description": "Samsung Galaxy Tab S9 FE, 128GB, Graphite"},

            # Electronics > Accessories
            {"name": "AirPods Pro 2", "sku": "ELEC-AC-001", "barcode": "5901234123465", "category": "Accessories",
             "cost_price": 22000, "selling_price": 32999, "stock_quantity": 40, "low_stock_threshold": 10,
             "description": "Apple AirPods Pro 2nd Gen with USB-C"},
            {"name": "Samsung 45W Charger", "sku": "ELEC-AC-002", "barcode": "5901234123466", "category": "Accessories",
             "cost_price": 2500, "selling_price": 4999, "stock_quantity": 3, "low_stock_threshold": 10,
             "description": "Samsung 45W Super Fast Charger"},

            # Clothing > Men
            {"name": "Classic Polo Shirt", "sku": "CLT-M-001", "barcode": "5901234123467", "category": "Men",
             "cost_price": 800, "selling_price": 1999, "stock_quantity": 50, "low_stock_threshold": 15,
             "description": "Cotton polo shirt, available in multiple colors"},
            {"name": "Slim Fit Jeans", "sku": "CLT-M-002", "barcode": "5901234123468", "category": "Men",
             "cost_price": 1200, "selling_price": 2999, "stock_quantity": 35, "low_stock_threshold": 10,
             "description": "Slim fit denim jeans, stretch fabric"},

            # Clothing > Women
            {"name": "Floral Summer Dress", "sku": "CLT-W-001", "barcode": "5901234123469", "category": "Women",
             "cost_price": 1500, "selling_price": 3999, "stock_quantity": 20, "low_stock_threshold": 8,
             "description": "Lightweight floral print summer dress"},
            {"name": "High Waist Pants", "sku": "CLT-W-002", "barcode": "5901234123470", "category": "Women",
             "cost_price": 1100, "selling_price": 2799, "stock_quantity": 25, "low_stock_threshold": 8,
             "description": "High waist tailored trousers"},

            # Groceries > Fruits
            {"name": "Fresh Apples (1kg)", "sku": "GRC-F-001", "barcode": "5901234123471", "category": "Fruits",
             "cost_price": 120, "selling_price": 249, "stock_quantity": 100, "low_stock_threshold": 20,
             "description": "Fresh red apples, 1kg pack"},
            {"name": "Bananas (1 dozen)", "sku": "GRC-F-002", "barcode": "5901234123472", "category": "Fruits",
             "cost_price": 60, "selling_price": 149, "stock_quantity": 80, "low_stock_threshold": 20,
             "description": "Ripe bananas, 1 dozen"},

            # Groceries > Dairy
            {"name": "Milk (1 litre)", "sku": "GRC-D-001", "barcode": "5901234123473", "category": "Dairy",
             "cost_price": 80, "selling_price": 160, "stock_quantity": 60, "low_stock_threshold": 15,
             "description": "Fresh full cream milk, 1 litre"},
            {"name": "Cheddar Cheese (250g)", "sku": "GRC-D-002", "barcode": "5901234123474", "category": "Dairy",
             "cost_price": 200, "selling_price": 449, "stock_quantity": 0, "low_stock_threshold": 10,
             "description": "Processed cheddar cheese block, 250g"},

            # Groceries > Beverages
            {"name": "Coca-Cola (1.5L)", "sku": "GRC-B-001", "barcode": "5901234123475", "category": "Beverages",
             "cost_price": 50, "selling_price": 120, "stock_quantity": 120, "low_stock_threshold": 30,
             "description": "Coca-Cola carbonated soft drink, 1.5 litre"},
            {"name": "Green Tea (25 bags)", "sku": "GRC-B-002", "barcode": "5901234123476", "category": "Beverages",
             "cost_price": 150, "selling_price": 349, "stock_quantity": 45, "low_stock_threshold": 15,
             "description": "Green tea bags, anti-oxidant, 25 count"},

            # Home & Kitchen > Kitchen Appliances
            {"name": "Blender Pro 1000", "sku": "HK-KA-001", "barcode": "5901234123477", "category": "Kitchen Appliances",
             "cost_price": 5000, "selling_price": 8999, "stock_quantity": 12, "low_stock_threshold": 4,
             "description": "1000W blender with multiple speed settings"},
            {"name": "Air Fryer XL", "sku": "HK-KA-002", "barcode": "5901234123478", "category": "Kitchen Appliances",
             "cost_price": 8000, "selling_price": 14999, "stock_quantity": 7, "low_stock_threshold": 3,
             "description": "6L air fryer with digital display"},

            # Sports > Cricket
            {"name": "Kashmir Willow Bat", "sku": "SPT-C-001", "barcode": "5901234123479", "category": "Cricket",
             "cost_price": 2000, "selling_price": 4499, "stock_quantity": 18, "low_stock_threshold": 5,
             "description": "Kashmir willow cricket bat, full size"},
            {"name": "Cricket Kit Set", "sku": "SPT-C-002", "barcode": "5901234123480", "category": "Cricket",
             "cost_price": 5000, "selling_price": 9999, "stock_quantity": 0, "low_stock_threshold": 3,
             "description": "Complete cricket kit with pads, gloves, helmet"},

            # Sports > Gym Equipment
            {"name": "Adjustable Dumbbells", "sku": "SPT-G-001", "barcode": "5901234123481", "category": "Gym Equipment",
             "cost_price": 8000, "selling_price": 14999, "stock_quantity": 6, "low_stock_threshold": 3,
             "description": "Adjustable dumbbells 2.5kg to 25kg pair"},
            {"name": "Yoga Mat Premium", "sku": "SPT-G-002", "barcode": "5901234123482", "category": "Gym Equipment",
             "cost_price": 800, "selling_price": 1999, "stock_quantity": 2, "low_stock_threshold": 5,
             "description": "Non-slip premium yoga mat, 6mm thick"},
        ]

        count = 0
        for p in products:
            category = categories.get(p["category"])
            if not category:
                continue
            obj, created = Product.objects.get_or_create(
                sku=p["sku"],
                defaults={
                    "name": p["name"],
                    "barcode": p["barcode"],
                    "category": category,
                    "cost_price": p["cost_price"],
                    "selling_price": p["selling_price"],
                    "stock_quantity": p["stock_quantity"],
                    "low_stock_threshold": p["low_stock_threshold"],
                    "description": p["description"],
                    "is_active": True,
                },
            )
            if created:
                count += 1

        self.stdout.write(f"  Created {count} products")
