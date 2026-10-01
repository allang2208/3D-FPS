"""Local roof update; retain the complete production manifest and editable source."""
import json,runpy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=ROOT/'Authored/manifest.json';before=json.loads(manifest.read_text('utf-8'))
runpy.run_path(str(ROOT/'Scripts/author_warehouse.py'),init_globals={'EXPORT_KINDS':{'RoofRibs'}})
after=json.loads(manifest.read_text('utf-8'));replacements={x['kind']:x for x in after['objects']}
before['objects']=[replacements.get(x['kind'],x) for x in before['objects']]
manifest.write_text(json.dumps(before,indent=2),encoding='utf-8')
