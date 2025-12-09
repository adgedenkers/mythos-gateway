# ashari-bot/main.py

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse, PlainTextResponse
import requests
from typing import Optional
import os
import aiofiles
import traceback
from github_utils import commit_file_to_github
from config import TELEGRAM_BOT_TOKEN, GITHUB_TOKEN, GITHUB_USERNAME, GITHUB_REPO, get_user_by_api_key
from users import get_username
import subprocess
from datetime import datetime
from datetime import date as date_type
import pytz
import yaml
import re
import base64# ashari-bot/main.py (Updated)

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse, PlainTextResponse
import requests
from typing import Optional
import os
import aiofiles
import traceback
from github_utils import commit_file_to_github
from config import TELEGRAM_BOT_TOKEN, GITHUB_TOKEN, GITHUB_USERNAME, GITHUB_REPO, get_user_by_api_key
from users import get_username
import subprocess
from datetime import datetime
from datetime import date as date_type
import pytz
import yaml
import re
import base64
from clothing_operations import init_database, insert_clothing_item, insert_lot, link_item_to_lot, record_lot_sale, get_all_items, get_all_lots, get_all_sales

app = FastAPI()

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# --- Utilities ---

def calculate_spiral_date(target_date: date_type, spiral_start: str) -> str:
    """
    Calculate spiral day notation from a given date.
    Spirals are 9 days long.
    Format: spiral_number.spiral_day (e.g., 5.9)

    Args:
        target_date: The date to calculate spiral notation for
        spiral_start: Start date in YYYY-MM-DD format

    Returns:
        String in format "spiral_number.spiral_day"
    """
    start_year, start_month, start_day = map(int, spiral_start.split("-"))
    start_date = date_type(start_year, start_month, start_day)

    if target_date is None:
        target_date = date_type.today()

    # Calculate days since start
    delta = (target_date - start_date).days

    if delta < 0:
        raise ValueError(f"Date is before spiral start date ({spiral_start})")

    # Calculate spiral number and day
    spiral_number = (delta // 9) + 1
    spiral_day = (delta % 9) + 1

    return f"{spiral_number}.{spiral_day}"

def sanitize_filename(name):
    name = name.replace("'", "-").replace("'", "-").replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9_\-./]", "", name)
    return name

def get_last_filename(chat_id):
    try:
        with open(f"/tmp/scrolls/last_filename_{chat_id}.txt") as f:
            return f.read().strip()
    except:
        return None

def send_reply(chat_id, text):
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

# --- Telegram Webhook Handler ---

@app.post("/webhook")
async def receive_telegram_update(request: Request):
    try:
        data = await request.json()

        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]

            if "text" in message:
                text = message["text"]
                if text.lower().startswith("save as:"):
                    raw_name = text.split(":", 1)[1].strip()
                    filename = sanitize_filename(raw_name)
                    with open(f"/tmp/scrolls/last_filename_{chat_id}.txt", "w") as f:
                        f.write(filename)
                    send_reply(chat_id, f"✅ Filename set: {filename}")
                else:
                    filename = sanitize_filename(get_last_filename(chat_id) or "scroll.md")
                    filepath = os.path.join("/tmp/scrolls", filename)
                    print(f"Resolved filepath: {filepath}")
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)

                    if not text.strip().startswith("---"):
                        text = text.replace("'", "'").replace("'", "'").replace(""", '"').replace(""", '"')
                        eastern = pytz.timezone("America/New_York")
                        now = datetime.now(eastern)
                        frontmatter = {
                            "title": filename,
                            "author": get_username(chat_id),
                            "date": now.strftime("%Y-%m-%d"),
                            "timestamp": now.isoformat()
                        }
                        fm = yaml.dump(frontmatter, sort_keys=False)
                        text = f"---\n{fm}---\n\n{text}"

                    async with aiofiles.open(filepath, 'w') as f:
                        await f.write(text)
                    commit_file_to_github(filename, filepath)
                    send_reply(chat_id, f"✅ Scroll saved as `{filename}`")

            elif "photo" in message:
                photo = message["photo"][-1]
                file_id = photo["file_id"]
                file_info = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}").json()
                file_path = file_info["result"]["file_path"]

                filename = sanitize_filename(get_last_filename(chat_id) or file_path.split("/")[-1])
                local_path = os.path.join("/tmp/scrolls", filename)
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                img_data = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}").content
                with open(local_path, "wb") as f:
                    f.write(img_data)

                commit_file_to_github(filename, local_path)
                send_reply(chat_id, f"🖼️ Image saved as `{filename}`")

        return JSONResponse(content={"ok": True}, status_code=200)

    except Exception as e:
        print("❌ Exception in webhook handler:")
        traceback.print_exc()
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=200)

