"""Clipboard history management."""
from typing import List, Union, Optional
from datetime import datetime
from PIL import Image

from .models import ClipboardEntry
from .utils import calculateHash


class ClipboardHistory:
    """Manages clipboard history with deduplication and pinning."""
    
    def __init__(self, maxEntries: int = 30):
        self.maxEntries = maxEntries
        self.history: List[ClipboardEntry] = []
        self.lastHash: Optional[str] = None
    
    def addEntry(self, content: Union[str, Image.Image], isImage: bool) -> bool:
        """
        Add content to history with deduplication.
        Returns True if entry was added, False if it was a duplicate.
        """
        contentHash = calculateHash(content)
        
        # Skip if duplicate of last entry
        if contentHash == self.lastHash:
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
        return True
    
    def togglePin(self, entry: ClipboardEntry) -> None:
        """Toggle pin status of an entry."""
        entry.isPinned = not entry.isPinned
        
        # Re-sort: pinned items first, then by timestamp
        pinned = [e for e in self.history if e.isPinned]
        unpinned = [e for e in self.history if not e.isPinned]
        self.history = pinned + unpinned
    
    def removeEntry(self, entry: ClipboardEntry) -> None:
        """Remove an entry from history."""
        if entry in self.history:
            self.history.remove(entry)
    
    def filterEntries(self, searchQuery: str) -> List[ClipboardEntry]:
        """Filter entries by search query."""
        if not searchQuery:
            return self.history
        
        query = searchQuery.lower()
        filtered = []
        
        for entry in self.history:
            if entry.isImage:
                # For images, search in the word "image"
                if query in "image".lower():
                    filtered.append(entry)
            else:
                # For text, check if searchQuery is a substring
                if query in entry.content.lower():
                    filtered.append(entry)
        
        return filtered
    
    def getAllEntries(self) -> List[ClipboardEntry]:
        """Get all entries in history."""
        return self.history.copy()