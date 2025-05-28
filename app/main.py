from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from redis import Redis
from typing import List

import os

app = FastAPI()

class Stock(BaseModel):
    product_id: int
    quantity: int
    category: str

class StockResponse(Stock):
    id: int

def get_redis():
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return Redis.from_url(redis_url)

@app.post("/stock/", response_model=StockResponse)
def create_product_stock(stock: Stock):
    redis = get_redis()
    stock_id = redis.incr("stock_id")
    stock_key = f"stock:{stock_id}"

    redis.hset(stock_key, mapping={
        "product_id": stock.product_id,
        "quantity": str(stock.quantity),
        "category": stock.category
    })

    return {**stock.model_dump(), "id": stock_id}

@app.get("/stock/", response_model=List[StockResponse])
def get_all_products_stocks():
    redis = get_redis()
    stock_ids = redis.keys("stock:*")

    stocks = []
    for key in stock_ids:
        stock_data = redis.hgetall(key)
        stocks.append({
            "id": key.decode().split(":")[1],
            "product_id": stock_data[b'product_id'].decode(),
            "quantity": int(stock_data[b'quantity']),
            "category": stock_data[b'category'].decode()
        })

    return stocks

@app.get("/stock/{stock_id}", response_model=StockResponse)
def get_stock_by_id(stock_id: int):
    redis = get_redis()
    stock_key = f"stock:{stock_id}"

    if not redis.exists(stock_key):
        raise HTTPException(status_code=404, detail="Stock information not found")

    stock_data = redis.hgetall(stock_key)

    return {
        "id": stock_id,
        "product_id": int(stock_data[b'product_id']),
        "quantity": int(stock_data[b'quantity']),
        "category": stock_data[b'category'].decode()
    }

@app.put("/stock/{stock_id}", response_model=dict)
def update_stock(stock_id: int, stock: Stock):
    redis = get_redis()
    stock_key = f"stock:{stock_id}"

    if not redis.exists(stock_key):
        raise HTTPException(status_code=404, detail="Stock information not found")

    redis.hset(stock_key, mapping={
        "product_id": stock.product_id,
        "quantity": str(stock.quantity),
        "category": stock.category
    })

    return {**stock.model_dump(), "id": stock_id}

@app.delete("/stock/{stock_id}")
def delete_stock(stock_id: int):
    redis = get_redis()
    stock_key = f"stock:{stock_id}"

    if not redis.exists(stock_key):
        raise HTTPException(status_code=404, detail="Stock information not found")

    redis.delete(stock_key)
    return {"message": "Stock information deleted"}