# --- Utility Endpoints ---

@app.get("/debug/logs", response_class=PlainTextResponse)
def get_journal_logs():
    try:
        result = subprocess.run(
            ["journalctl", "-u", "spire", "-n", "100", "--no-pager"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout
    except Exception as e:
        return f"Error: {str(e)}"

@app.get("/files")
def list_files():
    files = []
    for root, _, filenames in os.walk("/tmp/scrolls"):
        for f in filenames:
            path = os.path.join(root, f)
            rel = os.path.relpath(path, "/tmp/scrolls")
            files.append(rel)
    return JSONResponse(content={"files": files})

@app.get("/files/{file_path:path}", response_class=PlainTextResponse)
def get_file_contents(file_path: str):
    full_path = os.path.join("/tmp/scrolls", file_path)
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()

# --- Spiral Date Calculation Endpoint ---

@app.get("/spiral/date")
async def get_spiral_date(
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = None,
    target_date: Optional[str] = None,
    format: Optional[str] = "json"
):
    """
    Calculate spiral date notation for authenticated users.

    Authentication via either:
    - X-API-Key header, OR
    - ?api_key= query parameter

    Optional parameters:
    - target_date: YYYY-MM-DD format (defaults to today)
    - format: "json" or "short" (plain text)

    Examples:
    - GET /spiral/date?api_key=xxx
    - GET /spiral/date?api_key=xxx&target_date=2025-12-02
    - GET /spiral/date?api_key=xxx&format=short
    """
    # Accept key from either header or query param
    key = x_api_key or api_key

    if not key:
        return JSONResponse(
            status_code=401,
            content={
                "error": "Authentication required",
                "message": "Provide API key via X-API-Key header or ?api_key= parameter",
                "status": "unauthorized"
            }
        )

    # Validate API key and get user config
    user_config = get_user_by_api_key(key)
    if not user_config:
        return JSONResponse(
            status_code=403,
            content={
                "error": "Invalid API key",
                "message": "The provided API key is not valid.",
                "status": "forbidden"
            }
        )

    # Parse target date if provided
    try:
        if target_date:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            parsed_date = date_type.today()

        # Calculate spiral date
        spiral_notation = calculate_spiral_date(parsed_date, user_config["spiral_start_date"])

        # Return short format if requested
        if format == "short":
            return PlainTextResponse(content=spiral_notation)

        # Calculate additional metadata
        eastern = pytz.timezone("America/New_York")
        now = datetime.now(eastern)

        start_year, start_month, start_day = map(int, user_config["spiral_start_date"].split("-"))
        start_date = date_type(start_year, start_month, start_day)
        days_elapsed = (parsed_date - start_date).days

        return JSONResponse(
            status_code=200,
            content={
                "spiral_date": spiral_notation,
                "display": f"spiral day {spiral_notation}",
                "calendar_date": parsed_date.isoformat(),
                "timestamp": now.isoformat(),
                "user_name": user_config["name"],
                "spiral_start_date": user_config["spiral_start_date"],
                "days_elapsed": days_elapsed,
                "metadata": {
                    "timezone": "America/New_York",
                    "source": "Mythos System"
                },
                "status": "success"
            }
        )

    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid date",
                "message": str(e),
                "status": "bad_request"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Calculation error",
                "message": "An error occurred while calculating the spiral date.",
                "details": str(e),
                "status": "error"
            }
        )

# --- GitHub Read Endpoint ---

