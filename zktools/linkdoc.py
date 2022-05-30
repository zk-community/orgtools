#!/usr/bin/env python
# coding: utf-8
# License: MIT
# Author: Chris Ward <chris@zeroknowledge.fm>
# Simple tool for extracting printable title from a list of links
__app_name__ = "LinkDoc"
__version__ = "0.1"
'''
0.1:
'''

# TODO:
# https://blog.octachart.com/how-to-by-pass-cloudflare-while-scraping
# for eg https://www.rsaconference.com/usa/agenda/session/Proofs%20Without%20Evidence%20Assurance%20on%20the%20Blockchain%20and%20Other%20Applications
# >> Starting new HTTPS connection (1): www.rsaconference.com:443
# >> https://www.rsaconference.com:443 "GET /usa/agenda/session/Proofs%20Without%20Evidence%20Assurance%20on%20the%20Blockchain%20and%20Other%20Applications HTTP/1.1" 403 None
# >> [Please Wait... | Cloudflare](https://www.rsaconference.com/usa/agenda/session/Proofs%20Without%20Evidence%20Assurance%20on%20the%20Blockchain%20and%20Other%20Applications) | rsaconference.com 
# >> https://www.rsaconference.com/usa/agenda/session/Proofs%20Without%20Evidence%20Assurance%20on%20the%20Blockchain%20and%20Other%20Applications | Please Wait... | Cloudflare | rsaconference.com

from IPython.core.debugger import set_trace

from urllib.parse import urlsplit, urlunsplit, urlparse, parse_qs, unquote
import re
from lxml import html
from bs4 import BeautifulSoup
import pprint
import hashlib
import base64

import logging
log_format = '>> %(message)s'
logging.basicConfig(level=logging.DEBUG, format=log_format)
log = logging.getLogger()

import requests
req_log = requests.logging.getLogger()
req_log.setLevel(logging.WARNING)  # Quiet down request API calls from request by default

re_generic_url = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'((?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...  #group 1
        r'localhost|' #localhost...  #group 1
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}))' # ...or ip  #group 1
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.I) 


def hash_url(url, length=10):
    length = 0 if length is None else length
    _ = url.lower()
    _ = str.encode(_)
    _ = hashlib.sha1(_)
    _ = _.hexdigest()
    if length > 0:  # truncate
        _ = _[:length]
    return _


class Links:
    def __init__(self, urls, sort=True, debug=False):
        if debug:
            log.setLevel(logging.DEBUG)
        if isinstance(urls, str):
            urls = re.sub(r'[\n\r]+', '\n', urls.strip())
            urls = [x.strip() for x in urls.split('\n')]
        self.data = {}
        # sort and remove exact dups
        self._urls = sorted(set(urls)) if sort else urls

    def parse(self):
        for k, url in enumerate(self._urls):
            if re.search('t.co/', url):  # expand the url
                new_url = requests.get(url).history[-1].headers['Location'] 
                log.info('Expanded {url} -> {new_url}')
                url = new_url

            if re.search('github.com', url):
                d_link = GithubLink(url).parse().data
            elif re.search('twitter.com', url):
                d_link = TwitterLink(url).parse().data
            elif re.search('zeroknowledge.fm', url):
                d_link = ZeroKnowledgeFMLink(url).parse().data
            elif re.search('youtu\.?be(.com)?', url):
                d_link = YoutubeLink(url).parse().data
            elif re.search('iacr.org|ia.cr|kobi.one', url):
                d_link = IACRLink(url).parse().data
            elif re.search('0xparc.org', url):
                d_link = ZXParcLink(url).parse().data
            else:
                d_link = Link(url).parse().data

            url = self._urls[k] = d_link['url']

            hurl = hash_url(url)
            _id = d_link['_id']
            assert(hurl == _id)

            self.data[_id] = d_link
        return self

    def pprint(self):
        pprint.PrettyPrinter(indent=2).pprint(self.data)


