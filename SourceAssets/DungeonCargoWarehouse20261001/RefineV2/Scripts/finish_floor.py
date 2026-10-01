import json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];HALL=ROOT.parent
path=ROOT/'Authored/manifest.json';manifest=json.loads(path.read_text('utf-8'))
runpy.run_path(str(HALL/'Scripts/author_warehouse.py'),init_globals=dict(EXPORT_OUT=ROOT/'Authored',EXPORT_SUFFIX='_V2',EXPORT_KINDS={'FloorMarkings'}))
new=json.loads(path.read_text('utf-8'))['objects'][0]
manifest['objects']=[new if old['kind']=='FloorMarkings' else old for old in manifest['objects']]
path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
