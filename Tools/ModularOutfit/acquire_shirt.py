"""Acquire the CC0 sweater source; keep the source license with local authoring inputs."""
from pathlib import Path
import urllib.request, re, zipfile, json, hashlib
ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924')
OUT = ROOT / 'Donor'
OUT.mkdir(parents=True, exist_ok=True)
url = 'https://static.makehumancommunity.org/assets/assetpacks/shirts01.html'
html = urllib.request.urlopen(url, timeout=40).read().decode()
(OUT/'shirts01-source.html').write_text(html, encoding='utf-8')
links = re.findall(r'href="([^"]+\.zip)"', html)
archive = OUT/'shirts01.zip'
if not archive.exists():
    errors=[]
    for link in links:
        try:
            urllib.request.urlretrieve(link, archive)
            break
        except Exception as exc:
            errors.append(str(exc))
    else:
        raise RuntimeError(errors or 'No archive link')
with zipfile.ZipFile(archive) as pack:
    chosen = [n for n in pack.namelist() if 'fisherman_sweater' in n.lower() and not n.endswith('/')]
    for name in chosen:
        target = OUT / Path(name).name
        target.write_bytes(pack.read(name))
(OUT/'provenance.json').write_text(json.dumps({'source':url,'author':'MargaretToigo',
    'asset':'toigo_fisherman_sweater','license':'CC0','archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
    'extracted':chosen,'changes':'Fit to project body, transfer skin weights, derive first-person sleeves, new materials.'},indent=2),encoding='utf-8')
print('SWEATER_SOURCE', chosen)
