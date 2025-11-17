"""
Build script for creating executable with assets
"""

import PyInstaller.__main__
import shutil
import sys
import os
from pathlib import Path

def cleanBuild():
    """Clean previous builds"""
    # Clean build directories
    for dir in ['build', 'dist']:
        if Path(dir).exists():
            shutil.rmtree(dir)
    
    # Clean .spec file
    specFile = Path('MindfulClipboard.spec')
    if specFile.exists():
        specFile.unlink()
    
    print("[CLEAN] Cleaned previous builds")

def getBuildArgs():
    """Get platform-specific build arguments"""
    
    # Detect platform
    isWindows = sys.platform.startswith('win')
    isLinux = sys.platform.startswith('linux')
    isMacOS = sys.platform.startswith('darwin')
    
    # Base arguments
    args = [
        'main.py',
        '--name=MindfulClipboard',
        '--onefile',
        '--noconsole',
        '--noupx',
        '--clean',
    ]
    
    # Add icon (platform-specific)
    if isWindows:
        iconPath = 'assets/images/icon.ico'  # Windows needs .ico
        if Path(iconPath).exists():
            args.append(f'--icon={iconPath}')
        else:
            print(f"[WARNING] Icon file not found: {iconPath}")
    elif isLinux or isMacOS:
        iconPath = 'assets/images/icon.png'  # Linux/macOS uses .png
        if Path(iconPath).exists():
            args.append(f'--icon={iconPath}')
        else:
            print(f"[WARNING] Icon file not found: {iconPath}")
    
    # Verify required folders exist
    if not Path('assets').exists():
        print("[ERROR] Assets folder not found!")
        sys.exit(1)
    
    if not Path('locales').exists():
        print("[ERROR] Locales folder not found!")
        sys.exit(1)
    
    # Add assets (platform-specific separator)
    if isWindows:
        args.append('--add-data=assets;assets')
        args.append('--add-data=locales;locales')
    else:
        args.append('--add-data=assets:assets')
        args.append('--add-data=locales:locales')
    
    # Hidden imports for system tray
    args.extend([
        '--hidden-import=pystray',
        '--hidden-import=PIL',
        '--hidden-import=PIL._imagingtk',
        '--hidden-import=PIL._tkinter_finder',
        '--hidden-import=pyperclip',
        '--hidden-import=keyboard',
    ])
    
    # Windows-specific options
    if isWindows:
        args.extend([
            '--hidden-import=win32clipboard',
            '--hidden-import=win32con',
            '--hidden-import=win32api',
            '--hidden-import=winshell',           
            '--hidden-import=win32com',           
            '--hidden-import=win32com.client',
        ])
    
    # Linux-specific options
    if isLinux:
        args.extend([
            '--hidden-import=Xlib',
        ])
    
    return args

def main():
    """Main build function"""
    print("=" * 50)
    print("Building MindfulClipboard")
    print("=" * 50)
    print(f"[INFO] Platform: {sys.platform}")
    print(f"[INFO] Python: {sys.version.split()[0]}")
    
    # Clean previous builds
    cleanBuild()
    
    # Get build arguments
    args = getBuildArgs()
    
    print(f"[INFO] Build arguments:")
    for arg in args:
        print(f"  - {arg}")
    
    # Build
    try:
        print("\n[BUILD] Starting PyInstaller...")
        PyInstaller.__main__.run(args)
        
        # Verify build output
        exeName = 'MindfulClipboard.exe' if sys.platform.startswith('win') else 'MindfulClipboard'
        exePath = Path('dist') / exeName
        
        if exePath.exists():
            fileSize = exePath.stat().st_size / (1024*1024)
            print("\n" + "=" * 50)
            print("[SUCCESS] Build complete!")
            print("=" * 50)
            print(f"[INFO] Executable: {exePath.absolute()}")
            print(f"[INFO] Size: {fileSize:.2f} MB")
            
            # Make executable on Linux/macOS
            if not sys.platform.startswith('win'):
                os.chmod(exePath, 0o755)
                print(f"[INFO] Made executable with chmod +x")
        else:
            print(f"[ERROR] Executable not found at: {exePath}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[ERROR] Build failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()