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
    for dir in ['build', 'dist']:
        if Path(dir).exists():
            shutil.rmtree(dir)
    print("🧹 Cleaned previous builds")

def getBuildArgs():
    """Get platform-specific build arguments"""
    
    # Detect platform
    isWindows = sys.platform.startswith('win')
    isLinux = sys.platform.startswith('linux')
    
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
    
    return args

def main():
    """Main build function"""
    print("🔨 Building MindfulClipboard...")
    print(f"📦 Platform: {sys.platform}")
    
    # Clean previous builds
    cleanBuild()
    
    # Get build arguments
    args = getBuildArgs()
    
    print(f"⚙️  Build arguments: {' '.join(args)}")
    
    # Build
    try:
        PyInstaller.__main__.run(args)
        print("✅ Build complete! Executable in dist/ folder")
        
        # Show final executable location
        exeName = 'MindfulClipboard.exe' if sys.platform.startswith('win') else 'MindfulClipboard'
        exePath = Path('dist') / exeName
        if exePath.exists():
            print(f"📍 Executable location: {exePath.absolute()}")
            print(f"📏 Size: {exePath.stat().st_size / (1024*1024):.2f} MB")
    except Exception as e:
        print(f"❌ Build failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()