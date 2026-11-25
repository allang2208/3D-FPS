"""Keep the licensed source archives and prepare the mill's game-resolution PBR maps."""
import json
import os
import shutil
from pathlib import Path
from zipfile import ZipFile

from PIL import Image

HERE = Path(__file__).resolve().parent
LIBRARY = HERE.parents[3] / 'VaultCache/FabLibrary'
OUT = Path(os.environ['WINDMILL_ART']) / 'Exchange'
SCANS = {
    'Hay': ('1c539c16-5e9b-4547-8208-18ff68f60ac5', 2048),
    'Barrow': ('8c26b0e8-ff72-498b-bba2-f43c98643f77', 2048),
    'Fork': ('02264775-629a-4d8b-8b5f-9817ceb8559f', 1024),
    'Stone': ('53db74ab-0ec0-458b-b52c-52260af512ed', 1024),
}


def prepare(role, uid, size):
    archive = next((HERE / 'Quixel').glob('*' + uid[:8] + '/*.zip'), None)
    if not archive:
        cached = next(LIBRARY.glob('*' + uid[:8] + '/*.zip'))
        archive = HERE / 'Quixel' / cached.parent.name / cached.name
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cached, archive)
    folder = OUT / role
    folder.mkdir(parents=True, exist_ok=True)
    with ZipFile(archive) as pack:
        names = pack.namelist()
        def channel(suffix, mode):
            key = next(n for n in names if n.lower().endswith('_' + suffix.lower() + '.jpg'))
            with pack.open(key) as file, Image.open(file) as img:
                return img.convert(mode).resize((size, size), Image.Resampling.LANCZOS)
        for suffix in ('BaseColor', 'Normal'):
            channel(suffix, 'RGB').save(folder / (suffix + '.png'))
        metallic = (channel('Metalness', 'L') if any(n.endswith('_Metalness.jpg') for n in names)
                    else Image.new('L', (size, size)))
        Image.merge('RGB', (channel('AO', 'L'), channel('Roughness', 'L'), metallic)).save(folder / 'ORM.png')
        model = next((n for n in names if n.lower().endswith('.fbx')), None)
        if model:
            (folder / 'Scan.fbx').write_bytes(pack.read(model))
        metadata = json.loads(pack.read(next(n for n in names if n.endswith('.json'))))
    return dict(role=role, listing='https://www.fab.com/listings/' + uid, scan_id=metadata['id'],
                archive=archive.relative_to(HERE).as_posix(), resolution=size)


if __name__ == '__main__':
    sources = [prepare(role, *spec) for role, spec in SCANS.items()]
    (OUT / 'scans.json').write_text(json.dumps(sources, indent=2), encoding='utf-8')
