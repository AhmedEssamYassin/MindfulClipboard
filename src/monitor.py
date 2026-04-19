"""Clipboard monitoring service."""
import threading
import time
import ctypes
import pyperclip
from typing import Callable

from .utils import getClipboardImage


class ClipboardMonitor:
    """Monitors clipboard for changes and triggers callbacks."""
    
    def __init__(self, onContentChange: Callable):
        self.onContentChange = onContentChange
        self.monitoring = True
        self._monitorThread = None
        self._lastContent = None
        self._lastSequenceNumber = 0
        self._errorCount = 0
        self._maxErrors = 10
    
    def _getClipboardSequenceNumber(self) -> int:
        """Get Windows clipboard sequence number."""
        try:
            return ctypes.windll.user32.GetClipboardSequenceNumber()
        except Exception:
            return 0
    
    def _monitorLoop(self):
        """Monitor clipboard for changes."""
        print("[MONITOR] Clipboard monitoring started")
        
        # Get initial sequence number
        self._lastSequenceNumber = self._getClipboardSequenceNumber()
        
        while self.monitoring:
            try:
                currentSequence = self._getClipboardSequenceNumber()
                
                # Only check clipboard if sequence number changed
                if currentSequence != self._lastSequenceNumber:
                    self._lastSequenceNumber = currentSequence
                    
                    # Check for image first
                    img = getClipboardImage()
                    if img:
                        self.onContentChange(img, isImage=True)
                        self._errorCount = 0
                    else:
                        # Check for text
                        text = pyperclip.paste()
                        if text and text.strip():
                            self.onContentChange(text, isImage=False)
                            self._errorCount = 0
                            
            except KeyboardInterrupt:
                print("[MONITOR] Keyboard interrupt received")
                break
            except Exception as e:
                self._errorCount += 1
                
                if self._errorCount <= 3:
                    print(f"[WARNING] Clipboard monitoring error: {e}")
                elif self._errorCount == self._maxErrors:
                    print(f"[ERROR] Too many clipboard errors ({self._maxErrors}), suppressing further messages")
                
                if self._errorCount > self._maxErrors:
                    time.sleep(2)
            
            time.sleep(0.5)
        
        print("[MONITOR] Clipboard monitoring stopped")
    
    def start(self):
        """Start monitoring clipboard."""
        if self._monitorThread and self._monitorThread.is_alive():
            print("[WARNING] Monitor already running")
            return
            
        self.monitoring = True
        self._errorCount = 0
        self._monitorThread = threading.Thread(target=self._monitorLoop, daemon=True)
        self._monitorThread.start()
    
    def stop(self):
        """Stop monitoring clipboard."""
        print("[MONITOR] Stopping clipboard monitoring...")
        self.monitoring = False
        if self._monitorThread:
            self._monitorThread.join(timeout=2)
            if self._monitorThread.is_alive():
                print("[WARNING] Monitor thread did not stop cleanly")
            else:
                print("[OK] Monitor stopped successfully")