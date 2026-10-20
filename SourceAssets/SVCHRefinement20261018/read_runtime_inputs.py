"""Read saved SVCh/SVD bind and animation inputs for contact authoring. No game."""
import json
from pathlib import Path
import unreal as u

O = Path(__file__).parent
def xf(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]

meshes={
 'svch':'/Game/Weapons/SVCH/Integrated20261017/SK_SVCH_Manny',
 'svd':'/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock'}
out={'meshes':{},'clips':{}}
for key,path in meshes.items():
    mesh=u.load_asset(path)
    mod=u.SkeletonModifier()
    if not mod.set_skeletal_mesh(mesh): raise RuntimeError(path)
    names=list(mod.get_all_bone_names())
    out['meshes'][key]={'path':path,'names':[str(n) for n in names],
      'parents':[str(mod.get_parent_name(n)) for n in names],
      'local':[xf(mod.get_bone_transform(n,False)) for n in names],
      'component':[xf(mod.get_bone_transform(n,True)) for n in names]}
    del mod
names=out['meshes']['svd']['names']
for role in ['idle','aim','fire','aim_fire','equip','reload','reload_empty','inspect','quick_melee','sprint_enter','sprint_loop','sprint_exit']:
    path='/Game/Weapons/SVDDragunov20260922/Complete20260923/Animations/A_SVD_'+role
    a=u.load_asset(path)
    if not a: continue
    duration=a.get_play_length(); count=round(duration*120)
    frames=[]
    for i in range(count+1):
        frames.append([xf(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,names,min(i/120,duration),False)])
    out['clips'][role]={'path':path,'duration':duration,'fps':120,'frames':frames}
    print('SVCH_INPUT',role,len(frames),flush=True)
(O/'runtime_inputs.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
print('SVCH_INPUTS_SAVED',flush=True)
