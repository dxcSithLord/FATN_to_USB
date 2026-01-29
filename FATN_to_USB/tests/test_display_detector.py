"""Tests for display_detector module.

This module tests:
- Raspberry Pi model detection
- GUI environment detection (X11, Wayland, console)
- SPI device detection
- Display initialization and fallback logic
- Display abstraction layer
"""

import os
import sys
import subprocess
from unittest.mock import patch, MagicMock, mock_open

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'fatn_to_usb'))

from display_detector import (
    detect_raspberry_pi_model,
    detect_debian_version,
    detect_x11,
    detect_wayland,
    is_console_only,
    detect_gui_type,
    detect_spi_devices,
    detect_framebuffer,
    try_init_st7789,
    try_init_st7735,
    detect_and_init_display,
    DisplayInfo,
    ZERO_REVISIONS,
)


class TestDisplayInfo:
    """Tests for DisplayInfo class."""

    def test_display_info_initialization(self):
        """Test DisplayInfo initializes with correct defaults."""
        info = DisplayInfo()

        assert info.display_type is None
        assert info.display_instance is None
        assert info.pi_model is None
        assert info.is_zero is False
        assert info.is_zero_2 is False
        assert info.hardware is None
        assert info.revision is None
        assert info.gui_type is None
        assert info.is_console_only is False
        assert info.debian_version is None
        assert info.has_framebuffer is False
        assert info.spi_devices == []

    def test_display_info_str(self):
        """Test DisplayInfo string representation."""
        info = DisplayInfo()
        info.display_type = 'ST7789'
        info.pi_model = 'Pi Zero 2 W'
        info.is_zero = True
        info.is_zero_2 = True
        info.gui_type = 'console'
        info.is_console_only = True
        info.debian_version = '13'
        info.has_framebuffer = True
        info.spi_devices = ['/dev/spidev0.0']

        str_repr = str(info)

        assert 'Display Configuration:' in str_repr
        assert 'Display Type: ST7789' in str_repr
        assert 'Raspberry Pi: Pi Zero 2 W' in str_repr
        assert 'Zero Family: Yes' in str_repr
        assert 'GUI Type: console' in str_repr
        assert 'Console Only: True' in str_repr
        assert 'Debian Version: 13' in str_repr
        assert 'Framebuffer: /dev/fb0' in str_repr
        assert '/dev/spidev0.0' in str_repr


class TestRaspberryPiDetection:
    """Tests for Raspberry Pi model detection."""

    def test_detect_pi_zero_1_2(self):
        """Test detection of Pi Zero 1.2."""
        cpuinfo_content = """processor : 0
model name : ARMv6-compatible processor rev 7 (v6l)
Hardware : BCM2835
Revision : 900092
"""
        with patch('builtins.open', mock_open(read_data=cpuinfo_content)):
            result = detect_raspberry_pi_model()

        assert result['model'] == 'Pi Zero 1.2'
        assert result['is_zero'] is True
        assert result['is_zero_2'] is False
        assert result['hardware'] == 'BCM2835'
        assert result['revision'] == '900092'

    def test_detect_pi_zero_2_w(self):
        """Test detection of Pi Zero 2 W."""
        cpuinfo_content = """processor : 0
model name : ARMv7 Processor rev 3 (v7l)
Hardware : BCM2710A1
Revision : 902120
"""
        with patch('builtins.open', mock_open(read_data=cpuinfo_content)):
            result = detect_raspberry_pi_model()

        assert result['model'] == 'Pi Zero 2 W 1.0'
        assert result['is_zero'] is True
        assert result['is_zero_2'] is True
        assert result['hardware'] == 'BCM2710A1'
        assert result['revision'] == '902120'

    def test_detect_pi_zero_w(self):
        """Test detection of Pi Zero W."""
        cpuinfo_content = """processor : 0
model name : ARMv6-compatible processor rev 7 (v6l)
Hardware : BCM2835
Revision : 9000c1
"""
        with patch('builtins.open', mock_open(read_data=cpuinfo_content)):
            result = detect_raspberry_pi_model()

        assert result['model'] == 'Pi Zero W 1.1'
        assert result['is_zero'] is True
        assert result['is_zero_2'] is False
        assert result['revision'] == '9000c1'

    def test_detect_non_raspberry_pi(self):
        """Test detection on non-Raspberry Pi system."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            result = detect_raspberry_pi_model()

        assert result['model'] == 'Not a Raspberry Pi'
        assert result['is_zero'] is False
        assert result['is_zero_2'] is False

    def test_detect_unknown_revision(self):
        """Test detection with unknown revision code."""
        cpuinfo_content = """processor : 0
