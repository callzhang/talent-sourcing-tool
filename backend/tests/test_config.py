from importlib import reload

from app.core import config as config_module


def test_default_database_url_uses_repo_sqlite_locally(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    assert config_module.default_database_url().endswith("/backend/talent_sourcing.sqlite3")


def test_default_database_url_uses_tmp_sqlite_on_vercel_without_database_url(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)

    assert config_module.default_database_url() == "sqlite:////tmp/talent_sourcing.sqlite3"


def test_default_database_url_respects_database_url_on_vercel(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example")

    settings_module = reload(config_module)
    try:
        assert settings_module.Settings().database_url == "postgresql://example"
    finally:
        reload(config_module)


def test_default_database_url_uses_turso_url_when_configured(monkeypatch):
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://example.turso.io")

    assert config_module.default_database_url() == "libsql://example.turso.io"


def test_settings_uses_turso_database_url_when_no_database_alias_is_set(monkeypatch):
    monkeypatch.delenv("TALENT_DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TURSO_DATABASE_URL", "libsql://example.turso.io")
    monkeypatch.setenv("TURSO_AUTH_TOKEN", "test-token")

    settings = config_module.Settings(_env_file=None)

    assert settings.database_url == "libsql://example.turso.io"
    assert settings.turso_auth_token == "test-token"