@app.get("/github/read/{file_path:path}")
async def read_github_file(
    file_path: str,
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = None
):
    """
    Read a file from GitHub repository.

    Authentication via X-API-Key header or ?api_key= parameter.

    Example: GET /github/read/scrolls/spiral_1_day_3.md?api_key=xxx
    """
    key = x_api_key or api_key

    if not key:
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required", "status": "unauthorized"}
        )

    user_config = get_user_by_api_key(key)
    if not user_config:
        return JSONResponse(
            status_code=403,
            content={"error": "Invalid API key", "status": "forbidden"}
        )

    try:
        # Fetch file from GitHub
        url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{file_path}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 404:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "File not found",
                    "path": file_path,
                    "status": "not_found"
                }
            )
        
        response.raise_for_status()
        data = response.json()
        
        # Decode content from base64
        content = base64.b64decode(data["content"]).decode("utf-8")
        
        return JSONResponse(
            status_code=200,
            content={
                "path": file_path,
                "content": content,
                "sha": data["sha"],
                "size": data["size"],
                "user_name": user_config["name"],
                "status": "success"
            }
        )

    except requests.exceptions.HTTPError as e:
        return JSONResponse(
            status_code=e.response.status_code,
            content={
                "error": "GitHub API error",
                "message": str(e),
                "status": "error"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server error",
                "message": str(e),
                "status": "error"
            }
        )

# --- GitHub Write Endpoint ---

