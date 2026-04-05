import csv
import os
import re
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from backend import Role, Watch, User, Admin, Catalogue, SessionManager

app = Flask(__name__)
app.secret_key = "watch-catalogue-secret-key"

# Backend setup
catalogue = Catalogue()
users = {}


def load_watches_from_csv(filepath):
    """Load watches from the luxury watches CSV dataset."""
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            try:
                price = float(row.get("price", "0"))
            except ValueError:
                price = 0.0

            watch_id_value = row.get("watch_id")
            if watch_id_value is not None and watch_id_value.strip() != "":
                try:
                    watch_id = int(watch_id_value)
                except ValueError:
                    watch_id = i
            else:
                watch_id = i

            watch = Watch(
                watch_id=watch_id,
                name=row.get("name", "").strip(),
                brand=row.get("brand", "").strip(),
                price=price,
                material=row.get("material", "").strip(),
                reference=row.get("reference", "").strip(),
                condition=row.get("condition", "").strip(),
                image_url=row.get("image_url", "").strip(),
            )
            catalogue.add_watch(watch)


def save_watches_to_csv(filepath, watches):
    fieldnames = [
        "watch_id",
        "name",
        "brand",
        "price",
        "material",
        "reference",
        "condition",
        "image_url",
    ]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for watch in watches:
            writer.writerow({
                "watch_id": watch.watch_id,
                "name": watch.name,
                "brand": watch.brand,
                "price": f"{watch.price}",
                "material": watch.material,
                "reference": watch.reference,
                "condition": watch.condition,
                "image_url": watch.image_url,
            })


def load_users_from_csv(filepath):
    loaded_users = {}
    if not os.path.exists(filepath):
        return loaded_users

    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            username = row.get("username", "").strip()
            password = row.get("password", "").strip()
            role_value = row.get("role", "USER").strip().upper()
            user_id = int(row.get("user_id", "0") or 0)
            wishlist_str = row.get("wishlist", "").strip()
            wishlist = [int(wid) for wid in wishlist_str.split(",") if wid.strip()] if wishlist_str else []
            if not username:
                continue
            if role_value == Role.ADMIN.value:
                loaded_users[username] = Admin(user_id or len(loaded_users) + 1, username, password, wishlist)
            else:
                loaded_users[username] = User(user_id or len(loaded_users) + 1, username, password, Role.USER, wishlist)
    return loaded_users


def save_users_to_csv(filepath, users_dict):
    fieldnames = ["user_id", "username", "password", "role", "wishlist"]
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for user in users_dict.values():
            writer.writerow({
                "user_id": user.user_id,
                "username": user.username,
                "password": user.password_hash,
                "role": user.role.value,
                "wishlist": ",".join(str(watchId) for watchId in user.wishlist),
            })


def initialize_users(filepath):
    global users
    users = load_users_from_csv(filepath)
    if not users:
        users = {
            "user": User(1, "user", "1234", Role.USER, []),
            "admin": Admin(2, "admin", "admin123", []),
        }
        save_users_to_csv(filepath, users)


def get_similar_watches(target_watch, all_watches, limit=3):
    if target_watch is None:
        return []

    target_brand = (target_watch.brand or "").strip().lower()
    target_material = (target_watch.material or "").strip().lower()
    target_condition = (target_watch.condition or "").strip().lower()
    target_price = target_watch.price or 0.0

    scored_watches = []
    for watch in all_watches:
        if watch.watch_id == target_watch.watch_id:
            continue

        score = 0
        if target_brand and (watch.brand or "").strip().lower() == target_brand:
            score += 100
        if target_material and (watch.material or "").strip().lower() == target_material:
            score += 40
        if target_condition and (watch.condition or "").strip().lower() == target_condition:
            score += 20

        if target_price > 0 and watch.price is not None:
            price_diff = abs(watch.price - target_price)
            if price_diff <= target_price * 0.2:
                score += 10
                score += max(0, int((target_price * 0.2 - price_diff) / (target_price * 0.02)))

        if score > 0:
                scored_watches.append((score, watch))

    scored_watches.sort(key=lambda item: (-item[0], item[1].watch_id))
    return [watch for _, watch in scored_watches[:limit]]


