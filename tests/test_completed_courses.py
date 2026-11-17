from app import db
from app.models import Course, Student


def register_and_log_in(client):
    client.post(
        "/register",
        data={
            "student_id": "S100",
            "full_name": "Ada Student",
            "email": "ada@example.com",
            "password": "longpassword",
        },
    )
    client.post(
        "/login",
        data={"email": "ada@example.com", "password": "longpassword"},
    )


def add_course(client, **overrides):
    data = {
        "course_identifier": "CS101",
        "course_name": "Introduction to Computing",
        "credit_hours": "3",
        "letter_grade": "A",
    }
    data.update(overrides)
    return client.post("/courses", data=data)


def test_authenticated_student_adds_completed_course(app, client):
    register_and_log_in(client)

    response = add_course(client)

    assert response.status_code == 302
    with app.app_context():
        student = Student.query.filter_by(student_id="S100").one()
        course = Course.query.filter_by(student_id=student.id).one()
        assert course.course_identifier == "CS101"
        assert course.course_name == "Introduction to Computing"
        assert course.credit_hours == 3
        assert course.letter_grade == "A"
    page = client.get("/")
    assert b"CS101" in page.data
    assert b"Introduction to Computing" in page.data


def test_completed_course_page_requires_authentication(client):
    response = client.get("/courses")

    assert response.status_code == 302
    assert response.location.endswith("/login")


def test_authenticated_student_views_all_completed_course_details(client):
    register_and_log_in(client)
    assert add_course(client).status_code == 302
    assert add_course(
        client,
        course_identifier="CS102",
        course_name="Data Structures",
        credit_hours="4",
        letter_grade="B",
    ).status_code == 302

    response = client.get("/completed-courses")

    assert response.status_code == 200
    assert b"CS101" in response.data
    assert b"Introduction to Computing" in response.data
    assert b"3" in response.data
    assert b"A" in response.data
    assert b"CS102" in response.data
    assert b"Data Structures" in response.data
    assert b"4" in response.data
    assert b"B" in response.data
    assert b"Earned letter grade" in response.data


def test_student_with_no_completed_courses_sees_empty_message(client):
    register_and_log_in(client)

    response = client.get("/completed-courses")

    assert response.status_code == 200
    assert b"No completed courses recorded." in response.data
    assert b"class=\"empty-state\"" in response.data
    assert b"No GPA available." in response.data


def test_completed_courses_are_scoped_to_authenticated_student(client):
    register_and_log_in(client)
    assert add_course(client).status_code == 302

    client.post("/logout")
    client.post(
        "/register",
        data={
            "student_id": "S200",
            "full_name": "Grace Student",
            "email": "grace@example.com",
            "password": "longpassword",
        },
    )
    client.post(
        "/login",
        data={"email": "grace@example.com", "password": "longpassword"},
    )

    response = client.get("/completed-courses")

    assert response.status_code == 200
    assert b"CS101" not in response.data
    assert b"Introduction to Computing" not in response.data
    assert b"No completed courses recorded." in response.data


def test_missing_completed_course_field_is_rejected(app, client):
    register_and_log_in(client)

    response = add_course(client, course_name="")

    assert response.status_code == 400
    assert b"All course fields are required" in response.data
    with app.app_context():
        assert Course.query.count() == 0


def test_invalid_credit_hours_are_rejected(app, client):
    register_and_log_in(client)

    for credits in ("0", "-1", "2.5", "abc"):
        response = add_course(client, credit_hours=credits)
        assert response.status_code == 400
        assert b"Credit hours must be a positive whole number" in response.data

    with app.app_context():
        assert Course.query.count() == 0


def test_invalid_letter_grade_is_rejected(app, client):
    register_and_log_in(client)

    response = add_course(client, letter_grade="Z")

    assert response.status_code == 400
    assert b"Letter grade must be one of A, B, C, D, or F" in response.data
    with app.app_context():
        assert Course.query.count() == 0


def test_duplicate_course_identifier_is_rejected(app, client):
    register_and_log_in(client)
    assert add_course(client).status_code == 302

    response = add_course(client, course_name="Another Name")

    assert response.status_code == 400
    assert b"already recorded" in response.data
    with app.app_context():
        assert Course.query.count() == 1


def test_duplicate_course_identifier_is_scoped_per_student(app, client):
    register_and_log_in(client)
    assert add_course(client).status_code == 302

    client.post("/logout")
    client.post(
        "/register",
        data={
            "student_id": "S200",
            "full_name": "Grace Student",
            "email": "grace@example.com",
            "password": "longpassword",
        },
    )
    client.post(
        "/login",
        data={"email": "grace@example.com", "password": "longpassword"},
    )

    response = add_course(client)

    assert response.status_code == 302
    with app.app_context():
        assert Course.query.count() == 2


def test_gpa_is_credit_weighted_and_updated(app, client):
    register_and_log_in(client)
    assert add_course(client, credit_hours="3", letter_grade="A").status_code == 302
    assert add_course(
        client,
        course_identifier="CS102",
        course_name="Data Structures",
        credit_hours="1",
        letter_grade="C",
    ).status_code == 302

    with app.app_context():
        student = Student.query.filter_by(student_id="S100").one()
        assert student.gpa == 3.5


def test_completed_courses_page_displays_gpa_with_two_decimal_places(client):
    register_and_log_in(client)
    assert add_course(client, credit_hours="3", letter_grade="A").status_code == 302
    assert add_course(
        client,
        course_identifier="CS102",
        course_name="Data Structures",
        credit_hours="1",
        letter_grade="C",
    ).status_code == 302

    response = client.get("/completed-courses")

    assert response.status_code == 200
    assert b"3.50" in response.data
