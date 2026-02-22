"""Tests for authentication — password hashing and JWT."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from jose import jwt

from policy_system.auth.jwt_handler import create_token, decode_token
from policy_system.auth.password import hash_password, verify_password
from policy_system.config import settings
from policy_system.core.exceptions import AuthenticationError


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        hashed = hash_password("my_password")
        assert hashed != "my_password"

    def test_verify_correct_password(self):
        hashed = hash_password("correct_password")
        assert verify_password("correct_password", hashed) is True

    def test_reject_wrong_password(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_same_password_different_hashes(self):
        """bcrypt generates different salts each time."""
        h1 = hash_password("password")
        h2 = hash_password("password")
        assert h1 != h2
        assert verify_password("password", h1)
        assert verify_password("password", h2)


class TestJWT:
    def test_create_and_decode_token(self):
        user_id = str(uuid.uuid4())
        token = create_token(user_id, "test@example.com")
        payload = decode_token(token)
        assert payload["sub"] == user_id
        assert payload["email"] == "test@example.com"

    def test_expired_token_raises(self):
        expired_payload = {
            "sub": str(uuid.uuid4()),
            "email": "x@x.com",
            "exp": datetime(2020, 1, 1, tzinfo=timezone.utc),
            "iat": datetime(2020, 1, 1, tzinfo=timezone.utc),
        }
        token = jwt.encode(expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        with pytest.raises(AuthenticationError):
            decode_token(token)

    def test_tampered_token_raises(self):
        token = create_token(str(uuid.uuid4()), "x@x.com")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(AuthenticationError):
            decode_token(tampered)

    def test_missing_sub_raises(self):
        payload = {"email": "x@x.com"}
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        with pytest.raises(AuthenticationError):
            decode_token(token)
