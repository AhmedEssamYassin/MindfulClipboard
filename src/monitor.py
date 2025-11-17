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
        self._lastContent = None
        self._errorCount = 0
        self._maxErrors = 10
    
    def _monitorLoop(self):
        """Monitor clipboard for changes."""
        print("[MONITOR] Clipboard monitoring started")
        
        while self.monitoring:
            try:
                # Check for image first
                img = getClipboardImage()
                if img:
                    self.onContentChange(img, isImage=True)
                    self._errorCount = 0  # Reset error count on success
                else:
                    # Check for text
                    text = pyperclip.paste()
                    if text and text.strip():
                        self.onContentChange(text, isImage=False)
                        self._errorCount = 0  # Reset error count on success
                        
            except KeyboardInterrupt:
                # Allow clean shutdown
                print("[MONITOR] Keyboard interrupt received")
                break
            except Exception as e:
                self._errorCount += 1
                
                # Only print first few errors to avoid spam
                if self._errorCount <= 3:
                    print(f"[WARNING] Clipboard monitoring error: {e}")
                elif self._errorCount == self._maxErrors:
                    print(f"[ERROR] Too many clipboard errors ({self._maxErrors}), suppressing further messages")
                
                # If too many consecutive errors, slow down polling
                if self._errorCount > self._maxErrors:
                    time.sleep(2)  # Slow down if having persistent issues
            
            # Normal polling interval
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