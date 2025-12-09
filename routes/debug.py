# routes/debug.py

from fastapi import APIRouter
from starlette.responses import PlainTextResponse
import subprocess

router = APIRouter()

@router.get("/debug/journal", response_class=PlainTextResponse, tags=["debug"])
def get_mythos_gateway_logs():
    try:
        result = subprocess.run(
            ["journalctl", "-u", "mythos_gateway", "-n", "50", "--no-pager", "--output=short"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error running journalctl:\n{e.stderr or str(e)}"