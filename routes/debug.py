# routes/debug.py

from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import PlainTextResponse
from core.config import get_settings
import subprocess
import os

router = APIRouter(prefix="/debug", tags=["debug"])

@router.get("/journal", response_class=PlainTextResponse)
def get_journal_logs():
    try:
        result = subprocess.run(
            ["journalctl", "-u", "mythos_gateway", "-n", "50", "--no-pager"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error getting journal logs: {e.stderr}")

@router.get("/env")
def get_sanitized_env(settings=Depends(get_settings)):
    hidden_keys = {"NEO4J_PASS", "GITHUB_TOKEN", "TELEGRAM_BOT_TOKEN", "KATUAR_API_KEY", "SERAPHET_API_KEY"}
    return {
        k: ("***" if k in hidden_keys else v)
        for k, v in os.environ.items()
        if not k.startswith("_")
    }

@router.get("/dependencies", response_class=PlainTextResponse)
def list_dependencies():
    try:
        result = subprocess.run(
            ["/opt/mythos-gateway/.venv/bin/pip", "freeze"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error listing dependencies: {e.stderr}")

@router.get("/disk", response_class=PlainTextResponse)
def get_disk_usage():
    try:
        result = subprocess.run(["df", "-h"], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Error getting disk usage: {e.stderr}")

@router.get("/ping-db")
def ping_neo4j(settings=Depends(get_settings)):
    from neo4j import GraphDatabase, basic_auth
    try:
        driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=basic_auth(settings.NEO4J_USER, settings.NEO4J_PASS)
        )
        with driver.session() as session:
            result = session.run("RETURN 1 AS ok").single()
            return {"neo4j_connection": "successful", "result": result["ok"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Neo4j connection failed: {str(e)}")
