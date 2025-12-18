"""Display detection and abstraction layer for FATN to USB.

This module provides comprehensive display detection for:
- SPI displays (ST7789, ST7735)
- Raspberry Pi model identification (Zero, Zero W, Zero 2 W)
- GUI environment detection (X11, Wayland, console-only)
- Fallback to framebuffer or console output

Target Hardware: Raspberry Pi Zero, Zero W, Zero 2 W
Target OS: Debian Trixie (13) Slim (console-only minimum)
"""

import os
import subprocess
from typing import Dict, Optional, Tuple, Any

__version__ = '0.3.0'


# Raspberry Pi Zero revision codes
ZERO_REVISIONS = {
    '900092': 'Pi Zero 1.2',
    '900093': 'Pi Zero 1.3',
    '920093': 'Pi Zero 1.3',
    '9000c1': 'Pi Zero W 1.1',
    '902120': 'Pi Zero 2 W 1.0',
}


class DisplayInfo:
    """Information about detected display configuration."""

    def __init__(self):
        self.display_type = None  # 'ST7789', 'ST7735', 'framebuffer', 'console', None
        self.display_instance = None  # Actual display object if initialized
        self.pi_model = None  # Raspberry Pi model string
        self.is_zero = False  # True if Pi Zero family
        self.is_zero_2 = False  # True if Pi Zero 2 W
        self.hardware = None  # Hardware identifier from cpuinfo
        self.revision = None  # Revision code from cpuinfo
        self.gui_type = None  # 'X11', 'Wayland', 'console', None
        self.is_console_only = False  # True if no GUI available
        self.debian_version = None  # Debian version number
        self.has_framebuffer = False  # True if /dev/fb0 exists
        self.spi_devices = []  # List of detected SPI devices

    def __str__(self):
        """Human-readable display information."""
        lines = ['Display Configuration:']
        lines.append(f'  Display Type: {self.display_type or "None detected"}')
        lines.append(f'  Raspberry Pi: {self.pi_model or "Unknown"}')
        if self.is_zero:
            lines.append(f'  Zero Family: Yes (Zero 2: {self.is_zero_2})')
        lines.append(f'  GUI Type: {self.gui_type or "None"}')
        lines.append(f'  Console Only: {self.is_console_only}')
        lines.append(f'  Debian Version: {self.debian_version or "Unknown"}')
        lines.append(f'  Framebuffer: {"/dev/fb0" if self.has_framebuffer else "Not available"}')
        if self.spi_devices:
            lines.append(f'  SPI Devices: {", ".join(self.spi_devices)}')
        return '\n'.join(lines)


def detect_raspberry_pi_model() -> Dict[str, Any]:
    """Detect specific Raspberry Pi model from /proc/cpuinfo.

    Returns:
        Dictionary with model information:
        - model: Human-readable model name
        - is_zero: True if Pi Zero family
        - is_zero_2: True if Pi Zero 2 W
        - hardware: Hardware identifier
        - revision: Revision code
    """
    model_info = {
        'model': 'unknown',
        'is_zero': False,
        'is_zero_2': False,
        'hardware': None,
        'revision': None,
    }

    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()

        # Extract Hardware line
        for line in cpuinfo.split('\n'):
            if line.startswith('Hardware'):
                model_info['hardware'] = line.split(':')[1].strip()
            elif line.startswith('Revision'):
                model_info['revision'] = line.split(':')[1].strip()

        # Identify Zero models by revision code
        revision = model_info['revision']
        if revision in ZERO_REVISIONS:
            model_info['model'] = ZERO_REVISIONS[revision]
            model_info['is_zero'] = True

            # Pi Zero 2 W has revision 902120
            if revision == '902120':
                model_info['is_zero_2'] = True

        # Additional detection by hardware identifier
        hardware = model_info['hardware']
        if hardware:
            if 'BCM2835' in hardware and not model_info['is_zero']:
                # BCM2835 used in Pi Zero (ARMv6)
                model_info['is_zero'] = True
                model_info['model'] = 'Pi Zero (BCM2835)'
            elif 'BCM2710A1' in hardware:
                # BCM2710A1 used in Pi Zero 2 W (ARMv8)
                model_info['is_zero'] = True
                model_info['is_zero_2'] = True
                if model_info['model'] == 'unknown':
                    model_info['model'] = 'Pi Zero 2 W (BCM2710A1)'

    except FileNotFoundError:
        # Not running on Raspberry Pi
        model_info['model'] = 'Not a Raspberry Pi'
    except Exception as e:
        print(f'Warning: Error detecting Pi model: {e}')

    return model_info


