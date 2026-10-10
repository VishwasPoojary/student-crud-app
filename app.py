import os
import re
import secrets
import logging
from datetime import datetime, timezone, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from pymongo.errors import PyMongoError, ConnectionFailure, ServerSelectionTimeoutError, DuplicateKeyError
from bson import ObjectId
from bson.errors import InvalidId
from dotenv import load_dotenv

# Load environment variables from .env file if available
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Flask Secret Key Configuration
secret_key = os.getenv("SECRET_KEY")
if not secret_key:
    if os.getenv("RENDER"):
        raise RuntimeError("CRITICAL: SECRET_KEY environment variable is required in production.")
    secret_key = "dev-insecure-secret-key-replace-in-production"
    logger.warning("No SECRET_KEY set. Using development secret key. Set SECRET_KEY in production.")
app.secret_key = secret_key

# Session & Cookie Security
is_production = bool(os.getenv("RENDER")) or os.getenv("FLASK_ENV") == "production"
cookie_secure = os.getenv("SESSION_COOKIE_SECURE", "true" if is_production else "false").lower() == "true"

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=cookie_secure,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
)


def sanitize_mongodb_uri(uri: str) -> str:
    """Mask credentials in MongoDB connection string for safe logging."""
    if not uri:
        return ""
    return re.sub(r"(mongodb(?:\+srv)?://[^:]+:)([^@]+)(@)", r"\1****\3", uri)


# MongoDB Connection Configuration
raw_mongo_uri = os.getenv("MONGODB_URI")
if raw_mongo_uri and raw_mongo_uri.strip():
    MONGODB_URI = raw_mongo_uri.strip()
else:
    MONGODB_URI = "mongodb://localhost:27017/"

DB_NAME = "student_management"
STUDENTS_COLLECTION = "students"
USERS_COLLECTION = "users"

client = None
db = None
students = None
users = None
_client_pid = None


def get_db():
    """Retrieve or initialize fork-safe MongoDB connection for the current process."""
    global client, db, students, users, _client_pid
    current_pid = os.getpid()

    # Reconnect if uninitialized or if process was forked by Gunicorn
    if client is None or _client_pid != current_pid:
        if client is not None and _client_pid != current_pid:
            # Fork occurred! Safely close inherited parent client sockets
            try:
                client.close()
            except Exception:
                pass

        try:
            client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
            db = client.get_default_database(default=DB_NAME)
            students = db[STUDENTS_COLLECTION]
            users = db[USERS_COLLECTION]
            _client_pid = current_pid

            # Ensure unique email index once per process
            try:
                users.create_index("email", unique=True)
            except Exception as idx_err:
                logger.warning(f"Unique index creation notice: {sanitize_mongodb_uri(str(idx_err))}")

            logger.info(f"Initialized MongoDB connection (PID {current_pid}) for database '{db.name}' -> {sanitize_mongodb_uri(MONGODB_URI)}")
        except Exception as e:
            safe_msg = sanitize_mongodb_uri(str(e))
            logger.error(f"Failed to initialize MongoDB client (PID {current_pid}) [{type(e).__name__}]: {safe_msg}")
            raise

    return db


def init_db():
    """Explicitly initialize database connection."""
    return get_db()


def get_students_collection():
    """Retrieve students collection with fork-safe reconnection."""
    get_db()
    if students is None:
        raise ConnectionError("Unable to establish connection to MongoDB database.")
    return students


def get_users_collection():
    """Retrieve users collection with fork-safe reconnection."""
    get_db()
    if users is None:
        raise ConnectionError("Unable to establish connection to MongoDB database.")
    return users


EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --- CSRF PROTECTION & CONTEXT INJECTION ---

@app.context_processor
def inject_template_globals():
    """Inject CSRF token and logged-in user details into templates."""
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_hex(32)
    return {
        "csrf_token": lambda: session.get("_csrf_token", ""),
        "current_user": {
            "id": session.get("user_id"),
            "name": session.get("user_name"),
            "email": session.get("user_email")
        } if session.get("user_id") else None
    }


@app.before_request
def csrf_protect():
    """Verify CSRF token on all state-changing HTTP requests."""
    # Testing bypass if CSRF check is explicitly disabled in tests
    if app.config.get("TESTING") and app.config.get("CSRF_DISABLED"):
        return

    if request.method in ("POST", "PUT", "PATCH", "DELETE"):
        session_token = session.get("_csrf_token")
        header_token = request.headers.get("X-CSRF-Token") or request.headers.get("X-CSRFToken")
        form_token = request.form.get("csrf_token")

        submitted_token = header_token or form_token

        if not session_token or not submitted_token or not secrets.compare_digest(session_token, submitted_token):
            if request.path.startswith("/students") or request.is_json:
                return jsonify({"error": "CSRF validation failed: missing or invalid token"}), 403
            flash("Your session security token was invalid or expired. Please try again.", "danger")
            return redirect(request.referrer or url_for("login"))


