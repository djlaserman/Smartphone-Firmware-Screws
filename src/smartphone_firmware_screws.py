#!/usr/bin/env python3
"""
Smartphone Firmware Screws - Complete Android ROM & Firmware Toolkit
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

Author: Isaki Dube | License: Dual
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
import logging # Added for detailed startup logging
import traceback # Added for detailed exception logging
import math
import mmap
import glob
import tarfile
import gzip # Added for ramdisk decompression

# Optional plotting for entropy (install matplotlib to enable)
try:
    import matplotlib.pyplot as plt
    MATPLOTLIB = True
except Exception:
    MATPLOTLIB = False

# -------------------------
# Configuration & Constants
# -------------------------
APP_TITLE = "Smartphone Firmware Screws"
VERSION = "1.0.0"  # Updated for fixes
TOOLS_DIR = os.path.join(os.path.dirname(__file__), "tools")

# Configure a file handler for startup logging
startup_logger = logging.getLogger('startup_logger')
startup_logger.setLevel(logging.DEBUG)
log_handler = logging.FileHandler('startup_debug.log')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_handler.setFormatter(formatter)
startup_logger.addHandler(log_handler)

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

# Samsung firmware file type detection and offset width mapping
SAMSUNG_FIRMWARE_TYPES = {
    # Bootloader components
    'pit': {'patterns': ['pit', 'param'], 'width': 4},
    'sboot.bin': {'patterns': ['sboot', 'sbl'], 'width': 5},
    'cm.bin': {'patterns': ['cm', 'cert'], 'width': 5},
    'up_param.bin': {'patterns': ['up_param', 'uparam'], 'width': 5},
    'param.bin': {'patterns': ['param'], 'width': 5},
    'tz.mbn': {'patterns': ['tz', 'trustzone'], 'width': 5},
    'tz.img': {'patterns': ['tz', 'trustzone'], 'width': 5},
    'hyp.mbn': {'patterns': ['hyp', 'hypervisor'], 'width': 5},
    'keymaster.mbn': {'patterns': ['keymaster'], 'width': 5},
    'cmnlib.mbn': {'patterns': ['cmnlib'], 'width': 5},
    'cmnlib64.mbn': {'patterns': ['cmnlib64'], 'width': 5},
    'abl.elf': {'patterns': ['abl'], 'width': 6},
    'abl.img': {'patterns': ['abl'], 'width': 6},
    'lk.elf': {'patterns': ['lk', 'little_kernel'], 'width': 5},
    'xbl.elf': {'patterns': ['xbl'], 'width': 6},
    'xbl_config.elf': {'patterns': ['xbl_config'], 'width': 6},
    'rpm.mbn': {'patterns': ['rpm'], 'width': 5},
    'pmic.mbn': {'patterns': ['pmic'], 'width': 5},
    'devcfg.mbn': {'patterns': ['devcfg'], 'width': 5},
    'storsec.mbn': {'patterns': ['storsec'], 'width': 5},
    'vbmeta.img': {'patterns': ['vbmeta'], 'width': 5},
    'vbmeta_system.img': {'patterns': ['vbmeta_system'], 'width': 5},
    'vbmeta_vendor.img': {'patterns': ['vbmeta_vendor'], 'width': 5},

    # Device tree components
    'dtb.img': {'patterns': ['dtb'], 'width': 6},
    'dtbo.img': {'patterns': ['dtbo'], 'width': 6},

    # Boot images
    'boot.img': {'patterns': ['boot'], 'width': 7},
    'vendor_boot.img': {'patterns': ['vendor_boot'], 'width': 7},
    'init_boot.img': {'patterns': ['init_boot'], 'width': 6},
    'recovery.img': {'patterns': ['recovery'], 'width': 7},

    # Kernel components
    'kernel': {'patterns': ['kernel', 'image', 'zimage'], 'width': 6},
    'ramdisk': {'patterns': ['ramdisk', 'cpio'], 'width': 6},

    # System partitions
    'system.img': {'patterns': ['system'], 'width': 8},
    'system_ext.img': {'patterns': ['system_ext'], 'width': 8},
    'vendor.img': {'patterns': ['vendor'], 'width': 8},
    'product.img': {'patterns': ['product'], 'width': 8},
    'odm.img': {'patterns': ['odm'], 'width': 8},
    'oem.img': {'patterns': ['oem'], 'width': 8},
    'super.img': {'patterns': ['super'], 'width': 9},
    'userdata.img': {'patterns': ['userdata'], 'width': 10},
    'cache.img': {'patterns': ['cache'], 'width': 8},
    'hidden.img': {'patterns': ['hidden'], 'width': 8},
    'optics.img': {'patterns': ['optics'], 'width': 8},
    'prism.img': {'patterns': ['prism'], 'width': 8},
    'omc.img': {'patterns': ['omc'], 'width': 8},
    'metadata.img': {'patterns': ['metadata'], 'width': 7},

    # Modem/baseband
    'modem.bin': {'patterns': ['modem'], 'width': 7},
    'non-hlos.bin': {'patterns': ['non-hlos'], 'width': 7},
    'btfm.bin': {'patterns': ['btfm', 'bluetooth'], 'width': 6},
    'wcnss.mbn': {'patterns': ['wcnss', 'wifi'], 'width': 6},
    'efs.img': {'patterns': ['efs'], 'width': 7},
    'persist.img': {'patterns': ['persist'], 'width': 8},

    # Odin packages
    'ap_*.tar.md5': {'patterns': ['ap_', 'application'], 'width': 8},
    'bl_*.tar.md5': {'patterns': ['bl_', 'bootloader'], 'width': 8},
    'cp_*.tar.md5': {'patterns': ['cp_', 'modem'], 'width': 7},
    'csc_*.tar.md5': {'patterns': ['csc_', 'region'], 'width': 8},
    'home_csc_*.tar.md5': {'patterns': ['home_csc'], 'width': 8},

    # Configuration files
    'cscfeature.xml': {'patterns': ['cscfeature'], 'width': 4},
    'cscnetwork.xml': {'patterns': ['cscnetwork'], 'width': 4},
    'customer.xml': {'patterns': ['customer'], 'width': 4},
    'verity_key': {'patterns': ['verity_key'], 'width': 4},
    'fstab': {'patterns': ['fstab'], 'width': 4},
    'init': {'patterns': ['init'], 'width': 5},
    'sepolicy': {'patterns': ['sepolicy', 'selinux'], 'width': 6},
    'ueventd.rc': {'patterns': ['ueventd'], 'width': 4},
}

def detect_firmware_file_type(filename: str) -> Optional[Dict[str, Any]]:
    """
    Detect Samsung firmware file type and return optimal offset width.
    Uses fuzzy matching to handle renamed files (e.g., myboot.img -> boot.img).
    """
    if not filename:
        return None

    filename_lower = filename.lower()

    # Exact matches first
    for file_type, config in SAMSUNG_FIRMWARE_TYPES.items():
        if filename_lower == file_type.lower():
            return {'type': file_type, 'width': config['width']}

    # Pattern matching for renamed files
    for file_type, config in SAMSUNG_FIRMWARE_TYPES.items():
        for pattern in config['patterns']:
            if pattern in filename_lower:
                return {'type': file_type, 'width': config['width']}

    # Special handling for Odin packages with version numbers
    if filename_lower.endswith('.tar.md5'):
        if filename_lower.startswith(('ap_', 'bl_', 'cp_', 'csc_', 'home_csc_')):
            prefix = filename_lower.split('_')[0] + '_*.tar.md5'
            if prefix in SAMSUNG_FIRMWARE_TYPES:
                return {'type': prefix, 'width': SAMSUNG_FIRMWARE_TYPES[prefix]['width']}

    return None

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

@dataclass
class PortRomConfig:
    """Configuration for device-agnostic ROM porting operations"""
    source_device: str = ""
    target_device: str = ""
    source_firmware_dir: str = ""
    target_firmware_dir: str = ""
    work_dir: str = ""

    def get_work_subdir(self, device: str, subdir: str) -> str:
        """Get work directory path for a specific device and subdirectory"""
        return os.path.join(self.work_dir, device, subdir)

    def get_extracted_dir(self, device: str) -> str:
        """Get extracted firmware directory for a device"""
        return self.get_work_subdir(device, "extracted")

    def get_boot_dir(self, device: str) -> str:
        """Get boot directory for a device"""
        return self.get_work_subdir(device, "boot")

    def get_system_dir(self, device: str) -> str:
        """Get system directory for a device"""
        return self.get_work_subdir(device, "system")

    def get_vendor_dir(self, device: str) -> str:
        """Get vendor directory for a device"""
        return self.get_work_subdir(device, "vendor")

    def get_output_dir(self) -> str:
        """Get output directory for final packages"""
        return os.path.join(self.work_dir, "output")

    def get_odin_dir(self) -> str:
        """Get Odin package directory"""
        return os.path.join(self.work_dir, "odin_package")

    def get_ap_package_name(self) -> str:
        """Get AP package name for Odin"""
        return f"AP_{self.source_device}_to_{self.target_device}.tar.md5"

    def get_bl_package_name(self) -> str:
        """Get BL package name for Odin"""
        return f"BL_{self.target_device}.tar.md5"

    def get_cp_package_name(self) -> str:
        """Get CP package name for Odin"""
        return f"CP_{self.target_device}.tar.md5"

    def get_mmc_controller(self, device: str) -> str:
        """Get MMC controller path for a device"""
        # This method is not used, but is kept for future reference.
        # In a fully agnostic system, this should be detected from firmware files.
        return '13500000.dwmmc0'  # Default fallback

    def get_device_model_code(self, device: str) -> str:
        """Get device model code for property replacements"""
        # This method is not used, but is kept for future reference.
        # In a fully agnostic system, this should be detected from firmware files.
        return device.upper()

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
            # JAR files start with 'PK' (ZIP header) and are valid for Java execution
            if path.lower().endswith('.jar') and header.startswith(b'PK'):
                return True
            return False # If it's not an exe/bat/cmd/jar and doesn't have MZ, it's likely not a valid Win32 app
        else:
            # Unix/Linux: ELF executable starts with '\x7fELF'
            if header.startswith(b'\x7fELF'):
                return True
            # JAR files start with 'PK' (ZIP header) and are valid for Java execution
            if path.lower().endswith('.jar') and header.startswith(b'PK'):
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
def format_offset(
    offset: int,
    file_size: int,
    base: int = 16,
    *,
    prefix: bool = False,
    group: int | None = None,
    min_width: int = 4,
    max_width: int = 12,
    clamp_profile: str = "firmware"
) -> str:
    """
    Professionally format an offset for hex-editor display, adapting width to file size.
    Fine-grained and accurate for Samsung smartphone firmware content:
    DTB, ramdisk, boot.img, vendor_boot.img, kernel (Image/zImage),
    sboot.bin, modem.bin, recovery.img, system/vendor/product/super.img,
    PIT/param.bin, userdata/cache, and raw NAND dumps.

    Parameters:
        offset (int): Byte offset to format (>= 0).
        file_size (int): Total file size in bytes (>= 1).
        base (int): 16 for hex (recommended), 10 for decimal.
        prefix (bool): Add "0x" for hex or no prefix for decimal.
        group (int|None): Digit grouping (e.g., 4 for hex nibbles or 3 for decimal).
        min_width (int): Minimum digits to show (default 4).
        max_width (int): Maximum digits to show (default 12).
        clamp_profile (str): Width clamping profile. One of:
            - "firmware": common firmware widths
            - "powerof2": round up to power-of-two nibble counts (hex)
            - "none": no clamping beyond [min_width, max_width]

    Returns:
        str: Formatted offset string (e.g., "0000ABCD" or "0x0000ABCD").
    """
    if offset < 0:
        raise ValueError("offset must be >= 0")
    if file_size <= 0:
        raise ValueError("file_size must be >= 1")
    if base not in (10, 16):
        raise ValueError("Only base 10 or 16 supported")

    # Determine required digits from file size (max representable index is file_size - 1)
    max_index = max(0, file_size - 1)

    if base == 16:
        # Hex digits: ceil(bit_length / 4)
        req_digits = max(1, (max_index.bit_length() + 3) // 4)
    else:
        # Decimal digits: length of string for max index
        req_digits = len(str(max_index))

    # Apply clamping profile for professional widths
    def clamp_width(d: int) -> int:
        d = max(min_width, min(d, max_width))
        if clamp_profile == "none":
            return d
        elif clamp_profile == "powerof2" and base == 16:
            # Round up to nibble-friendly widths
            for w in (4, 5, 6, 7, 8, 10, 12, 16):
                if d <= w:
                    return min(w, max_width)
            return min(d, max_width)
        elif clamp_profile == "firmware":
            # Tuned for Samsung firmware content spectrum
            # Hex: prefer 4,5,6,7,8,10,12; Dec: prefer 5,6,8,10,12
            choices_hex = (4, 5, 6, 7, 8, 10, 12)
            choices_dec = (5, 6, 8, 10, 12)
            choices = choices_hex if base == 16 else choices_dec
            for w in choices:
                if d <= w:
                    return min(w, max_width)
            return min(d, max_width)
        else:
            return min(d, max_width)

    width = clamp_width(req_digits)

    # Format core number
    if base == 16:
        core = f"{offset:0{width}X}"
    else:
        core = f"{offset:0{width}d}"

    # Optional digit grouping for readability
    if group and group > 0:
        # Group from the right; non-destructive to leading zeros
        rev = core[::-1]
        chunks = [rev[i:i + group] for i in range(0, len(rev), group)]
        core = " ".join(chunk[::-1] for chunk in chunks[::-1])

    # Optional prefix
    if prefix and base == 16:
        return f"0x{core}"
    return core

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

    # Fallback to cpio command if bsdtar fails
    cpio = tool_resolve("cpio")
    if cpio:
        try:
            with open(work_file, 'rb') as f:
                result = run_cmd([cpio, "-idm"], cwd=out_dir, input_data=f.read())
                if result.returncode == 0:
                    return
        except Exception:
            pass

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
# GUI: Text Output Dialog
# -------------------------
class TextOutputDialog(tk.Toplevel):
    """A simple dialog to display text output."""
    def __init__(self, parent, title: str, text_content: str):
        super().__init__(parent)
        self.title(title)
        self.geometry("600x400")
        self.resizable(True, True)

        self.text_area = scrolledtext.ScrolledText(self, wrap='word', font=('Consolas', 10),
                                                  bg=COLORS['log_bg'], fg=COLORS['log_fg'])
        self.text_area.insert(tk.END, text_content)
        self.text_area.config(state='disabled') # Make it read-only
        self.text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        close_button = ttk.Button(self, text="Close", command=self.destroy)
        close_button.pack(pady=5)

        self.transient(parent)
        self.grab_set()
        self.wait_window(self)

# -------------------------
# GUI: Hex Editor Widget
# -------------------------
class HexEditorWidget(ttk.Frame):
    """Hex Editor widget integrated with the main application"""

    def __init__(self, parent, log_callback, status_callback, progress_callback=None):
        super().__init__(parent)
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.progress_callback = progress_callback  # Callback to update progress bar
        self.set_status = status_callback  # For compatibility with existing code
        self._init_state()
        self._build_ui()
        self._bind_shortcuts()

    def _init_state(self):
        self.file_path = None
        self.data = bytearray()
        self.mmap_file = None
        self.file_handle = None
        self.modified = False
        self.offset_top = 0
        self.bytes_per_line = 16
        self.endian = "big"  # default big-endian
        self.undo_stack = []
        self.redo_stack = []
        self.bookmarks = {}
        self.current_selection = (None, None)  # (start, end)
        self.windowed = False
        self.firmware_type = None  # Detected firmware file type
        self.preserved_selection = None  # To preserve selection across focus changes

    def _build_ui(self):
        # Apply consistent background colors to match the application theme
        # Note: Frame background is handled by ttk style

        # Configure styles for consistent background in right panel
        hex_style = ttk.Style()
        hex_style.configure("HexEditor.TLabelframe", background=COLORS['bg_card'], foreground=COLORS['text_primary'])
        hex_style.configure("HexEditor.TLabel", background=COLORS['bg_card'], foreground=COLORS['text_primary'])
        hex_style.configure("HexEditor.TEntry", fieldbackground=COLORS['log_bg'], foreground=COLORS['text_primary'])
        hex_style.configure("HexEditor.TButton", background=COLORS['bg_card'])

        # Menu items are handled by the parent application

        # Top frame controls
        top_frame = ttk.Frame(self, style='Card.TFrame')
        top_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Button(top_frame, text="Open", command=self.open_file, takefocus=False).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_frame, text="Save", command=self.save_file, takefocus=False).pack(side=tk.LEFT, padx=2)
        ttk.Label(top_frame, text=" Endian: ").pack(side=tk.LEFT, padx=2)
        self.endian_var = tk.StringVar(value=self.endian)
        endian_combo = ttk.Combobox(top_frame, textvariable=self.endian_var, values=("big", "little"), width=6, takefocus=False)
        endian_combo.pack(side=tk.LEFT)
        endian_combo.bind("<<ComboboxSelected>>", lambda e: self.set_endian(self.endian_var.get()))
        ttk.Button(top_frame, text="Entropy", command=self.entropy_analysis, takefocus=False).pack(side=tk.LEFT, padx=4)
        ttk.Button(top_frame, text="Strings", command=self.show_strings, takefocus=False).pack(side=tk.LEFT, padx=4)

        # Main panes: left = hex view, right = converters / analysis
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL, style='Card.TFrame')
        main_pane.pack(fill=tk.BOTH, expand=True)

        # Left frame: hex text view
        left_frame = ttk.Frame(main_pane, style='Card.TFrame')
        self.hex_text = tk.Text(left_frame, font=("Courier New", 10), wrap="none", undo=False,
                               bg=COLORS['log_bg'], fg=COLORS['log_fg'], insertbackground=COLORS['text_primary'])
        self.hex_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.hex_text.bind("<<Selection>>", self.on_selection)
        self.hex_text.bind("<Button-1>", self.on_click)
        self.hex_text.bind("<KeyRelease>", self.on_hex_key_release)
        self.hex_text.bind("<FocusOut>", self._on_focus_out)
        self.hex_text.bind("<FocusIn>", self._on_focus_in)
        # Configure persistent selection tag for visibility when unfocused
        self.hex_text.tag_config('persistent_sel', background='#4f94cd', foreground='white')
        # Scrollbars
        yscroll = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, command=self.hex_text.yview)
        self.hex_text.configure(yscrollcommand=yscroll.set)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        xscroll = ttk.Scrollbar(self, orient=tk.HORIZONTAL, command=self.hex_text.xview)
        self.hex_text.configure(xscrollcommand=xscroll.set)
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)

        main_pane.add(left_frame, weight=3)

        # Right frame: converters and tools
        right_frame = ttk.Frame(main_pane, width=420, style='Card.TFrame')
        main_pane.add(right_frame, weight=1)

        # Create a scrollable frame for the right panel
        right_canvas = tk.Canvas(right_frame, bg=COLORS['bg_card'], highlightthickness=0)
        right_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=right_canvas.yview)
        right_scrollable_frame = ttk.Frame(right_canvas, style='Card.TFrame')

        right_scrollable_frame.bind(
            "<Configure>",
            lambda e: right_canvas.configure(scrollregion=right_canvas.bbox("all"))
        )

        right_canvas.create_window((0, 0), window=right_scrollable_frame, anchor="nw")
        right_canvas.configure(yscrollcommand=right_scrollbar.set)

        # Make the scrollable frame fill the canvas
        def resize_canvas(event):
            right_canvas.itemconfig(right_canvas.find_all()[0], width=event.width)

        right_canvas.bind('<Configure>', resize_canvas)

        # Bind mouse wheel to scroll the canvas
        def on_mousewheel(event):
            right_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        right_canvas.bind_all("<MouseWheel>", on_mousewheel)

        right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        right_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Selection info - make it fill more space
        info_frame = ttk.LabelFrame(right_scrollable_frame, text="Selection / Offset", style='HexEditor.TLabelframe')
        info_frame.pack(fill=tk.X, padx=6, pady=(6, 3))
        self.offset_label = ttk.Label(info_frame, text="Offset: -", style='HexEditor.TLabel')
        self.offset_label.pack(anchor="w", padx=4, pady=2)
        self.length_label = ttk.Label(info_frame, text="Length: -", style='HexEditor.TLabel')
        self.length_label.pack(anchor="w", padx=4, pady=2)

        # Byte edit box
        edit_frame = ttk.LabelFrame(right_scrollable_frame, text="Edit Bytes", style='HexEditor.TLabelframe')
        edit_frame.pack(fill=tk.X, padx=6, pady=(3, 6))
        self.byte_entry = ttk.Entry(edit_frame, style='HexEditor.TEntry')
        self.byte_entry.pack(fill=tk.X, padx=4, pady=4)
        ttk.Button(edit_frame, text="Write Bytes (hex space-separated)", command=self.write_bytes_from_entry, style='HexEditor.TButton', takefocus=False).pack(padx=4, pady=4)

        # Converter outputs - make it expand to fill space
        conv_frame = ttk.LabelFrame(right_scrollable_frame, text="Converters (live)", style='HexEditor.TLabelframe')
        conv_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(6, 3))
        # Endian toggle
        self.endian_display = ttk.Label(conv_frame, text=f"Endian: {self.endian}", style='HexEditor.TLabel')
        self.endian_display.pack(anchor="w", padx=4, pady=2)

        # Integer display
        self.int_signed_var = tk.BooleanVar(value=False)
        chk = ttk.Checkbutton(conv_frame, text="Signed", variable=self.int_signed_var, command=self.refresh_converters)
        chk.pack(anchor="w", padx=4)
        self.int_label = ttk.Label(conv_frame, text="Integer:", style='HexEditor.TLabel')
        self.int_label.pack(anchor="w", padx=4, pady=2)

        # Float display (32 / 64)
        self.float32_label = ttk.Label(conv_frame, text="Float32:", style='HexEditor.TLabel')
        self.float32_label.pack(anchor="w", padx=4, pady=2)
        self.float64_label = ttk.Label(conv_frame, text="Float64:", style='HexEditor.TLabel')
        self.float64_label.pack(anchor="w", padx=4, pady=2)

        # String interpretations
        self.utf8_label = ttk.Label(conv_frame, text="UTF-8:", style='HexEditor.TLabel')
        self.utf8_label.pack(anchor="w", padx=4, pady=2)
        self.utf16_label = ttk.Label(conv_frame, text="UTF-16:", style='HexEditor.TLabel')
        self.utf16_label.pack(anchor="w", padx=4, pady=2)
        self.utf32_label = ttk.Label(conv_frame, text="UTF-32:", style='HexEditor.TLabel')
        self.utf32_label.pack(anchor="w", padx=4, pady=2)

        # Hex display and copy
        self.hex_label = ttk.Label(conv_frame, text="Hex:", style='HexEditor.TLabel')
        self.hex_label.pack(anchor="w", padx=4, pady=2)
        ttk.Button(conv_frame, text="Copy Hex", command=self.copy_hex_to_clipboard, style='HexEditor.TButton', takefocus=False).pack(anchor="w", padx=4, pady=2)

        # Live string extraction display
        self.strings_label = ttk.Label(conv_frame, text="Extractable Strings:", style='HexEditor.TLabel')
        self.strings_label.pack(anchor="w", padx=4, pady=(10, 2))

        # Create a frame to contain the text widget and its scrollbar
        strings_frame = ttk.Frame(conv_frame, style='Card.TFrame')
        strings_frame.pack(fill=tk.X, padx=4, pady=(0, 4))

        self.strings_text = tk.Text(strings_frame, height=4, width=40, wrap="none",
                                   bg=COLORS['log_bg'], fg=COLORS['log_fg'],
                                   font=('Consolas', 8), state="disabled",
                                   tabs=('1c', '5c', 'left'))  # Set tab stops: offset at 1cm, string at 5cm
        strings_scrollbar = ttk.Scrollbar(strings_frame, orient=tk.VERTICAL, command=self.strings_text.yview)
        self.strings_text.configure(yscrollcommand=strings_scrollbar.set)
        self.strings_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        strings_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Analysis frame (entropy + strings)
        analysis_frame = ttk.LabelFrame(right_scrollable_frame, text="Quick Analysis", style='HexEditor.TLabelframe')
        analysis_frame.pack(fill=tk.X, padx=6, pady=(3, 6))
        ttk.Button(analysis_frame, text="Compute Entropy (selection/file)", command=self.entropy_analysis, style='HexEditor.TButton', takefocus=False).pack(fill=tk.X, padx=4, pady=2)
        ttk.Button(analysis_frame, text="Extract Printable Strings", command=self.show_strings, style='HexEditor.TButton', takefocus=False).pack(fill=tk.X, padx=4, pady=2)
        ttk.Button(analysis_frame, text="Byte Histogram", command=self.byte_histogram, style='HexEditor.TButton', takefocus=False).pack(fill=tk.X, padx=4, pady=2)

        # Status bar
        self.status = ttk.Label(self, text="Ready", relief=tk.SUNKEN, anchor="w", style='HexEditor.TLabel')
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

    # Shortcuts bindings
    def _bind_shortcuts(self):
        self.bind("<Control-o>", lambda e: self.open_file())
        self.bind("<Control-s>", lambda e: self.save_file())
        self.bind("<Control-f>", lambda e: self.find_dialog())
        self.bind("<Control-h>", lambda e: self.replace_dialog())
        self.bind("<Control-g>", lambda e: self.goto_dialog())
        self.bind("<Control-z>", lambda e: self.undo())
        self.bind("<Control-y>", lambda e: self.redo())

    # File operations
    def open_file(self, mmap_ok=False):
        path = filedialog.askopenfilename(title="Open file", filetypes=[("All files", "*.*")])
        if not path:
            return
        self.close_file()
        try:
            if mmap_ok:
                res, fhandle = self.read_file_bytes(path)
                if isinstance(res, mmap.mmap):
                    self.mmap_file = res
                    self.file_handle = fhandle
                    self.data = None
                else:
                    self.data = bytearray(res)
            else:
                self.data, _ = self.read_file_bytes(path, use_mmap=False)
            self.file_path = path
            self.modified = False
            self.offset_top = 0
            data_len = len(self.data) if self.data else (self.mmap_file.size() if self.mmap_file else 0)
            self.windowed = data_len > 1024 * 256

            # Detect firmware file type for optimal offset display
            filename = os.path.basename(path)
            self.firmware_type = detect_firmware_file_type(filename)

            self.refresh_view()
            data_len = len(self.data) if self.data else (self.mmap_file.size() if self.mmap_file else 0)
            self.set_status(f"Opened {path} ({data_len} bytes)")
            self.log_callback(f"Hex Editor: Opened {path}", 'success')
            # Focus the hex text widget so Ctrl+A works immediately after opening
            # Use after() to ensure the widget is fully rendered before focusing
            self.after(100, lambda: (self.focus(), self.hex_text.focus_set()))
        except Exception as e:
            messagebox.showerror("Open Error", str(e))
            self.log_callback(f"Hex Editor: Failed to open {path}: {e}", 'error')

    def close_file(self):
        if self.mmap_file:
            try:
                self.mmap_file.close()
                if self.file_handle:
                    self.file_handle.close()
            except Exception:
                pass
        self.mmap_file = None
        self.file_handle = None
        self.data = bytearray()
        self.file_path = None
        self.modified = False

    def save_file(self):
        if not self.file_path:
            self.save_as()
            return
        try:
            if self.mmap_file:
                # write back from memory to mmap then flush
                self.mmap_file.seek(0)
                self.mmap_file.write(self._get_bytes_all())
                self.mmap_file.flush()
            else:
                with open(self.file_path, "wb") as f:
                    f.write(self._get_bytes_all())
            self.modified = False
            self.set_status("Saved")
            self.log_callback(f"Hex Editor: Saved {self.file_path}", 'success')
        except Exception as e:
            messagebox.showerror("Save Error", str(e))
            self.log_callback(f"Hex Editor: Failed to save {self.file_path}: {e}", 'error')

    def save_as(self):
        path = filedialog.asksaveasfilename(title="Save As")
        if not path:
            return
        self.file_path = path
        self.save_file()

    # Helpers to get/set bytes across mmap/data
    def _get_len(self):
        if self.mmap_file:
            return self.mmap_file.size()
        return len(self.data) if self.data else 0

    def _get_slice(self, start, length):
        if self.mmap_file:
            return self.mmap_file[start:start + length]
        return bytes(self.data[start:start + length]) if self.data else b""

    def _write_slice(self, start, bts: bytes):
        # record for undo
        old = self._get_slice(start, len(bts))
        self.undo_stack.append(("write", start, old))
        self.redo_stack.clear()
        if self.mmap_file:
            self.mmap_file[start:start + len(bts)] = bts
        else:
            if self.data:
                self.data[start:start + len(bts)] = bts
        self.modified = True

    def _get_bytes_all(self):
        if self.mmap_file:
            return self.mmap_file[:]
        return bytes(self.data) if self.data else b""

    # Rendering hex view
    def refresh_view(self):
        self.hex_text.configure(state=tk.NORMAL)
        self.hex_text.delete("1.0", tk.END)
        total_len = self._get_len()
        # windowed display if large file
        if self.windowed:
            length = min(1024 * 256, total_len - self.offset_top)
            data = self._get_slice(self.offset_top, length)
            base = self.offset_top
        else:
            data = self._get_slice(0, total_len)
            base = 0
        for i in range(0, len(data), self.bytes_per_line):
            chunk = data[i:i + self.bytes_per_line]
            hex_chunk = " ".join(f"{b:02X}" for b in chunk)
            # pad hex chunk to fixed width
            hex_padded = f"{hex_chunk:<{self.bytes_per_line * 3 - 1}}"
            ascii_chunk = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
            # Use firmware-specific width if detected, otherwise adapt to file size
            if self.firmware_type:
                offset_str = format_offset(base + i, total_len, base=16, min_width=self.firmware_type['width'],
                                          max_width=self.firmware_type['width'], clamp_profile="none")
            else:
                offset_str = format_offset(base + i, total_len, base=16, clamp_profile="firmware")
            line = f"{offset_str}  {hex_padded}  {ascii_chunk}\n"
            self.hex_text.insert(tk.END, line)
        # Keep the widget editable - do not disable it
        self.update_selection_info(None, None)

    # Selection / mapping: map mouse click in Text to byte offset
    def on_click(self, event):
        try:
            index = self.hex_text.index("@%d,%d" % (event.x, event.y))
            line, col = map(int, index.split("."))
            text_line = self.hex_text.get(f"{line}.0", f"{line}.end")
            # parse offset at line start - now variable length due to format_offset
            # Find the first space after the offset (which separates offset from hex data)
            space_pos = text_line.find('  ')
            if space_pos == -1:
                return
            offset_hex = text_line[:space_pos].strip()
            # Handle empty string (offset 0 case)
            if not offset_hex:
                base = 0
            else:
                base = int(offset_hex, 16)
            # hex starts after offset and spaces (variable position now)
            hex_start = space_pos + 2  # Skip the two spaces
            # compute position in hex area; each byte is "XX " except last may be shorter
            # find nearest hex token by splitting.
            tokens = text_line[hex_start:hex_start + self.bytes_per_line * 3].split()
            # find which token mouse clicked over by computing char index
            col_in_line = col - hex_start
            if col_in_line < 0:
                return
            # compute approximate token index
            token_idx = max(0, min(len(tokens) - 1, col_in_line // 3))
            # select byte
            byte_offset = base + token_idx
            self.update_selection_info(byte_offset, 1)
        except Exception:
            pass

    def on_hex_key_release(self, event):
        """Handle key presses in the hex text widget for editing"""
        if not self.file_path or event.char == '':
            return

        try:
            # Get current cursor position
            cursor_pos = self.hex_text.index(tk.INSERT)
            line, col = map(int, cursor_pos.split("."))

            text_line = self.hex_text.get(f"{line}.0", f"{line}.end")
            # Find the first space after the offset (which separates offset from hex data)
            space_pos = text_line.find('  ')
            if space_pos == -1:
                return
            offset_hex = text_line[:space_pos].strip()
            # Handle empty string (offset 0 case)
            if not offset_hex:
                base = 0
            else:
                base = int(offset_hex, 16)
            # hex starts after offset and spaces (variable position now)
            hex_start = space_pos + 2  # Skip the two spaces

            # Only allow editing in the hex area
            if col < hex_start:
                return

            # Calculate which byte we're editing
            col_in_line = col - hex_start
            token_idx = col_in_line // 3
            if token_idx >= self.bytes_per_line:
                return

            byte_offset = base + token_idx

            # Check if it's a valid hex character
            if event.char.upper() in '0123456789ABCDEF':
                # Get current byte value
                current_byte = self._get_slice(byte_offset, 1)
                if current_byte:
                    current_hex = current_byte.hex().upper()
                    # Determine if we're editing the first or second nibble
                    nibble_pos = (col_in_line % 3)
                    if nibble_pos == 0:  # First character of byte
                        new_hex = event.char + current_hex[1]
                    elif nibble_pos == 1:  # Second character of byte
                        new_hex = current_hex[0] + event.char
                    else:
                        return  # Space or invalid position

                    # Convert to byte and write
                    new_byte = bytes.fromhex(new_hex)
                    self._write_slice(byte_offset, new_byte)
                    self.refresh_view()
                    self.update_selection_info(byte_offset, 1)

                    # Move cursor to next nibble or byte
                    if nibble_pos == 0:
                        self.hex_text.mark_set(tk.INSERT, f"{line}.{col + 1}")
                    else:
                        next_byte_col = col + 2  # Skip space
                        if next_byte_col < len(text_line):
                            self.hex_text.mark_set(tk.INSERT, f"{line}.{next_byte_col}")
                        else:
                            # Move to next line
                            next_line = line + 1
                            if next_line < int(self.hex_text.index(tk.END).split(".")[0]):
                                self.hex_text.mark_set(tk.INSERT, f"{next_line}.{hex_start}")

        except Exception as e:
            # Silently ignore invalid edits
            pass

    def on_selection(self, event=None):
        try:
            sel = self.hex_text.tag_ranges("sel")
            if not sel:
                self.update_selection_info(None, None)
                return
            start = sel[0]
            s_line = int(str(start).split(".")[0])
            s_col = int(str(start).split(".")[1])
            end = sel[1]
            e_line = int(str(end).split(".")[0])
            e_col = int(str(end).split(".")[1])
            # map start and end to offsets similarly as click
            start_off = self._text_pos_to_offset(s_line, s_col)
            end_off = self._text_pos_to_offset(e_line, e_col)
            if start_off is None or end_off is None:
                self.update_selection_info(None, None)
                return
            if end_off < start_off:
                start_off, end_off = end_off, start_off
            self.update_selection_info(start_off, end_off - start_off + 1)
        except Exception:
            self.update_selection_info(None, None)

    def select_all(self):
        """Handle Ctrl+A to select the entire file"""
        total_len = self._get_len()
        if total_len > 0:
            self.update_selection_info(0, total_len)
            # Always highlight the entire text - this is what Ctrl+A should do
            # Use after() to defer the highlighting to avoid blocking the UI
            self.after(10, lambda: self._highlight_all_text())
            self.hex_text.see("1.0")

    def _highlight_all_text(self):
        """Highlight all text in the widget (deferred to avoid UI blocking)"""
        try:
            self.hex_text.tag_add("sel", "1.0", tk.END)
        except Exception:
            # If highlighting fails for any reason, at least the selection info is updated
            pass

    def _text_pos_to_offset(self, line, col):
        try:
            text_line = self.hex_text.get(f"{line}.0", f"{line}.end")
            # Find the first space after the offset (which separates offset from hex data)
            space_pos = text_line.find('  ')
            if space_pos == -1:
                return None
            offset_hex = text_line[:space_pos].strip()
            # Handle empty string (offset 0 case)
            if not offset_hex:
                base = 0
            else:
                base = int(offset_hex, 16)
            # hex starts after offset and spaces (variable position now)
            hex_start = space_pos + 2  # Skip the two spaces
            # find token column
            col_in_line = col - hex_start
            if col_in_line < 0:
                return None
            token_idx = max(0, min(self.bytes_per_line - 1, col_in_line // 3))
            return base + token_idx
        except Exception:
            return None

    def update_selection_info(self, start, length):
        if start is None:
            self.offset_label.config(text="Offset: -")
            self.length_label.config(text="Length: -")
            self.current_selection = (None, None)
            self._clear_converters()
            return
        self.current_selection = (start, length)
        # Use firmware-specific width if detected, otherwise adapt to file size
        if self.firmware_type:
            formatted_offset = format_offset(start, self._get_len(), base=16, min_width=self.firmware_type['width'],
                                           max_width=self.firmware_type['width'], clamp_profile="none")
        else:
            formatted_offset = format_offset(start, self._get_len(), base=16, clamp_profile="firmware")
        self.offset_label.config(text=f"Offset: 0x{formatted_offset} ({start})")
        self.length_label.config(text=f"Length: {length}")
        self.refresh_converters()
        self.refresh_live_strings()

    def _on_focus_out(self, event=None):
        """Preserve selection when focus is lost"""
        try:
            sel = self.hex_text.tag_ranges("sel")
            if sel:
                start_idx = sel[0]
                end_idx = sel[1]
                self.preserved_selection = (start_idx, end_idx)
                # Apply persistent selection tag to keep it visible
                self.hex_text.tag_add("persistent_sel", start_idx, end_idx)
        except Exception:
            pass

    def _on_focus_in(self, event=None):
        """Restore selection when focus is regained"""
        if self.preserved_selection:
            try:
                start_idx, end_idx = self.preserved_selection
                # Remove persistent tag and restore normal selection
                self.hex_text.tag_remove("persistent_sel", start_idx, end_idx)
                self.hex_text.tag_add("sel", start_idx, end_idx)
                self.preserved_selection = None
            except Exception:
                pass

    def _clear_converters(self):
        self.int_label.config(text="Integer:")
        self.float32_label.config(text="Float32:")
        self.float64_label.config(text="Float64:")
        self.utf8_label.config(text="UTF-8:")
        self.utf16_label.config(text="UTF-16:")
        self.utf32_label.config(text="UTF-32:")
        self.hex_label.config(text="Hex:")
        self._clear_live_strings()

    # Converters
    def refresh_converters(self):
        sel = self.current_selection
        if sel[0] is None:
            self._clear_converters()
            return
        start, length = sel
        try:
            raw = self._get_slice(start, length)
        except Exception:
            raw = b""
        # Endian
        endian = self.endian_var.get()
        self.endian_display.config(text=f"Endian: {endian}")
        # Integer - limit display for large selections to prevent conversion errors
        if len(raw) > 8:  # Only show integer conversion for reasonable sizes
            self.int_label.config(text="Integer: (selection too large)")
        else:
            try:
                endian_fixed = endian if isinstance(endian, str) and endian in ["little", "big"] else "big"
                val_unsigned = int.from_bytes(raw, byteorder=endian_fixed, signed=False) if raw else 0  # type: ignore
                val_signed = int.from_bytes(raw, byteorder=endian_fixed, signed=True) if raw else 0  # type: ignore
                if self.int_signed_var.get():
                    self.int_label.config(text=f"Integer: {val_signed} (signed)")
                else:
                    self.int_label.config(text=f"Integer: {val_unsigned} (unsigned)")
            except Exception:
                self.int_label.config(text="Integer: -")
        # Floats: attempt if length matches 4 or 8 or can be trimmed/padded
        if len(raw) >= 4:
            try:
                b4 = raw[:4] if endian == "big" else raw[:4][::-1]
                f32 = struct.unpack(">f" if endian == "big" else "<f", raw[:4])[0]
                self.float32_label.config(text=f"Float32: {f32}")
            except Exception:
                self.float32_label.config(text="Float32: -")
        else:
            self.float32_label.config(text="Float32: -")
        if len(raw) >= 8:
            try:
                f64 = struct.unpack(">d" if endian == "big" else "<d", raw[:8])[0]
                self.float64_label.config(text=f"Float64: {f64}")
            except Exception:
                self.float64_label.config(text="Float64: -")
        else:
            self.float64_label.config(text="Float64: -")
        # Strings
        try:
            s_utf8 = raw.decode("utf-8", errors="replace")
            self.utf8_label.config(text=f"UTF-8: {s_utf8}")
        except Exception:
            self.utf8_label.config(text="UTF-8: -")
        try:
            s_utf16 = raw.decode("utf-16le" if endian == "little" else "utf-16be", errors="replace")
            self.utf16_label.config(text=f"UTF-16: {s_utf16}")
        except Exception:
            self.utf16_label.config(text="UTF-16: -")
        try:
            s_utf32 = raw.decode("utf-32le" if endian == "little" else "utf-32be", errors="replace")
            self.utf32_label.config(text=f"UTF-32: {s_utf32}")
        except Exception:
            self.utf32_label.config(text="UTF-32: -")
        # Hex
        self.hex_label.config(text=f"Hex: {self.to_hex(raw)}")

    def extract_strings(self, data: bytes, min_len: int = 4) -> List[Tuple[int, str]]:
        """Extract printable strings with their offsets from binary data"""
        strings = []
        current = ""
        start_offset = 0
        for i, byte in enumerate(data):
            if 32 <= byte <= 126:  # printable ASCII
                if not current:
                    start_offset = i
                current += chr(byte)
            else:
                if len(current) >= min_len:
                    strings.append((start_offset, current))
                current = ""
        if len(current) >= min_len:
            strings.append((start_offset, current))
        return strings

    def refresh_live_strings(self):
        """Update the live string extraction display"""
        sel = self.current_selection
        if sel[0] is None:
            self._clear_live_strings()
            return

        start, length = sel
        try:
            # Get a larger context around the selection for string extraction
            context_start = max(0, start - 256)  # Look 256 bytes before
            context_end = min(self._get_len(), start + length + 256)  # Look 256 bytes after
            context_data = self._get_slice(context_start, context_end - context_start)

            # Extract strings from the context
            strings = self.extract_strings(context_data, min_len=4)

            # Filter strings that are near the selection
            relevant_strings = []
            for offset, s in strings[:10]:  # Limit to first 10 strings
                actual_pos = context_start + offset
                # Include strings that overlap with or are close to selection
                if (actual_pos <= start + length and actual_pos + len(s) >= start) or \
                    (abs(actual_pos - start) < 50) or \
                    (abs((actual_pos + len(s)) - (start + length)) < 50):
                    # Use firmware-specific width if detected, otherwise adapt to file size
                    if self.firmware_type:
                        formatted_offset = format_offset(actual_pos, self._get_len(), base=16,
                                                       min_width=self.firmware_type['width'],
                                                       max_width=self.firmware_type['width'],
                                                       clamp_profile="none")
                    else:
                        formatted_offset = format_offset(actual_pos, self._get_len(), base=16, clamp_profile='firmware')
                    relevant_strings.append(f"0x{formatted_offset}: {s}")

            # Update the text widget with formatted columns
            self.strings_text.config(state="normal")
            self.strings_text.delete("1.0", tk.END)
            if relevant_strings:
                for string_info in relevant_strings:
                    if ": " in string_info:
                        offset, string_text = string_info.split(": ", 1)
                        # Format as tab-separated columns
                        formatted_line = f"{offset}\t{string_text}"
                        self.strings_text.insert(tk.END, formatted_line + "\n")
            else:
                self.strings_text.insert("1.0", "No extractable strings found in selection context")
            self.strings_text.config(state="disabled")

        except Exception as e:
            self._clear_live_strings()

    def _clear_live_strings(self):
        """Clear the live strings display"""
        self.strings_text.config(state="normal")
        self.strings_text.delete("1.0", tk.END)
        self.strings_text.insert("1.0", "Select bytes to see extractable strings")
        self.strings_text.config(state="disabled")

    def set_endian(self, e):
        self.endian = e
        self.endian_var.set(e)
        self.refresh_converters()

    def copy_hex_to_clipboard(self):
        sel = self.current_selection
        if sel[0] is None:
            return
        raw = self._get_slice(sel[0], sel[1])
        self.clipboard_clear()
        self.clipboard_append(self.to_hex(raw))
        self.set_status("Hex copied to clipboard")

    # Byte editing UI
    def write_bytes_from_entry(self):
        txt = self.byte_entry.get().strip()
        if not txt:
            return
        # parse space/comma/hex string
        tokens = [t for t in txt.replace(",", " ").split() if t]
        try:
            bts = bytes(int(t, 16) for t in tokens)
        except Exception as e:
            messagebox.showerror("Parse error", f"Could not parse bytes: {e}")
            return
        sel = self.current_selection
        if sel[0] is None:
            messagebox.showwarning("No selection", "Select an offset first by clicking a byte or using Go To")
            return
        start, length = sel
        # write
        self._write_slice(start, bts)
        self.refresh_view()
        # Use firmware-specific width if detected, otherwise adapt to file size
        if self.firmware_type:
            formatted_offset = format_offset(start, self._get_len(), base=16, min_width=self.firmware_type['width'],
                                           max_width=self.firmware_type['width'], clamp_profile="none")
        else:
            formatted_offset = format_offset(start, self._get_len(), base=16, clamp_profile="firmware")
        self.set_status(f"Wrote {len(bts)} bytes at 0x{formatted_offset}")

    # Undo / Redo
    def undo(self):
        if not self.undo_stack:
            return
        op = self.undo_stack.pop()
        typ = op[0]
        if typ == "write":
            start, old_bytes = op[1], op[2]
            # store redo
            cur = self._get_slice(start, len(old_bytes))
            self.redo_stack.append(("write", start, cur))
            # restore old
            if self.mmap_file:
                self.mmap_file[start:start + len(old_bytes)] = old_bytes
            else:
                if self.data:
                    self.data[start:start + len(old_bytes)] = old_bytes
            self.refresh_view()
            self.set_status("Undo")
        else:
            self.set_status("Unknown undo operation")

    def redo(self):
        if not self.redo_stack:
            return
        op = self.redo_stack.pop()
        typ = op[0]
        if typ == "write":
            start, bts = op[1], op[2]
            old = self._get_slice(start, len(bts))
            self.undo_stack.append(("write", start, old))
            if self.mmap_file:
                self.mmap_file[start:start + len(bts)] = bts
            else:
                if self.data:
                    self.data[start:start + len(bts)] = bts
            self.refresh_view()
            self.set_status("Redo")

    # Find / Replace / Goto
    def find_dialog(self):
        # Create a persistent find dialog
        if hasattr(self, 'find_window') and self.find_window.winfo_exists():
            self.find_window.lift()
            return

        find_window = tk.Toplevel(self)
        find_window.title("Find (hex or text)")
        find_window.geometry("450x200")
        self.find_window = find_window

        ttk.Label(find_window, text="Pattern (hex bytes space-separated or text):").pack(pady=5)
        find_entry = ttk.Entry(find_window, width=50)
        find_entry.pack(pady=5)

        is_hex_var = tk.BooleanVar(value=False)  # Default to text search
        ttk.Checkbutton(find_window, text="Hex input", variable=is_hex_var).pack(pady=5)

        # Occurrence counter label
        self.occurrence_label = ttk.Label(find_window, text="")
        self.occurrence_label.pack(pady=5)

        # Buttons frame
        button_frame = ttk.Frame(find_window)
        button_frame.pack(pady=10)

        def do_find():
            pattern = find_entry.get().strip()
            if not pattern:
                return
            result = (pattern, is_hex_var.get())
            # Process the find result
            self._process_find_result(result)

        ttk.Button(button_frame, text="Find", command=do_find).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Previous", command=self.find_previous).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Next", command=self.find_next).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=find_window.destroy).pack(side=tk.LEFT, padx=5)

        find_entry.focus_set()
        find_window.transient(self.winfo_toplevel())
        find_window.protocol("WM_DELETE_WINDOW", lambda: setattr(self, 'find_window', None))

    def _process_find_result(self, result):
        pattern, is_hex = result
        data = self._get_slice(0, self._get_len())
        if is_hex:
            try:
                pat = bytes(int(x, 16) for x in pattern.split())
            except ValueError:
                messagebox.showerror("Invalid Hex", "Invalid hex pattern. Each byte should be 2 hex digits (00-FF) separated by spaces.")
                return
        else:
            pat = pattern.encode("utf-8")

        # Store current pattern for highlighting
        self.current_find_pattern = pat

        # Find all occurrences
        self.find_occurrences = []
        start = 0
        while True:
            idx = data.find(pat, start)
            if idx == -1:
                break
            self.find_occurrences.append(idx)
            start = idx + len(pat)

        if not self.find_occurrences:
            self.occurrence_label.config(text="No occurrences found")
            messagebox.showinfo("Find", "Pattern not found")
            return

        # Initialize current occurrence index
        self.current_occurrence = 0
        self._goto_occurrence(self.current_occurrence)

    def _goto_occurrence(self, index):
        if not hasattr(self, 'find_occurrences') or not self.find_occurrences:
            return

        idx = self.find_occurrences[index]
        # Get the actual pattern length from the stored pattern
        if hasattr(self, 'current_find_pattern'):
            pat_len = len(self.current_find_pattern)
        else:
            pat_len = 1  # Fallback

        # Highlight the current occurrence
        self._highlight_occurrence(idx, pat_len)

        # Update view and selection
        self.offset_top = max(0, idx - 256)
        self.refresh_view()
        self.update_selection_info(idx, pat_len)
        # Use firmware-specific width if detected, otherwise adapt to file size
        if self.firmware_type:
            formatted_offset = format_offset(idx, self._get_len(), base=16, min_width=self.firmware_type['width'],
                                           max_width=self.firmware_type['width'], clamp_profile="none")
        else:
            formatted_offset = format_offset(idx, self._get_len(), base=16, clamp_profile="firmware")
        self.set_status(f"Found at 0x{formatted_offset}")

        # Update occurrence counter
        self.occurrence_label.config(text=f"{index + 1} of {len(self.find_occurrences)}")

    def _highlight_occurrence(self, offset, length):
        """Highlight a specific occurrence in the hex view"""
        # Clear previous highlights
        self.hex_text.tag_remove("find_highlight", "1.0", tk.END)

        # Calculate which lines contain this occurrence
        bytes_per_line = self.bytes_per_line
        start_line = offset // bytes_per_line
        end_line = (offset + length - 1) // bytes_per_line

        for line_idx in range(start_line, end_line + 1):
            line_start_offset = line_idx * bytes_per_line
            line_end_offset = min(line_start_offset + bytes_per_line, self._get_len())

            # Find the range within this line
            occ_start = max(offset, line_start_offset)
            occ_end = min(offset + length, line_end_offset)

            if occ_start < occ_end:
                # Get the actual line text to find hex start position
                text_line = self.hex_text.get(f"{line_idx + 1}.0", f"{line_idx + 1}.end")
                space_pos = text_line.find('  ')
                hex_start = space_pos + 2 if space_pos != -1 else 10  # fallback to old position

                # Convert to text positions
                char_start = hex_start + (occ_start - line_start_offset) * 3  # 3 chars per byte (XX + space)
                char_end = hex_start + (occ_end - line_start_offset) * 3 - 1  # -1 to exclude trailing space

                self.hex_text.tag_add("find_highlight", f"{line_idx + 1}.{char_start}", f"{line_idx + 1}.{char_end}")

        # Configure highlight tag
        self.hex_text.tag_config("find_highlight", background="yellow", foreground="black")

    def find_next(self):
        if not hasattr(self, 'find_occurrences') or not self.find_occurrences:
            return
        self.current_occurrence = (self.current_occurrence + 1) % len(self.find_occurrences)
        self._goto_occurrence(self.current_occurrence)

    def find_previous(self):
        if not hasattr(self, 'find_occurrences') or not self.find_occurrences:
            return
        self.current_occurrence = (self.current_occurrence - 1) % len(self.find_occurrences)
        self._goto_occurrence(self.current_occurrence)

    def replace_dialog(self):
        # Create a simple replace dialog
        replace_window = tk.Toplevel(self)
        replace_window.title("Replace (hex or text)")
        replace_window.geometry("400x200")

        ttk.Label(replace_window, text="Find (hex bytes space-separated or text):").pack(pady=2)
        find_entry = ttk.Entry(replace_window, width=50)
        find_entry.pack(pady=2)

        ttk.Label(replace_window, text="Replace with (hex bytes space-separated or text):").pack(pady=2)
        replace_entry = ttk.Entry(replace_window, width=50)
        replace_entry.pack(pady=2)

        is_hex_var = tk.BooleanVar(value=False)  # Default to text search
        ttk.Checkbutton(replace_window, text="Hex input", variable=is_hex_var).pack(pady=5)

        def do_replace():
            find_pat = find_entry.get().strip()
            replace_pat = replace_entry.get().strip()
            if not find_pat:
                messagebox.showerror("Error", "Find pattern cannot be empty")
                return
            result = (find_pat, replace_pat, is_hex_var.get())
            replace_window.destroy()
            # Process the replace result
            self._process_replace_result(result)

        ttk.Button(replace_window, text="Replace All", command=do_replace).pack(pady=10)
        find_entry.focus_set()
        replace_window.transient(self.winfo_toplevel())
        replace_window.grab_set()
        self.wait_window(replace_window)

    def _process_replace_result(self, result):
        find_pat, replace_pat, is_hex = result
        data = bytearray(self._get_slice(0, self._get_len()))
        if is_hex:
            src = bytes(int(x, 16) for x in find_pat.split())
            dst = bytes(int(x, 16) for x in replace_pat.split())
        else:
            src = find_pat.encode("utf-8")
            dst = replace_pat.encode("utf-8")
        count = 0
        i = data.find(src)
        while i != -1:
            # do replace
            data[i:i + len(src)] = dst
            count += 1
            i = data.find(src, i + len(dst))
        # write back
        if count > 0:
            self.undo_stack.append(("write", 0, bytes(self._get_slice(0, self._get_len()))))
            if self.mmap_file:
                self.mmap_file[:] = data
            else:
                if self.data:
                    self.data[:] = data
            self.refresh_view()
            self.set_status(f"Replaced {count} occurrences")
        else:
            messagebox.showinfo("Replace", "No occurrences found")

    def goto_dialog(self):
        s = simpledialog.askstring("Go To", "Enter offset (hex or dec):")
        if not s:
            return
        try:
            off = int(s, 0)
            if off < 0 or off >= self._get_len():
                raise ValueError("Out of range")
            self.offset_top = max(0, off - 32)
            self.refresh_view()
            self.update_selection_info(off, 1)
            # Update status with firmware-specific width if detected, otherwise adapt to file size
            if self.firmware_type:
                formatted_offset = format_offset(off, self._get_len(), base=16, min_width=self.firmware_type['width'],
                                               max_width=self.firmware_type['width'], clamp_profile="none")
            else:
                formatted_offset = format_offset(off, self._get_len(), base=16, clamp_profile="firmware")
            self.set_status(f"Goto: 0x{formatted_offset}")
        except Exception as e:
            messagebox.showerror("Go To", f"Invalid offset: {e}")

    # Analysis tools
    def entropy_analysis(self):
        sel = self.current_selection
        if sel[0] is None:
            data = self._get_slice(0, self._get_len())
        else:
            data = self._get_slice(sel[0], sel[1])
        ent = self.calc_entropy(data)
        if MATPLOTLIB:
            # plot sliding window entropy
            window = 4096
            ent_vals = []
            xs = []
            for i in range(0, max(1, len(data) - window), window):
                ent_vals.append(self.calc_entropy(data[i:i + window]))
                xs.append(i)
            import matplotlib.pyplot as plt
            plt.figure(figsize=(8, 3))
            plt.plot(xs, ent_vals)
            plt.title(f"Entropy (selection/file) — {ent:.4f}")
            plt.xlabel("Offset")
            plt.ylabel("Entropy")
            plt.show()
        else:
            # fallback: text summary
            messagebox.showinfo("Entropy", f"Entropy: {ent:.6f}")

    def show_strings(self):
        """Show enhanced strings dialog with search capabilities"""
        sel = self.current_selection
        if sel[0] is None:
            data = self._get_slice(0, self._get_len())
            data_offset = 0
        else:
            data = self._get_slice(sel[0], sel[1])
            data_offset = sel[0]

        # Use threading to prevent UI freeze during string extraction
        def extract_strings_thread():
            try:
                self.set_status("Extracting strings...")
                if self.progress_callback:
                    self.progress_callback.start()

                strings_with_offsets = []
                strings = self.extract_strings(data, min_len=4)
                for s_offset, s_string in strings: # Corrected to unpack tuple
                    # Find all occurrences of this string in the data
                    try:
                        string_bytes = s_string.encode('utf-8', errors='ignore')
                        pos = 0
                        while True:
                            pos = data.find(string_bytes, pos)
                            if pos == -1:
                                break
                            strings_with_offsets.append((data_offset + pos, s_string))
                            pos += len(string_bytes)
                    except:
                        continue

                # Sort by offset
                strings_with_offsets.sort(key=lambda x: x[0])

                # Create enhanced dialog (non-modal so selection updates work)
                def create_dialog():
                    dlg = EnhancedStringsDialog(self, strings_with_offsets, self._get_len(), hex_editor=self)
                    self.set_status("Ready")
                    # Refocus on hex editor after dialog creation
                    self.after(100, lambda: self.hex_text.focus_set())

                self.after(0, create_dialog)

            except Exception as e:
                self.log_callback(f"String extraction failed: {e}", 'error')
                self.set_status("Ready")
            finally:
                if self.progress_callback:
                    self.progress_callback.stop()

        threading.Thread(target=extract_strings_thread, daemon=True).start()

    def byte_histogram(self):
        sel = self.current_selection
        if sel[0] is None:
            data = self._get_slice(0, self._get_len())
        else:
            data = self._get_slice(sel[0], sel[1])
        freq = [0] * 256
        for b in data:
            freq[b] += 1
        if MATPLOTLIB:
            import matplotlib.pyplot as plt
            plt.bar(range(256), freq, width=1.0)
            plt.title("Byte histogram")
            plt.show()
        else:
            # textual top 16
            items = sorted(((i, freq[i]) for i in range(256)), key=lambda x: -x[1])[:20]
            text = "\n".join(f"{i:02X}: {c}" for i, c in items)
            dlg = TextOutputDialog(self, "Byte histogram (top 20)", text)
            self.wait_window(dlg)

    # Utility
    def set_status(self, text):
        self.status.config(text=text)
        self.status_callback.config(text=text)

    def on_exit(self):
        if self.modified and messagebox.askyesno("Exit", "File modified. Save before exit?"):
            self.save_file()

    # Utility functions (moved from global scope)
    def to_hex(self, byte_arr, sep=" "):
        return sep.join(f"{b:02X}" for b in byte_arr)

    def ascii_repr(self, byte_arr):
        return "".join(chr(b) if 32 <= b < 127 else "." for b in byte_arr)

    def read_file_bytes(self, path, use_mmap=True):
        size = os.path.getsize(path)
        if use_mmap and size > 0:
            f = open(path, "r+b")
            mm = mmap.mmap(f.fileno(), 0)
            return mm, f  # caller must close both
        else:
            with open(path, "rb") as f:
                return bytearray(f.read()), None

    def calc_entropy(self, data: bytes):
        if not data:
            return 0.0
        freq = {}
        for b in data:
            freq[b] = freq.get(b, 0) + 1
        ent = 0.0
        length = len(data)
        for v in freq.values():
            p = v / length
            ent -= p * math.log2(p)
        return ent

    def to_int(self, data_bytes: bytes, signed=False, byteorder="big"):
        if not data_bytes:
            return 0
        byteorder_fixed = byteorder if isinstance(byteorder, str) and byteorder in ["little", "big"] else "big"
        return int.from_bytes(data_bytes, byteorder=byteorder_fixed, signed=signed)  # type: ignore

    def to_float(self, data_bytes: bytes, fmt=">f"):
        try:
            return struct.unpack(fmt, data_bytes)[0]
        except Exception:
            return None

# -------------------------
# GUI: Enhanced Strings Dialog
# -----------------------------
class EnhancedStringsDialog(tk.Toplevel):
    """Enhanced strings dialog with search, navigation, and regex support"""

    def __init__(self, parent, strings_with_offsets: List[Tuple[int, str]], file_size: int, hex_editor=None):
        super().__init__(parent)
        self.title("Enhanced Strings Analysis")
        self.geometry("1000x700")
        self.resizable(True, True)

        self.strings_with_offsets = strings_with_offsets
        self.file_size = file_size
        self.hex_editor = hex_editor
        self.firmware_type = hex_editor.firmware_type if hex_editor else None
        self.filtered_strings = strings_with_offsets.copy()
        self.current_index = -1
        self.search_history = []
        self.search_index = -1
        self.predictive_suggestions = []

        self._build_ui()
        self._populate_strings()
        self._bind_shortcuts()
        self._setup_predictive_search()

    def _build_ui(self):
        # Main frame
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Search frame
        search_frame = ttk.LabelFrame(main_frame, text="Search & Navigation")
        search_frame.pack(fill=tk.X, pady=(0, 10))

        # Search controls
        controls_frame = ttk.Frame(search_frame)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)

        ttk.Label(controls_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(controls_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry.bind('<KeyRelease>', self._on_search_key_release)

        # Search options
        options_frame = ttk.Frame(controls_frame)
        options_frame.pack(side=tk.LEFT, padx=(10, 0))

        self.regex_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Regex", variable=self.regex_var,
                       command=self._perform_search).pack(side=tk.LEFT, padx=(0, 10))

        self.case_sensitive_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Case Sensitive", variable=self.case_sensitive_var,
                       command=self._perform_search).pack(side=tk.LEFT, padx=(0, 10))

        self.whole_word_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Whole Word", variable=self.whole_word_var,
                       command=self._perform_search).pack(side=tk.LEFT, padx=(0, 10))

        # Predictive search checkbox
        self.predictive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Predictive", variable=self.predictive_var,
                       command=self._toggle_predictive_search).pack(side=tk.LEFT)

        # Navigation buttons
        nav_frame = ttk.Frame(controls_frame)
        nav_frame.pack(side=tk.RIGHT)

        self.prev_btn = ttk.Button(nav_frame, text="◀ Previous", command=self._goto_previous,
                                  state=tk.DISABLED)
        self.prev_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.next_btn = ttk.Button(nav_frame, text="Next ▶", command=self._goto_next,
                                  state=tk.DISABLED)
        self.next_btn.pack(side=tk.LEFT)

        # Status label
        self.status_label = ttk.Label(search_frame, text=f"Total strings: {len(self.strings_with_offsets)}")
        self.status_label.pack(anchor=tk.W, padx=5, pady=(0, 5))

        # Strings list frame
        list_frame = ttk.LabelFrame(main_frame, text="Strings")
        list_frame.pack(fill=tk.BOTH, expand=True)

        # Create treeview for strings
        columns = ('offset', 'hex_offset', 'length', 'string')
        self.strings_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=20)

        # Configure columns
        self.strings_tree.heading('offset', text='Offset (Dec)')
        self.strings_tree.heading('hex_offset', text='Offset (Hex)')
        self.strings_tree.heading('length', text='Length')
        self.strings_tree.heading('string', text='String')

        self.strings_tree.column('offset', width=100, anchor=tk.E)
        self.strings_tree.column('hex_offset', width=100, anchor=tk.E)
        self.strings_tree.column('length', width=80, anchor=tk.E)
        self.strings_tree.column('string', width=600)

        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.strings_tree.yview)
        self.strings_tree.configure(yscrollcommand=v_scrollbar.set)

        # Pack treeview and scrollbars
        self.strings_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind events
        self.strings_tree.bind('<Double-1>', self._on_string_double_click)
        self.strings_tree.bind('<Return>', self._on_string_select)

        # Bottom buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(btn_frame, text="Copy Selected", command=self._copy_selected).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="Export to File", command=self._export_to_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side=tk.RIGHT)

    def _bind_shortcuts(self):
        self.bind('<Control-f>', lambda e: self.search_entry.focus_set())
        self.bind('<F3>', self._goto_next)
        self.bind('<Shift-F3>', self._goto_previous)
        self.bind('<Escape>', lambda e: self.destroy())

    def _populate_strings(self):
        """Populate the strings treeview"""
        # Clear existing items
        for item in self.strings_tree.get_children():
            self.strings_tree.delete(item)

        # Add strings
        for offset, string in self.filtered_strings:
            hex_offset = f"0x{offset:08X}"
            length = len(string)
            self.strings_tree.insert('', tk.END, values=(offset, hex_offset, length, string))

        # Update status with formatted offset info
        if self.filtered_strings:
            first_offset = self.filtered_strings[0][0]
            last_offset = self.filtered_strings[-1][0]
            formatted_first = format_offset(first_offset, self.file_size, base=16, clamp_profile="firmware")
            formatted_last = format_offset(last_offset, self.file_size, base=16, clamp_profile="firmware")
            self.status_label.config(text=f"Showing {len(self.filtered_strings)} of {len(self.strings_with_offsets)} strings (0x{formatted_first} - 0x{formatted_last})")
        else:
            self.status_label.config(text=f"Showing {len(self.filtered_strings)} of {len(self.strings_with_offsets)} strings")

    def _on_search_key_release(self, event):
        """Handle search input changes"""
        if event.keysym in ('Up', 'Down'):
            return  # Handle arrow keys separately for history

        # Update predictive suggestions
        self._update_predictive_suggestions()

        # Debounce search to avoid too many updates
        if hasattr(self, '_search_timer'):
            self.after_cancel(self._search_timer)

        self._search_timer = self.after(300, self._perform_search)

    def _perform_search(self):
        """Perform the actual search with recursive binary search optimization"""
        search_text = self.search_var.get().strip()
        is_regex = self.regex_var.get()
        case_sensitive = self.case_sensitive_var.get()
        whole_word = self.whole_word_var.get()

        if not search_text:
            self.filtered_strings = self.strings_with_offsets.copy()
        else:
            self.filtered_strings = []
            flags = 0 if case_sensitive else re.IGNORECASE

            try:
                if is_regex:
                    # Use full JavaScript-compatible regex syntax
                    if whole_word:
                        pattern = re.compile(r'\b' + search_text + r'\b', flags)
                    else:
                        pattern = re.compile(search_text, flags)
                else:
                    # For non-regex searches, escape special characters and optionally add word boundaries
                    escaped_text = re.escape(search_text)
                    if whole_word:
                        pattern = re.compile(r'\b' + escaped_text + r'\b', flags)
                    else:
                        pattern = re.compile(escaped_text, flags)

                # Use recursive binary search for large datasets
                if len(self.strings_with_offsets) > 1000:
                    self.filtered_strings = self._recursive_binary_search(
                        self.strings_with_offsets, pattern, 0, len(self.strings_with_offsets) - 1
                    )
                else:
                    # Linear search for smaller datasets
                    for offset, string in self.strings_with_offsets:
                        if pattern.search(string):
                            self.filtered_strings.append((offset, string))

            except re.error as e:
                self.status_label.config(text=f"Regex error: {e}")
                return

        self._populate_strings()
        self._update_navigation_buttons()

        # Select first match if any
        if self.filtered_strings:
            first_item = self.strings_tree.get_children()[0]
            self.strings_tree.selection_set(first_item)
            self.strings_tree.focus(first_item)
            self.current_index = 0

    def _recursive_binary_search(self, strings_list, pattern, left, right):
        """Recursive binary search for string matching"""
        if left > right:
            return []

        mid = (left + right) // 2
        offset, string = strings_list[mid]

        # Check if current string matches
        matches = []
        if pattern.search(string):
            matches.append((offset, string))

        # Search left half
        left_matches = self._recursive_binary_search(strings_list, pattern, left, mid - 1)

        # Search right half
        right_matches = self._recursive_binary_search(strings_list, pattern, mid + 1, right)

        # Combine results: left matches + current match + right matches
        return left_matches + matches + right_matches

    def _update_navigation_buttons(self):
        """Update navigation button states"""
        has_matches = len(self.filtered_strings) > 0
        self.prev_btn.config(state=tk.NORMAL if has_matches else tk.DISABLED)
        self.next_btn.config(state=tk.NORMAL if has_matches else tk.DISABLED)

    def _goto_next(self, event=None):
        """Go to next match"""
        if not self.filtered_strings:
            return

        children = self.strings_tree.get_children()
        if not children:
            return

        # Get current selection
        selection = self.strings_tree.selection()
        if selection:
            current_item = selection[0]
            current_idx = children.index(current_item)
            next_idx = (current_idx + 1) % len(children)
        else:
            next_idx = 0

        next_item = children[next_idx]
        self.strings_tree.selection_set(next_item)
        self.strings_tree.focus(next_item)
        self.strings_tree.see(next_item)
        self.current_index = next_idx

    def _goto_previous(self, event=None):
        """Go to previous match"""
        if not self.filtered_strings:
            return

        children = self.strings_tree.get_children()
        if not children:
            return

        # Get current selection
        selection = self.strings_tree.selection()
        if selection:
            current_item = selection[0]
            current_idx = children.index(current_item)
            prev_idx = (current_idx - 1) % len(children)
        else:
            prev_idx = len(children) - 1

        prev_item = children[prev_idx]
        self.strings_tree.selection_set(prev_item)
        self.strings_tree.focus(prev_item)
        self.strings_tree.see(prev_item)
        self.current_index = prev_idx

    def _on_string_double_click(self, event):
        """Handle double-click on string"""
        selection = self.strings_tree.selection()
        if selection:
            item = selection[0]
            values = self.strings_tree.item(item, 'values')
            offset = int(values[0])
            length = int(values[2])
            # Jump to offset in hex editor and highlight it
            if self.hex_editor and self.hex_editor.file_path:  # Use the passed hex_editor reference
                self.hex_editor.offset_top = max(0, offset - 32)  # Show some context before
                self.hex_editor.refresh_view()
                self.hex_editor.update_selection_info(offset, length)  # Select the full string length
                # Update status with formatted offset
                formatted_offset = format_offset(offset, self.hex_editor._get_len(), base=16, clamp_profile="firmware")
                self.hex_editor.set_status(f"Jumped to string at 0x{formatted_offset}")

    def _on_string_select(self, event):
        """Handle Enter key on selected string"""
        self._on_string_double_click(event)

    def _copy_selected(self):
        """Copy selected strings to clipboard"""
        selection = self.strings_tree.selection()
        if not selection:
            return

        selected_strings = []
        for item in selection:
            values = self.strings_tree.item(item, 'values')
            offset, hex_offset, length, string = values
            # Use firmware-specific width if detected, otherwise adapt to file size
            if self.firmware_type:
                formatted_offset = format_offset(int(offset), self.file_size, base=16,
                                               min_width=self.firmware_type['width'],
                                               max_width=self.firmware_type['width'],
                                               clamp_profile="none")
            else:
                formatted_offset = format_offset(int(offset), self.file_size, base=16, clamp_profile='firmware')
            selected_strings.append(f"0x{formatted_offset}: {string}")

        if selected_strings:
            self.clipboard_clear()
            self.clipboard_append('\n'.join(selected_strings))

    def _setup_predictive_search(self):
        """Setup predictive search functionality"""
        # Create a toplevel window for suggestions
        self.predictive_toplevel = tk.Toplevel(self)
        self.predictive_toplevel.withdraw()  # Initially hidden
        self.predictive_toplevel.overrideredirect(True)  # Remove window decorations
        self.predictive_toplevel.attributes('-topmost', True)  # Keep on top

        # Frame for listbox and scrollbar
        frame = ttk.Frame(self.predictive_toplevel)
        frame.pack(fill=tk.BOTH, expand=True)

        self.predictive_listbox = tk.Listbox(frame, height=10, font=('Consolas', 9), activestyle='none')
        self.predictive_scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.predictive_listbox.yview)
        self.predictive_listbox.configure(yscrollcommand=self.predictive_scrollbar.set)

        self.predictive_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.predictive_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind predictive listbox events
        self.predictive_listbox.bind('<<ListboxSelect>>', self._on_predictive_select)
        self.predictive_listbox.bind('<Double-1>', self._on_predictive_select)
        self.predictive_listbox.bind('<Return>', self._on_predictive_select)
        self.predictive_listbox.bind('<Escape>', self._hide_predictive)
        self.predictive_listbox.bind('<FocusOut>', self._hide_predictive)

        # Position predictive toplevel below search entry
        self.search_entry.bind('<FocusOut>', self._hide_predictive)

    def _toggle_predictive_search(self):
        """Toggle predictive search on/off"""
        if self.predictive_var.get():
            self._setup_predictive_search()
        else:
            if hasattr(self, 'predictive_toplevel'):
                self.predictive_toplevel.withdraw()

    def _update_predictive_suggestions(self):
        """Update predictive search suggestions"""
        if not self.predictive_var.get():
            return

        search_text = self.search_var.get().strip().lower()
        if len(search_text) < 2:
            self._hide_predictive()
            return

        # Find suggestions from current strings
        suggestions = set()
        for _, string in self.strings_with_offsets:
            if string.lower().startswith(search_text):
                suggestions.add(string)
            elif search_text in string.lower():
                # Also include partial matches
                start_idx = string.lower().find(search_text)
                # Extract word containing the match
                word_start = string.rfind(' ', 0, start_idx) + 1
                word_end = string.find(' ', start_idx + len(search_text))
                if word_end == -1:
                    word_end = len(string)
                word = string[word_start:word_end]
                if word:
                    suggestions.add(word)

        self.predictive_suggestions = sorted(list(suggestions))[:10]  # Limit to 10 suggestions

        if self.predictive_suggestions:
            self._show_predictive()
        else:
            self._hide_predictive()

    def _show_predictive(self):
        """Show predictive suggestions"""
        if not self.predictive_suggestions:
            return

        # Position below search entry
        x = self.search_entry.winfo_rootx()
        y = self.search_entry.winfo_rooty() + self.search_entry.winfo_height()

        self.predictive_listbox.delete(0, tk.END)
        for suggestion in self.predictive_suggestions:
            self.predictive_listbox.insert(tk.END, suggestion)

        # Set width to match search entry, height based on number of items (max 200px)
        width = self.search_entry.winfo_width()
        height = min(len(self.predictive_suggestions) * 20 + 10, 200)  # 20px per item + padding

        self.predictive_toplevel.geometry(f"{width}x{height}+{x}+{y}")
        self.predictive_toplevel.deiconify()
        self.predictive_toplevel.lift()
        self.predictive_listbox.focus_set()

    def _hide_predictive(self, event=None):
        """Hide predictive suggestions"""
        if hasattr(self, 'predictive_toplevel'):
            self.predictive_toplevel.withdraw()

    def _on_predictive_select(self, event):
        """Handle predictive suggestion selection"""
        selection = self.predictive_listbox.curselection()
        if selection:
            selected_text = self.predictive_listbox.get(selection[0])
            self.search_var.set(selected_text)
            self._hide_predictive()
            self._perform_search()
            self.search_entry.focus_set()
            self.search_entry.icursor(tk.END)  # Move cursor to end

    def _export_to_file(self):
        """Export strings to file"""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not filename:
            return

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("Offset (Dec),Offset (Hex),Length,String\n")
                for offset, string in self.filtered_strings:
                    hex_offset = f"0x{offset:08X}"
                    length = len(string)
                    # Escape commas and quotes in CSV
                    escaped_string = string.replace('"', '""')
                    if ',' in escaped_string or '"' in escaped_string:
                        escaped_string = f'"{escaped_string}"'
                    # Use firmware-specific width if detected, otherwise adapt to file size
                    if self.firmware_type:
                        hex_offset_formatted = format_offset(int(offset), self.file_size, base=16,
                                                           min_width=self.firmware_type['width'],
                                                           max_width=self.firmware_type['width'],
                                                           clamp_profile="none")
                    else:
                        hex_offset_formatted = format_offset(int(offset), self.file_size, base=16, clamp_profile="firmware")
                    f.write(f"{offset},0x{hex_offset_formatted},{length},{escaped_string}\n")

            messagebox.showinfo("Export Complete", f"Exported {len(self.filtered_strings)} strings to {filename}")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")

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
        self.configure(menu=menubar)
        
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

        try:
            if self.regex_var.get():
                pattern = re.compile(search_text, flags)
            else:
                pattern = re.compile(re.escape(search_text), flags)
        except re.error:
            messagebox.showerror("Regex Error", "Invalid regular expression")
            return []

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
class SmartphoneFirmwareScrews(tk.Tk):
    """Main application window"""
    def __init__(self):
        super().__init__()
        startup_logger.info("SmartphoneFirmwareScrews: __init__ started.")
        self.title(f"{APP_TITLE} v{VERSION}")
        self.geometry("1400x900")
        self.configure(bg=COLORS['bg_primary'])

        self.current_project: Optional[Project] = None
        self.port_rom_config: Optional[PortRomConfig] = None

        startup_logger.info("SmartphoneFirmwareScrews: Calling _setup_style.")
        self._setup_style()
        startup_logger.info("SmartphoneFirmwareScrews: Calling _build_menu.")
        self._build_menu()
        startup_logger.info("SmartphoneFirmwareScrews: Calling _build_toolbar.")
        self._build_toolbar()
        startup_logger.info("SmartphoneFirmwareScrews: Calling _build_statusbar.")
        self._build_statusbar()
        startup_logger.info("SmartphoneFirmwareScrews: Calling _build_workspace.")
        self._build_workspace()

        self.bind('<Control-o>', lambda e: self.open_firmware())
        self.bind('<Control-s>', lambda e: self.save_project())
        self.bind('<Control-n>', lambda e: self.new_project())
        self.bind('<F5>', lambda e: self.refresh_tools())
        startup_logger.info("SmartphoneFirmwareScrews: __init__ finished.")
    
    def _setup_style(self):
        startup_logger.debug("SmartphoneFirmwareScrews: _setup_style started.")
        style = ttk.Style(self)
        style.theme_use('clam')

        style.configure('TFrame', background=COLORS['bg_card'])
        style.configure('TLabel', background=COLORS['bg_card'], foreground=COLORS['text_primary'])
        style.configure('TButton', background=COLORS['accent_blue'], foreground='white')
        style.map('TButton', background=[('active', COLORS['accent_orange'])])

        style.configure('Accent.TButton', background=COLORS['accent_orange'])
        style.configure('Success.TButton', background=COLORS['accent_green'])
        style.configure('Danger.TButton', background=COLORS['accent_red'])

        style.configure('TLabelframe', background=COLORS['bg_card'], foreground=COLORS['text_primary'])

        style.configure('Treeview', background=COLORS['bg_tertiary'],
                        foreground=COLORS['text_primary'],
                        fieldbackground=COLORS['bg_tertiary'])

        # Professional progress bar styling
        style.configure('TProgressbar',
                        background=COLORS['accent_blue'],
                        troughcolor=COLORS['bg_secondary'],
                        borderwidth=1,
                        lightcolor=COLORS['accent_blue'],
                        darkcolor=COLORS['accent_blue'])
        startup_logger.debug("SmartphoneFirmwareScrews: _setup_style finished.")
    
    def _build_menu(self):
        startup_logger.debug("SmartphoneFirmwareScrews: _build_menu started.")
        menubar = tk.Menu(self, bg=COLORS['bg_secondary'], fg=COLORS['text_primary'], font=('Segoe UI', 12))
        self.config(menu=menubar)
        # Note: Frame doesn't have config(menu=), this is handled by the parent window

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
        
        port_rom_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Port ROM", menu=port_rom_menu)
        port_rom_menu.add_command(label="Step 1: Extract Firmware", command=self.switch_to_port_rom_tab)
        port_rom_menu.add_command(label="Step 2: Unpack Boot Images", command=lambda: self.switch_to_port_rom_tab(step=2))
        port_rom_menu.add_command(label="Step 3: Modify Ramdisk", command=lambda: self.switch_to_port_rom_tab(step=3))
        port_rom_menu.add_command(label="Step 4: Repack Boot Image", command=lambda: self.switch_to_port_rom_tab(step=4))
        port_rom_menu.add_command(label="Step 5: Extract System/Vendor Images", command=lambda: self.switch_to_port_rom_tab(step=5))
        
        flash_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Flash", menu=flash_menu)
        flash_menu.add_command(label="Detect Device", command=self.detect_device)
        flash_menu.add_command(label="Flash via Heimdall", command=self.flash_heimdall)

        hex_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Hex Editor", menu=hex_menu)
        hex_menu.add_command(label="Open File", command=self.hex_editor_open_file, accelerator="Ctrl+O")
        hex_menu.add_command(label="Save", command=self.hex_editor_save, accelerator="Ctrl+S")
        hex_menu.add_command(label="Save As", command=self.hex_editor_save_as)
        hex_menu.add_separator()
        hex_menu.add_command(label="Find", command=self.hex_editor_find, accelerator="Ctrl+F")
        hex_menu.add_command(label="Replace", command=self.hex_editor_replace, accelerator="Ctrl+H")
        hex_menu.add_command(label="Go To", command=self.hex_editor_goto, accelerator="Ctrl+G")
        hex_menu.add_separator()
        hex_menu.add_command(label="Entropy Analysis", command=self.hex_editor_entropy)
        hex_menu.add_command(label="Extract Strings", command=self.hex_editor_strings)
        hex_menu.add_command(label="Byte Histogram", command=self.hex_editor_histogram)
        
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
        startup_logger.debug("SmartphoneFirmwareScrews: _build_toolbar finished.")
    
    def _build_workspace(self):
        startup_logger.debug("SmartphoneFirmwareScrews: _build_workspace started.")
        self.workspace = ttk.PanedWindow(self, orient='vertical')
        self.workspace.pack(fill='both', expand=True, padx=5, pady=5)

        # Initial split: workspace and log
        self.main_pane = ttk.PanedWindow(self.workspace, orient='horizontal')
        self.workspace.add(self.main_pane, weight=3)

        # Log at bottom
        log_frame = ttk.LabelFrame(self.workspace, text="Activity Log", padding=5)
        self.workspace.add(log_frame, weight=1)

        # Set minimum height for log frame to prevent squishing
        log_frame.configure(height=200)  # Minimum height of 300 pixels
        log_frame.pack_propagate(False)  # Prevent the frame from shrinking below its configured size

        self.log_console = LogConsole(log_frame)
        self.log_console.pack(fill='both', expand=True)
        startup_logger.debug("SmartphoneFirmwareScrews: _build_workspace finished.")
        
        # Initial content in main pane
        self._add_notebook_to_pane(self.main_pane)
    
    def _add_notebook_to_pane(self, pane):
        startup_logger.debug("SmartphoneFirmwareScrews: _add_notebook_to_pane started.")
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

        # Hex Editor tab
        hex_editor_frame = ttk.Frame(notebook)
        notebook.add(hex_editor_frame, text="Hex Editor")
        self._build_hex_editor_ui(hex_editor_frame)

        # Store progress bar reference for hex editor
        self.hex_editor_progress = self.progress

        # Tools tab
        tools_frame = ttk.Frame(notebook)
        notebook.add(tools_frame, text="Tools")
        self._build_tools_ui(tools_frame)

        # Port ROM tab
        port_rom_frame = ttk.Frame(notebook)
        notebook.add(port_rom_frame, text="Port ROM")
        self._build_port_rom_ui(port_rom_frame)
    
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
        self.file_editor_tree.bind("<Button-1>", self._on_file_editor_file_single_click)
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
                                                      bg=COLORS['log_bg'], fg=COLORS['log_fg'],
                                                      state=tk.NORMAL, insertbackground=COLORS['text_primary'])
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
        # Skip syntax highlighting for large files to prevent UI freezing
        content = self.file_editor.get('1.0', tk.END)
        if len(content) > 1000000:  # 1MB limit for syntax highlighting
            return

        # Clear all existing tags
        for tag in self.file_editor.tag_names():
            if tag != 'sel':  # Don't remove selection tag
                self.file_editor.tag_remove(tag, '1.0', tk.END)

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
            file_size = os.path.getsize(file_path)
            self.after(0, lambda: self.status_label.config(text=f"Loading {os.path.basename(file_path)}..."))
            self.after(0, lambda: self.progress.start())

            # Check file size and handle large files differently
            if file_size > 50 * 1024 * 1024:  # 50MB limit
                self.after(0, lambda: messagebox.showwarning("Large File Warning",
                    f"File is {file_size / (1024*1024):.1f} MB. Loading may be slow.\n\n"
                    "Consider using an external editor for files larger than 50MB."))
                return

            # Read file in chunks to avoid UI freezing on large files
            content = ""
            chunk_size = 16384  # 16KB chunks for better performance
            max_content_size = 10 * 1024 * 1024  # 10MB max content to display

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                bytes_read = 0
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    content += chunk
                    bytes_read += len(chunk)

                    # Limit content size to prevent memory issues
                    if len(content) > max_content_size:
                        content = content[:max_content_size] + "\n\n[FILE TRUNCATED - Content too large to display fully]"
                        self.after(0, lambda: self.log(f"File truncated at {max_content_size} characters", 'warning'))
                        break

                    # Update progress for large files (>1MB)
                    if file_size > 1024 * 1024:
                        progress = min(100, int((bytes_read / file_size) * 100))
                        self.after(0, lambda p=progress: self.progress.config(value=p))

                    # Yield control more frequently for very large files
                    if file_size > 10 * 1024 * 1024:  # >10MB
                        time.sleep(0.01)  # Longer sleep for responsiveness
                    else:
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
        # Disable updates during content insertion for better performance
        self.file_editor.config(state=tk.NORMAL)
        self.file_editor.delete('1.0', tk.END)
        self.file_editor.insert('1.0', content)
        self.current_file = file_path
        # Only apply syntax highlighting for smaller files
        if len(content) <= 1000000:  # 1MB limit
            self._apply_syntax_highlighting()
        # Ensure the editor remains editable and focused
        self.file_editor.config(state=tk.NORMAL)
        self.file_editor.focus_set()
        self.file_editor.mark_set(tk.INSERT, '1.0')
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

    def _open_file_editor_entry_with_lock(self, item):
        """Wrapper to handle loading lock"""
        try:
            self._open_file_editor_entry(item)
        finally:
            self._loading_file = False

    def _on_file_editor_file_double_click(self, event):
        item = self.file_editor_tree.selection()[0]
        if item:
            # Check if file is already being loaded to prevent multiple loads
            if hasattr(self, '_loading_file') and self._loading_file:
                return
            self._loading_file = True
            # Use threading to prevent UI freezing
            threading.Thread(target=self._open_file_editor_entry_with_lock, args=(item,), daemon=True).start()

    def _on_file_editor_file_single_click(self, event):
        """Handle single click to prevent accidental multiple loads"""
        # Optional: could add logic here if needed
        pass

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

            # Get content and handle large files efficiently
            content = self.file_editor.get('1.0', tk.END).rstrip() + '\n'

            # Write in chunks for large files to prevent memory issues
            chunk_size = 65536  # 64KB chunks
            with open(self.current_file, 'w', encoding='utf-8') as f:
                for i in range(0, len(content), chunk_size):
                    f.write(content[i:i + chunk_size])

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

            # Check file size before reloading
            file_size = os.path.getsize(self.current_file)
            if file_size > 50 * 1024 * 1024:  # 50MB limit
                messagebox.showwarning("Large File Warning",
                    f"File is {file_size / (1024*1024):.1f} MB. Reload may be slow.")
                return

            with open(self.current_file, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(10 * 1024 * 1024)  # Limit to 10MB for display
                if len(content) == 10 * 1024 * 1024 and f.read(1):  # Check if more content exists
                    content += "\n\n[FILE TRUNCATED - Content too large to display fully]"

            self.file_editor.config(state=tk.NORMAL)
            self.file_editor.delete('1.0', tk.END)
            self.file_editor.insert('1.0', content)
            # Only apply syntax highlighting for smaller files
            if len(content) <= 1000000:
                self._apply_syntax_highlighting()
            self.file_editor.focus_set()
            self.file_editor.mark_set(tk.INSERT, '1.0')
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

    def _build_hex_editor_ui(self, parent):
        # Specific UI for hex editor
        # Pass the main app's status_label method instead of the label itself
        self.hex_editor_widget = HexEditorWidget(parent, self.log, lambda text: self.status_label.config(text=text), self.progress)
        self.hex_editor_widget.pack(fill='both', expand=True)
        # Store reference for menu commands
        self.hex_editor_widget_ref = self.hex_editor_widget
    
    def switch_to_port_rom_tab(self, step: int = 1):
        """Switch to the Port ROM tab and optionally set initial step focus"""
        self._port_rom_initial_step = step # Store the desired step
        for pane_child in self.main_pane.winfo_children():
            if isinstance(pane_child, ttk.Notebook):
                notebook = pane_child
                for i, tab_id in enumerate(notebook.tabs()):
                    if notebook.tab(tab_id, "text") == "Port ROM":
                        notebook.select(i)
                        # Rebuild UI to apply step focus logic
                        self._build_port_rom_ui(notebook.nametowidget(tab_id), step=self._port_rom_initial_step)
                        return

    def _build_port_rom_ui(self, parent, step: int = 1):
        # Clear existing widgets in the tab before rebuilding
        for widget in parent.winfo_children():
            widget.destroy()

        # Main frame for the Port ROM tab
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill='both', expand=True)

        # Create a scrollable canvas with vertical scrollbar
        canvas = tk.Canvas(main_frame, bg=COLORS['bg_card'], highlightthickness=0, scrollregion=(0, 0, 0, 0))
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding=10)

        # Create window in canvas and get its ID for later reference
        window_id = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        # Configure scroll region and canvas window sizing
        def _configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Update canvas window width to fill available space (minus scrollbar)
            canvas_width = canvas.winfo_width()
            if canvas_width > 0:
                # Leave space for the scrollbar
                canvas.itemconfig(window_id, width=canvas_width - scrollbar.winfo_width() if scrollbar.winfo_exists() else canvas_width)

        scrollable_frame.bind("<Configure>", _configure_scroll_region)
        
        # Configure canvas after it's mapped
        def _configure_canvas(event):
            canvas_width = canvas.winfo_width()
            if canvas_width > 0:
                canvas.itemconfig(window_id, width=canvas_width - scrollbar.winfo_width() if scrollbar.winfo_exists() else canvas_width)
        
        canvas.bind('<Configure>', _configure_canvas)

        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack the canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mouse wheel to scroll the canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        scrollable_frame.bind("<Enter>", _bind_mousewheel)
        scrollable_frame.bind("<Leave>", _unbind_mousewheel)

        # --- Step 1: Firmware Extraction ---
        step1_frame = ttk.LabelFrame(scrollable_frame, text="Step 1: Extract Base and Port Firmware", padding=10)
        step1_frame.pack(fill='x', pady=5, anchor='n')

        # Source Device (the device you're porting FROM)
        ttk.Label(step1_frame, text="Source Device Model (e.g., A336, S21, etc.):").grid(row=0, column=0, sticky='w', pady=2)
        self.port_rom_source_device = tk.StringVar()
        ttk.Entry(step1_frame, textvariable=self.port_rom_source_device, width=30).grid(row=1, column=0, sticky='w', padx=(0, 10))

        # Target Device (the device you're porting TO)
        ttk.Label(step1_frame, text="Target Device Model (e.g., A325, A32, etc.):").grid(row=0, column=1, sticky='w', pady=2)
        self.port_rom_target_device = tk.StringVar()
        ttk.Entry(step1_frame, textvariable=self.port_rom_target_device, width=30).grid(row=1, column=1, sticky='w')

        # Base Firmware (the ROM you want to port)
        ttk.Label(step1_frame, text="Source Firmware Directory (the ROM you want to port):").grid(row=2, column=0, columnspan=2, sticky='w', pady=(10, 2))
        self.port_rom_base_dir = tk.StringVar()
        ttk.Entry(step1_frame, textvariable=self.port_rom_base_dir, width=80).grid(row=3, column=0, columnspan=2, sticky='ew', padx=(0, 5))
        ttk.Button(step1_frame, text="Browse...", command=lambda: self._browse_dir(self.port_rom_base_dir)).grid(row=3, column=2, sticky='w')

        # Port Firmware (the stock ROM for your device)
        ttk.Label(step1_frame, text="Target Firmware Directory (the stock ROM for your target device):").grid(row=4, column=0, columnspan=2, sticky='w', pady=(10, 2))
        self.port_rom_port_dir = tk.StringVar()
        ttk.Entry(step1_frame, textvariable=self.port_rom_port_dir, width=80).grid(row=5, column=0, columnspan=2, sticky='ew', padx=(0, 5))
        ttk.Button(step1_frame, text="Browse...", command=lambda: self._browse_dir(self.port_rom_port_dir)).grid(row=5, column=2, sticky='w')

        step1_frame.grid_columnconfigure(0, weight=1)
        step1_frame.grid_columnconfigure(1, weight=1)

        # Action button
        action_frame = ttk.Frame(scrollable_frame)
        action_frame.pack(fill='x', pady=10)
        ttk.Button(action_frame, text="Start Firmware Extraction", command=self._start_firmware_extraction, style='Accent.TButton').pack()

        # --- Step 2: Boot Image Unpacking ---
        step2_frame = ttk.LabelFrame(scrollable_frame, text="Step 2: Unpack Boot Images", padding=10)
        step2_frame.pack(fill='x', pady=5, anchor='n')

        ttk.Label(step2_frame, text="This step will unpack the boot.img and extract the ramdisk for both Base and Port firmware.").pack(anchor='w', pady=5)
        ttk.Button(step2_frame, text="Start Boot Image Unpacking", command=self._start_boot_image_unpacking, style='Accent.TButton').pack(pady=5)

        # Scroll to specific step if requested
        if step == 2:
            # Scroll to the requested step
            self.after(100, lambda: self._scroll_to_step(canvas, step))

        # --- Step 3: Ramdisk Modification ---
        step3_frame = ttk.LabelFrame(scrollable_frame, text="Step 3: Modify Ramdisk for Porting", padding=10)
        step3_frame.pack(fill='x', pady=5, anchor='n')

        ttk.Label(step3_frame, text="This step will modify the Base firmware ramdisk to work with the Port firmware hardware.").pack(anchor='w', pady=5)
        ttk.Button(step3_frame, text="Start Ramdisk Modification", command=self._start_ramdisk_modification, style='Accent.TButton').pack(pady=5)

        # Scroll to specific step if requested
        if step == 3:
            # Scroll to the requested step
            self.after(100, lambda: self._scroll_to_step(canvas, step))

        # --- Step 4: Repack Boot Image ---
        step4_frame = ttk.LabelFrame(scrollable_frame, text="Step 4: Repack Boot Image", padding=10)
        step4_frame.pack(fill='x', pady=5, anchor='n')

        ttk.Label(step4_frame, text="This step will repack the boot image with the modified ramdisk to create a new boot.img for the ported ROM.").pack(anchor='w', pady=5)
        ttk.Button(step4_frame, text="Start Boot Image Repacking", command=self._start_boot_repacking, style='Accent.TButton').pack(pady=5)

        # Scroll to specific step if requested
        if step == 4:
            # Scroll to the requested step
            self.after(100, lambda: self._scroll_to_step(canvas, step))

        # --- Step 5: System and Vendor Image Extraction ---
        step5_frame = ttk.LabelFrame(scrollable_frame, text="Step 5: Extract System and Vendor Images", padding=10)
        step5_frame.pack(fill='x', pady=5, anchor='n')

        ttk.Label(step5_frame, text="This step will extract and mount system and vendor images from both Base and Port firmware for comparison.").pack(anchor='w', pady=5)
        ttk.Button(step5_frame, text="Start System/Vendor Extraction", command=self._start_system_vendor_extraction, style='Accent.TButton').pack(pady=5)

        # Scroll to specific step if requested
        if step == 5:
            # Scroll to the requested step
            self.after(100, lambda: self._scroll_to_step(canvas, step))

        # --- Step 6: Vendor Partition Modification ---
        step6_frame = ttk.LabelFrame(scrollable_frame, text="Step 6: Modify Vendor Partition", padding=10)
        step6_frame.pack(fill='x', pady=5, anchor='n')

        ttk.Label(step6_frame, text="This step will replace critical hardware HALs and firmware from the Port device for hardware compatibility.").pack(anchor='w', pady=5)
        ttk.Button(step6_frame, text="Start Vendor Modification", command=self._start_vendor_modification, style='Accent.TButton').pack(pady=5)

        # Scroll to specific step if requested
        if step == 6:
            # Scroll to the requested step
            self.after(100, lambda: self._scroll_to_step(canvas, step))

        # --- Step 7: System Partition Modification ---
        step7_frame = ttk.LabelFrame(scrollable_frame, text="Step 7: Modify System Partition", padding=10)
        step7_frame.pack(fill='x', pady=5, anchor='n')

        ttk.Label(step7_frame, text="This step will update system properties and device identifiers to match the Port device.").pack(anchor='w', pady=5)
        ttk.Button(step7_frame, text="Start System Modification", command=self._start_system_modification, style='Accent.TButton').pack(pady=5)

        # Scroll to specific step if requested
        if step == 7:
            # Scroll to the requested step
            self.after(100, lambda: self._scroll_to_step(canvas, step))

        # --- Step 8: Image Repacking ---
        step8_frame = ttk.LabelFrame(scrollable_frame, text="Step 8: Repack Images", padding=10)
        step8_frame.pack(fill='x', pady=5, anchor='n')

        ttk.Label(step8_frame, text="This step will repack the modified partitions into flashable images and prepare them for Odin.").pack(anchor='w', pady=5)
        ttk.Button(step8_frame, text="Start Image Repacking", command=self._start_image_repacking, style='Accent.TButton').pack(pady=5)

        # Scroll to specific step if requested
        if step == 8:
            # Scroll to the requested step
            self.after(100, lambda: self._scroll_to_step(canvas, step))

        # --- Step 9: Create Odin Package ---
        step9_frame = ttk.LabelFrame(scrollable_frame, text="Step 9: Create Odin Package", padding=10)
        step9_frame.pack(fill='x', pady=5, anchor='n')

        ttk.Label(step9_frame, text="This step will create a complete Odin flashable package with AP, BL, CP, and CSC components.").pack(anchor='w', pady=5)
        ttk.Button(step9_frame, text="Create Odin Package", command=self._start_odin_package_creation, style='Accent.TButton').pack(pady=5)

        # Scroll to specific step if requested
        if step == 9:
            # Scroll to the requested step
            self.after(100, lambda: self._scroll_to_step(canvas, step))

        # --- Step 10: Validate Package ---
        step10_frame = ttk.LabelFrame(scrollable_frame, text="Step 10: Validate Package", padding=10)
        step10_frame.pack(fill='x', pady=5, anchor='n')

        ttk.Label(step10_frame, text="This step will validate the Odin package for completeness, integrity, and safety before flashing.").pack(anchor='w', pady=5)
        ttk.Button(step10_frame, text="Validate Package", command=self._start_package_validation, style='Accent.TButton').pack(pady=5)

        # Scroll to specific step if requested
        if step == 10:
            # Scroll to the requested step
            self.after(100, lambda: self._scroll_to_step(canvas, step))

    def _scroll_to_step(self, canvas, step):
        """Scroll canvas to bring the requested step into view"""
        # Calculate the position of the target step
        # Each step frame is roughly 100-150 pixels tall with padding
        step_height = 120
        target_y = (step - 1) * step_height
        
        # Use after to ensure the canvas is fully rendered
        canvas.update_idletasks()
        canvas.yview_moveto(max(0, (target_y - 50) / max(1, canvas.bbox("all")[3] - canvas.winfo_height())))
        
        self.log(f"Navigated to Port ROM tab, intended to focus on Step {step}.", 'info')

    def _browse_dir(self, var: tk.StringVar):
        path = filedialog.askdirectory()
        if path:
            var.set(path)

    def _start_firmware_extraction(self):
        source_device = self.port_rom_source_device.get().strip()
        target_device = self.port_rom_target_device.get().strip()
        base_dir = self.port_rom_base_dir.get()
        port_dir = self.port_rom_port_dir.get()

        if not source_device or not target_device:
            messagebox.showerror("Error", "Please enter both source and target device models.")
            return

        if not base_dir or not port_dir:
            messagebox.showerror("Error", "Please select both firmware directories.")
            return

        if not os.path.isdir(base_dir) or not os.path.isdir(port_dir):
            messagebox.showerror("Error", "One or both selected paths are not valid directories.")
            return

        # Create device-agnostic configuration
        self.port_rom_config = PortRomConfig(
            source_device=source_device,
            target_device=target_device,
            source_firmware_dir=base_dir,
            target_firmware_dir=port_dir,
            work_dir=os.path.join(os.getcwd(), "firmware_port")
        )

        threading.Thread(target=self._extract_firmware_for_porting_thread,
                         args=(base_dir, port_dir), daemon=True).start()

    def _extract_tar_md5_for_porting(self, tar_md5_path: str, extract_to_dir: str):
        self.log(f"[*] Extracting {os.path.basename(tar_md5_path)}")
        tmp_tar = tempfile.mktemp(suffix=".tar")
        try:
            strip_md5_footer(tar_md5_path, tmp_tar)
            bsdtar = tool_resolve("bsdtar")
            if bsdtar:
                result = run_cmd([bsdtar, "-xf", tmp_tar, "-C", extract_to_dir])
                if result.returncode == 0:
                    return
            # Fallback to 7z
            seven_z = tool_resolve("7z")
            if seven_z:
                result = run_cmd([seven_z, "x", tmp_tar, f"-o{extract_to_dir}"])
                if result.returncode == 0:
                    return
            raise RuntimeError("Could not extract tar archive")
        finally:
            if os.path.exists(tmp_tar):
                os.remove(tmp_tar)

    def _extract_firmware_for_porting_thread(self, base_dir: str, port_dir: str):
        import os
        import shutil
        if not hasattr(self, 'port_rom_config') or not self.port_rom_config:
            self.log("[!] No port ROM configuration found", 'error')
            self.after(0, lambda: messagebox.showerror("Error", "Port ROM configuration not initialized"))
            return

        config = self.port_rom_config
        work_dir = config.work_dir
        self.log(f"[*] Starting firmware extraction. Working directory: {work_dir}")

        # Create working directory structure using device-agnostic paths
        base_work_dir = config.get_work_subdir(config.source_device, "")
        port_work_dir = config.get_work_subdir(config.target_device, "")
        ensure_dir(config.get_extracted_dir(config.source_device))
        ensure_dir(config.get_extracted_dir(config.target_device))

        try:
            self.status_label.config(text="Extracting firmware...")
            self.progress.start()

            # --- Extract Source Firmware ---
            self.log(f"[*] Extracting {config.source_device} firmware...")
            for pattern in ["AP_*.tar.md5", "BL_*.tar.md5", "CP_*.tar.md5", "CSC_*.tar.md5", "HOME_CSC_*.tar.md5"]:
                files = glob.glob(os.path.join(base_dir, pattern))
                for file_path in files:
                    self._extract_tar_md5_for_porting(file_path, config.get_extracted_dir(config.source_device))
                    if "CP_" in os.path.basename(file_path):
                        shutil.copy(file_path, os.path.join(base_work_dir, "CP_original.tar.md5"))

            # --- Extract Target Firmware ---
            self.log(f"[*] Extracting {config.target_device} firmware...")
            for pattern in ["AP_*.tar.md5", "BL_*.tar.md5", "CP_*.tar.md5", "CSC_*.tar.md5", "HOME_CSC_*.tar.md5"]:
                files = glob.glob(os.path.join(port_dir, pattern))
                for file_path in files:
                    self._extract_tar_md5_for_porting(file_path, config.get_extracted_dir(config.target_device))
                    if "BL_" in os.path.basename(file_path):
                        shutil.copy(file_path, os.path.join(port_work_dir, "BL_original.tar.md5"))
                    if "CP_" in os.path.basename(file_path):
                        shutil.copy(file_path, os.path.join(port_work_dir, "CP_original.tar.md5"))

            self.log("[*] Firmware extraction complete.", 'success')
            self.log(f"[*] {config.source_device} extracted to: {config.get_extracted_dir(config.source_device)}")
            self.log(f"[*] {config.target_device} extracted to: {config.get_extracted_dir(config.target_device)}")
            self.after(0, lambda: messagebox.showinfo("Success", "Firmware extraction complete!"))

        except Exception as e:
            self.log(f"[!] Error during extraction: {e}", 'error')
            self.after(0, lambda: messagebox.showerror("Error", f"An error occurred during extraction: {e}"))
        finally:
            self.status_label.config(text="Ready")
            self.progress.stop()

    def _start_boot_image_unpacking(self):
        work_dir = os.path.join(os.getcwd(), "firmware_port")
        base_extracted_dir = os.path.join(work_dir, "base", "extracted")
        port_extracted_dir = os.path.join(work_dir, "port", "extracted")

        if not os.path.isdir(base_extracted_dir) or not os.path.isdir(port_extracted_dir):
            messagebox.showerror("Error", "Firmware not extracted. Please complete Step 1 first.")
            return

        threading.Thread(target=self._unpack_boot_images_thread, daemon=True).start()

    def _unpack_boot_images_thread(self):
        if not hasattr(self, 'port_rom_config') or not self.port_rom_config:
            self.log("[!] No port ROM configuration found", 'error')
            self.after(0, lambda: messagebox.showerror("Error", "Port ROM configuration not initialized"))
            return

        config: PortRomConfig = self.port_rom_config  # Type assertion for Pylance
        self.log("[*] Starting boot image unpacking...")

        # Get device-specific directories from config
        source_boot_dir = config.get_boot_dir(config.source_device)
        target_boot_dir = config.get_boot_dir(config.target_device)
        source_extracted_dir = config.get_extracted_dir(config.source_device)
        target_extracted_dir = config.get_extracted_dir(config.target_device)

        ensure_dir(source_boot_dir)
        ensure_dir(target_boot_dir)

        try:
            self.status_label.config(text="Unpacking boot images...")
            self.progress.start()
            self.log("[*] Starting boot image unpacking...", 'info')

            # --- Unpack Source Boot Image ---
            self.log(f"[*] Unpacking {self.port_rom_config.source_device} boot.img...")
            boot_source_path = glob.glob(os.path.join(source_extracted_dir, "boot.img*"))
            if not boot_source_path:
                self.log(f"[!] boot.img not found in {self.port_rom_config.source_device} firmware", 'error')
                raise FileNotFoundError(f"boot.img not found in {self.port_rom_config.source_device} firmware")
            boot_source_file = boot_source_path[0]
            shutil.copy(boot_source_file, os.path.join(source_boot_dir, "boot.img"))

            unpack_boot_img(os.path.join(source_boot_dir, "boot.img"), source_boot_dir)
            self.log(f"[*] {self.port_rom_config.source_device} boot.img unpacked to: {source_boot_dir}", 'success')

            # Extract ramdisk for Source
            self._extract_ramdisk_from_boot_dir(source_boot_dir)

            # --- Unpack Target Boot Image ---
            self.log(f"[*] Unpacking {self.port_rom_config.target_device} boot.img...")
            boot_target_path = glob.glob(os.path.join(target_extracted_dir, "boot.img*"))
            if not boot_target_path:
                self.log(f"[!] boot.img not found in {self.port_rom_config.target_device} firmware", 'error')
                raise FileNotFoundError(f"boot.img not found in {self.port_rom_config.target_device} firmware")
            boot_target_file = boot_target_path[0]
            shutil.copy(boot_target_file, os.path.join(target_boot_dir, "boot.img"))

            unpack_boot_img(os.path.join(target_boot_dir, "boot.img"), target_boot_dir)
            self.log(f"[*] {self.port_rom_config.target_device} boot.img unpacked to: {target_boot_dir}", 'success')

            # Extract ramdisk for Target
            self._extract_ramdisk_from_boot_dir(target_boot_dir)

            self.log("[*] Boot image unpacking complete.", 'success')
            self.log(f"[*] {self.port_rom_config.source_device} kernel: {os.path.join(source_boot_dir, 'kernel')}")
            self.log(f"[*] {self.port_rom_config.target_device} kernel: {os.path.join(target_boot_dir, 'kernel')}")
            self.log(f"[*] {self.port_rom_config.source_device} ramdisk: {os.path.join(source_boot_dir, 'ramdisk')}")
            self.log(f"[*] {self.port_rom_config.target_device} ramdisk: {os.path.join(target_boot_dir, 'ramdisk')}")
            self.after(0, lambda: messagebox.showinfo("Success", "Boot image unpacking complete!"))

        except Exception as e:
            self.log(f"[!] Error during boot image unpacking: {e}", 'error')
            self.after(0, lambda: messagebox.showerror("Error", f"An error occurred during boot image unpacking: {e}"))
        finally:
            self.status_label.config(text="Ready")
            self.progress.stop()

    def _extract_ramdisk_from_boot_dir(self, boot_dir: str):
        ramdisk_cpio = os.path.join(boot_dir, "ramdisk.cpio")
        ramdisk_cpio_gz = os.path.join(boot_dir, "ramdisk.cpio.gz")
        ramdisk_out_dir = os.path.join(boot_dir, "ramdisk")
        ensure_dir(ramdisk_out_dir)

        if os.path.exists(ramdisk_cpio):
            self.log(f"[*] Extracting {ramdisk_cpio}...", 'info')
            extract_ramdisk(ramdisk_cpio, ramdisk_out_dir)
            self.log(f"[*] Ramdisk extracted to {ramdisk_out_dir}", 'success')
        elif os.path.exists(ramdisk_cpio_gz):
            self.log(f"[*] Decompressing and extracting {ramdisk_cpio_gz}...", 'info')
            # Use piping like the bash script: gzip -dc ramdisk.cpio.gz | cpio -idm
            cpio = tool_resolve("cpio")
            if cpio:
                try:
                    with open(ramdisk_cpio_gz, 'rb') as f_in:
                        gz_data = gzip.decompress(f_in.read())
                        result = run_cmd([cpio, "-idm"], cwd=ramdisk_out_dir, input_data=gz_data)
                        if result.returncode == 0:
                            self.log(f"[*] Ramdisk extracted to {ramdisk_out_dir}", 'success')
                        else:
                            raise RuntimeError("cpio extraction failed")
                except Exception as e:
                    self.log(f"[!] Failed to decompress or extract ramdisk.cpio.gz: {e}", 'error')
            else:
                # Fallback to temporary file method
                tmp_cpio = tempfile.mktemp(suffix=".cpio")
                try:
                    with open(ramdisk_cpio_gz, 'rb') as f_in, gzip.open(tmp_cpio, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)
                    extract_ramdisk(tmp_cpio, ramdisk_out_dir)
                    self.log(f"[*] Ramdisk extracted to {ramdisk_out_dir}", 'success')
                except Exception as e:
                    self.log(f"[!] Failed to decompress or extract ramdisk.cpio.gz: {e}", 'error')
                finally:
                    if os.path.exists(tmp_cpio):
                        os.remove(tmp_cpio)
        else:
            self.log(f"[!] Ramdisk (ramdisk.cpio or ramdisk.cpio.gz) not found in {boot_dir}", 'warning')

    def _start_ramdisk_modification(self):
        """Start the ramdisk modification process"""
        if not hasattr(self, 'port_rom_config') or not self.port_rom_config:
            messagebox.showerror("Error", "Port ROM configuration not found. Please complete Step 1 first.")
            return

        config = self.port_rom_config
        base_ramdisk_dir = os.path.join(config.get_boot_dir(config.source_device), "ramdisk")
        port_ramdisk_dir = os.path.join(config.get_boot_dir(config.target_device), "ramdisk")

        if not os.path.isdir(base_ramdisk_dir) or not os.path.isdir(port_ramdisk_dir):
            messagebox.showerror("Error", "Ramdisk directories not found. Please complete Step 2 first.")
            return

        threading.Thread(target=self._modify_ramdisk_thread,
                        args=(base_ramdisk_dir, port_ramdisk_dir, config), daemon=True).start()

    def _modify_ramdisk_thread(self, base_ramdisk_dir: str, port_ramdisk_dir: str, config: PortRomConfig):
        """Thread to perform ramdisk modification"""
        try:
            self.status_label.config(text="Modifying ramdisk...")
            self.progress.start()
            self.log("[*] Starting ramdisk modification...", 'info')

            # Create backup of original base ramdisk
            backup_dir = os.path.join(os.path.dirname(base_ramdisk_dir), "ramdisk.backup")
            if os.path.exists(backup_dir):
                import shutil
                shutil.rmtree(backup_dir)
            import shutil
            shutil.copytree(base_ramdisk_dir, backup_dir)
            self.log(f"[*] Backup created: {backup_dir}", 'info')

            # Find and replace fstab files
            self.log("[*] Modifying fstab files...")
            self._modify_fstab_files(base_ramdisk_dir, port_ramdisk_dir, config)

            # Modify init scripts
            self.log("[*] Modifying init scripts...")
            self._modify_init_scripts(base_ramdisk_dir, config)

            # Modify property files
            self.log("[*] Modifying property files...")
            self._modify_property_files(base_ramdisk_dir, config)

            # Copy port-specific hardware configurations
            self.log(f"[*] Copying {config.target_device}-specific hardware configurations...")
            self._copy_hardware_configs(base_ramdisk_dir, port_ramdisk_dir, config)

            # Verify critical files
            missing_files = self._verify_critical_files(base_ramdisk_dir)

            if missing_files > 0:
                self.log(f"[!] WARNING: {missing_files} critical files missing. Manual intervention may be required.", 'warning')

            self.log("[*] Ramdisk modification complete.", 'success')
            self.log(f"[*] Modified ramdisk: {base_ramdisk_dir}", 'info')
            self.log(f"[*] Backup: {backup_dir}", 'info')
            self.after(0, lambda: messagebox.showinfo("Success",
                "Ramdisk modification complete!\n\n"
                "IMPORTANT: Review changes manually before repacking:\n"
                "- Verify fstab partition paths match port device\n"
                "- Check init*.rc for hardware-specific services\n"
                "- Confirm device tree files are from port device"))

        except Exception as e:
            self.log(f"[!] Error during ramdisk modification: {e}", 'error')
            self.after(0, lambda: messagebox.showerror("Error", f"An error occurred during ramdisk modification: {e}"))
        finally:
            self.status_label.config(text="Ready")
            self.progress.stop()

    def _modify_fstab_files(self, base_ramdisk_dir: str, port_ramdisk_dir: str, config: PortRomConfig):
        """Modify fstab files in the ramdisk"""
        import glob
        import filecmp

        fstab_patterns = ['fstab.*']
        for pattern in fstab_patterns:
            for fstab_path in glob.glob(os.path.join(base_ramdisk_dir, pattern)):
                filename = os.path.basename(fstab_path)
                self.log(f"[*] Processing {filename}", 'info')

                # Read original content
                with open(fstab_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Apply device-agnostic modifications based on source and target devices
                modifications = [
                    # Device model replacements (case-insensitive)
                    (config.source_device.lower(), config.target_device.lower()),
                    (config.source_device.upper(), config.target_device.upper()),
                    (config.source_device.capitalize(), config.target_device.capitalize()),
                    # Common Samsung model patterns (SM-XXXX)
                    (f'SM-{config.source_device.upper()}', f'SM-{config.target_device.upper()}'),
                    (f'sm-{config.source_device.lower()}', f'sm-{config.target_device.lower()}'),
                    # Chipset replacements (if known, can be extended)
                    # Add more patterns as needed based on device characteristics
                ]

                modified_content = content
                for old, new in modifications:
                    modified_content = modified_content.replace(old, new)

                # Write modified content
                with open(fstab_path, 'w', encoding='utf-8') as f:
                    f.write(modified_content)

                # Check if port device has corresponding fstab for comparison
                port_fstab_path = os.path.join(port_ramdisk_dir, filename)
                if os.path.exists(port_fstab_path):
                    self.log(f"[*] Found matching port fstab, comparing partition layouts...", 'info')
                    try:
                        with open(fstab_path, 'r', encoding='utf-8', errors='ignore') as f:
                            base_partitions = set(re.findall(r'/dev/block/[^\s]+', f.read()))
                        with open(port_fstab_path, 'r', encoding='utf-8', errors='ignore') as f:
                            port_partitions = set(re.findall(r'/dev/block/[^\s]+', f.read()))

                        if base_partitions != port_partitions:
                            self.log("[!] WARNING: Partition layout differences detected", 'warning')
                            self.log("[!] Manual verification required for partition paths", 'warning')
                        else:
                            self.log(f"[*] Partition layouts match for {filename}", 'info')
                    except Exception as e:
                        self.log(f"[!] Error comparing partition layouts: {e}", 'warning')

    def _modify_init_scripts(self, ramdisk_dir: str, config: PortRomConfig):
        """Modify init scripts in the ramdisk"""
        import glob

        init_patterns = ['init*.rc', 'init*']
        for pattern in init_patterns:
            for init_path in glob.glob(os.path.join(ramdisk_dir, pattern)):
                if os.path.isfile(init_path):
                    filename = os.path.basename(init_path)
                    self.log(f"[*] Processing {filename}", 'info')

                    try:
                        # Read original content
                        with open(init_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()

                        # Apply device-agnostic modifications based on source and target devices
                        modifications = [
                            # Device model replacements (case-insensitive)
                            (config.source_device.lower(), config.target_device.lower()),
                            (config.source_device.upper(), config.target_device.upper()),
                            (config.source_device.capitalize(), config.target_device.capitalize()),
                            # Common Samsung model patterns (SM-XXXX)
                            (f'SM-{config.source_device.upper()}', f'SM-{config.target_device.upper()}'),
                            (f'sm-{config.source_device.lower()}', f'sm-{config.target_device.lower()}'),
                            # Add more patterns as needed based on device characteristics
                        ]

                        modified_content = content
                        for old, new in modifications:
                            modified_content = modified_content.replace(old, new)

                        # Write modified content
                        with open(init_path, 'w', encoding='utf-8') as f:
                            f.write(modified_content)

                    except Exception as e:
                        self.log(f"[!] Error processing {filename}: {e}", 'warning')

    def _modify_property_files(self, ramdisk_dir: str, config: PortRomConfig):
        """Modify property files in the ramdisk"""
        import glob

        prop_patterns = ['*.prop', 'default.prop']
        for pattern in prop_patterns:
            for prop_path in glob.glob(os.path.join(ramdisk_dir, pattern)):
                if os.path.isfile(prop_path):
                    filename = os.path.basename(prop_path)
                    self.log(f"[*] Processing {filename}", 'info')

                    try:
                        # Read original content
                        with open(prop_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()

                        # Apply device-agnostic property modifications based on source and target devices
                        modifications = [
                            # Device model replacements (case-insensitive)
                            (f'ro.product.device={config.source_device.lower()}', f'ro.product.device={config.target_device.lower()}'),
                            (f'ro.product.device={config.source_device.upper()}', f'ro.product.device={config.target_device.upper()}'),
                            (f'ro.product.device={config.source_device.capitalize()}', f'ro.product.device={config.target_device.capitalize()}'),
                            # Model name replacements (assuming SM-XXXX format)
                            (f'ro.product.model=SM-{config.source_device.upper()}', f'ro.product.model=SM-{config.target_device.upper()}'),
                            (f'ro.product.name={config.source_device.lower()}', f'ro.product.name={config.target_device.lower()}'),
                            (f'ro.product.name={config.source_device.upper()}', f'ro.product.name={config.target_device.upper()}'),
                            (f'ro.product.name={config.source_device.capitalize()}', f'ro.product.name={config.target_device.capitalize()}'),
                            # Build product replacements
                            (f'ro.build.product={config.source_device.lower()}', f'ro.build.product={config.target_device.lower()}'),
                            (f'ro.build.product={config.source_device.upper()}', f'ro.build.product={config.target_device.upper()}'),
                            (f'ro.build.product={config.source_device.capitalize()}', f'ro.build.product={config.target_device.capitalize()}'),
                            # Add more patterns as needed based on device characteristics
                        ]

                        modified_content = content
                        for old, new in modifications:
                            modified_content = modified_content.replace(old, new)

                        # Write modified content
                        with open(prop_path, 'w', encoding='utf-8') as f:
                            f.write(modified_content)

                    except Exception as e:
                        self.log(f"[!] Error processing {filename}: {e}", 'warning')

    def _copy_hardware_configs(self, base_ramdisk_dir: str, port_ramdisk_dir: str, config: PortRomConfig):
        """Copy port-specific hardware configuration files"""
        import glob

        # Hardware-specific files to copy from port device
        hardware_files = [
            'init.exynos*.rc',  # Chipset-specific init files
            'init.mt*.rc',      # MediaTek variants
            'init.target.rc',   # Target-specific configs
            'dt'                # Device tree directory
        ]

        for pattern in hardware_files:
            for port_file in glob.glob(os.path.join(port_ramdisk_dir, pattern)):
                filename = os.path.basename(port_file)
                base_file = os.path.join(base_ramdisk_dir, filename)

                try:
                    if os.path.isdir(port_file):
                        # Handle directories (like dt)
                        if os.path.exists(base_file):
                            import shutil
                            shutil.rmtree(base_file)
                        import shutil
                        shutil.copytree(port_file, base_file)
                        self.log(f"[*] Copied directory: {filename}", 'info')
                    else:
                        # Handle files
                        import shutil
                        shutil.copy2(port_file, base_file)
                        self.log(f"[*] Copied file: {filename}", 'info')

                except Exception as e:
                    self.log(f"[!] Error copying {filename}: {e}", 'warning')

    def _verify_critical_files(self, ramdisk_dir: str) -> int:
        """Verify that critical files exist in the modified ramdisk"""
        import glob
        
        # Critical files that should exist
        critical_files = [
            'init',           # Main init executable
            'init.rc',        # Main init script
        ]
        
        # Optional files (check for patterns)
        optional_patterns = [
            'fstab.exynos*',  # fstab for exynos chipset
            'fstab.mt*',      # fstab for mediatek chipset
        ]
        
        missing_count = 0
        
        # Check required files
        for critical_file in critical_files:
            file_path = os.path.join(ramdisk_dir, critical_file)
            if not os.path.exists(file_path):
                self.log(f"[!] WARNING: Critical file {critical_file} not found", 'warning')
                missing_count += 1
        
        # Check optional file patterns
        for pattern in optional_patterns:
            matching_files = glob.glob(os.path.join(ramdisk_dir, pattern))
            if not matching_files:
                self.log(f"[!] WARNING: No files matching pattern {pattern} found", 'warning')
                missing_count += 1
        
        return missing_count

    def _start_boot_repacking(self):
        """Start the boot image repacking process"""
        work_dir = os.path.join(os.getcwd(), "firmware_port")
        base_boot_dir = os.path.join(work_dir, "base", "boot")
        base_ramdisk_dir = os.path.join(base_boot_dir, "ramdisk")

        if not os.path.isdir(base_ramdisk_dir):
            messagebox.showerror("Error", "Modified ramdisk not found. Please complete Step 3 first.")
            return

        # Ask user for output path
        out_path = filedialog.asksaveasfilename(
            title="Save new boot image as",
            defaultextension=".img",
            filetypes=[("Boot Image", "*.img")]
        )
        if not out_path:
            return

        threading.Thread(target=self._repack_boot_image_thread,
                        args=(base_boot_dir, out_path), daemon=True).start()

    def _repack_boot_image_thread(self, base_boot_dir: str, out_path: str):
        """Thread to repack the boot image with modified ramdisk"""
        try:
            self.status_label.config(text="Repacking boot image...")
            self.progress.start()
            self.log("[*] Starting boot image repacking...", 'info')

            # Set up directories
            work_dir = os.path.join(os.getcwd(), "firmware_port")
            port_boot_dir = os.path.join(work_dir, "port", "boot")
            
            # Check required directories exist
            if not os.path.isdir(base_boot_dir) or not os.path.isdir(port_boot_dir):
                self.log("[!] Boot directories not found. Run previous scripts first.", 'error')
                self.after(0, lambda: messagebox.showerror("Error",
                    "Boot directories not found. Please complete previous steps first."))
                return

            # Check if magiskboot is available
            magiskboot_path = tool_resolve("magiskboot")
            if not magiskboot_path:
                self.log("[!] magiskboot not found. Please install Magisk.", 'error')
                self.after(0, lambda: messagebox.showerror("Error",
                    "magiskboot not found. Please install Magisk in the tools folder."))
                return

            self.log(f"[*] Using magiskboot: {magiskboot_path}", 'info')
            
            # Create working directory
            import shutil
            temp_dir = tempfile.mkdtemp(prefix="boot_repack_")
            
            try:
                self.log(f"[*] Working in temporary directory: {temp_dir}", 'info')
                
                # Copy base boot directory contents to working directory
                for item in os.listdir(base_boot_dir):
                    src = os.path.join(base_boot_dir, item)
                    dst = os.path.join(temp_dir, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                
                # Step 1: Use port kernel (critical for hardware compatibility!)
                port_kernel = os.path.join(port_boot_dir, "kernel")
                if os.path.exists(port_kernel):
                    shutil.copy2(port_kernel, os.path.join(temp_dir, "kernel"))
                    self.log("[*] Port kernel copied successfully", 'success')
                else:
                    raise FileNotFoundError(f"Port kernel not found at {port_kernel}")
                
                # Step 2: Use port device tree blob
                port_dtb = os.path.join(port_boot_dir, "dtb")
                port_dt_img = os.path.join(port_boot_dir, "dt.img")
                
                if os.path.exists(port_dtb):
                    shutil.copy2(port_dtb, os.path.join(temp_dir, "dtb"))
                    self.log("[*] Port DTB copied successfully", 'success')
                elif os.path.exists(port_dt_img):
                    shutil.copy2(port_dt_img, os.path.join(temp_dir, "dt.img"))
                    self.log("[*] Port dt.img copied successfully", 'success')
                
                # Step 3: Use port kernel DTB if it exists
                port_kernel_dtb = os.path.join(port_boot_dir, "kernel_dtb")
                if os.path.exists(port_kernel_dtb):
                    shutil.copy2(port_kernel_dtb, os.path.join(temp_dir, "kernel_dtb"))
                    self.log("[*] Port kernel DTB copied successfully", 'success')
                
                # Step 4: Repack ramdisk
                self.log("[*] Repacking ramdisk...", 'info')
                ramdisk_dir = os.path.join(temp_dir, "ramdisk")
                if not os.path.isdir(ramdisk_dir):
                    raise FileNotFoundError("Modified ramdisk directory not found")
                
                # Change to ramdisk directory and create new ramdisk
                old_cwd = os.getcwd()
                try:
                    os.chdir(ramdisk_dir)
                    new_ramdisk = os.path.join(temp_dir, "ramdisk-new.cpio.gz")
                    
                    # Use cpio to create new ramdisk, then gzip it
                    cpio_path = tool_resolve("cpio")
                    if cpio_path:
                        # Create ramdisk with cpio
                        import subprocess
                        result = subprocess.run(
                            [cpio_path, "-o", "-H", "newc"],
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            cwd=ramdisk_dir
                        )
                        
                        if result.returncode == 0:
                            # Compress with gzip
                            gzip_path = tool_resolve("gzip")
                            if gzip_path:
                                with open(new_ramdisk.replace('.gz', ''), 'wb') as f:
                                    f.write(result.stdout)
                                
                                result = run_cmd([gzip_path, "-f", new_ramdisk.replace('.gz', '')])
                                if result.returncode != 0:
                                    raise RuntimeError("Failed to compress ramdisk")
                            else:
                                raise FileNotFoundError("gzip not found for ramdisk compression")
                        else:
                            raise RuntimeError(f"Failed to create ramdisk cpio: {result.stderr.decode()}")
                    else:
                        raise FileNotFoundError("cpio not found for ramdisk creation")
                        
                finally:
                    os.chdir(old_cwd)
                
                # Step 5: Replace old ramdisk with new one
                new_ramdisk_path = os.path.join(temp_dir, "ramdisk-new.cpio.gz")
                old_ramdisk_path1 = os.path.join(temp_dir, "ramdisk.cpio")
                old_ramdisk_path2 = os.path.join(temp_dir, "ramdisk.cpio.gz")
                
                if os.path.exists(new_ramdisk_path):
                    # Remove old ramdisk files
                    for old_path in [old_ramdisk_path1, old_ramdisk_path2]:
                        try:
                            if os.path.exists(old_path):
                                os.remove(old_path)
                        except:
                            pass
                    
                    # Move new ramdisk to final location
                    final_ramdisk_path = os.path.join(temp_dir, "ramdisk.cpio.gz")
                    shutil.move(new_ramdisk_path, final_ramdisk_path)
                    self.log("[*] Ramdisk repacked successfully", 'success')
                else:
                    raise FileNotFoundError("Failed to create new ramdisk")
                
                # Step 6: Repack boot image using magiskboot
                self.log("[*] Repacking boot.img...", 'info')
                old_cwd = os.getcwd()
                try:
                    os.chdir(temp_dir)
                    
                    # Use magiskboot to repack the boot image
                    result = run_cmd([magiskboot_path, "repack", "boot.img", "new_boot.img"], cwd=temp_dir)
                    if result.returncode != 0:
                        error_msg = result.stderr.decode() if result.stderr else "Unknown error"
                        raise RuntimeError(f"magiskboot repack failed: {error_msg}")
                    
                    new_boot_img_path = os.path.join(temp_dir, "new_boot.img")
                    if not os.path.exists(new_boot_img_path):
                        raise FileNotFoundError("magiskboot failed to create new_boot.img")
                    
                    # Verify the new boot image
                    file_size = os.path.getsize(new_boot_img_path)
                    self.log(f"[*] New boot image size: {file_size} bytes", 'info')
                    
                    if file_size < 10000000:  # Less than 10MB
                        self.log("[!] WARNING: Boot image seems too small (< 10MB)", 'warning')
                    
                    # Create checksum
                    checksum_path = new_boot_img_path + ".sha256"
                    with open(checksum_path, 'w') as f:
                        import hashlib
                        with open(new_boot_img_path, 'rb') as img_f:
                            file_hash = hashlib.sha256(img_f.read()).hexdigest()
                        f.write(f"{file_hash}  new_boot.img\n")
                    
                    self.log(f"[*] SHA256: {file_hash}", 'info')
                    
                    # Copy final result to output path
                    shutil.copy2(new_boot_img_path, out_path)
                    
                    # Also copy checksum if output directory is writable
                    try:
                        checksum_out_path = out_path + ".sha256"
                        shutil.copy2(checksum_path, checksum_out_path)
                        self.log(f"[*] Checksum saved: {checksum_out_path}", 'info')
                    except:
                        pass  # Non-critical if checksum can't be saved
                    
                finally:
                    os.chdir(old_cwd)
                
                # Success message
                self.log("[*] Boot image repacking complete.", 'success')
                self.log(f"[*] New boot image: {out_path}", 'info')
                self.log(f"[*] SHA256: {file_hash}", 'info')
                self.log("[*] Boot image components:", 'info')
                self.log("    - Kernel: Port device (for hardware compatibility)", 'info')
                self.log("    - DTB: Port device tree", 'info')
                self.log("    - Ramdisk: Base device modified for port device", 'info')
                
                self.after(0, lambda: messagebox.showinfo("Success",
                    "Boot image repacking complete!\n\n"
                    f"New boot image saved as:\n{out_path}\n\n"
                    f"SHA256: {file_hash}\n\n"
                    "Boot image components:\n"
                    "- Kernel: Port device (for hardware compatibility)\n"
                    "- DTB: Port device tree\n"
                    "- Ramdisk: Base device modified for port device"))
                
            finally:
                # Cleanup temporary directory
                shutil.rmtree(temp_dir, ignore_errors=True)
                
        except Exception as e:
            self.log(f"[!] Error during boot repacking: {e}", 'error')
            self.after(0, lambda: messagebox.showerror("Error", f"An error occurred during boot repacking: {e}"))
        finally:
            self.status_label.config(text="Ready")
            self.progress.stop()

    def _create_ramdisk(self, ramdisk_dir: str, out_path: str, compress: bool = True):
        """Create a ramdisk from a directory (simplified version)"""
        import glob
        import subprocess
        
        # Create temporary cpio file
        temp_cpio = out_path + ".cpio" if compress else out_path
        
        try:
            # Use bsdtar to create cpio archive
            bsdtar_path = tool_resolve("bsdtar")
            if not bsdtar_path:
                raise FileNotFoundError("bsdtar not found for ramdisk creation")
            
            # Create the cpio archive
            result = run_cmd([bsdtar_path, "-cf", temp_cpio, "-C", ramdisk_dir, "."])
            if result.returncode != 0:
                raise RuntimeError("Failed to create ramdisk cpio archive")
            
            # Compress if requested
            if compress:
                lz4_path = tool_resolve("lz4")
                if not lz4_path:
                    raise FileNotFoundError("lz4 not found for ramdisk compression")
                
                result = run_cmd([lz4_path, "-9", "-f", temp_cpio, out_path])
                if result.returncode != 0:
                    raise RuntimeError("Failed to compress ramdisk")
                
                # Clean up uncompressed cpio
                try:
                    os.remove(temp_cpio)
                except:
                    pass
            else:
                # Move temp file to final location
                import shutil
                shutil.move(temp_cpio, out_path)
                
        except Exception as e:
            # Clean up on error
            for temp_file in [temp_cpio, out_path]:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except:
                    pass
            raise e

    def _start_vendor_modification(self):
        """Start the vendor partition modification process"""
        if not hasattr(self, 'port_rom_config') or not self.port_rom_config:
            messagebox.showerror("Error", "Port ROM configuration not found. Please complete Step 1 first.")
            return

        config = self.port_rom_config
        work_dir = config.work_dir

        # Check if vendor directories exist from Step 5
        source_vendor = config.get_vendor_dir(config.source_device)
        target_vendor = config.get_vendor_dir(config.target_device)

        if not os.path.isdir(source_vendor) or not os.path.isdir(target_vendor):
            messagebox.showerror("Error", "Vendor directories not found. Please complete Step 5 first.")
            return

        threading.Thread(target=self._vendor_modification_thread, daemon=True).start()

    def _start_system_modification(self):
        """Start the system partition modification process"""
        if not hasattr(self, 'port_rom_config') or not self.port_rom_config:
            messagebox.showerror("Error", "Port ROM configuration not found. Please complete Step 1 first.")
            return

        config = self.port_rom_config
        work_dir = config.work_dir

        # Check if system directories exist from Step 5
        source_system = config.get_system_dir(config.source_device)
        target_system = config.get_system_dir(config.target_device)

        if not os.path.isdir(source_system) or not os.path.isdir(target_system):
            messagebox.showerror("Error", "System directories not found. Please complete Step 5 first.")
            return

        threading.Thread(target=self._system_modification_thread, daemon=True).start()

    def _start_image_repacking(self):
        """Start the image repacking process"""
        work_dir = os.path.join(os.getcwd(), "firmware_port")

        # Check if modified directories exist from Steps 6-7
        a33_vendor = os.path.join(work_dir, "a33", "vendor", "work")
        a33_system = os.path.join(work_dir, "a33", "system", "work")

        if not os.path.isdir(a33_vendor) and not os.path.isdir(a33_system):
            messagebox.showerror("Error", "Modified directories not found. Please complete Steps 6-7 first.")
            return

        # Check for required tools
        make_ext4fs_path = tool_resolve("make_ext4fs")
        img2simg_path = tool_resolve("img2simg")

        if not make_ext4fs_path:
            messagebox.showerror("Error", "make_ext4fs not found. Please install android-tools or place make_ext4fs in the tools folder.")
            return

        if not img2simg_path:
            messagebox.showerror("Error", "img2simg not found. Please install android-tools or place img2simg in the tools folder.")
            return

        threading.Thread(target=self._image_repacking_thread, daemon=True).start()

    def _start_odin_package_creation(self):
        """Start the Odin package creation process"""
        work_dir = os.path.join(os.getcwd(), "firmware_port")
        output_dir = os.path.join(work_dir, "output")

        # Check if repacked images exist from Step 8
        if not os.path.isdir(output_dir):
            messagebox.showerror("Error", "Output directory not found. Please complete Step 8 first.")
            return

        # Check for required images
        required_images = ["system.img", "vendor.img"]
        missing_images = []
        for img in required_images:
            if not os.path.exists(os.path.join(output_dir, img)):
                missing_images.append(img)

        if missing_images:
            messagebox.showerror("Error", f"Required images not found: {', '.join(missing_images)}")
            return

        threading.Thread(target=self._odin_package_creation_thread, daemon=True).start()

    def _start_package_validation(self):
        """Start the package validation process"""
        work_dir = os.path.join(os.getcwd(), "firmware_port")
        odin_dir = os.path.join(work_dir, "odin_package")

        # Check if Odin package exists from Step 9
        if not os.path.isdir(odin_dir):
            messagebox.showerror("Error", "Odin package directory not found. Please complete Step 9 first.")
            return

        # Check for critical files
        critical_files = ["AP_A33_to_A32.tar.md5", "BL_A32.tar.md5", "CP_A32.tar.md5"]
        missing_files = []
        for file in critical_files:
            if not os.path.exists(os.path.join(odin_dir, file)):
                missing_files.append(file)

        if missing_files:
            messagebox.showerror("Error", f"Critical files not found: {', '.join(missing_files)}")
            return

        threading.Thread(target=self._package_validation_thread, daemon=True).start()

    def _start_system_vendor_extraction(self):
        """Start the system and vendor image extraction process"""
        work_dir = os.path.join(os.getcwd(), "firmware_port")

        if not os.path.isdir(work_dir):
            messagebox.showerror("Error", "Working directory not found. Please complete previous steps first.")
            return

        # Check for required tools
        simg2img_path = tool_resolve("simg2img")
        if not simg2img_path:
            messagebox.showerror("Error", "simg2img not found. Please install android-tools-fsutils or place simg2img in the tools folder.")
            return

        threading.Thread(target=self._extract_system_vendor_thread,
                        args=(work_dir,), daemon=True).start()

    def _vendor_modification_thread(self):
        """Thread to perform comprehensive vendor partition modification"""
        try:
            self.status_label.config(text="Modifying vendor partition...")
            self.progress.start()
            self.log("[*] Starting vendor partition modification...", 'info')

            if not self.port_rom_config:
                raise RuntimeError("Port ROM configuration not initialized.")
            config: PortRomConfig = self.port_rom_config

            source_device = config.source_device
            target_device = config.target_device

            source_vendor_work_dir = os.path.join(config.work_dir, source_device, "vendor", "work")
            target_vendor_work_dir = os.path.join(config.work_dir, target_device, "vendor", "work")

            # Verify directories exist
            if not os.path.isdir(source_vendor_work_dir):
                raise FileNotFoundError(f"Source vendor directory not found: {source_vendor_work_dir}")
            if not os.path.isdir(target_vendor_work_dir):
                raise FileNotFoundError(f"Target vendor directory not found: {target_vendor_work_dir}")

            # Create backup of original source vendor
            self.log("[*] Creating backup...")
            backup_dir = os.path.join(config.work_dir, source_device, "vendor", "work.backup")
            if os.path.exists(backup_dir):
                import shutil
                shutil.rmtree(backup_dir)
            import shutil
            shutil.copytree(source_vendor_work_dir, backup_dir)
            self.log(f"[*] Backup created: {backup_dir}", 'info')

            # Function to safely copy files/directories
            def safe_copy(src, dest):
                if os.path.exists(src):
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    if os.path.isdir(src):
                        shutil.copytree(src, dest, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dest)
                    self.log(f"[*] Copied: {os.path.basename(src)}")
                    return True
                else:
                    self.log(f"[!] Not found: {src}")
                    return False

            # Replace critical hardware HALs
            self.log("[*] Replacing Hardware Abstraction Layers...")

            # Camera HALs
            self.log("[*] Replacing camera HALs...")
            import glob
            for cam_lib in glob.glob(os.path.join(target_vendor_work_dir, "lib*", "hw", "camera.*")) + \
                          glob.glob(os.path.join(target_vendor_work_dir, "lib*", "hw", "android.hardware.camera*")):
                if os.path.exists(cam_lib):
                    rel_path = os.path.relpath(cam_lib, target_vendor_work_dir)
                    dest_path = os.path.join(source_vendor_work_dir, rel_path)
                    safe_copy(cam_lib, dest_path)

            # Camera firmware
            camera_fw_src = os.path.join(target_vendor_work_dir, "firmware", "camera")
            if os.path.exists(camera_fw_src):
                camera_fw_dest = os.path.join(source_vendor_work_dir, "firmware", "camera")
                if os.path.exists(camera_fw_dest):
                    shutil.rmtree(camera_fw_dest)
                safe_copy(camera_fw_src, camera_fw_dest)

            # Audio HALs
            self.log("[*] Replacing audio HALs...")
            for audio_lib in glob.glob(os.path.join(target_vendor_work_dir, "lib*", "hw", "audio.*")) + \
                            glob.glob(os.path.join(target_vendor_work_dir, "lib*", "hw", "android.hardware.audio*")):
                if os.path.exists(audio_lib):
                    rel_path = os.path.relpath(audio_lib, target_vendor_work_dir)
                    dest_path = os.path.join(source_vendor_work_dir, rel_path)
                    safe_copy(audio_lib, dest_path)

            # Sensor HALs
            self.log("[*] Replacing sensor HALs...")
            for sensor_lib in glob.glob(os.path.join(target_vendor_work_dir, "lib*", "hw", "sensors.*")) + \
                             glob.glob(os.path.join(target_vendor_work_dir, "lib*", "hw", "android.hardware.sensors*")):
                if os.path.exists(sensor_lib):
                    rel_path = os.path.relpath(sensor_lib, target_vendor_work_dir)
                    dest_path = os.path.join(source_vendor_work_dir, rel_path)
                    safe_copy(sensor_lib, dest_path)

            # Graphics HALs (CRITICAL - wrong GPU = no boot)
            self.log("[*] Replacing graphics HALs...")
            for gfx_dir in ["egl", "vulkan"]:
                src_dir = os.path.join(target_vendor_work_dir, "lib", gfx_dir)
                if os.path.exists(src_dir):
                    dest_dir = os.path.join(source_vendor_work_dir, "lib", gfx_dir)
                    if os.path.exists(dest_dir):
                        shutil.rmtree(dest_dir)
                    safe_copy(src_dir, dest_dir)

                src_dir64 = os.path.join(target_vendor_work_dir, "lib64", gfx_dir)
                if os.path.exists(src_dir64):
                    dest_dir64 = os.path.join(source_vendor_work_dir, "lib64", gfx_dir)
                    if os.path.exists(dest_dir64):
                        shutil.rmtree(dest_dir64)
                    safe_copy(src_dir64, dest_dir64)

            for gfx_lib in glob.glob(os.path.join(target_vendor_work_dir, "lib*", "hw", "gralloc.*")) + \
                          glob.glob(os.path.join(target_vendor_work_dir, "lib*", "hw", "hwcomposer.*")) + \
                          glob.glob(os.path.join(target_vendor_work_dir, "lib*", "hw", "vulkan.*")):
                if os.path.exists(gfx_lib):
                    rel_path = os.path.relpath(gfx_lib, target_vendor_work_dir)
                    dest_path = os.path.join(source_vendor_work_dir, rel_path)
                    safe_copy(gfx_lib, dest_path)

            # GPU firmware and drivers
            mali_lib = os.path.join(target_vendor_work_dir, "lib", "libGLES_mali.so")
            if os.path.exists(mali_lib):
                safe_copy(mali_lib, os.path.join(source_vendor_work_dir, "lib", "libGLES_mali.so"))

            mali_lib64 = os.path.join(target_vendor_work_dir, "lib64", "libGLES_mali.so")
            if os.path.exists(mali_lib64):
                safe_copy(mali_lib64, os.path.join(source_vendor_work_dir, "lib64", "libGLES_mali.so"))

            # Fingerprint HALs
            self.log("[*] Replacing fingerprint HALs...")
            for fp_lib in glob.glob(os.path.join(target_vendor_work_dir, "lib*", "hw", "fingerprint.*")) + \
                         glob.glob(os.path.join(target_vendor_work_dir, "lib*", "hw", "android.hardware.biometrics.fingerprint*")):
                if os.path.exists(fp_lib):
                    rel_path = os.path.relpath(fp_lib, target_vendor_work_dir)
                    dest_path = os.path.join(source_vendor_work_dir, rel_path)
                    safe_copy(fp_lib, dest_path)

            # Wi-Fi and Bluetooth firmware
            self.log("[*] Replacing wireless firmware...")
            wifi_src = os.path.join(target_vendor_work_dir, "firmware", "wifi")
            if os.path.exists(wifi_src):
                wifi_dest = os.path.join(source_vendor_work_dir, "firmware", "wifi")
                if os.path.exists(wifi_dest):
                    shutil.rmtree(wifi_dest)
                safe_copy(wifi_src, wifi_dest)

            bt_src = os.path.join(target_vendor_work_dir, "firmware", "bluetooth")
            if os.path.exists(bt_src):
                bt_dest = os.path.join(source_vendor_work_dir, "firmware", "bluetooth")
                if os.path.exists(bt_dest):
                    shutil.rmtree(bt_dest)
                safe_copy(bt_src, bt_dest)

            # All other firmware
            self.log("[*] Syncing all firmware files...")
            firmware_src = os.path.join(target_vendor_work_dir, "firmware")
            if os.path.exists(firmware_src):
                # Copy all target firmware, overwriting source
                import subprocess
                rsync_path = tool_resolve("rsync")
                if rsync_path:
                    result = run_cmd([rsync_path, "-av", firmware_src + "/", os.path.join(source_vendor_work_dir, "firmware") + "/"])
                    if result.returncode != 0:
                        self.log("[!] rsync failed, using shutil copytree", 'warning')
                        # Fallback to shutil
                        firmware_dest = os.path.join(source_vendor_work_dir, "firmware")
                        if os.path.exists(firmware_dest):
                            shutil.rmtree(firmware_dest)
                        shutil.copytree(firmware_src, firmware_dest)
                else:
                    # Fallback to shutil
                    firmware_dest = os.path.join(source_vendor_work_dir, "firmware")
                    if os.path.exists(firmware_dest):
                        shutil.rmtree(firmware_dest)
                    shutil.copytree(firmware_src, firmware_dest)

            # RIL (Radio Interface Layer) - critical for modem
            self.log("[*] Replacing RIL libraries...")
            for ril_lib in glob.glob(os.path.join(target_vendor_work_dir, "lib*", "libril*.so")) + \
                          glob.glob(os.path.join(target_vendor_work_dir, "lib*", "libsec-ril*.so")) + \
                          glob.glob(os.path.join(target_vendor_work_dir, "lib*", "*ril*.so")):
                if os.path.exists(ril_lib):
                    rel_path = os.path.relpath(ril_lib, target_vendor_work_dir)
                    dest_path = os.path.join(source_vendor_work_dir, rel_path)
                    safe_copy(ril_lib, dest_path)

            # Power HALs
            self.log("[*] Replacing power HALs...")
            for pwr_lib in glob.glob(os.path.join(target_vendor_work_dir, "lib*", "hw", "power.*")) + \
                          glob.glob(os.path.join(target_vendor_work_dir, "lib*", "hw", "android.hardware.power*")):
                if os.path.exists(pwr_lib):
                    rel_path = os.path.relpath(pwr_lib, target_vendor_work_dir)
                    dest_path = os.path.join(source_vendor_work_dir, rel_path)
                    safe_copy(pwr_lib, dest_path)

            # Thermal HALs
            self.log("[*] Replacing thermal HALs...")
            for thm_lib in glob.glob(os.path.join(target_vendor_work_dir, "lib*", "hw", "thermal.*")) + \
                          glob.glob(os.path.join(target_vendor_work_dir, "lib*", "hw", "android.hardware.thermal*")):
                if os.path.exists(thm_lib):
                    rel_path = os.path.relpath(thm_lib, target_vendor_work_dir)
                    dest_path = os.path.join(source_vendor_work_dir, rel_path)
                    safe_copy(thm_lib, dest_path)

            # Modify vendor build.prop
            self.log("[*] Modifying vendor/build.prop...")
            build_prop_path = os.path.join(source_vendor_work_dir, "build.prop")
            if os.path.exists(build_prop_path):
                # Create backup
                shutil.copy2(build_prop_path, build_prop_path + ".backup")

                # Get target device info
                target_build_prop = os.path.join(target_vendor_work_dir, "build.prop")
                if os.path.exists(target_build_prop):
                    target_device_prop = None
                    target_model_prop = None
                    target_fingerprint_prop = None

                    with open(target_build_prop, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            line = line.strip()
                            if line.startswith('ro.product.vendor.device='):
                                target_device_prop = line.split('=', 1)[1]
                            elif line.startswith('ro.product.vendor.model='):
                                target_model_prop = line.split('=', 1)[1]
                            elif line.startswith('ro.vendor.build.fingerprint='):
                                target_fingerprint_prop = line.split('=', 1)[1]

                    # Read and modify source vendor build.prop
                    with open(build_prop_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Replace device info
                    if target_device_prop:
                        content = content.replace(f'ro.product.vendor.device={source_device.lower()}', f'ro.product.vendor.device={target_device_prop}')
                    if target_model_prop:
                        content = content.replace(f'ro.product.vendor.model=SM-{source_device.upper()}', f'ro.product.vendor.model={target_model_prop}')
                    if target_fingerprint_prop:
                        import re
                        content = re.sub(r'ro\.vendor\.build\.fingerprint=.*', f'ro.vendor.build.fingerprint={target_fingerprint_prop}', content)

                    # Replace source device references with target device references
                    content = content.replace(source_device.lower(), target_device.lower())
                    content = content.replace(source_device.upper(), target_device.upper())
                    # Example: replace chipset if known
                    # content = content.replace('exynos1280', 'exynos850') # This should be dynamic or user-defined

                    # Write modified content
                    with open(build_prop_path, 'w', encoding='utf-8') as f:
                        f.write(content)

                    self.log("[*] vendor/build.prop modified", 'success')
                else:
                    self.log(f"[!] {target_device} build.prop not found for reference", 'warning')

            # Modify default.prop if exists
            default_prop_path = os.path.join(source_vendor_work_dir, "default.prop")
            if os.path.exists(default_prop_path):
                with open(default_prop_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                content = content.replace(source_device.lower(), target_device.lower())
                content = content.replace(source_device.upper(), target_device.upper())
                with open(default_prop_path, 'w', encoding='utf-8') as f:
                    f.write(content)

            # Copy target device-specific configuration files
            self.log(f"[*] Copying {target_device} device configs...")

            etc_src = os.path.join(target_vendor_work_dir, "etc")
            if os.path.exists(etc_src):
                # Audio configs
                for audio_conf in glob.glob(os.path.join(etc_src, "audio*.xml")) + \
                                glob.glob(os.path.join(etc_src, "*audio*.conf")):
                    if os.path.exists(audio_conf):
                        rel_path = os.path.relpath(audio_conf, target_vendor_work_dir)
                        dest_path = os.path.join(source_vendor_work_dir, rel_path)
                        safe_copy(audio_conf, dest_path)

                # Media configs
                for media_conf in glob.glob(os.path.join(etc_src, "media_*.xml")) + \
                                glob.glob(os.path.join(etc_src, "*media*.xml")):
                    if os.path.exists(media_conf):
                        rel_path = os.path.relpath(media_conf, target_vendor_work_dir)
                        dest_path = os.path.join(source_vendor_work_dir, rel_path)
                        safe_copy(media_conf, dest_path)

                # Thermal configs
                thermal_src = os.path.join(etc_src, "thermal")
                if os.path.exists(thermal_src):
                    thermal_dest = os.path.join(source_vendor_work_dir, "etc", "thermal")
                    if os.path.exists(thermal_dest):
                        shutil.rmtree(thermal_dest)
                    safe_copy(thermal_src, thermal_dest)

            # Fix permissions
            self.log("[*] Fixing permissions...")
            try:
                # Set ownership to root:root (if running as admin/sudo)
                import subprocess
                if sys.platform.startswith('win'):
                    # On Windows, just set basic permissions
                    pass  # Windows permissions are handled differently
                else:
                    # Unix-like systems
                    result = run_cmd(['chown', '-R', 'root:root', source_vendor_work_dir])
                    if result.returncode != 0:
                        self.log("[!] Could not set ownership (may require sudo)", 'warning')

                # Set directory permissions to 755
                for root_dir, dirs, files in os.walk(source_vendor_work_dir):
                    for d in dirs:
                        dir_path = os.path.join(root_dir, d)
                        os.chmod(dir_path, 0o755)

                # Set file permissions to 644
                for root_dir, dirs, files in os.walk(source_vendor_work_dir):
                    for f in files:
                        file_path = os.path.join(root_dir, f)
                        os.chmod(file_path, 0o644)

                # Set executable permissions for bin directory
                bin_dir = os.path.join(source_vendor_work_dir, "bin")
                if os.path.exists(bin_dir):
                    for root_dir, dirs, files in os.walk(bin_dir):
                        for f in files:
                            file_path = os.path.join(root_dir, f)
                            os.chmod(file_path, 0o755)

                # Set executable permissions for .so files
                for root_dir, dirs, files in os.walk(source_vendor_work_dir):
                    for f in files:
                        if f.endswith('.so'):
                            file_path = os.path.join(root_dir, f)
                            os.chmod(file_path, 0o644)

            except Exception as e:
                self.log(f"[!] Error fixing permissions: {e}", 'warning')

            self.log("[*] Vendor modification complete.", 'success')
            self.log(f"[*] Modified vendor: {source_vendor_work_dir}", 'info')
            self.log(f"[*] Backup: {backup_dir}", 'info')
            self.log("", 'info')
            self.log(f"[!] Files replaced from {target_device}:", 'warning')
            self.log("    - Camera HALs and firmware", 'info')
            self.log("    - Audio HALs and configs", 'info')
            self.log("    - Graphics HALs (GPU drivers)", 'info')
            self.log("    - Sensor HALs", 'info')
            self.log("    - Fingerprint HALs", 'info')
            self.log("    - Wireless firmware", 'info')
            self.log("    - RIL libraries", 'info')
            self.log("    - Power/Thermal HALs", 'info')
            self.log("    - Device configurations", 'info')

            self.after(0, lambda: messagebox.showinfo("Success",
                "Vendor partition modification complete!\n\n"
                f"Modified vendor: {source_vendor_work_dir}\n"
                f"Backup: {backup_dir}\n\n"
                f"Files replaced from {target_device}:\n"
                "• Camera HALs and firmware\n"
                "• Audio HALs and configs\n"
                "• Graphics HALs (GPU drivers)\n"
                "• Sensor HALs\n"
                "• Fingerprint HALs\n"
                "• Wireless firmware\n"
                "• RIL libraries\n"
                "• Power/Thermal HALs\n"
                "• Device configurations\n\n"
                "The vendor partition is now ready for repacking into the ported ROM."))

        except Exception as e:
            self.log(f"[!] Error during vendor modification: {e}", 'error')
            self.after(0, lambda: messagebox.showerror("Error", f"An error occurred during vendor modification: {e}"))
        finally:
            self.status_label.config(text="Ready")
            self.progress.stop()

    def _system_modification_thread(self):
        """Thread to perform system partition modification for device identity"""
        try:
            self.status_label.config(text="Modifying system partition...")
            self.progress.start()
            self.log("[*] Starting system partition modification...", 'info')

            work_dir = os.path.join(os.getcwd(), "firmware_port")
            a33_system = os.path.join(work_dir, "a33", "system", "work")
            a32_system = os.path.join(work_dir, "a32", "system", "work")

            # Verify directories exist
            if not os.path.isdir(a33_system):
                raise FileNotFoundError(f"A33 system directory not found: {a33_system}")
            if not os.path.isdir(a32_system):
                raise FileNotFoundError(f"A32 system directory not found: {a32_system}")

            # Create backup
            self.log("[*] Creating backup...")
            backup_dir = os.path.join(work_dir, "a33", "system", "work.backup")
            if os.path.exists(backup_dir):
                import shutil
                shutil.rmtree(backup_dir)
            import shutil
            shutil.copytree(a33_system, backup_dir)
            self.log(f"[*] Backup created: {backup_dir}", 'info')

            # Find and modify build.prop
            self.log("[*] Modifying system/build.prop...")

            # Possible build.prop locations
            build_prop_paths = [
                os.path.join(a33_system, "system", "build.prop"),
                os.path.join(a33_system, "build.prop")
            ]

            build_prop_path = None
            for path in build_prop_paths:
                if os.path.exists(path):
                    build_prop_path = path
                    break

            if not build_prop_path:
                raise FileNotFoundError("build.prop not found in A33 system directory")

            # Create backup of build.prop
            shutil.copy2(build_prop_path, build_prop_path + ".backup")

            # Find A32 build.prop for reference
            a32_build_prop_paths = [
                os.path.join(a32_system, "system", "build.prop"),
                os.path.join(a32_system, "build.prop")
            ]

            a32_build_prop_path = None
            for path in a32_build_prop_paths:
                if os.path.exists(path):
                    a32_build_prop_path = path
                    break

            # Read and modify A33 build.prop
            with open(build_prop_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Extract A32 device information if available
            if a32_build_prop_path:
                a32_model = None
                a32_device = None
                a32_name = None
                a32_fingerprint = None

                with open(a32_build_prop_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('ro.product.model='):
                            a32_model = line.split('=', 1)[1]
                        elif line.startswith('ro.product.device='):
                            a32_device = line.split('=', 1)[1]
                        elif line.startswith('ro.product.name='):
                            a32_name = line.split('=', 1)[1]
                        elif line.startswith('ro.build.fingerprint='):
                            a32_fingerprint = line.split('=', 1)[1]

                # Replace device identifiers
                import re
                if a32_model:
                    content = re.sub(r'^ro\.product\.model=.*', f'ro.product.model={a32_model}', content, flags=re.MULTILINE)
                if a32_device:
                    content = re.sub(r'^ro\.product\.device=.*', f'ro.product.device={a32_device}', content, flags=re.MULTILINE)
                    content = re.sub(r'^ro\.build\.product=.*', f'ro.build.product={a32_device}', content, flags=re.MULTILINE)
                if a32_name:
                    content = re.sub(r'^ro\.product\.name=.*', f'ro.product.name={a32_name}', content, flags=re.MULTILINE)
                if a32_fingerprint:
                    content = re.sub(r'^ro\.build\.fingerprint=.*', f'ro.build.fingerprint={a32_fingerprint}', content, flags=re.MULTILINE)

            # General replacements for device compatibility
            content = content.replace('a33', 'a32')
            content = content.replace('A33', 'A32')
            content = content.replace('SM-A336', 'SM-A325')
            content = content.replace('exynos1280', 'exynos850')

            # Write modified content
            with open(build_prop_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self.log("[*] system/build.prop modified", 'success')

            # Modify system/etc/prop.default if exists
            prop_default_path = os.path.join(a33_system, "system", "etc", "prop.default")
            if os.path.exists(prop_default_path):
                self.log("[*] Modifying system/etc/prop.default...")
                with open(prop_default_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                content = content.replace('a33', 'a32')
                content = content.replace('A33', 'A32')

                with open(prop_default_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                self.log("[*] system/etc/prop.default modified", 'success')

            self.log("[*] System modification complete.", 'success')
            self.log(f"[*] Modified system: {a33_system}", 'info')
            self.log(f"[*] Backup: {backup_dir}", 'info')
            self.log("", 'info')
            self.log("[*] Changes made:", 'info')
            self.log("    - Device model changed to A32", 'info')
            self.log("    - Build fingerprint updated", 'info')
            self.log("    - Device identifiers updated", 'info')

            self.after(0, lambda: messagebox.showinfo("Success",
                "System partition modification complete!\n\n"
                "Modified system: " + a33_system + "\n"
                "Backup: " + backup_dir + "\n\n"
                "Changes made:\n"
                "• Device model changed to A32\n"
                "• Build fingerprint updated\n"
                "• Device identifiers updated\n\n"
                "The system partition is now configured for the A32 device identity."))

        except Exception as e:
            self.log(f"[!] Error during system modification: {e}", 'error')
            self.after(0, lambda: messagebox.showerror("Error", f"An error occurred during system modification: {e}"))
        finally:
            self.status_label.config(text="Ready")
            self.progress.stop()

    def _image_repacking_thread(self):
        """Thread to repack modified images into flashable format"""
        try:
            self.status_label.config(text="Repacking images...")
            self.progress.start()
            self.log("[*] Starting image repacking...", 'info')

            work_dir = os.path.join(os.getcwd(), "firmware_port")
            output_dir = os.path.join(work_dir, "output")
            os.makedirs(output_dir, exist_ok=True)

            # Check for required tools
            make_ext4fs_path = tool_resolve("make_ext4fs")
            img2simg_path = tool_resolve("img2simg")

            if not make_ext4fs_path:
                raise FileNotFoundError("make_ext4fs not found")
            if not img2simg_path:
                raise FileNotFoundError("img2simg not found")

            # Function to get original image size
            def get_image_size(image_path):
                return os.path.getsize(image_path)

            # Function to repack ext4 image
            def repack_ext4(name, source_dir, orig_image, output_image):
                self.log(f"[*] Repacking {name}...")

                # Get original image size
                img_size = get_image_size(orig_image)
                img_size_mb = img_size // (1024 * 1024)

                self.log(f"[*] Original {name} size: {img_size_mb}MB")

                # Calculate size with 10% overhead
                new_size_mb = img_size_mb + (img_size_mb // 10) + 50

                self.log(f"[*] Creating new {name} with size: {new_size_mb}MB")

                # Create ext4 image
                cmd = [
                    make_ext4fs_path, "-s", "-L", name, "-a", name,
                    "-l", f"{new_size_mb}M", output_image, source_dir
                ]

                result = run_cmd(cmd)
                if result.returncode != 0:
                    raise RuntimeError(f"make_ext4fs failed for {name}: {result.stderr.decode(errors='ignore')}")

                if not os.path.exists(output_image):
                    raise FileNotFoundError(f"Failed to create {output_image}")

                # Convert to sparse image
                self.log("[*] Converting to sparse image...")
                sparse_image = output_image.replace('.img', '_sparse.img')

                result = run_cmd([img2simg_path, output_image, sparse_image])
                if result.returncode != 0:
                    raise RuntimeError(f"img2simg failed for {name}: {result.stderr.decode(errors='ignore')}")

                # Replace with sparse version
                os.replace(sparse_image, output_image)

                # Calculate and display size
                new_img_size = get_image_size(output_image)
                new_img_size_mb = new_img_size // (1024 * 1024)
                self.log(f"[*] Final {name} size: {new_img_size_mb}MB (sparse)")

                return True

            # Unmount any mounted images first (if applicable)
            self.log("[*] Checking for mounted images...")
            # Note: Actual unmounting would require admin privileges and is system-dependent

            # Repack vendor
            a33_vendor_work = os.path.join(work_dir, "a33", "vendor", "work")
            if os.path.isdir(a33_vendor_work):
                a33_vendor_img = os.path.join(work_dir, "a33", "vendor", "vendor.img")
                if os.path.exists(a33_vendor_img):
                    output_vendor = os.path.join(output_dir, "vendor.img")
                    repack_ext4("vendor", a33_vendor_work, a33_vendor_img, output_vendor)
                else:
                    self.log("[!] A33 vendor.img not found for size reference", 'warning')
            else:
                self.log("[!] A33 vendor work directory not found", 'warning')

            # Repack system
            a33_system_work = os.path.join(work_dir, "a33", "system", "work")
            if os.path.isdir(a33_system_work):
                a33_system_img = os.path.join(work_dir, "a33", "system", "system.img")
                if os.path.exists(a33_system_img):
                    output_system = os.path.join(output_dir, "system.img")
                    repack_ext4("system", a33_system_work, a33_system_img, output_system)
                else:
                    self.log("[!] A33 system.img not found for size reference", 'warning')
            else:
                self.log("[!] A33 system work directory not found", 'warning')

            # Repack product if it exists
            a33_product_work = os.path.join(work_dir, "a33", "product", "work")
            if os.path.isdir(a33_product_work):
                a33_product_img = os.path.join(work_dir, "a33", "product", "product.img")
                if os.path.exists(a33_product_img):
                    output_product = os.path.join(output_dir, "product.img")
                    repack_ext4("product", a33_product_work, a33_product_img, output_product)

            # Copy boot image
            self.log("[*] Copying modified boot image...")
            a33_new_boot = os.path.join(work_dir, "a33", "boot", "new_boot.img")
            if os.path.exists(a33_new_boot):
                output_boot = os.path.join(output_dir, "boot.img")
                import shutil
                shutil.copy2(a33_new_boot, output_boot)
                self.log("[*] boot.img copied")
            else:
                self.log("[!] Modified boot.img not found", 'warning')

            # Copy recovery if exists
            a33_recovery = os.path.join(work_dir, "a33", "extracted", "recovery.img")
            if os.path.exists(a33_recovery):
                self.log("[*] Copying recovery image...")
                output_recovery = os.path.join(output_dir, "recovery.img")
                import shutil
                shutil.copy2(a33_recovery, output_recovery)

            # Copy other partitions that don't need modification
            self.log("[*] Copying additional partitions...")
            extracted_dir = os.path.join(work_dir, "a33", "extracted")
            additional_partitions = ["dtbo.img", "vbmeta.img", "super.img"]

            for partition in additional_partitions:
                partition_path = os.path.join(extracted_dir, partition)
                if os.path.exists(partition_path):
                    output_partition = os.path.join(output_dir, partition)
                    import shutil
                    shutil.copy2(partition_path, output_partition)
                    self.log(f"[*] {partition} copied")

            # Create checksums
            self.log("[*] Creating checksums...")
            import hashlib

            checksums = []
            for file in os.listdir(output_dir):
                if file.endswith('.img'):
                    file_path = os.path.join(output_dir, file)
                    with open(file_path, 'rb') as f:
                        checksum = hashlib.sha256(f.read()).hexdigest()
                    checksums.append(f"{checksum}  {file}")

            checksum_file = os.path.join(output_dir, "checksums.sha256")
            with open(checksum_file, 'w') as f:
                f.write('\n'.join(checksums))

            self.log("[*] Checksums created:")
            for checksum in checksums:
                self.log(f"  {checksum}")

            # Get file sizes for summary
            self.log("", 'info')
            self.log("[*] Image repacking complete.", 'success')
            self.log(f"[*] Output directory: {output_dir}", 'info')
            self.log("", 'info')
            self.log("[*] Repacked images:", 'info')

            total_size = 0
            for file in sorted(os.listdir(output_dir)):
                if file.endswith('.img'):
                    file_path = os.path.join(output_dir, file)
                    size_mb = os.path.getsize(file_path) // (1024 * 1024)
                    total_size += size_mb
                    self.log(f"  {file}: {size_mb}MB")

            self.log("", 'info')
            self.log(f"[!] Total size: {total_size}MB", 'warning')
            self.log("[!] Ready for Odin packaging.", 'success')

            self.after(0, lambda: messagebox.showinfo("Success",
                f"Image repacking complete!\n\n"
                f"Output directory: {output_dir}\n\n"
                f"Total size: {total_size}MB\n\n"
                "Images ready for Odin packaging:\n"
                "• vendor.img (modified)\n"
                "• system.img (modified)\n"
                "• boot.img (modified)\n"
                "• Additional partitions copied\n\n"
                "Checksums saved to checksums.sha256"))

        except Exception as e:
            self.log(f"[!] Error during image repacking: {e}", 'error')
            self.after(0, lambda: messagebox.showerror("Error", f"An error occurred during image repacking: {e}"))
        finally:
            self.status_label.config(text="Ready")
            self.progress.stop()

    def _odin_package_creation_thread(self):
        """Thread to create Odin flashable package"""
        import shutil
        try:
            self.status_label.config(text="Creating Odin package...")
            self.progress.start()
            self.log("[*] Starting Odin package creation...", 'info')

            work_dir = os.path.join(os.getcwd(), "firmware_port")
            output_dir = os.path.join(work_dir, "output")
            odin_dir = os.path.join(work_dir, "odin_package")
            os.makedirs(odin_dir, exist_ok=True)

            # Create AP tar package
            self.log("[*] Creating AP package...")

            ap_files = []
            ap_images = ["boot.img", "recovery.img", "system.img", "vendor.img", "product.img", "dtbo.img", "vbmeta.img"]

            for img in ap_images:
                img_path = os.path.join(output_dir, img)
                if os.path.exists(img_path):
                    ap_files.append(img)

            if not ap_files:
                raise FileNotFoundError("No images found for AP package")

            self.log(f"[*] AP package will contain: {', '.join(ap_files)}")

            # Create tar archive
            ap_tar_path = os.path.join(odin_dir, "AP_A33_to_A32.tar")
            import tarfile
            with tarfile.open(ap_tar_path, 'w') as tar:
                for img_file in ap_files:
                    img_path = os.path.join(output_dir, img_file)
                    tar.add(img_path, arcname=img_file)

            # Add MD5 checksum
            import hashlib
            with open(ap_tar_path, 'rb') as f:
                md5_hash = hashlib.md5(f.read()).hexdigest()

            with open(ap_tar_path, 'ab') as f:
                f.write(md5_hash.encode('ascii'))

            # Rename to .tar.md5
            ap_final_path = os.path.join(odin_dir, "AP_A33_to_A32.tar.md5")
            os.rename(ap_tar_path, ap_final_path)

            self.log("[*] AP package created: AP_A33_to_A32.tar.md5")

            # Copy A32 BL package
            self.log("[*] Copying A32 bootloader...")
            a32_bl = os.path.join(work_dir, "a32", "BL_original.tar.md5")
            if os.path.exists(a32_bl):
                bl_dest = os.path.join(odin_dir, "BL_A32.tar.md5")
                import shutil
                shutil.copy2(a32_bl, bl_dest)
                self.log("[*] BL package copied: BL_A32.tar.md5")
            else:
                self.log("[!] WARNING: A32 bootloader not found", 'warning')
                self.log("[!] You must use A32's original bootloader!", 'warning')

            # Copy A32 CP package
            self.log("[*] Copying A32 modem...")
            a32_cp = os.path.join(work_dir, "a32", "CP_original.tar.md5")
            if os.path.exists(a32_cp):
                cp_dest = os.path.join(odin_dir, "CP_A32.tar.md5")
                shutil.copy2(a32_cp, cp_dest)
                self.log("[*] CP package copied: CP_A32.tar.md5")
            else:
                self.log("[!] WARNING: A32 modem not found", 'warning')
                self.log("[!] You must use A32's original modem firmware!", 'warning')

            # Handle CSC
            self.log("[*] Preparing CSC package...")
            csc_found = False

            # Try to use A32 CSC first
            import glob
            a32_csc_pattern = os.path.join(work_dir, "a32", "CSC_*.tar.md5")
            a32_csc_files = glob.glob(a32_csc_pattern)
            if not a32_csc_files:
                a32_csc_pattern = os.path.join(work_dir, "a32", "HOME_CSC_*.tar.md5")
                a32_csc_files = glob.glob(a32_csc_pattern)

            if a32_csc_files:
                a32_csc = a32_csc_files[0]
                csc_dest = os.path.join(odin_dir, os.path.basename(a32_csc))
                shutil.copy2(a32_csc, csc_dest)
                self.log(f"[*] Using A32 CSC: {os.path.basename(a32_csc)}")
                csc_found = True
            else:
                self.log("[!] WARNING: A32 CSC not found. May use A33 CSC (risky)", 'warning')
                # Try A33 CSC as fallback
                a33_csc_pattern = os.path.join(work_dir, "a33", "HOME_CSC_*.tar.md5")
                a33_csc_files = glob.glob(a33_csc_pattern)
                if a33_csc_files:
                    a33_csc = a33_csc_files[0]
                    csc_dest = os.path.join(odin_dir, "CSC_A33_modified.tar.md5")
                    shutil.copy2(a33_csc, csc_dest)
                    self.log("[*] Copied A33 CSC (may need modification)")
                    csc_found = True

            # Create flash instructions
            flash_instructions = f"""===========================================
