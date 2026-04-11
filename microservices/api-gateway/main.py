"""API Gateway - Port 8000"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import sys
sys.path.append('/app')

from shared.redis import get_cache, set_cache, rate_limit
from shared.schemas import TransactionCreate, TransactionResponse, PredictionResponse, DashboardResponse

app = FastAPI(title="Gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TRANSACTIONS_URL = "http://transactions:8001"
AI_URL = "http://ai:8002"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/transactions", response_model=TransactionResponse)
async def create_transaction(txn: TransactionCreate):
    if not await rate_limit(txn.user_id):
        raise HTTPException(429, "Rate limit exceeded")

    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(f"{TRANSACTIONS_URL}/transactions", json=txn.model_dump(mode='json'))
        resp.raise_for_status()
        return resp.json()


@app.get("/api/transactions/{user_id}", response_model=list[TransactionResponse])
async def get_transactions(user_id: int, limit: int = 50):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{TRANSACTIONS_URL}/transactions/{user_id}?limit={limit}")
        resp.raise_for_status()
        return resp.json()


@app.get("/api/dashboard/{user_id}", response_model=DashboardResponse)
async def get_dashboard(user_id: int):
    cache_key = f"dashboard:{user_id}"
    cached = await get_cache(cache_key)
    if cached:
        return cached

    async with httpx.AsyncClient(timeout=5.0) as client:
        balance_resp = await client.get(f"{TRANSACTIONS_URL}/balance/{user_id}")
        txns_resp = await client.get(f"{TRANSACTIONS_URL}/transactions/{user_id}?limit=10")

        try:
            pred_resp = await client.get(f"{AI_URL}/predict/{user_id}")
            prediction = pred_resp.json() if pred_resp.status_code == 200 else None
        except:
            prediction = None

        balance_resp.raise_for_status()
        txns_resp.raise_for_status()

        dashboard = {
            **balance_resp.json(),
            "prediction": prediction,
            "recent_transactions": txns_resp.json()
        }

        await set_cache(cache_key, dashboard, ttl=30)
        return dashboard


@app.post("/api/predict/{user_id}", response_model=PredictionResponse)
async def trigger_prediction(user_id: int):
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(f"{AI_URL}/predict/{user_id}")
        resp.raise_for_status()
        return resp.json()


@app.get("/api/predict/{user_id}", response_model=PredictionResponse)
async def get_prediction(user_id: int):
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.get(f"{AI_URL}/predict/{user_id}")
        if resp.status_code == 404:
            raise HTTPException(404, "No prediction found")
        resp.raise_for_status()
        return resp.json()
