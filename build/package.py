#!/usr/bin/env python3
"""
Desktop Sorter Packaging Script
PyInstaller wrapper for building Windows executables
"""

import argparse
import pathlib
import shutil
import sys
import os
from typing import Optional

try:
    from PyInstaller.__main__ import run as pyinstaller_run
except ImportError:
    print("ERROR: PyInstaller not installed. Run: pip install pyinstaller")
    sys.exit(1)

# Project paths
ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = ROOT / "build" / "DesktopSorter.spec"
BUILD_ROOT = ROOT / "build"
DIST = BUILD_ROOT / "dist"  # PyInstaller creates dist under build/ since spec is there
WORKPATH = BUILD_ROOT / "pyinstaller"


def get_tkdnd_resource_path() -> Optional[str]:
    """
    Locate the tkinterdnd2 native library directory for Windows x64.
    Returns the path to the tkdnd win-x64 directory that contains the DLLs and TCL files.
    """
    try:
        import tkinterdnd2
        tkdnd_base = pathlib.Path(tkinterdnd2.__file__).parent / "tkdnd"

        # Look for Windows x64 directory
        win_x64_path = tkdnd_base / "win-x64"
        if win_x64_path.exists() and win_x64_path.is_dir():
            return str(win_x64_path)

        # Fallback: look for any Windows directory
        for candidate in ["win-x64", "win-x86", "win-arm64"]:
            candidate_path = tkdnd_base / candidate
            if candidate_path.exists() and candidate_path.is_dir():
                print(f"WARNING: Using {candidate} instead of win-x64 for tkdnd resources")
                return str(candidate_path)

        print("ERROR: No Windows tkdnd directory found in tkinterdnd2 package")
        return None

    except ImportError:
        print("ERROR: tkinterdnd2 not installed. Run: pip install tkinterdnd2")
        return None
    except Exception as e:
        print(f"ERROR: Failed to locate tkdnd resources: {e}")
        return None


def clean_build():
    """Remove build artifacts"""
    print("Cleaning build artifacts...")

    # Remove dist and workpath directories
    for path in [DIST, WORKPATH]:
        if path.exists():
            print(f"  Removing: {path}")
            shutil.rmtree(path, ignore_errors=True)

    # Legacy cleanup: remove old top-level dist if it exists
    legacy_dist = ROOT / "dist"
    if legacy_dist.exists() and legacy_dist != DIST:
        print(f"  WARNING: Found unexpected dist directory at {legacy_dist}")
        print("  This indicates a packaging misconfiguration. Removing it.")
        print(f"  Removing legacy dist: {legacy_dist}")
        shutil.rmtree(legacy_dist, ignore_errors=True)

    # Remove other generated items inside build/ except tracked files
    if BUILD_ROOT.exists():
        for entry in BUILD_ROOT.iterdir():
            if entry.name in {"package.py", "DesktopSorter.spec"}:
                continue
            if entry.is_dir():
                print(f"  Removing directory: {entry}")
                shutil.rmtree(entry, ignore_errors=True)
            else:
                print(f"  Removing file: {entry}")
                entry.unlink(missing_ok=True)

    # Remove any standalone spec-generated files in root
    for pattern in ["DesktopSorter.spec", "DesktopSorter.exe"]:
        for match in ROOT.glob(pattern):
            if match.is_file():
                print(f"  Removing: {match}")
                match.unlink()

    print("Clean complete.")


def build_package():
    """Build the application package using PyInstaller"""
    print("Building Desktop Sorter package...")

    # Verify spec file exists
    if not SPEC.exists():
        print(f"ERROR: PyInstaller spec file not found: {SPEC}")
        print("Make sure DesktopSorter.spec exists in the build/ directory")
        return False

    # Verify tkdnd resources
    tkdnd_path = get_tkdnd_resource_path()
    if not tkdnd_path:
        print("ERROR: Cannot locate tkinterdnd2 native resources")
        return False

    print(f"Using tkdnd resources from: {tkdnd_path}")

    # Set environment variable for the spec file
    os.environ['TKDND_PATH'] = tkdnd_path

    try:
        # Run PyInstaller with the spec file
        args = [
            "--clean",
            "--noconfirm",
            "--workpath", str(WORKPATH),
            "--distpath", str(DIST),
            str(SPEC)
        ]

        print(f"Running PyInstaller with: {' '.join(args)}")
        pyinstaller_run(args)

        # Check if build succeeded
        exe_path = DIST / "DesktopSorter" / "DesktopSorter.exe"
        if exe_path.exists():
            print(f"SUCCESS: Package built at {exe_path}")
            print(f"Distribution directory: {DIST / 'DesktopSorter'}")
            return True
        else:
            legacy_dist = ROOT / "dist"
            legacy_exe = legacy_dist / "DesktopSorter" / "DesktopSorter.exe"

            if legacy_exe.exists():
                print(
                    "WARNING: PyInstaller emitted artifacts under root dist/ despite "
                    "--distpath. Relocating to build/dist."
                )

                # Ensure destination parent exists
                DIST.mkdir(parents=True, exist_ok=True)

                legacy_app_dir = legacy_exe.parent
                destination_dir = DIST / legacy_exe.parent.name

                if destination_dir.exists():
                    shutil.rmtree(destination_dir, ignore_errors=True)

                shutil.move(str(legacy_app_dir), str(destination_dir))

                # Clean up empty legacy dist directory if possible
                try:
                    shutil.rmtree(legacy_dist, ignore_errors=True)
                except Exception:
                    pass

                exe_path = destination_dir / "DesktopSorter.exe"

            if exe_path.exists():
                print(f"SUCCESS: Package built at {exe_path}")
                print(f"Distribution directory: {exe_path.parent}")
                return True

            print(
                "ERROR: Build completed but executable not found at expected location: "
                f"{exe_path}"
            )

            if legacy_exe.exists():
                print(
                    "  Note: After relocation attempt, an executable remains in root dist/. "
                    "Manual investigation recommended."
                )

            return False

    except Exception as e:
        print(f"ERROR: PyInstaller build failed: {e}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Desktop Sorter packaging script for Windows"
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="build",
        choices=["build", "clean"],
        help="Command to execute (default: build)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    print(f"Desktop Sorter Packaging Script")
    print(f"Project root: {ROOT}")
    print(f"Command: {args.command}")
    print()

    if args.command == "clean":
        clean_build()
        return 0
    elif args.command == "build":
        # Clean before build for consistency
        clean_build()
        print()

        success = build_package()
        return 0 if success else 1
    else:
        print(f"ERROR: Unknown command: {args.command}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
