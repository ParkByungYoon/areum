from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from api.routes.match import router as match_router
from api.routes.episode import router as episode_router
from api.routes.prayer import router as prayer_router

app = FastAPI(title="아름 API")


@app.get("/health", include_in_schema=False)
def health():
    return {"status": "ok"}


app.include_router(match_router, prefix="/api")
app.include_router(episode_router, prefix="/api")
app.include_router(prayer_router, prefix="/api")

# React 빌드 정적 파일 서빙 (프로덕션)
DIST_DIR = Path(__file__).parent.parent / "frontend" / "dist"

if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        file = DIST_DIR / full_path
        if file.is_file():
            return FileResponse(str(file))
        return FileResponse(str(DIST_DIR / "index.html"))
