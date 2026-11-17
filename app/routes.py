import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app import db
from app.models import Student


bp = Blueprint("main", __name__)

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@bp.route("/")
def index():
    return render_template("index.html")


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
            flash("Invalid email/student ID or password.", "error")
            return render_template("login.html"), 401

        session["student_id"] = student.id
        session["user_id"] = student.id
        flash("Logged in successfully.", "success")
        return redirect(url_for("main.index"))

    return render_template("login.html")


def validate_registration(student_id, full_name, email, password):
    """Validate registration fields and return an error message, if any."""
    if not student_id or not full_name or not email or not password:
        return "All fields are required."
    if not EMAIL_PATTERN.match(email):
        return "Enter a valid email address."
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    return None