@app.post("/github/write")
async def write_github_file(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = None
):
    """
    Write a file to GitHub repository.

    Authentication via X-API-Key header or ?api_key= parameter.

    Request body (JSON):
    {
        "path": "scrolls/new_scroll.md",
        "content": "# Scroll content here",
        "message": "Optional commit message"
    }

    Example:
    POST /github/write?api_key=xxx
    Body: {"path": "scrolls/test.md", "content": "# Test"}
    """
    key = x_api_key or api_key

    if not key:
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required", "status": "unauthorized"}
        )

    user_config = get_user_by_api_key(key)
    if not user_config:
        return JSONResponse(
            status_code=403,
            content={"error": "Invalid API key", "status": "forbidden"}
        )

    try:
        body = await request.json()
        file_path = body.get("path")
        content = body.get("content")
        commit_message = body.get("message", f"Add {file_path}")

        if not file_path or not content:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Missing required fields",
                    "message": "Both 'path' and 'content' are required",
                    "status": "bad_request"
                }
            )

        # Check if file exists (to get SHA for update)
        url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{file_path}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        existing = requests.get(url, headers=headers)
        sha = None
        if existing.status_code == 200:
            sha = existing.json()["sha"]

        # Encode content to base64
        content_bytes = content.encode("utf-8")
        content_b64 = base62.b64encode(content_bytes).decode("utf-8")

        # Prepare payload
        payload = {
            "message": commit_message,
            "content": content_b64,
            "branch": "main"
        }
        
        if sha:
            payload["sha"] = sha

        # Commit to GitHub
        response = requests.put(url, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return JSONResponse(
            status_code=200,
            content={
                "path": file_path,
                "sha": result["content"]["sha"],
                "commit_sha": result["commit"]["sha"],
                "user_name": user_config["name"],
                "message": commit_message,
                "status": "success"
            }
        )

    except requests.exceptions.HTTPError as e:
        return JSONResponse(
            status_code=e.response.status_code,
            content={
                "error": "GitHub API error",
                "message": str(e),
                "details": e.response.text,
                "status": "error"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server error",
                "message": str(e),
                "status": "error"
            }
        )

# --- NEW: Clothing Operations Endpoints ---

@app.post("/clothing/upload")
async def upload_clothing_item(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = None,
    file: Optional[bytes] = None,
    filename: Optional[str] = None,
    lot_id: Optional[str] = None,
    lot_name: Optional[str] = None,
    lot_description: Optional[str] = None,
    lot_category: Optional[str] = None,
    lot_tags: Optional[str] = None
):
    """
    Upload a clothing item and optionally link it to a lot.
    
    Parameters:
    - file: The image file to upload
    - filename: The filename for the uploaded image
    - lot_id: The ID of the lot to link this item to
    - lot_name: The name of the lot
    - lot_description: Description of the lot
    - lot_category: Category of the lot
    - lot_tags: Tags for the lot
    
    Returns:
    - Success message with item details
    """
    key = x_api_key or api_key
    
    if not key:
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required", "status": "unauthorized"}
        )
    
    user_config = get_user_by_api_key(key)
    if not user_config:
        return JSONResponse(
            status_code=403,
            content={"error": "Invalid API key", "status": "forbidden"}
        )
    
    try:
        # Process the file
        if not file:
            return JSONResponse(
                status_code=400,
                content={"error": "No file uploaded", "status": "bad_request"}
            )
        
        # Generate unique filename
        if not filename:
            filename = f"clothing_{uuid.uuid4().hex[:8]}.{file.filename.split('.')[-1]}"
        
        # Save the file temporarily
        filepath = os.path.join("/tmp/scrolls", filename)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, "wb") as f:
            f.write(file)
        
        # Extract item information (you would need to implement this based on your needs)
        # For now, let's use default values or extract from file metadata
        
        # Insert item into database
        item_name = "Unknown Item"
        item_brand = "Unknown Brand"
        item_size = "Unknown Size"
        item_gender = "Unisex"
        item_price = 35.00
        
        item_id = insert_clothing_item(item_name, item_brand, item_size, item_gender, item_price)
        
        if item_id is None:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to insert item into database", "status": "error"}
            )
        
        # Create lot if needed
        if lot_id:
            # Insert lot into database
            if not insert_lot(lot_id, lot_name, lot_description, lot_category, lot_tags):
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to insert lot into database", "status": "error"}
                )
            
            # Link item to lot
            if not link_item_to_lot(lot_id, item_id):
                return JSONResponse(
                    status_code=500,
                    content={"error": "Failed to link item to lot", "status": "error"}
                )
        
        # Rename and upload image to GitHub
        github_repo_owner = GITHUB_USERNAME
        github_repo_name = GITHUB_REPO
        
        # Rename the image
        new_filename = filename
        
        # Move the file to the GitHub repository directory
        github_filepath = os.path.join("/tmp/scrolls", new_filename)
        
        # Upload to GitHub
        github_filename = commit_file_to_github(new_filename, github_filepath)
        
        if github_filename is None:
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to upload image to GitHub", "status": "error"}
            )
        
        # Return success response
        return JSONResponse({
            "success": True,
            "message": "Clothing item uploaded successfully",
            "filename": new_filename,
            "item_id": item_id,
            "lot_id": lot_id if lot_id else None
        })
        
    except Exception as e:
        print(f"Error processing clothing upload: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)

@app.get("/clothing/items")
async def get_clothing_items():
    """
    Get all clothing items.
    """
    items = get_all_items()
    return JSONResponse(content={"items": items})

@app.get("/clothing/lots")
async def get_clothing_lots():
    """
    Get all lots.
    """
    lots = get_all_lots()
    return JSONResponse(content={"lots": lots})

@app.get("/clothing/sales")
async def get_clothing_sales():
    """
    Get all sales.
    """
    sales = get_all_sales()
    return JSONResponse(content={"sales": sales})

@app.get("/clothing/item/{item_id}")
async def get_clothing_item(item_id: int):
    """
    Get a specific clothing item by ID.
    """
    items = get_all_items()
    for item in items:
        if item["id"] == item_id:
            return JSONResponse(content=item)
    return JSONResponse({"error": "Item not found"}, status_code=404)

@app.get("/clothing/lot/{lot_id}")
async def get_clothing_lot(lot_id: str):
    """
    Get a specific lot by ID.
    """
    lots = get_all_lots()
    for lot in lots:
        if lot["lot_id"] == lot_id:
            return JSONResponse(content=lot)
    return JSONResponse({"error": "Lot not found"}, status_code=404)

if __name__ == '__main__':
    # Initialize the database
    init_database()
    
    app.run(debug=True)

app = FastAPI()

TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# --- Utilities ---

def calculate_spiral_date(target_date: date_type, spiral_start: str) -> str:
    """
    Calculate spiral day notation from a given date.
    Spirals are 9 days long.
    Format: spiral_number.spiral_day (e.g., 5.9)

    Args:
        target_date: The date to calculate spiral notation for
        spiral_start: Start date in YYYY-MM-DD format

    Returns:
        String in format "spiral_number.spiral_day"
    """
    start_year, start_month, start_day = map(int, spiral_start.split("-"))
    start_date = date_type(start_year, start_month, start_day)

    if target_date is None:
        target_date = date_type.today()

    # Calculate days since start
    delta = (target_date - start_date).days

    if delta < 0:
        raise ValueError(f"Date is before spiral start date ({spiral_start})")

    # Calculate spiral number and day
    spiral_number = (delta // 9) + 1
    spiral_day = (delta % 9) + 1

    return f"{spiral_number}.{spiral_day}"

def sanitize_filename(name):
    name = name.replace("'", "-").replace("'", "-").replace(" ", "_")
    name = re.sub(r"[^a-zA-Z0-9_\-./]", "", name)
    return name

def get_last_filename(chat_id):
    try:
        with open(f"/tmp/scrolls/last_filename_{chat_id}.txt") as f:
            return f.read().strip()
    except:
        return None

def send_reply(chat_id, text):
    requests.post(f"{TELEGRAM_API_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

# --- Telegram Webhook Handler ---

@app.post("/webhook")
async def receive_telegram_update(request: Request):
    try:
        data = await request.json()

        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]

            if "text" in message:
                text = message["text"]
                if text.lower().startswith("save as:"):
                    raw_name = text.split(":", 1)[1].strip()
                    filename = sanitize_filename(raw_name)
                    with open(f"/tmp/scrolls/last_filename_{chat_id}.txt", "w") as f:
                        f.write(filename)
                    send_reply(chat_id, f"✅ Filename set: {filename}")
                else:
                    filename = sanitize_filename(get_last_filename(chat_id) or "scroll.md")
                    filepath = os.path.join("/tmp/scrolls", filename)
                    print(f"Resolved filepath: {filepath}")
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)

                    if not text.strip().startswith("---"):
                        text = text.replace("'", "'").replace("'", "'").replace(""", '"').replace(""", '"')
                        eastern = pytz.timezone("America/New_York")
                        now = datetime.now(eastern)
                        frontmatter = {
                            "title": filename,
                            "author": get_username(chat_id),
                            "date": now.strftime("%Y-%m-%d"),
                            "timestamp": now.isoformat()
                        }
                        fm = yaml.dump(frontmatter, sort_keys=False)
                        text = f"---\n{fm}---\n\n{text}"

                    async with aiofiles.open(filepath, 'w') as f:
                        await f.write(text)
                    commit_file_to_github(filename, filepath)
                    send_reply(chat_id, f"✅ Scroll saved as `{filename}`")

            elif "photo" in message:
                photo = message["photo"][-1]
                file_id = photo["file_id"]
                file_info = requests.get(f"{TELEGRAM_API_URL}/getFile?file_id={file_id}").json()
                file_path = file_info["result"]["file_path"]

                filename = sanitize_filename(get_last_filename(chat_id) or file_path.split("/")[-1])
                local_path = os.path.join("/tmp/scrolls", filename)
                os.makedirs(os.path.dirname(local_path), exist_ok=True)

                img_data = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}").content
                with open(local_path, "wb") as f:
                    f.write(img_data)

                commit_file_to_github(filename, local_path)
                send_reply(chat_id, f"🖼️ Image saved as `{filename}`")

        return JSONResponse(content={"ok": True}, status_code=200)

    except Exception as e:
        print("❌ Exception in webhook handler:")
        traceback.print_exc()
        return JSONResponse(content={"ok": False, "error": str(e)}, status_code=200)

