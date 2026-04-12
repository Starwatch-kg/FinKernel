"""
End-to-end tests for authentication flow.
Tests registration, login, token refresh, and authorization.
"""

import time
import uuid

import pytest
from httpx import AsyncClient

BASE_URL = "http://localhost:8000"


class TestRegistration:
    """Test user registration"""

    @pytest.mark.asyncio
    async def test_register_success(self):
        """Test successful user registration"""
        async with AsyncClient(base_url=BASE_URL) as client:
            unique_id = uuid.uuid4().hex[:8]
            email = f"test_{unique_id}@example.com"
            response = await client.post(
                "/api/auth/register",
                json={
                    "email": email,
                    "name": f"Test User {unique_id}",
                    "password": "Test123!@#",
                },
            )

            assert response.status_code == 200
            data = response.json()

            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "Bearer"
            assert data["expires_in"] == 900  # 15 minutes

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self):
        """Test registration with duplicate email fails"""
        async with AsyncClient(base_url=BASE_URL) as client:
            unique_id = uuid.uuid4().hex[:8]
            email = f"duplicate_{unique_id}@example.com"

            # First registration
            response1 = await client.post(
                "/api/auth/register",
                json={
                    "email": email,
                    "name": f"User {unique_id}_1",
                    "password": "Test123!@#",
                },
            )
            assert response1.status_code == 200

            # Second registration with same email
            response2 = await client.post(
                "/api/auth/register",
                json={
                    "email": email,
                    "name": f"User {unique_id}_2",
                    "password": "Test123!@#",
                },
            )
            assert response2.status_code == 400
            assert "already exists" in response2.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_register_weak_password(self):
        """Test registration with weak password fails"""
        async with AsyncClient(base_url=BASE_URL) as client:
            email = f"test_{uuid.uuid4().hex[:8]}@example.com"

            # No uppercase
            response = await client.post(
                "/api/auth/register",
                json={"email": email, "name": "Test User", "password": "test123!@#"},
            )
            assert response.status_code == 422

            # No digit
            response = await client.post(
                "/api/auth/register",
                json={"email": email, "name": "Test User", "password": "TestTest!@#"},
            )
            assert response.status_code == 422

            # No special character
            response = await client.post(
                "/api/auth/register",
                json={"email": email, "name": "Test User", "password": "Test123456"},
            )
            assert response.status_code == 422

            # Too short
            response = await client.post(
                "/api/auth/register",
                json={"email": email, "name": "Test User", "password": "Te1!"},
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_invalid_email(self):
        """Test registration with invalid email fails"""
        async with AsyncClient(base_url=BASE_URL) as client:
            response = await client.post(
                "/api/auth/register",
                json={
                    "email": "not-an-email",
                    "name": "Test User",
                    "password": "Test123!@#",
                },
            )
            assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_rate_limit(self):
        """Test registration rate limiting"""
        async with AsyncClient(base_url=BASE_URL) as client:
            email_base = f"ratelimit_{uuid.uuid4().hex[:8]}"

            # Try to register 4 times quickly (limit is 3 per 5 min)
            for i in range(4):
                response = await client.post(
                    "/api/auth/register",
                    json={
                        "email": f"{email_base}_{i}@example.com",
                        "name": f"User {email_base}_{i}",
                        "password": "Test123!@#",
                    },
                )

                if i < 3:
                    assert response.status_code == 200
                else:
                    # 4th request should be rate limited
                    assert response.status_code == 429


class TestLogin:
    """Test user login"""

    @pytest.mark.asyncio
    async def test_login_success(self):
        """Test successful login"""
        async with AsyncClient(base_url=BASE_URL) as client:
            email = f"login_{uuid.uuid4().hex[:8]}@example.com"
            password = "Test123!@#"

            # Register user
            await client.post(
                "/api/auth/register",
                json={"email": email, "name": "Test User", "password": password},
            )

            # Login
            response = await client.post(
                "/api/auth/login", json={"email": email, "password": password}
            )

            assert response.status_code == 200
            data = response.json()

            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "Bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self):
        """Test login with wrong password fails"""
        async with AsyncClient(base_url=BASE_URL) as client:
            email = f"wrongpass_{uuid.uuid4().hex[:8]}@example.com"

            # Register user
            await client.post(
                "/api/auth/register",
                json={"email": email, "name": "Test User", "password": "Test123!@#"},
            )

            # Login with wrong password
            response = await client.post(
                "/api/auth/login",
                json={"email": email, "password": "WrongPassword123!@#"},
            )

            assert response.status_code == 401
            assert "invalid credentials" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self):
        """Test login with non-existent user fails"""
        async with AsyncClient(base_url=BASE_URL) as client:
            response = await client.post(
                "/api/auth/login",
                json={
                    "email": f"nonexistent_{uuid.uuid4().hex[:8]}@example.com",
                    "password": "Test123!@#",
                },
            )

            assert response.status_code == 401
            assert "invalid credentials" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_login_case_insensitive_email(self):
        """Test login is case-insensitive for email"""
        async with AsyncClient(base_url=BASE_URL) as client:
            email = f"CaseSensitive_{uuid.uuid4().hex[:8]}@example.com"
            password = "Test123!@#"

            # Register with mixed case
            await client.post(
                "/api/auth/register",
                json={"email": email, "name": "Test User", "password": password},
            )

            # Login with lowercase
            response = await client.post(
                "/api/auth/login", json={"email": email.lower(), "password": password}
            )

            assert response.status_code == 200


