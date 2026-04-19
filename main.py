"""Main entry point for the Clipboard Manager application."""
import sys
import os
import threading
import webview

from src.manager import ClipboardManager


def getHtmlPath():
    if getattr(sys, "frozen", False):
        basePath = sys._MEIPASS
    else:
        basePath = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(basePath, "src", "web", "index.html")


def main():
    manager = ClipboardManager()
    manager.start()
    
    htmlPath = getHtmlPath()
    if not os.path.exists(htmlPath):
        print(f"Error: HTML file not found at {htmlPath}")
        sys.exit(1)
    
    window = webview.create_window(
        "MindfulClipboard",
        url=htmlPath,
        width=420,
        height=540,
        x=-5000,
        y=-5000,
        resizable=False,
        frameless=True,
        transparent=True,
        on_top=True,
        hidden=True,
        js_api=manager.api
    )
    
    manager.window = window
    manager.api.setRefreshCallback(lambda: window.evaluate_js("refreshData()"))
    
    def onClosing():
        window.hide()
        return True
    
    window.events.closing += onClosing
    
    def startMonitorLoop():
        import time
        while True:
            time.sleep(0.5)
    
    monitorThread = threading.Thread(target=startMonitorLoop, daemon=True)
    monitorThread.start()
    
    # Restore SystemTray
    from src.tray import SystemTray
    
    def onQuit():
        manager.stop()
        window.destroy()
        os._exit(0)
        
    def onShow():
        manager.showPopup()
    if getattr(sys, "frozen", False):
        basePath = sys._MEIPASS
    else:
        basePath = os.path.abspath(os.path.dirname(__file__))
    assetsPath = os.path.join(basePath, "assets")
    
    tray = SystemTray(onQuit=onQuit, onShow=onShow, assetsDir=assetsPath)
    tray.start()
    
    import time
    time.sleep(1.0)
    if manager.i18n:
        tray.showNotification(
            title=manager.i18n.t('app_name', 'MindfulClipboard'),
            message=manager.i18n.t('tray_started', 'Press Win+V to open clipboard history')
        )
    
    try:
        webview.start(debug=False, http_server=True)
    finally:
        tray.stop()

if __name__ == "__main__":
    main()