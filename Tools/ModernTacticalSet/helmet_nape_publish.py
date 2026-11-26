"""Publish the nape revision over the current contoured helmet."""
import hashlib
import json
from pathlib import Path
import runpy

project = Path(__file__).resolve().parents[2]
sources = project/'SourceAssets/ModernTacticalSet20261113'
revision = sources/'HelmetNapeR3'
artwork = json.loads((revision/'artwork.json').read_bytes())
saved = json.loads((revision/'saved.json').read_bytes())
for relative,digest in artwork['source_sha256'].items():
    if hashlib.sha256((revision/relative).read_bytes()).hexdigest()!=digest:
        raise RuntimeError('Helmet source changed after rendering inventory and pickup')
icon = Path(artwork['icon']['png'])
if saved.get('icon_sha') != hashlib.sha256(icon.read_bytes()).hexdigest():
    raise RuntimeError('Saved texture and current inventory PNG differ')

previous = (sources/'HelmetContourR2/Icons'/icon.name).read_bytes()
catalog = project/'Content/ColdSteelData'
entry = json.loads((catalog/'items.json').read_bytes())['ue_modern_tactical_helmet']
for target in (catalog/entry['ue_icon'],catalog/'Icons'/icon.name):
    if target.read_bytes() not in (previous,icon.read_bytes()):
        raise RuntimeError(f'Concurrent helmet icon edit at {target}')
runpy.run_path(str(Path(__file__).with_name('helmet_contour_publish.py')),init_globals={
    'HELMET_REVISION':'HelmetNapeR3', 'PREVIOUS_HELMET_WEAR':'HelmetContourR2',
    'PREVIOUS_HELMET_DISPLAY':'HelmetContourR2'})