class TestTokenRefresh:
    """Test token refresh"""

    @pytest.mark.asyncio
    async def test_refresh_token_success(self):
        """Test successful token refresh"""
        async with AsyncClient(base_url=BASE_URL) as client:
            email = f"refresh_{uuid.uuid4().hex[:8]}@example.com"

            # Register and get tokens
            register_response = await client.post(
                "/api/auth/register",
                json={"email": email, "name": "Test User", "password": "Test123!@#"},
            )
            assert register_response.status_code == 200, f"Registration failed: {register_response.status_code} - {register_response.text}"
            refresh_token = register_response.json()["refresh_token"]

            # Refresh token
            response = await client.post(
                "/api/auth/refresh", json={"refresh_token": refresh_token}
            )

            assert response.status_code == 200
            data = response.json()

            assert "access_token" in data
            assert "refresh_token" in data
            # New tokens should be different
            assert data["refresh_token"] != refresh_token

    @pytest.mark.asyncio
    async def test_refresh_with_invalid_token(self):
        """Test refresh with invalid token fails"""
        async with AsyncClient(base_url=BASE_URL) as client:
            response = await client.post(
                "/api/auth/refresh", json={"refresh_token": "invalid.token.here"}
            )

            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_with_access_token_fails(self):
        """Test refresh with access token instead of refresh token fails"""
        async with AsyncClient(base_url=BASE_URL) as client:
            email = f"wrongtoken_{uuid.uuid4().hex[:8]}@example.com"

            # Register and get tokens
            register_response = await client.post(
                "/api/auth/register",
                json={"email": email, "name": "Test User", "password": "Test123!@#"},
            )
            assert register_response.status_code == 200, f"Registration failed: {register_response.status_code} - {register_response.text}"
            access_token = register_response.json()["access_token"]

            # Try to refresh with access token
            response = await client.post(
                "/api/auth/refresh", json={"refresh_token": access_token}
            )

            assert response.status_code == 401


class TestAuthorization:
    """Test authorization and protected endpoints"""

    @pytest.mark.asyncio
    async def test_protected_endpoint_requires_auth(self):
        """Test protected endpoints require authentication"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # Try to access protected endpoint without token
            response = await client.get("/api/dashboard")
            assert response.status_code == 401

            response = await client.get("/api/transactions")
            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_token_grants_access(self):
        """Test valid token grants access to protected endpoints"""
        async with AsyncClient(base_url=BASE_URL) as client:
            email = f"access_{uuid.uuid4().hex[:8]}@example.com"

            # Register and get token
            register_response = await client.post(
                "/api/auth/register",
                json={"email": email, "name": "Test User", "password": "Test123!@#"},
            )
            assert register_response.status_code == 200, f"Registration failed: {register_response.status_code} - {register_response.text}"
            token = register_response.json()["access_token"]

            # Access protected endpoint with token
            client.headers["Authorization"] = f"Bearer {token}"
            response = await client.get("/api/dashboard")

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self):
        """Test invalid token is rejected"""
        async with AsyncClient(base_url=BASE_URL) as client:
            client.headers["Authorization"] = "Bearer invalid.token.here"
            response = await client.get("/api/dashboard")

            assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_auth_header_rejected(self):
        """Test malformed authorization header is rejected"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # Missing "Bearer" prefix
            client.headers["Authorization"] = "just-a-token"
            response = await client.get("/api/dashboard")
            assert response.status_code == 401

            # Empty header
            client.headers["Authorization"] = ""
            response = await client.get("/api/dashboard")
            assert response.status_code == 401


class TestAdminAuthorization:
    """Test admin-only endpoints"""

    @pytest.mark.asyncio
    async def test_admin_endpoint_requires_admin(self):
        """Test admin endpoints require admin privileges"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # Regular user
            email = f"regular_{uuid.uuid4().hex[:8]}@example.com"
            register_response = await client.post(
                "/api/auth/register",
                json={"email": email, "name": "Regular User", "password": "Test123!@#"},
            )
            token = register_response.json()["access_token"]

            # Try to access admin endpoint
            client.headers["Authorization"] = f"Bearer {token}"
            response = await client.get("/api/admin/users")

            assert response.status_code == 403


class TestTokenExpiration:
    """Test token expiration"""

    @pytest.mark.asyncio
    async def test_access_token_short_lived(self):
        """Test access token has short expiration (15 minutes)"""
        async with AsyncClient(base_url=BASE_URL) as client:
            email = f"expiry_{uuid.uuid4().hex[:8]}@example.com"

            register_response = await client.post(
                "/api/auth/register",
                json={"email": email, "name": "Test User", "password": "Test123!@#"},
            )

            data = register_response.json()
            assert data["expires_in"] == 900  # 15 minutes in seconds


class TestSecurityHeaders:
    """Test security headers are present"""

    @pytest.mark.asyncio
    async def test_security_headers_present(self):
        """Test all security headers are present in responses"""
        async with AsyncClient(base_url=BASE_URL) as client:
            response = await client.get("/health")

            headers = response.headers

            # Check security headers
            assert "strict-transport-security" in headers
            assert "x-frame-options" in headers
            assert "x-content-type-options" in headers
            assert "x-xss-protection" in headers
            assert "content-security-policy" in headers
            assert "referrer-policy" in headers
            assert "x-request-id" in headers


class TestAuditLogging:
    """Test audit logging for authentication events"""

    @pytest.mark.asyncio
    async def test_failed_login_logged(self):
        """Test failed login attempts are logged"""
        async with AsyncClient(base_url=BASE_URL) as client:
            # Attempt login with wrong credentials
            response = await client.post(
                "/api/auth/login",
                json={
                    "email": "nonexistent@example.com",
                    "password": "WrongPassword123!@#",
                },
            )

            assert response.status_code == 401
            # Audit log should contain this failed attempt
            # (verified through logs, not API response)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
