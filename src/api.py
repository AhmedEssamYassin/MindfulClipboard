"""Python API bridge for web UI."""
import os
import json
import threading
import webview
import keyboard

from .history import ClipboardHistory
from .monitor import ClipboardMonitor
from .utils import copyImageToClipboard, addToStartup, removeFromStartup
from .i18n import initI18n, getI18n
from .models import ClipboardEntry

import pyperclip


class ClipboardApi:
    """API exposed to the web frontend."""
    
    def __init__(self, manager):
        self._manager = manager
        self._refreshCallback = None
    
    def setRefreshCallback(self, callback):
        self._refreshCallback = callback
    
    def getHistory(self):
        """Return history entries as JSON-serializable list."""
        entries = self._manager.history.getAllEntries()
        result = []
        for entry in entries:
            entryData = {
                "contentHash": entry.contentHash,
                "timestamp": entry.timestamp.isoformat(),
                "isImage": entry.isImage,
                "isPinned": entry.isPinned,
                "content": "" if entry.isImage else entry.content
            }
            if entry.isImage:
                try:
                    import base64
                    from io import BytesIO
                    buffered = BytesIO()
                    # Create a small thumbnail to keep JSON payload lightweight
                    img = entry.content.copy()
                    if img.mode not in ('RGB', 'RGBA'):
                        img = img.convert('RGBA')
                    img.thumbnail((800, 800))
                    img.save(buffered, format="PNG")
                    imgStr = base64.b64encode(buffered.getvalue()).decode("utf-8")
                    entryData["imagePath"] = f"data:image/png;base64,{imgStr}"
                except Exception as e:
                    print(f"Error encoding image: {e}")
                    entryData["imagePath"] = ""
            result.append(entryData)
        return result
    
    def getImageLabel(self):
        """Get localized image label."""
        return getI18n().t("image_label")
    
    def copyEntry(self, contentHash):
        """Copy an entry to clipboard and simulate paste."""
        entry = self._manager.history.getEntryByHash(contentHash)
        if not entry:
            return False
        
        try:
            if entry.isImage:
                copyImageToClipboard(entry.content)
            else:
                pyperclip.copy(entry.content)
            
            self._manager.closePopupWeb()
            threading.Timer(0.15, lambda: keyboard.send("ctrl+v")).start()
            return True
        except Exception as e:
            print(f"Copy error: {e}")
            return False
    
    def pinEntry(self, contentHash):
        """Toggle pin status of an entry."""
        entry = self._manager.history.getEntryByHash(contentHash)
        if entry:
            self._manager.history.togglePin(entry)
            return True
        return False
    
    def removeEntry(self, contentHash):
        """Remove an entry from history."""
        entry = self._manager.history.getEntryByHash(contentHash)
        if entry:
            self._manager.history.removeEntry(entry)
            return True
        return False
    
    def setTheme(self, isDark):
        """Save theme preference."""
        self._manager.setTheme(isDark)
    
    def closeWindow(self):
        """Close the popup window."""
        self._manager.closePopupWeb()
