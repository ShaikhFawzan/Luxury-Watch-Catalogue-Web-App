import csv
import os
import re
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from backend import Role, Watch, User, Admin, Catalogue, Review
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")

# Backend setup
catalogue = Catalogue()
users = {}
# reviews: {watch_id: [Review, ...]}
reviews: dict[int, list] = {}


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
                loaded_users[username] = Admin(user_id, username, password, wishlist)
            else:
                loaded_users[username] = User(user_id, username, password, Role.USER, wishlist)

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


def load_reviews_from_csv(filepath):
    if not os.path.exists(filepath):
        return
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                review = Review(
                    review_id=int(row["review_id"]),
                    watch_id=int(row["watch_id"]),
                    username=row["username"].strip(),
                    rating=int(row["rating"]),
                    title=row["title"].strip(),
                    body=row["body"].strip(),
                    timestamp=row["timestamp"].strip(),
                )
                reviews.setdefault(review.watch_id, []).append(review)
            except (KeyError, ValueError):
                continue


def save_reviews_to_csv(filepath):
    fieldnames = ["review_id", "watch_id", "username", "rating", "title", "body", "timestamp"]
    all_reviews = [r for bucket in reviews.values() for r in bucket]
    all_reviews.sort(key=lambda r: r.review_id)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in all_reviews:
            writer.writerow(r.to_dict())


def initialize_users(filepath):
    global users
    users = load_users_from_csv(filepath)

    # if file already has users, dont overwrite
    if users:
        return

    # if file is empty, then add 2 default roles (1 admin, 1 normal user)
    users["user"] = User(1, "user", generate_password_hash("1234"), Role.USER, []
    )

    users["admin"] = Admin(2, "admin", generate_password_hash("admin123"), []
    )

    save_users_to_csv(filepath, users)


def get_similar_watches(target_watch, all_watches, limit=3):
    """
    Find and return a list of watches similar to a given target watch.

    Similarity is determined using a weighted scoring system based on:
    - Brand (highest priority)
    - Material
    - Condition
    - Price proximity (within 20%)

    Args:
        target_watch (Watch): The reference watch to compare against.
        all_watches (list[Watch]): List of all available watches.
        limit (int): Maximum number of similar watches to return.

    Returns:
        list[Watch]: A list of the most similar watches, sorted by relevance.
                    Returns an empty list if no similar watches are found.
    """

    # Return empty list if no target is provided
    if target_watch is None:
        return []

    # Normalize target attributes for consistent comparison
    target_brand = (target_watch.brand or "").strip().lower()
    target_material = (target_watch.material or "").strip().lower()
    target_condition = (target_watch.condition or "").strip().lower()
    target_price = target_watch.price or 0.0

    scored_watches = []

    # Iterate through all watches to compute similarity scores
    for watch in all_watches:

        # Skip comparing the watch with itself
        if watch.watch_id == target_watch.watch_id:
            continue

        score = 0

        # Brand match (highest weight)
        if target_brand and (watch.brand or "").strip().lower() == target_brand:
            score += 100
        # Material match
        if target_material and (watch.material or "").strip().lower() == target_material:
            score += 40
        # Condition match
        if target_condition and (watch.condition or "").strip().lower() == target_condition:
            score += 20

        # Price similarity (within ±20% range)
        if target_price > 0 and watch.price is not None:
            price_diff = abs(watch.price - target_price)

            if price_diff <= target_price * 0.2:
                # Base score for being within range
                score += 10

                # Bonus score: closer prices get higher points
                score += max(
                    0,
                    int((target_price * 0.2 - price_diff) / (target_price * 0.02))
                )

        # Only include watches that have some similarity
        if score > 0:
            scored_watches.append((score, watch))

    # Sort watches by:
    # 1. Highest score (descending)
    # 2. Watch ID (ascending) to ensure consistent ordering
    scored_watches.sort(key=lambda item: (-item[0], item[1].watch_id))

    # Return only the top 'limit' watches (limit = 3)
    return [watch for _, watch in scored_watches[:limit]]

# Load watches, users, and reviews from CSV
csv_path = os.path.join(os.path.dirname(__file__), "data", "watches.csv")
users_csv_path = os.path.join(os.path.dirname(__file__), "data", "users.csv")
reviews_csv_path = os.path.join(os.path.dirname(__file__), "data", "reviews.csv")
load_watches_from_csv(csv_path)
initialize_users(users_csv_path)
load_reviews_from_csv(reviews_csv_path)


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

        if request.form.get("guest"):
            session["username"] = "Guest"
            session["role"] = Role.GUEST.value
            session["wishlist"] = []
            return redirect(url_for("catalogue_page"))

        user = users.get(username)
        if user is None:
            return render_template("login.html", error="User not found.")

        if user.login(username, password):
            session["username"] = username
            session["role"] = user.role.value
            session["wishlist"] = user.wishlist.copy()
            return redirect(url_for("catalogue_page"))

        return render_template("login.html", error="Incorrect username or password.")

    return render_template("login.html")



