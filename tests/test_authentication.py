def register_and_log_in(client):
    registration = client.post(
        "/register",
        data={
            "student_id": "S100",
            "full_name": "Ada Student",
            "email": "ada@example.com",
            "password": "longpassword",
        },
    )
    assert registration.status_code == 302

    return client.post(
        "/login",
        data={"email": "ada@example.com", "password": "longpassword"},
    )


def test_valid_credentials_grant_access_to_protected_page(client):
    response = register_and_log_in(client)

    assert response.status_code == 302
    assert response.location.endswith("/")
    assert client.get("/").status_code == 200


def test_invalid_credentials_show_error_and_do_not_authenticate(client):
    register_and_log_in(client)

    response = client.post(
        "/login",
        data={"email": "ada@example.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401
    assert b"Invalid email/student ID or password" in response.data
    assert client.get("/").status_code == 302


def test_unauthenticated_student_is_redirected_from_protected_page(client):
    response = client.get("/")

    assert response.status_code == 302
    assert response.location.endswith("/login")
    assert b"Please log in to access this page." in client.get(
        response.location
    ).data


def test_logout_ends_access_to_protected_page(client):
    register_and_log_in(client)

    response = client.post("/logout")

    assert response.status_code == 302
    assert response.location.endswith("/login")
    assert client.get("/").status_code == 302
