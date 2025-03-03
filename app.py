# app.py
import os
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///course_website.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'super-secret-key'  # Change this in production!

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# ------------------
# Database Models
# ------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20))  # "student" or "teacher"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    # Relationships to assignments and lectures
    assignments = db.relationship('Assignment', backref='course', lazy=True)
    lectures = db.relationship('Lecture', backref='course', lazy=True)

class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    file_path = db.Column(db.String(256))
    # A one-to-many relationship: an assignment can have many submissions
    submissions = db.relationship('Submission', backref='assignment', lazy=True)

class Lecture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    video_path = db.Column(db.String(256))

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_email = db.Column(db.String(120), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    file_path = db.Column(db.String(256))
    submitted_at = db.Column(db.DateTime, default=db.func.now())

# ------------------
# API Endpoints
# ------------------

# User Registration Endpoint (for demonstration)
@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')
    if User.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already registered."}), 400
    user = User(email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return jsonify({"success": True, "message": "User registered successfully."}), 201

# Login Endpoint: Validate credentials and return a JWT token
@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    role = data.get('role')
    user = User.query.filter_by(email=email, role=role).first()
    if user and user.check_password(password):
        access_token = create_access_token(identity={'email': user.email, 'role': user.role})
        return jsonify({
            "success": True,
            "message": "Login successful",
            "token": access_token,
            "role": user.role
        })
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

# Protected Endpoint: Retrieve list of courses
@app.route('/api/courses', methods=['GET'])
@jwt_required()
def get_courses():
    courses = Course.query.all()
    courses_list = [
        {"id": course.course_id, "name": course.name, "description": course.description}
        for course in courses
    ]
    return jsonify(courses_list)

# Protected Endpoint: Retrieve course details (including dummy materials)
@app.route('/api/course/<course_id>', methods=['GET'])
@jwt_required()
def get_course(course_id):
    course = Course.query.filter_by(course_id=course_id).first()
    if course:
        course_details = {
            "id": course.course_id,
            "name": course.name,
            "description": course.description,
            "materials": {
                "lectureVideos": ["/static/video1.mp4"],
                "assignments": ["Assignment 1", "Assignment 2"],
                "lectureNotes": ["Note 1", "Note 2"]
            }
        }
        return jsonify(course_details)
    return jsonify({"message": "Course not found"}), 404

# Protected Teacher Endpoint: Upload an assignment file
@app.route('/api/teacher/upload-assignment', methods=['POST'])
@jwt_required()
def upload_assignment():
    identity = get_jwt_identity()
    if identity.get('role') != 'teacher':
        return jsonify({"message": "Unauthorized"}), 403
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file provided"}), 400
    file = request.files['file']
    filename = file.filename
    upload_folder = os.path.join(os.getcwd(), "uploads", "assignments")
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    return jsonify({"success": True, "message": "Assignment uploaded successfully", "filename": filename})

# Protected Teacher Endpoint: View submissions (dummy data)
@app.route('/api/teacher/view-submissions', methods=['GET'])
@jwt_required()
def view_submissions():
    identity = get_jwt_identity()
    if identity.get('role') != 'teacher':
        return jsonify({"message": "Unauthorized"}), 403
    submissions = [
        {"student": "student1@example.com", "assignment": "Assignment 1", "submittedAt": "2023-02-01T10:00:00"},
        {"student": "student2@example.com", "assignment": "Assignment 1", "submittedAt": "2023-02-01T10:30:00"}
    ]
    return jsonify(submissions)

# Protected Teacher Endpoint: Upload a lecture file
@app.route('/api/teacher/upload-lecture', methods=['POST'])
@jwt_required()
def upload_lecture():
    identity = get_jwt_identity()
    if identity.get('role') != 'teacher':
        return jsonify({"message": "Unauthorized"}), 403
    if 'file' not in request.files:
        return jsonify({"success": False, "message": "No file provided"}), 400
    file = request.files['file']
    filename = file.filename
    upload_folder = os.path.join(os.getcwd(), "uploads", "lectures")
    os.makedirs(upload_folder, exist_ok=True)
    file_path = os.path.join(upload_folder, filename)
    file.save(file_path)
    return jsonify({"success": True, "message": "Lecture uploaded successfully", "filename": filename})

# Protected Chatbot Endpoint: Simulated chatbot response
@app.route('/api/chatbot', methods=['POST'])
@jwt_required()
def chatbot():
    data = request.get_json()
    message = data.get("message")
    response = f"This is a response to '{message}'"
    return jsonify({"reply": response})

# Serve static files (e.g., lecture videos) from the "public" folder
@app.route('/static/<path:filename>', methods=['GET'])
def serve_static(filename):
    return send_from_directory(os.path.join(os.getcwd(), "public"), filename)

if __name__ == '__main__':
    app.run(debug=True)
