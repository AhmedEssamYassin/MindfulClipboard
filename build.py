"""Build configuration and packaging script for MindfulClipboard."""
import os
import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

import update_deps

# --- Project Configuration ---
APP_NAME = "MindfulClipboard"
VERSION_NUMBER = "1.0.0"
APP_DESCRIPTION = "Smart Clipboard Manager"

# --- Paths ---
PROJECT_ROOT = Path(__file__).parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
ASSETS_DIR = PROJECT_ROOT / "assets"
LOCALES_DIR = PROJECT_ROOT / "locales"

# Define icon path
ICON_PATH = ASSETS_DIR / "images" / "icon.ico"


def cleanBuildDirs():
    """Removes build, dist directories and .spec files to ensure a fresh build."""
    # 1. Clean directories
    dirs = [DIST_DIR, BUILD_DIR]
    for d in dirs:
        if d.exists():
            try:
                shutil.rmtree(d)
                print(f"[CLEAN] Removed directory: {d.name}")
            except Exception as e:
                print(f"[ERROR] Could not remove {d.name}: {e}")

    # 2. Clean the .spec file
    specFile = PROJECT_ROOT / f"{APP_NAME}.spec"
    if specFile.exists():
        specFile.unlink()  # Deletes the file
        print(f"[CLEAN] Deleted spec file: {APP_NAME}.spec")


def getCommonArgs():
    """Returns the base PyInstaller arguments required for the project."""
    args = [
        "main.py",
        f"--name={APP_NAME}",
        "--clean",
        "--noconsole",  # Hide the terminal window
        "--noupx",      # Disable UPX compression to avoid antivirus false positives
    ]

    # Add Icon
    if ICON_PATH.exists():
        args.append(f"--icon={ICON_PATH}")
    
    # Add Data Files (Windows separator is ;)
    if ASSETS_DIR.exists():
        args.append(f"--add-data={ASSETS_DIR};assets")
    
    if LOCALES_DIR.exists():
        args.append(f"--add-data={LOCALES_DIR};locales")
        
    webDir = PROJECT_ROOT / "src" / "web"
    if webDir.exists():
        args.append(f"--add-data={webDir};src/web")

    # Hidden Imports (Explicitly include dependencies to prevent runtime errors)
    hiddenImports = [
        "pystray",
        "PIL",
        "win32clipboard",
        "win32con",
        "win32api",
        "winshell",
        "win32com",
        "win32com.client",
        "keyboard",
        "darkdetect",
        "webview",
        "webview.platforms.winforms",
    ]
    
    for module in hiddenImports:
        args.append(f"--hidden-import={module}")

    return args


def buildOnefile():
    """Builds the project as a single executable file."""
    print(f"\n[BUILD] Starting ONEFILE build for {APP_NAME}...")
    args = getCommonArgs()
    args.append("--onefile")
    PyInstaller.__main__.run(args)


def buildOnedir():
    """Builds the project as a directory (faster startup, good for debugging)."""
    print(f"\n[BUILD] Starting ONEDIR build for {APP_NAME}...")
    args = getCommonArgs()
    args.append("--onedir")
    PyInstaller.__main__.run(args)


def createSpecFile():
    """Generates and builds from a custom spec file."""
    print(f"\n[SPEC] Generating and building from spec file...")
    
    # Run PyInstaller with --onefile to generate the spec, but we handle the build via the spec 
    # Logic: simple way is just run the build which generates the spec automatically.
    # But to match the menu option "Custom spec file", we'll run the build and note that the spec is used.
    print("[INFO] Building with full configuration which generates a reproducible .spec file")
    buildOnefile()
    print("[INFO] You can now find 'MindfulClipboard.spec' in the root directory for future custom use.")


def showMenu():
    """Show build options menu."""
    print("=" * 60)
    print(f"   {APP_NAME} v{VERSION_NUMBER} - Build Script")
    print("=" * 60)
    print("\nBuild Options:")
    print("   1. One File (single .exe, slower startup)")
    print("   2. One Directory (folder with .exe, faster startup)")
    print("   3. Custom spec file (uses specific hidden imports)")
    print("   4. Clean build directories only")
    print("   0. Exit")
    print()
    return input("Select option [1-4, 0]: ").strip()


def main():
    """Main build process."""
    # Ensure we are on Windows for this script
    if sys.platform != "win32":
        print("[WARNING] This script is optimized for Windows. Linux builds may fail.")
    
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception as e:
        print(f"Could not configure stdout: {e}")

    try:
        while True:
            userChoice = showMenu()
            
            if userChoice == "0":
                sys.exit(0)
            
            if userChoice == "4":
                cleanBuildDirs()
                continue  # Show menu again

            # For build options, clean first then build
            if userChoice in ["1", "2", "3"]:
                cleanBuildDirs()
                
                # Ensure assets exist
                if not ASSETS_DIR.exists():
                    print(f"Warning: {ASSETS_DIR} not found. Creating empty folder.")
                    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

                if userChoice == "1":
                    buildOnefile()
                elif userChoice == "2":
                    buildOnedir()
                elif userChoice == "3":
                    createSpecFile()
                
                print("\n" + "=" * 60)
                print("Build process completed successfully!")
                print("=" * 60)
                break  # Exit after successful build
            else:
                print("Invalid option. Please try again.")
            
    except KeyboardInterrupt:
        print("\n[EXIT] Build cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}")
        sys.exit(1)


if __name__ == "__main__":
    update_deps.updateAllDeps()
    main()