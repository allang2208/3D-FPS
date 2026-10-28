import concurrent.futures
import html
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
(ROOT / 'Sources').mkdir(parents=True, exist_ok=True)
PAGES = {
    'MagicSmite': 'https://opengameart.org/content/magic-smite',
    'LaserMagicImpacts': 'https://freesound.org/people/TannerSound/sounds/842627/',
    'MagicalHit': 'https://freesound.org/people/SailorErick/sounds/430769/',
    'MagicSpellSFX': 'https://opengameart.org/content/magic-spell-sfx',
}

def fetch(item):
    key, url = item
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        text = urllib.request.urlopen(req, timeout=35).read().decode('utf-8', errors='replace')
        (ROOT / 'Sources' / (key + '.html')).write_text(text, encoding='utf-8')
        urls = sorted(set(html.unescape(x).replace('\\/', '/') for x in re.findall(r'(?:https?:)?//[^\s<>\"\x27]+?\.(?:wav|mp3|ogg|m4a)(?:\?[^\s<>\"\x27]*)?', text)))
        return {'source': key, 'audio': urls[:12]}
    except Exception as exc:
        return {'source': key, 'error': str(exc)}

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for result in pool.map(fetch, PAGES.items()):
        print(result)
