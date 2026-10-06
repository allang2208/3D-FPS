"""Replace only the RSH Resonance inspect support-arm tracks."""
import bpy,copy,json,shutil,sys
from pathlib import Path
from mathutils import Matrix,Quaternion
O=Path(__file__).parent;S=O.parent;CURRENT=S/'RSH12Foregrips20261004/Profiles'
B=O/'Before';B.mkdir(exist_ok=True)
for name in ('angled.json','RSH12_angled_Editable.blend'):
    if not (B/name).exists():shutil.copy2(CURRENT/name,B/name)
sys.path.insert(0,str(O));sys.path.insert(0,str(S/'RSH12InspectGrip20261004'))
from grip_scene import load,pose,matrix,applied,set_pose
from inspect_support import rewrite_inspect
rig,D,_,meta=load();rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
source=json.loads((B/'angled.json').read_text());result=copy.deepcopy(source)
receipt=rewrite_inspect(rig,D,result)
(O/'profile.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf8')
set_pose(rig,pose(rig,D,result,'idle',D['clips']['idle']['samples'][0]))
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'RSH12_InspectArm_Editable.blend'))
receipt['runtime_tested']=False
(O/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf8')
print('RSH_INSPECT_SUPPORT_AUTHORED',receipt['samples'],flush=True)
