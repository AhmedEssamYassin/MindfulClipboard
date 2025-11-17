"""Utility functions for clipboard operations."""
import hashlib
import io
from typing import Union, Optional
from PIL import Image, ImageGrab
import win32clipboard


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
    """Copy image to system clipboard."""
    output = io.BytesIO()
    image.convert('RGB').save(output, 'BMP')
    data = output.getvalue()[14:]  # Remove BMP header
    output.close()
    
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
    win32clipboard.CloseClipboard()