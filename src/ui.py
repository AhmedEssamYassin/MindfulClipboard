"""User interface components for clipboard manager."""
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
from typing import Callable, Optional

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
        self.searchTraceId: Optional[str] = None
        self.canvas: Optional[tk.Canvas] = None
        self.scrollableFrame: Optional[tk.Frame] = None
    
    def showPopup(self, x: int, y: int) -> None:
        """Show history popup at specified coordinates."""
        if self.popupWindow:
            # Close any existing popup before opening a new one
            self.popupWindow.destroy()
            self.popupWindow = None  # Clear the reference to the old popup
        
        # Popup dimensions
        popup_width = 500
        popup_height = 500
        
        # Get screen dimensions
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Adjust x position to prevent horizontal overflow
        if x + popup_width > screen_width:
            x = screen_width - popup_width - 10  # 10px margin from right edge
        if x < 0:
            x = 10  # 10px margin from left edge
        
        # Adjust y position to prevent vertical overflow
        if y + popup_height > screen_height:
            y = screen_height - popup_height - 10  # 10px margin from bottom
        if y < 0:
            y = 10  # 10px margin from top
        
        # Create popup
        self.popupWindow = tk.Toplevel(self.root)
        self.popupWindow.title(self.i18n.t('window_title'))
        self.popupWindow.attributes('-topmost', True)
        self.popupWindow.overrideredirect(True)
        self.popupWindow.geometry(f"{popup_width}x{popup_height}+{x}+{y}")
        
        # Add border
        outerFrame = tk.Frame(self.popupWindow, bg='#2196F3', relief='flat', borderwidth=1)
        outerFrame.pack(fill='both', expand=True)
        
        # Title bar
        self._createTitleBar(outerFrame)
        
        # Search bar
        self._createSearchBar(outerFrame)
        
        # Create frame with scrollbar
        self._createScrollableArea(outerFrame)
        
        # Force focus after the popup is created
        self.root.after(10, self.popupWindow.focus_force)
        
        # Bind events
        self.popupWindow.bind('<Escape>', lambda e: self.closePopup())
        self.popupWindow.bind('<FocusOut>', lambda e: self.closePopup())
        
        # Ensure popup stays on top and gets focus
        self.root.after(100, self._bindOutsideClick)
    
    def _createTitleBar(self, parent: tk.Frame) -> None:
        """Create the title bar."""
        titleFrame = tk.Frame(parent, bg='#2196F3', height=35)
        titleFrame.pack(fill='x')
        titleFrame.pack_propagate(False)
        
        titleLabel = tk.Label(titleFrame, text=f"📋 {self.i18n.t('window_title')}", 
                               bg='#2196F3', fg='white', font=('Arial', 11, 'bold'))
        titleLabel.pack(side='left', padx=10, pady=5)
        
        hintLabel = tk.Label(titleFrame, text=self.i18n.t('click_outside_hint'), 
                             bg='#2196F3', fg='#E3F2FD', font=('Arial', 8))
        hintLabel.pack(side='right', padx=10)
    
    def _createSearchBar(self, parent: tk.Frame) -> None:
        """Create the search bar."""
        searchFrame = tk.Frame(parent, bg='white')
        searchFrame.pack(fill='x', padx=5, pady=5)
        
        searchIcon = tk.Label(searchFrame, text="🔍", bg='white', font=('Arial', 12))
        searchIcon.pack(side='left', padx=(5, 2))
        
        self.searchVar = tk.StringVar()
        # Store the trace ID so we can remove it later
        self.searchTraceId = self.searchVar.trace('w', lambda *args: self._safeRefresh())
        
        searchEntry = tk.Entry(searchFrame, textvariable=self.searchVar, 
                            font=('Arial', 10), relief='flat', bg='#F5F5F5')
        searchEntry.pack(side='left', fill='x', expand=True, padx=5, pady=5)
        searchEntry.insert(0, self.i18n.t('search_placeholder'))
        searchEntry.config(fg='grey')
        
        def onSearchFocusIn(e):
            if searchEntry.get() == self.i18n.t('search_placeholder'):
                searchEntry.delete(0, tk.END)
                searchEntry.config(fg='black')
        
        def onSearchFocusOut(e):
            if not searchEntry.get():
                searchEntry.insert(0, self.i18n.t('search_placeholder'))
                searchEntry.config(fg='grey')
        
        searchEntry.bind('<FocusIn>', onSearchFocusIn)
        searchEntry.bind('<FocusOut>', onSearchFocusOut)
    
    def _createScrollableArea(self, parent: tk.Frame) -> None:
        """Create the scrollable content area."""
        mainFrame = tk.Frame(parent, bg='white')
        mainFrame.pack(fill='both', expand=True)
        
        self.canvas = tk.Canvas(mainFrame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(mainFrame, orient='vertical', command=self.canvas.yview)
        self.scrollableFrame = tk.Frame(self.canvas, bg='white')
        
        self.scrollableFrame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollableFrame, anchor='nw')
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
    
    def _safeRefresh(self) -> None:
        """Safely refresh display, checking if widgets still exist."""
        if self.popupWindow and self.scrollableFrame:
            try:
                # Check if widgets still exist
                if self.popupWindow.winfo_exists() and self.scrollableFrame.winfo_exists():
                    self.onRefresh()
            except:
                pass

    def refreshDisplay(self, entries: list) -> None:
        """Refresh the display with given entries."""
        if not self.scrollableFrame:
            return
        
        # Safety check: verify the widget still exists
        try:
            self.scrollableFrame.winfo_exists()
        except:
            return
        
        # Clear existing items
        for widget in self.scrollableFrame.winfo_children():
            widget.destroy()
        
        # Add entries
        for idx, entry in enumerate(entries):
            self._createHistoryItem(self.scrollableFrame, entry, idx)
    
    def _createHistoryItem(self, parent: tk.Frame, entry: ClipboardEntry, idx: int) -> None:
        """Create a history item widget."""
        itemFrame = tk.Frame(parent, bg='white', relief='solid', borderwidth=0)
        itemFrame.pack(fill='x', padx=5, pady=3)
        
        # Content frame (left side)
        contentFrame = tk.Frame(itemFrame, bg='white')
        contentFrame.pack(side='left', fill='both', expand=True)
        
        # Create content display
        if entry.isImage:
            self._createImageItem(contentFrame, entry, itemFrame)
        else:
            self._createTextItem(contentFrame, entry)
        
        # Action buttons frame (right side)
        actionFrame = self._createActionButtons(itemFrame, entry)
        
        # Click to copy and paste
        self._bindCopyPaste(contentFrame, entry)
        
        # Hover effect
        self._bindHoverEffect(itemFrame, contentFrame, actionFrame)
    
    def _createImageItem(self, parent: tk.Frame, entry: ClipboardEntry, itemFrame: tk.Frame) -> None:
        """Create an image item display."""
        # Thumbnail for image
        img = entry.content.copy()
        img.thumbnail((60, 60), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        
        label = tk.Label(parent, image=photo, bg='white')
        label.image = photo
        label.pack(side='left', padx=5, pady=5)
        
        pinIndicator = "📌 " if entry.isPinned else ""
        textLabel = tk.Label(parent, 
                             text=f"{pinIndicator}[{self.i18n.t('image_label')}] {entry.timestamp.strftime('%H:%M:%S')}", 
                             bg='white', anchor='w', font=('Arial', 9))
        textLabel.pack(side='left', fill='x', expand=True, padx=5)
        
        # Bind hover for preview
        parent.bind('<Enter>', lambda e, ent=entry, frm=itemFrame: self._showImagePreview(e, ent))
        parent.bind('<Leave>', self._hidePreview)
        label.bind('<Enter>', lambda e, ent=entry, frm=itemFrame: self._showImagePreview(e, ent))
        label.bind('<Leave>', self._hidePreview)
    
    def _createTextItem(self, parent: tk.Frame, entry: ClipboardEntry) -> None:
        """Create a text item display."""
        preview = entry.content[:80] + '...' if len(entry.content) > 80 else entry.content
        preview = preview.replace('\n', ' ')
        
        pinIndicator = "📌 " if entry.isPinned else ""
        textLabel = tk.Label(parent, text=f"{pinIndicator}{preview}", 
                            bg='white', anchor='w', justify='left', 
                            font=('Arial', 9), wraplength=350)
        textLabel.pack(side='left', fill='x', expand=True, padx=10, pady=8)
        
        # Bind hover for text preview
        parent.bind('<Enter>', lambda e, ent=entry: self._showTextPreview(e, ent))
        parent.bind('<Leave>', self._hidePreview)
        textLabel.bind('<Enter>', lambda e, ent=entry: self._showTextPreview(e, ent))
        textLabel.bind('<Leave>', self._hidePreview)
    
    def _createActionButtons(self, parent: tk.Frame, entry: ClipboardEntry) -> None:
        """Create action buttons for an entry."""
        actionFrame = tk.Frame(parent, bg='white')
        actionFrame.pack(side='right', padx=5)
        
        # Pin button
        pinBtn = tk.Button(actionFrame, text="📌" if not entry.isPinned else "📍",
                        bg='white', relief='flat', font=('Arial', 12),
                        cursor='hand2', borderwidth=0, activebackground='#E3F2FD')
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
                            bg='#333', fg='white', font=('Arial', 9), padx=5, pady=2)
            label.pack()
            
            x = e.widget.winfo_rootx()
            y = e.widget.winfo_rooty() - 30
            pinTooltip.geometry(f"+{x}+{y}")
            pinBtn.config(bg='#E3F2FD')
        
        def hidePinTooltip(e):
            nonlocal pinTooltip
            if pinTooltip:
                try:
                    pinTooltip.destroy()
                    pinTooltip = None
                except:
                    pinTooltip = None
            try:
                pinBtn.config(bg='#E3F2FD')
            except:
                pass  # Button might have been destroyed
        
        pinBtn.bind('<Enter>', showPinTooltip)
        pinBtn.bind('<Leave>', hidePinTooltip)
        
        # Remove button
        removeBtn = tk.Button(actionFrame, text="🗑️",
                            bg='white', relief='flat', font=('Arial', 12),
                            cursor='hand2', borderwidth=0, activebackground='#FFEBEE')
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
            removeBtn.config(bg='#E3F2FD')
        
        def hideRemoveTooltip(e):
            nonlocal removeTooltip
            if removeTooltip:
                try:
                    removeTooltip.destroy()
                    removeTooltip = None
                except:
                    removeTooltip = None
            try:
                removeBtn.config(bg='#E3F2FD')
            except:
                pass  # Button might have been destroyed
        
        removeBtn.bind('<Enter>', showRemoveTooltip)
        removeBtn.bind('<Leave>', hideRemoveTooltip)

        return actionFrame
    
    def _bindCopyPaste(self, contentFrame: tk.Frame, entry: ClipboardEntry) -> None:
        """Bind copy and paste action to content frame."""
        def copyAndPasteEntry(e):
            # Don't trigger if clicking buttons
            if isinstance(e.widget, tk.Button):
                return
            self.onCopy(entry)
        
        contentFrame.bind('<Button-1>', copyAndPasteEntry)
        for child in contentFrame.winfo_children():
            if not isinstance(child, tk.Button):
                child.bind('<Button-1>', copyAndPasteEntry)
    
    def _bindHoverEffect(self, itemFrame: tk.Frame, contentFrame: tk.Frame, actionFrame: tk.Frame) -> None:
        """Bind hover effects to item frame."""
        hoverColor = '#E3F2FD'
        defaultColor = 'white'

        def onEnter(e):
            itemFrame.config(bg=hoverColor, relief='solid', borderwidth=0)
            contentFrame.config(bg=hoverColor)
            actionFrame.config(bg=hoverColor)
            
            # Update children of contentFrame
            for child in contentFrame.winfo_children():
                if isinstance(child, tk.Label):
                    child.config(bg=hoverColor)
            
            # Update children of actionFrame (the buttons)
            for child in actionFrame.winfo_children():
                if isinstance(child, tk.Button):
                    child.config(bg=hoverColor)

        def onLeave(e):
            itemFrame.config(bg=defaultColor, relief='solid', borderwidth=0)
            contentFrame.config(bg=defaultColor)
            actionFrame.config(bg=defaultColor)
            
            # Update children of contentFrame (labels)
            for child in contentFrame.winfo_children():
                if isinstance(child, tk.Label):
                    child.config(bg=defaultColor)
            
            # Update children of actionFrame (buttons)
            for child in actionFrame.winfo_children():
                if isinstance(child, tk.Button):
                    child.config(bg=defaultColor)
        
        itemFrame.bind('<Enter>', onEnter)
        itemFrame.bind('<Leave>', onLeave)
    
    def _showImagePreview(self, event, entry: ClipboardEntry) -> None:
        """Show image preview on hover."""
        if not entry.isImage:
            return
        
        # Destroy existing preview
        if self.hoverPreview:
            try:
                self.hoverPreview.destroy()
            except:
                pass
        
        # Create new preview window
        self.hoverPreview = tk.Toplevel(self.root)
        self.hoverPreview.overrideredirect(True)
        self.hoverPreview.attributes('-topmost', True)
        
        # Position near cursor
        x = event.x_root + 15
        y = event.y_root + 15
        
        # Resize image for preview
        img = entry.content.copy()
        img.thumbnail((400, 400), Image.Resampling.LANCZOS)
        
        # Store the PhotoImage as an attribute to prevent garbage collection
        self.hoverPreview.photo = ImageTk.PhotoImage(img)
        
        # Create frame with border
        frame = tk.Frame(self.hoverPreview, bg='#333', relief='solid', borderwidth=0)
        frame.pack()
        
        label = tk.Label(frame, image=self.hoverPreview.photo, bg='white')
        label.pack(padx=2, pady=2)
        
        self.hoverPreview.geometry(f"+{x}+{y}")
        self.hoverPreview.update_idletasks()
    
    def _hidePreview(self, event) -> None:
        """Hide image preview."""
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
        
        # Remove search trace before destroying
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
        self.canvas = None
        self.scrollableFrame = None
    
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

    def _showTextPreview(self, event, entry: ClipboardEntry) -> None:
        """Show text preview on hover."""
        if entry.isImage:
            return
        
        # Destroy existing preview
        if self.hoverPreview:
            try:
                self.hoverPreview.destroy()
            except:
                pass
        
        # Create new preview window
        self.hoverPreview = tk.Toplevel(self.root)
        self.hoverPreview.overrideredirect(True)
        self.hoverPreview.attributes('-topmost', True)
        
        # Position near cursor
        x = event.x_root + 15
        y = event.y_root + 15
        
        # Create frame with border
        frame = tk.Frame(self.hoverPreview, bg='#333', relief='solid', borderwidth=0)
        frame.pack()
        
        # Create text widget for full content
        textWidget = tk.Text(frame, bg='white', fg='black', 
                            font=('Arial', 10), wrap='word',
                            width=60, height=20, relief='flat',
                            padx=10, pady=10)
        textWidget.insert('1.0', entry.content)
        textWidget.config(state='disabled')
        textWidget.pack(padx=2, pady=2)
        
        self.hoverPreview.geometry(f"+{x}+{y}")
        self.hoverPreview.update_idletasks()