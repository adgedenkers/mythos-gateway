from fastapi import APIRouter, HTTPException
from api.github.service import GitHubService

router = APIRouter(prefix="/github", tags=["github"])
github_service = GitHubService()

@router.post("/create-scroll")
async def create_scroll(scroll_data: dict):
    try:
        return await github_service.create_scroll(scroll_data)
    except Exception as e:
        raise HTTPException(500, detail=str(e))
