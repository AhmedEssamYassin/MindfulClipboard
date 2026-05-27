"""Data models for clipboard entries."""
from dataclasses import dataclass
from datetime import datetime
from typing import Union

from PIL import Image

@dataclass
class ClipboardEntry:
    """Represents a clipboard entry with hash for deduplication."""
    content: Union[str, Image.Image]
    contentHash: str
    timestamp: datetime
    isImage: bool
    isPinned: bool = False