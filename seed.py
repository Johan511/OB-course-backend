# seed.py
from app import app, db, Course, User, Assignment, Lecture  # Import your app and models
import chromadb
from sentence_transformers import SentenceTransformer
import datetime

chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="documents")
embed_model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")

def seed_data():
    # Seed Courses if none exist
    if Course.query.count() == 0:
        course1 = Course(course_id="course1", name="Introduction to Biology", description="Learn the basics of biology.")
        course2 = Course(course_id="course2", name="Advanced Mathematics", description="Deep dive into mathematical theories.")
        course3 = Course(course_id="course3", name="Modern History", description="Explore modern historical events.")
        db.session.add_all([course1, course2, course3])
        db.session.commit()
        print("Courses seeded.")
    else:
        print("Courses already seeded.")

    # Seed default users if they don't exist
    if User.query.filter_by(email="teacher@example.com").first() is None:
        teacher = User(email="teacher@example.com", role="teacher", id=0)
        teacher.set_password("password")
        db.session.add(teacher)
        print("Teacher user seeded.")
    
    if User.query.filter_by(email="student@example.com").first() is None:
        student = User(email="student@example.com", role="student", id=1)
        student.set_password("password")
        db.session.add(student)
        print("Student user seeded.")

    # Enroll student in course
    user = User.query.filter_by(id=1).first() 
    course = Course.query.filter_by(course_id="course1").first()

    lectures = course.lectures
    if(len(lectures) == 0):
        # Add lectures to the course
        lecture1 = Lecture(
            title = "Lecture 1: Introduction to Biology",
            description = "This is the content of lecture 1.",
            course_id = course.course_id,
            video_link = "https://www.youtube.com/watch?v=example1",
            transcript = """The Cell: Basic Unit of Life
    Cells are the fundamental units of life, forming the structural and functional basis of all organisms. There are two main types:

    Prokaryotic Cells: Simple cells without a nucleus (e.g., bacteria).

    Eukaryotic Cells: Complex cells with a nucleus and organelles (e.g., plant and animal cells).
    Cell organelles like the nucleus, mitochondria, and ribosomes play essential roles in maintaining life processes.""",
        )
        lecture2 = Lecture(
            course_id = course.course_id,
            title = "Lecture 2: Cell Biology",
            description = "This is the content of lecture 2.",
            video_link = "https://www.youtube.com/watch?v=example2",
            transcript = """DNA & Genetics
DNA (Deoxyribonucleic Acid) carries genetic instructions. Key concepts:

Genes: Segments of DNA coding for proteins.

Chromosomes: Structures holding DNA in cells.

Mutation: Changes in DNA sequence leading to genetic variation.

Heredity: Transmission of traits from parents to offspring.""",
        )
        course.lectures.append(lecture1)
        course.lectures.append(lecture2)

    if course not in user.courses:
        user.courses.append(course)
    else:
        print(f"${user.email} is already enrolled in ${course.name}")

    # Add assignment to the course
    if len(course.assignments) == 0:
        assignment_content = [
            {
                "question": "What is the cell theory?",
                "options": ["Alpha", "Beta", "Gamma", "Delta"],
                "correct_option": "Alpha"
            },
            {
                "question": "What is the endoplasmic reticulum?",
                "options": ["Alpha", "Beta"],
                "correct_option": "Beta"
            }
        ]
        assignment = Assignment(title="Assignment 1", description="Complete the assignment", 
                                due_date=datetime.datetime.now() + datetime.timedelta(days=365), 
                                course_id=course.course_id, content=assignment_content)
        course.assignments.append(assignment)

    db.session.commit()

    rag_content = ["""
1. The Cell: Basic Unit of Life
    Cells are the fundamental units of life, forming the structural and functional basis of all organisms. There are two main types:

    Prokaryotic Cells: Simple cells without a nucleus (e.g., bacteria).

    Eukaryotic Cells: Complex cells with a nucleus and organelles (e.g., plant and animal cells).
    Cell organelles like the nucleus, mitochondria, and ribosomes play essential roles in maintaining life processes.
    """,
    """  
DNA & Genetics
DNA (Deoxyribonucleic Acid) carries genetic instructions. Key concepts:

Genes: Segments of DNA coding for proteins.

Chromosomes: Structures holding DNA in cells.

Mutation: Changes in DNA sequence leading to genetic variation.

Heredity: Transmission of traits from parents to offspring.
    """,
    """
    Evolution & Natural Selection
Evolution explains species' adaptation over time. Charles Darwin proposed:

Natural Selection: Favorable traits increase survival chances.

Adaptation: Genetic changes enhancing survival.

Speciation: Formation of new species due to genetic divergence.
    """,
    """
    Human Body Systems
The human body consists of interconnected systems:

Circulatory System: Heart and blood vessels transport nutrients and oxygen.

Digestive System: Breaks down food and absorbs nutrients.

Nervous System: Brain and nerves control body functions.

Respiratory System: Lungs facilitate oxygen intake and carbon dioxide removal.
    """,
    """
    Ecology & Environment
Ecology studies organisms and their environment. Key concepts:

Ecosystem: A community of organisms interacting with their surroundings.

Food Chain: Energy transfer from producers to consumers.

Biodiversity: Variety of life forms in an ecosystem.

Sustainability: Practices to maintain ecological balance.
    """] 
    for i in rag_content:
        embedding = embed_model.encode(i).tolist()
        collection.add(ids=[f"doc_{rag_content.index(i)}"], embeddings=[embedding], metadatas=[{"text": i}])

    print("Seeding complete.")

if __name__ == '__main__':
    with app.app_context():
        seed_data()
