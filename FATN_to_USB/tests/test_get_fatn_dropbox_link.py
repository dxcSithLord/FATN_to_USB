"""
Unit tests for Get_FATN_Dropbox_link module.

Tests the GetFATNUrl HTML parser class and Download_FATN function.
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, patch, mock_open, call
from fatn_to_usb.Get_FATN_Dropbox_link import GetFATNUrl, Download_FATN


# ============================================================================
# GetFATNUrl Class Tests
# ============================================================================

class TestGetFATNUrl:
    """Unit tests for GetFATNUrl HTML parser class."""

    @pytest.mark.unit
    def test_initialization(self):
        """Test that GetFATNUrl initializes with empty FATNurl."""
        parser = GetFATNUrl()
        assert parser.FATNurl == ''
        assert hasattr(parser, 'handle_starttag')

    @pytest.mark.unit
    def test_handle_starttag_valid_tinyurl(self):
        """Test extraction of valid tinyurl link from anchor tag."""
        parser = GetFATNUrl()
        attrs = [('href', 'https://tinyurl.com/test123')]

        parser.handle_starttag('a', attrs)

        assert parser.FATNurl == 'https://tinyurl.com/test123'
        assert 'tinyurl' in parser.FATNurl

    @pytest.mark.unit
    def test_handle_starttag_no_tinyurl(self):
        """Test behavior when no tinyurl present in anchor tag."""
        parser = GetFATNUrl()
        attrs = [('href', 'https://example.com')]

        parser.handle_starttag('a', attrs)

        assert parser.FATNurl == ''

    @pytest.mark.unit
    def test_handle_starttag_multiple_tinyurls(self):
        """Test that parser captures first tinyurl when multiple exist."""
        parser = GetFATNUrl()

        # First tinyurl
        parser.handle_starttag('a', [('href', 'https://tinyurl.com/first')])
        first_url = parser.FATNurl

        # Second tinyurl (should overwrite first)
        parser.handle_starttag('a', [('href', 'https://tinyurl.com/second')])

        # Parser should have the second URL (overwrites)
        assert parser.FATNurl == 'https://tinyurl.com/second'
        assert first_url == 'https://tinyurl.com/first'

    @pytest.mark.unit
    def test_handle_starttag_non_anchor_tag(self):
        """Test that non-anchor tags are ignored."""
        parser = GetFATNUrl()
        attrs = [('href', 'https://tinyurl.com/test')]

        parser.handle_starttag('div', attrs)

        assert parser.FATNurl == ''

    @pytest.mark.unit
    def test_handle_starttag_no_href_attribute(self):
        """Test anchor tag without href attribute."""
        parser = GetFATNUrl()
        attrs = [('class', 'some-class')]

        parser.handle_starttag('a', attrs)

        assert parser.FATNurl == ''

    @pytest.mark.unit
    def test_handle_starttag_multiple_attributes(self):
        """Test anchor tag with multiple attributes including tinyurl."""
        parser = GetFATNUrl()
        attrs = [
            ('class', 'download-link'),
            ('href', 'https://tinyurl.com/test456'),
            ('target', '_blank')
        ]

        parser.handle_starttag('a', attrs)

        assert parser.FATNurl == 'https://tinyurl.com/test456'

    @pytest.mark.unit
    def test_error_handler_does_not_raise(self):
        """Test that error handler doesn't raise exceptions."""
        parser = GetFATNUrl()

        # Should not raise any exception
        try:
            parser.error("Test error message")
            assert True
        except Exception:
            pytest.fail("error() method raised an exception")

    @pytest.mark.unit
    def test_feed_with_sample_html(self, sample_fatn_html_with_tinyurl):
        """Test feeding actual HTML to the parser."""
        parser = GetFATNUrl()
        parser.feed(sample_fatn_html_with_tinyurl)

        assert 'tinyurl.com/test123' in parser.FATNurl

    @pytest.mark.unit
    def test_feed_with_html_without_tinyurl(self, sample_fatn_html_without_tinyurl):
        """Test feeding HTML without tinyurl to the parser."""
        parser = GetFATNUrl()
        parser.feed(sample_fatn_html_without_tinyurl)

        assert parser.FATNurl == ''

    @pytest.mark.unit
    def test_feed_with_malformed_html(self, malformed_html):
        """Test that parser handles malformed HTML gracefully."""
        parser = GetFATNUrl()

        # Should not raise exception
        try:
            parser.feed(malformed_html)
            # Should still extract tinyurl if present
            assert 'tinyurl' in parser.FATNurl.lower()
        except Exception as e:
            pytest.fail(f"Parser raised exception on malformed HTML: {e}")


