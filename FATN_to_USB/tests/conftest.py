"""
Pytest configuration and shared fixtures for FATN_to_USB tests.
"""
import pytest
import os
import tempfile
import zipfile
from unittest.mock import Mock, MagicMock


# ============================================================================
# Mock Display Fixtures
# ============================================================================

@pytest.fixture
def mock_display():
    """Create a mock display object for testing without hardware."""
    display = Mock()
    display.width = 240
    display.height = 240
    display.begin = Mock()
    display.display = Mock()
    return display


@pytest.fixture
def mock_st7789(monkeypatch):
    """Mock ST7789 display module."""
    mock_module = Mock()
    mock_module.ST7789 = Mock(return_value=Mock(width=240, height=240))
    mock_module.BG_SPI_CS_FRONT = 1
    monkeypatch.setitem(__import__('sys').modules, 'ST7789', mock_module)
    return mock_module


@pytest.fixture
def mock_st7735(monkeypatch):
    """Mock ST7735 display module."""
    mock_module = Mock()
    mock_module.ST7735 = Mock(return_value=Mock(width=160, height=80))
    monkeypatch.setitem(__import__('sys').modules, 'ST7735', mock_module)
    return mock_module


# ============================================================================
# File System Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_zip_file(temp_dir):
    """Create a sample ZIP file with MP3 files for testing."""
    zip_path = os.path.join(temp_dir, 'FATN News Weekly File.zip')

    with zipfile.ZipFile(zip_path, 'w') as zf:
        # Add sample "MP3" files (actually just text for testing)
        zf.writestr('news_1.mp3', b'Sample audio content 1')
        zf.writestr('news_2.mp3', b'Sample audio content 2')
        zf.writestr('news_3.mp3', b'Sample audio content 3')

    return zip_path


@pytest.fixture
def empty_zip_file(temp_dir):
    """Create an empty ZIP file for testing."""
    zip_path = os.path.join(temp_dir, 'empty.zip')
    with zipfile.ZipFile(zip_path, 'w') as zf:
        pass  # Create empty zip
    return zip_path


@pytest.fixture
def corrupted_zip_file(temp_dir):
    """Create a corrupted ZIP file for testing."""
    zip_path = os.path.join(temp_dir, 'corrupted.zip')
    with open(zip_path, 'wb') as f:
        f.write(b'This is not a valid ZIP file')
    return zip_path


@pytest.fixture
def usb_mount_point(temp_dir):
    """Create a mock USB mount point directory."""
    mount_point = os.path.join(temp_dir, 'usb_mount')
    os.makedirs(mount_point, exist_ok=True)

    # Add some existing MP3 files
    for i in range(3):
        mp3_path = os.path.join(mount_point, f'old_news_{i}.mp3')
        with open(mp3_path, 'wb') as f:
            f.write(b'Old content')

    return mount_point


# ============================================================================
# HTML/Web Content Fixtures
# ============================================================================

@pytest.fixture
def sample_fatn_html_with_tinyurl():
    """Sample FATN website HTML with tinyurl link."""
    return '''
    <html>
        <body>
            <div class="content">
                <h1>FATN Talking News</h1>
                <p>Download the latest edition:</p>
                <a href="https://tinyurl.com/test123">Download FATN</a>
            </div>
        </body>
    </html>
    '''


@pytest.fixture
def sample_fatn_html_without_tinyurl():
    """Sample FATN website HTML without tinyurl link."""
    return '''
    <html>
        <body>
            <div class="content">
                <h1>FATN Talking News</h1>
                <p>No download available this week.</p>
                <a href="https://example.com">Other Link</a>
            </div>
        </body>
    </html>
    '''


@pytest.fixture
def sample_fatn_html_multiple_tinyurls():
    """Sample FATN website HTML with multiple tinyurl links."""
    return '''
    <html>
        <body>
            <a href="https://tinyurl.com/first">First</a>
            <a href="https://tinyurl.com/second">Second</a>
            <a href="https://example.com">Other</a>
        </body>
    </html>
    '''


