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
from sentence_transformers import SentenceTransformer
import chromadb
import ollama
import re

app = Flask(__name__)
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "http://localhost:3000"}})

# Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///course_website.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = 'super-secret-key'  # Change this in production!

MODEL = "deepseek-r1:1.5b"
OLLAMA_HOST = "http://localhost:9999"

client = ollama.Client(
    host=OLLAMA_HOST
    )
available_models = client.list()
is_model_available = False
for i in available_models.models:
    if MODEL in i.model:
        is_model_available = True
        break

if not is_model_available:
    client.pull(MODEL)

# Load embedding model
embed_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

# Initialize ChromaDB (or FAISS)
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="documents")

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
jwt = JWTManager(app)

# ------------------
# Database Models
# ------------------

user_courses = db.Table(
    'user_courses',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id', name="fk_user_courses_user"), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id', name="fk_user_courses_course"), primary_key=True)
)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20))  # "student" or "teacher"

    courses = db.relationship('Course', secondary=user_courses, back_populates='users')

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

    users = db.relationship('User', secondary=user_courses, back_populates='courses')

"""
Assignment Content JSON format

Assignment : [ Question, ... ]

Question: 
{
    "question": "question text",
    "options" : ["option text", ...]
    "correct_option": index of correct option
}
"""
class Assignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.DateTime)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    content = db.Column(db.JSON(True))
    # A one-to-many relationship: an assignment can have many submissions
    submissions = db.relationship('Submission', backref='assignment', lazy=True)

