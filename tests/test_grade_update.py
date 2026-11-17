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


def add_course(client, grade="A", credits="3"):
    return client.post(
        "/courses",
        data={
            "course_identifier": "CS101",
            "course_name": "Introduction to Computing",
            "credit_hours": credits,
            "letter_grade": grade,
        },
    )


def test_completed_course_page_displays_grade_editor(client):
    register_and_log_in(client)
    assert add_course(client).status_code == 302

    response = client.get("/completed-courses")

    assert response.status_code == 200
    assert b"Update Grade" in response.data
    assert b"name=\"letter_grade\"" in response.data


def test_valid_grade_update_is_accepted_and_displayed(app, client):
    register_and_log_in(client)
    assert add_course(client).status_code == 302
    with app.app_context():
        course = Course.query.filter_by(course_identifier="CS101").one()
        course_id = course.id

    response = client.post(
        f"/courses/{course_id}/grade",
        data={"letter_grade": "B"},
    )

    assert response.status_code == 302
    with app.app_context():
        course = Course.query.get(course_id)
        assert course.letter_grade == "B"
    page = client.get("/completed-courses")
    assert b"B" in page.data


def test_invalid_grade_update_is_rejected(app, client):
    register_and_log_in(client)
    assert add_course(client).status_code == 302
    with app.app_context():
        course = Course.query.filter_by(course_identifier="CS101").one()
        course_id = course.id

    response = client.post(
        f"/courses/{course_id}/grade",
        data={"letter_grade": "Z"},
    )

    assert response.status_code == 400
    assert b"Letter grade must be one of A, B, C, D, or F" in response.data
    with app.app_context():
        course = Course.query.get(course_id)
        assert course.letter_grade == "A"


def test_grade_update_recalculates_credit_weighted_gpa(app, client):
    register_and_log_in(client)
    assert add_course(client, grade="A", credits="3").status_code == 302
    client.post(
        "/courses",
        data={
            "course_identifier": "CS102",
            "course_name": "Data Structures",
            "credit_hours": "1",
            "letter_grade": "C",
        },
    )
    with app.app_context():
        course = Course.query.filter_by(course_identifier="CS101").one()
        course_id = course.id

    assert client.post(
        f"/courses/{course_id}/grade",
        data={"letter_grade": "F"},
    ).status_code == 302

    with app.app_context():
        student = Student.query.filter_by(student_id="S100").one()
        assert student.gpa == 0.5


def test_grade_update_requires_authentication(client):
    response = client.post("/courses/1/grade", data={"letter_grade": "B"})

    assert response.status_code == 302
    assert response.location.endswith("/login")


def test_grade_update_is_scoped_to_authenticated_student(app, client):
    register_and_log_in(client)
    assert add_course(client).status_code == 302
    with app.app_context():
        course = Course.query.filter_by(course_identifier="CS101").one()
        course_id = course.id

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

    response = client.post(
        f"/courses/{course_id}/grade",
        data={"letter_grade": "F"},
    )

    assert response.status_code == 404
    with app.app_context():
        course = Course.query.get(course_id)
        assert course.letter_grade == "A"
