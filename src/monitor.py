"""Clipboard monitoring service."""
import threading
import time
import pyperclip
from typing import Callable

from .utils import getClipboardImage


class ClipboardMonitor:
    """Monitors clipboard for changes and triggers callbacks."""
    
    def __init__(self, onContentChange: Callable):
        self.onContentChange = onContentChange
        self.monitoring = True
        self._monitorThread = None
    
    def _monitorLoop(self):
        """Monitor clipboard for changes."""
        while self.monitoring:
            try:
                # Check for image first
                img = getClipboardImage()
                if img:
                    self.onContentChange(img, isImage=True)
                else:
                    # Check for text
                    text = pyperclip.paste()
                    if text and text.strip():
                        self.onContentChange(text, isImage=False)
            except:
                pass
            
            time.sleep(0.5)
    
    def start(self):
        """Start monitoring clipboard."""
        self._monitorThread = threading.Thread(target=self._monitorLoop, daemon=True)
        self._monitorThread.start()
    
    def stop(self):
        """Stop monitoring clipboard."""
        self.monitoring = False
        if self._monitorThread:
            self._monitorThread.join(timeout=1)