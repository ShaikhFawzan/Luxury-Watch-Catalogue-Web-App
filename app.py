import os
import re
from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from backend import Role, Watch, User, Admin, Catalogue, Review
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-key")

# In-memory state (populated from Supabase on startup)
catalogue = Catalogue()
users = {}
reviews: dict[int, list] = {}


# ---------------------------------------------------------------------------
# Supabase helpers — watches
# ---------------------------------------------------------------------------

def load_watches_from_supabase():
    global catalogue
    catalogue = Catalogue()   # clears old in-memory data, avoid duplicates

    response = supabase.table("watches").select("*").execute()
    for row in response.data:
        try:
            price = float(row.get("price", 0) or 0)
        except (ValueError, TypeError):
            price = 0.0
        watch = Watch(
            watch_id=int(row["watch_id"]),
            name=(row.get("name") or "").strip(),
            brand=(row.get("brand") or "").strip(),
            price=price,
            material=(row.get("material") or "").strip(),
            reference=(row.get("reference") or "").strip(),
            condition=(row.get("condition") or "").strip(),
            image_url=(row.get("image_url") or "").strip(),
        )
        catalogue.add_watch(watch)


def save_watch_to_supabase(watch):
    """Upsert a single watch."""
    supabase.table("watches").upsert({
        "watch_id": watch.watch_id,
        "name": watch.name,
        "brand": watch.brand,
        "price": watch.price,
        "material": watch.material,
        "reference": watch.reference,
        "condition": watch.condition,
        "image_url": watch.image_url,
    }).execute()


def delete_watch_from_supabase(watch_id):
    supabase.table("watches").delete().eq("watch_id", watch_id).execute()


# ---------------------------------------------------------------------------
# Supabase helpers — users
# ---------------------------------------------------------------------------

def load_users_from_supabase():
    loaded = {}
    response = supabase.table("users").select("*").execute()
    for row in response.data:
        username = (row.get("username") or "").strip()
        if not username:
            continue
        password_hash = row.get("password", "")
        role_value = (row.get("role") or "USER").strip().upper()
        user_id = int(row.get("user_id") or 0)
        wishlist_str = row.get("wishlist") or ""
        wishlist = [int(wid) for wid in wishlist_str.split(",") if wid.strip()]

        if role_value == Role.ADMIN.value:
            loaded[username] = Admin(user_id, username, password_hash, wishlist)
        else:
            loaded[username] = User(user_id, username, password_hash, Role.USER, wishlist)
    return loaded


def save_user_to_supabase(user):
    """Upsert a single user."""
    supabase.table("users").upsert({
        "user_id": user.user_id,
        "username": user.username,
        "password": user.password_hash,
        "role": user.role.value,
        "wishlist": ",".join(str(wid) for wid in user.wishlist),
    }).execute()


def delete_user_from_supabase(username):
    supabase.table("users").delete().eq("username", username).execute()


# ---------------------------------------------------------------------------
# Supabase helpers — reviews
# ---------------------------------------------------------------------------

def load_reviews_from_supabase():
    global reviews
    reviews = {}   # clears old in-memory reviews, avoids duplicates

    response = supabase.table("reviews").select("*").execute()
    for row in response.data:
        try:
            review = Review(
                review_id=int(row["review_id"]),
                watch_id=int(row["watch_id"]),
                username=(row.get("username") or "").strip(),
                rating=int(row["rating"]),
                title=(row.get("title") or "").strip(),
                body=(row.get("body") or "").strip(),
                timestamp=(row.get("timestamp") or "").strip(),
            )
            reviews.setdefault(review.watch_id, []).append(review)
        except (KeyError, ValueError):
            continue


def save_review_to_supabase(review):
    """Upsert a single review."""
    supabase.table("reviews").upsert(review.to_dict()).execute()


def delete_review_from_supabase(review_id):
    supabase.table("reviews").delete().eq("review_id", review_id).execute()


