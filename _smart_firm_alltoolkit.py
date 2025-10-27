#!/usr/bin/env python3
"""
Ultimate Firmware Kitchen - Complete Android ROM & Firmware Toolkit
Professional-grade ROM building, firmware modification, and device flashing

Complete feature set:
- AOSP/Custom ROM building from source or existing images
- Odin .tar.md5 firmware building (byte-exact)
- Boot image modification (kernel, ramdisk, cmdline)
- System/vendor/product customization
- APK decompile/recompile with signing
- OTA package creation
- Sparse image handling
- Super partition manipulation
- Binary modding tools (7z, zip, etc.)
- Heimdall/Odin flashing
- Project-based workflow
- Utilizes 30+ tools from tools/ folder

Author: Generated with Claude | License: MIT
"""

import os
import sys
import shutil
import hashlib
import struct
import tempfile
import subprocess
import threading
import json
import time
import re
from pathlib import Path
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font, simpledialog, scrolledtext
import ctypes # For checking admin privileges on Windows
import sys # For checking platform
import logging # Added for detailed startup logging
import traceback # Added for detailed exception logging
from datetime import datetime # Ensure datetime is imported for logging timestamps

# Configure a file handler for startup logging
startup_logger = logging.getLogger('startup_logger')
startup_logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('startup_debug.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
startup_logger.addHandler(file_handler)

# -------------------------
# Configuration & Constants
# -------------------------
APP_TITLE = "Smartphone Firmware Screws"
VERSION = "4.2.0"  # Updated for fixes
TOOLS_DIR = os.path.join(os.path.dirname(__file__), "tools")

COLORS = {
    'bg_primary': '#0a0e14',
    'bg_secondary': '#0d1117',
    'bg_tertiary': '#161b22',
    'bg_card': '#0f1419',
    'accent_blue': '#58a6ff',
    'accent_orange': '#f97316',
    'accent_green': '#3fb950',
    'accent_purple': '#a78bfa',
    'accent_red': '#f85149',
    'text_primary': '#e6edf3',
    'text_secondary': '#8b949e',
    'text_tertiary': '#484f58',
    'border': '#30363d',
    'log_bg': '#010409',
    'log_fg': '#7ee787',
    'error': '#f85149',
    'warning': '#d29922',
    'success': '#3fb950',
}

TAR_BLOCK_SIZE = 512

# Common partition mappings for Samsung devices
SAMSUNG_PARTITION_MAP = {
    'bl1.bin': 'BL1',
    'bl2.bin': 'BL2',
    'bootloader.img': 'BOOTLOADER',
    'tzsw.img': 'TZSW',
    'cst.img': 'CST',
    'modem.bin': 'MODEM',
    'param.bin': 'PARAM',
    'boot.img': 'BOOT',
    'recovery.img': 'RECOVERY',
    'system.img': 'SYSTEM',
    'userdata.img': 'USERDATA',
    'cache.img': 'CACHE',
    'fota0.img': 'FOTA0',
    'fota1.img': 'FOTA1',
    'radio.img': 'RADIO',
    'vendor.img': 'VENDOR',
    'odm.img': 'ODM',
    'persist.img': 'PERSIST',
    # Add more as needed
}

# -------------------------
# Data Classes
# -------------------------
@dataclass
class Project:
    name: str
    path: str
    firmware_file: Optional[str] = None
    rom_dir: Optional[str] = None
    work_dir: Optional[str] = None
    replacements: Optional[Dict[str, str]] = None
    rom_config: Optional[Dict[str, Any]] = None
    created: str = ""
    modified: str = ""
    
    def __post_init__(self):
        if self.replacements is None:
            self.replacements = {}
        if self.rom_config is None:
            self.rom_config = {}
        if not self.created:
            self.created = datetime.now().isoformat()
        self.modified = datetime.now().isoformat()
    
    def save(self):
        os.makedirs(self.path, exist_ok=True)
        with open(os.path.join(self.path, "project.json"), "w") as f:
            json.dump(asdict(self), f, indent=2)
    
    @classmethod
    def load(cls, path: str):
        with open(os.path.join(path, "project.json"), "r") as f:
            data = json.load(f)
        return cls(**data)

# -------------------------
# Utility Functions
# -------------------------
def ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def tool_resolve(name: str) -> Optional[str]:
    """Resolve tool from ./tools/ then PATH with validation"""
    exts = ["", ".exe", ".jar", ".bat"] if sys.platform.startswith("win") else ["", ".jar"]

    # First check direct in TOOLS_DIR
    for ext in exts:
        candidate = os.path.join(TOOLS_DIR, name + ext)
        if os.path.exists(candidate) and os.path.isfile(candidate):
            if _is_valid_executable(candidate):
                return os.path.abspath(candidate)

    # Then recursively search subdirectories in TOOLS_DIR
    for root, dirs, files in os.walk(TOOLS_DIR):
        for file in files:
            if file == name or any(file == name + ext for ext in exts if ext):
                candidate = os.path.join(root, file)
                if os.path.isfile(candidate) and _is_valid_executable(candidate):
                    return os.path.abspath(candidate)

    # Special handling for tools that might be in subdirectories
    if name == "simg2img":
        # Check in boot_editor/tools/bin/
        candidate = os.path.join(TOOLS_DIR, "boot_editor", "tools", "bin", "simg2img.exe")
        if os.path.exists(candidate) and os.path.isfile(candidate):
            return os.path.abspath(candidate)
    elif name == "img2simg":
        # Check in boot_editor/tools/bin/
        candidate = os.path.join(TOOLS_DIR, "boot_editor", "tools", "bin", "img2simg.exe")
        if os.path.exists(candidate) and os.path.isfile(candidate):
            return os.path.abspath(candidate)
    elif name == "dtc":
        # Check in boot_editor/tools/bin/
        candidate = os.path.join(TOOLS_DIR, "boot_editor", "tools", "bin", "dtc.exe")
        if os.path.exists(candidate) and os.path.isfile(candidate):
            return os.path.abspath(candidate)

    # Finally check PATH
    for d in os.environ.get("PATH", "").split(os.pathsep):
        for ext in exts:
            candidate = os.path.join(d, name + ext)
            if os.path.exists(candidate) and os.path.isfile(candidate) and _is_valid_executable(candidate):
                return os.path.abspath(candidate)
    return None

def _is_valid_executable(path: str) -> bool:
    """Check if a file is a valid executable"""
    try:
        # Quick check: try to get file info
        with open(path, 'rb') as f:
            header = f.read(4)

        # Check for common executable signatures
        if sys.platform.startswith("win"):
            # Windows PE executable starts with 'MZ'
            if header.startswith(b'MZ'):
                return True
            # Also consider .exe files that might not have MZ header at the very beginning
            # or scripts that are meant to be executed directly (e.g., .bat, .cmd)
            if path.lower().endswith('.exe') or path.lower().endswith('.bat') or path.lower().endswith('.cmd'):
                return True
            return False # If it's not an exe/bat/cmd and doesn't have MZ, it's likely not a valid Win32 app
        else:
            # Unix/Linux: ELF executable starts with '\x7fELF'
            if header.startswith(b'\x7fELF'):
                return True
            # Could be a script (e.g., Python, Shell script)
            # Check for shebang or assume valid if it's not a known binary type
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                first_line = f.readline()
                if first_line.startswith('#!'):
                    return True
            return False # If it's not an ELF and not a script, it's likely not executable
    except (OSError, IOError):
        return False

def tool_resolve_apksigner() -> Optional[str]:
    """Resolve apksigner.jar from multiple possible locations."""
    # Primary location - check in java directory first
    apksigner_path = os.path.join(TOOLS_DIR, "java", "apksigner.jar")
    if os.path.exists(apksigner_path) and os.path.isfile(apksigner_path):
        return os.path.abspath(apksigner_path)

    # Alternative locations
    alt_paths = [
        os.path.join(TOOLS_DIR, "apksigner.jar"),
        os.path.join(TOOLS_DIR, "boot_editor", "aosp", "apksigner", "apksigner.jar"),
        os.path.join(TOOLS_DIR, "boot_editor", "apksigner.jar"),
    ]

    for path in alt_paths:
        if os.path.exists(path) and os.path.isfile(path):
            return os.path.abspath(path)

    # Check PATH
    for d in os.environ.get("PATH", "").split(os.pathsep):
        candidate = os.path.join(d, "apksigner.jar")
        if os.path.exists(candidate) and os.path.isfile(candidate):
            return os.path.abspath(candidate)

    return None

def run_cmd(cmd: List[str], cwd: Optional[str] = None, capture: bool = True,
            input_data: Optional[bytes] = None) -> subprocess.CompletedProcess:
    """Execute command with better error handling - NEVER raises exceptions"""
    try:
        return subprocess.run(
            cmd, cwd=cwd, capture_output=capture, text=False if input_data else True,
            input=input_data, check=False
        )
    except Exception as e:
        # Catch ALL exceptions and return a failed result instead of raising
        # This prevents any crashes from invalid executables or other issues
        result = subprocess.CompletedProcess(
            args=cmd,
            returncode=-1,
            stdout=b'' if not capture else None,
            stderr=str(e).encode() if capture else None
        )
        return result

def compute_md5(path: str, block_size: int = 1024*1024, length: Optional[int] = None) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        if length is None:
            length = os.path.getsize(path)
        remaining = length
        while remaining > 0:
            chunk_size = min(block_size, remaining)
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
            remaining -= len(chunk)
    return h.hexdigest().lower()

def read_bytes(path: str, offset: int = 0, length: Optional[int] = None) -> bytes:
    with open(path, "rb") as f:
        f.seek(offset)
        return f.read() if length is None else f.read(length)

def is_admin() -> bool:
    """Check if the current process is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def check_and_elevate():
    """Check admin status and elevate if needed, return True if we should continue."""
    if is_admin():
        print("Running with administrator privileges.")
        return True

    try:
        script = os.path.abspath(sys.argv[0])

        # Simple console prompt for admin elevation
        print("This application requires administrator privileges.")
        response = input("Restart with administrator privileges? (y/n): ").lower().strip()

        if response == 'y':
            result_code = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}"', None, 1)
            if result_code > 32:
                print("Restarting with administrator privileges...")
                sys.exit(0)  # Exit current process, new admin process will continue
            else:
                print("Failed to restart with administrator privileges.")
                return False
        else:
            print("Continuing without administrator privileges.")
            print("Warning: Device detection and flashing features may not work properly.")
            return True
    except Exception as e:
        print(f"Failed to check admin privileges: {e}")
        return False

def run_as_admin():
    """Restart the application with administrator privileges."""
    try:
        if sys.platform.startswith('win'):
            # Get the current script path
            script = os.path.abspath(sys.argv[0])
            # Use ShellExecute to run as admin
            result = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}"', None, 1)
            if result <= 32:  # Values <= 32 indicate failure
                return False
            sys.exit(0)  # Exit the current non-admin process
        else:
            # For non-Windows, assume it's already running with sufficient privileges
            return True
    except Exception as e:
        return False

# -------------------------
# TAR Operations
# -------------------------
def parse_tar_header(block: bytes) -> Optional[Dict[str, Any]]:
    """Parse 512-byte tar header"""
    if len(block) != TAR_BLOCK_SIZE or set(block) == {0}:
        return None
    
    try:
        name = block[0:100].rstrip(b'\x00').decode(errors='ignore')
        size_oct = block[124:136].rstrip(b'\x00').strip()
        size = int(size_oct or b'0', 8) if size_oct else 0
        typeflag = chr(block[156]) if block[156] else '0'
        prefix = block[345:500].rstrip(b'\x00').decode(errors='ignore')
        full_name = (prefix + "/" + name) if prefix else name
        
        return {
            'name': full_name,
            'size': size,
            'typeflag': typeflag,
            'raw_block': block
        }
    except Exception:
        return None

def list_tar_entries(tar_path: str) -> List[Tuple[str, int, int, int]]:
    """List TAR entries"""
    entries: List[Tuple[str, int, int, int]] = []
    with open(tar_path, "rb") as f:
        offset = 0
        while True:
            block = f.read(TAR_BLOCK_SIZE)
            if not block or len(block) < TAR_BLOCK_SIZE:
                break
            
            hdr = parse_tar_header(block)
            if not hdr:
                break
            
            entries.append((
                hdr['name'],
                offset,
                offset + TAR_BLOCK_SIZE,
                hdr['size']
            ))
            
            data_blocks = (hdr['size'] + TAR_BLOCK_SIZE - 1) // TAR_BLOCK_SIZE
            f.seek(data_blocks * TAR_BLOCK_SIZE, os.SEEK_CUR)
            offset = f.tell()
    
    return entries

def find_tar_entry(tar_path: str, target: str) -> Optional[Tuple[int, int, int]]:
    """Find entry and return offsets"""
    candidates = [target]
    if not target.startswith("./"):
        candidates.append("./" + target)
    else:
        candidates.append(target[2:])
    
    entries = list_tar_entries(tar_path)
    for name, hdr_off, data_off, size in entries:
        if name in candidates:
            return (hdr_off, data_off, size)
    return None

def replace_tar_entry_inplace(tar_path: str, entry_name: str, data: bytes,
                               pad_zeros: bool = True) -> None:
    """Replace TAR entry in-place and update MD5 if .tar.md5"""
    found = find_tar_entry(tar_path, entry_name)
    if not found:
        raise FileNotFoundError(f"Entry '{entry_name}' not found")
    
    hdr_off, data_off, orig_size = found
    
    if len(data) > orig_size:
        raise ValueError(
            f"Replacement size ({len(data)}) > original ({orig_size})"
        )
    
    if len(data) < orig_size:
        if pad_zeros:
            data = data + b'\x00' * (orig_size - len(data))
        else:
            raise ValueError("Replacement smaller and pad_zeros=False")
    
    with open(tar_path, "r+b") as f:
        f.seek(data_off)
        f.write(data)
    
    # If .tar.md5, update footer
    if tar_path.lower().endswith('.tar.md5'):
        full_size = os.path.getsize(tar_path)
        tar_length = full_size - 32
        if tar_length > 0 and full_size % 32 == 0:
            new_md5 = compute_md5(tar_path, length=tar_length)
            with open(tar_path, "r+b") as f:
                f.seek(tar_length)
                f.write(new_md5.encode('ascii'))

def extract_tar_entry(tar_path: str, entry_name: str, out_path: str) -> None:
    """Extract single TAR entry"""
    found = find_tar_entry(tar_path, entry_name)
    if not found:
        raise FileNotFoundError(f"Entry '{entry_name}' not found")
    
    _, data_off, size = found
    data = read_bytes(tar_path, data_off, size)
    with open(out_path, "wb") as f:
        f.write(data)

# -------------------------
# MD5 Footer Operations
# -------------------------
def strip_md5_footer(md5_path: str, tar_path: str) -> str:
    """
    Strip MD5 footer from a .tar.md5 file. This is a more robust implementation
    that reads the file from the end to find the MD5 hash.
    """
    md5_hex_str = None
    tar_size = 0

    with open(md5_path, 'rb') as f:
        # Seek to the end of the file
        f.seek(0, os.SEEK_END)
        file_size = f.tell()
        if file_size < 32:
            raise ValueError("File is too small to contain an MD5 footer.")

        # Read the file backwards in chunks to find the MD5
        chunk_size = 128
        buffer = b''
        for i in range(1, (file_size // chunk_size) + 2):
            offset = max(0, file_size - (i * chunk_size))
            f.seek(offset)
            chunk = f.read()
            buffer = chunk + buffer

            # Use regex to find the last 32-character hex string in the buffer
            matches = list(re.finditer(rb'([a-fA-F0-9]{32})', buffer))
            if matches:
                last_match = matches[-1]
                md5_hex_str = last_match.group(1).decode('ascii').lower()
                
                # The position of the MD5 is relative to the start of the buffer,
                # so we need to calculate its position in the original file.
                buffer_start_pos = offset
                md5_start_in_buffer = last_match.start()
                tar_size = buffer_start_pos + md5_start_in_buffer
                break
        
        if not md5_hex_str:
            raise ValueError("Could not find a valid MD5 footer in the file.")

        # Write the tar data to the output file
        f.seek(0)
        with open(tar_path, 'wb') as tar_file:
            # Read and write in chunks to handle large files
            remaining = tar_size
            while remaining > 0:
                read_size = min(1024 * 1024, remaining)
                tar_file.write(f.read(read_size))
                remaining -= read_size

    return md5_hex_str

def append_md5_footer(tar_path: str, out_md5: str) -> str:
    """Compute MD5 and append"""
    md5_hash = compute_md5(tar_path)
    
    with open(tar_path, "rb") as src, open(out_md5, "wb") as dst:
        shutil.copyfileobj(src, dst)
        dst.write(md5_hash.encode('ascii'))
    
    return md5_hash

def verify_tar_md5(md5_file: str) -> Tuple[bool, str]:
    """Verify MD5"""
    tmp = tempfile.mktemp(suffix=".tar")
    try:
        footer = strip_md5_footer(md5_file, tmp)
        computed = compute_md5(tmp)
        return (computed == footer.lower(), computed)
    finally:
        try:
            os.remove(tmp)
        except Exception:
            pass

# -------------------------
# ROM Building Operations
# -------------------------
def extract_system_image(system_img: str, out_dir: str) -> None:
    """Extract system.img using simg2img and mount"""
    ensure_dir(out_dir)
    
    # First convert sparse to raw if needed
    magic = read_bytes(system_img, 0, 4)
    if magic == b'\x3a\xff\x26\xed':  # Sparse image magic
        raw_img = tempfile.mktemp(suffix=".img")
        simg2img = tool_resolve("simg2img")
        if simg2img:
            result = run_cmd([simg2img, system_img, raw_img])
            if result.returncode == 0:
                system_img = raw_img
        else:
            raise FileNotFoundError("simg2img not found")
    
    # Extract using 7z or bsdtar
    seven_z = tool_resolve("7z")
    if seven_z:
        result = run_cmd([seven_z, "x", system_img, f"-o{out_dir}"])
        if result.returncode == 0:
            return
    
    bsdtar = tool_resolve("bsdtar")
    if bsdtar:
        result = run_cmd([bsdtar, "-xf", system_img, "-C", out_dir])
        if result.returncode == 0:
            return
    
    raise RuntimeError("Could not extract system image")

def build_rom_from_images(images_dir: str, out_zip: str,
                         rom_name: str = "CustomROM") -> None:
    """Build ROM ZIP from extracted images"""
    ensure_dir(os.path.dirname(out_zip))
    
    seven_z = tool_resolve("7z")
    if not seven_z:
        raise FileNotFoundError("Compression tool not found")
    
    # Create ROM structure
    rom_dir = tempfile.mkdtemp(prefix="rom_build_")
    
    # Copy build system files
    for item in os.listdir(images_dir):
        src = os.path.join(images_dir, item)
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(rom_dir, item))
        else:
            shutil.copy2(src, rom_dir)
    
    # Create META-INF if needed
    meta_dir = os.path.join(rom_dir, "META-INF", "com", "google", "android")
    ensure_dir(meta_dir)
    
    # Add placeholder updater-script (needs device-specific customization)
    with open(os.path.join(meta_dir, "updater-script"), "w") as f:
        f.write('ui_print("Installing Custom ROM...");\n')
        f.write('package_extract_dir("system", "/system");\n')
        f.write('ui_print("Installation complete");\n')
    
    # Compress with files at root
    result = run_cmd([seven_z, "a", "-tzip", out_zip, "."], cwd=rom_dir)
    
    shutil.rmtree(rom_dir, ignore_errors=True)
    
    if result.returncode != 0:
        raise RuntimeError("ROM build failed")

def modify_system_props(system_dir: str, properties: Dict[str, str]) -> None:
    """Modify system properties"""
    build_prop = os.path.join(system_dir, "build.prop")
    if not os.path.exists(build_prop):
        return
    
    with open(build_prop, "r") as f:
        lines = f.readlines()
    
    # Update existing or add new properties
    prop_dict = {}
    for line in lines:
        if "=" in line:
            key, val = line.split("=", 1)
            prop_dict[key.strip()] = val.strip()
    
    prop_dict.update(properties)
    
    with open(build_prop, "w") as f:
        for key, val in prop_dict.items():
            f.write(f"{key}={val}\n")

def create_keystore(keystore_path: str, key_alias: str, key_pass: str, store_pass: str,
                   dname: str = "CN=Android Debug,O=Android,C=US") -> None:
    """Create a new keystore with keytool"""
    keytool = tool_resolve("keytool")
    if not keytool:
        raise FileNotFoundError("keytool not found. Ensure Java JDK is installed.")

    cmd = [
        keytool, "-genkeypair",
        "-v",
        "-keystore", keystore_path,
        "-alias", key_alias,
        "-keyalg", "RSA",
        "-keysize", "2048",
        "-validity", "10000",
        "-storepass", store_pass,
        "-keypass", key_pass,
        "-dname", dname
    ]

    result = run_cmd(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"Keystore creation failed: {result.stderr.decode(errors='ignore')}")

def sign_apk_with_debug(apk_path: str) -> None:
    """Sign APK with Android debug keystore"""
    # Zipalign first
    zipalign = tool_resolve("zipalign")
    if zipalign:
        aligned = apk_path + ".aligned"
        result = run_cmd([zipalign, "-f", "4", apk_path, aligned])
        if result.returncode == 0:
            shutil.move(aligned, apk_path)
    else:
        raise FileNotFoundError("zipalign not found. Cannot align APK before signing.")

    apksigner_path = tool_resolve_apksigner()
    if not apksigner_path:
        # Fallback: try to use jarsigner from JDK if apksigner is not available
        jarsigner = tool_resolve("jarsigner")
        if jarsigner:
            return sign_apk_with_jarsigner(apk_path)
        raise FileNotFoundError("Neither apksigner.jar nor jarsigner found. Please ensure apksigner.jar is in the tools directory or install a JDK.")

    java_path = tool_resolve("java")
    if not java_path:
        raise FileNotFoundError("Java runtime not found to execute apksigner.jar. Ensure Java is installed and in PATH, or 'java.exe' is in the 'tools/' directory.")

    # Use Android's default debug keystore
    debug_keystore = os.path.join(os.path.expanduser("~"), ".android", "debug.keystore")
    if not os.path.exists(debug_keystore):
        # Create debug keystore if it doesn't exist
        ensure_dir(os.path.dirname(debug_keystore))
        create_keystore(debug_keystore, "androiddebugkey", "android", "android",
                       "CN=Android Debug,O=Android,C=US")

    # apksigner command with debug keystore
    cmd = [
        java_path, "-jar", apksigner_path, "sign",
        "--ks", debug_keystore,
        "--ks-key-alias", "androiddebugkey",
        "--ks-pass", "pass:android",
        apk_path
    ]

    result = run_cmd(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"APK signing failed: {result.stderr.decode(errors='ignore')}")

def sign_apk_with_jarsigner(apk_path: str) -> None:
    """Fallback signing using jarsigner from JDK"""
    jarsigner = tool_resolve("jarsigner")
    if not jarsigner:
        raise FileNotFoundError("jarsigner not found. Please install a JDK.")

    # Create a temporary debug keystore for jarsigner
    debug_keystore = os.path.join(tempfile.gettempdir(), "debug.keystore")
    try:
        # Create debug keystore
        create_keystore(debug_keystore, "androiddebugkey", "android", "android",
                       "CN=Android Debug,O=Android,C=US")

        # jarsigner command
        cmd = [
            jarsigner, "-verbose", "-sigalg", "SHA1withRSA", "-digestalg", "SHA1",
            "-keystore", debug_keystore,
            "-storepass", "android",
            "-keypass", "android",
            apk_path, "androiddebugkey"
        ]

        result = run_cmd(cmd)
        if result.returncode != 0:
            raise RuntimeError(f"APK signing with jarsigner failed: {result.stderr.decode(errors='ignore')}")

    finally:
        # Clean up temporary keystore
        try:
            os.remove(debug_keystore)
        except:
            pass

def sign_apk(apk_path: str, keystore: str, key_alias: str, key_pass: str) -> None:
    """Sign APK"""
    # Zipalign first
    zipalign = tool_resolve("zipalign")
    if zipalign:
        aligned = apk_path + ".aligned"
        result = run_cmd([zipalign, "-f", "4", apk_path, aligned])
        if result.returncode == 0:
            shutil.move(aligned, apk_path)
    else:
        raise FileNotFoundError("zipalign not found. Cannot align APK before signing.")

    apksigner_path = tool_resolve_apksigner()
    if not apksigner_path:
        raise FileNotFoundError("apksigner.jar not found. Ensure it's in 'tools/boot_editor/aosp/apksigner/'.")

    java_path = tool_resolve("java")
    if not java_path:
        raise FileNotFoundError("Java runtime not found to execute apksigner.jar. Ensure Java is installed and in PATH, or 'java.exe' is in the 'tools/' directory.")

    if not keystore:
        raise ValueError("Keystore path is required for signing.")

    # apksigner command
    cmd = [
        java_path, "-jar", apksigner_path, "sign",
        "--ks", keystore,
        "--ks-key-alias", key_alias,
        "--ks-pass", f"pass:{key_pass}",
        apk_path
    ]

    result = run_cmd(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"APK signing failed: {result.stderr.decode(errors='ignore')}")

def get_apktool_cmd(action: str, args: List[str]) -> List[str]:
    """Get command for apktool, handling wrapper or jar"""
    apktool_path = tool_resolve("apktool")
    if apktool_path:
        if apktool_path.lower().endswith('.jar'):
            java_path = tool_resolve("java")
            if not java_path:
                raise FileNotFoundError("Java runtime not found to execute apktool.jar. Ensure Java is installed and in PATH, or 'java.exe' is in the 'tools/' directory.")
            if not os.access(java_path, os.X_OK):
                raise PermissionError(f"Java executable '{java_path}' is not executable. Check file permissions.")
            return [java_path, "-jar", apktool_path, action] + args
        else: # Assume it's an executable like .exe or .bat
            if not os.access(apktool_path, os.X_OK):
                raise PermissionError(f"Apktool executable '{apktool_path}' is not executable. Check file permissions.")
            return [apktool_path, action] + args
    
    raise FileNotFoundError("apktool not found (neither apktool.exe nor apktool.jar with java). Ensure 'apktool.exe' or 'apktool.jar' is in the 'tools/' directory or in system PATH.")

def decompile_apk(apk_path: str, out_dir: str) -> None:
    """Decompile APK"""
    ensure_dir(out_dir) # Ensure output directory exists
    cmd = get_apktool_cmd("d", [apk_path, "-o", out_dir, "-f"])
    result = run_cmd(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"APK decompile failed: {result.stderr.decode(errors='ignore')}")

def recompile_apk(src_dir: str, out_apk: str, target_sdk: Optional[int] = None) -> None:
    """Recompile APK with proper compression settings for Android R+"""
    cmd = get_apktool_cmd("b", [src_dir, "-o", out_apk])

    # Use apktool with specific flags to ensure proper resource handling
    apktool_path = tool_resolve("apktool")
    if apktool_path and apktool_path.lower().endswith('.jar'):
        # For apktool.jar, use flags that help with Android R+ compatibility
        java_path = tool_resolve("java")
        if java_path:
            cmd = [java_path, "-jar", apktool_path, "b", src_dir, "-o", out_apk, "--use-aapt2"]
    else:
        # For executable apktool, use basic command
        cmd = get_apktool_cmd("b", [src_dir, "-o", out_apk])

    result = run_cmd(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"APK recompile failed: {result.stderr.decode(errors='ignore')}")

    # Post-process the APK to ensure resources.arsc is uncompressed and aligned
    fix_apk_compression(out_apk)

def unpack_boot_img(boot_img: str, out_dir: str) -> Dict[str, Any]:
    """Unpack boot image"""
    ensure_dir(out_dir)

    # Try magiskboot first
    magiskboot = tool_resolve("magiskboot")
    if magiskboot:
        boot_basename = os.path.basename(boot_img)
        dest_path = os.path.join(out_dir, boot_basename)
        # Normalize paths to handle different separators
        src_norm = os.path.normpath(os.path.abspath(boot_img))
        dst_norm = os.path.normpath(os.path.abspath(dest_path))
        if src_norm != dst_norm:
            shutil.copy2(boot_img, dest_path)  # Use copy2 to overwrite if exists
        result = run_cmd([magiskboot, "unpack", boot_basename], cwd=out_dir)
        if result.returncode == 0:
            return {'method': 'magiskboot', 'status': 'success'}

    # Try AIK as fallback
    aik = tool_resolve("unpackimg")
    if aik:
        result = run_cmd([aik, boot_img], cwd=out_dir)
        if result.returncode == 0:
            return {'method': 'AIK', 'status': 'success'}

    # If both fail, try a simple extraction method using 7z/bsdtar
    seven_z = tool_resolve("7z")
    if seven_z:
        result = run_cmd([seven_z, "x", boot_img, f"-o{out_dir}"])
        if result.returncode == 0:
            return {'method': '7z', 'status': 'success'}

    bsdtar = tool_resolve("bsdtar")
    if bsdtar:
        result = run_cmd([bsdtar, "-xf", boot_img, "-C", out_dir])
        if result.returncode == 0:
            return {'method': 'bsdtar', 'status': 'success'}

    raise RuntimeError("Boot image unpacker not found or all unpackers failed")

def repack_boot_img(work_dir: str, out_img: str) -> None:
    """Repack boot image"""
    magiskboot = tool_resolve("magiskboot")
    if magiskboot:
        result = run_cmd([magiskboot, "repack", "boot.img"], cwd=work_dir)
        if result.returncode == 0 and os.path.exists(os.path.join(work_dir, "new-boot.img")):
            shutil.copy(os.path.join(work_dir, "new-boot.img"), out_img)
            return
    
    raise RuntimeError("Boot repack failed")

def extract_kernel(boot_unpack_dir: str, out_path: str) -> None:
    """Extract kernel from unpacked boot directory"""
    kernel_path = os.path.join(boot_unpack_dir, "kernel")
    if not os.path.exists(kernel_path):
        raise FileNotFoundError("kernel not found in unpacked directory. Make sure you have unpacked a boot image first.")
    shutil.copy(kernel_path, out_path)

def extract_dtb(boot_unpack_dir: str, out_path: str) -> None:
    """Extract dtb from unpacked boot directory"""
    dtb_path = os.path.join(boot_unpack_dir, "dtb")
    if not os.path.exists(dtb_path):
        raise FileNotFoundError("dtb not found in unpacked directory. Make sure you have unpacked a boot image first.")
    shutil.copy(dtb_path, out_path)

def extract_ramdisk(cpio_file: str, out_dir: str) -> None:
    """Extract ramdisk"""
    ensure_dir(out_dir)
    
    work_file = cpio_file
    if cpio_file.lower().endswith('.lz4'):
        lz4 = tool_resolve("lz4")
        if lz4:
            work_file = tempfile.mktemp()
            result = run_cmd([lz4, "-d", "-f", cpio_file, work_file])
            if result.returncode != 0:
                raise RuntimeError("LZ4 decompress failed")
    
    bsdtar = tool_resolve("bsdtar")
    if bsdtar:
        result = run_cmd([bsdtar, "-xf", work_file, "-C", out_dir])
        if result.returncode == 0:
            return
    
    raise RuntimeError("Ramdisk extraction failed")

def create_ramdisk(src_dir: str, out_cpio: str, compress: bool = True) -> None:
    """Create ramdisk"""
    bsdtar = tool_resolve("bsdtar")
    if not bsdtar:
        raise FileNotFoundError("bsdtar not found")
    
    tmp_cpio = out_cpio if not compress else tempfile.mktemp()
    result = run_cmd([bsdtar, "-cf", tmp_cpio, "-C", src_dir, "."])
    if result.returncode != 0:
        raise RuntimeError("Ramdisk creation failed")
    
    if compress:
        lz4 = tool_resolve("lz4")
        if lz4:
            result = run_cmd([lz4, "-9", "-f", tmp_cpio, out_cpio])
            if result.returncode != 0:
                raise RuntimeError("LZ4 compression failed")
        try:
            os.remove(tmp_cpio)
        except Exception:
            pass

# -------------------------
# LZ4 Operations
# -------------------------
def lz4_decompress(src: str, dst: str, force: bool = True) -> None:
    """Decompress LZ4"""
    lz4 = tool_resolve("lz4")
    if not lz4:
        raise FileNotFoundError("lz4 not found")
    
    cmd = [lz4, "-d"]
    if force:
        cmd.append("-f")
    cmd.extend([src, dst])
    
    result = run_cmd(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"LZ4 decompress failed")

def lz4_compress(src: str, dst: str, level: int = 9, force: bool = True) -> None:
    """Compress LZ4"""
    lz4 = tool_resolve("lz4")
    if not lz4:
        raise FileNotFoundError("lz4 not found")
    
    cmd = [lz4]
    if force:
        cmd.append("-f")
    cmd.append(f"-{level}")
    cmd.extend([src, dst])
    
    result = run_cmd(cmd)
    if result.returncode != 0:
        raise RuntimeError(f"LZ4 compress failed")

# -------------------------
# Image Operations
# -------------------------
def sparse_to_raw(sparse_img: str, raw_img: str) -> None:
    """Convert sparse to raw"""
    simg2img = tool_resolve("simg2img")
    if not simg2img:
        raise FileNotFoundError("simg2img not found")
    
    result = run_cmd([simg2img, sparse_img, raw_img])
    if result.returncode != 0:
        raise RuntimeError("simg2img failed")

def raw_to_sparse(raw_img: str, sparse_img: str, block_size: int = 4096) -> None:
    """Convert raw to sparse"""
    img2simg = tool_resolve("img2simg")
    if not img2simg:
        raise FileNotFoundError("img2simg not found")

    result = run_cmd([img2simg, raw_img, sparse_img, str(block_size)])
    if result.returncode != 0:
        raise RuntimeError("img2simg failed")

def fix_apk_compression(apk_path: str) -> None:
    """Fix APK compression to ensure resources.arsc is uncompressed and aligned for Android R+"""
    temp_dir = tempfile.mkdtemp(prefix="apk_fix_")

    try:
        seven_z = tool_resolve("7z")
        if not seven_z:
            return  # Cannot fix without 7z

        # Extract APK contents
        result = run_cmd([seven_z, "x", apk_path, f"-o{temp_dir}"])
        if result.returncode != 0:
            return  # Skip if extraction fails

        # Check if resources.arsc exists
        resources_arsc = os.path.join(temp_dir, "resources.arsc")
        if not os.path.exists(resources_arsc):
            return  # No resources.arsc to fix

        # Remove original APK
        os.remove(apk_path)

        # Create exclusion list for resources.arsc (store uncompressed)
        exclude_file = os.path.join(temp_dir, "exclude.txt")
        with open(exclude_file, 'w') as f:
            f.write("resources.arsc\n")

        # First, add resources.arsc uncompressed
        result = run_cmd([
            seven_z, "a", "-tzip", "-mx=0", "-r", apk_path, "resources.arsc"
        ], cwd=temp_dir)

        if result.returncode == 0:
            # Then add everything else with compression, excluding resources.arsc
            result = run_cmd([
                seven_z, "a", "-tzip", "-mx=9", "-r", "-x@exclude.txt", apk_path, "."
            ], cwd=temp_dir)

        # Apply zipalign for proper alignment if available
        zipalign = tool_resolve("zipalign")
        if zipalign and os.path.exists(apk_path):
            aligned_apk = apk_path + ".aligned"
            result = run_cmd([zipalign, "-f", "4", apk_path, aligned_apk])
            if result.returncode == 0:
                import shutil
                shutil.move(aligned_apk, apk_path)
            else:
                try:
                    os.remove(aligned_apk)
                except:
                    pass

    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

# -------------------------
# Heimdall Flashing
# -------------------------
def heimdall_detect_device() -> bool:
    """Detect device"""
    heimdall = tool_resolve("heimdall")
    if not heimdall:
        return False
    
    result = run_cmd([heimdall, "detect"])
    return result.returncode == 0

def heimdall_flash(partition_map: Dict[str, str]) -> bool:
    """Flash via Heimdall"""
    heimdall = tool_resolve("heimdall")
    if not heimdall:
        raise FileNotFoundError("heimdall not found")
    
    cmd = [heimdall, "flash"]
    for partition, img_path in partition_map.items():
        cmd.extend([f"--{partition}", img_path])
    
    result = run_cmd(cmd, capture=False)
    return result.returncode == 0

# -------------------------
# GUI: Log Console
# -------------------------
class LogConsole(ttk.Frame):
    """Logging console"""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._build_ui()
    
    def _build_ui(self):
        toolbar = ttk.Frame(self)
        toolbar.pack(fill='x', padx=5, pady=2)
        
        ttk.Button(toolbar, text="Clear", command=self.clear).pack(side='left', padx=2)
        ttk.Button(toolbar, text="Save Log", command=self.save_log).pack(side='left', padx=2)
        
        self.text = tk.Text(self, wrap='word', height=12,
                           bg=COLORS['log_bg'], fg=COLORS['log_fg'],
                           font=('Consolas', 9))
        self.text.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.text.tag_config('error', foreground=COLORS['error'])
        self.text.tag_config('warning', foreground=COLORS['warning'])
        self.text.tag_config('success', foreground=COLORS['success'])
        self.text.tag_config('info', foreground=COLORS['log_fg'])
        
        vsb = ttk.Scrollbar(self.text, orient='vertical', command=self.text.yview)
        vsb.pack(side='right', fill='y')
        self.text.config(yscrollcommand=vsb.set)
    
    def log(self, msg: str, level: str = 'info'):
        timestamp = datetime.now().strftime('%H:%M:%S')
        full_msg = f"[{timestamp}] {msg}\n"
        self.text.insert(tk.END, full_msg, level)
        self.text.see(tk.END)
    
    def clear(self):
        self.text.delete('1.0', tk.END)
    
    def save_log(self):
        path = filedialog.asksaveasfilename(defaultextension=".log",
                                           filetypes=[("Log files", "*.log")])
        if path:
            with open(path, 'w') as f:
                f.write(self.text.get('1.0', tk.END))

# -------------------------
# GUI: Advanced Text Editor
# -------------------------
class AdvancedTextEditor(tk.Toplevel):
    """Advanced text editor with search and replace functionality"""
    def __init__(self, parent, initial_text: str = "", title: str = "Editor", callback=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("900x700")
        self.callback = callback
        self.current_match = None
        self.matches = []
        self.current_match_index = -1
        self._build_ui(initial_text)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _build_ui(self, initial_text):
        # Menu
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Save", command=self.save)
        file_menu.add_command(label="Save As...", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Close", command=self._on_close)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=lambda: self.text.event_generate("<<Undo>>"))
        edit_menu.add_command(label="Redo", command=lambda: self.text.event_generate("<<Redo>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", command=lambda: self.text.event_generate("<<Cut>>"))
        edit_menu.add_command(label="Copy", command=lambda: self.text.event_generate("<<Copy>>"))
        edit_menu.add_command(label="Paste", command=lambda: self.text.event_generate("<<Paste>>"))
        edit_menu.add_command(label="Select All", command=lambda: self.text.event_generate("<<SelectAll>>"))
        
        # Main text area
        frame = ttk.Frame(self)
        frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.text = scrolledtext.ScrolledText(frame, wrap='word', undo=True,
                                              font=('Consolas', 10))
        self.text.pack(fill='both', expand=True)
        self.text.insert('1.0', initial_text)
        
        # Search bar
        search_frame = ttk.Frame(self)
        search_frame.pack(fill='x', padx=5, pady=5)

        ttk.Label(search_frame, text="Find:").pack(side='left', padx=2)
        self.find_entry = ttk.Entry(search_frame, width=25)
        self.find_entry.pack(side='left', padx=2)
        self.find_entry.bind('<Return>', lambda e: self.find_next())

        ttk.Label(search_frame, text="Replace:").pack(side='left', padx=2)
        self.replace_entry = ttk.Entry(search_frame, width=25)
        self.replace_entry.pack(side='left', padx=2)

        # Options frame
        options_frame = ttk.Frame(search_frame)
        options_frame.pack(side='left', padx=5)

        self.case_sensitive_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Case", variable=self.case_sensitive_var).pack(side='top', anchor='w')

        self.whole_word_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Whole word", variable=self.whole_word_var).pack(side='top', anchor='w')

        self.regex_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text="Regex", variable=self.regex_var).pack(side='top', anchor='w')

        # Buttons frame
        buttons_frame = ttk.Frame(search_frame)
        buttons_frame.pack(side='left', padx=5)

        ttk.Button(buttons_frame, text="Find Next", command=self.find_next).pack(side='top', pady=1)
        ttk.Button(buttons_frame, text="Find Prev", command=self.find_prev).pack(side='top', pady=1)
        ttk.Button(buttons_frame, text="Replace", command=self.replace_current).pack(side='top', pady=1)
        ttk.Button(buttons_frame, text="Replace All", command=self.replace_all).pack(side='top', pady=1)

        # Status label
        self.search_status_label = ttk.Label(search_frame, text="")
        self.search_status_label.pack(side='right', padx=10)

        # Configure highlight tags
        self.text.tag_config("search_highlight", background="#FFFF00", foreground="#000000")  # Yellow highlight
        self.text.tag_config("current_match", background="#FFA500", foreground="#000000")     # Orange highlight for current
    
    def _find_matches(self, search_text):
        """Find all matches based on current options"""
        if not search_text:
            return []

        content = self.text.get("1.0", tk.END)
        flags = 0

        if not self.case_sensitive_var.get():
            flags |= re.IGNORECASE

        if self.whole_word_var.get():
            search_text = r'\b' + re.escape(search_text) + r'\b'

        if self.regex_var.get():
            try:
                pattern = re.compile(search_text, flags)
            except re.error:
                messagebox.showerror("Regex Error", "Invalid regular expression")
                return []
        else:
            pattern = re.compile(re.escape(search_text), flags)

        matches = []
        for match in pattern.finditer(content):
            matches.append((match.start(), match.end()))
        return matches

    def _highlight_matches(self):
        """Highlight all current matches"""
        # Clear previous highlights
        self.text.tag_remove("search_highlight", "1.0", tk.END)
        self.text.tag_remove("current_match", "1.0", tk.END)

        if not self.matches:
            return

        # Highlight all matches
        for start, end in self.matches:
            self.text.tag_add("search_highlight", f"1.0+{start}c", f"1.0+{end}c")

        # Highlight current match
        if self.current_match_index >= 0 and self.current_match_index < len(self.matches):
            start, end = self.matches[self.current_match_index]
            self.text.tag_add("current_match", f"1.0+{start}c", f"1.0+{end}c")
            self.text.see(f"1.0+{start}c")

    def find_next(self):
        search = self.find_entry.get()
        if not search:
            return

        # If this is a new search or no matches, find all matches
        if not self.matches or search != getattr(self, '_last_search', ''):
            self.matches = self._find_matches(search)
            self._last_search = search
            self.current_match_index = -1

        if not self.matches:
            self.search_status_label.config(text="No matches found")
            return

        # Move to next match
        self.current_match_index = (self.current_match_index + 1) % len(self.matches)
        self._highlight_matches()
        self.search_status_label.config(text=f"Match {self.current_match_index + 1} of {len(self.matches)}")

    def find_prev(self):
        search = self.find_entry.get()
        if not search:
            return

        # If this is a new search or no matches, find all matches
        if not self.matches or search != getattr(self, '_last_search', ''):
            self.matches = self._find_matches(search)
            self._last_search = search
            self.current_match_index = len(self.matches)  # Start from end

        if not self.matches:
            self.search_status_label.config(text="No matches found")
            return

        # Move to previous match
        self.current_match_index = (self.current_match_index - 1) % len(self.matches)
        self._highlight_matches()
        self.search_status_label.config(text=f"Match {self.current_match_index + 1} of {len(self.matches)}")

    def replace_current(self):
        if self.current_match_index < 0 or self.current_match_index >= len(self.matches):
            messagebox.showinfo("No Selection", "Please find a match first")
            return

        replace_with = self.replace_entry.get()
        start, end = self.matches[self.current_match_index]

        # Replace the current match
        self.text.delete(f"1.0+{start}c", f"1.0+{end}c")
        self.text.insert(f"1.0+{start}c", replace_with)

        # Update matches after replacement
        search = self.find_entry.get()
        self.matches = self._find_matches(search)

        # Adjust current index if needed
        if self.current_match_index >= len(self.matches):
            self.current_match_index = len(self.matches) - 1

        self._highlight_matches()
        if self.matches:
            self.search_status_label.config(text=f"Match {self.current_match_index + 1} of {len(self.matches)}")
        else:
            self.search_status_label.config(text="No matches found")

    def replace_all(self):
        search = self.find_entry.get()
        replace_with = self.replace_entry.get()
        if not search:
            return

        matches = self._find_matches(search)
        if not matches:
            self.search_status_label.config(text="No matches found")
            return

        # Replace all matches from end to beginning to maintain positions
        content = self.text.get("1.0", tk.END)
        new_content = content
        offset = 0

        for start, end in reversed(matches):
            actual_start = start + offset
            actual_end = end + offset
            new_content = new_content[:actual_start] + replace_with + new_content[actual_end:]
            offset += len(replace_with) - (end - start)

        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", new_content)

        # Clear highlights and reset
        self.matches = []
        self.current_match_index = -1
        self.text.tag_remove("search_highlight", "1.0", tk.END)
        self.text.tag_remove("current_match", "1.0", tk.END)
        self.search_status_label.config(text=f"Replaced {len(matches)} occurrence(s)")
    
    def save(self):
        if self.callback:
            self.callback(self.text.get("1.0", tk.END).strip())
        self.destroy()
    
    def save_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if path:
            with open(path, 'w') as f:
                f.write(self.text.get("1.0", tk.END))
    
    def _on_close(self):
        if self.callback:
            self.callback(None)  # Cancel
        self.destroy()

# -------------------------
# Main Application
# -------------------------
class UltimateFirmwareKitchen(tk.Tk):
    """Main application window"""
    def __init__(self):
        super().__init__()
        startup_logger.info("UltimateFirmwareKitchen: __init__ started.")
        self.title(f"{APP_TITLE} v{VERSION}")
        self.geometry("1400x900")
        self.configure(bg=COLORS['bg_primary'])
        
        self.current_project: Optional[Project] = None
        
        startup_logger.info("UltimateFirmwareKitchen: Calling _setup_style.")
        self._setup_style()
        startup_logger.info("UltimateFirmwareKitchen: Calling _build_menu.")
        self._build_menu()
        startup_logger.info("UltimateFirmwareKitchen: Calling _build_toolbar.")
        self._build_toolbar()
        startup_logger.info("UltimateFirmwareKitchen: Calling _build_workspace.")
        self._build_workspace()
        startup_logger.info("UltimateFirmwareKitchen: Calling _build_statusbar.")
        self._build_statusbar()
        
        self.bind('<Control-o>', lambda e: self.open_firmware())
        self.bind('<Control-s>', lambda e: self.save_project())
        self.bind('<Control-n>', lambda e: self.new_project())
        self.bind('<F5>', lambda e: self.refresh_tools())
        startup_logger.info("UltimateFirmwareKitchen: __init__ finished.")
    
    def _setup_style(self):
        startup_logger.debug("UltimateFirmwareKitchen: _setup_style started.")
        style = ttk.Style(self)
        style.theme_use('clam')
        
        style.configure('TFrame', background=COLORS['bg_card'])
        style.configure('TLabel', background=COLORS['bg_card'], foreground=COLORS['text_primary'])
        style.configure('TButton', background=COLORS['accent_blue'], foreground='white')
        style.map('TButton', background=[('active', COLORS['accent_orange'])])
        
        style.configure('Accent.TButton', background=COLORS['accent_orange'])
        style.configure('Success.TButton', background=COLORS['accent_green'])
        style.configure('Danger.TButton', background=COLORS['accent_red'])
        
        style.configure('Treeview', background=COLORS['bg_tertiary'],
                       foreground=COLORS['text_primary'],
                       fieldbackground=COLORS['bg_tertiary'])
        startup_logger.debug("UltimateFirmwareKitchen: _setup_style finished.")
    
    def _build_menu(self):
        startup_logger.debug("UltimateFirmwareKitchen: _build_menu started.")
        menubar = tk.Menu(self, bg=COLORS['bg_secondary'], fg=COLORS['text_primary'])
        self.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Project", command=self.new_project)
        file_menu.add_command(label="Open Project", command=self.open_project)
        file_menu.add_command(label="Save Project", command=self.save_project)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)
        
        rom_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="ROM Building", menu=rom_menu)
        rom_menu.add_command(label="Extract System Image", command=self.extract_system)
        rom_menu.add_command(label="Modify System Properties", command=self.modify_props)
        rom_menu.add_command(label="Decompile APK", command=self.decompile_apk_menu)
        rom_menu.add_command(label="Recompile APK", command=self.recompile_apk_menu)
        rom_menu.add_command(label="Sign APK", command=self.sign_apk_menu)
        rom_menu.add_command(label="Create Keystore", command=self.create_keystore_menu)
        rom_menu.add_separator()
        rom_menu.add_command(label="Extract Boot Image", command=self.extract_boot_menu)
        rom_menu.add_command(label="Extract Ramdisk", command=self.extract_ramdisk_menu)
        rom_menu.add_command(label="Create Ramdisk", command=self.create_ramdisk_menu)
        rom_menu.add_separator()
        rom_menu.add_command(label="Extract Kernel", command=self.extract_kernel_menu)
        rom_menu.add_command(label="Extract DTB", command=self.extract_dtb_menu)
        rom_menu.add_command(label="Repack Boot Image", command=self.repack_boot_img_menu) # Renamed for clarity
        rom_menu.add_separator()
        rom_menu.add_command(label="Build ROM ZIP", command=self.build_rom_menu)
        
        firmware_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Firmware", menu=firmware_menu)
        firmware_menu.add_command(label="Open .tar.md5", command=self.open_firmware)
        firmware_menu.add_command(label="Verify MD5", command=self.verify_md5)
        firmware_menu.add_command(label="Build .tar.md5", command=self.build_firmware)
        firmware_menu.add_separator()
        firmware_menu.add_command(label="Decompress LZ4", command=self.decompress_lz4)
        firmware_menu.add_command(label="Compress LZ4", command=self.compress_lz4)
        
        flash_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Flash", menu=flash_menu)
        flash_menu.add_command(label="Detect Device", command=self.detect_device)
        flash_menu.add_command(label="Flash via Heimdall", command=self.flash_heimdall)
        
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Tool Status", command=self.show_tool_status)
        tools_menu.add_command(label="Open Tools Folder", command=self.open_tools_folder)
        
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Split Horizontal", command=self.split_horizontal)
        view_menu.add_command(label="Split Vertical", command=self.split_vertical)
        view_menu.add_command(label="Close Pane", command=self.close_pane)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def _build_toolbar(self):
        toolbar = ttk.Frame(self, padding=5)
        toolbar.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(toolbar, text="🆕 New", command=self.new_project, width=10).pack(side='left', padx=2)
        ttk.Button(toolbar, text="📁 Open", command=self.open_firmware, width=10).pack(side='left', padx=2)
        ttk.Button(toolbar, text="💾 Save", command=self.save_project, width=10).pack(side='left', padx=2)
        
        ttk.Separator(toolbar, orient='vertical').pack(side='left', fill='y', padx=5)
        
        ttk.Button(toolbar, text="🔧 Build ROM", command=self.build_rom_menu, width=12,
                  style='Accent.TButton').pack(side='left', padx=2)
        ttk.Button(toolbar, text="⚙️ Build FW", command=self.build_firmware, width=12,
                  style='Accent.TButton').pack(side='left', padx=2)
        ttk.Button(toolbar, text="⚡ Flash", command=self.flash_heimdall, width=10,
                  style='Danger.TButton').pack(side='left', padx=2)
        
        ttk.Separator(toolbar, orient='vertical').pack(side='left', fill='y', padx=5)
        
        ttk.Button(toolbar, text="🔄 Refresh", command=self.refresh_tools, width=10).pack(side='left', padx=2)
        
        ttk.Label(toolbar, text="Tools:", font=('Segoe UI', 9, 'bold')).pack(side='right', padx=10)
        self.tool_status_label = ttk.Label(toolbar, text="⚠ Not checked", 
                                           foreground=COLORS['warning'])
        self.tool_status_label.pack(side='right')
        startup_logger.debug("UltimateFirmwareKitchen: _build_toolbar finished.")
    
    def _build_workspace(self):
        startup_logger.debug("UltimateFirmwareKitchen: _build_workspace started.")
        self.workspace = ttk.PanedWindow(self, orient='vertical')
        self.workspace.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Initial split: workspace and log
        self.main_pane = ttk.PanedWindow(self.workspace, orient='horizontal')
        self.workspace.add(self.main_pane, weight=3)
        
        # Log at bottom
        log_frame = ttk.LabelFrame(self.workspace, text="Activity Log", padding=5)
        self.workspace.add(log_frame, weight=1)
        
        self.log_console = LogConsole(log_frame)
        self.log_console.pack(fill='both', expand=True)
        startup_logger.debug("UltimateFirmwareKitchen: _build_workspace finished.")
        
        # Initial content in main pane
        self._add_notebook_to_pane(self.main_pane)
    
    def _add_notebook_to_pane(self, pane):
        startup_logger.debug("UltimateFirmwareKitchen: _add_notebook_to_pane started.")
        notebook = ttk.Notebook(pane)
        pane.add(notebook)
        
        # Firmware tab
        fw_frame = ttk.Frame(notebook)
        notebook.add(fw_frame, text="Firmware")
        self._build_firmware_ui(fw_frame)

        # ROM tab
        rom_frame = ttk.Frame(notebook)
        notebook.add(rom_frame, text="ROM Building")
        self._build_rom_ui(rom_frame)

        # File Editor tab
        file_editor_frame = ttk.Frame(notebook)
        notebook.add(file_editor_frame, text="File Editor")
        self._build_file_editor_ui(file_editor_frame)

        # Tools tab
        tools_frame = ttk.Frame(notebook)
        notebook.add(tools_frame, text="Tools")
        self._build_tools_ui(tools_frame)
    
    def split_horizontal(self):
        focused_widget = self.focus_get()
        if not focused_widget:
            return
        current_pane = focused_widget.master
        if isinstance(current_pane, ttk.Notebook):
            parent = current_pane.master
            if isinstance(parent, ttk.PanedWindow):
                new_pane = ttk.PanedWindow(parent, orient='horizontal')
                parent.add(new_pane)
                self._add_notebook_to_pane(new_pane)
    
    def split_vertical(self):
        focused_widget = self.focus_get()
        if not focused_widget:
            return
        current_pane = focused_widget.master
        if isinstance(current_pane, ttk.Notebook):
            parent = current_pane.master
            if isinstance(parent, ttk.PanedWindow):
                new_pane = ttk.PanedWindow(parent, orient='vertical')
                parent.add(new_pane)
                self._add_notebook_to_pane(new_pane)
    
    def close_pane(self):
        focused_widget = self.focus_get()
        if not focused_widget:
            return
        current_pane = focused_widget.master
        if isinstance(current_pane, ttk.Notebook):
            parent = current_pane.master
            if isinstance(parent, ttk.PanedWindow) and len(parent.panes()) > 1:
                parent.forget(current_pane)
    
    def _build_firmware_ui(self, parent):
        # Specific UI for firmware
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.fw_tree = ttk.Treeview(tree_frame, columns=('size', 'type'), 
                                    show='tree headings')
        self.fw_tree.heading('#0', text='Name')
        self.fw_tree.heading('size', text='Size')
        self.fw_tree.heading('type', text='Type')
        self.fw_tree.column('size', width=80)
        self.fw_tree.column('type', width=60)
        
        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=self.fw_tree.yview)
        vsb.pack(side='right', fill='y')
        self.fw_tree.config(yscrollcommand=vsb.set)
        self.fw_tree.pack(side='left', fill='both', expand=True)
        
        # Context menu
        self.fw_tree.bind("<Button-3>", self._fw_context_menu)
    
    def _fw_context_menu(self, event):
        item = self.fw_tree.identify_row(event.y)
        if item:
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Extract Selected", command=self.extract_selected_entries)
            menu.add_command(label="Replace Entry", command=self.replace_fw_entry)
            menu.post(event.x_root, event.y_root)
    
    def _build_rom_ui(self, parent):
        # Specific UI for ROM
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.rom_tree = ttk.Treeview(tree_frame, columns=('status',), 
                                     show='tree headings')
        self.rom_tree.heading('#0', text='Component')
        self.rom_tree.heading('status', text='Status')
        self.rom_tree.column('status', width=100)
        
        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=self.rom_tree.yview)
        vsb.pack(side='right', fill='y')
        self.rom_tree.config(yscrollcommand=vsb.set)
        self.rom_tree.pack(side='left', fill='both', expand=True)
        
        # Context menu
        self.rom_tree.bind("<Button-3>", self._rom_context_menu)
    
    def _rom_context_menu(self, event):
        item = self.rom_tree.identify_row(event.y)
        if item:
            menu = tk.Menu(self, tearoff=0)
            menu.add_command(label="Extract System", command=self.extract_system)
            menu.add_command(label="Extract Boot", command=self.extract_boot_menu)
            menu.add_command(label="Decompile APK", command=self.decompile_apk_menu)
            menu.add_command(label="Modify Properties", command=self.modify_props)
            menu.add_command(label="Build ROM ZIP", command=self.build_rom_menu)
            menu.post(event.x_root, event.y_root)
    
    def _build_file_editor_ui(self, parent):
        # Specific UI for decompiled APK viewer/editor
        self.file_editor_tree_frame = ttk.Frame(parent)
        self.file_editor_tree_frame.pack(side='left', fill='both', expand=False, padx=5, pady=5)

        # Toolbar for the tree
        tree_toolbar = ttk.Frame(self.file_editor_tree_frame)
        tree_toolbar.pack(fill='x', padx=2, pady=2)

        ttk.Button(tree_toolbar, text="📁 Set Base Folder", command=self._set_file_editor_base_folder).pack(side='left', padx=2)
        ttk.Button(tree_toolbar, text="🔄 Refresh", command=self._refresh_file_editor_tree).pack(side='left', padx=2)
        ttk.Button(tree_toolbar, text="📝 New File", command=self._create_new_file).pack(side='left', padx=2)

        self.file_editor_tree = ttk.Treeview(self.file_editor_tree_frame, show='tree')
        self.file_editor_tree.heading('#0', text='Files')
        self.file_editor_tree.pack(side='left', fill='both', expand=True)

        vsb_tree = ttk.Scrollbar(self.file_editor_tree_frame, orient='vertical', command=self.file_editor_tree.yview)
        vsb_tree.pack(side='right', fill='y')
        self.file_editor_tree.config(yscrollcommand=vsb_tree.set)

        self.file_editor_tree.bind("<Double-1>", self._on_file_editor_file_double_click)
        self.file_editor_tree.bind("<Button-3>", self._file_editor_context_menu)

        self.file_editor_frame = ttk.Frame(parent)
        self.file_editor_frame.pack(side='right', fill='both', expand=True, padx=5, pady=5)

        # Editor toolbar
        editor_toolbar = ttk.Frame(self.file_editor_frame)
        editor_toolbar.pack(fill='x', padx=2, pady=2)

        ttk.Button(editor_toolbar, text="💾 Save", command=self._save_current_file).pack(side='left', padx=2)
        ttk.Button(editor_toolbar, text="🔍 Find", command=self._show_find_dialog).pack(side='left', padx=2)
        ttk.Button(editor_toolbar, text="🔄 Reload", command=self._reload_current_file).pack(side='left', padx=2)
        ttk.Button(editor_toolbar, text="📋 Copy All", command=self._copy_all_to_clipboard).pack(side='left', padx=2)
        ttk.Button(editor_toolbar, text="📝 Notepad++", command=self._open_in_notepad_pp).pack(side='left', padx=2)

        # Font size controls
        ttk.Label(editor_toolbar, text="Font:").pack(side='right', padx=2)
        self.font_size_var = tk.StringVar(value="10")
        font_combo = ttk.Combobox(editor_toolbar, textvariable=self.font_size_var,
                                 values=["8", "9", "10", "11", "12", "14", "16", "18"],
                                 width=3, state="readonly")
        font_combo.pack(side='right', padx=2)
        font_combo.bind("<<ComboboxSelected>>", self._change_font_size)

        self.file_editor = scrolledtext.ScrolledText(self.file_editor_frame, wrap='word', undo=True,
                                                     font=('Consolas', 10),
                                                     bg=COLORS['log_bg'], fg=COLORS['log_fg'])
        self.file_editor.pack(fill='both', expand=True)

        # Comprehensive syntax highlighting tags for multiple languages
        # Keywords and control structures
        self.file_editor.tag_config('keyword', foreground='#CC7832', font=('Consolas', 10, 'bold'))  # Orange bold
        self.file_editor.tag_config('control', foreground='#CC7832', font=('Consolas', 10, 'italic'))  # Orange italic
        self.file_editor.tag_config('modifier', foreground='#CC7832')  # Orange

        # Data types and primitives
        self.file_editor.tag_config('datatype', foreground='#4E7BFF', font=('Consolas', 10, 'bold'))  # Blue bold
        self.file_editor.tag_config('primitive', foreground='#4E7BFF')  # Blue

        # Literals and values
        self.file_editor.tag_config('string', foreground='#6A8759')  # Green
        self.file_editor.tag_config('number', foreground='#6897BB')  # Blue
        self.file_editor.tag_config('boolean', foreground='#CC7832')  # Orange
        self.file_editor.tag_config('null', foreground='#CC7832')  # Orange

        # Identifiers and declarations
        self.file_editor.tag_config('class', foreground='#FFC66D', font=('Consolas', 10, 'bold'))  # Yellow bold
        self.file_editor.tag_config('interface', foreground='#FFC66D', font=('Consolas', 10, 'italic'))  # Yellow italic
        self.file_editor.tag_config('function', foreground='#A9B7C6', font=('Consolas', 10, 'bold'))  # Light Blue bold
        self.file_editor.tag_config('method', foreground='#A9B7C6')  # Light Blue
        self.file_editor.tag_config('variable', foreground='#9876AA')  # Purple
        self.file_editor.tag_config('constant', foreground='#9876AA', font=('Consolas', 10, 'bold'))  # Purple bold

        # Annotations and decorators
        self.file_editor.tag_config('annotation', foreground='#BBB529')  # Yellow-green
        self.file_editor.tag_config('decorator', foreground='#BBB529', font=('Consolas', 10, 'italic'))  # Yellow-green italic

        # Comments and documentation
        self.file_editor.tag_config('comment', foreground='#808080', font=('Consolas', 10, 'italic'))  # Grey italic
        self.file_editor.tag_config('docstring', foreground='#629755', font=('Consolas', 10, 'italic'))  # Green italic
        self.file_editor.tag_config('javadoc', foreground='#629755', font=('Consolas', 10, 'bold'))  # Green bold

        # Operators and symbols
        self.file_editor.tag_config('operator', foreground='#A9B7C6')  # Light Blue
        self.file_editor.tag_config('bracket', foreground='#A9B7C6', font=('Consolas', 10, 'bold'))  # Light Blue bold
        self.file_editor.tag_config('punctuation', foreground='#A9B7C6')  # Light Blue

        # Special Android/Smali constructs
        self.file_editor.tag_config('directive', foreground='#FFC66D', font=('Consolas', 10, 'bold'))  # Yellow bold
        self.file_editor.tag_config('register', foreground='#FF6B6B')  # Red
        self.file_editor.tag_config('opcode', foreground='#FF6B6B', font=('Consolas', 10, 'bold'))  # Red bold

        # XML/HTML tags (for Android manifests and layouts)
        self.file_editor.tag_config('xml_tag', foreground='#E8BF6A')  # Gold
        self.file_editor.tag_config('xml_attr', foreground='#BABABA')  # Light grey
        self.file_editor.tag_config('xml_value', foreground='#6A8759')  # Green

        # JSON keys and values
        self.file_editor.tag_config('json_key', foreground='#BABABA', font=('Consolas', 10, 'bold'))  # Light grey bold
        self.file_editor.tag_config('json_string', foreground='#6A8759')  # Green

        # Error and warning highlights
        self.file_editor.tag_config('error', background='#FF6B6B', foreground='white')  # Red background
        self.file_editor.tag_config('warning', background='#FFEB3B', foreground='black')  # Yellow background

        # Special highlighting for common patterns
        self.file_editor.tag_config('todo', background='#FF6B6B', foreground='white', font=('Consolas', 10, 'bold'))  # Red background bold
        self.file_editor.tag_config('fixme', background='#FF6B6B', foreground='white', font=('Consolas', 10, 'bold'))  # Red background bold
        self.file_editor.tag_config('hack', background='#FFEB3B', foreground='black', font=('Consolas', 10, 'italic'))  # Yellow background italic

        self.file_editor.bind("<KeyRelease>", self._on_editor_key_release)

        # Track current file
        self.current_file = None
        self.file_editor_base_folder = None

    def _on_editor_key_release(self, event):
        self._apply_syntax_highlighting()

    def _apply_syntax_highlighting(self):
        # Clear all existing tags
        for tag in self.file_editor.tag_names():
            if tag != 'sel':  # Don't remove selection tag
                self.file_editor.tag_remove(tag, '1.0', tk.END)

        content = self.file_editor.get('1.0', tk.END)

        # Determine file type from content for better highlighting
        file_ext = self._detect_file_type(content)

        if file_ext == 'smali':
            self._highlight_smali(content)
        elif file_ext == 'java':
            self._highlight_java(content)
        elif file_ext == 'xml':
            self._highlight_xml(content)
        elif file_ext == 'json':
            self._highlight_json(content)
        else:
            self._highlight_generic(content)

    def _detect_file_type(self, content: str) -> str:
        """Detect file type based on content patterns"""
        lines = content.split('\n')[:10]  # Check first 10 lines

        # Smali detection
        if any('.class' in line or '.method' in line or '.field' in line for line in lines):
            return 'smali'

        # XML detection
        if content.strip().startswith('<?xml') or content.strip().startswith('<'):
            return 'xml'

        # JSON detection
        if content.strip().startswith('{') or content.strip().startswith('['):
            try:
                json.loads(content)
                return 'json'
            except:
                pass

        # Java detection (basic)
        if any('public class' in line or 'package ' in line or 'import ' in line for line in lines):
            return 'java'

        return 'generic'

    def _highlight_smali(self, content: str):
        """Highlight Smali assembly code"""
        # Smali directives
        directives = ['.class', '.super', '.source', '.field', '.method', '.end method',
                     '.annotation', '.end annotation', '.param', '.end param', '.local',
                     '.end local', '.restart local', '.registers', '.locals', '.prologue',
                     '.line', '.catch', '.catchall', '.packed-switch', '.end packed-switch',
                     '.sparse-switch', '.end sparse-switch', '.array-data', '.end array-data']

        for directive in directives:
            for match in re.finditer(r'\b' + re.escape(directive) + r'\b', content):
                start, end = match.span()
                self.file_editor.tag_add('directive', f"1.0+{start}c", f"1.0+{end}c")

        # Registers (v0, v1, p0, etc.)
        for match in re.finditer(r'\b[vp]\d+\b', content):
            start, end = match.span()
            self.file_editor.tag_add('register', f"1.0+{start}c", f"1.0+{end}c")

        # Opcodes
        opcodes = ['nop', 'move', 'move-wide', 'move-object', 'move-result', 'move-result-wide',
                  'move-result-object', 'move-exception', 'return-void', 'return', 'return-wide',
                  'return-object', 'const', 'const-wide', 'const-string', 'const-string-jumbo',
                  'const-class', 'monitor-enter', 'monitor-exit', 'check-cast', 'instance-of',
                  'array-length', 'new-instance', 'new-array', 'filled-new-array', 'filled-new-array-range',
                  'fill-array-data', 'throw', 'goto', 'switch', 'cmp', 'if-', 'aget', 'aput',
                  'iget', 'iput', 'sget', 'sput', 'invoke', 'invoke-static', 'invoke-direct',
                  'invoke-virtual', 'invoke-super', 'invoke-interface', 'invoke-static-range',
                  'invoke-direct-range', 'invoke-virtual-range', 'invoke-super-range',
                  'invoke-interface-range', 'neg', 'not', 'add', 'sub', 'mul', 'div', 'rem',
                  'and', 'or', 'xor', 'shl', 'shr', 'ushr', 'add-int', 'sub-int', 'mul-int',
                  'div-int', 'rem-int', 'and-int', 'or-int', 'xor-int', 'shl-int', 'shr-int',
                  'ushr-int', 'add-long', 'sub-long', 'mul-long', 'div-long', 'rem-long',
                  'and-long', 'or-long', 'xor-long', 'shl-long', 'shr-long', 'ushr-long']

        for opcode in opcodes:
            for match in re.finditer(r'\b' + re.escape(opcode) + r'\b', content):
                start, end = match.span()
                self.file_editor.tag_add('opcode', f"1.0+{start}c", f"1.0+{end}c")

        # Comments (# style)
        for match in re.finditer(r'#.*', content):
            start, end = match.span()
            self.file_editor.tag_add('comment', f"1.0+{start}c", f"1.0+{end}c")

        # Strings
        for match in re.finditer(r'"[^"]*"', content):
            start, end = match.span()
            self.file_editor.tag_add('string', f"1.0+{start}c", f"1.0+{end}c")

        # Class names (Lpackage/ClassName;)
        for match in re.finditer(r'L[^;]+;', content):
            start, end = match.span()
            self.file_editor.tag_add('class', f"1.0+{start}c", f"1.0+{end}c")

    def _highlight_java(self, content: str):
        """Highlight Java source code"""
        # Keywords
        keywords = ['abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch', 'char',
                   'class', 'const', 'continue', 'default', 'do', 'double', 'else', 'enum',
                   'extends', 'final', 'finally', 'float', 'for', 'goto', 'if', 'implements',
                   'import', 'instanceof', 'int', 'interface', 'long', 'native', 'new',
                   'package', 'private', 'protected', 'public', 'return', 'short', 'static',
                   'strictfp', 'super', 'switch', 'synchronized', 'this', 'throw', 'throws',
                   'transient', 'try', 'void', 'volatile', 'while']

        for keyword in keywords:
            for match in re.finditer(r'\b' + re.escape(keyword) + r'\b', content):
                start, end = match.span()
                self.file_editor.tag_add('keyword', f"1.0+{start}c", f"1.0+{end}c")

        # Data types
        datatypes = ['boolean', 'byte', 'char', 'double', 'float', 'int', 'long', 'short', 'void']
        for dt in datatypes:
            for match in re.finditer(r'\b' + re.escape(dt) + r'\b', content):
                start, end = match.span()
                self.file_editor.tag_add('datatype', f"1.0+{start}c", f"1.0+{end}c")

        # Control structures
        controls = ['if', 'else', 'for', 'while', 'do', 'switch', 'case', 'default', 'try',
                   'catch', 'finally', 'break', 'continue', 'return', 'throw', 'throws']
        for ctrl in controls:
            for match in re.finditer(r'\b' + re.escape(ctrl) + r'\b', content):
                start, end = match.span()
                self.file_editor.tag_add('control', f"1.0+{start}c", f"1.0+{end}c")

        # Modifiers
        modifiers = ['public', 'private', 'protected', 'static', 'final', 'abstract', 'synchronized',
                    'native', 'strictfp', 'transient', 'volatile']
        for mod in modifiers:
            for match in re.finditer(r'\b' + re.escape(mod) + r'\b', content):
                start, end = match.span()
                self.file_editor.tag_add('modifier', f"1.0+{start}c", f"1.0+{end}c")

        # Literals
        for match in re.finditer(r'\b(true|false|null)\b', content):
            start, end = match.span()
            if match.group(1) in ['true', 'false']:
                self.file_editor.tag_add('boolean', f"1.0+{start}c", f"1.0+{end}c")
            else:
                self.file_editor.tag_add('null', f"1.0+{start}c", f"1.0+{end}c")

        # Class names (simple heuristic)
        for match in re.finditer(r'\b[A-Z][a-zA-Z0-9_]*\b', content):
            start, end = match.span()
            self.file_editor.tag_add('class', f"1.0+{start}c", f"1.0+{end}c")

        # Function/method names
        for match in re.finditer(r'\b[a-zA-Z_][a-zA-Z0-9_]*\s*\(', content):
            start = match.start()
            func_name = match.group().rstrip('(').strip()
            end = start + len(func_name)
            self.file_editor.tag_add('function', f"1.0+{start}c", f"1.0+{end}c")

        # Annotations
        for match in re.finditer(r'@\w+', content):
            start, end = match.span()
            self.file_editor.tag_add('annotation', f"1.0+{start}c", f"1.0+{end}c")

        # Comments
        for match in re.finditer(r'//.*|/\*[\s\S]*?\*/', content):
            start, end = match.span()
            self.file_editor.tag_add('comment', f"1.0+{start}c", f"1.0+{end}c")

        # Strings
        for match in re.finditer(r'"[^"]*"', content):
            start, end = match.span()
            self.file_editor.tag_add('string', f"1.0+{start}c", f"1.0+{end}c")

        # Numbers
        for match in re.finditer(r'\b\d+(\.\d+)?[fFdDlL]?\b', content):
            start, end = match.span()
            self.file_editor.tag_add('number', f"1.0+{start}c", f"1.0+{end}c")

    def _highlight_xml(self, content: str):
        """Highlight XML/HTML content"""
        # XML tags
        for match in re.finditer(r'</?[^>]+>', content):
            start, end = match.span()
            tag_content = match.group()
            self.file_editor.tag_add('xml_tag', f"1.0+{start}c", f"1.0+{end}c")

            # Attributes within tags
            attr_matches = re.finditer(r'(\w+)="([^"]*)"', tag_content)
            for attr_match in attr_matches:
                attr_start = start + attr_match.start(1)
                attr_end = start + attr_match.end(1)
                self.file_editor.tag_add('xml_attr', f"1.0+{attr_start}c", f"1.0+{attr_end}c")

                val_start = start + attr_match.start(2)
                val_end = start + attr_match.end(2)
                self.file_editor.tag_add('xml_value', f"1.0+{val_start}c", f"1.0+{val_end}c")

        # XML comments
        for match in re.finditer(r'<!--[\s\S]*?-->', content):
            start, end = match.span()
            self.file_editor.tag_add('comment', f"1.0+{start}c", f"1.0+{end}c")

        # XML processing instructions
        for match in re.finditer(r'<\?[\s\S]*?\?>', content):
            start, end = match.span()
            self.file_editor.tag_add('directive', f"1.0+{start}c", f"1.0+{end}c")

    def _highlight_json(self, content: str):
        """Highlight JSON content"""
        # JSON keys
        for match in re.finditer(r'"([^"]+)":', content):
            start, end = match.span()
            key_start = start + 1
            key_end = end - 2
            self.file_editor.tag_add('json_key', f"1.0+{key_start}c", f"1.0+{key_end}c")

        # JSON strings
        for match in re.finditer(r'"[^"]*"', content):
            start, end = match.span()
            self.file_editor.tag_add('json_string', f"1.0+{start}c", f"1.0+{end}c")

        # JSON numbers
        for match in re.finditer(r'\b\d+(\.\d+)?([eE][+-]?\d+)?\b', content):
            start, end = match.span()
            self.file_editor.tag_add('number', f"1.0+{start}c", f"1.0+{end}c")

        # JSON booleans and null
        for match in re.finditer(r'\b(true|false|null)\b', content):
            start, end = match.span()
            if match.group(1) in ['true', 'false']:
                self.file_editor.tag_add('boolean', f"1.0+{start}c", f"1.0+{end}c")
            else:
                self.file_editor.tag_add('null', f"1.0+{start}c", f"1.0+{end}c")

    def _highlight_generic(self, content: str):
        """Generic highlighting for unknown file types"""
        # Basic patterns that work for most text files

        # Comments (various styles)
        for match in re.finditer(r'#.*|//.*|/\*[\s\S]*?\*/', content):
            start, end = match.span()
            self.file_editor.tag_add('comment', f"1.0+{start}c", f"1.0+{end}c")

        # Strings
        for match in re.finditer(r'"[^"]*"|\'[^\']*\'', content):
            start, end = match.span()
            self.file_editor.tag_add('string', f"1.0+{start}c", f"1.0+{end}c")

        # Numbers
        for match in re.finditer(r'\b\d+(\.\d+)?\b', content):
            start, end = match.span()
            self.file_editor.tag_add('number', f"1.0+{start}c", f"1.0+{end}c")

        # TODO/FIXME/HACK markers
        for match in re.finditer(r'\b(TODO|FIXME|HACK)\b', content, re.IGNORECASE):
            start, end = match.span()
            tag_name = match.group(1).lower()
            self.file_editor.tag_add(tag_name, f"1.0+{start}c", f"1.0+{end}c")

        # Brackets and operators
        for match in re.finditer(r'[{}()\[\]]', content):
            start, end = match.span()
            self.file_editor.tag_add('bracket', f"1.0+{start}c", f"1.0+{end}c")

        for match in re.finditer(r'[+\-*/=<>!&|^%~?:;,.]', content):
            start, end = match.span()
            self.file_editor.tag_add('operator', f"1.0+{start}c", f"1.0+{end}c")

    def _open_file_editor_file_thread(self, file_path: str):
        """Thread to open and display file content."""
        try:
            self.after(0, lambda: self.status_label.config(text=f"Loading {os.path.basename(file_path)}..."))
            self.after(0, lambda: self.progress.start())

            # Read file in chunks to avoid UI freezing on large files
            content = ""
            chunk_size = 8192  # 8KB chunks
            file_size = os.path.getsize(file_path)

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                bytes_read = 0
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    content += chunk
                    bytes_read += len(chunk)

                    # Update progress for large files (>1MB)
                    if file_size > 1024 * 1024:
                        progress = int((bytes_read / file_size) * 100)
                        self.after(0, lambda p=progress: self.progress.config(value=p))

                    # Allow UI to remain responsive by yielding control
                    time.sleep(0.001)

            self.after(0, lambda: self._display_file_content(file_path, content))
            self.after(0, lambda: self.log(f"Opened file: {os.path.basename(file_path)} ({len(content)} chars)", 'info'))
        except Exception as e:
            self.after(0, lambda: self.log(f"Failed to open file {file_path}: {e}", 'error'))
        finally:
            self.after(0, lambda: self.status_label.config(text="Ready"))
            self.after(0, lambda: self.progress.stop())

    def _display_file_content(self, file_path: str, content: str):
        """Display file content in the editor."""
        self.file_editor.delete('1.0', tk.END)
        self.file_editor.insert('1.0', content)
        self.current_file = file_path
        self._apply_syntax_highlighting()
        self.log(f"File loaded: {os.path.basename(file_path)}", 'success')

    def _open_file_editor_entry(self, item_id):
        file_path = self.file_editor_tree.item(item_id, "values")[0]
        if os.path.isfile(file_path):
            # Check file size and warn for large files
            file_size = os.path.getsize(file_path)
            if file_size > 10 * 1024 * 1024:  # 10MB warning
                if not messagebox.askyesno("Large File Warning",
                    f"File is {file_size / (1024*1024):.1f} MB. Opening large files may be slow.\n\nContinue?"):
                    return

            # File opening is already threaded in the double-click handler
            self._open_file_editor_file_thread(file_path)
        else:
            self.log(f"Cannot open directory: {file_path}", 'warning')

    def _on_file_editor_file_double_click(self, event):
        item = self.file_editor_tree.selection()[0]
        if item:
            # Use threading to prevent UI freezing
            threading.Thread(target=self._open_file_editor_entry, args=(item,), daemon=True).start()

    def _set_file_editor_base_folder(self):
        """Set the base folder for file editing"""
        folder = filedialog.askdirectory(title="Select base folder for editing")
        if folder:
            self.file_editor_base_folder = folder
            self._populate_file_editor_tree(folder)
            self.log(f"Set base folder: {folder}", 'info')

    def _refresh_file_editor_tree(self):
        """Refresh the file tree"""
        if self.file_editor_base_folder and os.path.exists(self.file_editor_base_folder):
            self._populate_file_editor_tree(self.file_editor_base_folder)
            self.log("File tree refreshed", 'info')
        else:
            messagebox.showwarning("Warning", "No base folder set or folder doesn't exist")

    def _create_new_file(self):
        """Create a new file in the current base folder"""
        if not self.file_editor_base_folder:
            messagebox.showwarning("Warning", "Please set a base folder first")
            return

        filename = simpledialog.askstring("New File", "Enter filename:")
        if filename:
            filepath = os.path.join(self.file_editor_base_folder, filename)
            try:
                with open(filepath, 'w') as f:
                    f.write("")
                self._refresh_file_editor_tree()
                self.log(f"Created new file: {filename}", 'success')
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create file: {e}")

    def _save_current_file(self):
        """Save the current file being edited"""
        if not self.current_file:
            messagebox.showwarning("Warning", "No file is currently open")
            return

        try:
            self.status_label.config(text=f"Saving {os.path.basename(self.current_file)}...")
            self.progress.start()

            content = self.file_editor.get('1.0', tk.END).rstrip() + '\n'
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(content)

            self.log(f"Saved: {os.path.basename(self.current_file)}", 'success')
            self.status_label.config(text="Ready")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save file: {e}")
        finally:
            self.progress.stop()

    def _show_find_dialog(self):
        """Show find/replace dialog"""
        find_text = simpledialog.askstring("Find", "Enter text to find:")
        if find_text:
            replace_text = simpledialog.askstring("Replace", "Enter replacement text (leave empty to just find):")
            if replace_text is not None:  # Not cancelled
                self._find_and_replace(find_text, replace_text)

    def _find_and_replace(self, find_text: str, replace_text: str = ""):
        """Find and optionally replace text in the editor with improved functionality"""
        content = self.file_editor.get('1.0', tk.END)

        # Remove previous selection
        self.file_editor.tag_remove('sel', '1.0', tk.END)

        if not find_text:
            messagebox.showwarning("Warning", "Please enter text to find")
            return

        # Find all occurrences
        occurrences = []
        start = 0
        while True:
            idx = content.find(find_text, start)
            if idx == -1:
                break
            occurrences.append(idx)
            start = idx + 1

        if not occurrences:
            messagebox.showinfo("Not Found", f"'{find_text}' not found in the file")
            return

        if replace_text:
            # Replace all occurrences
            new_content = content.replace(find_text, replace_text)
            self.file_editor.delete('1.0', tk.END)
            self.file_editor.insert('1.0', new_content)
            self.log(f"Replaced {len(occurrences)} occurrence(s) of '{find_text}' with '{replace_text}'", 'info')
        else:
            # Just find - highlight first occurrence and show count
            start_idx = occurrences[0]
            end_idx = start_idx + len(find_text)
            self.file_editor.tag_add('sel', f'1.0+{start_idx}c', f'1.0+{end_idx}c')
            self.file_editor.see(f'1.0+{start_idx}c')
            self.log(f"Found {len(occurrences)} occurrence(s) of '{find_text}'", 'info')

    def _reload_current_file(self):
        """Reload the current file from disk"""
        if not self.current_file:
            messagebox.showwarning("Warning", "No file is currently open")
            return

        try:
            self.status_label.config(text=f"Reloading {os.path.basename(self.current_file)}...")
            self.progress.start()

            with open(self.current_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            self.file_editor.delete('1.0', tk.END)
            self.file_editor.insert('1.0', content)
            self._apply_syntax_highlighting()
            self.log(f"Reloaded: {os.path.basename(self.current_file)}", 'info')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to reload file: {e}")
        finally:
            self.status_label.config(text="Ready")
            self.progress.stop()

    def _copy_all_to_clipboard(self):
        """Copy all editor content to clipboard"""
        content = self.file_editor.get('1.0', tk.END).rstrip()
        self.clipboard_clear()
        self.clipboard_append(content)
        self.log("Content copied to clipboard", 'info')

    def _open_in_notepad_pp(self):
        """Open current file in Notepad++"""
        if not self.current_file:
            messagebox.showwarning("Warning", "No file is currently open")
            return

        try:
            notepad_pp = tool_resolve("notepad++")
            if notepad_pp:
                subprocess.Popen([notepad_pp, self.current_file])
                self.log(f"Opened in Notepad++: {os.path.basename(self.current_file)}", 'info')
            else:
                messagebox.showwarning("Notepad++ Not Found",
                    "Notepad++ is not available. Please ensure it's installed in the tools directory.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open in Notepad++: {e}")

    def _open_file_in_notepad_pp(self, file_path: str):
        """Open specific file in Notepad++"""
        try:
            notepad_pp = tool_resolve("notepad++")
            if notepad_pp:
                subprocess.Popen([notepad_pp, file_path])
                self.log(f"Opened in Notepad++: {os.path.basename(file_path)}", 'info')
            else:
                messagebox.showwarning("Notepad++ Not Found",
                    "Notepad++ is not available. Please ensure it's installed in the tools directory.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open in Notepad++: {e}")

    def _change_font_size(self, event=None):
        """Change the font size of the editor"""
        try:
            size = int(self.font_size_var.get())
            current_font = font.Font(font=self.file_editor['font'])
            current_font.configure(size=size)
            self.file_editor.configure(font=current_font)
            # Update syntax highlighting fonts
            for tag in self.file_editor.tag_names():
                if tag != 'sel':
                    current_tag_font = self.file_editor.tag_cget(tag, 'font')
                    if current_tag_font:
                        tag_font = font.Font(font=current_tag_font)
                        tag_font.configure(size=size)
                        self.file_editor.tag_config(tag, font=tag_font)
        except ValueError:
            pass

    def _file_editor_context_menu(self, event):
        item = self.file_editor_tree.identify_row(event.y)
        if item:
            file_path = self.file_editor_tree.item(item, "values")[0]
            menu = tk.Menu(self, tearoff=0)

            if os.path.isfile(file_path):
                menu.add_command(label="Open File", command=lambda: self._open_file_editor_entry(item))
                menu.add_command(label="Edit in External Editor", command=lambda: self._open_in_external_editor(file_path))
                menu.add_command(label="Edit in Notepad++", command=lambda: self._open_file_in_notepad_pp(file_path))
                menu.add_separator()
                menu.add_command(label="Copy File Path", command=lambda: self._copy_file_path(file_path))
                menu.add_command(label="Show in Explorer", command=lambda: self._show_in_explorer(file_path))
                menu.add_separator()
                menu.add_command(label="Delete File", command=lambda: self._delete_file(file_path))
            else:
                menu.add_command(label="Open Folder", command=lambda: self._open_folder(file_path))
                menu.add_command(label="Copy Folder Path", command=lambda: self._copy_file_path(file_path))
                menu.add_command(label="Show in Explorer", command=lambda: self._show_in_explorer(file_path))
                menu.add_separator()
                menu.add_command(label="Create Subfolder", command=lambda: self._create_subfolder(file_path))

            menu.add_separator()
            menu.add_command(label="Refresh Tree", command=self._refresh_file_editor_tree)
            menu.add_command(label="Set as Base Folder", command=self._set_file_editor_base_folder)
            menu.add_command(label="Decompile New APK", command=self.decompile_apk_menu)

            menu.post(event.x_root, event.y_root)

    def _open_in_external_editor(self, file_path: str):
        """Open file in external editor (Notepad++ if available, otherwise system default)"""
        try:
            # Try Notepad++ first if available
            notepad_pp = tool_resolve("notepad++")
            if notepad_pp:
                subprocess.Popen([notepad_pp, file_path])
                return

            # Fallback to system default
            if sys.platform.startswith('win'):
                os.startfile(file_path)
            else:
                subprocess.Popen(['xdg-open', file_path])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open in external editor: {e}")

    def _copy_file_path(self, file_path: str):
        """Copy file/folder path to clipboard"""
        self.clipboard_clear()
        self.clipboard_append(file_path)
        self.log(f"Copied path: {file_path}", 'info')

    def _show_in_explorer(self, file_path: str):
        """Show file/folder in system explorer"""
        try:
            if sys.platform.startswith('win'):
                subprocess.Popen(['explorer', '/select,', file_path])
            else:
                subprocess.Popen(['xdg-open', os.path.dirname(file_path)])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show in explorer: {e}")

    def _delete_file(self, file_path: str):
        """Delete a file after confirmation"""
        if messagebox.askyesno("Confirm Delete", f"Delete file '{os.path.basename(file_path)}'?"):
            try:
                os.remove(file_path)
                self._refresh_file_editor_tree()
                self.log(f"Deleted: {os.path.basename(file_path)}", 'warning')
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete file: {e}")

    def _open_folder(self, folder_path: str):
        """Open folder in system explorer"""
        try:
            if sys.platform.startswith('win'):
                os.startfile(folder_path)
            else:
                subprocess.Popen(['xdg-open', folder_path])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder: {e}")

    def _create_subfolder(self, parent_path: str):
        """Create a subfolder in the given path"""
        folder_name = simpledialog.askstring("New Folder", "Enter folder name:")
        if folder_name:
            new_path = os.path.join(parent_path, folder_name)
            try:
                os.makedirs(new_path, exist_ok=True)
                self._refresh_file_editor_tree()
                self.log(f"Created folder: {folder_name}", 'success')
            except Exception as e:
                messagebox.showerror("Error", f"Failed to create folder: {e}")

    def _populate_file_editor_tree(self, root_dir: str):
        self.file_editor_tree.delete(*self.file_editor_tree.get_children())
        self.file_editor_tree.insert('', 'end', text=os.path.basename(root_dir), iid=root_dir, open=True, values=(root_dir,))

        def insert_items(parent_id, path):
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    iid = self.file_editor_tree.insert(parent_id, 'end', text=item, iid=item_path, open=False, values=(item_path,))
                    insert_items(iid, item_path)
                else:
                    self.file_editor_tree.insert(parent_id, 'end', text=item, iid=item_path, values=(item_path,))

        insert_items(root_dir, root_dir)

    def _build_tools_ui(self, parent):
        # Specific UI for tools
        tree_frame = ttk.Frame(parent)
        tree_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.tools_tree = ttk.Treeview(tree_frame, columns=('path',), 
                                       show='tree headings')
        self.tools_tree.heading('#0', text='Tool')
        self.tools_tree.heading('path', text='Location')
        self.tools_tree.column('path', width=400)
        
        vsb = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tools_tree.yview)
        vsb.pack(side='right', fill='y')
        self.tools_tree.config(yscrollcommand=vsb.set)
        self.tools_tree.pack(side='left', fill='both', expand=True)
    
    def _build_statusbar(self):
        statusbar = ttk.Frame(self, relief='sunken')
        statusbar.pack(side='bottom', fill='x')
        
        self.status_label = ttk.Label(statusbar, text="Ready", anchor='w')
        self.status_label.pack(side='left', fill='x', expand=True, padx=5)
        
        self.progress = ttk.Progressbar(statusbar, length=200, mode='indeterminate')
        self.progress.pack(side='right', padx=5)
    
    # Logging
    def log(self, msg: str, level: str = 'info'):
        self.log_console.log(msg, level)
    
    # Project management
    def new_project(self):
        name = simpledialog.askstring("New Project", "Project name:")
        if not name:
            return
        
        path = filedialog.askdirectory(title="Select project directory")
        if not path:
            return
        
        project_path = os.path.join(path, name)
        self.current_project = Project(name=name, path=project_path)
        self.current_project.save()
        self.log(f"Created project: {name}", 'success')
        self.title(f"{APP_TITLE} - {name}")
    
    def open_project(self):
        path = filedialog.askdirectory(title="Select project directory")
        if not path:
            return
        
        try:
            self.current_project = Project.load(path)
            self.log(f"Opened project: {self.current_project.name}", 'success')
            self.title(f"{APP_TITLE} - {self.current_project.name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open project: {e}")
    
    def save_project(self):
        if not self.current_project:
            messagebox.showinfo("Info", "No project to save")
            return
        
        try:
            self.current_project.save()
            self.log(f"Saved project: {self.current_project.name}", 'success')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {e}")
    
    # Firmware operations
    def open_firmware(self):
        path = filedialog.askopenfilename(
            title="Open Firmware",
            filetypes=[("TAR MD5", "*.tar.md5"), ("TAR", "*.tar"), ("All", "*.*")]
        )
        if path:
            threading.Thread(target=self._load_firmware_thread, args=(path,),
                           daemon=True).start()

    def _load_firmware_thread(self, path: str):
        try:
            self.status_label.config(text="Loading firmware...")
            self.progress.start()

            work_tar = path
            is_md5 = path.lower().endswith('.tar.md5')
            if is_md5:
                tmp_tar = os.path.join(tempfile.gettempdir(),
                                      os.path.basename(path).replace('.tar.md5', '.tar'))
                strip_md5_footer(path, tmp_tar)
                work_tar = tmp_tar

            # Clear tree in main thread
            self.after(0, lambda: self.fw_tree.delete(*self.fw_tree.get_children()))

            entries = list_tar_entries(work_tar)

            # Update tree in main thread
            def update_tree():
                for name, _, _, size in entries:
                    self.fw_tree.insert('', 'end', text=name,
                                       values=(self._format_size(size), 'File'))

            self.after(0, update_tree)

            # Create project if none exists
            if not self.current_project:
                project_name = os.path.splitext(os.path.basename(path))[0]
                project_path = os.path.join(os.path.dirname(path), project_name)
                self.current_project = Project(name=project_name, path=project_path)
                self.current_project.save()
                self.title(f"{APP_TITLE} - {project_name}")

            self.current_project.firmware_file = path
            self.current_project.save()

            self.log(f"Loaded: {os.path.basename(path)}", 'success')
            self.status_label.config(text=f"Loaded: {os.path.basename(path)}")
        except Exception as e:
            self.log(f"Load failed: {e}", 'error')
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.progress.stop()
    
    def build_firmware(self):
        path = filedialog.askopenfilename(
            title="Select base .tar.md5",
            filetypes=[("TAR MD5", "*.tar.md5")]
        )
        if not path:
            return
        
        threading.Thread(target=self._build_firmware_thread, args=(path,), 
                        daemon=True).start()
    
    def _build_firmware_thread(self, firmware_path: str):
        try:
            self.status_label.config(text="Building firmware...")
            self.progress.start()
            self.log("Building firmware...", 'info')
            
            tmpdir = tempfile.mkdtemp(prefix="fwk_build_")
            base_tar = os.path.join(tmpdir, "base.tar")
            
            footer = strip_md5_footer(firmware_path, base_tar)
            self.log(f"Original MD5: {footer}", 'info')
            
            out_tar = os.path.join(tmpdir, "output.tar")
            shutil.copy(base_tar, out_tar)
            
            out_md5_path = os.path.join(tmpdir, "output.tar.md5")
            new_md5 = append_md5_footer(out_tar, out_md5_path)
            self.log(f"New MD5: {new_md5}", 'info')
            
            ok, computed = verify_tar_md5(out_md5_path)
            if not ok:
                raise RuntimeError(f"Verification failed")
            
            self.log("✓ Verification passed", 'success')
            
            default_name = os.path.basename(firmware_path).replace('.tar.md5', '_built.tar.md5')
            save_path = filedialog.asksaveasfilename(
                defaultextension=".tar.md5",
                initialfile=default_name,
                filetypes=[("TAR MD5", "*.tar.md5")]
            )
            
            if save_path:
                shutil.copy(out_md5_path, save_path)
                self.log(f"✓ Saved: {save_path}", 'success')
                messagebox.showinfo("Success", "Firmware built successfully!")
            
            self.status_label.config(text="Ready")
        except Exception as e:
            self.log(f"Build failed: {e}", 'error')
            messagebox.showerror("Error", str(e))
        finally:
            self.progress.stop()
    
    def verify_md5(self):
        path = filedialog.askopenfilename(
            title="Select file to verify",
            filetypes=[("TAR MD5", "*.tar.md5")]
        )
        if not path:
            return
        
        threading.Thread(target=self._verify_md5_thread, args=(path,),
                           daemon=True).start()

    def _verify_md5_thread(self, path: str):
        try:
            self.after(0, lambda: self.status_label.config(text="Verifying MD5..."))
            self.after(0, lambda: self.progress.start())
            self.log(f"Verifying MD5 for {os.path.basename(path)}...", 'info')

            ok, computed = verify_tar_md5(path)

            def update_ui():
                if ok:
                    self.log(f"✓ MD5 OK: {computed}", 'success')
                    messagebox.showinfo("Success", f"MD5 verified!\n\n{computed}")
                else:
                    self.log(f"✗ MD5 FAILED: {computed}", 'error')
                    messagebox.showerror("Failed", "MD5 verification failed!")
            
            self.after(0, update_ui)

        except Exception as e:
            self.log(f"Verify error: {e}", 'error')
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.after(0, lambda: self.status_label.config(text="Ready"))
            self.after(0, lambda: self.progress.stop())
    
    def decompress_lz4(self):
        src = filedialog.askopenfilename(filetypes=[("LZ4", "*.lz4")])
        if not src:
            return
        
        dst = filedialog.asksaveasfilename(
            initialfile=os.path.basename(src).replace('.lz4', '')
        )
        if not dst:
            return
        
        try:
            self.log("Decompressing LZ4...", 'info')
            lz4_decompress(src, dst)
            self.log("✓ Decompressed", 'success')
            messagebox.showinfo("Success", "Decompression complete!")
        except Exception as e:
            self.log(f"Failed: {e}", 'error')
            messagebox.showerror("Error", str(e))
    
    def compress_lz4(self):
        src = filedialog.askopenfilename()
        if not src:
            return
        
        dst = filedialog.asksaveasfilename(
            defaultextension=".lz4",
            initialfile=os.path.basename(src) + '.lz4'
        )
        if not dst:
            return
        
        try:
            self.log("Compressing LZ4...", 'info')
            lz4_compress(src, dst, level=9)
            self.log("✓ Compressed", 'success')
            ratio = (1 - os.path.getsize(dst) / os.path.getsize(src)) * 100
            messagebox.showinfo("Success", 
                f"Compression complete!\n\nRatio: {ratio:.1f}%")
        except Exception as e:
            self.log(f"Failed: {e}", 'error')
            messagebox.showerror("Error", str(e))
    
    # ROM operations
    def extract_system(self):
        system_img = filedialog.askopenfilename(
            title="Select system.img",
            filetypes=[("Image", "*.img")]
        )
        if not system_img:
            return
        
        out_dir = filedialog.askdirectory(title="Extract to")
        if not out_dir:
            return
        
        threading.Thread(target=self._extract_system_thread, 
                        args=(system_img, out_dir), daemon=True).start()
    
    def _extract_system_thread(self, img: str, out_dir: str):
        try:
            self.status_label.config(text="Extracting system...")
            self.log("Extracting system image...", 'info')
            extract_system_image(img, out_dir)
            self.log("✓ Extracted", 'success')
            messagebox.showinfo("Success", "System image extracted!")
        except Exception as e:
            self.log(f"Extract failed: {e}", 'error')
            messagebox.showerror("Error", str(e))
        finally:
            self.status_label.config(text="Ready")
    
    def extract_boot_menu(self):
        boot_img = filedialog.askopenfilename(
            title="Select boot.img",
            filetypes=[("Image", "*.img")]
        )
        if not boot_img:
            return

        out_dir = filedialog.askdirectory(title="Extract to")
        if not out_dir:
            return

        try:
            self.log("Unpacking boot image...", 'info')
            result = unpack_boot_img(boot_img, out_dir)
            self.log(f"✓ Unpacked ({result.get('method')})", 'success')
            messagebox.showinfo("Success", "Boot image unpacked!")
        except Exception as e:
            self.log(f"Unpack failed: {e}", 'error')
            messagebox.showerror("Error", str(e))

    def extract_kernel_menu(self):
        # Ask user whether to extract from boot.img or from already unpacked directory
        choice = messagebox.askyesnocancel(
            "Extract Kernel",
            "Do you want to extract kernel from a boot.img file?\n\n• Yes: Extract from boot.img\n• No: Extract from already unpacked boot directory\n• Cancel: Abort operation"
        )

        if choice is None:  # Cancel
            return
        elif choice:  # Yes - extract from boot.img
            boot_img = filedialog.askopenfilename(
                title="Select boot.img",
                filetypes=[("Boot Image", "*.img")]
            )
            if not boot_img:
                return

            out_file = filedialog.asksaveasfilename(
                defaultextension="",
                initialfile="kernel",
                filetypes=[("Kernel file", "*"), ("All files", "*.*")]
            )
            if not out_file:
                return

            try:
                self.log("Extracting kernel from boot.img...", 'info')
                # Create temporary directory for unpacking
                temp_dir = tempfile.mkdtemp(prefix="kernel_extract_")
                try:
                    result = unpack_boot_img(boot_img, temp_dir)
                    kernel_path = os.path.join(temp_dir, "kernel")
                    if os.path.exists(kernel_path):
                        # Wait a bit for file handles to be released
                        time.sleep(0.5)
                        # Try to read the file to ensure it's accessible
                        try:
                            with open(kernel_path, 'rb') as f:
                                f.read(1)
                        except PermissionError:
                            # If still locked, wait a bit more
                            time.sleep(1)
                        import shutil
                        shutil.copy2(kernel_path, out_file)
                        self.log("✓ Kernel extracted", 'success')
                        messagebox.showinfo("Success", f"Kernel extracted to:\n{out_file}")
                    else:
                        raise FileNotFoundError("Kernel file not found in unpacked boot image")
                finally:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                self.log(f"Kernel extraction failed: {e}", 'error')
                messagebox.showerror("Error", str(e))
        else:  # No - extract existing kernel file
            kernel_file = filedialog.askopenfilename(
                title="Select kernel file to extract contents from",
                filetypes=[("Kernel file", "*"), ("All files", "*.*")]
            )
            if not kernel_file:
                return

            out_dir = filedialog.askdirectory(title="Select output directory for extracted kernel contents")
            if not out_dir:
                return

            try:
                self.log("Extracting kernel contents...", 'info')

                # First, try to use extract-dtb to split kernel + appended DTBs
                try:
                    from extract_dtb import extract_dtb
                    import argparse

                    # Create args object for extract_dtb.split
                    args = argparse.Namespace()
                    args.filename = kernel_file
                    args.output_dir = out_dir
                    args.extract = True

                    # Call extract_dtb.split to extract kernel and DTBs
                    old_cwd = os.getcwd()
                    try:
                        os.chdir(out_dir)  # extract-dtb works relative to output dir
                        extract_dtb.split(args)
                    finally:
                        os.chdir(old_cwd)

                    self.log("✓ Kernel contents extracted using extract-dtb", 'success')
                    messagebox.showinfo("Success",
                        f"Kernel extraction complete!\n\n"
                        f"Output directory: {out_dir}\n\n"
                        "The extract-dtb tool has successfully extracted the kernel\n"
                        "and any appended DTB files. You can now edit the kernel source.")
                    return

                except ImportError:
                    self.log("extract-dtb not available, trying dtb-converter", 'warning')
                except Exception as e:
                    self.log(f"extract-dtb failed: {e}, trying dtb-converter", 'warning')

                # Try dtb-converter as alternative
                try:
                    dtb_converter_dir = os.path.join(TOOLS_DIR, "dtb-converter", "Superb_Extract-and_pack_dtb", "WorkDir")
                    dtb_converter_script = os.path.join(dtb_converter_dir, "extract-dtb.py")

                    if os.path.exists(dtb_converter_script):
                        # Run dtb-converter extract-dtb.py
                        cmd = [sys.executable, dtb_converter_script, kernel_file, "-o", out_dir]
                        result = run_cmd(cmd, cwd=dtb_converter_dir)

                        if result.returncode == 0:
                            self.log("✓ Kernel contents extracted using dtb-converter", 'success')
                            messagebox.showinfo("Success",
                                f"Kernel extraction complete!\n\n"
                                f"Output directory: {out_dir}\n\n"
                                "The dtb-converter tool has successfully extracted the kernel\n"
                                "and any appended DTB files. You can now edit the kernel source.")
                            return
                        else:
                            self.log(f"dtb-converter failed: {result.stderr.decode()}", 'warning')
                    else:
                        self.log("dtb-converter not found in tools directory", 'warning')

                except Exception as e:
                    self.log(f"dtb-converter failed: {e}, trying alternative methods", 'warning')

                # Fallback: Try to extract kernel contents using various tools
                success = False

                # Try using 7z to extract kernel contents (kernels can be archives)
                seven_z = tool_resolve("7z")
                if seven_z:
                    result = run_cmd([seven_z, "x", kernel_file, f"-o{out_dir}"])
                    if result.returncode == 0:
                        success = True
                        self.log("✓ Kernel contents extracted using 7z", 'success')

                # Try using bsdtar to extract kernel contents
                if not success:
                    bsdtar = tool_resolve("bsdtar")
                    if bsdtar:
                        result = run_cmd([bsdtar, "-xf", kernel_file, "-C", out_dir])
                        if result.returncode == 0:
                            success = True
                            self.log("✓ Kernel contents extracted using bsdtar", 'success')

                # Try using cpio (kernels are often cpio archives)
                if not success:
                    cpio = tool_resolve("cpio")
                    if cpio:
                        # Try to extract as cpio archive
                        import subprocess
                        try:
                            with open(kernel_file, 'rb') as f:
                                result = subprocess.run([cpio, "-i"], cwd=out_dir, stdin=f, capture_output=True)
                                if result.returncode == 0:
                                    success = True
                                    self.log("✓ Kernel contents extracted using cpio", 'success')
                        except:
                            pass

                # If extraction tools failed, try decompression as fallback
                if not success:
                    out_file = os.path.join(out_dir, "kernel_extracted")

                    # Check kernel file header to determine compression type
                    with open(kernel_file, 'rb') as f:
                        header = f.read(10)

                    # Try different decompression methods
                    if header.startswith(b'\x1f\x8b'):  # gzip
                        gzip_tool = tool_resolve("gzip")
                        if gzip_tool:
                            result = run_cmd([gzip_tool, "-dc", kernel_file], capture=False)
                            if result.returncode == 0:
                                with open(out_file, 'wb') as f:
                                    f.write(result.stdout)
                                success = True
                                self.log("✓ Kernel decompressed using gzip", 'success')

                    elif header.startswith(b'\x04\x22\x4d\x18'):  # LZ4
                        lz4_tool = tool_resolve("lz4")
                        if lz4_tool:
                            result = run_cmd([lz4_tool, "-d", "-f", kernel_file, out_file])
                            if result.returncode == 0:
                                success = True
                                self.log("✓ Kernel decompressed using LZ4", 'success')

                    elif header.startswith(b'\xfd\x37\x7a\x58\x5a\x00'):  # XZ
                        xz_tool = tool_resolve("xz")
                        if xz_tool:
                            result = run_cmd([xz_tool, "-dc", kernel_file], capture=False)
                            if result.returncode == 0:
                                with open(out_file, 'wb') as f:
                                    f.write(result.stdout)
                                success = True
                                self.log("✓ Kernel decompressed using XZ", 'success')

                    elif header.startswith(b'BZ'):  # BZIP2
                        bzcat_tool = tool_resolve("bzcat")
                        if bzcat_tool:
                            result = run_cmd([bzcat_tool, kernel_file], capture=False)
                            if result.returncode == 0:
                                with open(out_file, 'wb') as f:
                                    f.write(result.stdout)
                                success = True
                                self.log("✓ Kernel decompressed using BZIP2", 'success')

                # If all methods failed, copy the file as-is
                if not success:
                    import shutil
                    out_file = os.path.join(out_dir, os.path.basename(kernel_file))
                    shutil.copy2(kernel_file, out_file)
                    self.log("✓ Kernel file copied (could not extract contents)", 'warning')
                    messagebox.showinfo("Warning",
                        f"Kernel file copied to:\n{out_file}\n\n"
                        "Could not extract kernel contents automatically.\n"
                        "This kernel may be in a proprietary format or require\n"
                        "specific tools for your device.\n\n"
                        "For kernel modding, you typically need:\n"
                        "• Kernel source code for your device\n"
                        "• Cross-compiler toolchain\n"
                        "• Device-specific extraction tools")
                    return

                # Success message
                messagebox.showinfo("Success",
                    f"Kernel contents extracted to:\n{out_dir}\n\n"
                    "You can now examine and edit the kernel contents.\n"
                    "Look for source files, config files, and other kernel components.")

            except Exception as e:
                self.log(f"Kernel extraction failed: {e}", 'error')
                messagebox.showerror("Error", str(e))

    def extract_dtb_menu(self):
        # Ask user whether to extract from boot.img or from already unpacked directory
        choice = messagebox.askyesnocancel(
            "Extract DTB",
            "Do you want to extract DTB from a boot.img file?\n\n• Yes: Extract from boot.img\n• No: Extract from already unpacked boot directory\n• Cancel: Abort operation"
        )

        if choice is None:  # Cancel
            return
        elif choice:  # Yes - extract from boot.img
            boot_img = filedialog.askopenfilename(
                title="Select boot.img",
                filetypes=[("Boot Image", "*.img")]
            )
            if not boot_img:
                return

            out_file = filedialog.asksaveasfilename(
                defaultextension="",
                initialfile="dtb",
                filetypes=[("DTB file", "*"), ("All files", "*.*")]
            )
            if not out_file:
                return

            try:
                self.log("Extracting DTB from boot.img...", 'info')
                # Create temporary directory for unpacking
                temp_dir = tempfile.mkdtemp(prefix="dtb_extract_")
                try:
                    result = unpack_boot_img(boot_img, temp_dir)
                    dtb_path = os.path.join(temp_dir, "dtb")
                    if os.path.exists(dtb_path):
                        # Wait a bit for file handles to be released
                        time.sleep(0.5)
                        # Try to read the file to ensure it's accessible
                        try:
                            with open(dtb_path, 'rb') as f:
                                f.read(1)
                        except PermissionError:
                            # If still locked, wait a bit more
                            time.sleep(1)
                        import shutil
                        shutil.copy2(dtb_path, out_file)
                        self.log("✓ DTB extracted", 'success')
                        messagebox.showinfo("Success", f"DTB extracted to:\n{out_file}")
                    else:
                        raise FileNotFoundError("DTB file not found in unpacked boot image")
                finally:
                    import shutil
                    shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception as e:
                self.log(f"DTB extraction failed: {e}", 'error')
                messagebox.showerror("Error", str(e))
        else:  # No - extract existing DTB file
            dtb_file = filedialog.askopenfilename(
                title="Select DTB file to extract contents from",
                filetypes=[("DTB file", "*.dtb"), ("All files", "*.*")]
            )
            if not dtb_file:
                return

            out_dir = filedialog.askdirectory(title="Select output directory for extracted DTB contents")
            if not out_dir:
                return

            try:
                self.log("Extracting DTB contents...", 'info')

                # Try to decompile DTB to DTS using dtc if available
                dtc = tool_resolve("dtc")
                if dtc:
                    dts_file = os.path.join(out_dir, os.path.basename(dtb_file).replace('.dtb', '.dts'))
                    result = run_cmd([dtc, "-I", "dtb", "-O", "dts", "-o", dts_file, dtb_file])
                    if result.returncode == 0:
                        self.log("✓ DTB decompiled to DTS", 'success')
                        messagebox.showinfo("Success",
                            f"DTB contents extracted to DTS:\n{dts_file}\n\n"
                            "You can now edit the device tree source (.dts) file.\n"
                            "This contains the hardware configuration that you can modify\n"
                            "for kernel development and device customization.")
                        return

                # If dtc not available or failed, try dtb-converter if available
                try:
                    # Use the local dtb-converter tool from tools/dtb-converter/
                    dtb_converter_dir = os.path.join(TOOLS_DIR, "dtb-converter", "Superb_Extract-and_pack_dtb", "WorkDir")
                    dtb_converter_script = os.path.join(dtb_converter_dir, "extract-dtb.py")

                    if os.path.exists(dtb_converter_script):
                        # Run dtb-converter extract-dtb.py to convert DTB to DTS
                        cmd = [sys.executable, dtb_converter_script, dtb_file, "-o", out_dir]
                        result = run_cmd(cmd, cwd=dtb_converter_dir)

                        if result.returncode == 0:
                            self.log("✓ DTB converted to DTS using dtb-converter", 'success')
                            messagebox.showinfo("Success",
                                f"DTB contents extracted to DTS in:\n{out_dir}\n\n"
                                "You can now edit the device tree source (.dts) files.\n"
                                "Use dtb-converter pack-dtb.py to convert back to .dtb when done editing.")
                            return
                        else:
                            self.log(f"dtb-converter failed: {result.stderr.decode()}", 'warning')
                    else:
                        self.log("dtb-converter not found in tools directory", 'warning')

                except Exception as e:
                    self.log(f"dtb-converter failed: {e}", 'warning')

                # Try using 7z or bsdtar to extract DTB contents (some DTBs might be archives)
                success = False
                seven_z = tool_resolve("7z")
                if seven_z:
                    result = run_cmd([seven_z, "x", dtb_file, f"-o{out_dir}"])
                    if result.returncode == 0:
                        success = True
                        self.log("✓ DTB contents extracted using 7z", 'success')

                if not success:
                    bsdtar = tool_resolve("bsdtar")
                    if bsdtar:
                        result = run_cmd([bsdtar, "-xf", dtb_file, "-C", out_dir])
                        if result.returncode == 0:
                            success = True
                            self.log("✓ DTB contents extracted using bsdtar", 'success')

                if success:
                    messagebox.showinfo("Success",
                        f"DTB contents extracted to:\n{out_dir}\n\n"
                        "You can now examine and edit the DTB contents.\n"
                        "Look for device tree source files and configuration data.")
                    return

                # Fallback: Copy the DTB file itself for editing
                import shutil
                dtb_basename = os.path.basename(dtb_file)
                dest_path = os.path.join(out_dir, dtb_basename)
                shutil.copy2(dtb_file, dest_path)

                self.log("✓ DTB file copied (could not extract contents)", 'warning')
                messagebox.showinfo("Warning",
                    f"DTB file copied to:\n{dest_path}\n\n"
                    "Could not extract DTB contents automatically.\n"
                    "DTB files are usually binary blobs that need special tools.\n\n"
                    "For DTB editing, you need:\n"
                    "• Device tree compiler (dtc)\n"
                    "• DTB converter tools (roma21515/DTB-CONVERTER)\n"
                    "• Device-specific kernel source\n"
                    "• Understanding of device tree syntax")
                return

            except Exception as e:
                self.log(f"DTB extraction failed: {e}", 'error')
                messagebox.showerror("Error", str(e))


    def repack_boot_img_menu(self):
        work_dir = filedialog.askdirectory(title="Select unpacked boot directory")
        if not work_dir:
            return

        out_img = filedialog.asksaveasfilename(
            defaultextension=".img",
            initialfile="new-boot.img",
            filetypes=[("Boot Image", "*.img"), ("All files", "*.*")]
        )
        if not out_img:
            return

        # Check if output path would conflict with magiskboot's output
        out_dir = os.path.dirname(out_img)
        out_basename = os.path.basename(out_img)

        # Normalize paths for comparison
        work_dir_norm = os.path.normpath(work_dir)
        out_dir_norm = os.path.normpath(out_dir)

        if work_dir_norm == out_dir_norm and out_basename == "new-boot.img":
            messagebox.showerror("Error",
                "Cannot save to the same location as magiskboot's output.\n\n"
                "Please choose a different filename or directory.\n"
                "Magiskboot creates 'new-boot.img' in the work directory.")
            return

        try:
            self.log("Repacking boot image...", 'info')
            repack_boot_img(work_dir, out_img)
            self.log("✓ Boot image repacked", 'success')
            messagebox.showinfo("Success", f"Boot image repacked to:\n{out_img}")
        except Exception as e:
            self.log(f"Repack failed: {e}", 'error')
            messagebox.showerror("Error", str(e))
    
    def extract_ramdisk_menu(self):
        cpio = filedialog.askopenfilename(
            title="Select ramdisk",
            filetypes=[("CPIO/LZ4", "*.cpio;*.lz4")]
        )
        if not cpio:
            return
        
        out_dir = filedialog.askdirectory(title="Extract to")
        if not out_dir:
            return
        
        try:
            self.log("Extracting ramdisk...", 'info')
            extract_ramdisk(cpio, out_dir)
            self.log("✓ Extracted", 'success')
        except Exception as e:
            self.log(f"Extract failed: {e}", 'error')
            messagebox.showerror("Error", str(e))
    
    def create_ramdisk_menu(self):
        src_dir = filedialog.askdirectory(title="Select ramdisk source")
        if not src_dir:
            return
        
        out_file = filedialog.asksaveasfilename(
            defaultextension=".cpio.lz4",
            filetypes=[("CPIO LZ4", "*.cpio.lz4")]
        )
        if not out_file:
            return
        
        try:
            self.log("Creating ramdisk...", 'info')
            create_ramdisk(src_dir, out_file, compress=True)
            self.log("✓ Created", 'success')
        except Exception as e:
            self.log(f"Create failed: {e}", 'error')
            messagebox.showerror("Error", str(e))
    
    def decompile_apk_menu(self):
        apk = filedialog.askopenfilename(
            title="Select APK",
            filetypes=[("APK", "*.apk")]
        )
        if not apk:
            return
        
        out_dir = filedialog.askdirectory(title="Extract to")
        if not out_dir:
            return
        
        try:
            self.log("Decompiling APK...", 'info')
            # Get the command array to log it before execution
            cmd_to_log = get_apktool_cmd("d", [apk, "-o", out_dir, "-f"])
            self.log(f"Attempting to execute: {' '.join(cmd_to_log)}", 'info')
            self.log(f"Output directory: {out_dir}", 'info')
            decompile_apk(apk, out_dir)
            self.log("✓ Decompiled", 'success')
            messagebox.showinfo("Success", "APK decompiled!")
            self._populate_file_editor_tree(out_dir) # Populate the treeview with decompiled files
            # Switch to the File Editor tab
            for tab_id in self.main_pane.winfo_children():
                notebook = self.nametowidget(tab_id)
                if isinstance(notebook, ttk.Notebook):
                    for i, tab_text in enumerate(notebook.tab(tab_id, "text") for tab_id in notebook.tabs()):
                        if tab_text == "File Editor":
                            notebook.select(i)
                            break
                    break
        except RuntimeError as e:
            self.log(f"Decompile failed: {e}", 'error')
            messagebox.showerror("Error", str(e))
        except Exception as e:
            self.log(f"An unexpected error occurred during decompilation: {e}", 'error')
            messagebox.showerror("Error", str(e))

    def recompile_apk_menu(self):
        src_dir = filedialog.askdirectory(title="Select decompiled APK dir")
        if not src_dir:
            return
        
        out_apk = filedialog.asksaveasfilename(
            defaultextension=".apk",
            filetypes=[("APK", "*.apk")]
        )
        if not out_apk:
            return
        
        try:
            self.log("Recompiling APK...", 'info')
            recompile_apk(src_dir, out_apk)
            self.log("✓ Recompiled", 'success')
            
            if messagebox.askyesno("Sign APK?", "APK recompiled successfully. Do you want to sign it now?"):
                self.sign_apk_menu(apk_to_sign=out_apk)
            else:
                messagebox.showinfo("Success", "APK recompiled!")
        except Exception as e:
            self.log(f"Recompile failed: {e}", 'error')
            messagebox.showerror("Error", str(e))
    
    def create_keystore_menu(self):
        """Create a new keystore"""
        keystore_path = filedialog.asksaveasfilename(
            defaultextension=".jks",
            filetypes=[("Java Keystore", "*.jks"), ("Keystore", "*.keystore")]
        )
        if not keystore_path:
            return

        key_alias = simpledialog.askstring("Key Alias", "Enter key alias:", initialvalue="mykey")
        if not key_alias:
            return

        store_pass = simpledialog.askstring("Store Password", "Enter keystore password:", show='*')
        if not store_pass:
            return

        key_pass = simpledialog.askstring("Key Password", "Enter key password:", show='*')
        if not key_pass:
            return

        dname = simpledialog.askstring("Distinguished Name",
            "Enter distinguished name (leave empty for default):",
            initialvalue="CN=Android App,O=My Company,C=US")
        if dname is None:
            return
        if not dname.strip():
            dname = "CN=Android App,O=My Company,C=US"

        try:
            self.log("Creating keystore...", 'info')
            self.status_label.config(text="Creating keystore...")
            self.progress.start()

            create_keystore(keystore_path, key_alias, key_pass, store_pass, dname)
            self.log("✓ Keystore created successfully", 'success')
            messagebox.showinfo("Success", f"Keystore created at:\n{keystore_path}")
        except Exception as e:
            self.log(f"Keystore creation failed: {e}", 'error')
            messagebox.showerror("Error", str(e))
        finally:
            self.status_label.config(text="Ready")
            self.progress.stop()

    def sign_apk_menu(self, apk_to_sign: Optional[str] = None):
        apk_path = apk_to_sign
        if not apk_path:
            apk_path = filedialog.askopenfilename(
                title="Select APK to sign",
                filetypes=[("APK", "*.apk")]
            )
        if not apk_path:
            return

        # Ask user for signing method
        sign_methods = ["Debug signature (recommended)", "Custom keystore", "Cancel"]
        sign_method = messagebox.askyesnocancel(
            "Signing Method",
            "Choose APK signing method:\n\n• Debug signature: Quick, for testing\n• Custom keystore: Secure, for release\n\nWhich method would you like to use?",
            default=messagebox.YES
        )

        if sign_method is None or sign_method == False:  # Cancel
            return
        elif sign_method:  # Yes - debug signature
            try:
                self.log(f"Signing APK with debug key: {os.path.basename(apk_path)}...", 'info')
                self.status_label.config(text="Signing APK...")
                self.progress.start()

                sign_apk_with_debug(apk_path)
                self.log("✓ APK signed with debug key successfully", 'success')
                messagebox.showinfo("Success", "APK signed with Android debug key!\n\nNote: Debug-signed APKs should only be used for testing.")
            except Exception as e:
                self.log(f"APK signing failed: {e}", 'error')
                messagebox.showerror("Error", str(e))
            finally:
                self.status_label.config(text="Ready")
                self.progress.stop()
            return

        # No - custom keystore
        keystore_path = filedialog.askopenfilename(
            title="Select Keystore (.jks or .keystore)",
            filetypes=[("Keystore files", "*.jks *.keystore"), ("All files", "*.*")]
        )
        if not keystore_path:
            # Offer to create new keystore
            if messagebox.askyesno("Create Keystore?", "No keystore selected. Create a new one?"):
                self.create_keystore_menu()
                # After creating, ask again for keystore
                keystore_path = filedialog.askopenfilename(
                    title="Select the keystore you just created",
                    filetypes=[("Keystore files", "*.jks *.keystore"), ("All files", "*.*")]
                )
                if not keystore_path:
                    return
            else:
                return

        key_alias = simpledialog.askstring("Keystore Alias", "Enter keystore alias:")
        if not key_alias:
            return

        key_pass = simpledialog.askstring("Keystore Password", "Enter keystore password:", show='*')
        if not key_pass:
            return

        try:
            self.log(f"Signing APK: {os.path.basename(apk_path)}...", 'info')
            self.status_label.config(text="Signing APK...")
            self.progress.start()

            sign_apk(apk_path, keystore_path, key_alias, key_pass)
            self.log("✓ APK signed successfully", 'success')
            messagebox.showinfo("Success", "APK signed successfully!")
        except Exception as e:
            self.log(f"APK signing failed: {e}", 'error')
            messagebox.showerror("Error", str(e))
        finally:
            self.status_label.config(text="Ready")
            self.progress.stop()

    def modify_props(self):
        system_dir = filedialog.askdirectory(title="Select system directory")
        if not system_dir:
            return
        
        build_prop = os.path.join(system_dir, "build.prop")
        if not os.path.exists(build_prop):
            messagebox.showerror("Error", "build.prop not found")
            return
        
        with open(build_prop, "r") as f:
            initial_text = f.read()
        
        def apply_props(new_text):
            if new_text is None:
                return  # Cancelled
            props = {}
            for line in new_text.split('\n'):
                if '=' in line:
                    key, val = line.split('=', 1)
                    props[key.strip()] = val.strip()
            
            try:
                modify_system_props(system_dir, props)
                self.log("✓ Properties modified", 'success')
                messagebox.showinfo("Success", "Properties updated!")
            except Exception as e:
                messagebox.showerror("Error", str(e))
        
        AdvancedTextEditor(self, initial_text=initial_text, title="Modify Properties", callback=apply_props)
    
    def build_rom_menu(self):
        images_dir = filedialog.askdirectory(title="Select ROM source directory")
        if not images_dir:
            return
        
        out_zip = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP", "*.zip")]
        )
        if not out_zip:
            return
        
        threading.Thread(target=self._build_rom_thread, 
                        args=(images_dir, out_zip), daemon=True).start()
    
    def _build_rom_thread(self, src: str, out: str):
        try:
            self.status_label.config(text="Building ROM...")
            self.progress.start()
            self.log("Building ROM ZIP...", 'info')
            build_rom_from_images(src, out, "CustomROM")
            self.log("✓ ROM built", 'success')
            messagebox.showinfo("Success", "ROM ZIP created! Note: Updater-script is placeholder, customize for your device.")
            self.status_label.config(text="Ready")
        except Exception as e:
            self.log(f"Build failed: {e}", 'error')
            messagebox.showerror("Error", str(e))
        finally:
            self.progress.stop()
    
    # Firmware entries
    def extract_selected_entries(self):
        selected_items = self.fw_tree.selection()
        if not selected_items:
            messagebox.showinfo("Info", "Select one or more entries")
            return

        if not self.current_project or not self.current_project.firmware_file:
            messagebox.showerror("Error", "No firmware file loaded in the current project.")
            return

        out_dir = filedialog.askdirectory(title="Select output directory")
        if not out_dir:
            return

        threading.Thread(target=self._extract_selected_thread,
                        args=(selected_items, out_dir), daemon=True).start()

    def _extract_selected_thread(self, selected_items, out_dir):
        try:
            self.status_label.config(text=f"Extracting {len(selected_items)} entries...")
            self.progress.start()

            if not self.current_project or not self.current_project.firmware_file:
                self.after(0, lambda: messagebox.showerror("Error", "No firmware file loaded"))
                return

            firmware_file = self.current_project.firmware_file
            work_tar = firmware_file
            is_md5 = firmware_file.lower().endswith('.tar.md5')
            if is_md5:
                tmp_tar = os.path.join(tempfile.gettempdir(),
                                      os.path.basename(firmware_file).replace('.tar.md5', '.tar'))
                strip_md5_footer(firmware_file, tmp_tar)
                work_tar = tmp_tar

            extracted_count = 0
            for i, item in enumerate(selected_items):
                name = self.fw_tree.item(item, 'text')
                out_path = os.path.join(out_dir, os.path.basename(name))

                self.status_label.config(text=f"Extracting {name}... ({i+1}/{len(selected_items)})")

                try:
                    extract_tar_entry(work_tar, name, out_path)
                    self.log(f"✓ Extracted {name}", 'success')
                    extracted_count += 1
                except Exception as e:
                    self.log(f"✗ Failed to extract {name}: {e}", 'error')

            self.status_label.config(text=f"Extracted {extracted_count}/{len(selected_items)} entries")
            self.log(f"Extraction complete: {extracted_count}/{len(selected_items)} files extracted", 'success')

        except Exception as e:
            self.log(f"Extraction failed: {e}", 'error')
            self.after(0, lambda: messagebox.showerror("Error", str(e)))
        finally:
            self.progress.stop()
    
    def replace_fw_entry(self):
        if not self.fw_tree.selection():
            messagebox.showinfo("Info", "Select an entry")
            return
        
        entry = self.fw_tree.selection()[0]
        name = self.fw_tree.item(entry, 'text')
        
        replacement = filedialog.askopenfilename(title="Select replacement file")
        if replacement:
            if not self.current_project or not self.current_project.firmware_file:
                messagebox.showerror("Error", "No firmware file loaded in the current project.")
                return
            with open(replacement, "rb") as f:
                data = f.read()
            try:
                replace_tar_entry_inplace(self.current_project.firmware_file, name, data)
                self.log(f"Replaced {name} and updated MD5 if applicable", 'success')
            except Exception as e:
                self.log(f"Replacement failed: {e}", 'error')
    
    # Flashing
    def detect_device(self):
        if not is_admin():
            self.log("✗ Admin privileges required for device detection", 'error')
            messagebox.showerror("Admin Required", "Administrator privileges are required to detect devices via Heimdall.")
            return

        try:
            if heimdall_detect_device():
                self.log("✓ Device detected", 'success')
                messagebox.showinfo("Success", "Device found!")
            else:
                self.log("✗ No device", 'warning')
                messagebox.showwarning("No Device", "Device not detected")
        except Exception as e:
            self.log(f"Detection failed: {e}", 'error')
    
    def flash_heimdall(self):
        if not is_admin():
            self.log("✗ Admin privileges required for flashing", 'error')
            messagebox.showerror("Admin Required", "Administrator privileges are required to flash devices via Heimdall.")
            return

        if not messagebox.askyesno("Flash Warning",
            "⚠ FLASHING CAN BRICK DEVICE ⚠\n\nContinue?"):
            return

        if not self.current_project or not self.current_project.firmware_file:
            messagebox.showerror("Error", "No firmware loaded")
            return

        try:
            self.log("Preparing to flash via Heimdall...", 'info')
            firmware = self.current_project.firmware_file
            work_tar = firmware
            if firmware.lower().endswith('.tar.md5'):
                tmp_tar = tempfile.mktemp(suffix=".tar")
                strip_md5_footer(firmware, tmp_tar)
                work_tar = tmp_tar
            
            entries = list_tar_entries(work_tar)
            partition_map = {}
            temp_files = []
            
            for name, _, _, _ in entries:
                base_name = os.path.basename(name).lower()
                if base_name in SAMSUNG_PARTITION_MAP:
                    temp_img = tempfile.mktemp(suffix=os.path.splitext(base_name)[1])
                    extract_tar_entry(work_tar, name, temp_img)
                    partition_map[SAMSUNG_PARTITION_MAP[base_name]] = temp_img
                    temp_files.append(temp_img)
            
            if not partition_map:
                raise ValueError("No mappable partitions found in firmware")
            
            success = heimdall_flash(partition_map)
            if success:
                self.log("✓ Flashed successfully", 'success')
                messagebox.showinfo("Success", "Flashing complete!")
            else:
                self.log("✗ Flash failed", 'error')
                messagebox.showerror("Error", "Flashing failed")
            
            # Cleanup temps
            for f in temp_files:
                try:
                    os.remove(f)
                except:
                    pass
        except Exception as e:
            self.log(f"Flash failed: {e}", 'error')
            messagebox.showerror("Error", str(e))
    
    # Tools
    def refresh_tools(self):
        tools = {
            'bsdtar': 'TAR/CPIO',
            'lz4': 'LZ4 compression',
            'heimdall': 'Device flashing',
            'magiskboot': 'Boot images',
            'simg2img': 'Sparse convert',
            'img2simg': 'Raw to sparse',
            'apktool': 'APK tools (wrapper)',
            'apktool.jar': 'APK tools (jar)',
            'zipalign': 'APK alignment',
            'apksigner.jar': 'APK signing',
            '7z': 'Archive tool',
            'java': 'Java runtime',
            'notepad++': 'Advanced text editor',
        }
        
        self.tools_tree.delete(*self.tools_tree.get_children())
        found = 0
        
        for tool, desc in tools.items():
            if tool == 'apksigner.jar': # Special handling for apksigner
                path = tool_resolve_apksigner()
            else:
                path = tool_resolve(tool)

            if path:
                status = "✓"
                found += 1
                self.log(f"Resolved tool '{tool}' to: {path}", 'info')
            else:
                path = "NOT FOUND"
                status = "✗"
                self.log(f"Tool '{tool}' not found.", 'warning')
            
            self.tools_tree.insert('', 'end', text=f"{status} {tool}",
                                  values=(f"{path} ({desc})",))
        
        self.tool_status_label.config(
            text=f"✓ {found}/{len(tools)} tools",
            foreground=COLORS['success'] if found == len(tools) else COLORS['warning']
        )
        self.log(f"Tools: {found}/{len(tools)} found", 'info')
    
    def open_tools_folder(self):
        ensure_dir(TOOLS_DIR)
        if sys.platform.startswith('win'):
            os.startfile(TOOLS_DIR)
        else:
            subprocess.Popen(['xdg-open' if sys.platform != 'darwin' else 'open',
                            TOOLS_DIR])
    
    
    def show_tool_status(self):
        self.refresh_tools()
        messagebox.showinfo("Tool Status", "Tool detection complete. See Tools tab.")
    
    def show_about(self):
        about_text = f"""{APP_TITLE} v{VERSION}

Complete Android ROM & Firmware Toolkit

Features:
• AOSP/Custom ROM Building
• Odin .tar.md5 Firmware (Byte-exact)
• Boot Image Modification
• System Customization
• APK Decompile/Recompile/Sign
• LZ4 Compression
• Sparse Image Conversion
• Device Flashing (Heimdall)
• Project Management
• 30+ Tool Integration

Utilizes tools from: {TOOLS_DIR}

Place all tools in tools/ folder for full functionality.
"""
        messagebox.showinfo("About", about_text)
    
    def _format_size(self, size: int) -> str:
        """Format file size"""
        size_float = float(size)
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_float < 1024:
                return f"{size_float:.1f} {unit}"
            size_float /= 1024
        return f"{size_float:.1f} PB"

# -------------------------
# Entry Point
# -------------------------
def main():
    startup_logger.info("Initializing GUI.")
    startup_logger.info("Attempting to create a simple Tkinter root window.")
    try:
        root_test = tk.Tk()
        root_test.withdraw() # Hide the root window initially
        startup_logger.info("Simple Tkinter root window created successfully.")
        root_test.destroy()
        startup_logger.info("Simple Tkinter root window destroyed.")
    except Exception as e:
        startup_logger.exception("Failed to create simple Tkinter root window:")
        messagebox.showerror("Tkinter Error", f"Failed to initialize Tkinter. Error: {e}")
        sys.exit(1)

    startup_logger.info("Initializing UltimateFirmwareKitchen application.")
    app = UltimateFirmwareKitchen()
    app.refresh_tools()
    app.log(f"{APP_TITLE} v{VERSION} started", 'success')
    app.log(f"Tools directory: {TOOLS_DIR}", 'info')
    startup_logger.info("Calling app.mainloop() for UltimateFirmwareKitchen.")
    app.mainloop()
    startup_logger.info("app.mainloop() for UltimateFirmwareKitchen exited.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        with open("crash_log.txt", "w") as f:
            f.write(f"An unhandled exception occurred: {e}\n")
            f.write(traceback.format_exc())
        # Optionally, display a simple error message box if the GUI environment is still available
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw() # Hide the main window
            messagebox.showerror("Application Error", "An unexpected error occurred. Details have been written to crash_log.txt")
            root.destroy()
        except:
            pass
        sys.exit(1)
