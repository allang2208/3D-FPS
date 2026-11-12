"""Replace only the Peakwatch sight mesh field after the asset is saved."""
from pathlib import Path
from datetime import datetime
import json,os
P=Path(__file__).resolve().parent;root=P.parents[1]
receipt=json.loads((P/'import-receipt.json').read_text(encoding='utf-8'))
target='/Game/Weapons/WoodSteelLongbow20261026/Scope3to6V12/SM_Highland_Peakwatch3to6.SM_Highland_Peakwatch3to6'
previous=target.replace('/Scope3to6V12/','/Scope3to6V11/')
if receipt['saved']!=target:raise RuntimeError('New revision was not saved')
catalog=root/'Content/ColdSteelData/bow-gunsmith.json';before=catalog.read_bytes()
text=before.decode('utf-8')
if text.count(previous)!=1:raise RuntimeError('Catalog changed or revision already installed')
snapshot=P/'Before'/('bow-gunsmith-publish-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'.json')
snapshot.write_bytes(before)
after=text.replace(previous,target,1).encode('utf-8')
if catalog.read_bytes()!=before:raise RuntimeError('Concurrent catalog write retained')
temp=catalog.with_suffix('.peakwatch-joint.tmp');temp.write_bytes(after);os.replace(temp,catalog)
(P/'catalog-receipt.json').write_text(json.dumps(dict(
    weapon='bow_woodsteel',slot='sight',option='highland_peakwatch_3_6x',
    field='bow_part_sight_mesh',previous=previous,current=target,
    saved=True,runtime_tested=False),indent=2),encoding='utf-8')
print('PEAKWATCH_JOINT_CATALOG_SAVED')
