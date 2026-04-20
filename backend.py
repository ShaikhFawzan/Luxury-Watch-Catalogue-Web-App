from enum import Enum
from werkzeug.security import check_password_hash



# Keeps the user roles clear and easy to check.
class Role(Enum):
    GUEST = "GUEST"
    USER = "USER"
    ADMIN = "ADMIN"


# Represents one watch in the catalogue.
class Watch:
    def __init__(self, watch_id, name, brand, price, material,
                 reference, condition, image_url):
        self.watch_id = watch_id
        self.name = name
        self.brand = brand
        self.price = price
        self.material = material
        self.reference = reference
        self.condition = condition
        self.image_url = image_url

    def get_details(self):
        return {
            "watch_id": self.watch_id,
            "name": self.name,
            "brand": self.brand,
            "price": self.price,
            "material": self.material,
            "reference": self.reference,
            "condition": self.condition,
            "image_url": self.image_url,
        }

    def __str__(self):
        return f"{self.watch_id} - {self.name} ({self.brand}) - ${self.price}"


# Base user class.

class User:
    def __init__(self, user_id, username, password_hash, role=Role.USER, wishlist=None):
        self.user_id = user_id
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.logged_in = False
        self.wishlist = wishlist if wishlist is not None else []

    def login(self, username, password):
        if self.username == username and check_password_hash(self.password_hash, password):
            self.logged_in = True
            return True
        return False

    def logout(self):
        self.logged_in = False

    def is_logged_in(self):
        return self.logged_in


# Admin can do extra actions like adding watches.
class Admin(User):
    def __init__(self, user_id, username, password_hash, wishlist=None):
        super().__init__(user_id, username, password_hash, Role.ADMIN, wishlist)

    def add_watch(self, watch, catalogue):
        if not self.logged_in:
            raise PermissionError("Admin must be logged in before adding a watch.")
        catalogue.add_watch(watch)

    def edit_watch(self, watch_id, catalogue, **kwargs):
        if not self.logged_in:
            raise PermissionError("Admin must be logged in before editing a watch.")
        catalogue.edit_watch(watch_id, **kwargs)

    def delete_watch(self, watch_id, catalogue):
        if not self.logged_in:
            raise PermissionError("Admin must be logged in before deleting a watch.")
        catalogue.delete_watch(watch_id)


# Stores all watches.
class Catalogue:
    def __init__(self):
        self.watches = []

    def add_watch(self, watch):
        if watch.watch_id < 0:
            raise ValueError(f"Watch ID cannot be negative.")

        for existing_watch in self.watches:
            if existing_watch.watch_id == watch.watch_id:
                raise ValueError(f"Watch with ID {watch.watch_id} already exists.")
        self.watches.append(watch)

    def edit_watch(self, watch_id, **kwargs):
        for watch in self.watches:
            if watch.watch_id == watch_id:
                for key, value in kwargs.items():
                    if hasattr(watch, key):
                        setattr(watch, key, value)
                return watch
        raise ValueError(f"Watch with ID {watch_id} not found.")

    def delete_watch(self, watch_id):
        for i, watch in enumerate(self.watches):
            if watch.watch_id == watch_id:
                return self.watches.pop(i)
        raise ValueError(f"Watch with ID {watch_id} not found.")

    def get_watch(self, watch_id):
        for watch in self.watches:
            if watch.watch_id == watch_id:
                return watch
        return None

    def get_all_watches(self):
        return self.watches

    def search_watches(self, query):
        query = query.lower()
        return [w for w in self.watches if
                query in w.name.lower() or
                query in w.brand.lower() or
                query in w.reference.lower()]

    def filter_watches(self, brand=None, min_price=None, max_price=None,
                       material=None, condition=None):
        results = self.watches
        if brand:
            results = [w for w in results if w.brand.lower() == brand.lower()]
        if min_price is not None:
            results = [w for w in results if w.price >= min_price]
        if max_price is not None:
            results = [w for w in results if w.price <= max_price]
        if material:
            results = [w for w in results if w.material.lower() == material.lower()]
        if condition:
            results = [w for w in results if w.condition.lower() == condition.lower()]
        return results


class Review:
    def __init__(self, review_id, watch_id, username, rating, title, body, timestamp):
        self.review_id = review_id
        self.watch_id = watch_id
        self.username = username
        self.rating = rating        # int 1–5
        self.title = title
        self.body = body
        self.timestamp = timestamp  # ISO string

    def to_dict(self):
        return {
            "review_id": self.review_id,
            "watch_id": self.watch_id,
            "username": self.username,
            "rating": self.rating,
            "title": self.title,
            "body": self.body,
            "timestamp": self.timestamp,
        }