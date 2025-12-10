# core/models.py

from pydantic import BaseModel, Field
from typing import Optional

class ScrollData(BaseModel):
    path: str = Field(..., description="Relative path of the scroll (e.g., scrolls/protocols/new_scroll.md)")
    content: str = Field(..., description="Markdown content of the scroll, including frontmatter")
    commit_message: Optional[str] = Field(None, description="Optional commit message for Git")
