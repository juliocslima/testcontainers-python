import sys
import os
from pathlib import Path

# Adiciona o diretório raiz do projeto ao PATH
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
import os
from testcontainers.redis import RedisContainer
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture(scope="session")
def redis_container():
  with RedisContainer() as container:
    # Configura a aplicação para usar o Redis do container
    os.environ["REDIS_URL"] = f"redis://{container.get_container_host_ip()}:{container.get_exposed_port(6379)}/0"
    yield container

@pytest.fixture
def client(redis_container):
    return TestClient(app)

@pytest.fixture(autouse=True)
def clean_redis(redis_container):
    redis = redis_container.get_client()
    redis.flushall()

def test_create_stock(client):
  response = client.post(
    "/stock/",
    json={
      "product_id": 1,
      "quantity": 100,
      "category": "electronics"
    }
  )
  assert response.status_code == 200
  result = response.json()
  assert result["id"] == 1
  assert result["product_id"] == 1
  assert result["quantity"] == 100

def test_get_all_stocks(client):
    # Cria dois registros
    client.post("/stock/", json={"product_id": 1, "quantity": 100, "category": "electronics"})
    client.post("/stock/", json={"product_id": 2, "quantity": 50, "category": "books"})

    response = client.get("/stock/")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 2
    assert {item["product_id"] for item in data} == {1, 2}
    assert {item["category"] for item in data} == {"electronics", "books"}

def test_get_stock_by_id(client):
    # Create test stock
    create_response = client.post(
        "/stock/",
        json={"product_id": 1, "quantity": 100, "category": "electronics"}
    )
    stock_id = create_response.json()["id"]

    # Test successful retrieval
    get_response = client.get(f"/stock/{stock_id}")
    assert get_response.status_code == 200
    data = get_response.json()

    assert data["id"] == stock_id
    assert data["product_id"] == 1
    assert data["quantity"] == 100
    assert data["category"] == "electronics"

def test_update_stock(client):
  # Cria e atualiza
  create_response = client.post(
        "/stock/",
        json={"product_id": 1, "quantity": 100, "category": "electronics"}
    )

  stock_id = create_response.json()["id"]

  update_response = client.put(
    f"/stock/{stock_id}",
    json={"product_id": 1, "quantity": 75, "category": "updated"}
  )

  assert update_response.status_code == 200
  updated = update_response.json()
  assert updated["quantity"] == 75
  assert updated["category"] == "updated"

def test_delete_stock(client):
  # Cria e deleta
  create_response = client.post(
        "/stock/",
        json={"product_id": 1, "quantity": 100, "category": "electronics"}
    )

  stock_id = create_response.json()["id"]

  delete_response = client.delete(f"/stock/{stock_id}")
  assert delete_response.status_code == 200
  assert delete_response.json()["message"] == "Stock information deleted"

  # Verifica se foi removido
  response = client.get("/stock/")
  assert len(response.json()) == 0

def test_not_found_exceptions(client):
  # Testa erros em endpoints com ID específico
  response = client.get("/stock/999")
  assert response.status_code == 404

  response = client.put("/stock/999", json={"product_id": 1, "quantity": 100, "category": "test"})
  assert response.status_code == 404

  response = client.delete("/stock/999")
  assert response.status_code == 404