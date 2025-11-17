"""Utility functions for clipboard operations."""
import hashlib
import io
import sys
from typing import Union, Optional
from PIL import Image, ImageGrab

# Platform-specific imports
if sys.platform == 'win32':
    import win32clipboard
else:
    # Linux: Use subprocess for xclip
    import subprocess


def calculateHash(content: Union[str, Image.Image]) -> str:
    """Calculate hash of content for duplicate detection."""
    if isinstance(content, str):
        return hashlib.sha256(content.encode()).hexdigest()
    else:  # Image
        imgBytes = io.BytesIO()
        content.save(imgBytes, format='PNG')
        return hashlib.sha256(imgBytes.getvalue()).hexdigest()


def getClipboardImage() -> Optional[Image.Image]:
    """Get image from clipboard if available."""
    try:
        img = ImageGrab.grabclipboard()
        if isinstance(img, Image.Image):
            return img
    except:
        pass
    return None


def copyImageToClipboard(image: Image.Image) -> None:
    """Copy image to system clipboard (cross-platform)."""
    if sys.platform == 'win32':
        _copyImageToClipboardWindows(image)
    else:
        _copyImageToClipboardLinux(image)


def _copyImageToClipboardWindows(image: Image.Image) -> None:
    """Copy image to Windows clipboard."""
    output = io.BytesIO()
    image.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]  # Remove BMP header
    output.close()
    
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()


def _copyImageToClipboardLinux(image: Image.Image) -> None:
    """Copy image to Linux clipboard using xclip."""
    try:
        # Save image to bytes
        output = io.BytesIO()
        image.save(output, format='PNG')
        output.seek(0)
        
        # Use xclip to copy to clipboard
        process = subprocess.Popen(
            ['xclip', '-selection', 'clipboard', '-t', 'image/png'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        process.communicate(input=output.getvalue())
        output.close()
        
        if process.returncode != 0:
            raise Exception("xclip failed")
            
    except FileNotFoundError:
        print("Error: xclip not found. Install with: sudo apt-get install xclip")
        raise
    except Exception as e:
        print(f"Error copying image to clipboard on Linux: {e}")
        raise