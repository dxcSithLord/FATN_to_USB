#/* FATN_Parser.pl */

from html.parser import HTMLParser
#from html.entities import name2codepoint
#from lxml import html
import urllib

class GetFATNUrl(HTMLParser):
    
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
        
    local_filename = 'FATN News Weeekly File.zip'
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
print(FATNparse.FATNurl)

FATN2 = urllib.request.urlopen(FATNparse.FATNurl) # Get dropbox url from link
print("FATN Dropbox URL:", FATN2.geturl())
FATNdl= str(FATN2.geturl()).replace('?dl=0','?dl=1') # set the download bit
print( FATNdl )
Download_FATN(FATNdl, '/home/pi/' ) # go and get the file


