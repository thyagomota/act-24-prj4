from functools import wraps
import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app import db
from app.models import Course, Student


bp = Blueprint("main", __name__)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def login_required(view):
    """Redirect visitors to login unless they have an authenticated session."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("user_id") is None:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("main.login"))
        return view(*args, **kwargs)

    return wrapped_view


@bp.route("/")
@login_required
def index():
    student = Student.query.get(session["user_id"])
    courses = Course.query.filter_by(student_id=student.id).order_by(
        Course.course_identifier
    ).all()
    return render_template(
        "index.html",
        student=student,
        courses=courses,
        gpa=calculate_gpa(courses),
    )


@bp.route("/courses", methods=["GET", "POST"])
@bp.route("/completed-courses", methods=["GET", "POST"])
@login_required
def courses():
    student = Student.query.get(session["user_id"])
    if request.method == "POST":
        error = add_completed_course(student)
        if error:
            flash(error, "error")
            courses = get_student_courses(student)
            return render_template(
                "courses.html",
                student=student,
                courses=courses,
                gpa=calculate_gpa(courses),
            ), 400
        flash("Course added successfully.", "success")
        return redirect(url_for("main.courses"))

    courses = get_student_courses(student)
    return render_template(
        "courses.html",
        student=student,
        courses=courses,
        gpa=calculate_gpa(courses),
    )


@bp.route("/courses/add", methods=["POST"])
@bp.route("/add-course", methods=["POST"])
@login_required
def add_course():
    student = Student.query.get(session["user_id"])
    error = add_completed_course(student)
    if error:
        flash(error, "error")
        courses = get_student_courses(student)
        return render_template(
            "courses.html",
            student=student,
            courses=courses,
            gpa=calculate_gpa(courses),
        ), 400
    flash("Course added successfully.", "success")
    return redirect(url_for("main.courses"))


@bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        student_id = request.form.get("student_id", "").strip()
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        error = validate_registration(student_id, full_name, email, password)
        if error is None:
            if Student.query.filter_by(student_id=student_id).first():
                error = "That student ID is already registered."
            elif Student.query.filter_by(email=email).first():
                error = "That email address is already registered."

        if error:
            flash(error, "error")
            return render_template("register.html"), 400

        student = Student(
            student_id=student_id,
            full_name=full_name,
            email=email,
        )
        student.set_password(password)
        db.session.add(student)
        db.session.commit()
        flash("Registration successful.", "success")
        return redirect(url_for("main.login"))

    return render_template("register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = (
            request.form.get("email")
            or request.form.get("student_id")
            or request.form.get("identifier")
            or ""
        ).strip()
        password = request.form.get("password", "")

        if not identifier or not password:
            flash("Email/student ID and password are required.", "error")
            return render_template("login.html"), 400

        student = (
            Student.query.filter(
                db.func.lower(Student.email) == identifier.lower()
            ).first()
            or Student.query.filter_by(student_id=identifier).first()
        )
        if student is None or not student.check_password(password):
            session.pop("student_id", None)
            session.pop("user_id", None)
            flash("Invalid email/student ID or password.", "error")
            return render_template("login.html"), 401

        session["student_id"] = student.id
        session["user_id"] = student.id
        flash("Logged in successfully.", "success")
        return redirect(url_for("main.index"))

    return render_template("login.html")


@bp.route("/logout", methods=["POST"])
def logout():
    """End the current student's authenticated session."""
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.login"))


def validate_registration(student_id, full_name, email, password):
    """Validate registration fields and return an error message, if any."""
    if not student_id or not full_name or not email or not password:
        return "All fields are required."
    if not EMAIL_PATTERN.match(email):
        return "Enter a valid email address."
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    return None


def get_student_courses(student):
    """Return one student's completed courses in identifier order."""
    return Course.query.filter_by(student_id=student.id).order_by(
        Course.course_identifier
    ).all()


def calculate_gpa(courses):
    """Calculate the credit-hour-weighted GPA for a course list."""
    grade_points = {"A": 4.0, "B": 3.0, "C": 2.0, "D": 1.0, "F": 0.0}
    total_credits = sum(course.credit_hours for course in courses)
    if total_credits == 0:
        return None
    weighted_points = sum(
        course.credit_hours * grade_points[course.letter_grade]
        for course in courses
    )
    return round(weighted_points / total_credits, 2)


def validate_completed_course(course_identifier, course_name, credit_hours,
                              letter_grade):
    """Validate completed-course fields and return an error message, if any."""
    if not course_identifier or not course_name or not credit_hours or not letter_grade:
        return "All course fields are required."
    if not re.fullmatch(r"[1-9]\d*", str(credit_hours)):
        return "Credit hours must be a positive whole number."
    if str(letter_grade).strip().upper() not in {"A", "B", "C", "D", "F"}:
        return "Letter grade must be one of A, B, C, D, or F."
    return None


def recalculate_gpa(student):
    """Recalculate and update a student's credit-weighted GPA."""
    courses = get_student_courses(student)
    student.gpa = calculate_gpa(courses) or 0.0


def add_completed_course(student):
    """Validate and add a completed course owned by the given student."""
    course_identifier = (
        request.form.get("course_identifier")
        or request.form.get("course_id")
        or request.form.get("course_code")
        or ""
    ).strip()
    course_name = (
        request.form.get("course_name")
        or request.form.get("name")
        or request.form.get("course_title")
        or ""
    ).strip()
    credit_hours = (
        request.form.get("credit_hours")
        or request.form.get("credits")
        or ""
    ).strip()
    letter_grade = (
        request.form.get("letter_grade")
        or request.form.get("grade")
        or ""
    ).strip().upper()

    error = validate_completed_course(
        course_identifier, course_name, credit_hours, letter_grade
    )
    if error:
        return error

    if Course.query.filter_by(
        student_id=student.id,
        course_identifier=course_identifier,
    ).first():
        return "A course with that course identifier is already recorded."

    course = Course(
        student_id=student.id,
        course_identifier=course_identifier,
        course_name=course_name,
        credit_hours=int(credit_hours),
        letter_grade=letter_grade,
    )
    db.session.add(course)
    db.session.flush()
    recalculate_gpa(student)
    db.session.commit()
    return None
