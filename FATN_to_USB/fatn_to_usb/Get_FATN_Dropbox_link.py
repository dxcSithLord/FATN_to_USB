#!/usr/bin/env python3
#/* FATN_Parser.pl */

from html.parser import HTMLParser
import urllib

class GetFATNUrl(HTMLParser):
    ''' Extend HTMLParser template to handle FATN Website, looking for
    dropbox tinyurl link.  Define handle_starttag to checkfor 
    specific condition and extract link into self.FATNurl
    '''
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for name, value in attrs:
                if name == 'href' and 'tinyurl' in value:
                    print( "Dropbox URL: ", value)
                    self.FATNurl = value


import os
import requests 

def Download_FATN(url: str, folder_name:str):
    if not os.path.exists(folder_name):
        os.makedirs(folder_name) # create folder if it does not exist
        
    local_filename = 'FATN News Weekly File.zip'
    path=os.path.join(folder_name, local_filename)
    r = requests.get(url, stream=True)
    if r.ok:
        print("Saving to", os.path.abspath(path))
        with open(path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*8):
                if chunk:
                    f.write(chunk)
                    f.flush
                    os.fsync(f.fileno())
                    #print('.',end='')
    else: # HTTP status code 4xx/5xx
        print("Download failed: status code {}\n{}".format(r.status_code,r.text))


url = 'https://www.fatntalkingnews.org.uk/about-fatn-talking-news/#coronavirus'
FATNparse = GetFATNUrl()

FATN = urllib.request.urlopen(url)  # get the FATN wordpress webpage
FATNparse.feed(str(FATN.read()))    # parse it for the dropbox link
# print(FATNparse.FATNurl)

FATNdropboxurl = urllib.request.urlopen(FATNparse.FATNurl) # Get dropbox url from link
print("FATN Dropbox URL:", FATNdropboxurl.geturl())

FATNdownload= str(FATNdropboxurl.geturl()).replace('?dl=0','?dl=1') # set the download bit
print( FATNdownload )

Download_FATN(FATNdownload, '/home/pi/' ) # go and get the file


