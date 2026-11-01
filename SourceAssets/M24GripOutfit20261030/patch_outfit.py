"""Register the current M24 in the active Kaitlin appearance catalog."""
import json,hashlib,copy
from pathlib import Path
O=Path(__file__).resolve().parent
path=O.parents[1]/'Content/ColdSteelData/modular_outfits.json'
before=path.read_bytes();config=json.loads(before)
mesh='/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9.SK_M24_MotionV9'
source='/Game/Weapons/M4HK416Replica/SK_M4_FoldingSights_HK416.SK_M4_FoldingSights_HK416'
profiles=config['body_variants']['kaitlin']['profiles']
prior=copy.deepcopy(profiles.get(mesh));new=copy.deepcopy(profiles[source])
# The derivative uses M4's native arm rest, but M24 owns arm slots 0 and 1.
new['hide_source_materials']=list(config['profiles'][mesh]['hide_source_materials'])
if prior is not None and prior!=new:raise RuntimeError('Existing M24 Kaitlin profile retained for review')
profiles[mesh]=new
(O/'Before/modular_outfits.json').write_bytes(before)
if path.read_bytes()!=before:raise RuntimeError('Concurrent outfit configuration change retained')
tmp=path.with_name('modular_outfits.M24GripOutfit30.tmp')
tmp.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');tmp.replace(path)
(O/'outfit_receipt.json').write_text(json.dumps({'field':['body_variants','kaitlin','profiles',mesh],'before':prior,'after':new,'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'runtime_tested':False},indent=2))
print('M24_KAITLIN_OUTFIT_REGISTERED',mesh)