class Lecture(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    video_link = db.Column(db.String(256))

class Submission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_email = db.Column(db.String(120), nullable=False)
    assignment_id = db.Column(db.Integer, db.ForeignKey('assignment.id'), nullable=False)
    file_path = db.Column(db.String(256))
    submitted_at = db.Column(db.DateTime, default=db.func.now())

def check_cheating(query):
    forbidden_keywords = [ "solve", "answer", "solution"]
    return any(word in query.lower() for word in forbidden_keywords)

def clean_answer(answer):
    """Removes content enclosed within <think>...</think> tags."""
    return re.sub(r'<think>.*?</think>', '', answer, flags=re.DOTALL).strip()
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
        access_token = create_access_token(identity=user.email, additional_claims={"role": user.role}, expires_delta=False)
        response = jsonify({
            "success": True,
            "message": "Login successful",
            "role": user.role,
            "token": access_token
        })
        response.set_cookie(
            "access_token_cookie",
            access_token,
            secure=False,
            httponly=False,
            samesite="Lax",
        )
        return response
    
    return jsonify({"success": False, "message": "Invalid credentials"}), 401

# Protected Endpoint: Retrieve list of courses
@app.route('/api/courses', methods=['GET'])
@jwt_required(locations=["cookies"])
def get_courses():
    jwt = get_jwt_identity()
    user = User.query.filter_by(email=jwt).first()
    courses = user.courses
    courses_list = [
        {"id": course.course_id, "name": course.name, "description": course.description}
        for course in courses
    ]
    return jsonify(courses_list)

# Protected Endpoint: Retrieve course details (including dummy materials)
@app.route('/api/course/<course_id>', methods=['GET'])
@jwt_required(locations=["cookies"])
def get_course(course_id):
    course = Course.query.filter_by(course_id=course_id).first()
    if not course:
        return jsonify({"message": "Course not found"}), 404
    course = {
        "id": course.course_id,
        "name": course.name,
        "description": course.description,
        "assignments": [
            {
                "id": assignment.id,
                "title": assignment.title,
                "description": assignment.description,
                "due_date": assignment.due_date,
                "content": assignment.content
            }
            for assignment in course.assignments
        ],
        "lectures": [
            {
                "id": lecture.id,
                "title": lecture.title,
                "description": lecture.description,
                "video_link": lecture.video_link
            }
            for lecture in course.lectures
        ]
    }

    return jsonify(course)


# Protected Teacher Endpoint: Upload an assignment file
@app.route('/api/teacher/upload-assignment', methods=['POST'])
@jwt_required(locations=["cookies"])
def upload_assignment():
    identity = get_jwt_identity()
    if identity.get('role') != 'teacher':
        return jsonify({"message": "Unauthorized"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400
    
    assignment_title = data.get('title')
    assignment_description = data.get('description')
    due_date = data.get('due_date')
    course_id = data.get('course_id')
    content = data.get('content')

    if not assignment_title or not due_date or not course_id or not content:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    course = Course.query.filter_by(course_id=course_id).first()
    if not course:
        return jsonify({"success": False, "message": "Course not found"}), 404
    
    assignment = Assignment(
        title=assignment_title,
        description=assignment_description,
        due_date=datetime.strptime(due_date, "%Y-%m-%dT%H:%M:%S"),
        course_id=course.id,
        content=content
    )
    db.session.add(assignment)
    db.session.commit()
    return jsonify({"success": True, "message": "Assignment uploaded successfully"})

# Protected Teacher Endpoint: View submissions (dummy data)
@app.route('/api/teacher/view-submissions', methods=['GET'])
@jwt_required(locations=["cookies"])
def view_submissions():
    identity = get_jwt_identity()
    if identity.get('role') != 'teacher':
        return jsonify({"message": "Unauthorized"}), 403
    
    # TODO: get submissions
    return jsonify(["Yet to implement end point"])



# Protected Teacher Endpoint: Upload a lecture file
@app.route('/api/teacher/upload-lecture', methods=['POST'])
@jwt_required(locations=["cookies"])
def upload_lecture():
    identity = get_jwt_identity()
    if identity.get('role') != 'teacher':
        return jsonify({"message": "Unauthorized"}), 403

    data = request.get_json()
    if not data:
        return jsonify({"success": False, "message": "No data provided"}), 400
    
    lecture_title = data.get('title')
    lecture_description = data.get('description')
    course_id = data.get('course_id')
    video_link = data.get('video_link')

    if not lecture_title or not course_id or not video_link:
        return jsonify({"success": False, "message": "Missing required fields"}), 400
    
    course = Course.query.filter_by(course_id=course_id).first()
    if not course:
        return jsonify({"success": False, "message": "Course not found"}), 404
    
    lecture = Lecture(
        title=lecture_title,
        description=lecture_description,
        course_id=course.id,
        video_link=video_link
    )

    db.session.add(lecture)
    db.session.commit()
    return jsonify({"success": True, "message": "Lecture uploaded successfully"})

@app.route("/api/rag/add_document", methods=["POST"])
def add_document():
    data = request.json
    doc_text = data.get("text")
    doc_id = data.get("id")

    if not doc_text or not doc_id:
        return jsonify({"error": "Missing text or id"}), 400

    embedding = embed_model.encode(doc_text).tolist()
    collection.add(ids=[doc_id], embeddings=[embedding], metadatas=[{"text": doc_text}])

    return jsonify({"message": "Document added"})

# Function to query RAG
@app.route("/api/rag/query", methods=["POST"])
def query_rag():
    data = request.json
    user_query = data.get("query")

    if not user_query:
        return jsonify({"error": "Missing query"}), 400

    if check_cheating(user_query):
        return jsonify({"error": "Cheating detected"}), 403

    query_embedding = embed_model.encode(user_query).tolist()
    results = collection.query(query_embeddings=[query_embedding], n_results=5)

    retrieved_docs = [doc["text"] for doc in results["metadatas"][0]]
    context = "\n".join(retrieved_docs)

    # Pass retrieved context to LLM
    response = client.chat(model=MODEL, messages=[
    {"role": "system", "content": "Use the context to answer accurately in less than 4 lines."},
    {"role": "user", "content": f"Context: {context}\nQuestion: {user_query}"}
])

    return jsonify({
        "query": user_query,
        "answer": clean_answer(response["message"]["content"]),
        "sources": retrieved_docs
    })

@app.route("/api/llm/query", methods=["POST"])
def query_llm():
    data = request.json
    user_query = data.get("query")

    if not user_query:
        return jsonify({"error": "Missing query"}), 400

    response = client.chat(model=MODEL, messages=[
        {"role": "user", "content": user_query}
    ])

    return jsonify({
        "query": user_query,
        "answer": response["message"]["content"]
    })

# Health Check
@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"})

# Serve static files (e.g., lecture videos) from the "public" folder
@app.route('/static/<path:filename>', methods=['GET'])
def serve_static(filename):
    return send_from_directory(os.path.join(os.getcwd(), "public"), filename)

if __name__ == '__main__':
    app.run(debug=True)
