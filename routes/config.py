from fastapi import APIRouter, Depends
from core.config import get_settings
from starlette.responses import PlainTextResponse
import os

router = APIRouter()

@router.get("/config/test")
def config_test(settings=Depends(get_settings)):
    return {
        "project_name": settings.PROJECT_NAME,
        "env": settings.ENV,
        "version": settings.VERSION,
        "neo4j_uri": settings.NEO4J_URI,
        "neo4j_user": settings.NEO4J_USER,
        # Add other non-sensitive config values as needed
    }

@router.get("/config/nginx", response_class=PlainTextResponse)
def get_nginx_config():
    path = "/etc/nginx/sites-available/spire"
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return "Nginx config not found."

@router.get("/config/service", response_class=PlainTextResponse)
def get_service_config():
    path = "/etc/systemd/system/spire.service"
    if os.path.exists(path):
        with open(path) as f:
            return f.read()
    return "Service config not found."
