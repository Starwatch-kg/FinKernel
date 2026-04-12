"""
Helper functions for tests
"""

import uuid
import httpx
import os

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def generate_unique_email():
    """Generate unique email for testing"""
    return f"test_{uuid.uuid4().hex[:8]}@test.com"


def generate_unique_user():
    """Generate unique user data"""
    unique_id = uuid.uuid4().hex[:8]
    return {
        "email": f"test_{unique_id}@test.com",
        "name": f"Test User {unique_id}",
        "password": "Test123!@#",
    }


async def register_and_get_token(client: httpx.AsyncClient = None):
    """Register a new user and return access token"""
    if client is None:
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            return await _do_register(client)
    return await _do_register(client)


async def _do_register(client: httpx.AsyncClient):
    user_data = generate_unique_user()
    response = await client.post("/api/auth/register", json=user_data)

    if response.status_code != 200:
        raise Exception(
            f"Registration failed: {response.status_code} - {response.text}"
        )

    data = response.json()
    return {
        "token": data["access_token"],
        "refresh_token": data.get("refresh_token"),
        "email": user_data["email"],
        "password": user_data["password"],
    }


def get_auth_headers(token: str):
    """Get authorization headers"""
    return {"Authorization": f"Bearer {token}"}
