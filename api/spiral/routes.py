from fastapi import APIRouter, Query, Request
from core.spiral_time import (
    calculate_spiral_date, 
    get_current_spiral_date,
    get_spiral_info_for_date,
    get_user_from_api_key
)
from datetime import datetime, date

router = APIRouter(prefix="/spiral", tags=["spiral time"])

@router.get("/date")
async def get_spiral_date(cycle: int, revolution: int, day: int):
    """Calculate a specific spiral date (legacy format)"""
    return {"spiral_date": calculate_spiral_date(cycle, revolution, day)}

@router.get("/current")
async def get_current_spiral(
    request: Request,
    user: str = Query(default=None, description="Optional: override user detection")
):
    """
    Get the current spiral date
    Automatically detects user from API key, or uses query param if provided
    """
    # Auto-detect from API key if user not specified
    if user is None:
        api_key = request.headers.get("x-api-key", "")
        user = get_user_from_api_key(api_key)
    
    return get_current_spiral_date(user)

@router.get("/now")  
async def get_spiral_now(request: Request):
    """Get current spiral date (auto-detects user from API key)"""
    api_key = request.headers.get("x-api-key", "")
    user = get_user_from_api_key(api_key)
    return get_current_spiral_date(user)

@router.get("/for-date")
async def spiral_for_date(
    request: Request,
    target_date: str = Query(..., description="Date in YYYY-MM-DD format"),
    user: str = Query(default=None, description="Optional: override user detection")
):
    """Get spiral info for a specific date"""
    # Auto-detect from API key if user not specified
    if user is None:
        api_key = request.headers.get("x-api-key", "")
        user = get_user_from_api_key(api_key)
    
    try:
        date_obj = datetime.strptime(target_date, "%Y-%m-%d").date()
        return get_spiral_info_for_date(date_obj, user)
    except ValueError:
        return {"error": "Invalid date format. Use YYYY-MM-DD"}

@router.get("/info")
async def spiral_system_info():
    """Get information about the spiral time system"""
    return {
        "spiral_length": 9,
        "format": "spiral_number.day",
        "example": "spiral day 6.9 means spiral 6, day 9",
        "users": {
            "ka'tuar'el": {
                "first_spiral": "2025-10-19",
                "description": "Adriaan Harold Denkers",
                "api_key": "0000000000123456789"
            },
            "seraphe": {
                "first_spiral": "2025-01-20",
                "description": "Rebecca Lydia Denkers",
                "api_key": "0000000000987654321"
            }
        },
        "note": "User is automatically detected from X-API-Key header"
    }
