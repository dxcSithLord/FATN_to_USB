#!/usr/bin/env python3
"""
Main orchestration script for FATN_to_USB system.

This script coordinates the complete workflow:
1. Detect USB device insertion
2. Download latest FATN content from website
3. Display status messages on LCD
4. Extract content to USB drive
5. Safely unmount and signal completion
"""
import os
import sys
import time
import argparse
from pathlib import Path


def import_display_module():
    """
    Import and initialize display module using detection system.

    Returns:
        tuple: (display object, do_mes function) or (None, None) if unavailable
    """
    try:
        from scrolling_text import do_mes, disp
        # Display is already initialized by scrolling_text module
        # which uses the display_detector system
        return disp, do_mes

    except ImportError as e:
        print(f'Warning: Could not import display module: {e}')
        return None, None


def display_message(disp, do_mes, message, color=(0, 255, 0)):
    """
    Display a message on the LCD if available.

    Args:
        disp: Display object
        do_mes: Display function
        message (str): Message to display
        color (tuple): RGB color tuple (default green)
    """
    if disp and do_mes:
        try:
            do_mes(disp, message, color)
        except Exception as e:
            print(f'Error displaying message: {e}')
    else:
        print(f'[DISPLAY] {message}')


def is_safe_url(url):
    """
    Validate that a URL uses a safe scheme (http or https only).

    Prevents SSRF attacks by rejecting file://, ftp://, and other unsafe schemes.

    Args:
        url (str): URL to validate

    Returns:
        bool: True if URL scheme is safe, False otherwise
    """
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        # Only allow http and https schemes
        return parsed.scheme in ('http', 'https')
    except Exception:
        return False


def download_fatn_content(download_dir=None):
    """
    Download the latest FATN content with URL validation.

    Args:
        download_dir (str): Directory to save ZIP file (default: ~/FATN_to_USB/)

    Returns:
        str: Path to downloaded ZIP file, or None if failed
    """
    if download_dir is None:
        download_dir = os.path.expanduser('~/FATN_to_USB/')

    try:
        # Import the download module
        from Get_FATN_Dropbox_link import GetFATNUrl, Download_FATN
        from urllib.request import urlopen

        print('\n=== Downloading FATN Content ===')

        # Parse FATN website for Dropbox link
        url = 'https://www.fatntalkingnews.org.uk/about-fatn-talking-news/#coronavirus'
        print(f'Fetching FATN website: {url}')

        FATN_parse = GetFATNUrl()
        FATN = urlopen(url, timeout=30)
        FATN_parse.feed(str(FATN.read()))

        if not FATN_parse.FATNurl:
            print('❌ No Dropbox link found on FATN website')
            return None

        # Validate URL scheme before following redirect (SSRF prevention)
        if not is_safe_url(FATN_parse.FATNurl):
            print(f'❌ Security: Rejected unsafe URL scheme: {FATN_parse.FATNurl}')
            return None

        # Get actual Dropbox URL from tinyurl
        print(f'Resolving redirect: {FATN_parse.FATNurl}')
        FATNdropboxurl = urlopen(FATN_parse.FATNurl, timeout=30)
        dropbox_url = FATNdropboxurl.geturl()
        print(f'Dropbox URL: {dropbox_url}')

        # Convert to download link
        download_url = dropbox_url.replace('?dl=0', '?dl=1')
        print(f'Download URL: {download_url}')

        # Download the file
        Download_FATN(download_url, download_dir)

        # Construct expected file path
        zip_path = os.path.join(download_dir, 'FATN News Weekly File.zip')

        if os.path.exists(zip_path):
            print(f'✓ Downloaded successfully: {zip_path}')
            return zip_path
        else:
            print('❌ Download completed but file not found')
            return None

    except Exception as e:
        print(f'❌ Error downloading FATN content: {e}')
        import traceback
        traceback.print_exc()
        return None


def wait_for_usb_device(timeout=300):
    """
    Wait for a USB device to be inserted.

    Args:
        timeout (int): Maximum time to wait in seconds (default: 5 minutes)

    Returns:
        str: Device path if found, None if timeout
    """
    try:
        # Import USB management module
        # Use importlib to handle the dash in filename
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "copy_fatn",
            os.path.join(os.path.dirname(__file__), "copy-Fatn")
        )
        copy_fatn = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(copy_fatn)

        print(f'\nWaiting for USB device (timeout: {timeout}s)...')
        start_time = time.time()

        while (time.time() - start_time) < timeout:
            devices = copy_fatn.get_usb_devices()
            if devices:
                print(f'✓ USB device detected: {devices[0]}')
                return devices[0]

            # Check every 2 seconds
            time.sleep(2)
            # Show progress every 10 seconds
            if int(time.time() - start_time) % 10 == 0:
                print(f'  Still waiting... ({int(time.time() - start_time)}s elapsed)')

        print('❌ Timeout waiting for USB device')
        return None

    except Exception as e:
        print(f'❌ Error detecting USB device: {e}')
        return None


