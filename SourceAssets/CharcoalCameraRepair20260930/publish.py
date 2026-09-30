"""Publish this authorized existing-garment repair without claiming runtime QA."""
import sys
import json
from pathlib import Path

P = Path('D:/FPS3D/FPSGAME')
R = Path(__file__).resolve().parent
sys.path.insert(0, str(P / 'Tools/ModularOutfit'))
from garment_pipeline import read, write, digest, asset_file

path = P / 'Content/ColdSteelData/modular_outfits.json'
before_bytes = path.read_bytes()
config = json.loads(before_bytes.decode('utf-8-sig'))
item = config['items']['ue_field_sweater_charcoal']
expected = read(R / 'before.json')['sources']
saved = read(R / 'saved.json')
if set(saved) != set(expected):
    raise RuntimeError('Not all FP sleeve repairs have been saved')
for profile, source in expected.items():
    receipt = saved[profile]
    if item['rig_meshes'][profile] not in (source, receipt['asset']):
        raise RuntimeError('Concurrent charcoal reference edit: ' + profile)
    if digest(asset_file(source)) != receipt['source_sha256'] or digest(asset_file(receipt['native_skin'])) != receipt['native_skin_sha256']:
        raise RuntimeError('Source asset changed: ' + profile)
    if digest(asset_file(receipt['asset'])) != receipt['asset_sha256']:
        raise RuntimeError('Saved repair asset changed: ' + profile)
    item['rig_meshes'][profile] = receipt['asset']
write(R / 'publication-before.json', json.loads(before_bytes.decode('utf-8-sig')))
if path.read_bytes() != before_bytes:
    raise RuntimeError('Concurrent configuration edit before publication')
temporary = path.with_name('modular_outfits.charcoal-camera.tmp')
write(temporary, config); temporary.replace(path)
write(R / 'published.json', dict(item='ue_field_sweater_charcoal',
    profiles={k: v['asset'] for k, v in saved.items()}, runtime_tested=False,
    scope='20 native FP sleeve rebuilds plus existing SVD fit with revised LODs',
    next_load='Next game session reads these saved references', config_sha256=digest(path)))
print('CHARCOAL_CAMERA_PUBLISHED', len(saved), 'profiles; runtime_tested=False')