class Link:
    _r = None
    def __init__(self, url, from_path=False):
        self._from_path = from_path
        self.url = url.strip().rstrip('/')

        self._re_url_match = re_generic_url.match(self.url)
        if not self._re_url_match:
            log.error(f"Invalid url: URL({url})")
            raise ValueError(f"Invalid url: {url}")

        self._parsed_url = urlparse(self.url)

        __url_parts = urlsplit(self.url)
        self.hostname = __url_parts.hostname
        self.path = __url_parts.path
        self.fragment = __url_parts.fragment
        self.scheme = __url_parts.scheme
        self.query = __url_parts.query

        self._id = self.__get_url_id()
        self.title_url = self._get_title_from_url()
        self.data = {
                '_id': self._id,
                'url': self.url,
                'title_url': self.title_url,
        }

    def parse(self):
        self.title = self.get_title().strip()
        self.authors = self.get_authors().strip()
        self.pub = self.get_publication().strip()
        self.string = self.get_string(self.url, self.title, self.authors, self.pub)
        self.string = re.sub(r'\s+', ' ', self.string)
        self.markdown = self.get_markdown(self.url, self.title, self.authors, self.pub)
        self.data.update({
                'string': self.string,
                'markdown': self.markdown,
                'title': self.title,
                'authors': self.authors,
                'publication': self.pub,
        })
        return self

    def get_string(self, url, title, authors, pub):
        parts = [x for x in (url, title, authors, pub) if x]
        string = ' | '.join(parts)
        return string

    def get_markdown(self, url, title, authors, pub):
        string = f"[{title}]({url}) | {pub}"
        return string

    def get_authors(self):
        return ''

    def get_publication(self):
        pub = self.hostname
        pub = re.sub(r'www\.', '', pub)
        return pub

    def get_title(self):
        url = self.url
        hostname = self.hostname
        if self._from_path:
            title = self._get_title_from_url()
            title = unquote(title)
        else:
            title = self._scrape_title()
        title = title.title()  # upcase title
        return title

    def __get_url_id(self):
        _id = hash_url(self.url)
        return _id

    def _get_title_from_url(self):
        if self.path:
            title = self.path.rstrip('/')
            title = re.sub(r'[-_/]+', ' ', title)  # replace -_ with spaces
            title = re.sub(r'\s+', ' ', title)  # reduce down multiple spaces to one
        else:
            title = self.hostname
        title = title.strip().capitalize()
        return title

    def _scrape_title(self):
        return self._scrape_html_title()

    def _scrape_html_title(self):
        self._r = requests.get(self.url) if not self._r else self._r  # try loading cached
        soup = BeautifulSoup(self._r.content, 'html.parser')
        try:
            title = soup.find_all(attrs={'property': 'og:title'})[0].get('content')
        except:
            title = soup.title.string if soup.title else ''
        return title

    def pprint(self):
        pprint.PrettyPrinter(indent=4).pprint(self.data)


class ZXParcLink(Link):
    def get_title(self):
        title = self._get_title_from_url()
        return title


# NOTE: in 'tools' category (all github links) drop ` | {pub}`
class GithubLink(Link):
    def get_title(self):
        title = self._scrape_title()
        title = re.sub(r'·', '|', title)
        title = re.sub(r'Release ', 'Update: ', title, re.I)
        title = re.sub(r' \| GitHub', '', title, re.I)
        title = re.sub(r'GitHub - ', '', title, re.I)
        if 'releases/' in self.url:  
            # this is a release link, grab the release info
            v = self.url.split('/')[-1]
            if v not in self.url:
                title = f"{title}  {v}"
        return title

    def get_string(self, url, title, authors, pub):
        string = f"{url} | {title} | {pub}"
        #string = f"{url} | {title}"
        return string

    def get_markdown(self, url, title, authors, pub):
        string = f"[{title}]({url}) | {pub}"
        #string = f"[{title}]({url})"
        return string


class TwitterLink(Link):
    def get_title(self):
        title = self.data['title_url']
        return title

    def get_authors(self):
        authors = self.data['title_url'].split(' ')[0]
        return authors

    def get_string(self, url, title, authors, pub):
        string = f"{url} | Tweet by @{authors}"
        return string

    def get_markdown(self, url, title, authors, pub):
        string = f"[Tweet]({url}) by @{authors}"
        return string


## Zero Knolwedge Validator Blog
## Zk Tech Gitcoin Gr13 Recap | Zero Knowledge Validator Blogmedium.com
# https://medium.com/zero-knowledge-validator/zk-tech-gitcoin-gr13-recap-23f92a2b8c0d


