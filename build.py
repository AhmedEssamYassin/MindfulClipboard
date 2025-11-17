"""
Build script for creating executable with assets
"""

import PyInstaller.__main__
import shutil
import sys
import os
from pathlib import Path

# Fix encoding issues on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass

def cleanBuild():
    """Clean previous builds"""
    for dirName in ['build', 'dist']:
        if Path(dirName).exists():
            shutil.rmtree(dirName)
    print("[CLEAN] Cleaned previous builds")

def getBuildArgs():
    """Get platform-specific build arguments"""
    
    # Detect platform
    isWindows = sys.platform.startswith('win')
    isLinux = sys.platform.startswith('linux')
    
    print(f"[INFO] Building for: {sys.platform}")
    
    # Base arguments
    args = [
        'main.py',
        '--name=MindfulClipboard',
        '--onefile',
        '--clean',
    ]
    
    # Platform-specific console setting
    if isWindows:
        args.append('--noconsole')  # No console on Windows
    else:
        # On Linux, keep console for debugging
        # Remove --noconsole to see error messages
        pass
    
    # UPX compression (optional, can cause issues on Linux)
    if isWindows:
        args.append('--noupx')
    else:
        args.append('--noupx')  # Disable UPX on Linux too
    
    # Add icon (platform-specific)
    if isWindows:
        iconPath = 'assets/images/icon.ico'  # Windows needs .ico
        if Path(iconPath).exists():
            args.append(f'--icon={iconPath}')
    elif isLinux:
        iconPath = 'assets/images/icon.png'  # Linux uses .png
        if Path(iconPath).exists():
            args.append(f'--icon={iconPath}')
    
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
    ])
    
    # Platform-specific hidden imports
    if isWindows:
        args.extend([
            '--hidden-import=win32clipboard',
            '--hidden-import=win32con',
            '--hidden-import=win32api',
            '--hidden-import=winshell',
            '--hidden-import=win32com',
            '--hidden-import=win32com.client',
        ])
    elif isLinux:
        # Linux-specific imports
        args.extend([
            '--hidden-import=Xlib',
            '--hidden-import=Xlib.display',
            '--hidden-import=Xlib.X',
            '--hidden-import=Xlib.protocol',
            '--collect-all=pystray',  # Collect all pystray modules
            '--collect-all=PIL',      # Collect all PIL modules
        ])
    
    return args

def main():
    """Main build function"""
    print("[BUILD] Building MindfulClipboard...")
    print(f"[PLATFORM] {sys.platform}")
    print(f"[PYTHON] {sys.version}")
    
    # Clean previous builds
    cleanBuild()
    
    # Get build arguments
    args = getBuildArgs()
    
    print(f"[ARGS] Build arguments:")
    for arg in args:
        print(f"  {arg}")
    
    # Build
    try:
        PyInstaller.__main__.run(args)
        print("\n" + "="*50)
        print("[SUCCESS] Build complete! Executable in dist/ folder")
        print("="*50)
        
        # Show final executable location
        exeName = 'MindfulClipboard.exe' if sys.platform.startswith('win') else 'MindfulClipboard'
        exePath = Path('dist') / exeName
        if exePath.exists():
            print(f"[LOCATION] {exePath.absolute()}")
            print(f"[SIZE] {exePath.stat().st_size / (1024*1024):.2f} MB")
            
            # Make executable on Linux
            if sys.platform.startswith('linux'):
                os.chmod(exePath, 0o755)
                print("[CHMOD] Made executable (chmod +x)")
        else:
            print("[ERROR] Executable not found after build!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n[ERROR] Build failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()