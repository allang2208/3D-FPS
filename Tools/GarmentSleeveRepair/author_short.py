"""Extend the established fitted cotton construction to the two legacy branches."""
import json,runpy
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/GarmentSleeveRepair20261018'
scope=runpy.run_path(str(P/'SourceAssets/CharcoalCameraRepair20260930/author.py'))
build=scope['build'];build.__globals__['R']=R/'ShortSleeveAuthoring'
for row in json.loads((R/'inventory.json').read_text())['rows']:
    if row['item']!='ue_field_sweater_charcoal' or row['profile'] not in ('SVD','Super90'):continue
    skin=json.loads(Path(row['native_file']).read_text());skin['materials']=skin['triangle_materials']
    folder=R/'ShortSleeveAuthoring/Before'/row['profile'];folder.mkdir(parents=True,exist_ok=True)
    (folder/'skin.json').write_text(json.dumps(skin,separators=(',',':')))
    (folder/'paths.json').write_text(json.dumps(dict(skin=skin['source'],shirt=row['asset'],skin_sha256=skin['asset_sha256'])))
    build(row['profile'])
    target=R/'Authored'/row['item'];target.mkdir(parents=True,exist_ok=True)
    (target/(row['profile']+'.json')).write_bytes((R/'ShortSleeveAuthoring/Authored'/(row['profile']+'.json')).read_bytes())
