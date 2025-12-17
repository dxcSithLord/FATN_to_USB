"""
Unit tests for copy-Fatn USB management module.

Tests USB detection, mounting, file operations, and safe unmounting.
"""
import pytest
import os
import subprocess
import tempfile
from unittest.mock import Mock, patch, call, MagicMock
import importlib.util


# Helper to import copy-Fatn module (has dash in filename)
def import_copy_fatn():
    """Import the copy-Fatn module."""
    module_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        'fatn_to_usb',
        'copy-Fatn'
    )
    spec = importlib.util.spec_from_file_location("copy_fatn", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def copy_fatn():
    """Fixture to import copy-Fatn module."""
    return import_copy_fatn()


# ============================================================================
# CPU Info Tests
# ============================================================================

class TestCPUInfo:
    """Tests for CPU information detection."""

    @pytest.mark.unit
    def test_proc_cpuinfo_exists(self, copy_fatn):
        """Test detection of /proc/cpuinfo file."""
        # On Linux systems, /proc/cpuinfo should exist
        # This test may fail on non-Linux systems
        result = copy_fatn.proc_cpuinfo_exists()
        assert isinstance(result, bool)

    @pytest.mark.unit
    @patch('os.path.exists')
    def test_proc_cpuinfo_exists_mocked(self, mock_exists, copy_fatn):
        """Test proc_cpuinfo_exists with mocked file system."""
        mock_exists.return_value = True
        assert copy_fatn.proc_cpuinfo_exists() is True

        mock_exists.return_value = False
        assert copy_fatn.proc_cpuinfo_exists() is False

    @pytest.mark.unit
    def test_get_cpuinfo_returns_dict(self, copy_fatn, raspberry_pi_cpuinfo):
        """Test that get_cpuinfo returns a dictionary."""
        with patch('builtins.open', create=True) as mock_open_file:
            mock_open_file.return_value.__enter__.return_value = open(raspberry_pi_cpuinfo)

            with patch('os.path.exists', return_value=True):
                result = copy_fatn.get_cpuinfo()

            assert isinstance(result, dict)
            assert len(result) > 0

    @pytest.mark.unit
    def test_get_cpuinfo_raspberry_pi(self, copy_fatn, raspberry_pi_cpuinfo):
        """Test parsing Raspberry Pi cpuinfo."""
        with patch('builtins.open', create=True) as mock_open_file:
            mock_open_file.return_value.__enter__.return_value = open(raspberry_pi_cpuinfo)

            with patch('os.path.exists', return_value=True):
                result = copy_fatn.get_cpuinfo()

            assert 'Hardware' in result
            assert 'BCM' in result.get('Hardware', '')
            assert 'Model' in result

    @pytest.mark.unit
    def test_get_cpuinfo_generic_linux(self, copy_fatn, generic_linux_cpuinfo):
        """Test parsing generic Linux cpuinfo."""
        with patch('builtins.open', create=True) as mock_open_file:
            mock_open_file.return_value.__enter__.return_value = open(generic_linux_cpuinfo)

            with patch('os.path.exists', return_value=True):
                result = copy_fatn.get_cpuinfo()

            assert isinstance(result, dict)
            assert 'vendor_id' in result or 'model name' in result

    @pytest.mark.unit
    def test_is_raspberry_pi_detection(self, copy_fatn):
        """Test Raspberry Pi detection logic."""
        with patch.object(copy_fatn, 'get_cpuinfo') as mock_cpuinfo:
            # Test with Raspberry Pi hardware
            mock_cpuinfo.return_value = {
                'Hardware': 'BCM2835',
                'Model': 'Raspberry Pi Zero W Rev 1.1'
            }
            assert copy_fatn.is_raspberry_pi() is True

            # Test with non-Raspberry Pi hardware
            mock_cpuinfo.return_value = {
                'vendor_id': 'GenuineIntel',
                'model name': 'Intel Core i7'
            }
            assert copy_fatn.is_raspberry_pi() is False

            # Test with Raspberry Pi in model name
            mock_cpuinfo.return_value = {
                'Model': 'Raspberry Pi 4 Model B'
            }
            assert copy_fatn.is_raspberry_pi() is True


# ============================================================================
# USB Device Detection Tests
# ============================================================================

class TestUSBDeviceDetection:
    """Tests for USB device detection."""

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_get_usb_devices_success(self, mock_run, copy_fatn):
        """Test successful USB device detection."""
        mock_result = Mock()
        mock_result.stdout = '''
MODEL                     REVISION  SERIAL               DEVICE
JetFlash Transcend 8GB    1100      AA0000000001F6EC     /dev/sda1
'''
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with patch.object(copy_fatn, 'is_raspberry_pi', return_value=False):
            devices = copy_fatn.get_usb_devices()

        assert isinstance(devices, list)
        assert '/dev/sda1' in devices

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_get_usb_devices_filters_mmcblk_on_rpi(self, mock_run, copy_fatn):
        """Test that mmcblk devices are filtered on Raspberry Pi."""
        mock_result = Mock()
        mock_result.stdout = '''
/dev/mmcblk0
/dev/sda1
/dev/mmcblk0p1
/dev/sdb1
'''
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with patch.object(copy_fatn, 'is_raspberry_pi', return_value=True):
            devices = copy_fatn.get_usb_devices()

        # Should not contain mmcblk devices
        assert not any('mmcblk' in dev for dev in devices)
        # Should contain USB devices
        assert '/dev/sda1' in devices or '/dev/sdb1' in devices

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_get_usb_devices_empty_list(self, mock_run, copy_fatn):
        """Test when no USB devices are found."""
        mock_result = Mock()
        mock_result.stdout = 'No devices found'
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        with patch.object(copy_fatn, 'is_raspberry_pi', return_value=False):
            devices = copy_fatn.get_usb_devices()

        assert devices == []

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_get_usb_devices_subprocess_error(self, mock_run, copy_fatn, capsys):
        """Test handling of subprocess errors."""
        mock_run.side_effect = subprocess.CalledProcessError(1, 'udisksctl')

        devices = copy_fatn.get_usb_devices()

        assert devices == []
        captured = capsys.readouterr()
        assert 'Error running udisksctl' in captured.out

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_get_usb_devices_udisksctl_not_found(self, mock_run, copy_fatn, capsys):
        """Test when udisksctl is not installed."""
        mock_run.side_effect = FileNotFoundError()

        devices = copy_fatn.get_usb_devices()

        assert devices == []
        captured = capsys.readouterr()
        assert 'udisksctl not found' in captured.out


# ============================================================================
# USB Mounting Tests
# ============================================================================

class TestUSBMounting:
    """Tests for USB device mounting."""

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_mount_usb_device_success(self, mock_run, copy_fatn, capsys):
        """Test successful USB mounting."""
        mock_result = Mock()
        mock_result.stdout = 'Mounted /dev/sda1 at /media/user/USB'
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        mount_point = copy_fatn.mount_usb_device('/dev/sda1')

        assert mount_point == '/media/user/USB'
        captured = capsys.readouterr()
        assert 'Successfully mounted' in captured.out

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_mount_usb_device_no_mount_point_in_output(self, mock_run, copy_fatn, capsys):
        """Test when mount succeeds but can't determine mount point."""
        mock_result = Mock()
        mock_result.stdout = 'Mounted /dev/sda1'  # No 'at' keyword
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        mount_point = copy_fatn.mount_usb_device('/dev/sda1')

        assert mount_point is None
        captured = capsys.readouterr()
        assert 'could not determine mount point' in captured.out

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_mount_usb_device_failure(self, mock_run, copy_fatn, capsys):
        """Test failed USB mounting."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, 'udisksctl', stderr='Device not found'
        )

        mount_point = copy_fatn.mount_usb_device('/dev/sda1')

        assert mount_point is None
        captured = capsys.readouterr()
        assert 'Error mounting' in captured.out


# ============================================================================
# USB Unmounting Tests
# ============================================================================

class TestUSBUnmounting:
    """Tests for USB device unmounting."""

    @pytest.mark.unit
    @patch('subprocess.run')
    @patch('time.sleep')
    def test_unmount_usb_device_success(self, mock_sleep, mock_run, copy_fatn, capsys):
        """Test successful USB unmounting."""
        mock_result = Mock()
        mock_result.stdout = 'Unmounted /dev/sda1'
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        result = copy_fatn.unmount_usb_device('/dev/sda1')

        assert result is True
        # Verify sync was called twice
        assert mock_run.call_count >= 3  # 2 syncs + 1 unmount
        captured = capsys.readouterr()
        assert 'Successfully unmounted' in captured.out

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_unmount_usb_device_failure(self, mock_run, copy_fatn, capsys):
        """Test failed USB unmounting."""
        # Sync succeeds
        mock_run.side_effect = [
            Mock(returncode=0),  # First sync
            Mock(returncode=0),  # Second sync
            subprocess.CalledProcessError(1, 'udisksctl', stderr='Not mounted')
        ]

        result = copy_fatn.unmount_usb_device('/dev/sda1')

        assert result is False
        captured = capsys.readouterr()
        assert 'Error unmounting' in captured.out


# ============================================================================
# File Operations Tests
# ============================================================================

class TestFileOperations:
    """Tests for file operations on USB."""

    @pytest.mark.unit
    def test_remove_old_mp3_files(self, copy_fatn, usb_mount_point):
        """Test removal of old MP3 files."""
        count = copy_fatn.remove_old_mp3_files(usb_mount_point)

        assert count == 3  # Three old MP3 files created in fixture
        # Verify files were removed
        mp3_files = [f for f in os.listdir(usb_mount_point) if f.endswith('.mp3')]
        assert len(mp3_files) == 0

    @pytest.mark.unit
    def test_remove_old_mp3_files_invalid_mount_point(self, copy_fatn, capsys):
        """Test removing MP3 files from invalid mount point."""
        count = copy_fatn.remove_old_mp3_files('/invalid/path')

        assert count == 0
        captured = capsys.readouterr()
        assert 'Invalid mount point' in captured.out

    @pytest.mark.unit
    def test_remove_old_mp3_files_none_mount_point(self, copy_fatn, capsys):
        """Test with None as mount point."""
        count = copy_fatn.remove_old_mp3_files(None)

        assert count == 0
        captured = capsys.readouterr()
        assert 'Invalid mount point' in captured.out

    @pytest.mark.unit
    def test_extract_zip_to_usb_success(self, copy_fatn, sample_zip_file, usb_mount_point, capsys):
        """Test successful ZIP extraction to USB."""
        result = copy_fatn.extract_zip_to_usb(sample_zip_file, usb_mount_point)

        assert result is True

        # Verify files were extracted
        extracted_files = os.listdir(usb_mount_point)
        assert 'news_1.mp3' in extracted_files
        assert 'news_2.mp3' in extracted_files
        assert 'news_3.mp3' in extracted_files

        captured = capsys.readouterr()
        assert 'Extracted 3 files' in captured.out

    @pytest.mark.unit
    def test_extract_zip_to_usb_file_not_found(self, copy_fatn, usb_mount_point, capsys):
        """Test extraction when ZIP file doesn't exist."""
        result = copy_fatn.extract_zip_to_usb('/nonexistent/file.zip', usb_mount_point)

        assert result is False
        captured = capsys.readouterr()
        assert 'ZIP file not found' in captured.out

    @pytest.mark.unit
    def test_extract_zip_to_usb_invalid_mount_point(self, copy_fatn, sample_zip_file, capsys):
        """Test extraction to invalid mount point."""
        result = copy_fatn.extract_zip_to_usb(sample_zip_file, '/invalid/mount')

        assert result is False
        captured = capsys.readouterr()
        assert 'Invalid mount point' in captured.out

    @pytest.mark.unit
    def test_extract_zip_to_usb_corrupted_zip(self, copy_fatn, corrupted_zip_file, usb_mount_point, capsys):
        """Test extraction of corrupted ZIP file."""
        result = copy_fatn.extract_zip_to_usb(corrupted_zip_file, usb_mount_point)

        assert result is False
        captured = capsys.readouterr()
        assert 'Invalid ZIP file' in captured.out


# ============================================================================
# Complete Workflow Tests
# ============================================================================

class TestCompleteWorkflow:
    """Tests for the complete USB update workflow."""

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_process_usb_update_success(self, mock_run, copy_fatn, capsys):
        """Test successful complete USB update process."""
        with patch.object(copy_fatn, 'mount_usb_device') as mock_mount, \
             patch.object(copy_fatn, 'remove_old_mp3_files') as mock_remove, \
             patch.object(copy_fatn, 'extract_zip_to_usb') as mock_extract, \
             patch.object(copy_fatn, 'unmount_usb_device') as mock_unmount:

            mock_mount.return_value = '/media/user/USB'
            mock_remove.return_value = 3
            mock_extract.return_value = True
            mock_unmount.return_value = True
            mock_run.return_value = Mock(returncode=0)

            result = copy_fatn.process_usb_update('/dev/sda1', '/tmp/fatn.zip')

            assert result is True
            mock_mount.assert_called_once_with('/dev/sda1')
            mock_remove.assert_called_once_with('/media/user/USB')
            mock_extract.assert_called_once_with('/tmp/fatn.zip', '/media/user/USB')
            mock_unmount.assert_called_once_with('/dev/sda1')

            captured = capsys.readouterr()
            assert 'USB update complete' in captured.out

    @pytest.mark.unit
    def test_process_usb_update_mount_failure(self, copy_fatn, capsys):
        """Test USB update when mounting fails."""
        with patch.object(copy_fatn, 'mount_usb_device') as mock_mount:
            mock_mount.return_value = None

            result = copy_fatn.process_usb_update('/dev/sda1', '/tmp/fatn.zip')

            assert result is False
            captured = capsys.readouterr()
            assert 'Failed to mount USB device' in captured.out

    @pytest.mark.unit
    def test_process_usb_update_extract_failure(self, copy_fatn, capsys):
        """Test USB update when extraction fails."""
        with patch.object(copy_fatn, 'mount_usb_device') as mock_mount, \
             patch.object(copy_fatn, 'remove_old_mp3_files') as mock_remove, \
             patch.object(copy_fatn, 'extract_zip_to_usb') as mock_extract, \
             patch.object(copy_fatn, 'unmount_usb_device') as mock_unmount:

            mock_mount.return_value = '/media/user/USB'
            mock_remove.return_value = 0
            mock_extract.return_value = False
            mock_unmount.return_value = True

            result = copy_fatn.process_usb_update('/dev/sda1', '/tmp/fatn.zip')

            assert result is False
            # Should still attempt to unmount
            mock_unmount.assert_called_once()

    @pytest.mark.unit
    @patch('subprocess.run')
    def test_process_usb_update_unmount_failure(self, mock_run, copy_fatn, capsys):
        """Test USB update when unmounting fails."""
        with patch.object(copy_fatn, 'mount_usb_device') as mock_mount, \
             patch.object(copy_fatn, 'remove_old_mp3_files') as mock_remove, \
             patch.object(copy_fatn, 'extract_zip_to_usb') as mock_extract, \
             patch.object(copy_fatn, 'unmount_usb_device') as mock_unmount:

            mock_mount.return_value = '/media/user/USB'
            mock_remove.return_value = 2
            mock_extract.return_value = True
            mock_run.return_value = Mock(returncode=0)
            mock_unmount.return_value = False

            result = copy_fatn.process_usb_update('/dev/sda1', '/tmp/fatn.zip')

            assert result is False
            captured = capsys.readouterr()
            assert 'Failed to unmount USB device' in captured.out
