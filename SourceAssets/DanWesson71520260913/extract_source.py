"""Unpack the user's Fab Unity delivery into named local authoring inputs."""
import json, tarfile, shutil
from pathlib import Path

OUT = Path(__file__).parent
VAULT = Path('D:/FPS3D/VaultCache/FabLibrary/Revolver_Model_715-4d975165/unity')
records = []
with tarfile.open(VAULT / 'danwessonmodel715_202237f1.unitypackage', 'r:gz') as archive:
    members = {m.name.rstrip('/'): m for m in archive.getmembers()}
    for key, member in members.items():
        if not key.endswith('/pathname'):
            continue
        name = archive.extractfile(member).read().decode('utf-8').strip()
        asset = members.get(key.rsplit('/', 1)[0] + '/asset')
        if not asset or not asset.isfile():
            continue
        target = (OUT / 'Original' / name).resolve()
        if not target.is_relative_to((OUT / 'Original').resolve()):
            raise ValueError(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.extractfile(asset).read())
        meta = members.get(key.rsplit('/', 1)[0] + '/asset.meta')
        if meta:
            target.with_name(target.name + '.meta').write_bytes(archive.extractfile(meta).read())
        records.append({'file': name, 'bytes': asset.size})
shutil.copy2(VAULT / 'metadata', OUT / 'fab-metadata.json')
(OUT / 'source-files.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
print(json.dumps(records, indent=2))
