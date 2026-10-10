import unittest
import json
import re
from pymongo import MongoClient
from app import app, get_students_collection, get_users_collection


class AuthenticationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        cls.client = app.test_client()

        # Connect to MongoDB for validation and cleanup
        cls.mongo = MongoClient("mongodb://localhost:27017/")
        cls.db = cls.mongo["student_management"]
        cls.users_col = cls.db["users"]
        cls.students_col = cls.db["students"]

        # Ensure test users and test students are cleaned before tests
        cls.cleanup_test_data()

    @classmethod
    def tearDownClass(cls):
        # Clean up test users and test students after tests
        cls.cleanup_test_data()
        cls.mongo.close()

    @classmethod
    def cleanup_test_data(cls):
        cls.users_col.delete_many({"email": {"$regex": r"^test.*@example\.com$"}})
        cls.students_col.delete_many({"email": {"$regex": r"^test.*@example\.com$"}})

    def get_csrf_token(self):
        """Helper to fetch a CSRF token from a GET page response."""
        res = self.client.get("/login")
        html = res.data.decode("utf-8")
        match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
        if match:
            return match.group(1)
        # Fallback to session _csrf_token
        with self.client.session_transaction() as sess:
            return sess.get("_csrf_token", "")

    # --- 1. Unauthenticated Route Protection ---

    def test_01_unauthenticated_dashboard_redirects_to_login(self):
        """Unauthenticated browser request to / should redirect (302) to /login."""
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_02_unauthenticated_api_get_students_returns_401(self):
        """Unauthenticated GET /students must return 401 Unauthorized JSON."""
        response = self.client.get("/students")
        self.assertEqual(response.status_code, 401)
        data = response.get_json()
        self.assertIn("error", data)
        self.assertIn("Authentication required", data["error"])

    def test_03_unauthenticated_api_post_students_returns_401(self):
        """Unauthenticated POST /students must return 401 Unauthorized."""
        token = self.get_csrf_token()
        response = self.client.post(
            "/students",
            headers={"X-CSRF-Token": token},
            json={"name": "Hacker", "email": "hack@example.com", "course": "Sec", "year": 1}
        )
        self.assertEqual(response.status_code, 401)

    def test_04_unauthenticated_api_put_students_returns_401(self):
        """Unauthenticated PUT /students/<id> must return 401 Unauthorized."""
        token = self.get_csrf_token()
        response = self.client.put(
            "/students/507f1f77bcf86cd799439011",
            headers={"X-CSRF-Token": token},
            json={"name": "Hacker", "email": "hack@example.com", "course": "Sec", "year": 1}
        )
        self.assertEqual(response.status_code, 401)

    def test_05_unauthenticated_api_delete_students_returns_401(self):
        """Unauthenticated DELETE /students/<id> must return 401 Unauthorized."""
        token = self.get_csrf_token()
        response = self.client.delete(
            "/students/507f1f77bcf86cd799439011",
            headers={"X-CSRF-Token": token}
        )
        self.assertEqual(response.status_code, 401)

    # --- 2. Registration Tests ---

    def test_06_register_missing_fields_rejected(self):
        """Registration with missing or empty fields must be rejected with 400."""
        token = self.get_csrf_token()
        response = self.client.post("/register", data={
            "csrf_token": token,
            "name": "",
            "email": "test_invalid@example.com",
            "password": "Password123!",
            "confirm_password": "Password123!"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Full name is required", response.data)

    def test_07_register_short_password_rejected(self):
        """Registration with password shorter than 8 characters must be rejected with 400."""
        token = self.get_csrf_token()
        response = self.client.post("/register", data={
            "csrf_token": token,
            "name": "Test User",
            "email": "test_shortpw@example.com",
            "password": "short",
            "confirm_password": "short"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"at least 8 characters", response.data)

    def test_08_register_password_mismatch_rejected(self):
        """Registration with mismatched confirm password must be rejected with 400."""
        token = self.get_csrf_token()
        response = self.client.post("/register", data={
            "csrf_token": token,
            "name": "Test User",
            "email": "test_mismatch@example.com",
            "password": "Password123!",
            "confirm_password": "DifferentPassword!"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"Passwords do not match", response.data)

    def test_09_register_valid_user_success(self):
        """Registration with valid data must succeed, store hashed password, and redirect to login."""
        token = self.get_csrf_token()
        email = "test_user1@example.com"
        password = "SecurePassword123!"

        response = self.client.post("/register", data={
            "csrf_token": token,
            "name": "Test StudentHub Admin",
            "email": email,
            "password": password,
            "confirm_password": password
        }, follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

        # Verify in MongoDB
        user_record = self.users_col.find_one({"email": email})
        self.assertIsNotNone(user_record)
        self.assertEqual(user_record["name"], "Test StudentHub Admin")
        # Ensure password is NOT stored in plain text
        self.assertNotEqual(user_record["password_hash"], password)
        self.assertTrue(user_record["password_hash"].startswith("scrypt:") or user_record["password_hash"].startswith("pbkdf2:"))

    def test_10_register_duplicate_email_rejected(self):
        """Registering with an already registered email must be rejected with 400."""
        token = self.get_csrf_token()
        email = "test_user1@example.com"
        response = self.client.post("/register", data={
            "csrf_token": token,
            "name": "Duplicate User",
            "email": email,
            "password": "AnotherPassword123!",
            "confirm_password": "AnotherPassword123!"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn(b"already exists", response.data)

    # --- 3. Login & Logout Tests ---

    def test_11_login_invalid_password_returns_generic_error(self):
        """Login with wrong password must return 401 with generic message without revealing user existence."""
        token = self.get_csrf_token()
        response = self.client.post("/login", data={
            "csrf_token": token,
            "email": "test_user1@example.com",
            "password": "WrongPassword999!"
        })
        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Invalid email or password", response.data)

    def test_12_login_nonexistent_email_returns_generic_error(self):
        """Login with non-existent email must return 401 with same generic error."""
        token = self.get_csrf_token()
        response = self.client.post("/login", data={
            "csrf_token": token,
            "email": "test_nonexistent_email_999@example.com",
            "password": "SomePassword123!"
        })
        self.assertEqual(response.status_code, 401)
        self.assertIn(b"Invalid email or password", response.data)

    def test_13_login_valid_credentials_success(self):
        """Login with correct credentials must establish a session and redirect to /."""
        token = self.get_csrf_token()
        response = self.client.post("/login", data={
            "csrf_token": token,
            "email": "test_user1@example.com",
            "password": "SecurePassword123!"
        }, follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response.headers["Location"])

        # Check session
        with self.client.session_transaction() as sess:
            self.assertIn("user_id", sess)
            self.assertEqual(sess["user_name"], "Test StudentHub Admin")
            self.assertEqual(sess["user_email"], "test_user1@example.com")

    def test_14_authenticated_user_accesses_dashboard(self):
        """Authenticated user can access / dashboard with 200 OK and see their name in navbar."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Test StudentHub Admin", response.data)
        self.assertIn(b"Sign Out", response.data)

    def test_15_logout_clears_session_and_blocks_further_access(self):
        """Logout must clear session and redirect to login; subsequent access to / must be blocked."""
        response = self.client.get("/logout", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

        # Session should be empty
        with self.client.session_transaction() as sess:
            self.assertNotIn("user_id", sess)

        # Accessing / again must redirect to /login
        subsequent = self.client.get("/", follow_redirects=False)
        self.assertEqual(subsequent.status_code, 302)
        self.assertIn("/login", subsequent.headers["Location"])

    # --- 4. CRUD Functionality & Existing Student Integrity ---

    def test_16_existing_student_records_intact(self):
        """Confirm that existing student records in MongoDB remain intact."""
        existing_students = list(self.students_col.find())
        self.assertGreaterEqual(len(existing_students), 2)
        student_emails = [s.get("email") for s in existing_students]
        self.assertIn("vishwas@gmail.com", student_emails)
        self.assertIn("harish@gmail.com", student_emails)

    def test_17_authenticated_crud_lifecycle(self):
        """Verify full CRUD operations work seamlessly when authenticated."""
        # 1. Log in
        token = self.get_csrf_token()
        login_res = self.client.post("/login", data={
            "csrf_token": token,
            "email": "test_user1@example.com",
            "password": "SecurePassword123!"
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        # Retrieve session csrf token
        with self.client.session_transaction() as sess:
            user_csrf = sess.get("_csrf_token", "")

        # 2. READ: Get all students
        get_res = self.client.get("/students")
        self.assertEqual(get_res.status_code, 200)
        students_list = get_res.get_json()
        self.assertTrue(any(s["email"] == "vishwas@gmail.com" for s in students_list))

        # 3. CREATE: Add new test student
        post_res = self.client.post(
            "/students",
            headers={"X-CSRF-Token": user_csrf},
            json={
                "name": "Test Student A",
                "email": "test_student_a@example.com",
                "course": "B.Tech CSE",
                "year": 2
            }
        )
        self.assertEqual(post_res.status_code, 201)
        created_data = post_res.get_json()
        student_id = created_data["id"]
        self.assertIsNotNone(student_id)

        # 4. UPDATE: Update test student
        put_res = self.client.put(
            f"/students/{student_id}",
            headers={"X-CSRF-Token": user_csrf},
            json={
                "name": "Test Student A Updated",
                "email": "test_student_a@example.com",
                "course": "M.Tech CSE",
                "year": 1
            }
        )
        self.assertEqual(put_res.status_code, 200)
        updated_data = put_res.get_json()
        self.assertEqual(updated_data["student"]["name"], "Test Student A Updated")
        self.assertEqual(updated_data["student"]["course"], "M.Tech CSE")

        # 5. DELETE: Delete test student
        del_res = self.client.delete(
            f"/students/{student_id}",
            headers={"X-CSRF-Token": user_csrf}
        )
        self.assertEqual(del_res.status_code, 200)

        # Verify deleted in MongoDB
        db_student = self.students_col.find_one({"_id": student_id})
        self.assertIsNone(db_student)

        # 6. Verify existing records are STILL intact
        vishwas = self.students_col.find_one({"email": "vishwas@gmail.com"})
        self.assertIsNotNone(vishwas)
        self.assertEqual(vishwas["name"], "Vishwas J")

    # --- 5. CSRF Protection Validation ---

    def test_18_csrf_missing_token_rejected_with_403(self):
        """State-changing request with missing CSRF token must return 403 Forbidden."""
        # Log in first
        token = self.get_csrf_token()
        self.client.post("/login", data={
            "csrf_token": token,
            "email": "test_user1@example.com",
            "password": "SecurePassword123!"
        })

        # Send POST /students without X-CSRF-Token header or form token
        response = self.client.post(
            "/students",
            json={
                "name": "No CSRF Student",
                "email": "test_nocsrf@example.com",
                "course": "Testing",
                "year": 1
            }
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("CSRF validation failed", response.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