@pytest.fixture
def malformed_html():
    """Malformed HTML for testing error handling."""
    return '''
    <html>
        <body>
            <div class="content">
                <h1>Unclosed tags
                <a href="https://tinyurl.com/test">Link
            </div>
    '''


# ============================================================================
# HTTP Response Fixtures
# ============================================================================

@pytest.fixture
def mock_successful_http_response():
    """Mock a successful HTTP response."""
    response = Mock()
    response.ok = True
    response.status_code = 200
    response.iter_content = Mock(return_value=[
        b'chunk1' * 100,
        b'chunk2' * 100,
        b'chunk3' * 100
    ])
    return response


@pytest.fixture
def mock_failed_http_response():
    """Mock a failed HTTP response (404)."""
    response = Mock()
    response.ok = False
    response.status_code = 404
    response.text = 'Not Found'
    return response


@pytest.fixture
def mock_server_error_response():
    """Mock a server error response (500)."""
    response = Mock()
    response.ok = False
    response.status_code = 500
    response.text = 'Internal Server Error'
    return response


# ============================================================================
# Process/Subprocess Fixtures
# ============================================================================

@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for testing system commands."""
    def _mock_run(cmd, **kwargs):
        result = Mock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""

        # Simulate different commands
        if 'udisksctl' in cmd and 'status' in cmd:
            result.stdout = "/dev/sda1  mounted at /media/usb"
        elif 'udisksctl' in cmd and 'mount' in cmd:
            result.stdout = "Mounted /dev/sda1 at /media/user/USB"
        elif 'udisksctl' in cmd and 'unmount' in cmd:
            result.stdout = "Unmounted /dev/sda1"

        return result

    return _mock_run


# ============================================================================
# CPU Info Fixtures
# ============================================================================

@pytest.fixture
def raspberry_pi_cpuinfo(temp_dir):
    """Create a mock /proc/cpuinfo for Raspberry Pi."""
    cpuinfo_path = os.path.join(temp_dir, 'cpuinfo_rpi')
    with open(cpuinfo_path, 'w') as f:
        f.write('''processor       : 0
model name      : ARMv6-compatible processor rev 7 (v6l)
BogoMIPS        : 697.95
Hardware        : BCM2835
Revision        : 900092
Model           : Raspberry Pi Zero W Rev 1.1
''')
    return cpuinfo_path


@pytest.fixture
def generic_linux_cpuinfo(temp_dir):
    """Create a mock /proc/cpuinfo for generic Linux."""
    cpuinfo_path = os.path.join(temp_dir, 'cpuinfo_linux')
    with open(cpuinfo_path, 'w') as f:
        f.write('''processor       : 0
vendor_id       : GenuineIntel
cpu family      : 6
model           : 142
model name      : Intel(R) Core(TM) i7-8550U CPU @ 1.80GHz
''')
    return cpuinfo_path


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def rgb_colors():
    """Sample RGB color tuples for testing."""
    return {
        'red': (255, 0, 0),
        'green': (0, 255, 0),
        'blue': (0, 0, 255),
        'yellow': (255, 255, 0),
        'white': (255, 255, 255),
        'black': (0, 0, 0),
    }


@pytest.fixture
def test_messages():
    """Sample messages for display testing."""
    return {
        'short': 'USB',
        'medium': 'FATN READY',
        'long': 'Downloading latest FATN content',
        'very_long': 'This is a very long message that will definitely require scrolling on the display',
        'empty': '',
        'special_chars': 'Test!@#$%^&*()_+-=[]{}|;:",.<>?/',
    }


# ============================================================================
# Parametrize Helpers
# ============================================================================

# HTTP status codes for parametrized testing
HTTP_ERROR_CODES = [400, 401, 403, 404, 500, 502, 503]

# Common file system errors
FILE_SYSTEM_ERRORS = [
    FileExistsError,
    FileNotFoundError,
    PermissionError,
    OSError,
    IsADirectoryError,
    NotADirectoryError,
]

# USB device paths for testing
SAMPLE_USB_DEVICES = [
    '/dev/sda1',
    '/dev/sdb1',
    '/dev/sdc1',
    '/dev/nvme0n1p1',
]
