"""Utility functions for clipboard operations."""
import hashlib
import io
import sys
from pathlib import Path
from typing import Union, Optional
from PIL import Image, ImageGrab
import win32clipboard

try:
    import winshell
    from win32com.client import Dispatch
    STARTUP_AVAILABLE = True
except ImportError:
    STARTUP_AVAILABLE = False

def calculateHash(content: Union[str, Image.Image]) -> str:
    """Calculate hash of content for duplicate detection."""
    if isinstance(content, str):
        return hashlib.sha256(content.encode()).hexdigest()
    else:
        return hashlib.sha256(content.tobytes()).hexdigest()

def getAppDataDir() -> Path:
    """Get the correct directory for storing user data."""
    import os
    appData = os.getenv('LOCALAPPDATA')
    if not appData:
        appData = os.path.expanduser('~')
    appDir = Path(appData) / "MindfulClipboard"
    appDir.mkdir(parents=True, exist_ok=True)
    return appDir


def getClipboardImage() -> Optional[Image.Image]:
    """Get image from clipboard if available."""
    try:
        img = ImageGrab.grabclipboard()
        if isinstance(img, Image.Image):
            return img
    except Exception as e:
        print(f"Failed to get clipboard image: {e}")
    return None


def copyImageToClipboard(image: Image.Image) -> None:
    """Copy image to Windows clipboard."""
    output = io.BytesIO()
    image.convert("RGB").save(output, "BMP")
    data = output.getvalue()[14:]
    output.close()
    
    win32clipboard.OpenClipboard()
    try:
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    finally:
        win32clipboard.CloseClipboard()

def isInStartup() -> bool:
    """Check if app is in startup folder."""
    if not STARTUP_AVAILABLE: return False
    try:
        startupFolder = Path(winshell.startup())
        return (startupFolder / "MindfulClipboard.lnk").exists()
    except Exception as e:
        print(f"Failed to check startup: {e}")
        return False

def addToStartup() -> bool:
    """Add application to Windows startup."""
    if not STARTUP_AVAILABLE: return False
    try:
        startupFolder = Path(winshell.startup())
        shortcutPath = startupFolder / 'MindfulClipboard.lnk'
        
        # Determine paths based on how we are running (Frozen exe vs Python script)
        if getattr(sys, 'frozen', False):
            target = sys.executable
            args = ""
            cwd = str(Path(sys.executable).parent)
            icon = sys.executable
        else:
            # Running from source
            # Find pythonw.exe to run without console
            pyDir = Path(sys.executable).parent
            pythonw = pyDir / 'pythonw.exe'
            target = str(pythonw if pythonw.exists() else sys.executable)
            
            scriptPath = Path(__file__).parent.parent / 'main.py'
            args = f'"{scriptPath.resolve()}"'
            cwd = str(scriptPath.parent)
            icon = sys.executable

        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(str(shortcutPath))
        shortcut.Targetpath = target
        shortcut.Arguments = args
        shortcut.WorkingDirectory = cwd
        shortcut.IconLocation = icon
        shortcut.WindowStyle = 7  # Minimized
        shortcut.save()
        return True
    except Exception as e:
        print(f"Startup Error: {e}")
        return False

def removeFromStartup() -> bool:
    """Remove application from Windows startup."""
    if not STARTUP_AVAILABLE: return False
    try:
        startupFolder = Path(winshell.startup())
        shortcutPath = startupFolder / "MindfulClipboard.lnk"
        if shortcutPath.exists():
            shortcutPath.unlink()
        return True
    except Exception as e:
        print(f"Failed to remove from startup: {e}")
        return False