# --- AUTHENTICATION DECORATOR ---

def login_required(f):
    """Ensure user is authenticated; return 401 for APIs or redirect to login for browser."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/students") or request.is_json or request.headers.get("Accept") == "application/json":
                return jsonify({"error": "Unauthorized: Authentication required"}), 401
            return redirect(url_for("login", next=request.full_path if request.query_string else request.path))
        return f(*args, **kwargs)
    return decorated_function


# --- AUTHENTICATION ROUTES ---

@app.route("/register", methods=["GET", "POST"])
def register():
    """Handle user registration."""
    if session.get("user_id"):
        return redirect(url_for("home"))

    if request.method == "POST":
        name = str(request.form.get("name", "")).strip()
        email = str(request.form.get("email", "")).strip().lower()
        password = str(request.form.get("password", ""))
        confirm_password = str(request.form.get("confirm_password", ""))

        # Validation
        if not name or len(name) < 2:
            flash("Full name is required and must be at least 2 characters.", "danger")
            return render_template("register.html", name=name, email=email), 400

        if not email or not EMAIL_REGEX.match(email):
            flash("A valid email address is required.", "danger")
            return render_template("register.html", name=name, email=email), 400

        if not password or len(password) < 8:
            flash("Password must be at least 8 characters long.", "danger")
            return render_template("register.html", name=name, email=email), 400
        elif len(password) > 128:
            flash("Password cannot exceed 128 characters.", "danger")
            return render_template("register.html", name=name, email=email), 400

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html", name=name, email=email), 400

        try:
            col = get_users_collection()
            # Check for duplicate email
            if col.find_one({"email": email}):
                flash("An account with this email address already exists. Please log in.", "danger")
                return render_template("register.html", name=name, email=email), 400

            # Hash password securely using werkzeug (scrypt / pbkdf2)
            password_hash = generate_password_hash(password)

            user_doc = {
                "name": name,
                "email": email,
                "password_hash": password_hash,
                "created_at": datetime.now(timezone.utc)
            }
            col.insert_one(user_doc)

            flash("Registration successful! Please sign in with your credentials.", "success")
            return redirect(url_for("login"))
        except DuplicateKeyError:
            flash("An account with this email address already exists. Please log in.", "danger")
            return render_template("register.html", name=name, email=email), 400
        except Exception as e:
            safe_err = sanitize_mongodb_uri(str(e))
            logger.error(f"Error during user registration: {safe_err}")
            flash("An unexpected error occurred during registration. Please try again.", "danger")
            return render_template("register.html", name=name, email=email), 500

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login."""
    if session.get("user_id"):
        return redirect(url_for("home"))

    if request.method == "POST":
        email = str(request.form.get("email", "")).strip().lower()
        password = str(request.form.get("password", ""))

        if not email or not password or len(password) > 128:
            flash("Invalid email or password.", "danger")
            return render_template("login.html", email=email), 400 if (not email or not password) else 401

        try:
            col = get_users_collection()
            user = col.find_one({"email": email})

            # Constant-time / secure password verification
            # Generic error message to prevent account enumeration
            if not user or not check_password_hash(user.get("password_hash", ""), password):
                flash("Invalid email or password.", "danger")
                return render_template("login.html", email=email), 401

            # Prevent session fixation
            session.clear()
            session.permanent = True
            session["user_id"] = str(user["_id"])
            session["user_name"] = user.get("name", "User")
            session["user_email"] = user.get("email", "")
            session["_csrf_token"] = secrets.token_hex(32)

            flash(f"Welcome back, {user.get('name', 'User')}!", "success")

            # Validate next URL to prevent open redirect
            next_url = request.args.get("next")
            if (
                not next_url
                or not next_url.startswith("/")
                or next_url.startswith("//")
                or "\\" in next_url
                or next_url == url_for("login")
            ):
                next_url = url_for("home")

            return redirect(next_url)
        except Exception as e:
            safe_err = sanitize_mongodb_uri(str(e))
            logger.error(f"Error during user login: {safe_err}")
            flash("An unexpected error occurred during login. Please try again.", "danger")
            return render_template("login.html", email=email), 500

    return render_template("login.html")


@app.route("/logout", methods=["GET", "POST"])
def logout():
    """Log out current user and clear session."""
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))


# --- STUDENT DATA VALIDATION ---

def validate_student_data(data):
    """Validate student input fields."""
    if not isinstance(data, dict):
        return None, "Invalid request body: expected JSON object"

    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    course = str(data.get("course", "")).strip()
    raw_year = data.get("year")

    if not name:
        return None, "Student name is required"
    if len(name) < 2:
        return None, "Student name must be at least 2 characters long"

    if not email:
        return None, "Student email is required"
    if not EMAIL_REGEX.match(email):
        return None, "Invalid email address format"

    if not course:
        return None, "Course is required"

    if raw_year is None or str(raw_year).strip() == "":
        return None, "Year is required"

    try:
        year = int(raw_year)
        if year < 1 or year > 8:
            return None, "Year must be between 1 and 8"
    except (ValueError, TypeError):
        return None, "Year must be a valid number"

    return {
        "name": name,
        "email": email,
        "course": course,
        "year": year
    }, None