# Load watches and users from CSV
csv_path = os.path.join(os.path.dirname(__file__), "watches.csv")
users_csv_path = os.path.join(os.path.dirname(__file__), "users.csv")
load_watches_from_csv(csv_path)
initialize_users(users_csv_path)


@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("catalogue_page"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user = users.get(username)
        if user is None:
            return render_template("login.html", error="User not found.")

        if user.login(username, password):
            session["username"] = username
            session["role"] = user.role.value
            session["wishlist"] = user.wishlist.copy()  # Load user's wishlist into session
            return redirect(url_for("catalogue_page"))
        else:
            return render_template("login.html", error="Incorrect username or password.")

    message = request.args.get("message")
    return render_template("login.html", message=message)


@app.route("/signup", methods=["POST"])
def signup():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    errors = {}

    if not username:
        errors["username"] = "Username is required."
    if not password:
        errors["password"] = "Password is required."
    if username in users:
        errors["username"] = "That username is already taken."

    # Password restrictions
    if password:
        if len(password) < 8:
            errors["password"] = "Password must be at least 8 characters."
        elif not re.search(r"[A-Z]", password):
            errors["password"] = "Password must include at least one uppercase letter."
        elif not re.search(r"[a-z]", password):
            errors["password"] = "Password must include at least one lowercase letter."
        elif not re.search(r"\d", password):
            errors["password"] = "Password must include at least one number."

    if errors:
        return render_template(
            "login.html",
            show_signup=True,
            errors=errors,
            username=username
        )

    next_id = max((user.user_id for user in users.values()), default=0) + 1
    users[username] = User(next_id, username, password, Role.USER, [])
    save_users_to_csv(users_csv_path, users)

    return redirect(url_for("login", message="Account created successfully. Please sign in."))


@app.route("/logout")
def logout():
    username = session.get("username")
    if username and username in users:
        users[username].logout()
    session.clear()
    return redirect(url_for("login"))


@app.route("/api/wishlist")
def get_wishlist():
    if "username" not in session:
        return jsonify({"error": "Not logged in"}), 401
    ids = session.get("wishlist", [])
    watches = [w.get_details() for wid in ids if (w := catalogue.get_watch(wid))]
    return jsonify({"watches": watches})


@app.route("/api/wishlist/<int:watch_id>", methods=["POST"])
def add_to_wishlist(watch_id):
    if "username" not in session:
        return jsonify({"error": "Not logged in"}), 401
    if not catalogue.get_watch(watch_id):
        return jsonify({"error": "Watch not found"}), 404
    wishlist = session.get("wishlist", [])
    if watch_id not in wishlist:
        wishlist.append(watch_id)
        session["wishlist"] = wishlist
        # Update user's wishlist and save
        username = session["username"]
        users[username].wishlist = wishlist.copy()
        save_users_to_csv(users_csv_path, users)
    return jsonify({"success": True, "count": len(wishlist)})


@app.route("/api/wishlist/<int:watch_id>", methods=["DELETE"])
def remove_from_wishlist(watch_id):
    if "username" not in session:
        return jsonify({"error": "Not logged in"}), 401
    wishlist = session.get("wishlist", [])
    if watch_id in wishlist:
        wishlist.remove(watch_id)
        session["wishlist"] = wishlist
        # Update user's wishlist and save
        username = session["username"]
        users[username].wishlist = wishlist.copy()
        save_users_to_csv(users_csv_path, users)
    return jsonify({"success": True, "count": len(wishlist)})


@app.route("/catalogue")
def catalogue_page():
    if "username" not in session:
        return redirect(url_for("login"))

    query = request.args.get("q", "").strip()
    brand = request.args.get("brand", "").strip()
    material = request.args.get("material", "").strip()
    condition = request.args.get("condition", "").strip()
    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()
    sort_by = request.args.get("sort", "").strip()

    if query:
        watches = catalogue.search_watches(query)
    elif brand or material or condition or min_price or max_price:
        watches = catalogue.filter_watches(
            brand=brand or None,
            material=material or None,
            condition=condition or None,
            min_price=float(min_price) if min_price else None,
            max_price=float(max_price) if max_price else None,
        )
    else:
        watches = catalogue.get_all_watches()

    # Apply sorting
    sorted_watches = watches.copy()
    if sort_by == "price_low":
        sorted_watches.sort(key=lambda w: w.price)
    elif sort_by == "price_high":
        sorted_watches.sort(key=lambda w: w.price, reverse=True)
    elif sort_by == "brand_az":
        sorted_watches.sort(key=lambda w: w.brand.lower())
    elif sort_by == "brand_za":
        sorted_watches.sort(key=lambda w: w.brand.lower(), reverse=True)
    elif sort_by == "condition":
        sorted_watches.sort(key=lambda w: w.condition.lower())

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = 24
    total = len(sorted_watches)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    paginated = sorted_watches[(page - 1) * per_page : page * per_page]

    # Collect unique values for filter dropdowns.
    all_watches = catalogue.get_all_watches()
    brands = sorted(set(w.brand for w in all_watches))
    materials = sorted(set(w.material for w in all_watches))
    conditions = sorted(set(w.condition for w in all_watches))

    is_admin = session.get("role") == "ADMIN"
    wishlist_ids = session.get("wishlist", [])

    return render_template(
        "catalogue.html",
        watches=paginated,
        total=total,
        page=page,
        total_pages=total_pages,
        brands=brands,
        materials=materials,
        conditions=conditions,
        username=session["username"],
        is_admin=is_admin,
        query=query,
        sel_brand=brand,
        sel_material=material,
        sel_condition=condition,
        sel_min_price=min_price,
        sel_max_price=max_price,
        sel_sort=sort_by,
        wishlist_ids=wishlist_ids,
        wishlist_count=len(wishlist_ids),
    )


@app.route("/api/watch/<int:watch_id>")
def get_watch(watch_id):
    if "username" not in session:
        return jsonify({"error": "Not logged in"}), 401
    watch = catalogue.get_watch(watch_id)
    if watch:
        details = watch.get_details()
        details["similar_watches"] = [w.get_details() for w in get_similar_watches(watch, catalogue.get_all_watches())]
        return jsonify(details)
    return jsonify({"error": "Watch not found"}), 404


@app.route("/api/watch", methods=["POST"])
def add_watch():
    if "username" not in session or session.get("role") != "ADMIN":
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json()
    try:
        watch = Watch(
            watch_id=int(data["watch_id"]),
            name=data["name"],
            brand=data["brand"],
            price=float(data["price"]),
            material=data.get("material", ""),
            reference=data.get("reference", ""),
            condition=data.get("condition", ""),
            image_url=data.get("image_url", ""),
        )
        admin = users[session["username"]]
        admin.add_watch(watch, catalogue)
        save_watches_to_csv(csv_path, catalogue.get_all_watches())
        return jsonify({"success": True, "watch": watch.get_details()})
    except (ValueError, PermissionError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/watch/<int:watch_id>", methods=["PUT"])
def edit_watch(watch_id):
    if "username" not in session or session.get("role") != "ADMIN":
        return jsonify({"error": "Admin access required"}), 403

    data = request.get_json()
    try:
        admin = users[session["username"]]
        kwargs = {}
        for field in ["name", "brand", "material", "reference",
                       "condition", "image_url"]:
            if field in data:
                kwargs[field] = data[field]
        if "price" in data:
            kwargs["price"] = float(data["price"])
        admin.edit_watch(watch_id, catalogue, **kwargs)
        save_watches_to_csv(csv_path, catalogue.get_all_watches())
        watch = catalogue.get_watch(watch_id)
        return jsonify({"success": True, "watch": watch.get_details()})
    except (ValueError, PermissionError) as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/watch/<int:watch_id>", methods=["DELETE"])
def delete_watch(watch_id):
    if "username" not in session or session.get("role") != "ADMIN":
        return jsonify({"error": "Admin access required"}), 403

    try:
        admin = users[session["username"]]
        admin.delete_watch(watch_id, catalogue)
        save_watches_to_csv(csv_path, catalogue.get_all_watches())
        return jsonify({"success": True})
    except (ValueError, PermissionError) as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True, port=5000)
