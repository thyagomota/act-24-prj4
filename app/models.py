from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import synonym

from app import db


class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(50), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    gpa = db.Column(db.Float, nullable=False, default=0.0)
    courses = db.relationship("Course", back_populates="student", cascade="all, delete-orphan")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Course(db.Model):
    __tablename__ = "course"
    __table_args__ = (
        UniqueConstraint("student_id", "course_identifier", name="uq_student_course"),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student.id"), nullable=False)
    course_identifier = db.Column(db.String(50), nullable=False)
    course_name = db.Column(db.String(120), nullable=False)
    credit_hours = db.Column(db.Integer, nullable=False)
    letter_grade = db.Column(db.String(1), nullable=False)
    student = db.relationship("Student", back_populates="courses")

    course_id = synonym("course_identifier")
    course_code = synonym("course_identifier")
    course_title = synonym("course_name")
    credits = synonym("credit_hours")
    grade = synonym("letter_grade")


CompletedCourse = Course