class ZeroKnowledgeFMLink(Link):
    def get_title(self):
        title = self._scrape_title()
        title = re.sub('Episode', 'Ep', title)
        title = re.sub(' - ZK Podcast', '', title, re.I)
        return title

    def get_string(self, url, title, authors, pub):
        string = f"{url} | {title} | {pub}"
        return string

    def get_markdown(self, url, title, authors, pub):
        string = f"[{title}]({url}) | {pub}"
        return string

class YoutubeLink(Link):
    def get_title(self):
        title = self._scrape_yt_title()
        return title

    def get_string(self, url, title, authors, pub):
        if '/watch' in self.url:
            url = re.sub(r'&?ab_channel=[^&]+', '', url)
            #string = f"{url} | {title} by {authors} | {pub}"
            string = f"{url} | {title} by {authors}"
        elif '/playlist' in self.url:
            string = f"{url} | Playlist: {title}"
        else:
            string = f"{url} | {title}"
        return string

    def get_markdown(self, url, title, authors, pub):
        if '/watch' in self.url:
            url = re.sub(r'&?ab_channel=[^&]+', '', url)
            string = f"[{title} by {authors}]({url})"
        elif '/playlist' in self.url:
            string = f"[Playlist: {title}]({url})"
        else:
            string = f"[{title}]({url})"
        return string

    def _get_authors_video(self):
        authors = parse_qs(self._parsed_url.query).get('ab_channel', ['blabla'])[0]
        return authors

    def get_authors(self):
        if '/watch' in self.url:
            authors = self._get_authors_video()
        else:
            authors = ''
        return authors

    def _scrape_yt_title_video(self):
        params = {
            "format": "json",
            "url": self.url}
        _url = "https://www.youtube.com/oembed"
        self._r = requests.get(_url, params=params) if not self._r else self._r  # try loading cached
        if not self._r:
            title = '--No Title Found--'
        else:
            r_json = self._r.json()
            title = r_json.get('title')
        return title

    def _scrape_yt_title(self):
        if '/watch' in self.url:
            title = self._scrape_yt_title_video()
        elif '/playlist' in self.url:
            title = self._scrape_yt_title_video()
        else:
            title = self._scrape_title()
        return title


class IACRLink(Link):
    def __init__(self, url, from_path=True):
        new_url = re.sub('eprint\.kobi\.one', 'ia.cr', url, re.I)
        new_url = re.sub('eprint\.iacr\.org', 'ia.cr', url, re.I)
        log.info(f'Updating {url} -> {new_url}')
        super().__init__(new_url, from_path)
        
    def get_authors(self):
        l_authors = self._scrape_iacr_param('citation_author')
        def abbr(x):
            parts = x.split(' ')
            abbr = x[0][0]
            name = abbr + '. ' + ' '.join(parts[1:])
            return name
        authors = ', '.join([abbr(x) for x in l_authors])
        return authors

    def get_title(self):
        title = self._scrape_title()
        title = re.sub('Zero[- ]Knowledge Proof(s)?', 'ZKP', title)
        #title = scrape_iacr_param(line_in, 'citation_title')
        return title

    def get_string(self, url, title, authors, pub):
        edition = self.title_url.replace(' ', '/')
        #string = f"{url} | ({edition}) {title} by {authors} | {pub}"
        string = f"{url} | ({edition}) {title} by {authors}"
        return string
        #return f'{url} | {title} by {authors} | IACR - {ed}'

    def _scrape_iacr_param(self, attr):
        attrs = {'name': attr}
        self._r = requests.get(self.url) if not self._r else self._r  # try loading cached
        soup = BeautifulSoup(self._r.content, 'html.parser')
        _items = soup.find_all(attrs=attrs)
        items = [x.get('content') for x in _items]
        return items

    def get_markdown(self, url, title, authors, pub):
        edition = self.title_url.replace(' ', '/')
        string = f"[{title}]({url}) by {authors}"
        #string = f"[Paper {edition}: {title}]({url}) by {authors} | {pub}"
        return string

if __name__ == "__main__":
    print ("HELLO WORLD")