# --- Utility Endpoints ---

@app.get("/debug/logs", response_class=PlainTextResponse)
def get_journal_logs():
    try:
        result = subprocess.run(
            ["journalctl", "-u", "spire", "-n", "100", "--no-pager"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout
    except Exception as e:
        return f"Error: {str(e)}"

@app.get("/files")
def list_files():
    files = []
    for root, _, filenames in os.walk("/tmp/scrolls"):
        for f in filenames:
            path = os.path.join(root, f)
            rel = os.path.relpath(path, "/tmp/scrolls")
            files.append(rel)
    return JSONResponse(content={"files": files})

@app.get("/files/{file_path:path}", response_class=PlainTextResponse)
def get_file_contents(file_path: str):
    full_path = os.path.join("/tmp/scrolls", file_path)
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()

# --- Spiral Date Calculation Endpoint ---

@app.get("/spiral/date")
async def get_spiral_date(
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = None,
    target_date: Optional[str] = None,
    format: Optional[str] = "json"
):
    """
    Calculate spiral date notation for authenticated users.

    Authentication via either:
    - X-API-Key header, OR
    - ?api_key= query parameter

    Optional parameters:
    - target_date: YYYY-MM-DD format (defaults to today)
    - format: "json" or "short" (plain text)

    Examples:
    - GET /spiral/date?api_key=xxx
    - GET /spiral/date?api_key=xxx&target_date=2025-12-02
    - GET /spiral/date?api_key=xxx&format=short
    """
    # Accept key from either header or query param
    key = x_api_key or api_key

    if not key:
        return JSONResponse(
            status_code=401,
            content={
                "error": "Authentication required",
                "message": "Provide API key via X-API-Key header or ?api_key= parameter",
                "status": "unauthorized"
            }
        )

    # Validate API key and get user config
    user_config = get_user_by_api_key(key)
    if not user_config:
        return JSONResponse(
            status_code=403,
            content={
                "error": "Invalid API key",
                "message": "The provided API key is not valid.",
                "status": "forbidden"
            }
        )

    # Parse target date if provided
    try:
        if target_date:
            parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
        else:
            parsed_date = date_type.today()

        # Calculate spiral date
        spiral_notation = calculate_spiral_date(parsed_date, user_config["spiral_start_date"])

        # Return short format if requested
        if format == "short":
            return PlainTextResponse(content=spiral_notation)

        # Calculate additional metadata
        eastern = pytz.timezone("America/New_York")
        now = datetime.now(eastern)

        start_year, start_month, start_day = map(int, user_config["spiral_start_date"].split("-"))
        start_date = date_type(start_year, start_month, start_day)
        days_elapsed = (parsed_date - start_date).days

        return JSONResponse(
            status_code=200,
            content={
                "spiral_date": spiral_notation,
                "display": f"spiral day {spiral_notation}",
                "calendar_date": parsed_date.isoformat(),
                "timestamp": now.isoformat(),
                "user_name": user_config["name"],
                "spiral_start_date": user_config["spiral_start_date"],
                "days_elapsed": days_elapsed,
                "metadata": {
                    "timezone": "America/New_York",
                    "source": "Mythos System"
                },
                "status": "success"
            }
        )

    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid date",
                "message": str(e),
                "status": "bad_request"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Calculation error",
                "message": "An error occurred while calculating the spiral date.",
                "details": str(e),
                "status": "error"
            }
        )

