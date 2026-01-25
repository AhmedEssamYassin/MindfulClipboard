"""Main clipboard manager orchestrating all components."""
import tkinter as tk
import pyperclip
import keyboard
import os
from typing import Union
from PIL import Image

from .models import ClipboardEntry
from .history import ClipboardHistory
from .monitor import ClipboardMonitor
from .ui import ClipboardUI
from .utils import copyImageToClipboard
from .i18n import getI18n


class ClipboardManager:
    """Main clipboard manager coordinating all components."""
    
    def __init__(self, root: tk.Tk, maxEntries: int = 30):
        self.root = root
        self.i18n = getI18n()
        
        # Initialize components
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
    
    def _onClipboardChange(self, content: Union[str, Image.Image], isImage: bool) -> None:
        """Handle clipboard content change."""
        if self.history.addEntry(content, isImage):
            # Update display if popup is open
            if self.ui.isOpen():
                self.root.after(50, self._refreshDisplay)
    
    def _copyAndPasteEntry(self, entry: ClipboardEntry) -> None:
        """Copy entry to clipboard and paste it."""
        try:
            if entry.isImage:
                copyImageToClipboard(entry.content)
            else:
                pyperclip.copy(entry.content)
            
            self.ui.closePopup()
            self.root.after(100, lambda: keyboard.send('ctrl+v'))
        except Exception as e:
            print(f"Error copying to clipboard: {e}")
    
    def _togglePin(self, entry: ClipboardEntry) -> None:
        """Toggle pin status of an entry."""
        self.history.togglePin(entry)
        self._refreshDisplay()
    
    def _removeEntry(self, entry: ClipboardEntry) -> None:
        """Remove an entry from history."""
        self.history.removeEntry(entry)
        self._refreshDisplay()
    
    def _refreshDisplay(self) -> None:
        """Refresh the UI display."""
        if not self.ui.isOpen():
            return
        
        searchQuery = self.ui.getSearchQuery()
        entries = self.history.filterEntries(searchQuery)
        self.ui.refreshDisplay(entries)
    
    def _showHistoryPopup(self) -> None:
        """Show history popup at cursor position."""
        x = self.root.winfo_pointerx()
        y = self.root.winfo_pointery()
        
        self.ui.showPopup(x, y)
        
        # Initial display
        if self.ui.isOpen():
            self._refreshDisplay()
    
    def showPopup(self) -> None:
        """Flag to show history popup (called from hotkey thread)."""
        self.showPopupFlag = True
    
    def _checkPopupFlag(self) -> None:
        """Check if popup should be shown."""
        if self.showPopupFlag:
            self.showPopupFlag = False
            self._showHistoryPopup()
        self.root.after(100, self._checkPopupFlag)

    def _pass_through(self, hotkey: str) -> None:
        """
        Safely pass a hotkey to the OS.
        1. Unhook it (so we don't trigger ourselves).
        2. Send it.
        3. Re-hook it (to fix the 'typing' issue).
        """
        try:
            keyboard.remove_hotkey(hotkey)
            keyboard.send(hotkey)
            keyboard.add_hotkey(hotkey, lambda: self._pass_through(hotkey), suppress=True)
        except Exception as e:
            print(f"Error passing through {hotkey}: {e}")
            try:
                keyboard.add_hotkey(hotkey, lambda: self._pass_through(hotkey), suppress=True)
            except:
                pass

    def start(self) -> None:
        """Start the clipboard manager."""
        # Start monitoring
        self.monitor.start()
        
        # --- 1. Register 3-Key Shortcuts first ---
        # We use _pass_through for these to ensure the OS receives the clean event
        # without the physical keys leaking.
        
        # Register both orders to catch however the user presses it
        try:
            keyboard.add_hotkey('win+shift+s', lambda: self._pass_through('win+shift+s'), suppress=True)
            keyboard.add_hotkey('shift+win+s', lambda: self._pass_through('win+shift+s'), suppress=True)
        except Exception as e:
            print(f"Error registering Win+Shift+S: {e}")

        # --- 2. Register Common Shortcuts (Pass-through) ---
        common_hotkeys = [
            'win+d',    # Desktop
            'win+r',    # Run
            'win+tab',  # Task View
            'win+i',    # Settings
            'win+x',    # Quick Link Menu
            'win+a',    # Action Center
            'win+e'     # Explorer
        ]
        
        for key in common_hotkeys:
            keyboard.add_hotkey(key, lambda k=key: self._pass_through(k), suppress=True)

        # --- 3. Register Win+V last ---
        # This acts as the "catch-all" for the Win key suppression.
        try:
            keyboard.add_hotkey('win+v', self.showPopup, suppress=True)
        except Exception as e:
            print(f"Error registering Win+V: {e}")

        
        self.root.after(100, self._checkPopupFlag)
        
        print(self.i18n.t('startup_message'))
        print(self.i18n.t('hotkey_message'))
        print(self.i18n.t('override_message'))

    def stop(self) -> None:
        """Stop the clipboard manager."""
        self.monitor.stop()
        
        # Remove all hotkeys to restore Windows default behavior
        keyboard.unhook_all()
        
        print(self.i18n.t('shutdown_message'))