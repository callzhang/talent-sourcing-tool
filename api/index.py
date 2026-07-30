from __future__ import annotations

import sys
from pathlib import Path

from fastapi.responses import FileResponse


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.main import create_app, register_api_routers  # noqa: E402


# The current Vercel routing behavior for rewritten backend functions can expose
# either /jobs or /api/jobs to the ASGI app depending on how the request is
# routed. Register both prefixes so the same code works locally and in
# production. The function also serves the built SPA because Vercel currently
# packages this project as a single FastAPI service.
app = create_app(api_prefix="")
register_api_routers(app, prefixes=["/api"])


@app.get("/", include_in_schema=False)
async def serve_index() -> FileResponse:
    return FileResponse(FRONTEND_DIST / "index.html")


@app.get("/{asset_path:path}", include_in_schema=False)
async def serve_asset(asset_path: str) -> FileResponse:
    candidate = (FRONTEND_DIST / asset_path).resolve()
    if candidate.is_file() and FRONTEND_DIST in candidate.parents:
        return FileResponse(candidate)
    return FileResponse(FRONTEND_DIST / "index.html")
