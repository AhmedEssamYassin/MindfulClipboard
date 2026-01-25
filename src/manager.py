"""Main clipboard manager orchestrating all components."""
import tkinter as tk
import pyperclip
import keyboard
import winreg
import os
import sys
import time
import subprocess
import atexit
from typing import Union, List
from PIL import Image

from .models import ClipboardEntry
from .history import ClipboardHistory
from .monitor import ClipboardMonitor
from .ui import ClipboardUI
from .utils import copyImageToClipboard
from .i18n import getI18n

# COM imports for folder preservation
try:
    import pythoncom  # Required for threading safety with COM
    from win32com.client import Dispatch
    COM_AVAILABLE = True
except ImportError:
    COM_AVAILABLE = False

class ClipboardManager:
    """Main clipboard manager coordinating all components."""
    
    def __init__(self, root: tk.Tk, maxEntries: int = 30):
        self.root = root
        self.i18n = getI18n()
        
        self.history = ClipboardHistory(maxEntries)
        self.monitor = ClipboardMonitor(self._onClipboardChange)
        self.ui = ClipboardUI(
            root=root,
            onCopyCallback=self._copyAndPasteEntry,
            onPinCallback=self._togglePin,
            onRemoveCallback=self._removeEntry,
            onRefreshCallback=self._refreshDisplay,
            i18n=self.i18n
        )
        
        self.showPopupFlag = False
        self.originalHistoryState = 1
        
        # Ensure we restore settings if the app crashes or closes
        atexit.register(self.stop)

    # --- Event Handlers ---

    def _onClipboardChange(self, content: Union[str, Image.Image], isImage: bool) -> None:
        if self.history.addEntry(content, isImage):
            if self.ui.isOpen():
                self.root.after(50, self._refreshDisplay)
    
    def _copyAndPasteEntry(self, entry: ClipboardEntry) -> None:
        """Copy content and simulate Paste (Ctrl+V)."""
        try:
            if entry.isImage:
                copyImageToClipboard(entry.content)
            else:
                pyperclip.copy(entry.content)
            
            self.ui.closePopup()
            # Slight delay to allow focus to return to target window
            self.root.after(150, lambda: keyboard.send('ctrl+v'))
        except Exception as e:
            print(f"Error copying: {e}")
    
    def _togglePin(self, entry: ClipboardEntry) -> None:
        self.history.togglePin(entry)
        self._refreshDisplay()
    
    def _removeEntry(self, entry: ClipboardEntry) -> None:
        self.history.removeEntry(entry)
        self._refreshDisplay()
    
    def _refreshDisplay(self) -> None:
        if self.ui.isOpen():
            self.ui.refreshDisplay(self.history.filterEntries(self.ui.getSearchQuery()))
    
    def _showHistoryPopup(self) -> None:
        """Calculates position and shows the UI."""
        try:
            x = self.root.winfo_pointerx()
            y = self.root.winfo_pointery()
            self.ui.showPopup(x, y)
            if self.ui.isOpen():
                self._refreshDisplay()
        except Exception as e:
            print(f"Error showing popup: {e}")
            
    def showPopup(self) -> None:
        """Triggered by Hotkey (Thread-safe flag setting)."""
        self.showPopupFlag = True
        # Send a harmless key to ensure modifier keys (like Win) are released
        try:
            keyboard.send('ctrl')
        except:
            pass

    def _checkPopupFlag(self) -> None:
        """Polled by Tkinter main loop to show popup safely."""
        if self.showPopupFlag:
            self.showPopupFlag = False
            self._showHistoryPopup()
        self.root.after(50, self._checkPopupFlag)

    # --- System & Registry Configuration ---

    def _setSystemHistory(self, enable: bool):
        """Enable or Disable the Windows Clipboard History Service via Registry."""
        try:
            keyPath = r"Software\Microsoft\Clipboard"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, keyPath, 0, winreg.KEY_SET_VALUE)
            # 1 = Enable, 0 = Disable
            winreg.SetValueEx(key, "EnableClipboardHistory", 0, winreg.REG_DWORD, 1 if enable else 0)
            winreg.CloseKey(key)
        except Exception:
            pass

    def _getSystemHistoryState(self) -> int:
        """Read current state of Windows Clipboard History."""
        try:
            keyPath = r"Software\Microsoft\Clipboard"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, keyPath, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, "EnableClipboardHistory")
            winreg.CloseKey(key)
            return val
        except:
            return 1

    def _forceSystemReload(self):
        """Force clipboard service to read new Registry settings."""
        try:
            subprocess.run(["taskkill", "/F", "/IM", "cbdhsvc.exe"], 
                         capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        except:
            pass

    # --- Environment Sanitation (Crucial for PyInstaller) ---

    def _getCleanEnv(self):
        """
        Creates a 'clean room' environment for Explorer.
        Removes all PyInstaller variables that cause corruption/DLL conflicts.
        """
        env = os.environ.copy()
        
        # 1. Remove dangerous PyInstaller keys
        dirtyKeys = ['_MEIPASS', '_MEIPASS2', 'PYTHONPATH', 'LD_LIBRARY_PATH']
        for key in dirtyKeys:
            env.pop(key, None)
            
        # 2. Scrub the PATH variable
        # PyInstaller adds its temp folder to PATH. We must strip it out
        # to ensure Explorer loads system DLLs, not our bundled ones.
        if hasattr(sys, '_MEIPASS'):
            temp_path = sys._MEIPASS
            current_path = env.get('PATH', '')
            # Filter out any path segment that matches the temp path
            clean_parts = [p for p in current_path.split(os.pathsep) if temp_path not in p]
            env['PATH'] = os.pathsep.join(clean_parts)
        
        # 3. Ensure SystemRoot is present (Windows needs this)
        if 'SystemRoot' not in env:
            env['SystemRoot'] = r'C:\Windows'
            
        return env

    # --- Explorer & Folder Management ---

    def _getOpenExplorerWindows(self) -> List[str]:
        """Capture all currently open folder paths using COM."""
        paths = []
        if not COM_AVAILABLE:
            return paths
        
        try:
            pythoncom.CoInitialize()
            
            shell = Dispatch("Shell.Application")
            for window in shell.Windows():
                # Detect File Explorer windows (ignore IE/Edge)
                if "File Explorer" in window.FullName or "explorer.exe" in window.FullName.lower():
                    try:
                        path = window.LocationURL
                        if path.startswith("file:///"):
                            # Convert URL to Windows Path
                            path = path.replace("file:///", "").replace("/", "\\")
                            path = path.replace("%20", " ")
                            paths.append(path)
                    except:
                        pass
        except Exception as e:
            print(f"Could not save explorer windows: {e}")
        return paths

    def _restoreExplorerWindows(self, paths: List[str]):
        """Restores folders using the CLEAN environment."""
        if not paths: return
        print(f"[SYSTEM] Restoring {len(paths)} folder(s)...")
        
        cleanEnv = self._getCleanEnv()
        # Explicitly point to the real Explorer executable
        explorerPath = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'explorer.exe')
        
        for path in paths:
            try:
                # Open folder as a detached process with clean environment
                # cwd="C:\" ensures we don't accidentally load DLLs from App dir
                subprocess.Popen([explorerPath, path], env=cleanEnv, cwd="C:\\")
            except:
                pass

    def _modifyNativeHotkey(self, disable: bool) -> None:
        """
        Edits 'DisabledHotkeys' in Registry.
        Restarts Explorer ONLY if a change was actually made.
        """
        keyPath = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        restartNeeded = False
        
        try:
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, keyPath, 0, winreg.KEY_ALL_ACCESS)
            except FileNotFoundError:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, keyPath)

            try:
                currentVal, _ = winreg.QueryValueEx(key, "DisabledHotkeys")
            except FileNotFoundError:
                currentVal = ""

            newVal = currentVal
            if disable:
                # Add 'V' if not present
                if "V" not in currentVal:
                    newVal = currentVal + "V"
                    restartNeeded = True
                    print("[SYSTEM] Disabling Native Win+V in Registry...")
            else:
                # Remove 'V' if present
                if "V" in currentVal:
                    newVal = currentVal.replace("V", "")
                    restartNeeded = True
                    print("[SYSTEM] Restoring Native Win+V in Registry...")

            if restartNeeded:
                winreg.SetValueEx(key, "DisabledHotkeys", 0, winreg.REG_SZ, newVal)
            
            winreg.CloseKey(key)

            if restartNeeded:
                self._restartExplorer()
                
        except Exception as e:
            print(f"[WARNING] Registry access failed: {e}")

    def _restartExplorer(self) -> None:
        """
        Safely restarts Windows Explorer.
        Handles: Saving folders -> Killing -> Cleaning Env -> Starting -> Restoring folders.
        """
        print("[SYSTEM] Restarting Explorer... (Please wait)")
        
        # 1. Save Open Folders
        saved_paths = self._getOpenExplorerWindows()
        
        # 2. Kill Explorer
        subprocess.run(["taskkill", "/f", "/im", "explorer.exe"], 
                       creationflags=subprocess.CREATE_NO_WINDOW)
        time.sleep(1) # Allow process to die
        
        # 3. Start Explorer
        cleanEnv = self._getCleanEnv()
        explorerPath = os.path.join(os.environ.get('SystemRoot', r'C:\Windows'), 'explorer.exe')
        
        # launch explorer with cleaned environment and safe CWD
        subprocess.Popen([explorerPath], env=cleanEnv, cwd="C:\\")
        
        # 4. Wait for Shell to load
        print("[SYSTEM] Waiting for Desktop Shell to reload...")
        time.sleep(4) 
        
        # 5. Restore Folders
        self._restoreExplorerWindows(saved_paths)
        print("[SYSTEM] Desktop Shell Ready.")

    # --- Lifecycle Methods ---

    def start(self) -> None:
        """Initialize the manager, hook hotkeys, and configure system."""
        self.monitor.start()
        
        # 1. Disable Windows Internal History Service
        self.originalHistoryState = self._getSystemHistoryState()
        self._setSystemHistory(False)
        self._forceSystemReload()

        # 2. Disable Native Hotkey via Registry (Might restart explorer)
        self._modifyNativeHotkey(disable=True)

        # 3. Register our Hotkey
        # suppress=False is SAFE now because Windows is ignoring Win+V natively.
        # This keeps other hotkeys starting with `Win` working perfectly.
        try:
            keyboard.add_hotkey('win+v', self.showPopup, suppress=False)
            print("Registered Win+V")
        except Exception as e:
            print(f"Critical: Failed to hook Win+V: {e}")

        self.root.after(100, self._checkPopupFlag)

    def stop(self) -> None:
        """Cleanup, unhook, and restore system defaults."""
        print("[SYSTEM] Stopping Clipboard Manager...")
        self.monitor.stop()
        
        try:
            keyboard.unhook_all()
        except:
            pass
            
        # 1. Restore Native Hotkey (Might restart explorer)
        self._modifyNativeHotkey(disable=False)

        # 2. Restore History Service
        if self.originalHistoryState == 1:
            self._setSystemHistory(True)
            self._forceSystemReload()
            
        # Unregister atexit so it doesn't run twice
        atexit.unregister(self.stop)