Hardware : BCM2711
Revision : c03111
"""
        with patch('builtins.open', mock_open(read_data=cpuinfo_content)):
            result = detect_raspberry_pi_model()

        assert result['model'] == 'unknown'
        assert result['hardware'] == 'BCM2711'
        assert result['revision'] == 'c03111'


class TestDebianVersion:
    """Tests for Debian version detection."""

    def test_detect_debian_trixie(self):
        """Test detection of Debian Trixie (13)."""
        with patch('builtins.open', mock_open(read_data='13.0')):
            version = detect_debian_version()

        assert version == '13'

    def test_detect_debian_bookworm(self):
        """Test detection of Debian Bookworm (12)."""
        with patch('builtins.open', mock_open(read_data='12.5')):
            version = detect_debian_version()

        assert version == '12'

    def test_detect_debian_sid(self):
        """Test detection of Debian Sid (testing)."""
        with patch('builtins.open', mock_open(read_data='trixie/sid')):
            version = detect_debian_version()

        assert version == 'trixie'

    def test_detect_non_debian(self):
        """Test detection on non-Debian system."""
        with patch('builtins.open', side_effect=FileNotFoundError):
            version = detect_debian_version()

        assert version is None


class TestGUIDetection:
    """Tests for GUI environment detection."""

    def test_detect_x11_available(self):
        """Test X11 detection when available."""
        with patch.dict(os.environ, {'DISPLAY': ':0'}):
            with patch('shutil.which', return_value='/usr/bin/xdpyinfo'):
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = MagicMock(returncode=0)
                    result = detect_x11()

        assert result is True

    def test_detect_x11_no_display(self):
        """Test X11 detection with no DISPLAY variable."""
        with patch.dict(os.environ, {}, clear=True):
            result = detect_x11()

        assert result is False

    def test_detect_x11_not_responding(self):
        """Test X11 detection when server not responding."""
        with patch.dict(os.environ, {'DISPLAY': ':0'}):
            with patch('shutil.which', return_value='/usr/bin/xdpyinfo'):
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = MagicMock(returncode=1)
                    result = detect_x11()

        assert result is False

    def test_detect_x11_timeout(self):
        """Test X11 detection with timeout."""
        with patch.dict(os.environ, {'DISPLAY': ':0'}):
            with patch('shutil.which', return_value='/usr/bin/xdpyinfo'):
                with patch('subprocess.run', side_effect=subprocess.TimeoutExpired('xdpyinfo', 5)):
                    result = detect_x11()

        assert result is False

    def test_detect_wayland_available(self):
        """Test Wayland detection when available."""
        with patch.dict(os.environ, {'WAYLAND_DISPLAY': 'wayland-0'}):
            result = detect_wayland()

        assert result is True

    def test_detect_wayland_xdg_session(self):
        """Test Wayland detection via XDG_SESSION_TYPE."""
        with patch.dict(os.environ, {'XDG_SESSION_TYPE': 'wayland'}):
            result = detect_wayland()

        assert result is True

    def test_detect_wayland_not_available(self):
        """Test Wayland detection when not available."""
        with patch.dict(os.environ, {}, clear=True):
            result = detect_wayland()

        assert result is False

    def test_is_console_only_linux_term(self):
        """Test console-only detection with Linux terminal."""
        with patch.dict(os.environ, {'TERM': 'linux'}, clear=True):
            result = is_console_only()

        assert result is True

    def test_is_console_only_no_display_no_ssh(self):
        """Test console-only detection without display or SSH."""
        with patch.dict(os.environ, {}, clear=True):
            with patch('shutil.which', return_value='/usr/bin/systemctl'):
                with patch('subprocess.run') as mock_run:
                    mock_run.return_value = MagicMock(
                        returncode=0,
                        stdout='multi-user.target\n'
                    )
                    result = is_console_only()

        assert result is True

    def test_is_console_only_ssh_session(self):
        """Test console-only detection in SSH session."""
        with patch.dict(os.environ, {'SSH_CLIENT': '192.168.1.1'}, clear=True):
            result = is_console_only()

        assert result is True

    def test_is_console_only_with_display(self):
        """Test console-only detection with display available."""
        with patch.dict(os.environ, {'DISPLAY': ':0', 'TERM': 'xterm'}):
            result = is_console_only()

        assert result is False

    def test_detect_gui_type_x11(self):
        """Test GUI type detection for X11."""
        with patch('display_detector.detect_x11', return_value=True):
            result = detect_gui_type()

        assert result == 'X11'

    def test_detect_gui_type_wayland(self):
        """Test GUI type detection for Wayland."""
        with patch('display_detector.detect_x11', return_value=False):
            with patch('display_detector.detect_wayland', return_value=True):
                result = detect_gui_type()

        assert result == 'Wayland'

    def test_detect_gui_type_console(self):
        """Test GUI type detection for console."""
        with patch('display_detector.detect_x11', return_value=False):
            with patch('display_detector.detect_wayland', return_value=False):
                with patch('display_detector.is_console_only', return_value=True):
                    result = detect_gui_type()

        assert result == 'console'

    def test_detect_gui_type_none(self):
        """Test GUI type detection when none available."""
        with patch('display_detector.detect_x11', return_value=False):
            with patch('display_detector.detect_wayland', return_value=False):
                with patch('display_detector.is_console_only', return_value=False):
                    result = detect_gui_type()

        assert result is None


class TestSPIDevices:
    """Tests for SPI device detection."""

    def test_detect_spi_devices_found(self):
        """Test SPI device detection when devices exist."""
        with patch('os.listdir', return_value=['spidev0.0', 'spidev0.1', 'other']):
            devices = detect_spi_devices()

        assert '/dev/spidev0.0' in devices
        assert '/dev/spidev0.1' in devices
        assert len(devices) == 2

    def test_detect_spi_devices_none(self):
        """Test SPI device detection when no devices exist."""
        with patch('os.listdir', return_value=['tty0', 'null', 'random']):
            devices = detect_spi_devices()

        assert devices == []

    def test_detect_spi_devices_error(self):
        """Test SPI device detection with error."""
        with patch('os.listdir', side_effect=PermissionError):
            devices = detect_spi_devices()

        assert devices == []


class TestFramebuffer:
    """Tests for framebuffer detection."""

    def test_detect_framebuffer_available(self):
        """Test framebuffer detection when available."""
        with patch('os.path.exists', return_value=True):
            result = detect_framebuffer()

        assert result is True

    def test_detect_framebuffer_not_available(self):
        """Test framebuffer detection when not available."""
        with patch('os.path.exists', return_value=False):
            result = detect_framebuffer()

        assert result is False


class TestDisplayInitialization:
    """Tests for display initialization."""

    def test_try_init_st7789_success(self):
        """Test ST7789 initialization success."""
        with patch.dict(sys.modules, {'ST7789': MagicMock()}):
            disp = try_init_st7789()

        assert disp is not None

    def test_try_init_st7789_import_error(self):
        """Test ST7789 initialization with import error."""
        with patch.dict(sys.modules, {'ST7789': None}):
            with patch('builtins.__import__', side_effect=ImportError):
                disp = try_init_st7789()

        assert disp is None

    def test_try_init_st7789_runtime_error(self):
        """Test ST7789 initialization with runtime error."""
        mock_module = MagicMock()
        mock_module.ST7789.side_effect = RuntimeError('SPI not available')

        with patch.dict(sys.modules, {'ST7789': mock_module}):
            disp = try_init_st7789()

        assert disp is None

    def test_try_init_st7735_success(self):
        """Test ST7735 initialization success."""
        with patch.dict(sys.modules, {'ST7735': MagicMock()}):
            disp = try_init_st7735()

        assert disp is not None

    def test_try_init_st7735_import_error(self):
        """Test ST7735 initialization with import error."""
        with patch.dict(sys.modules, {'ST7735': None}):
            with patch('builtins.__import__', side_effect=ImportError):
                disp = try_init_st7735()

        assert disp is None


class TestDetectAndInitDisplay:
    """Tests for complete display detection workflow."""

    def test_detect_and_init_display_st7789(self, mock_st7789_display):
        """Test complete detection with ST7789 available."""
        cpuinfo_content = """Hardware : BCM2710A1