@app.route("/signup", methods=["POST"])
def signup():
    """
    Handle user signup form submission.

    This route:
    - Retrieves and validates user input (username and password)
    - Enforces password strength requirements
    - Prevents duplicate usernames
    - Creates and stores a new user if validation passes

    Returns:
        Response:
            - Renders the login page with errors if validation fails
            - Redirects to login page with success message if signup succeeds
    """

    # Retrieve and remove extra spaces from inputs
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    errors = {}

    # Basic validation checks
    if not username:
        errors["username"] = "Username is required."
    if not password:
        errors["password"] = "Password is required."
    if username in users:
        errors["username"] = "That username is already taken."

    # Password requirements
    if password:
        if len(password) < 8:
            errors["password"] = "Password must be at least 8 characters."
        elif not re.search(r"[A-Z]", password):
            errors["password"] = "Password must include at least one uppercase letter."
        elif not re.search(r"[a-z]", password):
            errors["password"] = "Password must include at least one lowercase letter."
        elif not re.search(r"\d", password):
            errors["password"] = "Password must include at least one number."

    # If validation fails, re-render signup form with error messages
    if errors:
        return render_template(
            "login.html",
            show_signup=True,   # ensures signup form is displayed
            errors=errors,
            username=username  # preserves user input for username
        )

    # Generate a new unique user ID
    next_id = max((user.user_id for user in users.values()), default=0) + 1

    # Create and store the new user with hashing
    password_hash = generate_password_hash(password)
    users[username] = User(next_id, username, password_hash, Role.USER, [])

    # Update users in CSV File
    save_users_to_csv(users_csv_path, users)

    # Redirect to login page with success message
    return redirect(url_for("login", message="Account created successfully. Please sign in."))


@app.route("/logout")
def logout():
    # Save wishlist back to user before clearing session
    if "username" in session and session.get("role") != Role.GUEST.value:
        username = session["username"]
        user = users.get(username)
        if user:
            user.wishlist = session.get("wishlist", []).copy()
            save_users_to_csv(users_csv_path, users)
    session.clear()
    return redirect(url_for("login", message="Logged out successfully."))


@app.route("/api/wishlist", methods=["GET"])
def get_wishlist():
    if "username" not in session or session.get("role") == Role.GUEST.value:
        return jsonify({"error": "Not logged in or guest account"}), 401

    username = session["username"]
    user = users.get(username)
    if not user:
        return jsonify({"error": "User not found"}), 404

    wishlist = session.get("wishlist", [])
    watches = [catalogue.get_watch(wid).get_details() for wid in wishlist if catalogue.get_watch(wid)]
    return jsonify({"watches": watches})


@app.route("/api/wishlist/<int:watch_id>", methods=["POST"])
def add_to_wishlist(watch_id):
    if "username" not in session or session.get("role") == Role.GUEST.value:
        return jsonify({"error": "Not logged in or guest account"}), 401

    username = session["username"]
    user = users.get(username)

    if not user:
        return jsonify({"error": "User not found"}), 404

    if watch_id not in user.wishlist:
        user.wishlist.append(watch_id)

    session["wishlist"] = user.wishlist.copy()
    save_users_to_csv(users_csv_path, users)

    return jsonify({"success": True, "count": len(user.wishlist)})


