# /* FATN_Parser.pl */

from html.parser import HTMLParser
import urllib
import os
import requests


class GetFATNUrl(HTMLParser):
    ''' Extend HTMLParser template to handle FATN Website, looking for
    dropbox tinyurl link.  Define handle_starttag to checkfor
    specific condition and extract link into self.FATNurl
    '''

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for name, value in attrs:
                if name == 'href' and 'tinyurl' in value:
                    print("Dropbox URL: ", value)
                    self.FATNurl = value


'''
 For future consideration:
 2001  curl -L -I http://files.fatntalkingnews.org.uk/audio/magazine.mp3
 2002  curl -L -I https://files.fatntalkingnews.org.uk/audio/magazine.mp3
 2003  curl -L -I https://files.fatntalkingnews.org.uk/audio/Arena.mp3
 2004  curl -L -I https://files.fatntalkingnews.org.uk/audio/Haslemere.mp3
 2005  curl -L -I https://files.fatntalkingnews.org.uk/audio/Alton.mp3
OSError
     ConnectionError
         BrokenPipeError
         ConnectionAbortedError
         ConnectionRefusedError
         ConnectionResetError
             RemoteDisconnected
     BlockingIOError
     ChildProcessError
     FileExistsError
     FileNotFoundError
     IsADirectoryError
     NotADirectoryError
     InterruptedError
     PermissionError
     ProcessLookupError
     TimeoutError
     UnsupportedOperation
     ItimerError
     Error
         SameFileError
     SpecialFileError
     ExecError
     ReadError
     URLError
         HTTPError
         ContentTooShortError
     herror
     gaierror
     timeout
     SSLError
         SSLCertVerificationError
         SSLZeroReturnError
         SSLWantReadError
         SSLWantWriteError
         SSLSyscallError
         SSLEOFError
     BadGzipFile
     RequestException
         HTTPError
         ConnectionError
             ProxyError
             SSLError
             ConnectTimeout
         Timeout
             ConnectTimeout
             ReadTimeout
         URLRequired
         TooManyRedirects
         MissingSchema
         InvalidSchema
         InvalidURL
             InvalidProxyURL
         InvalidHeader
         ChunkedEncodingError
         ContentDecodingError
         StreamConsumedError
         RetryError
         UnrewindableBodyError
     LoadError
     FetchCancelledException
     FetchFailedException
         UntrustedException
     LockFailedException
'''


def Download_FATN(download_url: str,
                  folder_name: str,
                  local_file=str('FATN News Weeekly File.zip')):
    """ Download the given url string into the location provided by
    folder_name and localFile.
    """
    try:
        os.makedirs(folder_name)  # create folder if it does not exist
    except FileExistsError as exception:
        print('FileExists error:', repr(exception))
    except FileNotFoundError as exception:
        print('FileNotFound error:', repr(exception))
    except IsADirectoryError as exception:
        ('Is A Directory error:', repr(exception))
    except NotADirectoryError as exception:
        print('Not A Directory error:', repr(exception))
    except PermissionError as exception:
        print('Permission error:', repr(exception))
    except OSError as exception:
        print('Unexpected OS error:', repr(exception))
        return
    except BaseException as exception:
        print('Unexpected error:', repr(exception))


    if os.path.exists(folder_name):
        path = os.path.join(folder_name, local_file)
        r = requests.get(download_url, stream=True)
        if r.ok:
            print("Saving to", os.path.abspath(path))
            with open(path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024 * 8):
                    if chunk:
                        f.write(chunk)
                        f.flush
                        os.fsync(f.fileno())
                        # print('.',end='')
        else:  # HTTP status code 4xx/5xx
            print("Download failed: status code {}\n{}".format(r.status_code, r.text))
    else:
        print('Download failed - directory location not valid')


url = 'https://www.fatntalkingnews.org.uk/about-fatn-talking-news/#coronavirus'
FATN_parse = GetFATNUrl()

FATN = urllib.request.urlopen(url)  # get the FATN wordpress webpage
FATN_parse.feed(str(FATN.read()))  # parse it for the dropbox link
# print(FATN_parse.FATNurl)

FATNdropboxurl = urllib.request.urlopen(FATNparse.FATNurl)  # Get dropbox url from link
print("FATN Dropbox URL:", FATNdropboxurl.geturl())

FATNdownload = str(FATNdropboxurl.geturl()).replace('?dl=0', '?dl=1')  # set the download bit
print(FATNdownload)

Download_FATN(FATNdownload, '/home/pi/')  # go and get the file