Revision : 902120
"""
        with patch('builtins.open', mock_open(read_data=cpuinfo_content)):
            with patch('display_detector.detect_spi_devices', return_value=['/dev/spidev0.0']):
                with patch('display_detector.try_init_st7789', return_value=mock_st7789_display):
                    with patch('display_detector.detect_debian_version', return_value='13'):
                        with patch('display_detector.detect_gui_type', return_value='console'):
                            with patch('display_detector.is_console_only', return_value=True):
                                with patch('display_detector.detect_framebuffer', return_value=False):
                                    info = detect_and_init_display()

        assert info.display_type == 'ST7789'
        assert info.display_instance == mock_st7789_display
        assert info.pi_model == 'Pi Zero 2 W 1.0'
        assert info.is_zero is True
        assert info.is_zero_2 is True
        assert info.debian_version == '13'
        assert info.gui_type == 'console'
        assert info.is_console_only is True

    def test_detect_and_init_display_st7735_fallback(self, mock_st7735_display):
        """Test complete detection with ST7735 fallback."""
        with patch('display_detector.detect_spi_devices', return_value=['/dev/spidev0.0']):
            with patch('display_detector.try_init_st7789', return_value=None):
                with patch('display_detector.try_init_st7735', return_value=mock_st7735_display):
                    with patch('display_detector.detect_raspberry_pi_model', return_value={
                        'model': 'Pi Zero W', 'is_zero': True, 'is_zero_2': False,
                        'hardware': 'BCM2835', 'revision': '9000c1'
                    }):
                        with patch('display_detector.detect_debian_version', return_value='13'):
                            with patch('display_detector.detect_gui_type', return_value='console'):
                                with patch('display_detector.is_console_only', return_value=True):
                                    with patch('display_detector.detect_framebuffer', return_value=False):
                                        info = detect_and_init_display()

        assert info.display_type == 'ST7735'
        assert info.display_instance == mock_st7735_display

    def test_detect_and_init_display_framebuffer_fallback(self):
        """Test complete detection with framebuffer fallback."""
        with patch('display_detector.detect_spi_devices', return_value=[]):
            with patch('display_detector.try_init_st7789', return_value=None):
                with patch('display_detector.try_init_st7735', return_value=None):
                    with patch('display_detector.detect_raspberry_pi_model', return_value={
                        'model': 'Pi Zero', 'is_zero': True, 'is_zero_2': False,
                        'hardware': 'BCM2835', 'revision': '900092'
                    }):
                        with patch('display_detector.detect_debian_version', return_value='13'):
                            with patch('display_detector.detect_gui_type', return_value='console'):
                                with patch('display_detector.is_console_only', return_value=True):
                                    with patch('display_detector.detect_framebuffer', return_value=True):
                                        info = detect_and_init_display()

        assert info.display_type == 'framebuffer'
        assert info.display_instance is None
        assert info.has_framebuffer is True

    def test_detect_and_init_display_console_only(self):
        """Test complete detection with console-only fallback."""
        with patch('display_detector.detect_spi_devices', return_value=[]):
            with patch('display_detector.try_init_st7789', return_value=None):
                with patch('display_detector.try_init_st7735', return_value=None):
                    with patch('display_detector.detect_raspberry_pi_model', return_value={
                        'model': 'Pi Zero', 'is_zero': True, 'is_zero_2': False,
                        'hardware': 'BCM2835', 'revision': '900092'
                    }):
                        with patch('display_detector.detect_debian_version', return_value='13'):
                            with patch('display_detector.detect_gui_type', return_value='console'):
                                with patch('display_detector.is_console_only', return_value=True):
                                    with patch('display_detector.detect_framebuffer', return_value=False):
                                        info = detect_and_init_display()

        assert info.display_type == 'console'
        assert info.display_instance is None
        assert info.has_framebuffer is False
        assert info.is_console_only is True

    def test_detect_and_init_display_no_options(self):
        """Test complete detection with no display options."""
        with patch('display_detector.detect_spi_devices', return_value=[]):
            with patch('display_detector.try_init_st7789', return_value=None):
                with patch('display_detector.try_init_st7735', return_value=None):
                    with patch('display_detector.detect_raspberry_pi_model', return_value={
                        'model': 'Not a Raspberry Pi', 'is_zero': False, 'is_zero_2': False,
                        'hardware': None, 'revision': None
                    }):
                        with patch('display_detector.detect_debian_version', return_value=None):
                            with patch('display_detector.detect_gui_type', return_value=None):
                                with patch('display_detector.is_console_only', return_value=False):
                                    with patch('display_detector.detect_framebuffer', return_value=False):
                                        info = detect_and_init_display()

        assert info.display_type is None
        assert info.display_instance is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
