#!/usr/bin/env python
# coding: utf-8
# License: MIT
# Author: Chris Ward <chris@zeroknowledge.fm>
# Simple tool for extracting printable title from a list of links
__app_name__ = "Gists"
__version__ = "0.1"
'''
0.1: Play with Gists by GitHub
'''

# DEBUG
#from IPython.core.debugger import set_trace
#######

import re
import requests

import logging
log_format = '>> %(message)s'
logging.basicConfig(level=logging.DEBUG, format=log_format)
log = logging.getLogger()

def gist_json(gist_id):
    _gist_call_api = f'https://api.github.com/gists/{gist_id}'
    r = requests.get(_gist_call_api)
    r_json = r.json()
    return r_json

class Gist:
    _gist_id = None
    _gist_filename = None
    def __init__(self, gist_id, gist_filename):
        self._configure(gist_id, gist_filename)

    def _configure(self, gist_id, gist_filename):
        self._gist_id = gist_id
        self._gist_filename = gist_filename
        self._gist_json = gist_json(gist_id)

    def content(self):
        data = self._gist_json
        gist = data['files'][self._gist_filename]['content']
        return gist