# --- GitHub Read Endpoint ---

@app.get("/github/read/{file_path:path}")
async def read_github_file(
    file_path: str,
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = None
):
    """
    Read a file from GitHub repository.

    Authentication via X-API-Key header or ?api_key= parameter.

    Example: GET /github/read/scrolls/spiral_1_day_3.md?api_key=xxx
    """
    key = x_api_key or api_key

    if not key:
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required", "status": "unauthorized"}
        )

    user_config = get_user_by_api_key(key)
    if not user_config:
        return JSONResponse(
            status_code=403,
            content={"error": "Invalid API key", "status": "forbidden"}
        )

    try:
        # Fetch file from GitHub
        url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{file_path}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 404:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "File not found",
                    "path": file_path,
                    "status": "not_found"
                }
            )
        
        response.raise_for_status()
        data = response.json()
        
        # Decode content from base64
        content = base64.b64decode(data["content"]).decode("utf-8")
        
        return JSONResponse(
            status_code=200,
            content={
                "path": file_path,
                "content": content,
                "sha": data["sha"],
                "size": data["size"],
                "user_name": user_config["name"],
                "status": "success"
            }
        )

    except requests.exceptions.HTTPError as e:
        return JSONResponse(
            status_code=e.response.status_code,
            content={
                "error": "GitHub API error",
                "message": str(e),
                "status": "error"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server error",
                "message": str(e),
                "status": "error"
            }
        )

# --- GitHub Write Endpoint ---