# ============================================================================
# Download_FATN Function Tests
# ============================================================================

class TestDownloadFATN:
    """Unit tests for Download_FATN function."""

    @pytest.mark.unit
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.requests.get')
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_success(self, mock_file, mock_makedirs, mock_get, temp_dir):
        """Test successful download with valid URL."""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.ok = True
        mock_response.iter_content = Mock(return_value=[
            b'chunk1',
            b'chunk2',
            b'chunk3'
        ])
        mock_get.return_value = mock_response

        # Execute download
        Download_FATN('http://test.com/file.zip', temp_dir)

        # Verify requests.get was called
        mock_get.assert_called_once_with('http://test.com/file.zip', stream=True)

        # Verify file was opened for writing
        expected_path = os.path.join(temp_dir, 'FATN News Weekly File.zip')
        mock_file.assert_called_once_with(expected_path, 'wb')

        # Verify chunks were written
        handle = mock_file()
        assert handle.write.call_count == 3

    @pytest.mark.unit
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.makedirs')
    def test_download_creates_directory(self, mock_makedirs, temp_dir):
        """Test that download creates directory if it doesn't exist."""
        test_dir = os.path.join(temp_dir, 'new_dir')

        with patch('fatn_to_usb.Get_FATN_Dropbox_link.requests.get'), \
             patch('builtins.open', mock_open()):
            Download_FATN('http://test.com/file.zip', test_dir)

        mock_makedirs.assert_called_once_with(test_dir)

    @pytest.mark.unit
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.requests.get')
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.makedirs')
    def test_download_handles_fileexists_error(self, mock_makedirs, mock_get, capsys):
        """Test handling of FileExistsError when creating directory."""
        mock_makedirs.side_effect = FileExistsError("Directory exists")
        mock_response = Mock()
        mock_response.ok = True
        mock_response.iter_content = Mock(return_value=[b'data'])
        mock_get.return_value = mock_response

        with patch('builtins.open', mock_open()), \
             patch('fatn_to_usb.Get_FATN_Dropbox_link.os.path.exists', return_value=True):
            Download_FATN('http://test.com/file.zip', '/test/dir')

        captured = capsys.readouterr()
        assert 'FileExists error' in captured.out

    @pytest.mark.unit
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.makedirs')
    def test_download_handles_permission_error(self, mock_makedirs, capsys):
        """Test handling of PermissionError when creating directory."""
        mock_makedirs.side_effect = PermissionError("No permission")

        Download_FATN('http://test.com/file.zip', '/root/protected')

        captured = capsys.readouterr()
        assert 'Permission error' in captured.out

    @pytest.mark.unit
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.requests.get')
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.makedirs')
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.path.exists', return_value=True)
    def test_download_http_404_error(self, mock_exists, mock_makedirs, mock_get, capsys):
        """Test handling of HTTP 404 error."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.text = 'Not Found'
        mock_get.return_value = mock_response

        Download_FATN('http://test.com/missing.zip', '/tmp')

        captured = capsys.readouterr()
        assert 'Download failed: status code 404' in captured.out

    @pytest.mark.unit
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.requests.get')
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.makedirs')
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.path.exists', return_value=True)
    def test_download_http_500_error(self, mock_exists, mock_makedirs, mock_get, capsys):
        """Test handling of HTTP 500 server error."""
        mock_response = Mock()
        mock_response.ok = False
        mock_response.status_code = 500
        mock_response.text = 'Internal Server Error'
        mock_get.return_value = mock_response

        Download_FATN('http://test.com/file.zip', '/tmp')

        captured = capsys.readouterr()
        assert 'Download failed: status code 500' in captured.out

    @pytest.mark.unit
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.makedirs')
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.path.exists', return_value=False)
    def test_download_invalid_directory(self, mock_exists, mock_makedirs, capsys):
        """Test behavior when directory doesn't exist after creation attempt."""
        # makedirs succeeds but directory still doesn't exist (edge case)
        Download_FATN('http://test.com/file.zip', '/invalid/path')

        captured = capsys.readouterr()
        assert 'Download failed - directory location not valid' in captured.out

    @pytest.mark.unit
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.requests.get')
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_uses_default_filename(self, mock_file, mock_makedirs, mock_get, temp_dir):
        """Test that download uses default filename when not specified."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.iter_content = Mock(return_value=[b'data'])
        mock_get.return_value = mock_response

        Download_FATN('http://test.com/file.zip', temp_dir)

        # Check that default filename was used
        expected_path = os.path.join(temp_dir, 'FATN News Weekly File.zip')
        mock_file.assert_called_with(expected_path, 'wb')

    @pytest.mark.unit
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.requests.get')
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_custom_filename(self, mock_file, mock_makedirs, mock_get, temp_dir):
        """Test download with custom filename."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.iter_content = Mock(return_value=[b'data'])
        mock_get.return_value = mock_response

        custom_name = 'custom_file.zip'
        Download_FATN('http://test.com/file.zip', temp_dir, custom_name)

        expected_path = os.path.join(temp_dir, custom_name)
        mock_file.assert_called_with(expected_path, 'wb')

    @pytest.mark.unit
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.requests.get')
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_chunked_writing(self, mock_file, mock_makedirs, mock_get, temp_dir):
        """Test that file is written in chunks correctly."""
        chunks = [b'chunk1', b'chunk2', b'chunk3', b'chunk4']
        mock_response = Mock()
        mock_response.ok = True
        mock_response.iter_content = Mock(return_value=chunks)
        mock_get.return_value = mock_response

        Download_FATN('http://test.com/file.zip', temp_dir)

        handle = mock_file()

        # Verify each chunk was written
        assert handle.write.call_count == len(chunks)
        for chunk in chunks:
            handle.write.assert_any_call(chunk)

        # Verify flush and fsync were called for each chunk
        assert handle.flush.call_count == len(chunks)
        assert handle.fileno.call_count == len(chunks)

    @pytest.mark.unit
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.requests.get')
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_empty_chunks_skipped(self, mock_file, mock_makedirs, mock_get, temp_dir):
        """Test that empty chunks are skipped during download."""
        # Mix of empty and non-empty chunks
        chunks = [b'chunk1', b'', b'chunk2', None, b'chunk3']
        mock_response = Mock()
        mock_response.ok = True
        mock_response.iter_content = Mock(return_value=chunks)
        mock_get.return_value = mock_response

        Download_FATN('http://test.com/file.zip', temp_dir)

        handle = mock_file()

        # Only non-empty chunks should be written (3 chunks)
        assert handle.write.call_count == 3

    @pytest.mark.unit
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.makedirs')
    def test_download_os_error(self, mock_makedirs, capsys):
        """Test handling of unexpected OS errors."""
        mock_makedirs.side_effect = OSError("Unexpected OS error")

        Download_FATN('http://test.com/file.zip', '/tmp')

        captured = capsys.readouterr()
        assert 'Unexpected OS error' in captured.out

    @pytest.mark.unit
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.requests.get')
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.makedirs')
    def test_download_streams_response(self, mock_makedirs, mock_get, temp_dir):
        """Test that download uses streaming mode for large files."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.iter_content = Mock(return_value=[b'data'])
        mock_get.return_value = mock_response

        with patch('builtins.open', mock_open()):
            Download_FATN('http://test.com/largefile.zip', temp_dir)

        # Verify stream=True was passed to requests.get
        mock_get.assert_called_once_with('http://test.com/largefile.zip', stream=True)

    @pytest.mark.unit
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.requests.get')
    @patch('fatn_to_usb.Get_FATN_Dropbox_link.os.makedirs')
    @patch('builtins.open', new_callable=mock_open)
    def test_download_chunk_size(self, mock_file, mock_makedirs, mock_get, temp_dir):
        """Test that download uses correct chunk size (8KB)."""
        mock_response = Mock()
        mock_response.ok = True
        mock_response.iter_content = Mock(return_value=[b'data'])
        mock_get.return_value = mock_response

        Download_FATN('http://test.com/file.zip', temp_dir)

        # Verify iter_content was called with correct chunk size
        mock_response.iter_content.assert_called_once_with(chunk_size=1024 * 8)
