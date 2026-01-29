# FATN_to_USB Requirements Document

## 1. Project Overview

### 1.1 Purpose
The FATN_to_USB system is designed to automate the downloading and USB loading of weekly audio content from the Farnham and Alton Talking News (FATN) service. The system provides an accessible solution for blind and partially sighted users who rely on FATN audio recordings of local newspapers.

### 1.2 Target Audience
- Blind and partially sighted users
- Volunteers managing FATN distribution
- Users with limited technical expertise

### 1.3 Target Platform
- Primary: Raspberry Pi Zero (or compatible models)
- Operating System: Linux-based (Raspberry Pi OS/Raspbian)
- Python 3.8 or higher required

## 2. Functional Requirements

### 2.1 USB Detection (FR-001)
**Priority: HIGH**
- The system SHALL detect when a USB drive is inserted into the device
- The system SHALL distinguish USB drives from other storage devices (e.g., SD cards on Raspberry Pi)
- The system SHALL support standard USB mass storage devices
- The system SHALL use udisks2 for USB device management

### 2.2 Content Download (FR-002)
**Priority: HIGH**
- The system SHALL download the latest FATN audio content from the FATN website
- The system SHALL parse the FATN website (https://www.fatntalkingnews.org.uk/about-fatn-talking-news/#coronavirus) to extract the Dropbox link
- The system SHALL handle TinyURL redirects to retrieve the actual Dropbox URL
- The system SHALL convert Dropbox preview links (?dl=0) to download links (?dl=1)
- The system SHALL download the ZIP file containing audio content
- The system SHALL save downloaded files with the name "FATN News Weekly File.zip"
- The system SHALL support resumable downloads (chunked downloading with 8KB chunks)

### 2.3 Content Extraction (FR-003)
**Priority: HIGH**
- The system SHALL extract MP3 files from the downloaded ZIP archive
- The system SHALL remove old MP3 files from the USB drive before copying new files
- The system SHALL copy extracted MP3 files to the USB drive
- The system SHALL ensure file integrity through proper synchronization (fsync)

### 2.4 Visual Feedback (FR-004)
**Priority: MEDIUM**
- The system SHALL provide visual status updates via an LCD display
- The system SHALL support ST7789 display drivers
- The system SHALL support ST7735 display drivers as a fallback
- The system SHALL display messages with customizable RGB background colors
- The system SHALL implement auto-scrolling for messages longer than display width
- The system SHALL scroll messages for up to 120 seconds
- The system SHALL use DejaVuSans-Bold font at 50pt for display messages
- The system SHALL provide visual indication when:
  - USB is detected
  - Download is in progress
  - Content is being copied
  - USB is ready for removal

### 2.5 Safe USB Removal (FR-005)
**Priority: HIGH**
- The system SHALL properly unmount USB drives before indicating safe removal
- The system SHALL synchronize all pending writes before unmounting
- The system SHALL provide clear indication when USB can be safely removed

### 2.6 Boot-Time Initialization (FR-006)
**Priority: MEDIUM**
- The system SHALL display status messages on boot
- The system SHALL accept command-line arguments for custom boot messages
- The system SHALL support RGB color specification for boot messages
- Default boot message color SHALL be green (0, 255, 0)

## 3. Non-Functional Requirements

### 3.1 Reliability (NFR-001)
**Priority: HIGH**
- The system SHALL handle network failures gracefully
- The system SHALL implement comprehensive error handling for:
  - File system errors (FileExistsError, FileNotFoundError, PermissionError, etc.)
  - Network errors (ConnectionError, TimeoutError, HTTPError, etc.)
  - SSL/TLS errors
  - Disk space errors
- The system SHALL log error conditions for troubleshooting
- The system SHALL not crash on recoverable errors

### 3.2 Usability (NFR-002)
**Priority: HIGH**
- The system SHALL require minimal user interaction
- The system SHALL operate automatically once USB is inserted
- The system SHALL provide clear, readable visual feedback
- The system SHALL be operable by users with visual impairments (through audio feedback if speaker attached)
- The system SHALL not require command-line interaction during normal operation

### 3.3 Performance (NFR-003)
**Priority: MEDIUM**
- The system SHALL complete downloads within reasonable time given network bandwidth
- The system SHALL use efficient chunked downloading (8KB chunks)
- The system SHALL display updates without blocking other operations
- LCD display refresh SHALL support 80MHz SPI speed for ST7789
- LCD display refresh SHALL support 10MHz SPI speed for ST7735

### 3.4 Maintainability (NFR-004)
**Priority: MEDIUM**
- Code SHALL follow Python best practices and PEP 8 style guidelines
- Error messages SHALL be descriptive and actionable
- The system SHALL use clear separation of concerns (parsing, downloading, display, USB management)
- Dependencies SHALL be managed via Poetry
- Version numbers SHALL be consistent across all configuration files

### 3.5 Security (NFR-005)
**Priority: MEDIUM**
- The system SHALL validate downloaded content
- The system SHALL use HTTPS for all web requests
- The system SHALL verify SSL certificates
- The system SHALL have appropriate file system permissions
- The system SHALL use PolicyKit for privilege management

### 3.6 Portability (NFR-006)
**Priority: LOW**
- The system SHALL detect platform type (Raspberry Pi vs. other Linux systems)
- The system SHALL adapt behavior based on detected hardware
- The system SHALL be configurable for different hardware setups

## 4. Technical Requirements

### 4.1 Hardware Requirements (TR-001)
**Minimum:**
- Raspberry Pi Zero (or compatible)
- Internet connectivity (WiFi)
- USB port for target USB drive
- LCD display (ST7789 or ST7735 compatible)
- SPI interface enabled

**Optional:**
- Powered speaker or Bluetooth speaker
- Audio output HAT (e.g., pHAT DAC)

### 4.2 Software Dependencies (TR-002)
**Python Version:**
- Python 3.8 or higher

**Core Dependencies:**
- argparse ^1.4.0 - Command-line argument parsing
- Pillow ^10.3.0 - Image manipulation for LCD displays
- requests ^2.32.4 - HTTP client for downloads
- ST7789 ^0.0.2 - Primary display driver
- ST7735 ^0.0.4 - Alternative display driver

**System Dependencies:**
- udisks2 - USB disk management
- PolicyKit - Permission management
- SPI kernel module - Display communication
- DejaVuSans-Bold.ttf font

### 4.3 Network Requirements (TR-003)
- Active internet connection
- Access to https://www.fatntalkingnews.org.uk
- Access to Dropbox (for file downloads)
- DNS resolution capability
- TLS/SSL support

### 4.4 File System Requirements (TR-004)
- Write access to /home/pi/ directory
- Read access to /proc/cpuinfo
- Write access to USB mount points
- Support for FAT32/exFAT formatted USB drives

### 4.5 Permission Requirements (TR-005)
- User SHALL be member of 'adm' group (for udisks operations)
- PolicyKit configuration SHALL allow:
  - Mounting/unmounting filesystems (udisks1 and udisks2)
  - Unlocking encrypted drives
  - Ejecting media and powering off drives
- SPI device access permissions

## 5. System Constraints

### 5.1 Design Constraints (DC-001)
- System is designed specifically for FATN website structure
- HTML parsing depends on specific website format (anchor tags with 'tinyurl' in href)
- Hard-coded paths assume Raspberry Pi default user (/home/pi/)
- Display code assumes specific SPI configurations

### 5.2 Implementation Constraints (DC-002)
- Must use Python 3.8+ (due to dependency requirements)
- Limited to Linux-based operating systems
- Requires physical LCD display (no headless mode)
- USB drive must be FAT32 or exFAT formatted

### 5.3 External Dependencies (DC-003)
- FATN website availability and structure
- Dropbox service availability
- TinyURL service availability
- Internet connectivity
- PyPI package availability for installations

## 6. Data Requirements

### 6.1 Input Data (DR-001)
- FATN website HTML content
- Dropbox download URLs
- ZIP file containing audio recordings
- User-provided configuration (boot messages, colors)

### 6.2 Output Data (DR-002)
- Downloaded ZIP files
- Extracted MP3 audio files
- Log messages (console output)
- LCD display output

### 6.3 Data Formats (DR-003)
- Input: ZIP archives containing MP3 files
- Output: MP3 audio files
- Configuration: Command-line arguments (strings, integers)
- Display: RGB color values (0-255 per channel)

## 7. Interface Requirements

### 7.1 User Interface (UI-001)
- LCD display showing status messages
- Visual color coding (green = success, other colors for different states)
- Scrolling text for long messages

### 7.2 Hardware Interface (HI-001)
- SPI interface for LCD displays
- USB interface for storage devices
- GPIO pins for display control (CS, DC, backlight)

### 7.3 Software Interface (SI-001)
- udisks2 D-Bus interface for USB management
- HTTP/HTTPS for web content retrieval
- File system interface for file operations

### 7.4 Network Interface (NI-001)
- HTTPS connections to FATN website
- HTTPS connections to Dropbox
- HTTP redirects handling (TinyURL)

## 8. Quality Attributes

### 8.1 Accessibility
- Design SHALL prioritize accessibility for visually impaired users
- Feedback mechanisms SHALL be clear and unambiguous
- Operation SHALL require minimal visual monitoring

### 8.2 Robustness
- System SHALL handle temporary network outages
- System SHALL recover from partial downloads
- System SHALL handle malformed HTML gracefully
- System SHALL handle full disk conditions

### 8.3 Simplicity
- User operation SHALL be plug-and-play
- Installation SHALL be straightforward
- Configuration SHALL be minimal

## 9. Known Issues and Limitations

### 9.1 Current Implementation Gaps
1. **Incomplete USB Management** (copy-Fatn.py file)
   - Core USB mounting/copying logic is commented out
   - Automatic USB detection not fully implemented
   - Integration between modules is incomplete

2. **Version Inconsistency**
   - __init__.py declares version 0.3.0
   - pyproject.toml files declare version 0.1.0
   - Tests expect version 0.1.0

3. **Code Quality Issues**
   - scrolling_text.py:11 has syntax error (missing try block)
   - require_version() call not properly wrapped
   - Inconsistent code formatting

4. **Testing Coverage**
   - Only version check test implemented
   - No functional tests for core features
   - No integration tests

5. **Hard-coded Paths**
   - /home/pi/ directory hard-coded
   - Not portable to different username configurations

6. **Fragile Web Scraping**
   - HTML parsing depends on specific website structure
   - No fallback if website structure changes
   - No validation of extracted URLs

### 9.2 Assumptions
- FATN website structure remains consistent
- Dropbox links continue to be published via TinyURL
- USB drives are pre-formatted (FAT32/exFAT)
- User has administrator/adm group privileges
- SPI interface is pre-configured and enabled

## 10. Future Enhancements

### 10.1 Potential Features
1. Audio feedback for users (using optional speaker)
2. Automatic detection of new content availability
3. Scheduled automatic downloads
4. Multiple content source support
5. Configuration file for customization
6. Email notifications on completion
7. Error logging to file
8. Web interface for monitoring
9. Retry logic for failed downloads
10. Content verification (checksum validation)

### 10.2 Scalability Considerations
- Support for multiple USB drives simultaneously
- Support for different audio formats
- Support for different zip archive structures
- Configurable download locations
- Multi-user support

## 11. Compliance and Standards

### 11.1 Licensing
- Project SHALL be licensed under GNU General Public License v3.0
- All dependencies SHALL have compatible licenses

### 11.2 Coding Standards
- Python code SHALL follow PEP 8 style guide
- Docstrings SHALL follow PEP 257 conventions
- Type hints SHALL be used where appropriate

### 11.3 Accessibility Standards
- Design SHALL consider WCAG principles where applicable
- Audio feedback SHALL follow best practices for visually impaired users

## 12. Success Criteria

The project SHALL be considered successful when:

1. System reliably downloads latest FATN content (95% success rate)
2. Content is correctly extracted to USB drives
3. Visual feedback is clear and understandable
4. System operates without requiring technical intervention
5. Error conditions are handled gracefully
6. USB drives can be safely removed without data corruption
7. System works on target hardware (Raspberry Pi Zero)
8. Users can operate system independently
9. Version consistency is maintained across all files
10. Test coverage exceeds 80% for core functionality

## 13. Approval and Sign-off

### 13.1 Document Version
- Version: 1.0
- Date: 2025-12-04
- Status: Draft

### 13.2 Review and Approval
- Technical Review: Pending
- User Acceptance: Pending
- Final Approval: Pending

### 13.3 Change History
| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-04 | Claude Code Review | Initial requirements document created |
