# Smartphone Firmware Screws

**Ultimate Firmware Kitchen - Complete Android ROM & Firmware Toolkit**

Professional-grade ROM building, firmware modification, and device flashing toolkit. This comprehensive suite provides everything needed for Android firmware development, from source code compilation to device flashing.

## Features

### Core Capabilities

- **AOSP/Custom ROM Building**: Build Android ROMs from source code or existing images
- **Odin Firmware Building**: Create byte-exact .tar.md5 firmware packages for Samsung devices
- **Boot Image Modification**: Edit kernel, ramdisk, cmdline, and other boot components
- **System Customization**: Modify system/vendor/product partitions and properties
- **APK Tools**: Decompile, recompile, sign, and modify Android applications
- **OTA Package Creation**: Build over-the-air update packages
- **Sparse Image Handling**: Convert between sparse and raw image formats
- **Super Partition Manipulation**: Work with modern Android super partitions
- **Binary Modding Tools**: Comprehensive archive and compression support (7z, zip, etc.)
- **Device Flashing**: Heimdall/Odin flashing support for Samsung devices
- **Project-Based Workflow**: Organized development with project management
- **30+ Tool Integration**: Extensive collection of external tools in the tools/ directory

### Detailed Functionality

#### Firmware Operations
- **Firmware Loading**: Load and analyze .tar.md5 firmware files
- **Entry Extraction**: Extract individual partitions and files from firmware
- **Entry Replacement**: Modify firmware entries in-place with MD5 updates
- **Firmware Building**: Create new firmware packages from modified components
- **MD5 Verification**: Verify firmware integrity and signatures

#### ROM Development
- **System Image Extraction**: Extract system.img using simg2img and mount
- **ROM Building**: Create custom ROM ZIP files from extracted images
- **Property Modification**: Edit build.prop and system properties
- **Keystore Management**: Create and manage signing keystores

#### APK Manipulation
- **APK Decompilation**: Convert APK to source code using apktool
- **APK Recompilation**: Build APK from modified source
- **APK Signing**: Sign APKs with debug or custom keystores
- **Compression Optimization**: Fix APK compression for Android R+ compatibility

#### Boot Image Tools
- **Boot Image Unpacking**: Extract kernel, ramdisk, and dtb from boot.img
- **Boot Image Repacking**: Create new boot images from modified components
- **Kernel Extraction**: Extract and modify Linux kernels
- **Device Tree Modification**: Edit device tree binaries (DTB) and sources (DTS)
- **Ramdisk Management**: Extract, modify, and repack ramdisk cpio archives

#### Compression & Archives
- **LZ4 Support**: Compress/decompress LZ4 files
- **TAR Operations**: Handle TAR archives with MD5 footers
- **7z/Zip Support**: Comprehensive archive manipulation
- **Sparse Conversion**: Convert between sparse and raw Android images

#### Device Integration
- **Heimdall Flashing**: Flash firmware to Samsung devices via USB
- **Device Detection**: Automatic device recognition and connection
- **Admin Privileges**: Windows UAC elevation for flashing operations

#### Advanced Features
- **Hex Editor**: Built-in hex editor with live data analysis
- **File Editor**: Advanced text editor with syntax highlighting
- **Entropy Analysis**: Analyze file entropy for security research
- **String Extraction**: Extract printable strings from binaries
- **Byte Histogram**: Statistical analysis of binary data
- **Live Converters**: Real-time conversion between data formats (hex, integer, float, strings)

## System Requirements

- **Python 3.7+**
- **Java JDK** (for APK tools and signing)
- **Windows/Linux/macOS** (cross-platform support)
- **Administrator privileges** (for device flashing on Windows)

## Installation

1. Clone or download the repository
2. Ensure Python 3.7+ is installed
3. Install Java JDK if APK manipulation is needed
4. Place required tools in the `tools/` directory (see tool integration below)

## Usage

### GUI Mode (Recommended)
```bash
python src/smartphone_firmware_screws.py
```

### Command Line
The application provides a comprehensive GUI interface with the following main sections:

- **Firmware Tab**: Load, analyze, and modify firmware files
- **ROM Tab**: Build and customize Android ROMs
- **APK Tab**: Decompile, modify, and recompile Android apps
- **Boot Tab**: Work with boot images and kernels
- **Tools Tab**: Manage external tools and check system status
- **Hex Editor**: Advanced binary file editing
- **File Editor**: Text file editing with syntax highlighting

## Tool Integration

The application integrates with 30+ external tools located in the `tools/` directory:

### Required Tools
- **Java**: APK compilation and signing
- **7z**: Archive manipulation
- **bsdtar**: TAR/CPIO operations
- **lz4**: LZ4 compression
- **simg2img/img2simg**: Sparse image conversion
- **apktool**: APK decompilation/recompilation
- **zipalign**: APK alignment
- **apksigner**: APK signing
- **magiskboot**: Boot image manipulation
- **heimdall**: Samsung device flashing
- **notepad++**: Advanced text editing

### Optional Tools
- **dtc**: Device tree compilation
- **extract-dtb**: Kernel DTB extraction
- **dtb-converter**: Device tree conversion
- **Various compression tools**: gzip, xz, bzcat, etc.

## Project Structure

```
SmartPhone Firmware Screws/
├── src/
│   └── smartphone_firmware_screws.py  # Main application
├── tools/                             # External tools directory
├── LICENSE.md                         # Dual license information
├── COMMERCIAL_LICENSE.md              # Commercial license terms
├── README.md                          # This file
└── Various project files
```

## License

This project uses a **dual licensing model**:

### Open Source License
- **GNU General Public License v2.0 (GPL-2.0)** with commercial use restrictions
- Permits non-commercial use, modification, and distribution
- **Commercial use requires a separate commercial license**

### Commercial License
- Available for commercial use, redistribution, and proprietary development
- Contact the copyright holder for licensing terms
- Includes support and custom development options

See `LICENSE.md` and `COMMERCIAL_LICENSE.md` for complete license terms.

## Author

**Isaki Dube** (djlaserman)

## Contributing

This project welcomes contributions. Please ensure all changes comply with the dual licensing model.

## Disclaimer

This software is provided "AS IS" without warranty. Use at your own risk. Device flashing can potentially brick devices if not done correctly. Always backup important data before flashing.

## Version

**Version 1.0.0** - Latest release with enhanced features and bug fixes.
