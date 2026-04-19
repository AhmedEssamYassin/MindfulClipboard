"""Clipboard history management."""
import threading
import json
import io
from pathlib import Path
from typing import List, Union, Optional
from datetime import datetime
from PIL import Image

from .models import ClipboardEntry
from .utils import calculateHash, getAppDataDir
from .i18n import getI18n

HISTORY_FILE = getAppDataDir() / "history.json"
HISTORY_IMAGES_DIR = getAppDataDir() / "history_images"


class ClipboardHistory:
    """Manages clipboard history with deduplication and pinning."""
    
    def __init__(self, maxEntries: int = 30):
        self.maxEntries = maxEntries
        self.history: List[ClipboardEntry] = []
        self.lastHash: Optional[str] = None
        self.lock = threading.Lock()
        self.loadFromFile()
    
    def addEntry(self, content: Union[str, Image.Image], isImage: bool) -> bool:
        """
        Add content to history with deduplication.
        Returns True if entry was added, False if it was a duplicate.
        """
        contentHash = calculateHash(content)
        
        with self.lock:
            # Skip if duplicate of last entry
            if contentHash == self.lastHash:
                return False
            
            # Check for existing duplicate - if pinned, don't add
            for entry in self.history:
                if entry.contentHash == contentHash and entry.isPinned:
                    return False
            
            # Remove duplicate if exists in history (but keep if pinned)
            for entry in self.history[:]:
                if entry.contentHash == contentHash and not entry.isPinned:
                    self.history.remove(entry)
            
            # Add new entry at the beginning
            entry = ClipboardEntry(
                content=content,
                contentHash=contentHash,
                timestamp=datetime.now(),
                isImage=isImage,
                isPinned=False
            )
            
            # Insert after pinned items
            pinnedCount = sum(1 for e in self.history if e.isPinned)
            self.history.insert(pinnedCount, entry)
            
            # Maintain max entries (don't count pinned items)
            unpinned = [e for e in self.history if not e.isPinned]
            if len(unpinned) > self.maxEntries:
                # Remove oldest unpinned entries
                for entry in unpinned[self.maxEntries:]:
                    self.history.remove(entry)
            
            self.lastHash = contentHash
            self.saveToFile()
            return True
    
    def togglePin(self, entry: ClipboardEntry) -> None:
        """Toggle pin status of an entry."""
        with self.lock:
            entry.isPinned = not entry.isPinned
            
            # Re-sort: pinned items first, then by timestamp
            pinned = [e for e in self.history if e.isPinned]
            unpinned = [e for e in self.history if not e.isPinned]
            self.history = pinned + unpinned
            self.saveToFile()
    
    def removeEntry(self, entry: ClipboardEntry) -> None:
        """Remove an entry from history."""
        with self.lock:
            if entry in self.history:
                self.history.remove(entry)
                self.saveToFile()
    
    def filterEntries(self, searchQuery: str) -> List[ClipboardEntry]:
        """Filter entries by search query."""
        with self.lock:
            if not searchQuery:
                return self.history.copy()
            
            query = searchQuery.lower()
            filtered = []
            
            for entry in self.history:
                if entry.isImage:
                    imageLabel = getI18n().t("image_label").lower()
                    if query in imageLabel:
                        filtered.append(entry)
                else:
                    # For text, check if searchQuery is a substring
                    if query in entry.content.lower():
                        filtered.append(entry)
            
            return filtered
    
    def getAllEntries(self) -> List[ClipboardEntry]:
        """Get all entries in history."""
        with self.lock:
            return self.history.copy()
    
    def getEntryByHash(self, contentHash: str) -> Optional[ClipboardEntry]:
        """Get entry by content hash."""
        with self.lock:
            for entry in self.history:
                if entry.contentHash == contentHash:
                    return entry
            return None
    
    def getImagePath(self, contentHash: str) -> str:
        """Get image file path for an entry."""
        imgPath = HISTORY_IMAGES_DIR / f"{contentHash}.png"
        return str(imgPath) if imgPath.exists() else ""
    
    def saveToFile(self) -> None:
        """Save history to file."""
        try:
            HISTORY_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
            
            entriesData = []
            for entry in self.history:
                entryData = {
                    "contentHash": entry.contentHash,
                    "timestamp": entry.timestamp.isoformat(),
                    "isImage": entry.isImage,
                    "isPinned": entry.isPinned
                }
                
                if entry.isImage:
                    imgPath = HISTORY_IMAGES_DIR / f"{entry.contentHash}.png"
                    if not imgPath.exists():
                        try:
                            entry.content.save(imgPath, format="PNG")
                        except Exception as e:
                            print(f"Failed to save image: {e}")
                            continue
                    entryData["imagePath"] = str(imgPath)
                else:
                    entryData["content"] = entry.content
                
                entriesData.append(entryData)
            
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump({"entries": entriesData, "maxEntries": self.maxEntries}, f, indent=2)
        except Exception as e:
            print(f"Failed to save history: {e}")
    
    def loadFromFile(self) -> None:
        """Load history from file."""
        try:
            if not HISTORY_FILE.exists():
                return
            
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            self.maxEntries = data.get("maxEntries", 30)
            
            for entryData in data.get("entries", []):
                try:
                    if entryData.get("isImage"):
                        imgPath = Path(entryData.get("imagePath", ""))
                        if imgPath.exists():
                            content = Image.open(imgPath)
                        else:
                            continue
                    else:
                        content = entryData.get("content", "")
                    
                    entry = ClipboardEntry(
                        content=content,
                        contentHash=entryData.get("contentHash", ""),
                        timestamp=datetime.fromisoformat(entryData.get("timestamp", datetime.now().isoformat())),
                        isImage=entryData.get("isImage", False),
                        isPinned=entryData.get("isPinned", False)
                    )
                    self.history.append(entry)
                except Exception as e:
                    print(f"Failed to load entry: {e}")
            
            if self.history:
                self.lastHash = self.history[0].contentHash
        except Exception as e:
            print(f"Failed to load history: {e}")

    def getImagePath(self, contentHash: str) -> str:
        """Get the file path for a cached image by hash."""
        imgPath = HISTORY_IMAGES_DIR / f"{contentHash}.png"
        return str(imgPath) if imgPath.exists() else ""