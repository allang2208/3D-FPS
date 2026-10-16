"""Record the stock save/export that preceded the import-metadata API error."""
import json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1]
C=json.loads((O/'inputs.json').read_text());row=C['meshes']['M16_stock'];path=row['path']
if (O/'install_receipt.json').exists():raise RuntimeError('Receipt already exists')
if not (O/'Final/M16_stock.fbx').exists():raise RuntimeError('Export did not complete')
digest=hashlib.sha256((P/'Content'/(path.removeprefix('/Game/')+'.uasset')).read_bytes()).hexdigest()
(O/'install_receipt.json').write_text(json.dumps({'meshes':{'M16_stock':{'path':path,'saved':True,'sha256':digest,'source_sha256':row['sha256'],'tangent_algorithm':'StandardMikkT','recovery':'Save and export completed before unsupported update_filename_only call; editor metadata is checked on resume'}},'complete':False,'gameplay_tested':False},indent=2),encoding='utf-8')
