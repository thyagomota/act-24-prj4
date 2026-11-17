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


def add_course(client, identifier="CS101", name="Introduction", credits="3",
              grade="A"):
    return client.post(
        "/courses",
        data={
            "course_identifier": identifier,
            "course_name": name,
            "credit_hours": credits,
            "letter_grade": grade,
        },
    )


def test_completed_course_list_offers_delete_request(client):
    register_and_log_in(client)
    assert add_course(client).status_code == 302

    response = client.get("/completed-courses")

    assert response.status_code == 200
    assert b"Delete" in response.data


def test_delete_request_requires_confirmation_without_deleting(app, client):
    register_and_log_in(client)
    assert add_course(client).status_code == 302
    with app.app_context():
        course = Course.query.filter_by(course_identifier="CS101").one()
        course_id = course.id

    response = client.get(f"/courses/{course_id}/delete")

    assert response.status_code == 200
    assert b"Are you sure" in response.data
    assert b"Confirm Delete" in response.data
    assert b"Cancel" in response.data
    with app.app_context():
        assert Course.query.count() == 1


def test_confirmed_delete_removes_course_and_recalculates_gpa(app, client):
    register_and_log_in(client)
    assert add_course(client, credits="3", grade="A").status_code == 302
    assert add_course(
        client,
        identifier="CS102",
        name="Data Structures",
        credits="1",
        grade="C",
    ).status_code == 302
    with app.app_context():
        course = Course.query.filter_by(course_identifier="CS101").one()
        course_id = course.id

    response = client.post(
        f"/courses/{course_id}/delete",
        data={"confirm": "yes"},
    )

    assert response.status_code == 302
    with app.app_context():
        assert Course.query.filter_by(course_identifier="CS101").first() is None
        student = Student.query.filter_by(student_id="S100").one()
        assert student.gpa == 2.0


def test_cancelled_delete_keeps_course(app, client):
    register_and_log_in(client)
    assert add_course(client).status_code == 302
    with app.app_context():
        course = Course.query.filter_by(course_identifier="CS101").one()
        course_id = course.id

    response = client.post(
        f"/courses/{course_id}/delete",
        data={"cancel": "yes"},
    )

    assert response.status_code == 302
    with app.app_context():
        assert Course.query.count() == 1
        student = Student.query.filter_by(student_id="S100").one()
        assert student.gpa == 4.0


def test_delete_requires_authentication(client):
    response = client.get("/courses/1/delete")

    assert response.status_code == 302
    assert response.location.endswith("/login")


def test_delete_is_scoped_to_authenticated_student(app, client):
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
        f"/courses/{course_id}/delete",
        data={"confirm": "yes"},
    )

    assert response.status_code == 404
    with app.app_context():
        assert Course.query.filter_by(id=course_id).one().course_identifier == "CS101"
