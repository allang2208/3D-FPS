"""Prepare the project's OFL faces and keep their provenance beside the staged fonts."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from urllib.request import Request, urlopen
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'Content/UI/GunsmithWorkbench/Fonts'
NOTO_COMMIT = 'f8d157532fbfaeda587e826d4cd5b21a49186f7c'
NOTO_VARIABLE_URL = f'https://raw.githubusercontent.com/notofonts/noto-cjk/{NOTO_COMMIT}/Sans/Variable/TTF/Subset/NotoSansSC-VF.ttf'
GLYPH_COMMITS = {
    'googlefonts/noto-emoji': '8998f5dd683424a73e2314a8c1f1e359c19e8742',
    'google/fonts': '83c62e30d87daa70216dab6b984d00d20d96d585',
}
GLYPH_FILES = [
    ('googlefonts/noto-emoji', 'fonts/NotoColorEmoji.ttf', 'NotoColorEmoji.ttf'),
    ('googlefonts/noto-emoji', 'fonts/LICENSE', 'NotoColorEmoji-OFL.txt'),
    ('google/fonts', 'ofl/notosanssymbols/NotoSansSymbols%5Bwght%5D.ttf', 'NotoSansSymbols-VF.ttf'),
    ('google/fonts', 'ofl/notosanssymbols/OFL.txt', 'NotoSansSymbols-OFL.txt'),
    ('google/fonts', 'ofl/notosanssymbols2/NotoSansSymbols2-Regular.ttf', 'NotoSansSymbols2-Regular.ttf'),
    ('google/fonts', 'ofl/notosanssymbols2/OFL.txt', 'NotoSansSymbols2-OFL.txt'),
]

def read(url):
    with urlopen(Request(url, headers={'User-Agent': 'FPSGAME-font-preparation'}), timeout=90) as response:
        return response.read()

def prepare_semibold(source):
    from fontTools.ttLib import TTFont
    from fontTools.varLib.instancer import instantiateVariableFont

    font = TTFont(BytesIO(source), recalcTimestamp=False)
    instantiateVariableFont(font, {'wght': 600}, inplace=True)
    names = {1: 'Noto Sans SC SemiBold', 2: 'Regular', 3: 'FPSGAME-NotoSansSC-SemiBold',
             4: 'Noto Sans SC SemiBold', 6: 'NotoSansSC-SemiBold',
             16: 'Noto Sans SC', 17: 'SemiBold'}
    for record in font['name'].names:
        if record.nameID in names:
            record.string = names[record.nameID].encode(record.getEncoding())
    target = OUT / 'NotoSansSC-SemiBold.ttf'
    output = BytesIO()
    font.save(output)
    data = output.getvalue()
    temp = target.with_suffix('.generating')
    temp.write_bytes(data)
    temp.replace(target)
    return dict(file=target.name, url=NOTO_VARIABLE_URL, commit=NOTO_COMMIT,
                source_sha256=hashlib.sha256(source).hexdigest(), weight=600,
                bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                license='SIL OFL 1.1', modified=True)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    commits = {
        'notofonts/noto-cjk': NOTO_COMMIT,
        'JetBrains/JetBrainsMono': '19371302b95d218af43299bce79ddbddd0bc364d',
        **GLYPH_COMMITS,
    }
    entries = [
        ('notofonts/noto-cjk', 'Sans/SubsetOTF/SC/NotoSansSC-Regular.otf', 'NotoSansSC-Regular.otf'),
        ('notofonts/noto-cjk', 'Sans/SubsetOTF/SC/NotoSansSC-Medium.otf', 'NotoSansSC-Medium.otf'),
        ('notofonts/noto-cjk', 'Sans/SubsetOTF/SC/NotoSansSC-Bold.otf', 'NotoSansSC-Bold.otf'),
        ('notofonts/noto-cjk', 'Sans/LICENSE', 'NotoSansSC-OFL.txt'),
        ('JetBrains/JetBrainsMono', 'fonts/ttf/JetBrainsMono-Regular.ttf', 'JetBrainsMono-Regular.ttf'),
        ('JetBrains/JetBrainsMono', 'fonts/ttf/JetBrainsMono-Medium.ttf', 'JetBrainsMono-Medium.ttf'),
        ('JetBrains/JetBrainsMono', 'fonts/ttf/JetBrainsMono-Bold.ttf', 'JetBrainsMono-Bold.ttf'),
        ('JetBrains/JetBrainsMono', 'OFL.txt', 'JetBrainsMono-OFL.txt'),
        *GLYPH_FILES,
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
    manifest.append(prepare_semibold(read(NOTO_VARIABLE_URL)))
    (OUT / 'provenance.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))

if __name__ == '__main__':
    main()
