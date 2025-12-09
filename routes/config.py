# routes/config.py

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import PlainTextResponse
from core.config import get_settings
import os

router = APIRouter(prefix="/config", tags=["system"])


# ------------------------------------------------------------
# /config/test
# ------------------------------------------------------------
@router.get("/test")
def config_test(settings=Depends(get_settings)):
    """Return non-sensitive configuration values."""

    return {
        "scroll_library_path": settings.SCROLL_LIBRARY_PATH,
        "github_repo": settings.GITHUB_REPO,
        "github_username": settings.GITHUB_USERNAME,
        "neo4j_uri": settings.NEO4J_URI,
        "neo4j_user": settings.NEO4J_USER,
        "api_keys_configured": len([k for k in settings.valid_api_keys if k]) > 0,
    }


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def read_file_or_error(path: str) -> str:
    """Safely read a system file and return its contents or error."""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    try:
        with open(path, "r") as f:
            return f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------------------------------------------
# /config/nginx
# ------------------------------------------------------------
@router.get("/nginx", response_class=PlainTextResponse)
def get_nginx_config():
    """Return the Nginx site configuration for Spire."""
    return read_file_or_error("/etc/nginx/sites-available/spire")


# ------------------------------------------------------------
# /config/service
# ------------------------------------------------------------
@router.get("/service", response_class=PlainTextResponse)
def get_service_config():
    """Return the systemd config for the Spire service."""
    return read_file_or_error("/etc/systemd/system/spire.service")
