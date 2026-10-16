"""Include the current dual-device runtime routes, not only legacy accessories."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
R=json.loads((O/'capture.json').read_text())
helper=(P/'SourceAssets/TelescopicAllGunsAudit20261015/capture.py').read_text(encoding='utf-8')
exec(compile(helper[helper.index('def record():'):helper.index('sms=')],'<graph_helpers>','exec'))
for p in (P/'Content/Weapons/TacticalDevices20260913/DualFit20261008/A762').glob('*.uasset'):
 path='/Game/'+str(p.relative_to(P/'Content').with_suffix('')).replace('\\','/')
 mesh=u.load_asset(path)
 R['assets'][path]={'sha256':hashlib.sha256(disk(path).read_bytes()).hexdigest(),'slots':[{'name':str(s.material_slot_name),'material':material(s.material_interface) if s.material_interface else None} for s in mesh.static_materials]}
for p,m in R['materials'].items():
 if 'sha256' not in m:m['sha256']=hashlib.sha256(disk(p).read_bytes()).hexdigest()
record();print('A762_TACTICAL_CAPTURED',len(R['assets']))