# --- PROTECTED APPLICATION ROUTES ---

@app.route("/")
@login_required
def home():
    """Serve the frontend single-page application dashboard."""
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def health_check():
    """Safe read-only database connectivity test without modifying or deleting data."""
    try:
        col = get_students_collection()
        # Test server connectivity with ping
        col.database.client.admin.command("ping")
        record_count = col.count_documents({})
        return jsonify({
            "status": "healthy",
            "database": "connected",
            "database_name": col.database.name,
            "collection": col.name,
            "record_count": record_count
        }), 200
    except Exception as e:
        exc_type = type(e).__name__
        safe_err = sanitize_mongodb_uri(str(e))
        logger.error(f"Database health check failed [{exc_type}]: {safe_err}")
        return jsonify({
            "status": "unhealthy",
            "error_type": exc_type,
            "error": safe_err
        }), 503


@app.route("/students", methods=["GET"])
@login_required
def get_students():
    """Retrieve all students from MongoDB."""
    try:
        col = get_students_collection()
        student_list = []
        for s in col.find():
            student_list.append({
                "id": str(s["_id"]),
                "name": s.get("name", ""),
                "email": s.get("email", ""),
                "course": s.get("course", ""),
                "year": s.get("year", "")
            })
        return jsonify(student_list), 200
    except Exception as e:
        exc_type = type(e).__name__
        safe_err = sanitize_mongodb_uri(str(e))
        logger.error(f"Failed to fetch students from MongoDB [{exc_type}]: {safe_err}")
        return jsonify({"error": f"Failed to fetch students: {safe_err}"}), 500


@app.route("/students", methods=["POST"])
@login_required
def add_student():
    """Add a new student to MongoDB."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Missing or invalid JSON request body"}), 400

    student, error = validate_student_data(data)
    if error:
        return jsonify({"error": error}), 400

    try:
        # Associate record with logged-in user
        student["created_by"] = session.get("user_id")
        student["created_by_name"] = session.get("user_name")
        student["created_at"] = datetime.now(timezone.utc)

        col = get_students_collection()
        result = col.insert_one(student)
        student_id = str(result.inserted_id)
        return jsonify({
            "message": "Student added successfully",
            "id": student_id,
            "student": {
                "id": student_id,
                "name": student["name"],
                "email": student["email"],
                "course": student["course"],
                "year": student["year"]
            }
        }), 201
    except Exception as e:
        safe_err = sanitize_mongodb_uri(str(e))
        logger.error(f"Failed to add student to MongoDB: {safe_err}")
        return jsonify({"error": f"Failed to add student: {safe_err}"}), 500


@app.route("/students/<id>", methods=["PUT"])
@login_required
def update_student(id):
    """Update an existing student's information in MongoDB."""
    if not ObjectId.is_valid(id):
        return jsonify({"error": "Invalid student ID format"}), 400

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Missing or invalid JSON request body"}), 400

    updated_fields, error = validate_student_data(data)
    if error:
        return jsonify({"error": error}), 400

    try:
        updated_fields["updated_by"] = session.get("user_id")
        updated_fields["updated_at"] = datetime.now(timezone.utc)

        col = get_students_collection()
        result = col.update_one(
            {"_id": ObjectId(id)},
            {"$set": updated_fields}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Student not found"}), 404

        return jsonify({
            "message": "Student updated successfully",
            "student": {
                "id": id,
                "name": updated_fields["name"],
                "email": updated_fields["email"],
                "course": updated_fields["course"],
                "year": updated_fields["year"]
            }
        }), 200
    except Exception as e:
        safe_err = sanitize_mongodb_uri(str(e))
        logger.error(f"Failed to update student in MongoDB: {safe_err}")
        return jsonify({"error": f"Failed to update student: {safe_err}"}), 500


@app.route("/students/<id>", methods=["DELETE"])
@login_required
def delete_student(id):
    """Delete a student from MongoDB."""
    if not ObjectId.is_valid(id):
        return jsonify({"error": "Invalid student ID format"}), 400

    try:
        col = get_students_collection()
        result = col.delete_one({"_id": ObjectId(id)})

        if result.deleted_count == 0:
            return jsonify({"error": "Student not found"}), 404

        return jsonify({
            "message": "Student deleted successfully",
            "id": id
        }), 200
    except Exception as e:
        safe_err = sanitize_mongodb_uri(str(e))
        logger.error(f"Failed to delete student from MongoDB: {safe_err}")
        return jsonify({"error": f"Failed to delete student: {safe_err}"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