ODIN FLASH INSTRUCTIONS - A33 to A32 Port
===========================================

CRITICAL WARNINGS:
1. This is a PORTED firmware - there is risk of bricking
2. Ensure battery is >70% charged
3. Have stock A32 firmware ready for recovery
4. Backup all data before flashing

PREREQUISITES:
- Samsung USB Drivers installed
- Odin 3.14.4 or newer
- A32 bootloader must be UNLOCKED
- Developer options enabled, OEM unlock enabled

FLASHING STEPS:

1. Boot A32 into Download Mode:
   - Power off device
   - Press and hold: Volume Down + Volume Up
   - Connect USB cable while holding buttons
   - Press Volume Up to confirm

2. Open Odin (run as Administrator on Windows)

3. Load firmware files:
   - AP: AP_A33_to_A32.tar.md5
   - BL: BL_A32.tar.md5
   - CP: CP_A32.tar.md5
   - CSC: Use HOME_CSC (if available) or CSC file

4. Odin Options:
   [X] Auto Reboot
   [X] F. Reset Time
   [ ] Do NOT check Re-partition

5. Click START and wait
   - Do NOT disconnect USB during flash
   - Device will reboot automatically
   - First boot may take 10-15 minutes

6. If device doesn't boot after 20 minutes:
   - Boot into recovery (Volume Up + Power while off)
   - Wipe cache partition
   - Factory reset (if necessary)
   - Reboot

