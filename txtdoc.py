#!/usr/bin/env python
# coding: utf-8
# License: MIT
# Author: Chris Ward <chris@zeroknowledge.fm>
# DESCRIPTION
__app_name__ = "XXX"
__version__ = "0.1"
'''
0.1:
'''

import re
from lxml import html

import logging
log_format = '>> %(message)s'
logging.basicConfig(level=logging.DEBUG, format=log_format)
log = logging.getLogger()

import requests
req_log = requests.logging.getLogger()
req_log.setLevel(logging.WARNING)  # Quiet down request API calls to airtable


def _github(line_in):
    r = re.match(r'^((https?://)?github.com/(([^/ ]+)/?(([^ /]*))))', line_in)
    return line_in if not r else f'{r.group(0)} | @{r.group(3)} | Github'


def _twitter(line_in):
    r = re.search(r'^((https?://)?twitter.com/([^/ ]+)/?([^ ]*))', line_in)
    by = 'Tweet by ' if r and r.group(4) else ''
    return f'{r.group(0)} | {by}@{r.group(3)} | Twitter' if r else line_in


def _zkfm(line_in):
    r = re.search(r'^((https?://)?zeroknowledge.fm/([^/ ]+))', line_in)
    title = scrape_html_title(r.group(0)) if r else ''
    title = re.sub('- ZK Podcast$', '| ZK Podcast', title)
    title = re.sub('Episode', 'Ep', title)
    return f'{r.group(0)} | {title}' if r else line_in


def _youtube(line_in):
    r = re.match(r'^((https?://)?(youtu\.?be(.com)?)/?(\w+))', line_in)
    if r:
        url = r.group(1)
        vid = r.group(5)
        title = scrape_yt_title(vid)
    return line_in if not r else f'{url} | {title}'


#  def scrape_meta(vid, param=None): # we could return the whole json...
def scrape_yt_title(vid):
    params = {
        "format": "json",
        "url": f"https://www.youtube.com/watch?v={vid}"}
    url = "https://www.youtube.com/oembed"
    r = requests.get(url, params=params)
    r_json = r.json()
    param_out = 'No Title'
    param_out = r_json.get('title', param_out) if r else param_out
    return param_out


def scrape_html_title(url):
    r = requests.get(url)
    title = html.fromstring(r.content).findtext('.//title')
    title = title if title else 'No Title'
    title = re.sub(r'\s+', ' ', title).strip()
    return title


class TextDoc:
    def __init__(self, txt):
        self.text_in = txt.strip().strip('\n').strip()
        self.lines_in = self.text_in.split('\n')
        self.lines_out = []
        self.text_out = ''

    def reformat_links(self, md=False, max_line_len=0):
        mll = max_line_len
        if mll < 0:
            raise ValueError
        
        self.lines_out = [
                self._process_line(_, md) for _ in self.lines_in]

        if mll > 0:
            self.lines_out = [self._truncate(_, mll) for _ in self.lines_out]

        self.text_out = '\n'.join(self.lines_out)
        return self.text_out

    def _truncate(self, string, length):
        string_out = string[:length-4]
        return f"{string_out}..."

    def _force_simple(self, line_in):
        # link is markdown? convert needed
        r = re.search(r'\[([^\]]+)\]\((.+)\)', line_in)
        if not r:
            line_out = line_in
        else:
            txt = r.group(1)
            url = r.group(2)
            line_out = f"{url} | {txt}"
        return line_out

    def _process_line(self, line_in, md):
        line_in = re.sub('^\s+', '', line_in)
        line_in = re.sub('\s+$', '', line_in)
        line_in = self._force_simple(line_in)
        ps = [_github, _twitter, _zkfm, _youtube]
        for f in ps:
            line_out = f(line_in)
            if line_out != line_in:
                break
        else:
            line_out = self._default(line_in, from_url=True)

        if md:
            url = line_out.split('|')[0].strip()
            txt = '|'.join(line_out.split('|')[1:]).strip()
            line_out = f"[{url}]({txt})"

        return line_out

    def _default(self, line_in, from_url=True):
        r = re.match(r'^(((https?://)?([^/ ]+))(/([^ ]+))?)', line_in)
        #r = re.match(r'^(1(2(3https?://)?(4[^/ ]+))(5/(6[^ ]+))?)', line_in)
        if not r:
            return line_in
        url = r.group(1)
        domain = r.group(4)
        path = r.group(6)

        if from_url and path:
            title = re.sub(r'/\s*$', '', r.group(6))  # trailing /
            title = title.split('/')[-1]  # get path end dir
            title = re.sub(r'[-_]+', ' ', title)  # replace -_ with spaces
            title = re.sub(r'[^\w\s.]', '', title)  # remove url param chars
            title = title.title()  # upcase title
        else:
            title = scrape_html_title(r.group(1)) if r else ''
        return f'{url} | {title} | {domain}'


class MarkdownDoc:
    def __init__(self, txt):
        self.text_in = txt
    



if __name__ == "__main__":
    txt = '''
[@tarunchitra](https://twitter.com/tarunchitra) | Twitter
[DevConnet AMS 2022](https://devconnect.org/)
https://github.com/paritytech - @paritytech | Github
https://github.com/paritytech/polkadot/tree/master/node/network - @polkadot/network | Github
https://twitter.com/rphmeier - @rphmeier | Twitter
https://zeroknowledge.fm/83-2/
https://kusama.network/ - Kusama, Polkadot’s canary network
https://docs.substrate.io/v3/runtime/frame/#pallets - Pallets
https://youtu.be/5cgq5jOZx9g - workshop from Parity’s Shawn Tabrizi
https://substrate.io - Substrate runtime modules
https://blog.quarkslab.com/resources/2022-02-27-xcmv2-audit/21-12-908-REP.pdf - Full audit report for XCM
'''
    t = TextDoc(txt)
    o = t.reformat_links()
    print (o)

    txt_md = '''
bla bla [Anna](https://twitter.com/annarrose) catches up with [Tarun](https://twitter.com/tarunchitra), [Guillermo](https://twitter.com/GuilleAngeris) and [Brendan](https://twitter.com/_bfarmer) at DevConnect  bla bla bla blabla

Here are some links for this episode:
[@tarunchitra](https://twitter.com/tarunchitra) | Twitter
[@GuilleAngeris](https://twitter.com/GuilleAngeris)  | Twitter
[@_bfarmer](https://twitter.com/_bfarmer) | Twitter
[Einstein Notation](https://en.wikipedia.org/wiki/Einstein_notation) | Wikipedia
[Wordcel / Shape Rotator / Mathcel](https://knowyourmeme.com/memes/cultures/wordcel-shape-rotator-mathcel) | knowyourmeme.com
(DevConnet AMS 2022)[https://devconnect.org/]
(zkSummit7 AMS)[https://zksummit.com/]
(Diplomacy game)[https://en.wikipedia.org/wiki/Diplomacy_(game)]
(zkSummit 7 YouTube Playlist)[https://www.youtube.com/playlist?list=PLj80z0cJm8QFnY6VLVa84nr-21DNvjW               H7]
(P-Value Explained)[https://www.investopedia.com/terms/p/p-value.asp]
(Topology)[https://topology.gg/]
(What is measure theory?)[https://www.britannica.com/science/measure-theory]

**If you like what we do:**
Subscribe to our [podcast newsletter](https://zeroknowledge.substack.com)
Follow us on Twitter [@zeroknowledgefm](https://twitter.com/zeroknowledgefm)
'''
    md = MarkdownDoc(txt_md)
