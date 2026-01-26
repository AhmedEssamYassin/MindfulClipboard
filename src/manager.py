"""Main clipboard manager orchestrating all components."""
import tkinter as tk
from tkinter import messagebox
import pyperclip
import keyboard
import winreg
import atexit
from typing import Union
from PIL import Image

from .models import ClipboardEntry
from .history import ClipboardHistory
from .monitor import ClipboardMonitor
from .ui import ClipboardUI
from .utils import copyImageToClipboard, addToStartup, removeFromStartup
from .i18n import getI18n

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

    def _modifyNativeHotkey(self, disable: bool) -> None:
        """
        Edits 'DisabledHotkeys' in Registry.
        Shows a popup to the user if a change was made, requesting a restart.
        """
        keyPath = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
        changeMade = False
        
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
                    changeMade = True
                    print("[SYSTEM] Disabling Native Win+V in Registry...")
            else:
                # Remove 'V' if present
                if "V" in currentVal:
                    newVal = currentVal.replace("V", "")
                    changeMade = True
                    print("[SYSTEM] Restoring Native Win+V in Registry...")

            if changeMade:
                winreg.SetValueEx(key, "DisabledHotkeys", 0, winreg.REG_SZ, newVal)
                
                # Show Prompt
                action = "disabled" if disable else "restored"
                messagebox.showinfo(
                    "System Restart Required",
                    f"The native Windows 'Win+V' hotkey has been {action} in the Registry.\n\n"
                    "For this change to take full effect, you must manually restart "
                    "Windows Explorer (Task Manager > Restart Explorer) or Sign Out/In."
                )
            
            winreg.CloseKey(key)

        except Exception as e:
            print(f"[WARNING] Registry access failed: {e}")

    # --- Lifecycle Methods ---

    def start(self) -> None:
        """Initialize the manager, hook hotkeys, and configure system."""
        self.monitor.start()
        
        # 1. Disable Windows Internal History Service
        self.originalHistoryState = self._getSystemHistoryState()
        self._setSystemHistory(False)

        # 2. Disable Native Hotkey via Registry (Prompts user if changed)
        self._modifyNativeHotkey(disable=True)

        # 3. Register our Hotkey
        # suppress=False: We let the event pass through.
        # Once the user reboots, Windows will ignore it (due to Registry),
        # but our app will still catch it.
        try:
            keyboard.add_hotkey('win+v', self.showPopup, suppress=False)
            print("Registered Win+V")
        except Exception as e:
            print(f"Critical: Failed to hook Win+V: {e}")

        addToStartup()

        self.root.after(100, self._checkPopupFlag)

    def stop(self) -> None:
        """Cleanup, unhook, and restore system defaults."""
        print("[SYSTEM] Stopping Clipboard Manager...")
        self.monitor.stop()
        
        try:
            keyboard.unhook_all()
        except:
            pass
            
        # 1. Restore Native Hotkey (Prompts user if changed)
        self._modifyNativeHotkey(disable=False)

        # 2. Restore History Service
        if self.originalHistoryState == 1:
            self._setSystemHistory(True)
        # 3. Turning off startup open
        removeFromStartup()
        # Unregister atexit so it doesn't run twice
        atexit.unregister(self.stop)