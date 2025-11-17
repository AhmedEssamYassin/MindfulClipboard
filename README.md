# MindfulClipboard

MindfulClipboard is a smart clipboard history manager for Windows and Linux, designed to replace the default `Win+V` functionality with a more powerful and feature-rich tool. It monitors your clipboard in the background, saves a history of your copied text and images, and provides a clean, searchable interface to access them.

## System Design (UML Diagram)
![UML Diagram](./docs/system%20design/UML%20Diagram.svg)

## Project Structure

```
MindfulClipboard/
├── main.py              # Main application entry point
├── build.py             # Build script for creating executables
├── requirements.txt     # Python dependencies
│
├── assets/              # Icons, images, and other static resources
│   └── images/
│       ├── icon.ico     # Windows icon
│       └── icon.png     # Linux/tray icon
│
├── locales/             # Internationalization files
│   ├── ar.json         # Arabic translations
│   └── en.json         # English translations
│
└── src/
    ├── manager.py       # The central controller; orchestrates all components
    ├── ui.py            # All Tkinter UI logic and component creation
    ├── history.py       # Manages the list of entries (adding, pinning, filtering)
    ├── monitor.py       # Background thread for monitoring clipboard changes
    ├── models.py        # Defines the ClipboardEntry data class
    ├── utils.py         # Helper functions (hashing, image handling)
    ├── i18n.py          # Internationalization handler
    ├── tray.py          # System tray implementation
    │
    └── __pycache__/     # Compiled Python bytecode (auto-generated)
```

## Features

* **Replaces Default Hotkey**: Binds to `Win+V` to show the history popup, suppressing the default Windows clipboard.
* **System Tray Integration**: Runs silently in the background with a system tray icon - just like Telegram!
* **Text and Image Support**: Monitors and saves both text snippets and images copied to the clipboard.
* **Click-to-Paste**: Clicking any entry in the history list copies it to the clipboard and automatically pastes it into your active window.
* **Pinning**: Pin important items to the top of the list. Pinned items are not subject to the history limit and will not be auto-removed.
* **Search & Filtering**: Instantly filter your clipboard history using the built-in search bar.
* **Hover Preview**:
   * **Text**: Hover over a text entry to see its full content in a tooltip.
   * **Images**: Hover over an image entry to see a larger preview.
* **Smart Deduplication**: Automatically ignores consecutive duplicate copies and cleans up older, non-pinned duplicates from the history.
* **Manual Removal**: Manually remove any entry from the history.
* **Smart UI**:
   * The popup appears at your cursor's current location.
   * Closes automatically on `<Escape>`, when focus is lost, or by clicking outside the window.
* **Background Monitoring**: Runs as a lightweight background thread to monitor clipboard changes without interrupting your workflow.
* **Internationalization**: Automatically detects your system language and displays the interface in your preferred language (currently supports English and Arabic).
* **Cross-Platform**: Works on both Windows and Linux!
### Keyboard Shortcut

Press `Win+V` (or `Super+V` on Linux) to open the clipboard history popup.

### System Tray

Right-click the system tray icon to:
- **Open Clipboard**: Show the clipboard history
- **About**: View application information
- **Quit**: Exit the application

## Supported Languages

* **English** (en) - Default
* **Arabic** (ar) - Automatically detected for Arabic systems

The application automatically detects your system's default language and uses the appropriate translations. If your language is not yet supported, it falls back to English.

### Adding a New Language

To add support for a new language:

1. Create a new JSON file in the `locales/` directory named with the language code (e.g., `fr.json` for French)
2. Copy the structure from `en.json` and translate all values
3. The application will automatically detect and use the new language on systems configured for that locale


## Installation

### From Source

1. Clone the repository:
```bash
git clone https://github.com/AhmedEssamYassin/MindfulClipboard.git
cd MindfulClipboard
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python main.py
```

### Building Portable Executable

1. Install build dependencies:
```bash
pip install -r requirements.txt
```

2. Build the executable:
```bash
python build.py
```

3. The executable will be in the `dist/` folder:
   - **Windows**: `dist/MindfulClipboard.exe`
   - **Linux**: `dist/MindfulClipboard`

## Usage

### Running the Application

- **From Source**: `python main.py`
- **Executable**: Double-click the executable file

The application will start in the background with a system tray icon.

## Requirements

* Python 3.7+
* Windows 10/11 or Linux (Ubuntu, Fedora, etc.)
* Required Python packages (see `requirements.txt`):
  * Pillow - Image processing
  * pyperclip - Clipboard operations
  * keyboard - Keyboard hotkey handling
  * pywin32 - Windows clipboard (Windows only)
  * pystray - System tray icon

## Platform-Specific Notes

### Windows
- Requires Windows 10 or later
- Uses `.ico` format for the application icon
- Automatically suppresses the default Windows+V clipboard

### Linux
- Requires X11 or Wayland
- May require additional permissions for keyboard shortcuts
- Uses `.png` format for icons
- On some distributions, you may need to install: `python3-tk` and `xclip`

## Troubleshooting

### Windows: Icon doesn't appear in build
Make sure you have `assets/images/icon.ico` file. Convert PNG to ICO using online tools.

### Linux: Keyboard shortcut doesn't work
Run with sudo permissions or add your user to the `input` group:
```bash
sudo usermod -a -G input $USER
```

### Application doesn't start on boot
- **Windows**: Check the Startup folder: `shell:startup`
- **Linux**: Check `~/.config/autostart/` directory

## License

This project is open source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.