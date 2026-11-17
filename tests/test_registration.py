import pytest

from app import db
from app.models import Student


def register(client, **overrides):
    data = {
        "student_id": "S100",
        "full_name": "Ada Student",
        "email": "ada@example.com",
        "password": "longpassword",
    }
    data.update(overrides)
    return client.post("/register", data=data)


def test_registration_creates_account_and_password_is_hashed(app, client):
    response = register(client)

    assert response.status_code == 302
    with app.app_context():
        student = Student.query.filter_by(student_id="S100").first()
        assert student is not None
        assert student.full_name == "Ada Student"
        assert student.email == "ada@example.com"
        assert student.password_hash != "longpassword"
        assert student.check_password("longpassword")


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("student_id", "", "All fields are required."),
        ("full_name", "", "All fields are required."),
        ("email", "", "All fields are required."),
        ("password", "", "All fields are required."),
        ("email", "not-an-email", "Enter a valid email address."),
        ("password", "short", "Password must be at least 8 characters long."),
    ],
)
def test_invalid_registration_is_rejected(app, client, field, value, message):
    response = register(client, **{field: value})

    assert response.status_code == 400
    assert message.encode() in response.data
    with app.app_context():
        assert Student.query.count() == 0


def test_duplicate_student_id_is_rejected(app, client):
    assert register(client).status_code == 302

    response = register(
        client,
        full_name="Another Student",
        email="another@example.com",
    )

    assert response.status_code == 400
    assert b"student ID is already registered" in response.data
    with app.app_context():
        assert Student.query.count() == 1


def test_duplicate_email_is_rejected(app, client):
    assert register(client).status_code == 302

    response = register(
        client,
        student_id="S200",
        full_name="Another Student",
    )

    assert response.status_code == 400
    assert b"email address is already registered" in response.data
    with app.app_context():
        assert Student.query.count() == 1


def test_registered_student_can_log_in(client):
    assert register(client).status_code == 302

    response = client.post(
        "/login",
        data={"email": "ada@example.com", "password": "longpassword"},
    )

    assert response.status_code == 302
    assert response.location.endswith("/")


def test_registered_student_can_log_in_with_student_id(client):
    assert register(client).status_code == 302

    response = client.post(
        "/login",
        data={"student_id": "S100", "password": "longpassword"},
    )

    assert response.status_code == 302
    assert response.location.endswith("/")


def test_invalid_login_credentials_are_rejected(client):
    assert register(client).status_code == 302

    response = client.post(
        "/login",
        data={"email": "ada@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert b"Invalid email/student ID or password" in response.data
