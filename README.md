# StudentHub — Student Management CRUD Application

A full-stack, responsive Student Management CRUD (Create, Read, Update, Delete) web application built with **Python**, **Flask**, **MongoDB (PyMongo)**, and modern **Vanilla HTML5, CSS3, and JavaScript**.

This project provides an intuitive and professional dashboard to manage student records with real-time database persistence, secure user authentication, client-side filtering, form validation, and interactive modal dialogs.

---

## 🌟 Features

- **Secure Authentication & Access Control**:
  - **User Registration**: Register with Name, Email, Password (minimum 8 characters), and Confirm Password. Strict email format checking and MongoDB unique index enforcement preventing duplicate registrations.
  - **Secure Password Hashing**: Passwords are cryptographically salted and hashed using `Werkzeug`'s implementation of `scrypt` / `PBKDF2`. Plain-text passwords are never stored.
  - **Secure Session Management**: Signed HTTP-only session cookies with `SameSite=Lax` and configurable HTTPS-only `Secure` cookies.
  - **Generic Login Errors**: Ambiguous error messaging (`Invalid email or password`) prevents account enumeration attacks.
  - **Session Fixation Defense**: Existing sessions are invalidated and regenerated upon successful login.
  - **CSRF Defense**: Cryptographic synchronized token CSRF protection on state-changing browser forms and AJAX/Fetch API calls (`X-CSRF-Token`).
  - **Full Route & API Protection**: Unauthenticated browser visits to `/` redirect to `/login`. Direct API calls to student endpoints (`/students*`) by unauthenticated clients return `401 Unauthorized` JSON responses.
- **Full Student CRUD Capabilities**:
  - **Create**: Add new students with validation on name, email format, course, and academic year. Automatically associates record with the logged-in user.
  - **Read**: View all students stored in MongoDB in an organized, responsive table.
  - **Update**: Edit existing student details seamlessly via an interactive modal dialog.
  - **Delete**: Permanently remove students with a confirmation dialog to prevent accidental deletion.
- **Real Database Persistence**: All operations interact directly with MongoDB (local or Atlas cloud cluster), preserving data across page reloads and server restarts.
- **Clean RESTful API**: Built with Flask adhering to REST conventions with appropriate HTTP status codes (`200`, `201`, `400`, `401`, `403`, `404`, `500`) and JSON responses.
- **Modern & Responsive UI**:
  - Professional design with the `Inter` font family and clean CSS variables.
  - Responsive layout optimized for desktop, tablet, and mobile screens.
  - Native HTML5 `<dialog>` modals with backdrop blur.
  - Dynamic avatar generation based on student initials and logged-in user profile badge with Sign Out action.
- **Mutually Exclusive UI States**:
  - **Loading**: Animated spinner while records are being fetched.
  - **Empty State**: Clear visual message when no records exist or search returns 0 results.
  - **Populated View**: Clean table display when student records exist.
- **Instant Search & Filter**: Real-time filtering across student names, emails, and courses, plus year-based dropdown filtering without unnecessary full-page reloads.
- **Toast Notifications**: Interactive feedback toasts for successful creations, updates, deletions, and error alerts.

---

## 🛠️ Technology Stack

| Layer | Technology | Description |
| :--- | :--- | :--- |
| **Backend** | Python 3.12+ | Core programming language |
| **Framework** | Flask 3.x | Lightweight WSGI web application framework & REST API |
| **Security** | Werkzeug Security | Industry-standard password hashing (`scrypt`) |
| **Database** | MongoDB | NoSQL document database (`student_management` db) |
| **DB Driver** | PyMongo | Official Python driver for MongoDB |
| **Frontend** | HTML5 | Semantic structure and native `<dialog>` elements |
| **Styling** | CSS3 | Responsive layout, CSS custom properties, and transitions |
| **Scripting** | JavaScript (ES6+) | Vanilla asynchronous Fetch API, state handling, DOM manipulation |
| **Testing** | unittest | Comprehensive test suite for auth, API, and database operations |

---

## 📁 Project Structure

```
student-crud-app/
├── app.py              # Flask server, authentication routes, MongoDB config & REST API
├── requirements.txt    # Production Python dependencies
├── .env.example        # Template for required environment variables
├── templates/
│   ├── index.html      # Protected student management dashboard SPA
│   ├── login.html      # Secure sign-in template with toggle visibility
│   └── register.html   # User registration template with validation
├── static/
│   ├── style.css       # Design system, auth page layouts, modals & components
│   └── script.js       # Asynchronous client-side logic, CSRF handling & API calls
├── tests/
│   └── test_auth.py    # Automated test suite (18 unit/integration test cases)
├── README.md           # Project documentation and setup guide
└── venv/               # Python virtual environment
```

---

## 📋 Prerequisites

Before running the application, ensure you have the following installed:

1. **Python 3.10+** (Python 3.12 recommended)
2. **MongoDB Community Server** running locally on default port `27017` (or access to a MongoDB Atlas cluster)
3. **MongoDB Compass** (optional, for visual inspection of documents)

