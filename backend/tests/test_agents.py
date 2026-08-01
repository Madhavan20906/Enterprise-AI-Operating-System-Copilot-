from unittest.mock import patch

def test_chat_unauthorized(client):
    response = client.post("/api/v1/chat/", json={"query": "Hello"})
    assert response.status_code == 401

@patch("app.api.routes.chat.agent_graph.invoke")
def test_chat_sync(mock_invoke, client):
    # Mock return value of LangGraph execution
    mock_invoke.return_value = {
        "final_response": "This is a mock answer from the agent graph."
    }

    # Register & Login
    client.post(
        "/api/v1/users/",
        json={"email": "chatter@enterprise.com", "password": "ChatPassword123!", "full_name": "Chatter User"}
    )
    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": "chatter@enterprise.com", "password": "ChatPassword123!"}
    )
    token = login_response.json()["access_token"]
    
    # Create thread
    conv_response = client.post(
        "/api/v1/chat/conversations",
        headers={"Authorization": f"Bearer {token}"}
    )
    conv_id = conv_response.json()["id"]

    # Send Chat message
    response = client.post(
        "/api/v1/chat/",
        headers={"Authorization": f"Bearer {token}"},
        json={"query": "What is Project Alpha?", "conversation_id": conv_id}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "This is a mock answer from the agent graph."
    assert data["conversation_id"] == conv_id