TROUBLESHOOTING:

Boot Loop:
- Enter recovery mode
- Wipe data/factory reset
- If still loops, flash stock A32 firmware

Stuck at Logo:
- Wait 20 minutes
- Force reboot: Hold Power for 10 seconds
- Retry boot or enter recovery

No Display:
- Force reboot
- Flash stock A32 firmware immediately

Features Not Working:
- Camera: May need additional calibration
- Fingerprint: Re-enroll fingerprints
- NFC: Check settings after boot

RECOVERY:
If all else fails, flash stock A32 firmware:
1. Download from sammobile.com or similar
2. Flash with Odin using same procedure
3. This will restore device to working state

===========================================
"""

            instructions_path = os.path.join(odin_dir, "FLASH_INSTRUCTIONS.txt")
            with open(instructions_path, 'w', encoding='utf-8') as f:
                f.write(flash_instructions)

            self.log("[*] Flash instructions created")

            # Create package info file
            from datetime import datetime
            package_info = f"""Package Information
===================
Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Base Firmware: Samsung A33 Android 16
Target Device: Samsung A32
Modification Level: Full port

Modified Components:
- Boot image (A32 kernel + modified A33 ramdisk)
- Vendor partition (A32 HALs + A33 system)
- System partition (A32 device identity)

Unmodified Components:
- Bootloader (A32 original - CRITICAL)
- Modem (A32 original - CRITICAL)

