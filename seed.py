# seed.py
from app import app, db, Course, User  # Import your app and models

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
        teacher = User(email="teacher@example.com", role="teacher")
        teacher.set_password("password")
        db.session.add(teacher)
        print("Teacher user seeded.")
    
    if User.query.filter_by(email="student@example.com").first() is None:
        student = User(email="student@example.com", role="student")
        student.set_password("password")
        db.session.add(student)
        print("Student user seeded.")
    
    db.session.commit()
    print("Seeding complete.")

if __name__ == '__main__':
    with app.app_context():
        seed_data()
