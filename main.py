"""Main entry point for the Clipboard Manager application."""
import tkinter as tk
import sys
import signal
import os
import time
from pathlib import Path
from src.manager import ClipboardManager
from src.tray import SystemTray
from src.i18n import initI18n
from src.utils import addToStartup, isInStartup

def resourcePath(relativePath):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        basePath = sys._MEIPASS
    except Exception:
        # Not in a PyInstaller bundle, so use the script's directory
        basePath = os.path.abspath(os.path.dirname(__file__))
    
    return os.path.join(basePath, relativePath)

def main():
    """Initialize and run the clipboard manager."""
    # Initialize i18n system
    localesPath = resourcePath("locales")
    i18n = initI18n(localesDir=localesPath, defaultLocale="en")
    print(f"Language detected: {i18n.getLocale()}")
    
    # Auto-add to startup on first run
    if not isInStartup():
        print("First run detected - adding to system startup...")
        addToStartup()
    
    # Create root window (hidden)
    root = tk.Tk()
    root.withdraw()
    
    # Prevent window from showing in taskbar
    root.overrideredirect(True)
    
    # Create and start manager
    manager = ClipboardManager(root, maxEntries=30)
    
    # Flag to track if we're quitting
    isQuitting = False
    
    # Create system tray
    def onQuit():
        """Handle quit from tray."""
        nonlocal isQuitting
        if isQuitting:
            return
        isQuitting = True
        
        try:
            manager.stop()
            root.quit()
            root.destroy()
        except:
            pass
        finally:
            # Force exit to close terminal
            os._exit(0)
    
    def onShow():
        """Handle show from tray (optional - shows popup)."""
        # Trigger the Win+V popup
        if not isQuitting:
            manager.showPopup()
    assetsPath = resourcePath("assets")
    tray = SystemTray(
        onQuit=onQuit, 
        onShow=onShow, 
        i18n=i18n,
        assetsDir=assetsPath  
    )
    # Start clipboard manager
    manager.start()

    tray.start()
    
    time.sleep(1.5)
    
    # Show notification
    tray.showNotification(
        title=i18n.t('app_name', 'MindfulClipboard'),
        message=i18n.t('tray_started', 'Press Win+V to open clipboard history')
    )
    
    # Handle window close (minimize to tray instead of exit)
    def onClosing():
        root.withdraw()
        return 'break'
    
    root.protocol("WM_DELETE_WINDOW", onClosing)
    
    # Handle Ctrl+C gracefully
    def signalHandler(sig, frame):
        nonlocal isQuitting
        if not isQuitting:
            print("\n Shutting down...")
            onQuit()
    
    signal.signal(signal.SIGINT, signalHandler)
    signal.signal(signal.SIGTERM, signalHandler)
    
    # Run main loop
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    finally:
        if not isQuitting:
            tray.stop()
            manager.stop()
            print(f"\n{i18n.t('shutdown_message')}")
        # Force exit
        os._exit(0)


if __name__ == "__main__":
    main()