Package Contents:
"""

            # Get file listing
            odin_files = []
            for file in os.listdir(odin_dir):
                if file.endswith(('.tar.md5', '.txt')):
                    file_path = os.path.join(odin_dir, file)
                    size_mb = os.path.getsize(file_path) / (1024 * 1024)
                    odin_files.append(f"{file}: {size_mb:.1f}MB")

            package_info += "\n".join(odin_files) + "\n\n"

            # Add checksums
            package_info += "Checksums:\n"
            checksums = []
            for file in os.listdir(odin_dir):
                if file.endswith('.tar.md5'):
                    file_path = os.path.join(odin_dir, file)
                    with open(file_path, 'rb') as f:
                        sha256 = hashlib.sha256(f.read()).hexdigest()
                    checksums.append(f"{sha256}  {file}")

            package_info += "\n".join(checksums)

            info_path = os.path.join(odin_dir, "PACKAGE_INFO.txt")
            with open(info_path, 'w', encoding='utf-8') as f:
                f.write(package_info)

            # Create final checksums file
            checksums_path = os.path.join(odin_dir, "CHECKSUMS.sha256")
            with open(checksums_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(checksums))

            self.log("", 'info')
            self.log("============================================", 'success')
            self.log("[*] Odin package creation complete!", 'success')
            self.log("============================================", 'success')
            self.log("", 'info')
            self.log(f"Package location: {odin_dir}", 'info')
            self.log("", 'info')
            self.log("Files created:", 'info')

            for file_info in odin_files:
                self.log(f"  {file_info}")

            self.log("", 'info')
            self.log("============================================", 'warning')
            self.log("NEXT STEPS:", 'warning')
            self.log("============================================", 'warning')
            self.log("1. Review FLASH_INSTRUCTIONS.txt", 'info')
            self.log("2. Verify all .tar.md5 files are present:", 'info')
            self.log("   - AP_A33_to_A32.tar.md5 (modified)", 'info')
            self.log("   - BL_A32.tar.md5 (A32 bootloader)", 'info')
            self.log("   - CP_A32.tar.md5 (A32 modem)", 'info')
            self.log("   - CSC file (A32 or modified A33)", 'info')
            self.log("", 'info')
            self.log("3. CRITICAL: Do NOT use A33 bootloader or modem!", 'error')
            self.log("4. Have stock A32 firmware ready for recovery", 'warning')
            self.log("5. Ensure device battery >70%", 'warning')
            self.log("6. Flash at your own risk", 'error')
            self.log("============================================", 'warning')

            success_msg = f"""Odin package creation complete!

