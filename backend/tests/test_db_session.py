import pytest

from app.db.session import create_db_engine


def test_turso_url_requires_auth_token():
    with pytest.raises(RuntimeError, match="TURSO_AUTH_TOKEN"):
        create_db_engine("libsql://example.turso.io")


def test_turso_url_uses_sqlalchemy_libsql_dialect(monkeypatch):
    captured: dict[str, object] = {}

    def fake_create_engine(url: str, **kwargs: object) -> object:
        captured["url"] = url
        captured.update(kwargs)
        return object()

    monkeypatch.setattr("app.db.session.create_engine", fake_create_engine)

    engine = create_db_engine(
        "libsql://example.turso.io",
        turso_auth_token="test-token",
    )

    assert engine is not None
    assert captured["url"] == "sqlite+libsql://example.turso.io?secure=true"
    assert captured["connect_args"] == {"auth_token": "test-token"}