@app.post("/github/write")
async def write_github_file(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = None
):
    """
    Write a file to GitHub repository.

    Authentication via X-API-Key header or ?api_key= parameter.

    Request body (JSON):
    {
        "path": "scrolls/new_scroll.md",
        "content": "# Scroll content here",
        "message": "Optional commit message"
    }

    Example:
    POST /github/write?api_key=xxx
    Body: {"path": "scrolls/test.md", "content": "# Test"}
    """
    key = x_api_key or api_key

    if not key:
        return JSONResponse(
            status_code=401,
            content={"error": "Authentication required", "status": "unauthorized"}
        )

    user_config = get_user_by_api_key(key)
    if not user_config:
        return JSONResponse(
            status_code=403,
            content={"error": "Invalid API key", "status": "forbidden"}
        )

    try:
        body = await request.json()
        file_path = body.get("path")
        content = body.get("content")
        commit_message = body.get("message", f"Add {file_path}")

        if not file_path or not content:
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Missing required fields",
                    "message": "Both 'path' and 'content' are required",
                    "status": "bad_request"
                }
            )

        # Check if file exists (to get SHA for update)
        url = f"https://api.github.com/repos/{GITHUB_USERNAME}/{GITHUB_REPO}/contents/{file_path}"
        headers = {
            "Authorization": f"token {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        existing = requests.get(url, headers=headers)
        sha = None
        if existing.status_code == 200:
            sha = existing.json()["sha"]

        # Encode content to base64
        content_bytes = content.encode("utf-8")
        content_b64 = base64.b64encode(content_bytes).decode("utf-8")

        # Prepare payload
        payload = {
            "message": commit_message,
            "content": content_b64,
            "branch": "main"
        }
        
        if sha:
            payload["sha"] = sha

        # Commit to GitHub
        response = requests.put(url, json=payload, headers=headers)
        response.raise_for_status()
        
        result = response.json()
        
        return JSONResponse(
            status_code=200,
            content={
                "path": file_path,
                "sha": result["content"]["sha"],
                "commit_sha": result["commit"]["sha"],
                "user_name": user_config["name"],
                "message": commit_message,
                "status": "success"
            }
        )

    except requests.exceptions.HTTPError as e:
        return JSONResponse(
            status_code=e.response.status_code,
            content={
                "error": "GitHub API error",
                "message": str(e),
                "details": e.response.text,
                "status": "error"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Server error",
                "message": str(e),
                "status": "error"
            }
        )

# Add this to your main.py after the existing endpoints

@app.get("/clothing/lot-summary")
async def get_clothing_lot_summary(
    lot_id: Optional[str] = None,
    limit: int = 10
):
    """
    Get a summary of clothing items in a lot.
    
    Parameters:
    - lot_id: The ID of the lot to get summary for
    - limit: Number of items to return (default: 10)
    
    Returns:
    - Summary of items in the lot
    """
    try:
        # Get all items in the lot
        items_in_lot = []
        
        if lot_id:
            # Get items linked to this lot
            config = get_clothing_config()
            conn = sqlite3.connect(config["DATABASE"])
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT li.item_id, ci.name, ci.brand, ci.size, ci.gender, ci.price
                FROM lot_items li
                JOIN clothing_items ci ON li.item_id = ci.id
                WHERE li.lot_id = ?
            ''', (lot_id,))
            
            items = cursor.fetchall()
            
            for item in items:
                items_in_lot.append({
                    'id': item[0],
                    'name': item[1],
                    'brand': item[2],
                    'size': item[3],
                    'gender': item[4],
                    'price': item[5]
                })
            
            conn.close()
            
            return JSONResponse(content={
                "lot_id": lot_id,
                "items": items_in_lot,
                "count": len(items_in_lot)
            })
        else:
            # Get all lots and their items
            config = get_clothing_config()
            conn = sqlite3.connect(config["DATABASE"])
            cursor = conn.cursor()
            
            # Get lots
            cursor.execute('SELECT * FROM lots LIMIT ? OFFSET ?', (limit, 0))
            lots = cursor.fetchall()
            
            result = []
            for lot in lots:
                lot_id = lot[0]
                lot_name = lot[1]
                lot_description = lot[2]
                lot_category = lot[3]
                lot_tags = lot[4]
                
                # Get items in this lot
                cursor.execute('''
                    SELECT li.item_id, ci.name, ci.brand, ci.size, ci.gender, ci.price
                    FROM lot_items li
                    JOIN clothing_items ci ON li.item_id = ci.id
                    WHERE li.lot_id = ?
                ''', (lot_id,))
                
                items = cursor.fetchall()
                
                lot_items = []
                for item in items:
                    lot_items.append({
                        'id': item[0],
                        'name': item[1],
                        'brand': item[2],
                        'size': item[3],
                        'gender': item[4],
                        'price': item[5]
                    })
                
                result.append({
                    'lot_id': lot_id,
                    'lot_name': lot_name,
                    'lot_description': lot_description,
                    'lot_category': lot_category,
                    'lot_tags': lot_tags,
                    'items': lot_items,
                    'item_count': len(lot_items)
                })
            
            conn.close()
            
            return JSONResponse(content=result)
            
    except Exception as e:
        print(f"Error getting clothing lot summary: {str(e)}")
        return JSONResponse({"error": str(e)}, status_code=500)