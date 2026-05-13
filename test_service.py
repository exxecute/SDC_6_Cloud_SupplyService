from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


# -----------------------------
# Helpers
# -----------------------------

def create_mock_connection():
    mock_conn = MagicMock()
    mock_cursor = MagicMock()

    mock_conn.cursor.return_value = mock_cursor

    return mock_conn, mock_cursor


# -----------------------------
# Health Check
# -----------------------------

def test_health():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Supply Service is running"
    }


# -----------------------------
# Create Item
# -----------------------------

@patch("app.get_connection")
def test_create_item_success(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()
    mock_cursor.fetchone.return_value = [1]

    mock_get_connection.return_value = mock_conn

    payload = {
        "name": "Laptop",
        "description": "Dell XPS",
        "total_count": 10,
        "available_count": 10,
        "status": "available",
    }

    response = client.post("/items", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "message": "Item created successfully",
        "id": 1,
    }

    mock_conn.commit.assert_called_once()


# -----------------------------
# Get Items
# -----------------------------

@patch("app.get_connection")
def test_get_items(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()

    mock_cursor.fetchall.return_value = [
        (1, "Laptop", "Dell", 10, 10, "available")
    ]

    mock_cursor.description = [
        ("id",),
        ("name",),
        ("description",),
        ("total_count",),
        ("available_count",),
        ("status",),
    ]

    mock_get_connection.return_value = mock_conn

    response = client.get("/items")

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == 1
    assert data[0]["name"] == "Laptop"


# -----------------------------
# Get Single Item
# -----------------------------

@patch("app.get_connection")
def test_get_item_success(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()

    mock_cursor.fetchone.return_value = (
        1, "Laptop", "Dell", 10, 10, "available"
    )

    mock_cursor.description = [
        ("id",),
        ("name",),
        ("description",),
        ("total_count",),
        ("available_count",),
        ("status",),
    ]

    mock_get_connection.return_value = mock_conn

    response = client.get("/items/1")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == 1
    assert data["name"] == "Laptop"


@patch("app.get_connection")
def test_get_item_not_found(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()

    mock_cursor.fetchone.return_value = None

    mock_get_connection.return_value = mock_conn

    response = client.get("/items/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


# -----------------------------
# Update Item
# -----------------------------

@patch("app.get_connection")
def test_update_item_success(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()
    mock_get_connection.return_value = mock_conn

    payload = {"name": "Updated Laptop"}

    response = client.put("/items/1", json=payload)

    assert response.status_code == 200
    assert response.json() == {
        "message": "Item updated successfully"
    }

    mock_conn.commit.assert_called_once()


@patch("app.get_connection")
def test_update_item_no_fields(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()
    mock_get_connection.return_value = mock_conn

    response = client.put("/items/1", json={})

    assert response.status_code == 500


# -----------------------------
# Delete Item
# -----------------------------

@patch("app.get_connection")
def test_delete_item_success(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()

    mock_cursor.rowcount = 1
    mock_get_connection.return_value = mock_conn

    response = client.delete("/items/1")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Item deleted successfully"
    }


@patch("app.get_connection")
def test_delete_item_not_found(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()

    mock_cursor.rowcount = 0
    mock_get_connection.return_value = mock_conn

    response = client.delete("/items/999")

    assert response.status_code == 500


# -----------------------------
# Reserve Item
# -----------------------------

@patch("app.get_connection")
def test_reserve_item_success(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()

    mock_cursor.fetchone.side_effect = [(10,), (5,)]
    mock_get_connection.return_value = mock_conn

    payload = {
        "rental_id": 101,
        "reserved_count": 2,
    }

    response = client.post("/items/1/reserve", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["reservation_id"] == 5
    assert data["available_count"] == 8


@patch("app.get_connection")
def test_reserve_item_not_enough_stock(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()

    mock_cursor.fetchone.return_value = (1,)
    mock_get_connection.return_value = mock_conn

    payload = {
        "rental_id": 101,
        "reserved_count": 5,
    }

    response = client.post("/items/1/reserve", json=payload)

    assert response.status_code == 500


# -----------------------------
# Release Item
# -----------------------------

@patch("app.get_connection")
def test_release_item_success(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()

    mock_cursor.fetchone.side_effect = [(1, 2, "reserved"), (8,)]
    mock_get_connection.return_value = mock_conn

    payload = {
        "rental_id": 101,
        "reserved_count": 2,
    }

    response = client.post("/items/1/release", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert data["message"] == "Reservation released successfully"
    assert data["available_count"] == 10


@patch("app.get_connection")
def test_release_item_not_found(mock_get_connection):

    mock_conn, mock_cursor = create_mock_connection()

    mock_cursor.fetchone.return_value = None
    mock_get_connection.return_value = mock_conn

    payload = {
        "rental_id": 101,
        "reserved_count": 2,
    }

    response = client.post("/items/1/release", json=payload)

    assert response.status_code == 500
