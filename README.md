# Smartphone Firmware Screws

## Ultimate Firmware Studio - Complete Android ROM & Firmware Toolkit

Windows-focused Android firmware and ROM workspace for inspecting Samsung firmware, porting ROM components, editing binary and text files, managing APK/XAPK projects, and preparing Odin/Heimdall packages.

## Features

### Core Capabilities

- **Samsung Firmware Workflow**: Load, inspect, extract, modify, verify, and package `.tar.md5` firmware
- **Odin Package Creation**: Build AP/BL/CP/CSC packages with TAR validation and MD5 footer verification
- **Boot Image Modification**: Edit kernel, ramdisk, cmdline, and other boot components
- **System Customization**: Modify system/vendor/product partitions and properties
- **APK/XAPK Workspace**: Analyze APK, XAPK, APKS, and APKM packages and manage decoded/build/signing artifacts
- **OTA Package Creation**: Build over-the-air update packages
- **Sparse Image Handling**: Convert between sparse and raw image formats
- **Super Partition Manipulation**: Work with modern Android super partitions
- **Binary Modding Tools**: Comprehensive archive and compression support (7z, zip, etc.)
- **Device Flashing**: Heimdall/Odin flashing support for Samsung devices
- **Project-Based Workflow**: Save and restore tabs, folders, editor state, Port ROM state, APK projects, and UI settings
- **Tool Resolver and Manager**: Detect, download, stage, and refresh integrated tools from the Tools tab
- **Windows CI Releases**: GitHub Actions builds and publishes a PyInstaller Windows executable for version tags

### Detailed Functionality

#### Firmware Operations

- **Firmware Loading**: Load and analyze .tar.md5 firmware files
- **Entry Extraction**: Extract individual partitions and files from firmware
- **Entry Replacement**: Modify firmware entries in-place with MD5 updates
- **Firmware Building**: Create new firmware packages from modified components
- **MD5 Verification**: Verify firmware integrity and signatures
- **TAR Safety Checks**: Validate regular TAR members, reject unsafe links, detect duplicate AP members, and select source packages deterministically

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
- **Bundle Analysis**: Run AAPT2 analysis against extracted inner APKs instead of outer XAPK/APKS/APKM containers
- **Manifest Patching**: Patch debuggable mode, application labels, permissions, and network security configuration through decoded manifests

#### Port ROM Workflow

The Port ROM tab contains 35 ordered steps grouped into preparation, extraction, analysis, modification, repacking, packaging, and validation phases. Steps cover firmware extraction, LZ4 and sparse image conversion, super/boot/ramdisk handling, DTB and SELinux work, APK analysis, image rebuilding, Odin packaging, AVB checks, MD5 checks, and manifest generation.

- Dependencies remain locked by default.
- Each step has independent `Skip` and `Done` acknowledgements.
- Explicitly skipping or acknowledging a prerequisite unlocks dependent steps.
- Skip and Done are mutually exclusive and are saved with the project.
- Porting steps are available in the Port ROM UI and the ordered `Port ROM > Porting Steps` menu.

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

- **Hex Editor**: Binary editing, undo/redo, searching, replacement, bookmarks, selections, endian conversion, entropy, strings, histograms, hashes, and context-menu analysis
- **File Editor**: Folder tree, unsaved buffers, syntax highlighting, language selection, line numbers, word wrap, font controls, find/replace, and Notepad++ integration
- **Split Workspace**: Split notebooks horizontally or vertically while preserving live tab widgets and editor state
- **Open Tab**: Reopen Firmware, ROM Building, Hex Editor, File Editor, APK/XAPK, Port ROM, and Tools tabs from the View menu
- **Entropy Analysis**: Analyze file entropy for security research
- **String Extraction**: Extract printable strings from binaries
- **Byte Histogram**: Statistical analysis of binary data
- **Live Converters**: Real-time conversion between data formats (hex, integer, float, strings)

#### Project Persistence

Project files store the current workflow state, including:

- Visible and selected tabs
- Firmware and Hex Editor file paths
- Hex layout, endian mode, gutter, font, and scroll position
- File Editor folder, current file, unsaved content, wrapping, syntax highlighting, line numbers, and font size
- Port ROM folders, device fields, step statuses, step results, and Skip/Done overrides
- APK/XAPK source, extracted/decoded/build/signing paths, package metadata, and bundle file lists
- Status bar and activity log visibility

## System Requirements

- **Windows 10/11** for the packaged executable and device workflows
- **Python 3.9+** for source execution
- **Java JDK** (for APK tools and signing)
- **Administrator privileges** when using device detection or flashing

## Installation

### Run from source

1. Clone or download the repository.
2. Ensure Python and Java are installed when APK operations are needed.
3. Place or download external tools into `src/tools/`.
4. Start the GUI:

```bash
python src/smartphone_firmware_screws.py
```

### Windows executable

Tagged GitHub releases are built automatically by [`.github/workflows/windows-build.yml`](.github/workflows/windows-build.yml). Each release contains the Windows executable, `VERSION.txt`, and `SHA256SUMS.txt`.

## Usage

### GUI Mode (Recommended)

```bash
python src/smartphone_firmware_screws.py
```

### Main workspace sections

- **Firmware Tab**: Load, analyze, and modify firmware files
- **ROM Building Tab**: Build and customize Android ROMs
- **Hex Editor Tab**: Inspect and modify binary files
- **File Editor Tab**: Edit text and decoded project files
- **APK/XAPK Tab**: Analyze, disassemble, assemble, sign, bundle, and patch Android packages
- **Port ROM Tab**: Run the ordered Samsung ROM porting workflow
- **Tools Tab**: Manage external tools and check system status

Use `File > New Project`, `File > Open Project`, and `File > Save Project` to persist the workspace state.

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

```text
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

## Version and Releases

The source currently reports version `1.0.0`. The `v1.0.1` GitHub release is built by CI with its tag version, and future `vMAJOR.MINOR.PATCH` tags automatically produce versioned Windows artifacts and releases.
