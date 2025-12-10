from fastapi import APIRouter, HTTPException
from core.models import ScrollData, PatchScrollData
from .service import GitHubService


router = APIRouter(prefix="/github", tags=["GitHub Local Scrolls"])

@router.post("/create-scroll-local")
async def create_scroll_local(scroll_data: ScrollData):
    service = GitHubService()
    return await service.create_scroll(scroll_data)

@router.post("/patch-scroll-local")
async def patch_scroll_local(patch_data: PatchScrollData):
    service = GitHubService()
    return await service.patch_scroll(patch_data)