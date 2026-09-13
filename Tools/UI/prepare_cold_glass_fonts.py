"""Fetch unmodified OFL font releases and keep provenance beside staged fonts."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request, urlopen
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Content/UI/GunsmithWorkbench/Fonts'

def read(url):
    with urlopen(Request(url, headers={'User-Agent': 'FPSGAME-font-preparation'}), timeout=90) as response:
        return response.read()

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    commits = {
        'notofonts/noto-cjk': 'f8d157532fbfaeda587e826d4cd5b21a49186f7c',
        'JetBrains/JetBrainsMono': '19371302b95d218af43299bce79ddbddd0bc364d',
    }
    entries = [
        ('notofonts/noto-cjk', 'Sans/SubsetOTF/SC/NotoSansSC-Regular.otf', 'NotoSansSC-Regular.otf'),
        ('notofonts/noto-cjk', 'Sans/SubsetOTF/SC/NotoSansSC-Medium.otf', 'NotoSansSC-Medium.otf'),
        ('notofonts/noto-cjk', 'Sans/LICENSE', 'NotoSansSC-OFL.txt'),
        ('JetBrains/JetBrainsMono', 'fonts/ttf/JetBrainsMono-Regular.ttf', 'JetBrainsMono-Regular.ttf'),
        ('JetBrains/JetBrainsMono', 'fonts/ttf/JetBrainsMono-Medium.ttf', 'JetBrainsMono-Medium.ttf'),
        ('JetBrains/JetBrainsMono', 'OFL.txt', 'JetBrainsMono-OFL.txt'),
    ]
    def download(entry):
        repo, path, name = entry
        url = f'https://raw.githubusercontent.com/{repo}/{commits[repo]}/{path}'
        data = read(url)
        if name.endswith('.txt'):
            assert b'SIL OPEN FONT LICENSE' in data
        else:
            assert data[:4] in (b'OTTO', b'\x00\x01\x00\x00'), name
        (OUT / name).write_bytes(data)
        return dict(file=name, url=url, commit=commits[repo], bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), license='SIL OFL 1.1', modified=False)
    with ThreadPoolExecutor(max_workers=6) as pool:
        manifest = list(pool.map(download, entries))
    (OUT / 'provenance.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
