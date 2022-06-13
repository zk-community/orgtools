#!/usr/bin/env python
# coding: utf-8
# License: MIT
# Author: Chris Ward <chris@zeroknowledge.fm>
# Simple tool for extracting printable title from a list of links
__app_name__ = "Trascript"
__version__ = "0.1"
'''
0.1: Convert transcript texts to srt
'''

# DEBUG
#from IPython.core.debugger import set_trace
#######

import re

import logging
log_format = '>> %(message)s'
logging.basicConfig(level=logging.DEBUG, format=log_format)
log = logging.getLogger()

class Transcript:
    def __init__(self, txt):
        self._txt = txt

    def as_srt(self):
        re_clip_start = re.compile(r'(\d\d:\d\d:\d\d)', re.I)
        re_clip_body = re.compile(r'\):\n?(.+)', re.I)
        titles = self._txt.split('\n\n')
        clips = []
        for i, _t in enumerate(titles):
            _clip_start = re_clip_start.search(_t)
            _clip_start = _clip_start.group(1)
            _clip_end = '00:00:00' if not clips else clips[-1]['start_ts']
            _clip_body = re_clip_body.search(_t)
            _clip_body = _clip_body.group(1)
            _clip = {'id': i, 'start_ts': _clip_start, 'end_ts': _clip_end, 'body': _clip_body}
            clips.append(_clip)
            if i > 0:
                # ripple adjust starts and ends
                clips[i-1]['end_ts'] = clips[i]['start_ts']

        srt = ''
        for c in clips:
            start = c["start_ts"]
            end = c["end_ts"]
            body = c["body"]
            _id = c["id"]
            srt += f'{_id}\n{start} --> {end}\n{body}\n\n'

        return srt

if __name__ == "__main__":
    print ("HELLO WORLD")