@app.route("/api/wishlist/<int:watch_id>", methods=["DELETE"])
def remove_from_wishlist(watch_id):
    if "username" not in session or session.get("role") == Role.GUEST.value:
        return jsonify({"error": "Not logged in or guest account"}), 401
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
    """
    Display the watch catalogue page with support for:
    - Search (by query)
    - Filtering (brand, material, condition, price range)
    - Sorting (price, brand, condition)
    - Pagination

    This route:
    - Ensures the user is authenticated
    - Retrieves query parameters from the request
    - Applies search OR filtering logic
    - Applies sorting on the resulting dataset
    - Paginates results for display
    - Prepares data for dropdown filters and UI rendering

    Returns:
        Response:
            - Redirects to login page if user is not authenticated
            - Renders catalogue.html with paginated watch data and UI state
    """

    # Ensure user is logged in before accessing catalogue
    if "username" not in session:
        return redirect(url_for("login"))

    # Retrieve query parameters (search, filters, sorting)
    query = request.args.get("q", "").strip()
    brand = request.args.get("brand", "").strip()
    material = request.args.get("material", "").strip()
    condition = request.args.get("condition", "").strip()
    min_price = request.args.get("min_price", "").strip()
    max_price = request.args.get("max_price", "").strip()
    sort_by = request.args.get("sort", "").strip()

    # Apply search OR filtering logic (search takes priority)
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
        # Default: return all watches
        watches = catalogue.get_all_watches()

    # Apply sorting to the resulting dataset
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

    # Pagination logic
    page = request.args.get("page", 1, type=int)
    per_page = 24  # number of items per page

    total = len(sorted_watches)
    total_pages = max(1, (total + per_page - 1) // per_page)

    # Ensure page number stays within valid bounds
    page = max(1, min(page, total_pages))

    # Slice dataset for current page
    start = (page - 1) * per_page
    paginated = sorted_watches[start : start + per_page]


    # Collect unique values for filter dropdowns (from full dataset)
    all_watches = catalogue.get_all_watches()
    brands = sorted(set(w.brand for w in all_watches))
    materials = sorted(set(w.material for w in all_watches))
    conditions = sorted(set(w.condition for w in all_watches))

    # User-related UI state
    is_admin = session.get("role") == "ADMIN"
    wishlist_ids = session.get("wishlist", [])

    # Render catalogue page with all required data
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


@app.route("/api/reviews/<int:watch_id>")
def get_reviews(watch_id):
    if "username" not in session:
        return jsonify({"error": "Not logged in"}), 401
    bucket = reviews.get(watch_id, [])
    bucket_sorted = sorted(bucket, key=lambda r: r.timestamp, reverse=True)
    current_user = session["username"]
    user_review = next((r.to_dict() for r in bucket_sorted if r.username == current_user), None)
    return jsonify({
        "reviews": [r.to_dict() for r in bucket_sorted],
        "user_review": user_review,
        "average_rating": round(sum(r.rating for r in bucket) / len(bucket), 1) if bucket else None,
        "is_guest": session.get("role") == Role.GUEST.value,
    })


@app.route("/api/reviews/<int:watch_id>", methods=["POST"])
def submit_review(watch_id):
    if "username" not in session:
        return jsonify({"error": "Not logged in"}), 401
    if session.get("role") == Role.GUEST.value:
        return jsonify({"error": "Guest accounts cannot submit reviews"}), 403
    if not catalogue.get_watch(watch_id):
        return jsonify({"error": "Watch not found"}), 404

    data = request.get_json()
    rating = data.get("rating")
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()

    if not isinstance(rating, int) or not (1 <= rating <= 5):
        return jsonify({"error": "Rating must be 1–5."}), 400
    if not title:
        return jsonify({"error": "Title is required."}), 400
    if not body:
        return jsonify({"error": "Review body is required."}), 400

    username = session["username"]
    bucket = reviews.setdefault(watch_id, [])

    # One review per user per watch — update if exists
    existing = next((r for r in bucket if r.username == username), None)
    if existing:
        existing.rating = rating
        existing.title = title
        existing.body = body
        existing.timestamp = datetime.now(timezone.utc).isoformat()
        save_reviews_to_csv(reviews_csv_path)
        return jsonify({"success": True, "review": existing.to_dict(), "updated": True})

    next_id = max((r.review_id for bucket in reviews.values() for r in bucket), default=0) + 1
    review = Review(
        review_id=next_id,
        watch_id=watch_id,
        username=username,
        rating=rating,
        title=title,
        body=body,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
    bucket.append(review)
    save_reviews_to_csv(reviews_csv_path)
    return jsonify({"success": True, "review": review.to_dict(), "updated": False})


@app.route("/api/reviews/<int:watch_id>", methods=["DELETE"])
def delete_review(watch_id):
    if "username" not in session:
        return jsonify({"error": "Not logged in"}), 401
    if session.get("role") == Role.GUEST.value:
        return jsonify({"error": "Guest accounts cannot delete reviews"}), 403

    username = session["username"]
    is_admin = session.get("role") == "ADMIN"
    review_id = request.args.get("review_id", type=int)

    bucket = reviews.get(watch_id, [])
    for i, r in enumerate(bucket):
        if r.review_id == review_id:
            if r.username != username and not is_admin:
                return jsonify({"error": "Cannot delete another user's review."}), 403
            bucket.pop(i)
            save_reviews_to_csv(reviews_csv_path)
            return jsonify({"success": True})
    return jsonify({"error": "Review not found."}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)
