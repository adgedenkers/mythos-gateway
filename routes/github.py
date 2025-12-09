# routes/github.py

from fastapi import APIRouter, Depends, HTTPException
from core.config import get_settings
from github import Github, GithubException
import base64

router = APIRouter(prefix="/github", tags=["github"])

def get_github_client(settings=Depends(get_settings)):
    token = settings.GITHUB_TOKEN
    if not token:
        raise HTTPException(status_code=500, detail="GitHub token not configured")
    return Github(token)

@router.get("/list-repo")
def list_repo_files(repo_name: str = None, path: str = "", settings=Depends(get_settings)):
    repo_name = repo_name or settings.GITHUB_REPO
    g = get_github_client(settings)
    try:
        repo = g.get_repo(f"{settings.GITHUB_USERNAME}/{repo_name}")
        contents = repo.get_contents(path)
        return [{"name": c.name, "type": c.type, "path": c.path} for c in contents]
    except GithubException as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/file-content")
def get_file_content(repo_name: str, file_path: str, settings=Depends(get_settings)):
    g = get_github_client(settings)
    try:
        repo = g.get_repo(f"{settings.GITHUB_USERNAME}/{repo_name}")
        file_content = repo.get_contents(file_path)
        decoded = base64.b64decode(file_content.content).decode("utf-8")
        return {"path": file_path, "content": decoded}
    except GithubException as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create-scroll")
def create_scroll(repo_name: str, scroll_name: str, content: str, commit_message: str, settings=Depends(get_settings)):
    g = get_github_client(settings)
    try:
        repo = g.get_repo(f"{settings.GITHUB_USERNAME}/{repo_name}")
        path = f"scrolls/{scroll_name}"
        repo.create_file(path, commit_message, content)
        return {"status": "success", "path": path, "commit_message": commit_message}
    except GithubException as e:
        raise HTTPException(status_code=500, detail=str(e))
