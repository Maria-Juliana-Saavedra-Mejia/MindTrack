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


def test_insight_provider_defaults_auto(monkeypatch):
    monkeypatch.delenv("MINDTRACK_INSIGHT_PROVIDER", raising=False)
    assert Config.insight_provider() == "auto"


def test_insight_provider_invalid_falls_back_auto(monkeypatch):
    monkeypatch.setenv("MINDTRACK_INSIGHT_PROVIDER", "bogus")
    assert Config.insight_provider() == "auto"


def test_insight_provider_openai_local(monkeypatch):
    monkeypatch.setenv("MINDTRACK_INSIGHT_PROVIDER", "openai")
    assert Config.insight_provider() == "openai"
    monkeypatch.setenv("MINDTRACK_INSIGHT_PROVIDER", "local")
    assert Config.insight_provider() == "local"


def test_mongo_uri_strips_trailing_slash(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017/")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    cfg = Config.to_app_config()
    assert cfg["MONGO_URI"] == "mongodb://localhost:27017"


def test_cors_blocks_live_server_127_true_in_production_with_github_only(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    monkeypatch.setenv("CORS_ORIGINS", "https://user.github.io")
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.delenv("MINDTRACK_MERGE_LIVE_SERVER_CORS", raising=False)
    assert Config.cors_blocks_live_server_127() is True


def test_cors_blocks_live_server_127_false_after_merge_flag(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://localhost:27017")
    monkeypatch.setenv("MONGO_DB_NAME", "mindtrack_test")
    monkeypatch.setenv("CORS_ORIGINS", "https://user.github.io")
    monkeypatch.setenv("FLASK_ENV", "production")
    monkeypatch.setenv("MINDTRACK_MERGE_LIVE_SERVER_CORS", "1")
    assert Config.cors_blocks_live_server_127() is False
