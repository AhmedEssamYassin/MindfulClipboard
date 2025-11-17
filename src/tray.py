"""System tray icon for MindfulClipboard."""
import sys
from pathlib import Path
from typing import Callable, Optional
from PIL import Image
import pystray
from pystray import MenuItem as item

# Platform-specific imports
IS_WINDOWS = sys.platform.startswith('win')
IS_LINUX = sys.platform.startswith('linux')

if IS_WINDOWS:
    try:
        import winshell
        from win32com.client import Dispatch
        WINDOWS_STARTUP_AVAILABLE = True
    except ImportError:
        WINDOWS_STARTUP_AVAILABLE = False
        print("[WARNING] winshell or win32com not available - startup feature disabled")


class SystemTray:
    """Manages the system tray icon and menu."""
    
    def __init__(self, onQuit: Callable, onShow: Optional[Callable] = None, i18n=None, assetsDir: str = "assets"):
        self.onQuit = onQuit
        self.onShow = onShow
        self.i18n = i18n
        self.assetsDir = Path(assetsDir)
        self.icon: Optional[pystray.Icon] = None
        self._running = False
    
    def _getIcon(self) -> Image.Image:
        """Load the tray icon image."""
        # Try to load from assets
        iconPaths = [
            self.assetsDir / 'images' / 'icon.png',
            self.assetsDir / 'images' / 'tray_icon.png',
        ]
        
        for iconPath in iconPaths:
            if iconPath.exists():
                return Image.open(iconPath)
        
        # Create a simple default icon if no image found
        return self._createDefaultIcon()
    
    def _createDefaultIcon(self) -> Image.Image:
        """Create a simple default icon."""
        from PIL import ImageDraw
        
        # Create 64x64 icon with clipboard symbol
        img = Image.new('RGB', (64, 64), color='#2196F3')
        draw = ImageDraw.Draw(img)
        
        # Draw simple clipboard shape
        draw.rectangle([16, 12, 48, 52], fill='white', outline='#1976D2', width=2)
        draw.rectangle([24, 8, 40, 16], fill='#1976D2')
        
        return img
    
    def _isInStartup(self) -> bool:
        """Check if app is in startup"""
        try:
            if IS_WINDOWS:
                if not WINDOWS_STARTUP_AVAILABLE:
                    return False
                try:
                    startupFolder = Path(winshell.startup())
                    return (startupFolder / 'MindfulClipboard.lnk').exists()
                except:
                    return False
            elif IS_LINUX:
                autostartDir = Path.home() / '.config' / 'autostart'
                return (autostartDir / 'mindfulclipboard.desktop').exists()
        except:
            return False
        return False
    
    def _toggleStartup(self, icon, item):
        """Toggle auto-start on/off"""
        if self._isInStartup():
            self._removeFromStartup()
        else:
            self._addToStartup()
        
        # Recreate menu to update checkbox
        self.icon.menu = self._createMenu()
    
    def _addToStartup(self):
        """Add to startup"""
        try:
            if IS_WINDOWS:
                if not WINDOWS_STARTUP_AVAILABLE:
                    self.showNotification("Error", "Missing dependencies: pip install pywin32 winshell")
                    return
                
                startupFolder = Path(winshell.startup())
                
                if getattr(sys, 'frozen', False):
                    # Running as compiled executable
                    exePath = Path(sys.executable)
                    
                    shortcutPath = startupFolder / 'MindfulClipboard.lnk'
                    shell = Dispatch('WScript.Shell')
                    shortcut = shell.CreateShortCut(str(shortcutPath))
                    shortcut.Targetpath = str(exePath)
                    shortcut.WorkingDirectory = str(exePath.parent)
                    shortcut.IconLocation = str(exePath)
                    shortcut.WindowStyle = 7  # Minimized
                    shortcut.save()
                    
                    self.showNotification("Auto-Start", "Enabled for system startup")
                    return
                else:
                    # Running from source - use pythonw.exe to hide console
                    pythonwPath = Path(sys.executable).parent / 'pythonw.exe'
                    
                    # Fall back to python.exe if pythonw.exe doesn't exist
                    if not pythonwPath.exists():
                        pythonwPath = Path(sys.executable)
                    
                    scriptPath = Path(__file__).parent.parent / 'main.py'
                    scriptPath = scriptPath.resolve()
                    
                    shortcutPath = startupFolder / 'MindfulClipboard.lnk'
                    shell = Dispatch('WScript.Shell')
                    shortcut = shell.CreateShortCut(str(shortcutPath))
                    shortcut.Targetpath = str(pythonwPath)
                    shortcut.Arguments = f'"{scriptPath}"'
                    shortcut.WorkingDirectory = str(scriptPath.parent)
                    shortcut.WindowStyle = 7
                    shortcut.save()
                    
                    self.showNotification("Auto-Start", "Enabled for system startup")
            
            elif IS_LINUX:
                autostartDir = Path.home() / '.config' / 'autostart'
                autostartDir.mkdir(parents=True, exist_ok=True)
                
                if getattr(sys, 'frozen', False):
                    exePath = Path(sys.executable)
                else:
                    scriptPath = Path(__file__).parent.parent / 'main.py'
                    exePath = f"python3 {scriptPath}"
                
                desktopFile = autostartDir / 'mindfulclipboard.desktop'
                iconPath = Path(__file__).parent.parent / 'assets' / 'images' / 'icon.png'
                
                content = f"""[Desktop Entry]
Type=Application
Name=MindfulClipboard
Comment=Smart Clipboard Manager
Exec={exePath}
Icon={iconPath if iconPath.exists() else ''}
Terminal=false
Categories=Utility;
X-GNOME-Autostart-enabled=true
StartupNotify=false
"""
                
                desktopFile.write_text(content)
                desktopFile.chmod(0o755)
                
                self.showNotification("Auto-Start", "Enabled for system startup")
                
        except Exception as e:
            self.showNotification("Error", f"Could not enable auto-start: {e}")
    
    def _removeFromStartup(self):
        """Remove from startup"""
        try:
            if IS_WINDOWS:
                if not WINDOWS_STARTUP_AVAILABLE:
                    self.showNotification("Error", "Missing dependencies for startup feature")
                    return
                    
                startupFolder = Path(winshell.startup())
                shortcutPath = startupFolder / 'MindfulClipboard.lnk'
                
                if shortcutPath.exists():
                    shortcutPath.unlink()
                    self.showNotification("Auto-Start", "Disabled from system startup")
                    
            elif IS_LINUX:
                autostartDir = Path.home() / '.config' / 'autostart'
                desktopFile = autostartDir / 'mindfulclipboard.desktop'
                
                if desktopFile.exists():
                    desktopFile.unlink()
                    self.showNotification("Auto-Start", "Disabled from system startup")
                    
        except Exception as e:
            self.showNotification("Error", f"Could not disable auto-start: {e}")
    
    def _createMenu(self) -> tuple:
        """Create the tray menu."""
        menuItems = []
        
        # Show window option (if callback provided)
        if self.onShow:
            showText = self.i18n.t('tray_show') if self.i18n else 'Open Clipboard'
            menuItems.append(item(showText, self._onShowClick))
            menuItems.append(pystray.Menu.SEPARATOR)
        
        # Auto-start toggle (only show if supported)
        if IS_WINDOWS or IS_LINUX:
            startupText = self.i18n.t('tray_autostart') if self.i18n else 'Run on Startup'
            menuItems.append(item(
                startupText,
                self._toggleStartup,
                checked=lambda item: self._isInStartup()
            ))
            menuItems.append(pystray.Menu.SEPARATOR)
        
        # About option
        aboutText = self.i18n.t('tray_about') if self.i18n else 'About'
        menuItems.append(item(aboutText, self._onAbout))
        
        # Quit option
        quitText = self.i18n.t('tray_quit') if self.i18n else 'Quit'
        menuItems.append(item(quitText, self._onQuitClick))
        
        return tuple(menuItems)
    
    def _onShowClick(self, icon, item):
        """Handle show window click."""
        if self.onShow:
            self.onShow()
    
    def _onAbout(self, icon, item):
        """Handle about click."""
        import tkinter as tk
        from tkinter import messagebox
        
        # Create a hidden root window if needed
        try:
            root = tk.Tk()
            root.withdraw()
            
            # Platform-specific hotkey text
            hotkey = "Win+V" if IS_WINDOWS else "Super+V"
            
            messagebox.showinfo(
                "MindfulClipboard",
                f"Smart Clipboard Manager\n\nPress {hotkey} to open clipboard history\n\nVersion 1.0"
            )
            root.destroy()
        except Exception as e:
            # Fallback to notification if messagebox fails
            hotkey = "Win+V" if IS_WINDOWS else "Super+V"
            self.showNotification(
                "MindfulClipboard",
                f"Smart Clipboard Manager\nPress {hotkey} to open clipboard history"
            )
    
    def _onQuitClick(self, icon, item):
        """Handle quit click."""
        # Stop icon first to prevent further menu interactions
        if self.icon:
            self.icon.visible = False
        
        # Schedule quit callback after a short delay to allow menu to close
        import threading
        def delayedQuit():
            self.stop()
            if self.onQuit:
                self.onQuit()
        
        threading.Timer(0.1, delayedQuit).start()
    
    def start(self) -> None:
        """Start the system tray icon."""
        if self._running:
            return
        
        self._running = True
        
        # Create icon
        iconImage = self._getIcon()
        title = self.i18n.t('app_name') if self.i18n else 'MindfulClipboard'
        menu = self._createMenu()
        
        self.icon = pystray.Icon(
            name='MindfulClipboard',
            icon=iconImage,
            title=title,
            menu=menu
        )
        
        # Run in separate thread
        self.icon.run_detached()
        
        print("[OK] System tray icon started")
    
    def stop(self) -> None:
        """Stop the system tray icon."""
        if self.icon and self._running:
            self._running = False
            try:
                self.icon.visible = False
                self.icon.stop()
                print("[STOP] System tray icon stopped")
            except Exception as e:
                print(f"[WARNING] Error stopping tray icon: {e}")
    
    def updateTitle(self, title: str) -> None:
        """Update the tray icon title."""
        if self.icon:
            self.icon.title = title
    
    def showNotification(self, title: str, message: str) -> None:
        """Show a system notification."""
        if self.icon:
            try:
                self.icon.notify(title=title, message=message)
            except Exception as e:
                print(f"[WARNING] Failed to show notification: {e}")