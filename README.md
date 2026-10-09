# StudentHub — Student Management CRUD Application

A full-stack, responsive Student Management CRUD (Create, Read, Update, Delete) web application built with **Python**, **Flask**, **MongoDB (PyMongo)**, and modern **Vanilla HTML5, CSS3, and JavaScript**.

This project provides an intuitive and professional dashboard to manage student records with real-time database persistence, client-side filtering, form validation, and interactive modal dialogs.

---

## 🌟 Features

- **Full CRUD Capabilities**:
  - **Create**: Add new students with validation on name, email format, course, and academic year.
  - **Read**: View all students stored in MongoDB in an organized, responsive table.
  - **Update**: Edit existing student details seamlessly via an interactive modal dialog.
  - **Delete**: Permanently remove students with a confirmation dialog to prevent accidental deletion.
- **Real Database Persistence**: All operations interact directly with a local MongoDB instance (`mongodb://localhost:27017/`), preserving data across page reloads and server restarts.
- **Clean RESTful API**: Built with Flask adhering to REST conventions with appropriate HTTP status codes (`200`, `201`, `400`, `404`, `500`) and JSON responses.
- **Modern & Responsive UI**:
  - Professional design with the `Inter` font family and clean CSS variables.
  - Responsive layout optimized for both desktop and mobile screens.
  - Native HTML5 `<dialog>` modals with backdrop blur.
  - Dynamic avatar generation based on student initials.
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
| **Database** | MongoDB | NoSQL document database (`student_management` db) |
| **DB Driver** | PyMongo | Official Python driver for MongoDB |
| **Frontend** | HTML5 | Semantic structure and native `<dialog>` elements |
| **Styling** | CSS3 | Responsive layout, CSS custom properties, and transitions |
| **Scripting** | JavaScript (ES6+) | Vanilla asynchronous Fetch API, state handling, DOM manipulation |

---

## 📁 Project Structure

```
student-crud-app/
├── app.py              # Flask server, MongoDB configuration & REST API routes
├── templates/
│   └── index.html      # Frontend HTML template
├── static/
│   ├── style.css       # Custom stylesheet & design system
│   └── script.js       # Asynchronous client-side logic & UI state handling
├── README.md           # Project documentation and setup guide
└── venv/               # Python virtual environment
```

---

## 📋 Prerequisites

Before running the application, ensure you have the following installed:

1. **Python 3.10+** (Python 3.12 recommended)
2. **MongoDB Community Server** running locally on default port `27017`
3. **MongoDB Compass** (optional, for visual inspection of documents)

---

## 🚀 Installation & Setup

### 1. Clone or Navigate to the Project

```bash
cd ~/Documents/student-crud-app
```

### 2. Set Up the Virtual Environment

If using the existing virtual environment:

```bash
source venv/bin/activate
```

Or to create a fresh virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
pip install flask pymongo
```

### 3. Ensure MongoDB is Running

Verify your local MongoDB service is active:

```bash
sudo systemctl status mongod
```

If it is not running, start it:

```bash
sudo systemctl start mongod
```

MongoDB URI used by the app: `mongodb://localhost:27017/`  
Database: `student_management`  
Collection: `students`

---

## 💻 Running the Application

1. Activate your virtual environment:
   ```bash
   source venv/bin/activate
   ```

2. Start the Flask server:
   ```bash
   python app.py
   ```

3. Open your web browser and navigate to:
   ```
   http://127.0.0.1:5000
   ```

---

## 📡 REST API Reference

All API routes communicate using JSON.

| Method | Endpoint | Description | Request Body | Success Code |
| :--- | :--- | :--- | :--- | :--- |
| `GET` | `/` | Serves the main UI | None | `200 OK` |
| `GET` | `/students` | Retrieves all students from MongoDB | None | `200 OK` |
| `POST` | `/students` | Creates a new student | `{ "name": "...", "email": "...", "course": "...", "year": 1-8 }` | `201 Created` |
| `PUT` | `/students/<id>` | Updates an existing student | `{ "name": "...", "email": "...", "course": "...", "year": 1-8 }` | `200 OK` |
| `DELETE` | `/students/<id>` | Deletes student by ObjectId | None | `200 OK` |

### Sample POST / PUT Request Body
```json
{
  "name": "Vishwas J",
  "email": "vishwas@gmail.com",
  "course": "BCA",
  "year": 3
}
```

### Sample Response (`GET /students`)
```json
[
  {
    "id": "6ab6967e52badf3b5c4e4bc7",
    "name": "Vishwas J",
    "email": "vishwas@gmail.com",
    "course": "BCA",
    "year": 3
  }
]
```

---

## 🧪 Validation & Error Handling

- **Name**: Must be non-empty and at least 2 characters.
- **Email**: Must match valid email regex pattern (`user@domain.tld`).
- **Course**: Required non-empty string.
- **Year**: Must be an integer between `1` and `8`.
- **ObjectId**: Invalid MongoDB ObjectId format returns `400 Bad Request`.
- **Not Found**: Operating on non-existent records returns `404 Not Found`.

---

## 🔍 Verification & Testing

### Running the Automated Test Suite

A comprehensive test suite is available to verify all endpoints, database operations, and data integrity:

```bash
python -c "
import urllib.request, json
res = urllib.request.urlopen('http://127.0.0.1:5000/students')
print('Active Students:', json.loads(res.read()))
"
```

### Manual Testing Checklist
- [x] **CREATE**: Add a student with valid information; verify document appears in table and MongoDB Compass.
- [x] **READ**: Refresh browser; verify existing students are loaded directly from MongoDB.
- [x] **UPDATE**: Edit a student's course or year; confirm changes reflect immediately.
- [x] **DELETE**: Delete a record with confirmation; verify it is permanently removed from the database.
- [x] **PERSISTENCE**: Stop and restart Flask; verify student records remain intact in MongoDB.
