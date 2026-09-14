"""Acquire the user's rig and pinned CC0 animation sources without changing originals."""
from pathlib import Path
import concurrent.futures, hashlib, json, re, urllib.request, zipfile

ROOT = Path(__file__).parent
SOURCE = ROOT / 'sources'
SOURCE.mkdir(parents=True, exist_ok=True)
repo = 'Mesh2Motion/mesh2motion-app'
html = urllib.request.urlopen(f'https://github.com/{repo}', timeout=30).read().decode()
commit = re.search(r'"currentOid":"([0-9a-f]{40})"', html).group(1)
items = ['static/animations/human-base-animations.glb',
         'static/animations/human-addon-animations.glb', 'LICENSE-CC0.MD', 'README.md']

def download(path):
    url = f'https://raw.githubusercontent.com/{repo}/{commit}/{path}'
    target = SOURCE / Path(path).name
    if not target.exists():
        target.write_bytes(urllib.request.urlopen(url, timeout=60).read())
    return {'path': str(target), 'url': url, 'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    records = list(pool.map(download, items))
archive = Path('D:/FPS3D/资产/Meshy_AI_Mutant_Zombie_Charact_biped.zip')
model = SOURCE / 'meshy'
model.mkdir(exist_ok=True)
with zipfile.ZipFile(archive) as z:
    for item in z.infolist():
        if not item.is_dir():
            (model / Path(item.filename).name).write_bytes(z.read(item))
manifest = {'animation_repository': repo, 'commit': commit, 'animation_license': 'CC0-1.0',
            'downloads': records, 'user_model': str(archive),
            'user_model_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
            'user_model_license': 'User-provided Meshy creation; separate from CC0 animations',
            'scope': 'Asset authoring, retargeting and UE import only; no runtime testing'}
(ROOT / 'source_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(manifest, indent=2, ensure_ascii=False))
