from fastapi.testclient import TestClient
from server import app

client = TestClient(app)


def test_get_notifications():
    response = client.get("/api/v1/notifications")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "unread_count" in data
    assert isinstance(data["items"], list)
    assert isinstance(data["unread_count"], int)


def test_mark_all_notifications_read():
    response = client.post("/api/v1/notifications/mark-all-read")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"

    # Verify unread count is now 0
    get_res = client.get("/api/v1/notifications")
    assert get_res.status_code == 200
    assert get_res.json()["unread_count"] == 0
