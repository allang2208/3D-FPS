"""Capture the effective near-side hand for each current equip and idle pose."""
from pathlib import Path
import unreal as u, json,gzip,hashlib
O=Path(__file__).resolve().parent;D=json.loads((O/'live_source.json').read_text())
P=O.parents[1];mesh=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9')
parents=json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())['parents']
def desc(n,ancestor):
    while n:
        if n==ancestor:return True
        n=parents[n]
    return False
arm=[n for n in parents if desc(n,'clavicle_r')]
needed=set(arm+['WPN_root'])
for n in list(needed):
    while parents[n]:
        n=parents[n];needed.add(n)
names=[n for n in parents if n in needed]
def mat(t):
    p,q,s=t.translation,t.rotation,t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
def digest(path):return hashlib.sha256((P/'Content'/(path[6:]+'.uasset')).read_bytes()).hexdigest()
dirty={x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
roles={'equip':D['equip'],'idle':'/Game/Weapons/M24/Hold20261027/Animations/A_M24_idle'}
src={'arm':arm,'parents':{n:parents[n] for n in names},'raw':{},'profiles':{},'paths':{},'sha':{}}
for role,path in roles.items():
    if path in dirty:raise RuntimeError('Dirty '+path)
    seq=u.load_asset(path);src['sha'][path]=digest(path)
    src['raw'][role]=[dict(zip(names,map(mat,u.AnimationLibrary.get_bone_poses_for_time(seq,names,k/30,False,mesh)))) for k in range(17 if role=='equip' else 1)]
if src['sha'][D['equip']]!=D['sha256']:raise RuntimeError('Equip changed after capture')
for family,spec in json.loads((O.parent/'M24BoltShoulder20261104/input_assets.json').read_text()).items():
    path=spec['path'];src['paths'][family]=path
    if path in dirty:raise RuntimeError('Dirty '+path)
    asset=u.load_asset(path);src['profiles'][family]={}
    for clip in asset.get_editor_property('clips'):
        base=clip.get_editor_property('base')
        if base is None:continue
        role=base.get_name().removeprefix('A_M24_')
        if role not in roles:continue
        if base.get_path_name().split('.')[0]!=roles[role] or clip.get_editor_property('retained'):raise RuntimeError('Different base '+path)
        tracks={}
        for tr in clip.get_editor_property('tracks'):
            n=str(tr.get_editor_property('bone'))
            if n in needed:tracks[n]={'times':list(tr.get_editor_property('times')),'values':list(tr.get_editor_property('values'))}
        src['profiles'][family][role]=tracks
with gzip.open(O/'grip_inputs.json.gz','wt',compresslevel=2) as file:json.dump(src,file,separators=(',',':'))
print('EQUIP_HAND_CONTACT_INPUT',len(arm),len(src['profiles']),flush=True)
