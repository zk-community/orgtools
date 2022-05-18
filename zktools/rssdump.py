#!/usr/bin/env python
# coding: utf-8
# License: MIT
# Author: Chris Ward <chris@zeroknowledge.fm>

__app_name__ = "rss-dump"
__version__ = "0.3.1"
'''
0.1.0: download mp3's and a full xml backup plus json
0.2.0: download cover images & transcripts
0.3.0: download research docs from iacr
0.3.1:
'''

# Archive the zeroknowledge.fm rss feed

from datetime import date
import os
import re
import json
import requests
import sys
from dateutil import parser as dtparse
import feedparser  # // pip install feedparser
import eyed3  # // pip install eyed3

import hashlib
import logging
log_format = ' > %(message)s'
logging.basicConfig(level=logging.DEBUG, format=log_format)
log = logging.getLogger()

# quiet down a little...
logging.getLogger("requests").setLevel(logging.WARNING)

TODAY_ISO = date.today().isoformat()
TODAY_ISO_NAME = TODAY_ISO.replace('-', '')
# feed_json['entries'][0].keys()
# 'title', 'title_detail', 'links', 'link', 'id', 'guidislink',
# 'published', 'published_parsed', 'authors', 'author', 'author_detail',
# 'itunes_episodetype', 'subtitle', 'subtitle_detail', 'itunes_duration',
# 'itunes_explicit', 'image', 'podcast_transcript', 'summary',
# 'summary_detail', 'tags', 'content', 'fireside_playerurl',
# 'fireside_playerembedcode', 'podcast_person'


class FeedParser:
    def __init__(self, rss_url, quiet=True):
        log_lvl = logging.INFO if quiet else logging.DEBUG
        log.setLevel(log_lvl)
        log.debug(f'Setting log level: {log_lvl}')

        # FIXME: move to .set_outdir()
        self.rss_url = rss_url

        # override whatever tempfile.gettempdir() offers .... FIXME cleanup
        # import tempfile
        # tmp_dir = tempfile.gettempdir() # prints the current temporary dir
        self.tmp_dir = './'
        url_name = self._autoname(rss_url)
        self.outpath = os.path.join(self.tmp_dir, f'{url_name}-out')
        log.debug(f'Saving to {self.outpath}')
        # check if a folder exists where to store the backup
        if not os.path.exists(self.outpath):
            # FIXME: redudant? since below we makedirs again?
            os.makedirs(self.outpath)

    def _autoname(self, name, prefix=None, ext=None, x_http=True):
        # Make names readable, for humans and machines
        _name = name.strip()
        _name = re.sub('https?://', '', _name) if x_http else _name
        _name = re.sub(r'[^a-zA-Z0-9_ ./]', '', _name)
        _name = re.sub(r'[./]', '_', _name)
        _name = re.sub(r'Episode', 'Ep', _name)
        _name = re.sub(r'[-\s_]+', '_', _name)
        _name = _name.title()
        _name = f"{prefix}_{_name}" if prefix else _name
        _name = f"{_name}.{ext}" if ext else _name
        return _name

    def hash_file(self, filename):
        # Get a sha256 hash of the file for later reference
        if os.path.isfile(filename) is False:
            raise Exception("File not found for hash operation")
        # make a hash object
        h_sha256 = hashlib.sha256()
        # open file for reading in binary mode
        with open(filename, 'rb') as file:
            # read file in chunks and update hash
            chunk = 0
            while chunk != b'':
                chunk = file.read(1024)
                h_sha256.update(chunk)
        # return the hex digest
        return h_sha256.hexdigest()

    def dump_file(self, data, save_as):
        log.debug(f'Saving data to file: {save_as}')
        # log.debug(f'data: {data}')
        # dump some data to a file on disk
        save_path = os.path.dirname(save_as)
        if save_path:
            if not os.path.exists(save_path):
                log.debug(f"Making dir: {save_path}")
                os.makedirs(save_path)

            with open(save_as, 'w') as f:
                try:
                    json.dump(data, f)
                    print(f'JSON dumped: {save_as}')
                except Exception as error:
                    # FIXME: catch proper exceptions; this might cover issues
                    log.debug(error)
                    with open(save_as, 'w') as f:
                        f.write(data.text)
                        print(f'File saved: {save_as}')
        # FIXME: RETURN FILE HASH
        return

    def download(self, url, save_as='', overwrite=False):
        # Download a url and save the result to disk
        save_as = save_as or self._autoname(url)
        save_path = os.path.dirname(save_as)
        path_exists = os.path.exists(save_as)

        log.info(f'Downloading {url}')
        log.debug(f'... as > {save_as}')
        if path_exists and not overwrite:
            log.debug(f" ... skpping, cached: {save_as}")
        else:
            if not os.path.exists(save_path):
                # FIXME: redudant? since below we makedirs again?
                os.makedirs(save_path)
            resp = requests.get(url)
            with open(save_as, "wb") as f:
                # opening a file handler to create new file
                f.write(resp.content)  # writing content to file
        return self.hash_file(save_as)

    def _walk_entries(self, entries):
        filehashes = {}
        for i in entries:
            pub_dt = dtparse.parse(i['published']).strftime('%Y%m%d')
            title = i['title']
            fn = self._autoname(f'{title}')
            fn_path = os.path.join(self.outpath, fn)
            fn_json = f'{fn_path}/{pub_dt}_{fn}.json'
            fn_mp3 = f'{fn_path}/{pub_dt}_{fn}.mp3'
            fn_img = f'{fn_path}/{pub_dt}_{fn}'  # add ext later
            fn_tra = f'{fn_path}/{pub_dt}_{fn}.txt'
            fn_ep_img = f'{fn_path}/{pub_dt}_{fn}'

            # save the entry as a json
            self.dump_file(i, fn_json)

            # save episode mp3
            urls = [_['href'] for _ in i['links'] if _['rel'] == 'enclosure']
            mp3_url = urls[0] if len(urls) > 0 else None
            mp3_sha256 = self.download(mp3_url, fn_mp3)

            # save episode cover image
            # 'image': {'href': 'https://.../cover.jpg?v=10'}
            img_url = i['image'].get('href', '').split('?')[0]
            img_ext = img_url.split('.')[-1] or 'JPG'
            fn_img = fn_img + '.' + img_ext
            img_sha256 = self.download(img_url, fn_img)

            # Save transcript 'podcast_transcript'
            # 'podcast_transcript':
            # {'url': 'https://.../transcript.txt', 'type': 'text/plain'}
            try:
                tra_url = i['podcast_transcript'].get('url', '').split('?')[0]
            except KeyError:
                log.error(
                    f'^^^ ERR ^^^ Missing key for {title}: podcast_transcript')
            else:
                tra_sha256 = self.download(tra_url, fn_tra)

            # extract out the images stored in the mp3 itself
            # (there is other stuff in there to....)
            # _log = eyed3.utils.log
            # _log.setLevel(logging.WARN)
            # Override the module's logging defaults;
            # it's a bit too noisy, we quiet it down here.
            eyed3.log.setLevel(logging.WARN)
            # print ("!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            audio_file = eyed3.load(fn_mp3)
            # print ("!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            # artist_name = audio_file.tag.artist
            k = 0
            for image in audio_file.tag.images:
                img_path = f"{fn_ep_img}_{k}.jpg"
                if os.path.exists(img_path):
                    log.debug(f"... skipping {img_path} (cached)")
                    continue
                # else
                log.info("Writing image")
                log.debug(f"... {img_path}")
                img_file = open(img_path, "wb")
                k += 1
                img_file.write(image.image_data)
                img_file.close()

            filehashes = {
                    fn_mp3: {'url': mp3_url, 'sha256': mp3_sha256},
                    fn_img: {'url': img_url, 'sha256': img_sha256},
                    fn_tra: {'url': tra_url, 'sha256': tra_sha256},
                    # add images extracted from mp3?
            }

        k = len(entries)
        print(f'{k} entries.')
        return filehashes

    def save(self):
        # Backup the main rss feed / json feed dump

        # Make the archive; save the xml and json converted plus entries mp3
        # FIXME: save other media
        self.rss_xml = requests.get(self.rss_url)
        self.rss_json = feedparser.parse(self.rss_url)

        # these are all entries of the show; all episodes
        entries = self.rss_json['entries']
        # Walk through every RSS entry one by one, get file hashes
        filehashes = self._walk_entries(entries)

        today = TODAY_ISO_NAME
        rss_url_name_xml = self._autoname(self.rss_url, today, ext='xml')
        rss_url_name_json = self._autoname(self.rss_url, today, ext='json')
        rss_filehashes_json = self._autoname('filehashes', today, ext='json')

        # force these to backup new everytime
        self.dump_file(self.rss_xml, rss_url_name_xml)
        self.dump_file(self.rss_json, rss_url_name_json)
        self.dump_file(filehashes, rss_filehashes_json)

        last_title = entries[0]['title']
        log.info(f'Last entry: {last_title}')


