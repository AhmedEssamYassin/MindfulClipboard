"""User interface components for clipboard manager."""
import sys
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from typing import Callable, Optional, List

from .models import ClipboardEntry


class ClipboardUI:
    """Manages the clipboard history popup UI."""
    
    def __init__(self, root: tk.Tk, onCopyCallback: Callable, onPinCallback: Callable, 
                 onRemoveCallback: Callable, onRefreshCallback: Callable, i18n):
        self.root = root
        self.i18n = i18n
        self.onCopy = onCopyCallback
        self.onPin = onPinCallback
        self.onRemove = onRemoveCallback
        self.onRefresh = onRefreshCallback
        
        self.popupWindow: Optional[tk.Toplevel] = None
        self.hoverPreview: Optional[tk.Toplevel] = None
        self.searchVar: Optional[tk.StringVar] = None
        self.searchEntry: Optional[tk.Entry] = None
        self.searchTraceId: Optional[str] = None
        self.canvas: Optional[tk.Canvas] = None
        self.scrollableFrame: Optional[tk.Frame] = None
        
        # Theme settings
        self.isDarkMode = self._detectSystemTheme()
        
        # Keyboard navigation
        self.currentEntries: List[ClipboardEntry] = []
        self.selectedIndex: int = 0
        self.itemFrames: List[tk.Frame] = []
    
    def _detectSystemTheme(self) -> bool:
        """Detect system theme (dark/light)."""
        try:
            import darkdetect
            return darkdetect.isDark()
        except:
            # Fallback to light mode if detection fails
            return False
    
    def toggleTheme(self):
        """Toggle between light and dark mode."""
        self.isDarkMode = not self.isDarkMode
        if self.isOpen():
            # Capture current position
            x = self.popupWindow.winfo_x()
            y = self.popupWindow.winfo_y()
            
            # Re-create window to apply theme to structural frames (borders, title, etc.)
            self.showPopup(x, y)
            
            # Refresh the content list
            self.onRefresh()
    
    def getTheme(self):
        """Get current theme colors."""
        if self.isDarkMode:
            return {
                'bg': '#1E1E1E',
                'fg': '#FFFFFF',
                'accent': '#0D47A1',
                'hover': '#2D2D2D',
                'border': '#0D47A1',
                'search_bg': '#2D2D2D',
                'search_fg': '#FFFFFF',
                'title_bg': '#0D47A1',
                'title_fg': '#FFFFFF',
                'selected': '#0D47A1',
                'tooltip_bg': '#424242',
                'tooltip_fg': '#FFFFFF',
                'btn_hover': '#3E3E3E',       # Slightly lighter than row hover
                'btn_danger': '#B71C1C'       # Dark Red for remove
            }
        else:
            return {
                'bg': '#FFFFFF',
                'fg': '#000000',
                'accent': '#2196F3',
                'hover': '#E3F2FD',
                'border': '#2196F3',
                'search_bg': '#F5F5F5',
                'search_fg': '#000000',
                'title_bg': '#2196F3',
                'title_fg': '#FFFFFF',
                'selected': '#BBDEFB',
                'tooltip_bg': '#333333',
                'tooltip_fg': '#FFFFFF',
                'btn_hover': '#BBDEFB',       # Distinct Blueish
                'btn_danger': '#FFEBEE'       # Light Red
            }
    
    def showPopup(self, x: int, y: int) -> None:
        """Show history popup at specified coordinates."""
        if self.popupWindow:
            self.popupWindow.destroy()
            self.popupWindow = None
        
        theme = self.getTheme()
        
        # Popup dimensions
        popup_width = 360
        popup_height = 450
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Adjust x position to prevent horizontal overflow
        if x + popup_width > screen_width:
            x = screen_width - popup_width - 10
        if x < 0:
            x = 10
        
        # Adjust y position to prevent vertical overflow
        if y + popup_height > screen_height:
            y = screen_height - popup_height - 10
        if y < 0:
            y = 10
        
        # Create popup
        self.popupWindow = tk.Toplevel(self.root)
        self.popupWindow.title(self.i18n.t('window_title'))
        self.popupWindow.attributes('-topmost', True)
        self.popupWindow.overrideredirect(True)
        self.popupWindow.geometry(f"{popup_width}x{popup_height}+{x}+{y}")
        
        # Set window background to match theme
        self.popupWindow.configure(bg=theme['bg'])
        
        # Add border
        outerFrame = tk.Frame(self.popupWindow, bg=theme['border'], relief='flat', borderwidth=1)
        outerFrame.pack(fill='both', expand=True)
        
        # Create inner frame with theme background
        innerFrame = tk.Frame(outerFrame, bg=theme['bg'])
        innerFrame.pack(fill='both', expand=True, padx=1, pady=1)
        
        # Title bar
        self._createTitleBar(innerFrame)
        
        # Search bar
        self._createSearchBar(innerFrame)
        
        # Create frame with scrollbar
        self._createScrollableArea(innerFrame)
        
        # Keyboard navigation bindings
        self.popupWindow.bind('<Up>', self._navigateUp)
        self.popupWindow.bind('<Down>', self._navigateDown)
        self.popupWindow.bind('<Return>', self._selectCurrentEntry)
        self.popupWindow.bind('<space>', self._selectCurrentEntry)
        self.popupWindow.bind('<Delete>', self._deleteCurrentEntry)
        self.popupWindow.bind('<p>', self._pinCurrentEntry)
        
        # Bind events
        self.popupWindow.bind('<Escape>', lambda e: self.closePopup())
        self.popupWindow.bind('<FocusOut>', self._onFocusOut)

        # --- FOCUS HANDLING ---
        # Update window to ensure it's fully created
        self.popupWindow.update_idletasks()
        
        # Windows-specific: Force foreground window
        if sys.platform == 'win32':
            try:
                import ctypes
                # Get the window handle (HWND)
                hwnd = ctypes.windll.user32.GetParent(self.popupWindow.winfo_id())
                if hwnd == 0:
                    hwnd = self.popupWindow.winfo_id()
                
                # Attach to foreground thread if needed
                foreground_hwnd = ctypes.windll.user32.GetForegroundWindow()
                if foreground_hwnd != hwnd:
                    foreground_thread = ctypes.windll.user32.GetWindowThreadProcessId(foreground_hwnd, None)
                    current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
                    ctypes.windll.user32.AttachThreadInput(foreground_thread, current_thread, True)
                    ctypes.windll.user32.SetForegroundWindow(hwnd)
                    ctypes.windll.user32.AttachThreadInput(foreground_thread, current_thread, False)
            except Exception:
                pass
        
        # Lift window and grab input
        self.popupWindow.lift()
        self.popupWindow.attributes('-topmost', True)
        
        # Delayed focus to ensure window is ready
        def setFocus():
            try:
                self.popupWindow.grab_set()
                if self.searchEntry and self.searchEntry.winfo_exists():
                    self.searchEntry.focus_force()
            except:
                pass
        
        self.root.after(50, setFocus)
        
        # Ensure popup stays on top and binds outside click
        self.root.after(100, self._bindOutsideClick)
    
    def _onFocusOut(self, event):
        """Handle focus out event."""
        # Get the widget that currently has focus
        focused_widget = self.popupWindow.focus_get()
        
        # If focus is still within the popup window (or its children), ignore the event
        if focused_widget and str(focused_widget).startswith(str(self.popupWindow)):
            return
            
        # Otherwise, close the popup
        self.closePopup()
        
    def _navigateUp(self, event=None):
        """Navigate to previous entry."""
        if self.selectedIndex > 0:
            self.selectedIndex -= 1
            self._updateSelection()
            self._scrollToSelected()
    
    def _navigateDown(self, event=None):
        """Navigate to next entry."""
        if self.selectedIndex < len(self.currentEntries) - 1:
            self.selectedIndex += 1
            self._updateSelection()
            self._scrollToSelected()
    
    def _selectCurrentEntry(self, event=None):
        """Select (copy and paste) the current entry."""
        if 0 <= self.selectedIndex < len(self.currentEntries):
            entry = self.currentEntries[self.selectedIndex]
            self.onCopy(entry)
    
    def _deleteCurrentEntry(self, event=None):
        """Delete the current entry."""
        if 0 <= self.selectedIndex < len(self.currentEntries):
            entry = self.currentEntries[self.selectedIndex]
            self.onRemove(entry)
    
    def _pinCurrentEntry(self, event=None):
        """Pin/unpin the current entry."""
        if 0 <= self.selectedIndex < len(self.currentEntries):
            entry = self.currentEntries[self.selectedIndex]
            self.onPin(entry)
    
    def _updateSelection(self):
        """Update visual selection of entries."""
        theme = self.getTheme()
        
        for idx, frame in enumerate(self.itemFrames):
            if idx == self.selectedIndex:
                # Highlight selected
                self._highlightFrame(frame, theme['selected'])
            else:
                # Reset to default
                self._highlightFrame(frame, theme['bg'])
    
    def _highlightFrame(self, frame, color):
        """Apply highlight color to frame and its children."""
        try:
            frame.config(bg=color)
            for child in frame.winfo_children():
                self._highlightWidget(child, color)
        except:
            pass
    
    def _highlightWidget(self, widget, color):
        """Recursively highlight widget and children."""
        try:
            if isinstance(widget, (tk.Frame, tk.Label, tk.Button)):
                widget.config(bg=color)
            for child in widget.winfo_children():
                self._highlightWidget(child, color)
        except:
            pass
    
    def _scrollToSelected(self):
        """Scroll canvas to show selected item."""
        if not self.canvas or not self.itemFrames:
            return
        
        if 0 <= self.selectedIndex < len(self.itemFrames):
            frame = self.itemFrames[self.selectedIndex]
            try:
                # Get frame position relative to canvas
                frame.update_idletasks()
                y = frame.winfo_y()
                h = frame.winfo_height()
                
                # Get canvas viewport
                canvas_height = self.canvas.winfo_height()
                
                # Calculate scroll position
                total_height = self.scrollableFrame.winfo_height()
                if total_height > 0:
                    # Scroll to center the selected item
                    scroll_pos = (y + h/2 - canvas_height/2) / total_height
                    scroll_pos = max(0, min(1, scroll_pos))
                    self.canvas.yview_moveto(scroll_pos)
            except:
                pass
    
    def _createTitleBar(self, parent: tk.Frame) -> None:
        """Create the title bar."""
        theme = self.getTheme()
        
        titleFrame = tk.Frame(parent, bg=theme['title_bg'], height=35)
        titleFrame.pack(fill='x')
        titleFrame.pack_propagate(False)
        
        titleLabel = tk.Label(titleFrame, text=f"📋 {self.i18n.t('window_title')}", 
                               bg=theme['title_bg'], fg=theme['title_fg'], font=('Arial', 11, 'bold'))
        titleLabel.pack(side='left', padx=10, pady=5)
        
        # Theme toggle button
        themeIcon = "🌙" if not self.isDarkMode else "☀️"
        themeBtn = tk.Button(titleFrame, text=themeIcon, 
                            bg=theme['title_bg'], fg=theme['title_fg'],
                            relief='flat', font=('Arial', 12),
                            cursor='hand2', borderwidth=0,
                            command=self.toggleTheme)
        themeBtn.pack(side='right', padx=5)
        
        hintLabel = tk.Label(titleFrame, text=self.i18n.t('click_outside_hint'), 
                             bg=theme['title_bg'], fg=theme['title_fg'], font=('Arial', 8))
        hintLabel.pack(side='right', padx=10)
    
    def _createSearchBar(self, parent: tk.Frame) -> None:
        """Create the search bar."""
        theme = self.getTheme()
        
        searchFrame = tk.Frame(parent, bg=theme['bg'])
        searchFrame.pack(fill='x', padx=5, pady=5)
        
        searchIcon = tk.Label(searchFrame, text="🔍", bg=theme['bg'], fg=theme['fg'], font=('Arial', 12))
        searchIcon.pack(side='left', padx=(5, 2))
        
        self.searchVar = tk.StringVar()
        self.searchTraceId = self.searchVar.trace('w', lambda *args: self._safeRefresh())
        
        self.searchEntry = tk.Entry(searchFrame, textvariable=self.searchVar, 
                            font=('Arial', 10), relief='flat', 
                            bg=theme['search_bg'], fg=theme['search_fg'],
                            insertbackground=theme['fg'])
        self.searchEntry.pack(side='left', fill='x', expand=True, padx=5, pady=5)
        self.searchEntry.insert(0, self.i18n.t('search_placeholder'))
        self.searchEntry.config(fg='grey')
        
        def onSearchFocusIn(e):
            if self.searchEntry.get() == self.i18n.t('search_placeholder'):
                self.searchEntry.delete(0, tk.END)
                self.searchEntry.config(fg=theme['search_fg'])
        
        def onSearchFocusOut(e):
            if not self.searchEntry.get():
                self.searchEntry.insert(0, self.i18n.t('search_placeholder'))
                self.searchEntry.config(fg='grey')
        
        self.searchEntry.bind('<FocusIn>', onSearchFocusIn)
        self.searchEntry.bind('<FocusOut>', onSearchFocusOut)
        def handleUp(e):
            self._navigateUp(e)
            return "break"  # Prevent event from bubbling up
        
        def handleDown(e):
            self._navigateDown(e)
            return "break"  # Prevent event from bubbling up
        
        def handleReturn(e):
            self._selectCurrentEntry(e)
            return "break"  # Prevent event from bubbling up
        self.searchEntry.bind('<Up>', handleUp)
        self.searchEntry.bind('<Down>', handleDown)
        self.searchEntry.bind('<Return>', handleReturn)
    
    def _createScrollableArea(self, parent: tk.Frame) -> None:
        """Create the scrollable content area."""
        theme = self.getTheme()
        
        mainFrame = tk.Frame(parent, bg=theme['bg'])
        mainFrame.pack(fill='both', expand=True)
        
        self.canvas = tk.Canvas(mainFrame, bg=theme['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(mainFrame, orient='vertical', command=self.canvas.yview)
        self.scrollableFrame = tk.Frame(self.canvas, bg=theme['bg'])
        
        self.scrollableFrame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollableFrame, anchor='nw')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Bind mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._onMouseWheel)
        self.canvas.bind_all("<Button-4>", self._onMouseWheel)
        self.canvas.bind_all("<Button-5>", self._onMouseWheel)
    
    def _onMouseWheel(self, event):
        """Handle mouse wheel scrolling."""
        if not self.canvas:
            return
        
        try:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        except:
            pass
    
    def _safeRefresh(self) -> None:
        """Safely refresh display, checking if widgets still exist."""
        if self.popupWindow and self.scrollableFrame:
            try:
                if self.popupWindow.winfo_exists() and self.scrollableFrame.winfo_exists():
                    self.selectedIndex = 0  # Reset selection on search
                    self.onRefresh()
            except:
                pass

    def refreshDisplay(self, entries: list) -> None:
        """Refresh the display with given entries."""
        if not self.scrollableFrame:
            return
        
        try:
            self.scrollableFrame.winfo_exists()
        except:
            return
        
        theme = self.getTheme()
        self.currentEntries = entries
        self.itemFrames = []
        
        # Clear existing items
        for widget in self.scrollableFrame.winfo_children():
            widget.destroy()
        
        # Add entries
        for idx, entry in enumerate(entries):
            frame = self._createHistoryItem(self.scrollableFrame, entry, idx)
            self.itemFrames.append(frame)
        
        # Update selection highlight
        self._updateSelection()
    
    def _createHistoryItem(self, parent: tk.Frame, entry: ClipboardEntry, idx: int) -> tk.Frame:
        """Create a history item widget."""
        theme = self.getTheme()
        
        itemFrame = tk.Frame(parent, bg=theme['bg'], relief='solid', borderwidth=0)
        itemFrame.pack(fill='x', padx=5, pady=3)
        
        # Content frame (left side)
        contentFrame = tk.Frame(itemFrame, bg=theme['bg'])
        contentFrame.pack(side='left', fill='both', expand=True)
        
        # Create content display
        if entry.isImage:
            self._createImageItem(contentFrame, entry, itemFrame)
        else:
            self._createTextItem(contentFrame, entry)
        
        # Action buttons frame (right side)
        actionFrame = self._createActionButtons(itemFrame, entry)
        
        # Click to copy and paste
        self._bindCopyPaste(contentFrame, entry, idx)
        
        # Hover effect
        self._bindHoverEffect(itemFrame, contentFrame, actionFrame, idx)
        
        return itemFrame
    
    def _createImageItem(self, parent: tk.Frame, entry: ClipboardEntry, itemFrame: tk.Frame) -> None:
        """Create an image item display."""
        theme = self.getTheme()
        
        # Thumbnail for image
        img = entry.content.copy()
        img.thumbnail((60, 60), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        
        label = tk.Label(parent, image=photo, bg=theme['bg'])
        label.image = photo
        label.pack(side='left', padx=5, pady=5)
        
        pinIndicator = "📌 " if entry.isPinned else ""
        textLabel = tk.Label(parent, 
                             text=f"{pinIndicator}[{self.i18n.t('image_label')}] {entry.timestamp.strftime('%H:%M:%S')}", 
                             bg=theme['bg'], fg=theme['fg'], anchor='w', font=('Arial', 9))
        textLabel.pack(side='left', fill='x', expand=True, padx=5)
        
        # Bind hover for preview
        parent.bind('<Enter>', lambda e, ent=entry, frm=itemFrame: self._showImagePreview(e, ent))
        parent.bind('<Leave>', self._hidePreview)
        label.bind('<Enter>', lambda e, ent=entry, frm=itemFrame: self._showImagePreview(e, ent))
        label.bind('<Leave>', self._hidePreview)
    
    def _createTextItem(self, parent: tk.Frame, entry: ClipboardEntry) -> None:
        """Create a text item display."""
        theme = self.getTheme()
        
        preview = entry.content[:80] + '...' if len(entry.content) > 80 else entry.content
        preview = preview.replace('\n', ' ')
        
        pinIndicator = "📌 " if entry.isPinned else ""
        textLabel = tk.Label(parent, text=f"{pinIndicator}{preview}", 
                            bg=theme['bg'], fg=theme['fg'], anchor='w', justify='left', 
                            font=('Arial', 9), wraplength=350)
        textLabel.pack(side='left', fill='x', expand=True, padx=10, pady=8)
        
        # Bind hover for text preview
        parent.bind('<Enter>', lambda e, ent=entry: self._showTextPreview(e, ent))
        parent.bind('<Leave>', self._hidePreview)
        textLabel.bind('<Enter>', lambda e, ent=entry: self._showTextPreview(e, ent))
        textLabel.bind('<Leave>', self._hidePreview)
    
    def _createActionButtons(self, parent: tk.Frame, entry: ClipboardEntry) -> tk.Frame:
        """Create action buttons for an entry."""
        theme = self.getTheme()
        
        actionFrame = tk.Frame(parent, bg=theme['bg'])
        actionFrame.pack(side='right', padx=5)
        
        # Pin button
        pinBtn = tk.Button(actionFrame, text="📌" if not entry.isPinned else "📍",
                        bg=theme['bg'], fg=theme['fg'], relief='flat', font=('Arial', 12),
                        cursor='hand2', borderwidth=0, activebackground=theme['btn_hover'])
        pinBtn.pack(side='left', padx=2)
        pinBtn.bind('<Button-1>', lambda e: (self.onPin(entry), hidePinTooltip(e)))
        
        # Pin button tooltip
        pinTooltip = None
        
        def showPinTooltip(e):
            nonlocal pinTooltip
            pinTooltip = tk.Toplevel(self.popupWindow)
            pinTooltip.overrideredirect(True)
            pinTooltip.attributes('-topmost', True)
            
            tooltip_text = self.i18n.t('unpin_tooltip') if entry.isPinned else self.i18n.t('pin_tooltip')
            label = tk.Label(pinTooltip, text=tooltip_text,
                            bg=theme['tooltip_bg'], fg=theme['tooltip_fg'], 
                            font=('Arial', 9), padx=5, pady=2)
            label.pack()
            
            x = e.widget.winfo_rootx()
            y = e.widget.winfo_rooty() - 30
            pinTooltip.geometry(f"+{x}+{y}")
            pinBtn.config(bg=theme['btn_hover'])
        
        def hidePinTooltip(e):
            nonlocal pinTooltip
            if pinTooltip:
                try:
                    pinTooltip.destroy()
                    pinTooltip = None
                except:
                    pinTooltip = None
            try:
                pinBtn.config(bg=actionFrame.cget('bg'))
            except:
                pass
        
        pinBtn.bind('<Enter>', showPinTooltip)
        pinBtn.bind('<Leave>', hidePinTooltip)
        
        # Remove button
        removeBtn = tk.Button(actionFrame, text="🗑️",
                            bg=theme['bg'], fg=theme['fg'], relief='flat', font=('Arial', 12),
                            cursor='hand2', borderwidth=0, activebackground=theme['btn_danger'])
        removeBtn.pack(side='left', padx=2)
        removeBtn.bind('<Button-1>', lambda e: (self.onRemove(entry), hideRemoveTooltip(e)))
        
        # Remove button tooltip
        removeTooltip = None
        
        def showRemoveTooltip(e):
            nonlocal removeTooltip
            removeTooltip = tk.Toplevel(self.popupWindow)
            removeTooltip.overrideredirect(True)
            removeTooltip.attributes('-topmost', True)
            
            label = tk.Label(removeTooltip, text=self.i18n.t('remove_tooltip'),
                            bg='#D32F2F', fg='white', font=('Arial', 9), padx=5, pady=2)
            label.pack()
            
            x = e.widget.winfo_rootx()
            y = e.widget.winfo_rooty() - 30
            removeTooltip.geometry(f"+{x}+{y}")
            removeBtn.config(bg=theme['btn_danger'])
        
        def hideRemoveTooltip(e):
            nonlocal removeTooltip
            if removeTooltip:
                try:
                    removeTooltip.destroy()
                    removeTooltip = None
                except:
                    removeTooltip = None
            try:
                removeBtn.config(bg=actionFrame.cget('bg'))
            except:
                pass
        
        removeBtn.bind('<Enter>', showRemoveTooltip)
        removeBtn.bind('<Leave>', hideRemoveTooltip)

        return actionFrame
    
    def _bindCopyPaste(self, contentFrame: tk.Frame, entry: ClipboardEntry, idx: int) -> None:
        """Bind copy and paste action to content frame."""
        def copyAndPasteEntry(e):
            if isinstance(e.widget, tk.Button):
                return
            self.selectedIndex = idx
            self._updateSelection()
            self.onCopy(entry)
        
        contentFrame.bind('<Button-1>', copyAndPasteEntry)
        for child in contentFrame.winfo_children():
            if not isinstance(child, tk.Button):
                child.bind('<Button-1>', copyAndPasteEntry)
    
    def _bindHoverEffect(self, itemFrame: tk.Frame, contentFrame: tk.Frame, 
                        actionFrame: tk.Frame, idx: int) -> None:
        """Bind hover effects to item frame."""
        theme = self.getTheme()
        hoverColor = theme['hover']
        defaultColor = theme['bg']

        def onEnter(e):
            # Don't override selection highlight
            if idx != self.selectedIndex:
                self._highlightFrame(itemFrame, hoverColor)

        def onLeave(e):
            # Don't override selection highlight
            if idx != self.selectedIndex:
                self._highlightFrame(itemFrame, defaultColor)
        
        itemFrame.bind('<Enter>', onEnter)
        itemFrame.bind('<Leave>', onLeave)
    
    def _showImagePreview(self, event, entry: ClipboardEntry) -> None:
        """Show image preview on hover."""
        if not entry.isImage:
            return
        
        if self.hoverPreview:
            try:
                self.hoverPreview.destroy()
            except:
                pass
        
        self.hoverPreview = tk.Toplevel(self.root)
        self.hoverPreview.overrideredirect(True)
        self.hoverPreview.attributes('-topmost', True)
        
        x = event.x_root + 15
        y = event.y_root + 15
        
        img = entry.content.copy()
        img.thumbnail((400, 400), Image.Resampling.LANCZOS)
        
        self.hoverPreview.photo = ImageTk.PhotoImage(img)
        
        frame = tk.Frame(self.hoverPreview, bg='#333', relief='solid', borderwidth=0)
        frame.pack()
        
        label = tk.Label(frame, image=self.hoverPreview.photo, bg='white')
        label.pack(padx=2, pady=2)
        
        self.hoverPreview.geometry(f"+{x}+{y}")
        self.hoverPreview.update_idletasks()
    
    def _showTextPreview(self, event, entry: ClipboardEntry) -> None:
        """Show text preview on hover."""
        if entry.isImage:
            return
        
        theme = self.getTheme()
        
        if self.hoverPreview:
            try:
                self.hoverPreview.destroy()
            except:
                pass
        
        self.hoverPreview = tk.Toplevel(self.root)
        self.hoverPreview.overrideredirect(True)
        self.hoverPreview.attributes('-topmost', True)
        
        x = event.x_root + 15
        y = event.y_root + 15
        
        frame = tk.Frame(self.hoverPreview, bg=theme['tooltip_bg'], relief='solid', borderwidth=0)
        frame.pack()
        
        textWidget = tk.Text(frame, bg=theme['bg'], fg=theme['fg'], 
                            font=('Arial', 10), wrap='word',
                            width=60, height=20, relief='flat',
                            padx=10, pady=10)
        textWidget.insert('1.0', entry.content)
        textWidget.config(state='disabled')
        textWidget.pack(padx=2, pady=2)
        
        self.hoverPreview.geometry(f"+{x}+{y}")
        self.hoverPreview.update_idletasks()
    
    def _hidePreview(self, event) -> None:
        """Hide preview."""
        if self.hoverPreview:
            try:
                self.hoverPreview.destroy()
            except:
                pass
            self.hoverPreview = None
    
    def _bindOutsideClick(self) -> None:
        """Bind click outside window to close."""
        if self.popupWindow:
            self.root.bind_all('<Button-1>', self._checkClickOutside, '+')
    
    def _checkClickOutside(self, event) -> None:
        """Check if click is outside popup window."""
        if self.popupWindow:
            x, y = self.popupWindow.winfo_x(), self.popupWindow.winfo_y()
            w, h = self.popupWindow.winfo_width(), self.popupWindow.winfo_height()
            
            if not (x <= event.x_root <= x + w and y <= event.y_root <= y + h):
                self.closePopup()
    
    def closePopup(self) -> None:
        """Close the history popup."""
        self.root.unbind_all('<Button-1>')
        self.root.unbind_all('<MouseWheel>')
        self.root.unbind_all('<Button-4>')
        self.root.unbind_all('<Button-5>')
        
        if self.searchVar and self.searchTraceId:
            try:
                self.searchVar.trace_vdelete('w', self.searchTraceId)
            except:
                pass
            self.searchTraceId = None
        
        if self.hoverPreview:
            try:
                self.hoverPreview.destroy()
            except:
                pass
            self.hoverPreview = None
        
        if self.popupWindow:
            self.popupWindow.destroy()
            self.popupWindow = None
        
        self.searchVar = None
        self.searchEntry = None
        self.canvas = None
        self.scrollableFrame = None
        self.currentEntries = []
        self.selectedIndex = 0
        self.itemFrames = []
    
    def getSearchQuery(self) -> str:
        """Get current search query."""
        if not self.searchVar:
            return ""
        
        query = self.searchVar.get()
        if query == self.i18n.t('search_placeholder'):
            return ""
        
        return query.lower()
    
    def isOpen(self) -> bool:
        """Check if popup is currently open."""
        return self.popupWindow is not None