Package location: {odin_dir}

Files created:
""" + "\n".join(odin_files) + """

===========================================
CRITICAL WARNINGS:
===========================================
• This is a PORTED firmware - RISK OF BRICKING
• NEVER use A33 bootloader or modem
• Have stock A32 firmware ready for recovery
• Ensure battery >70% before flashing

Next Steps:
1. Review FLASH_INSTRUCTIONS.txt
2. Verify all required .tar.md5 files are present
3. Test flash on A32 device (at your own risk)
===========================================
"""

            self.after(0, lambda: messagebox.showinfo("Success", success_msg))

        except Exception as e:
            self.log(f"[!] Error during Odin package creation: {e}", 'error')
            self.after(0, lambda: messagebox.showerror("Error", f"An error occurred during Odin package creation: {e}"))
        finally:
            self.status_label.config(text="Ready")
            self.progress.stop()

    def _package_validation_thread(self):
        """Thread to validate the Odin package for completeness and safety"""
        import os
        import hashlib
        try:
            self.status_label.config(text="Validating package...")
            self.progress.start()
            self.log("[*] Starting package validation...", 'info')

            work_dir = os.path.join(os.getcwd(), "firmware_port")
            odin_dir = os.path.join(work_dir, "odin_package")

            errors = 0
            warnings = 0

            self.log("============================================", 'info')
            self.log("FIRMWARE PACKAGE VALIDATION", 'info')
            self.log("============================================", 'info')
            self.log("", 'info')

            # Check required files
            self.log("[*] Checking required files...", 'info')

            def check_file(filename, critical=False):
                nonlocal errors, warnings
                file_path = os.path.join(odin_dir, filename)
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    size_mb = size // (1024 * 1024)
                    self.log(f"[✓] {filename} ({size_mb}MB)", 'success')
                    return True
                else:
                    if critical:
                        self.log(f"[✗] MISSING CRITICAL: {filename}", 'error')
                        errors += 1
                    else:
                        self.log(f"[!] WARNING: {filename} not found", 'warning')
                        warnings += 1
                    return False

            check_file("AP_A33_to_A32.tar.md5", critical=True)
            check_file("BL_A32.tar.md5", critical=True)
            check_file("CP_A32.tar.md5", critical=True)

            # Check for CSC files
            import glob
            csc_files = glob.glob(os.path.join(odin_dir, "CSC_*.tar.md5")) + \
                       glob.glob(os.path.join(odin_dir, "HOME_CSC_*.tar.md5"))
            if not csc_files:
                self.log("[!] WARNING: No CSC file found", 'warning')
                warnings += 1
            else:
                csc_name = os.path.basename(csc_files[0])
                self.log(f"[✓] CSC file: {csc_name}", 'success')

            self.log("", 'info')

            # Verify AP contents
            self.log("[*] Verifying AP package contents...", 'info')
            ap_path = os.path.join(odin_dir, "AP_A33_to_A32.tar.md5")

            if os.path.exists(ap_path):
                # Extract without md5 footer (last 32 bytes)
                with open(ap_path, 'rb') as f:
                    ap_data = f.read()
                ap_tar_data = ap_data[:-32] if len(ap_data) > 32 else ap_data

                # Write temporary tar file
                temp_tar = os.path.join(odin_dir, "AP_temp.tar")
                with open(temp_tar, 'wb') as f:
                    f.write(ap_tar_data)

                try:
                    import tarfile
                    with tarfile.open(temp_tar, 'r') as tar:
                        members = tar.getmembers()
                        img_files = [m.name for m in members if m.name.endswith('.img')]
                        self.log("[*] AP package contains:", 'info')
                        for img in img_files:
                            self.log(f"    {img}", 'info')

                        # Check for essential images
                        essential_images = ['boot.img', 'system.img', 'vendor.img']
                        for essential in essential_images:
                            if essential in img_files:
                                self.log(f"[✓] {essential} present", 'success')
                            else:
                                self.log(f"[✗] {essential} MISSING", 'error')
                                errors += 1

                finally:
                    # Clean up temp file
                    if os.path.exists(temp_tar):
                        os.remove(temp_tar)

            self.log("", 'info')

            # Verify checksums
            self.log("[*] Verifying package checksums...", 'info')
            checksums_path = os.path.join(odin_dir, "CHECKSUMS.sha256")

            if os.path.exists(checksums_path):
                import subprocess
                try:
                    result = subprocess.run(['sha256sum', '-c', checksums_path],
                                          cwd=odin_dir, capture_output=True, text=True)
                    if result.returncode == 0:
                        self.log("[✓] All checksums valid", 'success')
                    else:
                        self.log("[!] WARNING: Some checksums failed", 'warning')
                        warnings += 1
                except Exception as e:
                    self.log(f"[!] WARNING: Could not verify checksums: {e}", 'warning')
                    warnings += 1
            else:
                self.log("[!] WARNING: CHECKSUMS.sha256 not found", 'warning')
                warnings += 1

            self.log("", 'info')

            # Check boot image components
            self.log("[*] Checking boot image components...", 'info')
            boot_check = os.path.join(work_dir, "a33", "boot")

            if os.path.exists(os.path.join(boot_check, "kernel")):
                kernel_size = os.path.getsize(os.path.join(boot_check, "kernel"))
                kernel_size_mb = kernel_size // (1024 * 1024)
                self.log(f"[*] Kernel size: {kernel_size_mb}MB", 'info')

                # Check if it's reasonable size for A32 (A33 kernel is typically 20-25MB, A32 around 15-20MB)
                if kernel_size_mb < 30:
                    self.log("[✓] Kernel size looks reasonable for A32", 'success')
                else:
                    self.log("[!] WARNING: Kernel seems too large (might be A33 kernel)", 'warning')
                    warnings += 1

            if os.path.exists(os.path.join(boot_check, "ramdisk")):
                import os
                ramdisk_files = len([f for f in os.listdir(os.path.join(boot_check, "ramdisk"))
                                   if os.path.isfile(os.path.join(boot_check, "ramdisk", f))])
                self.log(f"[*] Ramdisk contains {ramdisk_files} files", 'info')

                # Check for A32-specific files
                fstab_found = False
                for fstab_file in ["fstab.exynos850", "fstab.mt6769"]:
                    if os.path.exists(os.path.join(boot_check, "ramdisk", fstab_file)):
                        fstab_found = True
                        break

                if fstab_found:
                    self.log("[✓] A32 fstab found in ramdisk", 'success')
                else:
                    self.log("[!] WARNING: A32-specific fstab not found", 'warning')
                    warnings += 1

            self.log("", 'info')

            # Verify BL is from A32
            self.log("[*] Verifying bootloader source...", 'info')
            bl_orig = os.path.join(work_dir, "a32", "BL_original.tar.md5")
            bl_odin = os.path.join(odin_dir, "BL_A32.tar.md5")

            if os.path.exists(bl_orig) and os.path.exists(bl_odin):
                import hashlib
                with open(bl_orig, 'rb') as f:
                    bl_orig_hash = hashlib.md5(f.read()).hexdigest()
                with open(bl_odin, 'rb') as f:
                    bl_odin_hash = hashlib.md5(f.read()).hexdigest()

                if bl_orig_hash == bl_odin_hash:
                    self.log("[✓] Bootloader is confirmed A32 original", 'success')
                else:
                    self.log("[✗] CRITICAL: Bootloader does not match A32 original!", 'error')
                    errors += 1
            else:
                self.log("[!] WARNING: Cannot verify bootloader source", 'warning')
                warnings += 1

            # Verify CP is from A32
            self.log("[*] Verifying modem source...", 'info')
            cp_orig = os.path.join(work_dir, "a32", "CP_original.tar.md5")
            cp_odin = os.path.join(odin_dir, "CP_A32.tar.md5")

            if os.path.exists(cp_orig) and os.path.exists(cp_odin):
                with open(cp_orig, 'rb') as f:
                    cp_orig_hash = hashlib.md5(f.read()).hexdigest()
                with open(cp_odin, 'rb') as f:
                    cp_odin_hash = hashlib.md5(f.read()).hexdigest()

                if cp_orig_hash == cp_odin_hash:
                    self.log("[✓] Modem is confirmed A32 original", 'success')
                else:
                    self.log("[✗] CRITICAL: Modem does not match A32 original!", 'error')
                    errors += 1
            else:
                self.log("[!] WARNING: Cannot verify modem source", 'warning')
                warnings += 1

            self.log("", 'info')

            # Check vendor modifications
            self.log("[*] Checking vendor modifications...", 'info')
            vendor_check = os.path.join(work_dir, "a33", "vendor", "work")

            if os.path.isdir(vendor_check):
                # Check if critical HALs exist
                hal_count = 0
                hal_patterns = ['camera', 'audio', 'sensors', 'gralloc']

                for root, dirs, files in os.walk(vendor_check):
                    for file in files:
                        for hal in hal_patterns:
                            if hal in file.lower() and (file.endswith('.so') or 'hal' in file.lower()):
                                hal_count += 1
                                break

                if hal_count >= 3:
                    self.log("[✓] Critical HALs present in vendor", 'success')
                else:
                    self.log(f"[!] WARNING: Some HALs may be missing ({hal_count}/4 found)", 'warning')
                    warnings += 1

                # Check build.prop modifications
                build_prop = os.path.join(vendor_check, "build.prop")
                if os.path.exists(build_prop):
                    with open(build_prop, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    if 'SM-A325' in content or 'a32' in content:
                        self.log("[✓] Vendor build.prop modified for A32", 'success')
                    else:
                        self.log("[!] WARNING: Vendor build.prop may not be properly modified", 'warning')
                        warnings += 1

            self.log("", 'info')

            # Final summary
            self.log("============================================", 'info')
            self.log("VALIDATION SUMMARY", 'info')
            self.log("============================================", 'info')
            self.log(f"Errors: {errors}", 'info')
            self.log(f"Warnings: {warnings}", 'info')
            self.log("", 'info')

            if errors > 0:
                self.log("[✗] VALIDATION FAILED", 'error')
                self.log(f"[!] {errors} critical errors found", 'error')
                self.log("[!] DO NOT FLASH - Fix errors first", 'error')
                self.log("============================================", 'error')

                self.after(0, lambda: messagebox.showerror("Validation Failed",
                    f"VALIDATION FAILED!\n\n"
                    f"{errors} critical errors found\n"
                    f"{warnings} warnings\n\n"
                    "DO NOT FLASH - Fix errors first"))

            elif warnings > 0:
                self.log("[!] VALIDATION PASSED WITH WARNINGS", 'warning')
                self.log(f"[!] {warnings} warnings found", 'warning')
                self.log("[!] Review warnings before flashing", 'warning')
                self.log("============================================", 'warning')

                success_msg = f"""VALIDATION PASSED WITH WARNINGS

