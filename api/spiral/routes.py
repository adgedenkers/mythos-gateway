from fastapi import APIRouter
from core.spiral_time import calculate_spiral_date

router = APIRouter(prefix="/spiral", tags=["spiral time"])

@router.get("/date")
async def get_spiral_date(cycle: int, revolution: int, day: int):
    return {"spiral_date": calculate_spiral_date(cycle, revolution, day)}