# ---------------------------------------------------------------------------
# Startup — seed default users if the table is empty
# ---------------------------------------------------------------------------

def initialize_users():
    global users
    users = load_users_from_supabase()
    if users:
        return

    # Seed two default accounts
    default_user = User(1, "user", generate_password_hash("1234"), Role.USER, [])
    default_admin = Admin(2, "admin", generate_password_hash("admin123"), [])
    users["user"] = default_user
    users["admin"] = default_admin
    save_user_to_supabase(default_user)
    save_user_to_supabase(default_admin)


# ---------------------------------------------------------------------------
# Similarity helper (unchanged)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Boot
# ---------------------------------------------------------------------------

load_watches_from_supabase()
initialize_users()
load_reviews_from_supabase()


# ---------------------------------------------------------------------------
# Routes (all logic identical — only persistence calls changed)
# ---------------------------------------------------------------------------

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
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    errors = {}

    if not username:
        errors["username"] = "Username is required."
    if not password:
        errors["password"] = "Password is required."
    if username in users:
        errors["username"] = "That username is already taken."

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
            username=username,
        )

    next_id = max((user.user_id for user in users.values()), default=0) + 1
    password_hash = generate_password_hash(password)
    new_user = User(next_id, username, password_hash, Role.USER, [])
    users[username] = new_user
    save_user_to_supabase(new_user)          # ← Supabase instead of CSV

    return redirect(url_for("login", message="Account created successfully. Please sign in."))


@app.route("/logout")
def logout():
    if "username" in session and session.get("role") != Role.GUEST.value:
        username = session["username"]
        user = users.get(username)
        if user:
            user.wishlist = session.get("wishlist", []).copy()
            save_user_to_supabase(user)      # ← Supabase instead of CSV
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
    save_user_to_supabase(user)              # ← Supabase instead of CSV

    return jsonify({"success": True, "count": len(user.wishlist)})


@app.route("/api/wishlist/<int:watch_id>", methods=["DELETE"])
def remove_from_wishlist(watch_id):
    if "username" not in session or session.get("role") == Role.GUEST.value:
        return jsonify({"error": "Not logged in or guest account"}), 401

    wishlist = session.get("wishlist", [])
    if watch_id in wishlist:
        wishlist.remove(watch_id)
        session["wishlist"] = wishlist
        username = session["username"]
        users[username].wishlist = wishlist.copy()
        save_user_to_supabase(users[username])  # ← Supabase instead of CSV

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

    page = request.args.get("page", 1, type=int)
    per_page = 24
    total = len(sorted_watches)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    paginated = sorted_watches[start: start + per_page]

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
        next_id = max(
        [w.watch_id for w in catalogue.get_all_watches()],
        default=0) + 1
        watch = Watch(
            watch_id=next_id,
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
        save_watch_to_supabase(watch)        # ← Supabase instead of CSV
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
        for field in ["name", "brand", "material", "reference", "condition", "image_url"]:
            if field in data:
                kwargs[field] = data[field]
        if "price" in data:
            kwargs["price"] = float(data["price"])

        admin.edit_watch(watch_id, catalogue, **kwargs)
        watch = catalogue.get_watch(watch_id)
        save_watch_to_supabase(watch)        # ← Supabase instead of CSV
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
        delete_watch_from_supabase(watch_id) # ← Supabase instead of CSV
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

    existing = next((r for r in bucket if r.username == username), None)
    if existing:
        existing.rating = rating
        existing.title = title
        existing.body = body
        existing.timestamp = datetime.now(timezone.utc).isoformat()
        save_review_to_supabase(existing)    # ← Supabase upsert
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
    save_review_to_supabase(review)          # ← Supabase instead of CSV
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
            delete_review_from_supabase(review_id)  # ← Supabase instead of CSV
            return jsonify({"success": True})
    return jsonify({"error": "Review not found."}), 404


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)