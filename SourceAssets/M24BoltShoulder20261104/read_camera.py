import json
from pathlib import Path
import unreal as u

folder=Path(__file__).resolve().parent
reference=u.load_asset('/Game/Weapons/M4ContactImpactFinal/A_AKM_idle')
hierarchy=json.loads((folder.parent/'M24SprintShoulder20261031/game_context.json').read_text())['m4_reference']['bones']
names=list(hierarchy)
poses=u.AnimationLibrary.get_bone_poses_for_time(reference,names,0.,False,None)
def fields(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
scope=u.load_asset('/Game/Weapons/M24/Surface20261027/SM_M24_m24_custom_scope_6x')
optic={}
for name in ('SightRear','SightFront','SightUp'):
    v=scope.find_socket(name).relative_location
    optic[name]=[v.x,v.y,v.z]
result={'m4_bones':hierarchy,'m4_local':dict(zip(names,map(fields,poses))),'scope':optic}
(folder/'camera_source.json').write_text(json.dumps(result))
print('BOLT_CAMERA_SOURCE',len(poses),optic,flush=True)
