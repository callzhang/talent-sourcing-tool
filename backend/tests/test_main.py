from collections.abc import Generator

from fastapi.testclient import TestClient

from app.main import app


def client() -> Generator[TestClient, None, None]:
    app.state.create_tables_on_startup = False
    with TestClient(app) as test_client:
        yield test_client
    app.state.create_tables_on_startup = True


def test_cors_allows_localhost_and_loopback_origins():
    app.state.create_tables_on_startup = False
    with TestClient(app) as test_client:
        localhost_response = test_client.options(
            "/api/jobs",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        loopback_response = test_client.options(
            "/api/jobs",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
    app.state.create_tables_on_startup = True

    assert localhost_response.status_code == 200
    assert (
        localhost_response.headers["access-control-allow-origin"]
        == "http://localhost:5173"
    )
    assert loopback_response.status_code == 200
    assert (
        loopback_response.headers["access-control-allow-origin"]
        == "http://127.0.0.1:5173"
    )