def detect_debian_version() -> Optional[str]:
    """Detect Debian version number.

    Returns:
        Version string (e.g., '13' for Trixie) or None
    """
    try:
        with open('/etc/debian_version', 'r') as f:
            version = f.read().strip()
            # Extract major version number
            if '/' in version:
                # Handle versions like "trixie/sid"
                return version.split('/')[0]
            else:
                # Handle numeric versions like "13.0"
                return version.split('.')[0]
    except FileNotFoundError:
        return None
    except Exception as e:
        print(f'Warning: Error detecting Debian version: {e}')
        return None


def detect_x11() -> bool:
    """Check if X11 display server is running.

    Returns:
        True if X11 is available and responding
    """
    display = os.environ.get('DISPLAY')
    if not display:
        return False

    # Check if X server is actually responding
    try:
        result = subprocess.run(
            ['xdpyinfo'],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # xdpyinfo not installed or not responding
        return False


def detect_wayland() -> bool:
    """Check if Wayland compositor is running.

    Returns:
        True if Wayland is available
    """
    wayland_display = os.environ.get('WAYLAND_DISPLAY')
    xdg_session_type = os.environ.get('XDG_SESSION_TYPE')

    return bool(wayland_display) or xdg_session_type == 'wayland'


def is_console_only() -> bool:
    """Determine if running in console-only (no GUI) mode.

    Returns:
        True if running in console-only mode
    """
    # Check for Linux console TERM
    term = os.environ.get('TERM', '')
    if term.startswith('linux'):
        return True

    # Check if no display variables set
    if not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'):
        # Might be console-only or SSH session
        # Check if we're in an SSH session
        if os.environ.get('SSH_CLIENT') or os.environ.get('SSH_TTY'):
            return True

        # Check systemd target (if available)
        try:
            result = subprocess.run(
                ['systemctl', 'get-default'],
                capture_output=True,
                timeout=5,
                text=True
            )
            if result.returncode == 0:
                target = result.stdout.strip()
                return target == 'multi-user.target'
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    return False


def detect_gui_type() -> Optional[str]:
    """Detect GUI environment type.

    Returns:
        'X11', 'Wayland', 'console', or None
    """
    if detect_x11():
        return 'X11'
    elif detect_wayland():
        return 'Wayland'
    elif is_console_only():
        return 'console'
    else:
        return None


def detect_spi_devices() -> list:
    """Detect available SPI devices.

    Returns:
        List of SPI device paths (e.g., ['/dev/spidev0.0', '/dev/spidev0.1'])
    """
    devices = []
    spi_base = '/dev'

    try:
        for entry in os.listdir(spi_base):
            if entry.startswith('spidev'):
                devices.append(os.path.join(spi_base, entry))
    except Exception as e:
        print(f'Warning: Error detecting SPI devices: {e}')

    return sorted(devices)


def detect_framebuffer() -> bool:
    """Check if framebuffer device is available.

    Returns:
        True if /dev/fb0 exists
    """
    return os.path.exists('/dev/fb0')


def try_init_st7789() -> Optional[Any]:
    """Attempt to initialize ST7789 display.

    Returns:
        Display instance if successful, None otherwise
    """
    try:
        import ST7789 as ST7789
        disp = ST7789.ST7789(
            port=0,
            cs=ST7789.BG_SPI_CS_FRONT,
            dc=9,
            backlight=19,
            spi_speed_hz=80 * 1000 * 1000
        )
        print('✓ ST7789 display initialized successfully')
        return disp
    except (ImportError, OSError, RuntimeError) as e:
        print(f'ST7789 not available: {repr(e)}')
        return None


def try_init_st7735() -> Optional[Any]:
    """Attempt to initialize ST7735 display.

    Returns:
        Display instance if successful, None otherwise
    """
    try:
        import ST7735 as ST7735
        disp = ST7735.ST7735(
            port=0,
            cs=1,
            dc=9,
            backlight=12,
            rotation=270,
            spi_speed_hz=10000000
        )
        print('✓ ST7735 display initialized successfully')
        return disp
    except (ImportError, OSError, RuntimeError) as e:
        print(f'ST7735 not available: {repr(e)}')
        return None


def detect_and_init_display() -> DisplayInfo:
    """Comprehensive display detection and initialization.

    Detection priority (as per requirements):
    1. Try ST7789 (expected primary display)
    2. Try ST7735 (expected secondary display)
    3. Detect Raspberry Pi model (Zero vs Zero 2)
    4. Detect GUI availability (X11/Wayland vs console-only)
    5. Check for framebuffer fallback

    Returns:
        DisplayInfo object with all detection results
    """
    info = DisplayInfo()

    print('=' * 60)
    print('FATN to USB - Display Detection')
    print('=' * 60)

    # Stage 1: Try SPI displays (expected configuration)
    print('\n[Stage 1] Checking for SPI displays...')
    info.spi_devices = detect_spi_devices()
    if info.spi_devices:
        print(f'Found SPI devices: {", ".join(info.spi_devices)}')
    else:
        print('No SPI devices detected')

    # Try ST7789 first
    disp = try_init_st7789()
    if disp:
        info.display_type = 'ST7789'
        info.display_instance = disp
    else:
        # Try ST7735 as fallback
        disp = try_init_st7735()
        if disp:
            info.display_type = 'ST7735'
            info.display_instance = disp

    # Stage 2: Detect Raspberry Pi model
    print('\n[Stage 2] Detecting Raspberry Pi model...')
    pi_info = detect_raspberry_pi_model()
    info.pi_model = pi_info['model']
    info.is_zero = pi_info['is_zero']
    info.is_zero_2 = pi_info['is_zero_2']
    info.hardware = pi_info['hardware']
    info.revision = pi_info['revision']

    print(f'Model: {info.pi_model}')
    if info.is_zero:
        print(f'  Zero Family: Yes')
        print(f'  Zero 2: {info.is_zero_2}')
        print(f'  Hardware: {info.hardware}')
        print(f'  Revision: {info.revision}')

    # Stage 3: Detect GUI environment
    print('\n[Stage 3] Detecting GUI environment...')
    info.debian_version = detect_debian_version()
    info.gui_type = detect_gui_type()
    info.is_console_only = is_console_only()

    print(f'Debian Version: {info.debian_version or "Unknown"}')
    print(f'GUI Type: {info.gui_type or "None"}')
    print(f'Console Only: {info.is_console_only}')

    # Stage 4: Check framebuffer fallback
    print('\n[Stage 4] Checking fallback options...')
    info.has_framebuffer = detect_framebuffer()
    print(f'Framebuffer (/dev/fb0): {"Available" if info.has_framebuffer else "Not available"}')

    # Determine final output method
    print('\n' + '=' * 60)
    if info.display_type:
        print(f'✓ Display Initialized: {info.display_type}')
    elif info.has_framebuffer:
        print('⚠ No SPI display - framebuffer available')
        info.display_type = 'framebuffer'
    elif info.is_console_only:
        print('⚠ No display hardware - console-only mode')
        info.display_type = 'console'
    else:
        print('❌ No display options available - logging only')
        info.display_type = None

    print('=' * 60)

    return info


# Global display info instance
_display_info = None


def get_display_info() -> DisplayInfo:
    """Get cached display information (singleton pattern).

    Returns:
        DisplayInfo object (runs detection on first call)
    """
    global _display_info
    if _display_info is None:
        _display_info = detect_and_init_display()
    return _display_info


if __name__ == '__main__':
    """Run display detection when executed directly."""
    info = detect_and_init_display()
    print('\n' + str(info))
