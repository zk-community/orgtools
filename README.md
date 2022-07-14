# tools
Shared lib for generic tools used to manage zeroknowledge.fm

## Usage

```
$> git clone git@github.com:zk-community/orgtools.git
$> cd orgtools
$> pip install -r requirements.txt
$> python3

Python 3.9.12 ...
>>> import rssdump
>>> # Backup the entire zeroknowledge podcast feed
>>> furl = 'https://feeds.fireside.fm/zeroknowledge/rss'
>>> feed = rssdump.FeedParser(furl, quiet=False)
>>> feed.save()
```

All files will saves to the current working directy in a folder called (default) `Feeds_Fireside_Fm_Zeroknowledge_Rss-out`

Rerunning the same commands will download only the latest episodes, not yet downloaded (cached).

That's it!
