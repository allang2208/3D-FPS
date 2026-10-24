"""Publish the native Kaitlin LOD/simulation setup into owned groom recipes."""
import copy
import json
import runpy
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME'); W=P/'SourceAssets/KaitlinHairLOD20261024'
recipes=json.loads((P/'SourceAssets/KaitlinPlayer20261023/groom_recipes.json').read_text())
native={row['asset']:row for row in recipes}
path=P/'Content/ColdSteelData/player_body.json'; before=path.read_bytes()
body=json.loads(before.decode('utf-8-sig')); head=body['body_variants']['kaitlin']['heads']['kaitlin']
for rows in (head['grooms'],head['hair_styles']['long_straight']['grooms']):
    for row in rows:
        source=native[row['asset']]
        if source['lod_mapping']!=[1,3,5,7]: raise RuntimeError('Native LOD map differs from captured diagnosis.')
        row['lod_mapping']=copy.deepcopy(source['lod_mapping'])
        row['simulation_setup']=copy.deepcopy(source['simulation_setup'])
base=('body_variants','kaitlin','heads','kaitlin')
receipt=runpy.run_path(str(P/'Tools/PlayerBody/config_transaction.py'))['commit'](
    path,before,body,owned_paths=[base+('grooms',),base+('hair_styles','long_straight','grooms')],producer=__file__)
(W/'publication.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('Kaitlin authored groom LOD and simulation setup published; other appearance fields preserved.')
