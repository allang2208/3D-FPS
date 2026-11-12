"""Replace only captured female ST6 mesh leaves after all assets are saved."""
import hashlib
import json
import os
import runpy
import tempfile
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
WORK = PROJECT / 'SourceAssets/ST6FemaleCollar20261108'
config_path = PROJECT / 'Content/ColdSteelData/modular_outfits.json'
manifest = json.loads((WORK / 'manifest.json').read_text())
saved = json.loads((WORK / 'saved_assets.json').read_text())
if not saved.get('completed'):
    raise RuntimeError('Save all female ST6 variants before publishing')
patch_hash = hashlib.sha256((WORK / 'collar.json').read_bytes()).hexdigest()
transaction = runpy.run_path(str(PROJECT / 'Tools/PlayerBody/config_transaction.py'))
with transaction['_lock'](PROJECT / 'Saved/ModularOutfitConfigWrites/writer.lock'):
    before = config_path.read_bytes()
    current = json.loads(before.decode('utf-8-sig'))
    text = before.decode('utf-8-sig')
    owned = []
    mapping = {}
    for row in manifest['meshes']:
        record = saved['meshes'][row['source']]
        if record['collar_sha256'] != patch_hash or record['original_sha256'] != row['source_sha256']:
            raise RuntimeError('Saved collar revision does not match authoring inputs')
        source_file = PROJECT / 'Content' / (row['source'].split('.')[0][6:] + '.uasset')
        if hashlib.sha256(source_file.read_bytes()).hexdigest() != row['source_sha256']:
            raise RuntimeError('Original garment changed during production')
        target = record['asset']
        mapping[row['source']] = target
        for selector in row['selectors']:
            value = current
            for part in selector:
                value = value[part]
            if value not in (row['source'], target):
                raise RuntimeError('Female ST6 route changed concurrently: ' + repr(selector))
            text = transaction['_set'](text, tuple(selector), target)
            owned.append(selector)
    result = (b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'') + text.encode('utf-8')
    (WORK / 'Publication').mkdir(exist_ok=True)
    (WORK / 'Publication/before.json').write_bytes(before)
    (WORK / 'Publication/after.json').write_bytes(result)
    with tempfile.NamedTemporaryFile(dir=config_path.parent, prefix='.st6-female-', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(result)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        if config_path.read_bytes() != before:
            raise RuntimeError('Shared outfit file changed; merge from fresh input')
        os.replace(temporary, config_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    (WORK / 'published.json').write_text(json.dumps(dict(status='saved_and_integrated',
        meshes=len(mapping), changed_routes=len(owned), owned_paths=owned, mesh_map=mapping,
        before_sha256=hashlib.sha256(before).hexdigest(), after_sha256=hashlib.sha256(result).hexdigest(),
        runtime_tested=False, git_commit=None, git_push=None), indent=2), encoding='utf-8')
print('ST6_FEMALE_PUBLISHED', len(mapping), 'meshes;', len(owned), 'routes')