def process_fatn_workflow(args):
    """
    Execute the complete FATN_to_USB workflow.

    Args:
        args: Command-line arguments

    Returns:
        int: Exit code (0 = success, 1 = failure)
    """
    # Initialize display
    disp, do_mes = import_display_module()

    # Step 1: Show ready message
    display_message(disp, do_mes, 'FATN READY', (0, 255, 0))
    print('\n=== FATN_to_USB System Ready ===')

    # Step 2: Download FATN content if requested
    zip_path = None
    if args.download or args.auto:
        display_message(disp, do_mes, 'DOWNLOADING', (0, 128, 255))
        zip_path = download_fatn_content(args.download_dir)

        if not zip_path:
            display_message(disp, do_mes, 'DOWNLOAD FAILED', (255, 0, 0))
            return 1

        display_message(disp, do_mes, 'DOWNLOAD OK', (0, 255, 0))
    else:
        # Use existing ZIP file
        default_path = os.path.expanduser('~/FATN_to_USB/FATN News Weekly File.zip')
        zip_path = args.zip_file or default_path

        if not os.path.exists(zip_path):
            print(f'❌ ZIP file not found: {zip_path}')
            print('Use --download to download content first')
            display_message(disp, do_mes, 'NO ZIP FILE', (255, 128, 0))
            return 1

    # Step 3: Wait for USB device
    device_path = None
    if args.auto or args.wait_usb:
        display_message(disp, do_mes, 'INSERT USB', (255, 255, 0))
        device_path = wait_for_usb_device(timeout=args.usb_timeout)

        if not device_path:
            display_message(disp, do_mes, 'NO USB FOUND', (255, 0, 0))
            return 1
    else:
        # Use specified device
        device_path = args.device

        if not device_path:
            print('❌ No device specified. Use --device or --wait-usb')
            display_message(disp, do_mes, 'NO DEVICE', (255, 0, 0))
            return 1

    # Step 4: Process USB update
    try:
        # Import USB management module
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "copy_fatn",
            os.path.join(os.path.dirname(__file__), "copy-Fatn")
        )
        copy_fatn = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(copy_fatn)

        display_message(disp, do_mes, 'LOADING USB', (0, 128, 255))

        success = copy_fatn.process_usb_update(device_path, zip_path)

        if success:
            display_message(disp, do_mes, 'COMPLETE!', (0, 255, 0))
            print('\n✓ FATN content loaded successfully!')
            print('✓ USB can be safely removed')
            return 0
        else:
            display_message(disp, do_mes, 'USB FAILED', (255, 0, 0))
            return 1

    except Exception as e:
        print(f'❌ Error processing USB: {e}')
        import traceback
        traceback.print_exc()
        display_message(disp, do_mes, 'ERROR', (255, 0, 0))
        return 1


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(
        description='FATN_to_USB - Automated USB loader for FATN audio content',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Full automatic workflow (download + wait for USB + load)
  %(prog)s --auto

  # Download only
  %(prog)s --download

  # Load existing ZIP to specified USB device
  %(prog)s --device /dev/sda1 --zip-file ~/FATN\\ News\\ Weekly\\ File.zip

  # Wait for USB and load existing ZIP
  %(prog)s --wait-usb --zip-file ~/Downloads/fatn.zip
        '''
    )

    parser.add_argument(
        '--auto',
        action='store_true',
        help='Automatic mode: download, wait for USB, and load content'
    )

    parser.add_argument(
        '--download',
        action='store_true',
        help='Download latest FATN content from website'
    )

    parser.add_argument(
        '--download-dir',
        default=None,
        help='Directory to save downloaded ZIP (default: ~/FATN_to_USB/)'
    )

    parser.add_argument(
        '--zip-file',
        default=None,
        help='Path to FATN ZIP file (default: ~/FATN_to_USB/FATN News Weekly File.zip)'
    )

    parser.add_argument(
        '--device',
        default=None,
        help='USB device path (e.g., /dev/sda1)'
    )

    parser.add_argument(
        '--wait-usb',
        action='store_true',
        help='Wait for USB device to be inserted'
    )

    parser.add_argument(
        '--usb-timeout',
        type=int,
        default=300,
        help='USB detection timeout in seconds (default: 300)'
    )

    args = parser.parse_args()

    # Validate arguments
    if not (args.auto or args.download or args.device or args.wait_usb):
        parser.print_help()
        print('\nError: Must specify --auto, --download, --device, or --wait-usb')
        return 1

    # Execute workflow
    return process_fatn_workflow(args)


if __name__ == '__main__':
    sys.exit(main())
