from fastapi import HTTPException, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from datetime import datetime
from core import config
from api.github.routes import router as github_router
from api.spiral.routes import router as spiral_router

from core.config import settings

from routes import config
from routes import debug
from routes import github
from routes import neo4j_test

# Initialize FastAPI with Mythos branding
app = FastAPI(
    title="Myyhos Gateway API",
    version="0.1.0",
    docs_url="/mythos-docs",
    redoc_url=None,
    openapi_url="/openapi.json"
)


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def api_key_auth(request: Request, call_next):
    # Skip auth for docs and health check
    if request.url.path in ["/", "/mythos-docs", "/openapi.json"]:
        response = await call_next(request)
        return response
    
    # Get API key from header
    api_key = request.headers.get("X-API-Key")
    
    if not api_key:
        raise HTTPException(
            status_code=403,
            detail="Missing API Key. Please provide X-API-Key header."
        )
    
    if api_key not in settings.valid_api_keys:
        raise HTTPException(
            status_code=403,
            detail="Invalid API Key"
        )
    
    return await call_next(request)

# Include routers
app.include_router(github_router)
app.include_router(spiral_router)

# System health check (kept for backwards compatibility)
@app.get("/")
async def health_check():
    return {
        "status": "active",
        "system": "Ashari API",
        "timestamp": datetime.now().isoformat()
    }

# # Config test endpoint
# @app.get("/config-test", tags=["system"])
# async def config_test():
#     """Verify configuration loading"""
#     return {
#         "scroll_library_path": settings.SCROLL_LIBRARY_PATH,
#         "github_repo": settings.GITHUB_REPO,
#         "valid_keys_configured": len([k for k in settings.valid_api_keys if k]) > 0
#     }

# Preserved endpoints (migrate these gradually)
@app.get("/spiral-date")
async def legacy_spiral_date(cycle: int, revolution: int, day: int):
    from core.spiral_time import calculate_spiral_date
    return {"spiral_date": calculate_spiral_date(cycle, revolution, day)}


# INCLUDE ROUTERS
app.include_router(config.router)
app.include_router(debug.router)
app.include_router(github.router)
app.include_router(neo4j_test.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