Errors: {errors}
Warnings: {warnings}

Review warnings before flashing:
• Check all warning messages above
• Ensure bootloader and modem are A32 originals
• Verify all modifications are correct

Final checklist before flashing:
- Battery >70% charged
- Stock A32 firmware downloaded for recovery
- All data backed up
- Read FLASH_INSTRUCTIONS.txt
- Understand the risks"""

                self.after(0, lambda: messagebox.showwarning("Validation Passed with Warnings", success_msg))

            else:
                self.log("[✓] VALIDATION PASSED", 'success')
                self.log("[✓] Package appears ready for flashing", 'success')
                self.log("", 'info')
                self.log("Final checklist before flashing:", 'info')
                self.log("  [ ] Battery >70% charged", 'info')
                self.log("  [ ] Stock A32 firmware downloaded for recovery", 'info')
                self.log("  [ ] All data backed up", 'info')
                self.log("  [ ] Read FLASH_INSTRUCTIONS.txt", 'info')
                self.log("  [ ] Understand the risks", 'info')
                self.log("============================================", 'success')

                success_msg = f"""VALIDATION PASSED!

Errors: {errors}
Warnings: {warnings}

Package appears ready for flashing.

Final checklist before flashing:
- Battery >70% charged
- Stock A32 firmware downloaded for recovery
- All data backed up
- Read FLASH_INSTRUCTIONS.txt
- Understand the risks

