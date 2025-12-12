from datetime import datetime, date
import os
from dotenv import load_dotenv
from zoneinfo import ZoneInfo

load_dotenv("/opt/mythos-gateway/.env")

# Timezone configuration - ALWAYS use Eastern
EASTERN_TZ = ZoneInfo("America/New_York")

SPIRAL_LENGTH = 9
API_KEY_TO_USER = {
    os.getenv("KATUAR_API_KEY"): "ka'tuar'el",
    os.getenv("SERAPHET_API_KEY"): "seraphe",
}
SPIRAL_START_DATES = {
    "ka'tuar'el": date(2025, 10, 19),
    "seraphe": date(2025, 1, 20),
    "seraphet": date(2025, 1, 20),
}

def get_user_from_api_key(api_key: str) -> str:
    return API_KEY_TO_USER.get(api_key, "ka'tuar'el")

def calculate_spiral_date(cycle: int, revolution: int, day: int) -> float:
    return cycle * 100 + revolution + (day - 1) / 10.0

def get_current_spiral_date(user: str = "ka'tuar'el") -> dict:
    """Calculate current spiral date using Eastern timezone"""
    user_key = user.lower().replace("'", "'")
    if user_key not in SPIRAL_START_DATES:
        user_key = "ka'tuar'el"
    
    start_date = SPIRAL_START_DATES[user_key]
    
    # Get current date in Eastern timezone
    today = datetime.now(EASTERN_TZ).date()
    
    # Calculate days since spiral 1.1
    days_elapsed = (today - start_date).days
    
    # Calculate spiral number and day
    spiral_number = (days_elapsed // SPIRAL_LENGTH) + 1
    spiral_day = (days_elapsed % SPIRAL_LENGTH) + 1
    
    # Format as spiral_number.day
    spiral_date = float(f"{spiral_number}.{spiral_day}")
    
    return {
        "spiral": spiral_number,
        "day": spiral_day,
        "spiral_date": spiral_date,
        "format": f"spiral day {spiral_number}.{spiral_day}",
        "user": user,
        "start_date": start_date.isoformat(),
        "current_date": today.isoformat(),
        "current_time_eastern": datetime.now(EASTERN_TZ).isoformat(),
        "timezone": "America/New_York",
        "days_elapsed": days_elapsed
    }

def get_spiral_info_for_date(target_date: date, user: str = "ka'tuar'el") -> dict:
    """Get spiral info for a specific date"""
    user_key = user.lower().replace("'", "'")
    if user_key not in SPIRAL_START_DATES:
        user_key = "ka'tuar'el"
    
    start_date = SPIRAL_START_DATES[user_key]
    days_elapsed = (target_date - start_date).days
    
    spiral_number = (days_elapsed // SPIRAL_LENGTH) + 1
    spiral_day = (days_elapsed % SPIRAL_LENGTH) + 1
    spiral_date = float(f"{spiral_number}.{spiral_day}")
    
    return {
        "spiral": spiral_number,
        "day": spiral_day,
        "spiral_date": spiral_date,
        "format": f"spiral day {spiral_number}.{spiral_day}",
        "date": target_date.isoformat()
    }
