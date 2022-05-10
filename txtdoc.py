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
import requests
from lxml import html

import logging
log_format = '>> %(message)s'
logging.basicConfig(level=logging.DEBUG, format=log_format)
log = logging.getLogger()


def _github(line_in):
    r = re.match(r'^((https?://)?github.com/(([^/ ]+)/?(([^ /]*))))', line_in)
    return line_in if not r else f'{r.group(0)} | @{r.group(3)} | Github'


def _twitter(line_in):
    r = re.search(r'^((https?://)?twitter.com/([^/ ]+)/?([^ ]*))', line_in)
    by = 'Tweet by ' if r and r.group(4) else ''
    return f'{r.group(0)} | {by}@{r.group(3)} | Twitter' if r else line_in


def _zkfm(line_in):
    r = re.search(r'^((https?://)?zeroknowledge.fm/([^/ ]+))', line_in)
    title = scrape_title(r.group(0)) if r else ''
    title = re.sub('- ZK Podcast$', '| ZK Podcast', title)
    title = re.sub('Episode', 'Ep', title)
    return f'{r.group(0)} | {title}' if r else line_in


def _youtube(line_in):
    r = re.match(r'^((https?://)?(youtu\.?be(.com)?)/?(\w+))', line_in)
    if r:
        url = r.group(1)
        vid = r.group(5)
        title = scrape_title(vid)
    return line_in if not r else f'{url} | {title}'


def _unknown(line_in, from_url=True):
    r = re.match(r'^(((https?://)?([^/ ]+))(/([^ ]+))?)', line_in)
    if not r:
        return line_in
    domain = '.'.join(r.group(3).split('.')[-2:])
    if from_url and r.group(4):
        title = re.sub(r'/\s*$', '', r.group(4))
        title = title.split('/')[-1]
        title = re.sub(r'[-_]+', ' ', title)
        title = title.title()
    else:
        title = scrape_title(r.group(1)) if r else ''
    return f'{r.group(1)} | {title} | {domain}'


#  def scrape_meta(vid, param=None): # we could return the whole json...
def scrape_title(vid):
    params = {
        "format": "json",
        "url": f"https://www.youtube.com/watch?v={vid}"}
    url = "https://www.youtube.com/oembed"
    r = requests.get(url, params=params)
    r_json = r.json()
    param_out = 'No Title'
    param_out = r_json.get('title', param_out) if r else param_out
    return param_out


def _scrape_title(url):
    r = requests.get(url)
    title = html.fromstring(r.content).findtext('.//title')
    title = title if title else 'No Title'
    title = re.sub(r'\s+', ' ', title).strip()
    return title


class TextDoc:
    def __init__(self, txt):
        self.txt_in = txt.strip().strip('\n').strip()
        self.lines_in = self.text_in.split('\n')

    def reformat_links(self, md=False):
        return [self._process_line(_, md) for _ in self.lines_in]

    def _process_line(self, line_in, md):
        ps = [_github, _twitter, _zkfm, _youtube]
        for f in ps:
            line_out = f(line_in)
            if line_out != line_in:
                break
        else:
            line_out = _unknown(line_in, from_url=True)

        if md:
            url = line_out.split('|')[0].strip()
            txt = '|'.join(line_out.split('|')[1:]).strip()
            line_out = f"[{url}]({txt})"

        return line_out


if __name__ == "__main__":
    txt = '''
https://zeroknowledge.fm/15-2/
https://github.com/paritytech/xcm-format'''
    t = TextDoc(txt)
