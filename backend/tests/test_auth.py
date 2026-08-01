def test_register_user(client):
    response = client.post(
        "/api/v1/users/",
        json={"email": "test@enterprise.com", "password": "TestPassword123!", "full_name": "Test User"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test@enterprise.com"
    assert "id" in data

def test_login_user(client):
    # Register first
    client.post(
        "/api/v1/users/",
        json={"email": "login@enterprise.com", "password": "LoginPassword123!", "full_name": "Login User"}
    )
    
    # Login
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "login@enterprise.com", "password": "LoginPassword123!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_get_me(client):
    # Register & Login
    client.post(
        "/api/v1/users/",
        json={"email": "me@enterprise.com", "password": "MePassword123!", "full_name": "Me User"}
    )
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "me@enterprise.com", "password": "MePassword123!"}
    )
    token = login_response.json()["access_token"]
    
    # Get Me details
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@enterprise.com"
    assert data["full_name"] == "Me User"