# {'links':
# [{'rel': 'alternate', 'type': 'text/html',
#   'href': 'https://eprint.iacr.org/2022/509'}],
# 'link': 'https://eprint.iacr.org/2022/509',
# 'title': '...', 'title_detail': {'type': 'text/plain',
#   'language': None, 'base':
# 'https://eprint.iacr.org/rss/rss.xml', 'value': '...'},
# 'summary': "...", 'summary_detail': {'type': 'text/html', 'language': None,
# 'base': 'https://eprint.iacr.org/rss/rss.xml', 'value': "..."},
# 'id': 'https://eprint.iacr.org/2022/509', 'guidislink': False}
class IACRFeedParser (FeedParser):
    def _walk_entries(self, entries):
        filehashes = {}
        for i in entries:
            title = i['title']

            # save linked document
            url = i['link']
            url_pdf = f"{url}.pdf"

            pub_year, pub_k = url.split('/')[-2:]

            fn = self._autoname(f'{title}')
            fn_path = os.path.join(self.outpath, pub_year)
            fn_json = os.path.join(fn_path, 'json', f'{pub_k}-{fn}.json')
            fn_pdf = os.path.join(fn_path, 'pdf', f'{pub_k}-{fn}.pdf')

            filehashes = {
                'pdf': {'sha256': self.download(url_pdf, fn_pdf)},
                'json': {'sha256': self.dump_file(i, fn_json)}
            }
        k = len(entries)
        log.info(f'{k} entries.')
        return filehashes


if __name__ == "__main__":
    # Backup the entire zeroknowledge podcast feed
    furl = 'https://feeds.fireside.fm/zeroknowledge/rss'
    furl = sys.argv[1] if len(sys.argv) > 1 else furl
    feed = IACRFeedParser(furl, quiet=False)
    feed.save()

    # XML for this feed is different from zk rss
    # furl = 'https://eprint.iacr.org/rss/rss.xml'
