import pytest
import importlib.util

spec = importlib.util.spec_from_file_location("main_app", "app.py")
main_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_app)
app = main_app.app

from app.database import init_db

@pytest.fixture(scope="module")
def test_client():
    app.config["TESTING"] = True
    init_db()
    with app.test_client() as client:
        yield client

def test_health(test_client):
    response = test_client.get("/health")
    assert response.status_code == 200

def test_create_todo(test_client):
    response = test_client.post("/todos/", json={"title": "Buy milk"})
    assert response.status_code == 201
    assert response.json["title"] == "Buy milk"
