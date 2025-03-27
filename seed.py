# seed.py
from app import app, db, Course, User, Assignment  # Import your app and models
import datetime

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
                "correct_answer": 0
            },
            {
                "question": "What is the endoplasmic reticulum?",
                "options": ["Alpha", "Beta"],
                "correct_answer": 1
            }
        ]
        assignment = Assignment(title="Assignment 1", description="Complete the assignment", 
                                due_date=datetime.datetime.now() + datetime.timedelta(days=365), 
                                course_id=course.course_id, content=assignment_content)
        course.assignments.append(assignment)

    db.session.commit()
    print("Seeding complete.")

if __name__ == '__main__':
    with app.app_context():
        seed_data()
