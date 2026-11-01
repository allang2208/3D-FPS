import unreal as u,json,hashlib,shutil
from pathlib import Path
O=Path(__file__).resolve().parent;data=json.loads((O/'ue_before.json').read_text());names=data['names'];mesh=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9')
def tr(t):
    p,q,s=t.translation,t.rotation,t.scale3d;return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
paths={c['base'] for clips in data['profiles'].values() for c in clips}
paths.update('/Game/Weapons/M24/Bipod20261029/A_M24_Bipod_'+f+'.A_M24_Bipod_'+f for f in ('base','mag10'))
out={}
for path in sorted(paths):
    a=u.load_asset(path);dm=a.get_editor_property('data_model_interface');rate=dm.get_frame_rate();fps=rate.numerator/rate.denominator
    out[path]={'path':path,'fps':fps,'keys':dm.get_number_of_keys(),'poses':{str(i):[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,names,i/fps,False,mesh)] for i in range(dm.get_number_of_keys())}}
(O/'roles_before.json').write_text(json.dumps(out));print('IDLE_RELATED_ROLES',len(out),flush=True)
