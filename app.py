from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from bson import ObjectId
from bson.errors import InvalidId
import re

app = Flask(__name__)

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")

# Select database
db = client["student_management"]

# Select collection
students = db["students"]

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


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


@app.route("/")
def home():
    """Serve the frontend single-page application."""
    return render_template("index.html")


@app.route("/students", methods=["GET"])
def get_students():
    """Retrieve all students from MongoDB."""
    try:
        student_list = []
        for s in students.find():
            student_list.append({
                "id": str(s["_id"]),
                "name": s.get("name", ""),
                "email": s.get("email", ""),
                "course": s.get("course", ""),
                "year": s.get("year", "")
            })
        return jsonify(student_list), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch students: {str(e)}"}), 500


@app.route("/students", methods=["POST"])
def add_student():
    """Add a new student to MongoDB."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Missing or invalid JSON request body"}), 400

    student, error = validate_student_data(data)
    if error:
        return jsonify({"error": error}), 400

    try:
        result = students.insert_one(student)
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
        return jsonify({"error": f"Failed to add student: {str(e)}"}), 500


@app.route("/students/<id>", methods=["PUT"])
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
        result = students.update_one(
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
        return jsonify({"error": f"Failed to update student: {str(e)}"}), 500


@app.route("/students/<id>", methods=["DELETE"])
def delete_student(id):
    """Delete a student from MongoDB."""
    if not ObjectId.is_valid(id):
        return jsonify({"error": "Invalid student ID format"}), 400

    try:
        result = students.delete_one({"_id": ObjectId(id)})

        if result.deleted_count == 0:
            return jsonify({"error": "Student not found"}), 404

        return jsonify({
            "message": "Student deleted successfully",
            "id": id
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete student: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)