---

## 🚀 Installation & Setup

### 1. Clone or Navigate to the Project

```bash
cd ~/Documents/student-crud-app
```

### 2. Set Up the Virtual Environment

```bash
source venv/bin/activate
# Or create a new virtual environment:
# python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy `.env.example` to `.env` and set your secrets:

```bash
cp .env.example .env
```

Key variables in `.env`:
- `SECRET_KEY`: A cryptographically strong secret key (generate with `python -c "import secrets; print(secrets.token_hex(32))"`).
- `MONGODB_URI`: Connection string (defaults to `mongodb://localhost:27017/` locally).
- `SESSION_COOKIE_SECURE`: `false` for local HTTP, `true` for production HTTPS.

---

## 💻 Running the Application

### Local Development
1. Ensure local MongoDB is running:
   ```bash
   sudo systemctl status mongod
   # If not running: sudo systemctl start mongod
   ```

2. Activate virtual environment and start the Flask server:
   ```bash
   source venv/bin/activate
   python app.py
   ```

3. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```
   *(Unauthenticated requests will automatically redirect you to `/login`).*

---

## ☁️ Deploying to Render

My existing application is deployed at:  
👉 **`https://student-crud-app-hquc.onrender.com/`**

### Render Configuration Checklist:

1. **Build & Start Commands**:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

2. **Required Environment Variables (Render Dashboard -> Environment)**:
   | Variable | Value / Description |
   | :--- | :--- |
   | `SECRET_KEY` | High-entropy production key (e.g. 64-char hex string) |
   | `MONGODB_URI` | `mongodb+srv://<user>:<password>@cluster.mongodb.net/student_management?retryWrites=true&w=majority` |
   | `SESSION_COOKIE_SECURE` | `true` (enforces HTTPS cookie transmission) |
   | `PYTHON_VERSION` | `3.12.3` |

3. **MongoDB Atlas Network Access**:
   - In MongoDB Atlas -> **Network Access**, ensure `0.0.0.0/0` is whitelisted so Render's dynamic instances can connect.

---

## 📡 REST API & Authentication Routes

### Authentication Routes

| Method | Endpoint | Description | Parameters / Body | Behavior |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/register` | Registration UI | None | Returns registration page |
| `POST` | `/register` | Create user account | `name`, `email`, `password`, `confirm_password`, `csrf_token` | Hashes password, checks uniqueness, redirects to `/login` |
| `GET` | `/login` | Sign-in UI | Query param `next` (optional) | Returns login page |
| `POST` | `/login` | Authenticate user | `email`, `password`, `csrf_token` | Validates credentials, establishes session, redirects |
| `GET`/`POST` | `/logout` | Terminate session | None | Clears session cookie, redirects to `/login` |

### Student Management CRUD Endpoints (Protected by `@login_required`)

| Method | Endpoint | Description | Request Body | Headers | Response Code |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | Serves dashboard UI | None | Session Cookie | `200 OK` (or `302` to `/login`) |
| `GET` | `/students` | Retrieves all students | None | Session Cookie, `Accept: application/json` | `200 OK` (or `401 Unauthorized`) |
| `POST` | `/students` | Creates student record | `{ "name": "...", "email": "...", "course": "...", "year": 1-8 }` | `X-CSRF-Token`, Session Cookie | `201 Created` (or `401`/`403`) |
| `PUT` | `/students/<id>` | Updates student | `{ "name": "...", "email": "...", "course": "...", "year": 1-8 }` | `X-CSRF-Token`, Session Cookie | `200 OK` (or `401`/`403`/`404`) |
| `DELETE` | `/students/<id>` | Deletes student | None | `X-CSRF-Token`, Session Cookie | `200 OK` (or `401`/`403`/`404`) |

---

## 🔍 Verification & Automated Testing

### Running the Test Suite

Run the full automated test suite containing 18 test cases:

```bash
source venv/bin/activate
python -m unittest tests/test_auth.py -v
```

### Automated Test Coverage Summary:
- [x] **Unauthenticated Redirection**: Direct visits to `/` redirect to `/login`.
- [x] **API Route Protection**: Direct HTTP `GET`, `POST`, `PUT`, `DELETE` to `/students` without session return `401 Unauthorized`.
- [x] **Validation & Error Handling**: Missing fields, short passwords (<8 chars), mismatched passwords, and duplicate emails are rejected with descriptive errors.
- [x] **Generic Login Errors**: Incorrect passwords and non-existent emails return generic `Invalid email or password` errors to prevent account enumeration.
- [x] **Secure Sessions & Fixation Defense**: Sessions are cleared before login and populated with secure cookies.
- [x] **CSRF Protection**: State-changing requests without CSRF tokens are rejected with `403 Forbidden`.
- [x] **Data Integrity**: Existing student records (`Vishwas J`, `Harish`) remain intact and unharmed in MongoDB.
- [x] **Post-Auth CRUD Functionality**: Authenticated users can list, create, update, and delete students.
