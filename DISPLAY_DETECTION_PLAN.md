# Display Detection and Fallback Strategy Plan

## Executive Summary

This document outlines a comprehensive strategy for detecting and utilizing various display outputs on Raspberry Pi systems for the FATN_to_USB project. The plan provides a cascading fallback mechanism from specialized GPIO-based displays to HDMI outputs and finally to console-based text output, ensuring the system can provide user feedback regardless of the hardware configuration.

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Display Detection Strategy](#2-display-detection-strategy)
3. [Display Types and Detection Methods](#3-display-types-and-detection-methods)
4. [Implementation Phases](#4-implementation-phases)
5. [Technical Implementation Details](#5-technical-implementation-details)
6. [Testing Strategy](#6-testing-strategy)
7. [References and Resources](#7-references-and-resources)

---

## 1. Current State Analysis

### 1.1 Existing Implementation

The current `scrolling_text.py` module attempts to initialize displays in the following order:

1. **ST7789** display (SPI-based, 240x240 pixels)
2. **ST7735** display (SPI-based, 160x80 pixels, as fallback)
3. If both fail, `disp = None` (no display available)

### 1.2 Limitations

- **No detection mechanism** - Relies on ImportError/RuntimeError during initialization
- **Hard-coded display types** - Only supports two specific display models
- **No HDMI fallback** - Cannot use standard monitors/TVs
- **No console fallback** - Silent failure if no display available
- **No automatic detection** - Cannot determine which display is actually connected

### 1.3 User Impact

- Users with different display hardware cannot use the system
- Users with only HDMI displays get no visual feedback
- Headless systems provide no user feedback mechanism
- Debugging display issues is difficult without detection logs

---

## 2. Display Detection Strategy

### 2.1 Cascading Fallback Hierarchy (Updated for RPi Zero/Zero 2)

**Target Hardware:** Raspberry Pi Zero, Zero W, Zero 2 W
**Target OS:** Debian Trixie Slim (console-only minimum), with GUI detection

```
Priority 1: Known GPIO Displays (Expected Hardware)
    ├── ST7789 (240x240, SPI) - Primary expected display
    └── ST7735 (160x80, SPI) - Secondary expected display

Priority 2: Raspberry Pi Model Detection
    ├── Detect RPi Zero/Zero 2 vs other models
    ├── Read /proc/cpuinfo for hardware identification
    └── Determine display capabilities based on model

Priority 3: GUI Availability Check
    ├── Check for X11 display server (DISPLAY environment)
    ├── Check for Wayland compositor
    ├── Detect desktop environment presence
    └── Fall back to framebuffer if GUI unavailable

Priority 4: Framebuffer/Console Output
    ├── /dev/fb0 (if HDMI connected)
    ├── Console/TTY output (always available)
    └── Syslog logging (headless fallback)

Priority 5: Headless/Log-Only Mode
    └── systemd journal logging only
```

### 2.2 Detection Philosophy (Revised)

**Hardware-First Approach**: The system is designed for Raspberry Pi Zero/Zero 2 with one of two specific SPI displays. Detection prioritizes these known configurations before attempting fallbacks.

**Stages:**
1. **Stage 1:** Try ST7789 and ST7735 initialization (expected configuration)
2. **Stage 2:** If no SPI display found, identify the Raspberry Pi model
3. **Stage 3:** Based on RPi model, check for GUI vs console-only environment
4. **Stage 4:** Select appropriate output method (framebuffer, console, or log-only)

**Key Principle**: Graceful degradation from the expected configuration to whatever output is available.

---

## 3. Display Types and Detection Methods

### 3.0 Raspberry Pi Model Detection (Priority 2)

#### Raspberry Pi Zero and Zero 2 Identification

**Target Models:**
- Raspberry Pi Zero (ARMv6, BCM2835, single-core, 512MB)
- Raspberry Pi Zero W (Zero + WiFi/Bluetooth)
- Raspberry Pi Zero 2 W (ARMv8, BCM2710A1, quad-core, 512MB)

#### Detection Method

**Read /proc/cpuinfo:**
```python
def detect_raspberry_pi_model():
    """
    Detect specific Raspberry Pi model from /proc/cpuinfo.

    Returns:
        dict: Model information including type, revision, and capabilities
    """
    model_info = {
        'model': 'unknown',
        'is_zero': False,
        'is_zero_2': False,
        'hardware': None,
        'revision': None
    }

    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()

        for line in cpuinfo.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()

                if key == 'Hardware':
                    model_info['hardware'] = value
                elif key == 'Revision':
                    model_info['revision'] = value
                elif key == 'Model':
                    model_info['model'] = value

                    # Detect Zero variants
                    if 'Zero' in value:
                        model_info['is_zero'] = True
                        if 'Zero 2' in value:
                            model_info['is_zero_2'] = True

    except FileNotFoundError:
        pass

    return model_info
```

**Revision Code Lookup:**
```python
# Raspberry Pi revision codes for Zero models
ZERO_REVISIONS = {
    '900092': 'Pi Zero 1.2',
    '900093': 'Pi Zero 1.3',
    '920093': 'Pi Zero 1.3',
    '9000c1': 'Pi Zero W 1.1',
    '902120': 'Pi Zero 2 W 1.0'
}

def identify_zero_model(revision):
    """Identify specific Zero model from revision code."""
    return ZERO_REVISIONS.get(revision, 'Unknown Zero variant')
```

#### Zero-Specific Considerations

| Model | CPU | Architecture | Limitations |
|-------|-----|--------------|-------------|
| Zero | BCM2835 Single-core | ARMv6 | Limited processing power |
| Zero W | BCM2835 Single-core | ARMv6 | WiFi/BT, same CPU as Zero |
| Zero 2 W | BCM2710A1 Quad-core | ARMv8 (64-bit capable) | Much faster, use for performance |

**Performance Implications:**
- Zero/Zero W: Avoid heavy framebuffer operations, prioritize SPI displays
- Zero 2 W: Can handle framebuffer rendering, more display options
- All models: 512MB RAM limit, minimize memory usage

### 3.0.1 GUI Detection (Priority 3)

#### Debian Trixie Environment Detection

**Minimum Target:** Debian Trixie Slim (console-only, no GUI)
**Optional:** Full desktop environment (if installed)

#### Detection Methods

**1. X11 Display Server Detection:**
```python
import os

def detect_x11():
    """Check if X11 display server is running."""
    display = os.environ.get('DISPLAY')

    if not display:
        return False

    # Check if X server is actually responding
    try:
        import subprocess
        result = subprocess.run(
            ['xdpyinfo'],
            capture_output=True,
            timeout=2
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
```

**2. Wayland Compositor Detection:**
```python
def detect_wayland():
    """Check if Wayland compositor is running."""
    wayland_display = os.environ.get('WAYLAND_DISPLAY')
    xdg_session_type = os.environ.get('XDG_SESSION_TYPE')

    if wayland_display or xdg_session_type == 'wayland':
        return True

    # Check for Wayland socket
    wayland_socket = f"/run/user/{os.getuid()}/wayland-0"
    return os.path.exists(wayland_socket)
```

**3. Desktop Environment Detection:**
```python
def detect_desktop_environment():
    """Detect if a desktop environment is running."""
    # Check common DE indicators
    de_indicators = [
        'XDG_CURRENT_DESKTOP',
        'DESKTOP_SESSION',
        'GNOME_DESKTOP_SESSION_ID',
        'KDE_FULL_SESSION'
    ]

    for indicator in de_indicators:
        if os.environ.get(indicator):
            return {
                'has_gui': True,
                'type': os.environ.get(indicator),
                'session': os.environ.get('XDG_SESSION_TYPE', 'unknown')
            }

    return {'has_gui': False, 'type': None, 'session': 'console'}
```

**4. Console-Only Detection:**
```python
def is_console_only():
    """Determine if running in console-only (no GUI) mode."""
    # Check if running on a virtual terminal (tty)
    if os.environ.get('TERM', '').startswith('linux'):
        return True

    # Check if SSH session
    if os.environ.get('SSH_CONNECTION') or os.environ.get('SSH_CLIENT'):
        return True

    # No DISPLAY and no WAYLAND_DISPLAY
    if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
        return True

    return False
```

#### GUI Availability Matrix

| Environment | Detection Method | Available Outputs |
|-------------|------------------|-------------------|
| Debian Trixie Slim (console) | TERM=linux, no DISPLAY | SPI displays, Console, FB |
| Trixie + X11 | DISPLAY set, xdpyinfo works | All display types |
| Trixie + Wayland | WAYLAND_DISPLAY set | All display types |
| SSH Session | SSH_CONNECTION set | SPI displays, Console |
| Headless | No TTY, no DISPLAY | SPI displays, Logging only |

#### Debian Trixie Specific Considerations

**OS Detection:**
```python
def detect_debian_version():
    """Detect Debian version."""
    try:
        with open('/etc/debian_version', 'r') as f:
            version = f.read().strip()

        # Trixie is version 13
        if version.startswith('13') or 'trixie' in version.lower():
            return 'trixie'

        return version
    except FileNotFoundError:
        return None
```

**Minimal Installation Check:**
```python
def is_minimal_install():
    """Check if running Debian Slim/minimal install."""
    # Check for common GUI packages
    gui_packages = [
        'xserver-xorg',
        'lightdm',
        'gdm3',
        'lxde',
        'xfce4'
    ]

    try:
        result = subprocess.run(
            ['dpkg', '-l'] + gui_packages,
            capture_output=True,
            text=True,
            timeout=5
        )

        # If none installed, likely minimal
        return 'no packages found' in result.stderr.lower()
    except:
        # Assume minimal if can't determine
        return True
```

### 3.1 SPI-Based Displays (GPIO) - Priority 1

#### Detection Method

**SPI Device Enumeration:**
```python
import os
import glob

def detect_spi_devices():
    """Detect available SPI devices."""
    spi_devices = glob.glob('/dev/spidev*')
    return spi_devices
```

**SPI Bus Scanning:**
```python
try:
    import spidev
    spi = spidev.SpiDev()
    # Try opening SPI bus 0, chip select 0
    spi.open(0, 0)
    # Display might be present
    spi.close()
    return True
except (FileNotFoundError, PermissionError):
    return False
```

#### Common SPI Displays

| Display Model | Resolution | Bus/CS | DC Pin | Notes |
|---------------|------------|--------|--------|-------|
| ST7789 | 240x240 | SPI0, CS0/1 | GPIO 9 | Current primary |
| ST7735 | 160x80 | SPI0, CS1 | GPIO 9 | Current fallback |
| ILI9341 | 320x240 | SPI0 | GPIO 25 | Common TFT |
| ILI9486 | 480x320 | SPI0 | GPIO 24 | Larger TFT |

#### Detection Strategy

1. Check if `/dev/spidev0.0` and `/dev/spidev0.1` exist
2. Attempt to import display libraries (ST7789, ST7735, etc.)
3. Try initializing each display with common pin configurations
4. Verify display responds to test commands
5. Select first successfully initialized display

### 3.2 I2C-Based Displays (GPIO)

#### Detection Method

**I2C Bus Scanning:**
```bash
# Command-line detection
i2cdetect -y 1  # Scan I2C bus 1 (GPIO pins 2/3)
```

**Python Detection:**
```python
import smbus
import subprocess

def detect_i2c_devices():
    """Detect I2C devices on bus 1."""
    try:
        # Check if I2C is enabled
        if not os.path.exists('/dev/i2c-1'):
            return []

        # Run i2cdetect command
        result = subprocess.run(
            ['i2cdetect', '-y', '1'],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Parse addresses from output
        devices = []
        for line in result.stdout.split('\n')[1:]:
            parts = line.split()
            for addr in parts[1:]:
                if addr != '--' and addr.isalnum():
                    devices.append(int(addr, 16))

        return devices
    except Exception as e:
        print(f'I2C detection error: {e}')
        return []
```

#### Common I2C Displays

| Display Model | Resolution | I2C Address | Notes |
|---------------|------------|-------------|-------|
| SSD1306 | 128x64 | 0x3C or 0x3D | Common OLED |
| SH1106 | 128x64 | 0x3C | OLED variant |
| SSD1331 | 96x64 | 0x3C | Color OLED |
| LCD1602 | 16x2 chars | 0x27 or 0x3F | Character LCD |

#### Detection Strategy

1. Enable I2C if not already enabled (check `/boot/config.txt`)
2. Scan I2C bus 1 (GPIO 2/3) for devices
3. Match detected addresses to known display types
4. Attempt initialization with detected address
5. Verify display responds to test pattern

### 3.3 HDMI/Framebuffer Displays

#### Detection Method

**Framebuffer Detection:**
```python
import os

def detect_framebuffer():
    """Detect available framebuffer devices."""
    framebuffers = []

    for fb in ['/dev/fb0', '/dev/fb1', '/dev/fb2']:
        if os.path.exists(fb):
            try:
                # Try to get framebuffer info
                with open(f'/sys/class/graphics/{os.path.basename(fb)}/name', 'r') as f:
                    fb_name = f.read().strip()

                # Check if framebuffer is functional
                stat = os.stat(fb)
                if stat.st_size > 0 or os.access(fb, os.W_OK):
                    framebuffers.append({
                        'device': fb,
                        'name': fb_name
                    })
            except Exception:
                pass

    return framebuffers
```

**HDMI Hotplug Detection:**
```python
def detect_hdmi_connection():
    """Check if HDMI display is connected."""
    try:
        # Check HDMI hotplug status (requires root)
        hotplug_paths = [
            '/sys/kernel/debug/dri/card1/hdmi0_regs',
            '/sys/kernel/debug/dri/card1/hdmi1_regs'
        ]

        for path in hotplug_paths:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    content = f.read()
                    if 'HOTPLUG' in content and 'connected' in content.lower():
                        return True
    except PermissionError:
        # Fall back to checking if framebuffer exists
        return os.path.exists('/dev/fb0')

    return False
```

**KMS/DRM Detection (Modern Method):**
```python
def detect_kms_displays():
    """Detect displays using KMS/DRM."""
    try:
        import subprocess

        # Use modetest to enumerate displays
        result = subprocess.run(
            ['modetest', '-M', 'vc4'],
            capture_output=True,
            text=True,
            timeout=5
        )

        # Parse connected displays
        connected = []
        for line in result.stdout.split('\n'):
            if 'connected' in line.lower():
                connected.append(line.strip())

        return connected
    except Exception:
        return []
```

#### Raspberry Pi OS Considerations

**Legacy vs. Modern Graphics Stack:**

| OS Version | Graphics Stack | Framebuffer | Notes |
|------------|----------------|-------------|-------|
| Buster (Legacy) | vc4-fkms-v3d | /dev/fb0 available | Uses fake KMS |
| Bullseye+ | vc4-kms-v3d | May not have /dev/fb0 | Full KMS |
| Bookworm 2024 | vc4-kms-v3d | KMSDRM only | No framebuffer |

**Configuration Fix for Framebuffer:**

Edit `/boot/config.txt`:
```ini
# Change from:
# dtoverlay=vc4-kms-v3d

# To (for framebuffer support):
dtoverlay=vc4-fkms-v3d
```

#### Display Libraries for HDMI

**pygame (Recommended for HDMI):**
```python
import pygame
import os

def init_hdmi_display():
    """Initialize pygame for HDMI output."""
    # Set SDL to use framebuffer
    os.environ['SDL_VIDEODRIVER'] = 'fbcon'
    os.environ['SDL_FBDEV'] = '/dev/fb0'

    # For modern systems, try KMSDRM
    # os.environ['SDL_VIDEODRIVER'] = 'kmsdrm'

    pygame.init()
    screen = pygame.display.set_mode((800, 600))
    return screen
```

**PIL + Framebuffer:**
```python
from PIL import Image
import numpy as np

def display_to_framebuffer(image, fb_device='/dev/fb0'):
    """Write PIL image directly to framebuffer."""
    # Get framebuffer info
    with open(fb_device, 'rb+') as fb:
        # Convert image to raw bytes
        data = np.array(image.convert('RGB'))
        # Write to framebuffer
        fb.write(data.tobytes())
```

### 3.4 Console/Terminal Output

#### Detection Method

**TTY Detection:**
```python
import sys
import os

def is_interactive_terminal():
    """Check if running in an interactive terminal."""
    return sys.stdout.isatty() and os.environ.get('TERM')

def get_terminal_size():
    """Get terminal dimensions."""
    try:
        import shutil
        columns, rows = shutil.get_terminal_size()
        return columns, rows
    except:
        return 80, 24  # Default
```

#### Console Output Libraries

**Rich (Modern Terminal UI):**
```python
from rich.console import Console
from rich.progress import Progress
from rich.panel import Panel

console = Console()
console.print("[bold green]USB READY[/bold green]")
console.print(Panel("FATN content downloading...", style="blue"))
```

**Asciimatics (Full TUI):**
```python
from asciimatics.screen import Screen
from asciimatics.scene import Scene
from asciimatics.widgets import Frame, Layout, Label

def display_message(screen, message):
    screen.print_at(message, 0, 0)
    screen.refresh()
```

**Simple ASCII Art:**
```python
from pyfiglet import Figlet

def ascii_message(text):
    """Create large ASCII art text."""
    f = Figlet(font='standard')
    return f.renderText(text)

print(ascii_message('USB READY'))
```

#### Color Support Detection

```python
import sys

def supports_color():
    """Check if terminal supports color."""
    # Check if stdout is a TTY
    if not hasattr(sys.stdout, 'isatty'):
        return False

    if not sys.stdout.isatty():
        return False

    # Check TERM environment variable
    term = os.environ.get('TERM', '')
    if term in ('dumb', 'unknown'):
        return False

    # Check for color support
    return 'color' in term or term in ('xterm', 'linux', 'screen')
```

---

## 4. Implementation Phases

### Phase 1: Enhanced Display Detection (Week 1)

**Objective:** Implement comprehensive display detection across all types.

**Tasks:**
1. Create `display_detector.py` module
2. Implement SPI device detection
3. Implement I2C device detection
4. Implement framebuffer detection
5. Implement console detection
6. Create display capability registry

**Deliverables:**
- `fatn_to_usb/display_detector.py`
- Detection functions for each display type
- Unit tests for detection logic

### Phase 2: Display Abstraction Layer (Week 2)

**Objective:** Create unified display interface for all output types.

**Tasks:**
1. Design `DisplayInterface` abstract base class
2. Implement `SPIDisplay` adapter
3. Implement `I2CDisplay` adapter
4. Implement `FramebufferDisplay` adapter
5. Implement `ConsoleDisplay` adapter
6. Implement `NullDisplay` (headless mode)

**Deliverables:**
- `fatn_to_usb/display/` package
- Abstract interface and concrete implementations
- Unit tests for each adapter

### Phase 3: Smart Display Selection (Week 3)

**Objective:** Implement intelligent display selection with fallback.

**Tasks:**
1. Create `DisplayManager` class
2. Implement priority-based selection
3. Implement automatic fallback
4. Add configuration overrides
5. Add display health monitoring
6. Implement graceful degradation

**Deliverables:**
- `DisplayManager` with auto-detection
- Configuration file support
- Fallback chain implementation

### Phase 4: HDMI/Framebuffer Support (Week 4)

**Objective:** Add full HDMI display support.

**Tasks:**
1. Implement pygame-based HDMI output
2. Add framebuffer direct write support
3. Handle KMS vs framebuffer differences
4. Test on Bullseye and Bookworm
5. Add resolution auto-detection
6. Optimize for performance

**Deliverables:**
- HDMI display adapter
- Framebuffer utilities
- Performance optimizations

### Phase 5: Console Fallback (Week 5)

**Objective:** Implement rich console output for headless operation.

**Tasks:**
1. Add Rich library integration
2. Implement ASCII art status display
3. Add progress bars for operations
4. Implement color-aware output
5. Add syslog integration
6. Create journald structured logging

**Deliverables:**
- Console display adapter
- Rich formatted output
- Logging integration

### Phase 6: Testing and Documentation (Week 6)

**Objective:** Comprehensive testing and documentation.

**Tasks:**
1. Test on Raspberry Pi Zero, 3, 4, 5
2. Test with various display types
3. Test headless operation
4. Create hardware compatibility matrix
5. Write user documentation
6. Create troubleshooting guide

**Deliverables:**
- Test results matrix
- Hardware compatibility guide
- User documentation
- Troubleshooting procedures

---

## 5. Technical Implementation Details

### 5.1 Display Abstraction Layer Design

```python
# fatn_to_usb/display/base.py

from abc import ABC, abstractmethod
from typing import Tuple, Optional

class DisplayInterface(ABC):
    """Abstract base class for all display types."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the display hardware."""
        pass

    @abstractmethod
    def get_capabilities(self) -> dict:
        """Return display capabilities."""
        pass

    @abstractmethod
    def show_message(self, message: str, color: Tuple[int, int, int] = (0, 255, 0)) -> bool:
        """Display a message with optional color."""
        pass

    @abstractmethod
    def clear(self) -> bool:
        """Clear the display."""
        pass

    @abstractmethod
    def shutdown(self) -> bool:
        """Safely shutdown the display."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if display is available and functional."""
        pass

    @property
    @abstractmethod
    def display_type(self) -> str:
        """Return display type identifier."""
        pass
```

### 5.2 Display Manager Implementation

```python
# fatn_to_usb/display/manager.py

from typing import List, Optional
from .base import DisplayInterface
from .spi_display import SPIDisplay
from .i2c_display import I2CDisplay
from .framebuffer_display import FramebufferDisplay
from .console_display import ConsoleDisplay
from .null_display import NullDisplay

class DisplayManager:
    """Manages display detection and selection."""

    def __init__(self, preferred_type: Optional[str] = None):
        self.preferred_type = preferred_type
        self.displays: List[DisplayInterface] = []
        self.active_display: Optional[DisplayInterface] = None

    def detect_displays(self) -> List[DisplayInterface]:
        """Detect all available displays."""
        displays = []

        # Priority 1: SPI displays
        spi_displays = SPIDisplay.detect_all()
        displays.extend(spi_displays)

        # Priority 2: I2C displays
        i2c_displays = I2CDisplay.detect_all()
        displays.extend(i2c_displays)

        # Priority 3: Framebuffer/HDMI
        fb_display = FramebufferDisplay.detect()
        if fb_display:
            displays.append(fb_display)

        # Priority 4: Console
        console_display = ConsoleDisplay.detect()
        if console_display:
            displays.append(console_display)

        # Fallback: Null display (always available)
        displays.append(NullDisplay())

        self.displays = displays
        return displays

    def select_display(self) -> DisplayInterface:
        """Select best available display."""
        if self.preferred_type:
            # Try to find preferred type
            for display in self.displays:
                if display.display_type == self.preferred_type:
                    if display.initialize():
                        self.active_display = display
                        return display

        # Auto-select first working display
        for display in self.displays:
            if display.is_available:
                if display.initialize():
                    self.active_display = display
                    print(f'Selected display: {display.display_type}')
                    return display

        # Should never reach here due to NullDisplay fallback
        return NullDisplay()

    def get_display(self) -> DisplayInterface:
        """Get active display, selecting one if needed."""
        if not self.active_display:
            self.detect_displays()
            self.select_display()
        return self.active_display
```

### 5.3 Configuration File Support

```yaml
# /etc/fatn_to_usb/display.conf (YAML format)

display:
  # Preferred display type (auto, spi, i2c, hdmi, console, null)
  preferred: auto

  # Detection order (comma-separated list)
  priority: spi,i2c,hdmi,console

  # SPI display settings
  spi:
    models: ST7789,ST7735,ILI9341
    bus: 0
    cs: 0
    dc_pin: 9
    backlight_pin: 19

  # I2C display settings
  i2c:
    bus: 1
    scan_addresses: true

  # HDMI/Framebuffer settings
  hdmi:
    device: /dev/fb0
    width: 800
    height: 600
    driver: kmsdrm  # kmsdrm, fbcon, x11

  # Console settings
  console:
    use_color: true
    use_ascii_art: true
    log_to_syslog: true

  # Fallback behavior
  fallback:
    retry_count: 3
    retry_delay: 2
    allow_console: true
```

### 5.4 Example Usage

```python
# In main.py or scrolling_text.py

from display.manager import DisplayManager

# Initialize display manager
display_mgr = DisplayManager()

# Auto-detect and select best display
display = display_mgr.get_display()

# Use display with unified interface
display.show_message("FATN READY", color=(0, 255, 0))
display.show_message("DOWNLOADING", color=(0, 128, 255))
display.show_message("COMPLETE!", color=(0, 255, 0))

# Cleanup
display.shutdown()
```

---

## 6. Testing Strategy

### 6.1 Hardware Test Matrix

| Display Type | RPi Model | OS Version | Status | Notes |
|--------------|-----------|------------|--------|-------|
| ST7789 | Zero W | Bullseye | ✅ | Current |
| ST7789 | 4B | Bullseye | ✅ | Current |
| ST7735 | Zero W | Bullseye | ✅ | Current |
| SSD1306 (I2C) | 4B | Bullseye | 🔄 | To test |
| ILI9341 | 3B+ | Bullseye | 🔄 | To test |
| HDMI via /dev/fb0 | 4B | Bullseye | 🔄 | To test |
| HDMI via KMS | 4B | Bookworm | 🔄 | To test |
| HDMI via KMS | 5 | Bookworm | 🔄 | To test |
| Console | All | All | 🔄 | To test |
| Headless | All | All | 🔄 | To test |

### 6.2 Test Scenarios

1. **Single Display Detection**
   - Connect only one display type
   - Verify correct detection
   - Verify initialization
   - Verify message display

2. **Multiple Display Scenario**
   - Connect SPI + HDMI
   - Verify priority selection
   - Verify fallback on failure

3. **No Display Scenario**
   - Disconnect all displays
   - Verify console fallback
   - Verify logging works

4. **Hot-swap Testing**
   - Disconnect active display
   - Verify fallback activation
   - Reconnect display
   - Verify recovery

5. **Configuration Override**
   - Set preferred display in config
   - Verify preference respected
   - Test invalid preferences

---

## 7. References and Resources

### 7.1 Display Detection Resources

**I2C Detection:**
- [How to Detect I2C Devices on Raspberry Pi](https://fleetstack.io/blog/detect-i2c-device-raspberry-pi)
- [Raspberry Pi SPI and I2C Tutorial - SparkFun](https://learn.sparkfun.com/tutorials/raspberry-pi-spi-and-i2c-tutorial/all)
- [Scanning I2C Addresses - Adafruit](https://learn.adafruit.com/scanning-i2c-addresses/raspberry-pi)

**SPI Detection:**
- [Raspberry Pi using SPI and I2C with Python](https://www.halvorsen.blog/documents/programming/python/resources/powerpoints/Raspberry%20Pi%20using%20SPI%20and%20I2C%20with%20Python.pdf)
- [Python code for detecting I2C ports - Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=114401)

**Framebuffer/HDMI:**
- [Framebuffer on Raspberry Pi](https://raspi.muth.org/framebuffer.html)
- [Writing GUI applications without X - Avik Das](https://medium.com/@avik.das/writing-gui-applications-on-the-raspberry-pi-without-a-desktop-environment-8f8f840d9867)
- [/dev/fb0 missing on Bullseye - RPi Forums](https://forums.raspberrypi.com/viewtopic.php?t=348483)
- [Display Priority on Raspberry Pi 5 - RPi Forums](https://forums.raspberrypi.com/viewtopic.php?t=373306)

**Pygame and Display Output:**
- [Pi Video Output Using pygame - Adafruit](https://learn.adafruit.com/pi-video-output-using-pygame?view=all)
- [Pygame 2 + Bookworm + SPI display - RPi Forums](https://forums.raspberrypi.com/viewtopic.php?t=358144)

**Console/Terminal Output:**
- [Asciimatics - PyPI](https://pypi.org/project/asciimatics/)
- [ASCII Art in Python - AskPython](https://www.askpython.com/python-modules/ascii-art)
- [Easily make terminal art - RPi Forums](https://forums.raspberrypi.com/viewtopic.php?t=366749)

### 7.2 Python Libraries

**Display Libraries:**
- `ST7789` - ST7789 SPI display driver
- `ST7735` - ST7735 SPI display driver
- `luma.oled` - OLED display drivers (SSD1306, SH1106, etc.)
- `luma.lcd` - LCD display drivers
- `pygame` - Graphics and game library with framebuffer support
- `Pillow` - Python Imaging Library

**Detection Libraries:**
- `spidev` - SPI device interface
- `smbus` / `smbus2` - I2C device interface
- `gpiozero` - GPIO device interface

**Console Libraries:**
- `rich` - Modern terminal formatting
- `asciimatics` - Full-screen text UIs
- `pyfiglet` - ASCII art text generation
- `colorama` - Cross-platform colored terminal output

### 7.3 System Tools

```bash
# I2C Detection
i2cdetect -y 1

# SPI Devices
ls -la /dev/spidev*

# Framebuffer Info
fbset -i
cat /sys/class/graphics/fb0/name

# Display Detection (KMS)
modetest -M vc4

# HDMI Status
vcgencmd display_power
tvservice -s
```

---

## 8. Risks and Mitigation

### 8.1 Identified Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Library incompatibility with new OS versions | High | Medium | Version pinning, abstraction layer |
| Display hardware not detected | High | Medium | Cascading fallbacks, console output |
| Performance degradation | Medium | Low | Caching, lazy initialization |
| Permission issues (framebuffer access) | High | Medium | Document requirements, sudo guidance |
| Breaking changes in pygame/SDL | Medium | Medium | Multiple driver support, fallbacks |

### 8.2 Rollback Plan

If display detection causes issues:
1. Maintain current ST7789/ST7735 logic as default
2. Make new detection system opt-in via config
3. Add `--legacy-display` command-line flag
4. Document how to disable auto-detection

---

## 9. Success Criteria

The display detection and fallback system will be considered successful when:

1. ✅ System automatically detects and uses ST7789/ST7735 displays (current functionality maintained)
2. ✅ System detects and uses I2C OLED displays (SSD1306, etc.)
3. ✅ System detects and uses HDMI/framebuffer output
4. ✅ System provides console output when no display available
5. ✅ Fallback chain works correctly on all Raspberry Pi models (Zero, 3, 4, 5)
6. ✅ Works correctly on Bullseye and Bookworm OS versions
7. ✅ Configuration file allows manual override
8. ✅ Display selection completes in < 5 seconds
9. ✅ System never fails silently (always provides some output)
10. ✅ Documentation allows users to troubleshoot display issues

---

## 10. Timeline and Milestones

### Week 1-2: Research and Design
- ✅ Research display detection methods (COMPLETED)
- ✅ Design abstraction layer (COMPLETED - This document)
- 🔄 Review and approve plan

### Week 3-4: Core Implementation
- Implement display detection
- Implement abstraction layer
- Basic SPI/I2C support

### Week 5-6: HDMI and Console
- HDMI/framebuffer support
- Console output implementation
- Configuration system

### Week 7-8: Testing and Documentation
- Hardware testing
- Documentation
- Bug fixes and refinement

**Target Completion:** 8 weeks from plan approval

---

## 11. Conclusion

This plan provides a comprehensive roadmap for implementing robust display detection and fallback capabilities in the FATN_to_USB system, specifically optimized for Raspberry Pi Zero and Zero 2 W hardware running Debian Trixie.

### Key Focus Areas

**Primary Hardware Target:**
- Raspberry Pi Zero, Zero W, and Zero 2 W
- Optimized for limited resources (512MB RAM, single/quad-core)
- Expected configuration: ST7789 or ST7735 SPI display attached

**Operating System Target:**
- Debian Trixie 13 (Slim/minimal installation assumed)
- Console-only environment as baseline
- GUI detection for optional desktop environments

**Detection Hierarchy:**
1. **Stage 1 (Priority):** ST7789/ST7735 SPI displays (expected hardware)
2. **Stage 2 (Fallback):** Raspberry Pi model identification
3. **Stage 3 (Adaptation):** GUI vs console-only environment detection
4. **Stage 4 (Graceful Degradation):** Framebuffer, console output, or logging

### Implementation Philosophy

The hardware-first approach prioritizes the known, expected configuration (SPI displays on Pi Zero) before attempting more complex detection. This ensures:

- **Fast startup** on correctly configured systems (< 2 seconds for known displays)
- **Minimal overhead** on resource-constrained Zero/Zero W hardware
- **Reliable fallback** when hardware doesn't match expectations
- **Clear diagnostics** to help users identify configuration issues

### Value Delivered

By implementing this plan, the FATN_to_USB system will:

1. ✅ **Maintain current functionality** for users with ST7789/ST7735 displays
2. ✅ **Support Debian Trixie** as the primary OS (console and GUI variants)
3. ✅ **Optimize for Pi Zero/Zero 2** performance characteristics
4. ✅ **Provide console output** on minimal installations without displays
5. ✅ **Enable debugging** through comprehensive detection logging
6. ✅ **Support future hardware** through the abstraction layer

The cascading fallback approach ensures reliability while the abstraction layer maintains clean, maintainable code. Progressive implementation allows for incremental delivery of value while minimizing risk to existing functionality.

---

**Document Version:** 1.1 (Updated for Pi Zero + Debian Trixie focus)
**Date:** 2025-12-18
**Status:** Draft - Pending Approval
**Target Hardware:** Raspberry Pi Zero, Zero W, Zero 2 W
**Target OS:** Debian Trixie 13 (Slim minimum)
**Author:** Claude Code Implementation Team
**Next Review:** Upon plan approval
