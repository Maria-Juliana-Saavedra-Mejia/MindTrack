# backend/tests/test_config.py
"""Tests for configuration validation."""

import pytest

from app.config import Config


def test_validate_raises_on_missing(monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    monkeypatch.delenv("MONGO_DB_NAME", raising=False)
    monkeypatch.setenv("MONGO_URI", "")
    monkeypatch.setenv("MONGO_DB_NAME", "")
    with pytest.raises(EnvironmentError):
        Config.validate()


def test_validate_success(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    Config.validate()


def test_mongo_uri_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017/")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    cfg = Config.to_app_config()
    assert cfg["MONGO_URI"] == "mongodb://localhost:27017"
