# api/github/service.py

from git import Repo
from pathlib import Path
from core.config import settings
from core.models import ScrollData, PatchScrollData
import os
import re


class GitHubService:
    def __init__(self):
        self.repo = Repo(settings.SCROLL_LIBRARY_PATH)
        self.root_path = Path(settings.SCROLL_LIBRARY_PATH)

    async def create_scroll(self, scroll_data: ScrollData) -> dict:
        rel_path = scroll_data.path
        content = scroll_data.content
        commit_message = scroll_data.commit_message or f"Create {rel_path}"

        full_path = self.root_path / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")

        # Stage and commit
        self.repo.index.add([str(full_path.relative_to(self.root_path))])
        self.repo.index.commit(commit_message)

        # Attempt to push to origin
        try:
            origin = self.repo.remote(name="origin")
            origin.push()
            pushed = True
        except Exception as e:
            pushed = False
            print(f"[Mythos] Git push failed: {e}")

        # (Optional) Update Redis if you’ve already implemented it
        try:
            from core.scroll_index import index_single_scroll
            index_single_scroll(full_path)
        except Exception as e:
            print(f"[Mythos] Redis index update failed: {e}")

        return {
            "status": "success",
            "path": rel_path,
            "commit_message": commit_message,
            "pushed": pushed
        }

async def patch_scroll(self, patch_data: PatchScrollData):
    scroll_path = os.path.join(self.repo_path, patch_data.path)
    
    if not os.path.isfile(scroll_path):
        raise HTTPException(status_code=404, detail=f"Scroll not found: {patch_data.path}")
    
    with open(scroll_path, "r", encoding="utf-8") as f:
        original_content = f.read()

    # Apply patch
    try:
        new_content = re.sub(patch_data.pattern, patch_data.replacement, original_content, flags=re.MULTILINE)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Regex error: {str(e)}")

    if new_content == original_content:
        return {"status": "noop", "message": "No change made"}

    with open(scroll_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    # Commit the change
    self.repo.index.add([patch_data.path])
    self.repo.index.commit(patch_data.commit_message)
    origin = self.repo.remote(name="origin")
    origin.push()

    return {
        "status": "patched",
        "path": patch_data.path,
        "commit_message": patch_data.commit_message,
        "pushed": True
    }
