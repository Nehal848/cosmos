"""My COSMOS API.
Local:   uvicorn app.main:app --reload --port 8020
Server:  uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import assistant, graph, opportunities, papers_api, recommend, search, trends

STATIC_CANDIDATES = [
    Path(__file__).resolve().parent / "static",
    Path(__file__).resolve().parent.parent / "static",
    Path("static"),
    Path("backend/static"),
]
STATIC_DIR = next(
    (c for c in STATIC_CANDIDATES if c.exists() and (c / "index.html").is_file()),
    Path(__file__).resolve().parent / "static",
)

# Websites allowed to call this API. On a server, set COSMOS_CORS_ORIGINS to your site's
# address(es), comma-separated, e.g. "https://my-cosmos.example".
DEFAULT_ORIGINS = "http://localhost:5173,http://localhost:5174,http://localhost:4173"
ORIGINS = [o.strip().rstrip("/") for o in os.getenv("COSMOS_CORS_ORIGINS", DEFAULT_ORIGINS).split(",") if o.strip()]

app = FastAPI(title="My COSMOS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

if (STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.middleware("http")
async def spa_middleware(request: Request, call_next):
    accept = request.headers.get("accept", "")
    path = request.url.path
    if (
        request.method == "GET"
        and "text/html" in accept
        and not path.startswith(("/docs", "/openapi.json", "/redoc"))
        and STATIC_DIR.exists()
        and (STATIC_DIR / "index.html").is_file()
    ):
        rel_path = path.lstrip("/")
        if rel_path and (STATIC_DIR / rel_path).is_file():
            return FileResponse(STATIC_DIR / rel_path)
        return FileResponse(STATIC_DIR / "index.html")
    return await call_next(request)


app.include_router(papers_api.router)
app.include_router(search.router)
app.include_router(recommend.router)
app.include_router(graph.router)
app.include_router(trends.router)
app.include_router(opportunities.router)
app.include_router(assistant.router)


@app.get("/debug_static", include_in_schema=False)
def debug_static():
    return {
        "file": str(Path(__file__).resolve()),
        "cwd": str(Path.cwd()),
        "static_dir": str(STATIC_DIR),
        "static_dir_exists": STATIC_DIR.exists(),
        "has_index": (STATIC_DIR / "index.html").is_file() if STATIC_DIR.exists() else False,
        "files_in_cwd": [p.name for p in Path.cwd().iterdir()] if Path.cwd().exists() else [],
        "files_in_parent": [p.name for p in Path(__file__).resolve().parent.iterdir()] if Path(__file__).resolve().parent.exists() else [],
    }


@app.get("/vite.svg", include_in_schema=False)
def vite_svg():
    svg_path = STATIC_DIR / "vite.svg"
    if svg_path.is_file():
        return FileResponse(svg_path)


@app.get("/")
def root():
    """Serves the frontend application if built, or API status info."""
    if STATIC_DIR.exists() and (STATIC_DIR / "index.html").is_file():
        return FileResponse(STATIC_DIR / "index.html")
    return {
        "message": "Welcome to COSMOS API",
        "docs": "/docs",
        "health": "/health",
        "stats": "/stats",
    }


@app.get("/health")
def health():
    """Hosts call this to check the API is alive."""
    return {"status": "ok", "answer_provider": assistant.PROVIDER.name}
