# MindfulClipboard

MindfulClipboard is a smart clipboard history manager for Windows (currently), designed to replace the default `Win+V` functionality with a more powerful and feature-rich tool. It monitors your clipboard in the background, saves a history of your copied text and images, and provides a clean, searchable interface to access them.

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
* **Modern UI**: Built with PyWebView (Chromium) and HTML/CSS/JS for a stunning, responsive, and native-feeling web interface.
* **Smart Window Management**: 
   * The popup appears precisely at your cursor's current location.
   * Uses a global mouse-click hook to reliably close the popup the instant you click outside of it, flawlessly bypassing restrictive Windows UIPI focus rules.
* **Background Monitoring**: Runs as a lightweight background thread to monitor clipboard changes without interrupting your workflow.
* **Persistent Storage**: Safely stores your clipboard history and settings in the Windows Local AppData folder to guarantee it runs perfectly without requiring Administrator privileges.
* **Internationalization**: Automatically detects your system language and displays the interface in your preferred language (currently supports English and Arabic).
### Keyboard Shortcut

Press `Win+V` to open the clipboard history popup.

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

## Architectural View

The application has been fully modernized, transitioning from a legacy Tkinter base to a modern Chromium-backed web interface. 

- **Frontend (`src/web`)**: A responsive HTML/JS/CSS application handling the UI, dynamic search, and hover previews.
- **Backend Bridge (`src/api.py`)**: A PyWebView API layer that securely exposes native Python functionality to the JavaScript frontend.
- **State Management (`src/history.py`)**: Handles the thread-safe queue of clipboard items, deduplication, and file I/O interactions.
- **System Control (`src/manager.py`)**: Orchestrates the global hotkeys, Windows Registry hooks (to suppress the native Win+V), and the global mouse-hook lifecycle tracker.

### System Design (UML Diagram)
![UML Diagram](./docs/system%20design%20UML.svg)

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

The build process is automated via `build.py` to generate an optimized `--onedir` distribution, ensuring near-instantaneous startup times required for a background utility.

1. Install build dependencies:
```bash
pip install -r requirements.txt
```

2. Run the automated build script:
```bash
python build.py
```

3. The compiled application will be ready in the `dist/` folder:
   - **Windows**: `dist/MindfulClipboard/MindfulClipboard.exe`

## Usage

### Running the Application

- **From Source**: `python main.py`
- **Executable**: Double-click the executable file

The application will start in the background with a system tray icon.

## Requirements

* Python 3.7+
* Windows 10/11
* Required Python packages (see `requirements.txt`):
  * pywebview - Chromium web UI engine
  * Pillow - Image processing and thumbnail generation
  * pyperclip - Clipboard operations
  * keyboard - Global keyboard hotkey hooking
  * pywin32 - Windows registry and low-level API bindings
  * pystray - System tray icon management

## Platform-Specific Notes

### Windows
- Requires Windows 10 or later
- Uses `.ico` format for the application icon
- Automatically suppresses the default Windows+V clipboard

## Troubleshooting

### Windows: Application doesn't start or immediately crashes
Ensure that PyWebView is correctly bundling the web assets. If running from source, ensure the `src/web/` directory is present. If running the compiled executable, ensure you haven't moved `MindfulClipboard.exe` outside of its generated `dist/MindfulClipboard/` folder, as it relies on the bundled assets in that directory.

### Application doesn't start on boot
- **Windows**: Check the Startup folder: `shell:startup`

## License

This project is open source and available under the MIT License, for more details see the [LICENSE](LICENSE) file.