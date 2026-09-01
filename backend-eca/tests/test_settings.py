"""Pruebas de `app/core/settings.py` — ECA-002."""
from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_settings_falla_sin_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/eca_db_test")
    monkeypatch.delenv("SECRET_KEY", raising=False)

    from app.core.settings import Settings

    with pytest.raises(ValidationError):
        Settings()


def test_settings_falla_sin_database_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "clave-de-prueba-suficientemente-larga-000000")
    monkeypatch.delenv("DATABASE_URL", raising=False)

    from app.core.settings import Settings

    with pytest.raises(ValidationError):
        Settings()


def test_settings_carga_con_env_valido(env_valido: None) -> None:
    from app.core.settings import Settings

    settings = Settings()
    assert settings.SECRET_KEY
    assert settings.DATABASE_URL
    assert settings.CORS_ORIGINS == ["http://localhost:5173"]
    assert settings.es_produccion is False


def test_settings_cors_origins_csv(monkeypatch: pytest.MonkeyPatch, env_valido: None) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example.com, https://b.example.com")

    from app.core.settings import Settings

    settings = Settings()
    assert settings.CORS_ORIGINS == ["https://a.example.com", "https://b.example.com"]


def test_settings_es_produccion(monkeypatch: pytest.MonkeyPatch, env_valido: None) -> None:
    monkeypatch.setenv("APP_ENV", "production")

    from app.core.settings import Settings

    assert Settings().es_produccion is True


def test_get_settings_cacheado(env_valido: None) -> None:
    from app.core.settings import get_settings

    get_settings.cache_clear()
    assert get_settings() is get_settings()
