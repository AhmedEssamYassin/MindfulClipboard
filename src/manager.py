"""Main application controller for MindfulClipboard."""
import os
import sys
import json
import pathlib
import ctypes
import winreg
import keyboard
import threading

from .history import ClipboardHistory
from .monitor import ClipboardMonitor
from .utils import addToStartup, removeFromStartup
from .i18n import initI18n
from .api import ClipboardApi

class ClipboardManager:
    """Main clipboard manager coordinating all components."""
    
    def __init__(self):
        self.i18n = None
        self.history = None
        self.monitor = None
        self.api = None
        self.window = None
        self._isPopupOpen = False
        self.isDarkMode = self._detectSystemTheme()
        self._configPath = self._getConfigPath()
        self._loadConfig()
    
    def _getConfigPath(self):
        from .utils import getAppDataDir
        return getAppDataDir() / "config.json"
    
    def _loadConfig(self):
        try:
            if self._configPath.exists():
                with open(self._configPath, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    self.isDarkMode = config.get("isDarkMode", True)
        except Exception as e:
            print(f"Config load error: {e}")
    
    def _saveConfig(self):
        try:
            config = {}
            if self._configPath.exists():
                with open(self._configPath, "r", encoding="utf-8") as f:
                    config = json.load(f)
            config["isDarkMode"] = self.isDarkMode
            with open(self._configPath, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Config save error: {e}")
    
    def _detectSystemTheme(self):
        try:
            import darkdetect
            return darkdetect.isDark()
        except:
            return True
    
    def setTheme(self, isDark):
        self.isDarkMode = isDark
        self._saveConfig()
    
    def start(self):
        """Initialize the manager, hook hotkeys, and configure system."""
        localesPath = self._getLocalesPath()
        self.i18n = initI18n(localesDir=localesPath, defaultLocale="en")
        print(f"Language: {self.i18n.getLocale()}")
        
        self.history = ClipboardHistory(maxEntries=30)
        self.monitor = ClipboardMonitor(self._onClipboardChange)
        
        self.api = ClipboardApi(self)
        self.originalHistoryState = self._getSystemHistoryState()
        
        self.monitor.start()
        self._startFocusTracker()
        
        # Disable native clipboard
        self._setSystemHistory(False)
        self._modifyNativeHotkey(disable=True)
        
        if not self._isInStartup():
            print("Adding to startup...")
            addToStartup()
        
        self._registerHotkey()
    
    def _setSystemHistory(self, enable):
        """Enable or Disable the Windows Clipboard History Service via Registry."""
        try:
            keyPath = r"Software\Microsoft\Clipboard"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, keyPath, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "EnableClipboardHistory", 0, winreg.REG_DWORD, 1 if enable else 0)
            winreg.CloseKey(key)
        except:
            pass

    def _getSystemHistoryState(self):
        """Read current state of Windows Clipboard History."""
        try:
            keyPath = r"Software\Microsoft\Clipboard"
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, keyPath, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, "EnableClipboardHistory")
            winreg.CloseKey(key)
            return val
        except:
            return 1

    def _modifyNativeHotkey(self, disable):
        """Edits 'DisabledHotkeys' in Registry."""
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
                if "V" not in currentVal:
                    newVal = currentVal + "V"
                    changeMade = True
            else:
                if "V" in currentVal:
                    newVal = currentVal.replace("V", "")
                    changeMade = True

            if changeMade:
                winreg.SetValueEx(key, "DisabledHotkeys", 0, winreg.REG_SZ, newVal)
                action = "disabled" if disable else "restored"
                ctypes.windll.user32.MessageBoxW(
                    0, 
                    f"The native Windows 'Win+V' hotkey has been {action} in the Registry.\n\nFor this change to take full effect, you must manually restart Windows Explorer (Task Manager > Restart Explorer) or Sign Out/In.", 
                    "System Restart Required", 
                    0x40 | 0x40000 # MB_ICONINFORMATION | MB_TOPMOST
                )
            winreg.CloseKey(key)
        except Exception as e:
            print(f"[WARNING] Registry access failed: {e}")
            
    def _getLocalesPath(self):
        if getattr(sys, 'frozen', False):
            basePath = sys._MEIPASS
        else:
            basePath = os.path.abspath(os.path.dirname(__file__)).rsplit(os.sep, 1)[0]
        return os.path.join(basePath, "locales")
    
    def _startFocusTracker(self):
        """Poll global mouse state. If the user clicks anywhere outside the 
        popup window's bounding box, close the popup. This completely bypasses OS focus rules."""
        import threading
        import time
        import ctypes
        
        self._isPopupOpen = False
        self._showGraceUntil = 0
        
        VK_LBUTTON = 0x01
        VK_RBUTTON = 0x02
        
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
            
        def track():
            while True:
                time.sleep(0.02) # 20ms polling is fast enough to catch clicks, low CPU overhead
                if getattr(self, '_isPopupOpen', False) and self.window and time.time() > self._showGraceUntil:
                    l_state = ctypes.windll.user32.GetAsyncKeyState(VK_LBUTTON)
                    r_state = ctypes.windll.user32.GetAsyncKeyState(VK_RBUTTON)
                    
                    # 0x8000 checks if the button is currently held down
                    if (l_state & 0x8000) or (r_state & 0x8000):
                        pt = POINT()
                        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
                        
                        if hasattr(self, '_popupRect'):
                            rect = self._popupRect
                            # Check if click is inside the popup's known screen coordinates
                            if not (rect['x'] <= pt.x <= rect['x'] + 420 and rect['y'] <= pt.y <= rect['y'] + 540):
                                self.closePopupWeb()
                                # Add a tiny delay so we don't trigger multiple closes for a long click
                                time.sleep(0.2)
                                
        t = threading.Thread(target=track, daemon=True)
        t.start()
    
    def _isInStartup(self):
        from .utils import isInStartup
        return isInStartup()
    
    def _onClipboardChange(self, content, isImage):
        if self.history.addEntry(content, isImage):
            if self.window:
                self._refreshFrontend()
    
    def _refreshFrontend(self):
        if self.window:
            try:
                self.window.evaluate_js("refreshData()")
            except:
                pass
    
    def _registerHotkey(self):
        try:
            keyboard.add_hotkey("win+v", self.showPopup, suppress=False)
            print("Registered Win+V")
        except Exception as e:
            print(f"Hotkey error: {e}")
    
    def showPopup(self):
        """Toggle the popup: if already open, close it."""
        import time
        
        if not self.window:
            return
        
        # Toggle behavior: if already open, just close
        if self._isPopupOpen:
            self.closePopupWeb()
            return
        
        # Release modifier keys (Win key) before showing
        # The OS sometimes holds the Win key logically, which prevents our window from getting focus
        try:
            keyboard.send('ctrl')
        except:
            pass
            
        # Debounce: ignore rapid-fire calls within 300ms (keyboard lib can double-fire because of the synthetic 'ctrl' press)
        now = time.time()
        if now - getattr(self, '_lastShowTime', 0) < 0.3:
            return
        self._lastShowTime = now
        
        class POINT(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
        pt = POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        
        x = pt.x + 15
        y = pt.y + 15
        
        screenWidth = ctypes.windll.user32.GetSystemMetrics(0)
        screenHeight = ctypes.windll.user32.GetSystemMetrics(1)
        
        if x + 420 > screenWidth:
            x = screenWidth - 420
        if y + 540 > screenHeight:
            y = screenHeight - 540
        
        self.window.move(x, y)
        self.window.show()
        self._isPopupOpen = True
        self._popupRect = {'x': x, 'y': y}
        
        # Give user 0.3 seconds before the click tracker starts listening
        self._showGraceUntil = time.time() + 0.3
        
        self.window.evaluate_js("refreshData()")
    
    def closePopupWeb(self):
        if self.window:
            self._isPopupOpen = False
            self.window.hide()
    
    def stop(self):
        """Cleanup, unhook, and restore system defaults."""
        self.monitor.stop()
        try:
            keyboard.unhook_all()
        except:
            pass
        self._modifyNativeHotkey(disable=False)
        if hasattr(self, 'originalHistoryState') and self.originalHistoryState == 1:
            self._setSystemHistory(True)