===========================================
FLASH AT YOUR OWN RISK!
===========================================
"""

                self.after(0, lambda: messagebox.showinfo("Validation Passed", success_msg))

        except Exception as e:
            self.log(f"[!] Error during package validation: {e}", 'error')
            self.after(0, lambda: messagebox.showerror("Error", f"An error occurred during package validation: {e}"))
        finally:
            self.status_label.config(text="Ready")
            self.progress.stop()

    def _extract_system_vendor_thread(self, work_dir: str):
        """Thread to extract system and vendor images"""
        try:
            self.status_label.config(text="Extracting system/vendor images...")
            self.progress.start()
            self.log("[*] Starting system and vendor image extraction...", 'info')

            # Check for required tools
            simg2img_path = tool_resolve("simg2img")
            if not simg2img_path:
                raise FileNotFoundError("simg2img not found")

            # Image types to extract
            image_types = ["vendor", "system", "product"]
            devices = ["base", "port"]  # Assuming base=a33, port=a32 in the example

            extracted_info = []

            for device in devices:
                device_dir = os.path.join(work_dir, device)
                extracted_dir = os.path.join(device_dir, "extracted")

                if not os.path.isdir(extracted_dir):
                    self.log(f"[!] Extracted directory not found for {device}", 'warning')
                    continue

                for image_type in image_types:
                    self.log(f"[*] Processing {image_type} for {device}...", 'info')

                    try:
                        # Find the image file
                        image_files = []
                        for file in os.listdir(extracted_dir):
                            if file.startswith(image_type) and file.endswith('.img'):
                                image_files.append(file)

                        if not image_files:
                            self.log(f"[!] {image_type}.img not found for {device}", 'warning')
                            continue

                        image_file = image_files[0]  # Use first match
                        image_path = os.path.join(extracted_dir, image_file)

                        # Create output directory
                        output_dir = os.path.join(device_dir, image_type)
                        os.makedirs(output_dir, exist_ok=True)

                        # Copy image to working directory
                        work_image_path = os.path.join(output_dir, f"{image_type}.img")
                        import shutil
                        shutil.copy2(image_path, work_image_path)

                        # Check if it's a sparse image
                        try:
                            result = run_cmd(["file", work_image_path])
                            if "sparse" in result.stdout.lower() or result.returncode == 0:
                                # Try to detect sparse image by reading magic
                                with open(work_image_path, 'rb') as f:
                                    magic = f.read(4)
                                    if magic == b'\x3a\xff\x26\xed':  # Sparse image magic
                                        self.log(f"[*] Converting sparse image to raw...", 'info')
                                        raw_image_path = work_image_path.replace('.img', '_raw.img')

                                        result = run_cmd([simg2img_path, work_image_path, raw_image_path])
                                        if result.returncode == 0:
                                            # Replace original with raw
                                            os.remove(work_image_path)
                                            shutil.move(raw_image_path, work_image_path)
                                        else:
                                            raise RuntimeError("Failed to convert sparse image")
                        except Exception as e:
                            self.log(f"[!] Warning: Could not check for sparse image: {e}", 'warning')

                        # Create extraction directories
                        mount_dir = os.path.join(output_dir, "mount")
                        work_extraction_dir = os.path.join(output_dir, "work")
                        os.makedirs(mount_dir, exist_ok=True)

                        self.log(f"[*] {image_type} prepared for {device} at {output_dir}", 'info')
                        extracted_info.append({
                            'device': device,
                            'type': image_type,
                            'path': work_extraction_dir,
                            'mount_path': mount_dir,
                            'image_path': work_image_path
                        })

                    except Exception as e:
                        self.log(f"[!] Error processing {image_type} for {device}: {e}", 'error')
                        continue

            if not extracted_info:
                raise RuntimeError("No images were successfully extracted")

            # Generate summary report
            base_paths = []
            port_paths = []

            for info in extracted_info:
                if info['device'] == 'base':
                    base_paths.append(f"    {info['type']}: {info['path']}")
                else:
                    port_paths.append(f"    {info['type']}: {info['path']}")

            self.log("[*] Image extraction complete.", 'success')
            self.log("[*] Base Images:", 'info')
            for path in base_paths:
                self.log(path, 'info')
            self.log("[*] Port Images (reference):", 'info')
            for path in port_paths:
                self.log(path, 'info')

            # Create user-friendly summary
            summary = "System and vendor image extraction complete!\n\n"
            summary += "Extracted Images:\n"
            summary += f"Base device:\n" + "\n".join(base_paths) + "\n\n"
            summary += f"Port device (reference):\n" + "\n".join(port_paths) + "\n\n"
            summary += "IMPORTANT: Images are ready for extraction. To extract contents:\n"
            summary += "• Mount the .img files using appropriate tools\n"
            summary += "• Extract contents to the 'work' subdirectories\n"
            summary += "• Compare and modify as needed for porting\n\n"
            summary += "Note: This implementation prepares the images for extraction.\n"
            summary += "Actual mounting/extraction requires filesystem-specific tools."

            self.after(0, lambda: messagebox.showinfo("Success", summary))

        except Exception as e:
            self.log(f"[!] Error during system/vendor extraction: {e}", 'error')
            self.after(0, lambda: messagebox.showerror("Error", f"An error occurred during system/vendor extraction: {e}"))
        finally:
            self.status_label.config(text="Ready")
            self.progress.stop()

    def _build_statusbar(self):
        # Create a frame to hold status bar and progress bar
        status_frame = tk.Frame(self)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)

        # Status bar (left side)
        self.status_label = tk.Label(status_frame, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W,
                                    font=('Segoe UI', 9), height=1)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Progress bar (right side, always visible)
        self.progress = ttk.Progressbar(status_frame, length=200, mode='indeterminate')
        self.progress.pack(side=tk.RIGHT, padx=(5, 0))
    
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

Author: Isaki Dube | License: Dual
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

    # Hex Editor menu commands
    def hex_editor_open_file(self):
        if hasattr(self, 'hex_editor_widget_ref'):
            self.hex_editor_widget_ref.open_file()

    def hex_editor_save(self):
        if hasattr(self, 'hex_editor_widget_ref'):
            self.hex_editor_widget_ref.save_file()

    def hex_editor_save_as(self):
        if hasattr(self, 'hex_editor_widget_ref'):
            self.hex_editor_widget_ref.save_as()

    def hex_editor_find(self):
        if hasattr(self, 'hex_editor_widget_ref'):
            self.hex_editor_widget_ref.find_dialog()

    def hex_editor_replace(self):
        if hasattr(self, 'hex_editor_widget_ref'):
            self.hex_editor_widget_ref.replace_dialog()

    def hex_editor_goto(self):
        if hasattr(self, 'hex_editor_widget_ref'):
            self.hex_editor_widget_ref.goto_dialog()

    def hex_editor_entropy(self):
        if hasattr(self, 'hex_editor_widget_ref'):
            self.hex_editor_widget_ref.entropy_analysis()

    def hex_editor_strings(self):
        if hasattr(self, 'hex_editor_widget_ref'):
            self.hex_editor_widget_ref.show_strings()

    def hex_editor_histogram(self):
        if hasattr(self, 'hex_editor_widget_ref'):
            self.hex_editor_widget_ref.byte_histogram()

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

    startup_logger.info("Initializing SmartphoneFirmwareScrews application.")
    app = SmartphoneFirmwareScrews()
    app.refresh_tools()
    app.log(f"{APP_TITLE} v{VERSION} started", 'success')
    app.log(f"Tools directory: {TOOLS_DIR}", 'info')
    startup_logger.info("Calling app.mainloop() for SmartphoneFirmwareScrews.")
    app.mainloop()
    startup_logger.info("app.mainloop() for SmartphoneFirmwareScrews exited.")

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
