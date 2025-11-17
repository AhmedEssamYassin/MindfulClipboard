"""Main entry point for the Clipboard Manager application."""
import tkinter as tk
import sys
import signal
import os
from pathlib import Path
from src.manager import ClipboardManager
from src.tray import SystemTray
from src.i18n import initI18n

def resourcePath(relativePath):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        basePath = sys._MEIPASS
    except Exception:
        # Not in a PyInstaller bundle, so use the script's directory
        basePath = os.path.abspath(os.path.dirname(__file__))
    
    return os.path.join(basePath, relativePath)

def isInStartup():
    """Check if app is already in startup"""
    try:
        if sys.platform.startswith('win'):
            try:
                import winshell
                startupFolder = Path(winshell.startup())
                return (startupFolder / 'MindfulClipboard.lnk').exists()
            except:
                return False
        elif sys.platform.startswith('linux'):
            autostartDir = Path.home() / '.config' / 'autostart'
            return (autostartDir / 'mindfulclipboard.desktop').exists()
    except:
        return False
    return False

def addToStartup():
    """Automatically add app to system startup"""
    try:
        if sys.platform.startswith('win'):
            try:
                import winshell
                from win32com.client import Dispatch
            except ImportError:
                print("Could not add to startup (missing dependencies)")
                return False
            
            startupFolder = Path(winshell.startup())
            
            # Get executable path
            if getattr(sys, 'frozen', False):
                # Running as compiled executable
                exePath = Path(sys.executable)
                
                # Create shortcut for executable
                shortcutPath = startupFolder / 'MindfulClipboard.lnk'
                shell = Dispatch('WScript.Shell')
                shortcut = shell.CreateShortCut(str(shortcutPath))
                shortcut.Targetpath = str(exePath)
                shortcut.WorkingDirectory = str(exePath.parent)
                shortcut.IconLocation = str(exePath)
                shortcut.WindowStyle = 7  # 7 = Minimized
                shortcut.save()
                
                print(f"Added to Windows startup")
                return True
            else:
                # Running from source - use pythonw.exe to hide console
                pythonwPath = Path(sys.executable).parent / 'pythonw.exe'
                
                # Fall back to python.exe if pythonw.exe doesn't exist
                if not pythonwPath.exists():
                    pythonwPath = Path(sys.executable)
                
                scriptPath = Path(__file__).resolve()  # CHANGED: added .resolve()
                
                # Create shortcut to run Python script
                shortcutPath = startupFolder / 'MindfulClipboard.lnk'
                shell = Dispatch('WScript.Shell')
                shortcut = shell.CreateShortCut(str(shortcutPath))
                shortcut.Targetpath = str(pythonwPath)  # CHANGED: use pythonw
                shortcut.Arguments = f'"{scriptPath}"'
                shortcut.WorkingDirectory = str(scriptPath.parent)
                shortcut.WindowStyle = 7  # Minimized
                shortcut.save()
                
                print(f"Added to Windows startup (using {'pythonw.exe' if pythonwPath.name == 'pythonw.exe' else 'python.exe'})")
                return True
            
        elif sys.platform.startswith('linux'):
            autostartDir = Path.home() / '.config' / 'autostart'
            autostartDir.mkdir(parents=True, exist_ok=True)
            
            # Get executable path
            if getattr(sys, 'frozen', False):
                exePath = Path(sys.executable)
            else:
                scriptPath = Path(__file__).resolve()  # CHANGED: added .resolve()
                exePath = f"python3 {scriptPath}"
            
            # Create .desktop file
            desktopFile = autostartDir / 'mindfulclipboard.desktop'
            iconPath = Path(__file__).parent / 'assets' / 'images' / 'icon.png'
            
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
            
            print(f"Added to Linux autostart")
            return True
            
    except Exception as e:
        print(f"Could not add to startup: {e}")
        return False
    
    return False


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
    tray.start()
    
    # Start clipboard manager
    manager.start()
    
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
            print("\n⚠️  Shutting down...")
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