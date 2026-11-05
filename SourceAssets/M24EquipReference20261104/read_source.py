"""Capture the one shared action, its idle sight basis, and equip layer ownership."""
from pathlib import Path
import hashlib, json
import unreal as u
O=Path(__file__).resolve().parent;project=O.parents[1]
host_path='/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9'
equip_path='/Game/Weapons/M24/MotionMagazine20261027/Animations/A_M24_equip'
idle_path='/Game/Weapons/M24/Hold20261027/Animations/A_M24_idle'
ref_path='/Game/Weapons/M4ContactImpactFinal/A_AKM_idle'
profile_paths=json.loads((O.parent/'M24BoltShoulder20261104/input_assets.json').read_text())
dirty={x.get_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for path in [host_path,equip_path,idle_path,ref_path]+[s['path'] for s in profile_paths.values()]:
    if path in dirty:raise RuntimeError('Unsaved input: '+path)
def tr(t):
    p=t.translation;q=t.rotation;s=t.scale3d
    return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
def digest(path):return hashlib.sha256((project/'Content'/(path[6:]+'.uasset')).read_bytes()).hexdigest()
host=u.load_asset(host_path);equip=u.load_asset(equip_path);idle=u.load_asset(idle_path);ref=u.load_asset(ref_path)
hier=json.loads((O.parent/'M24ArmRebuild20261027/source_after.json').read_text())['parents']
refhier=json.loads((O.parent/'M24BoltShoulder20261104/camera_source.json').read_text())['m4_bones']
refidx={v['index']:n for n,v in refhier.items()}
refparents={n:refidx.get(v['parent']) for n,v in refhier.items()}
def chain(parents):
    names=set()
    for n in ['hand_r','WPN_root','WPN_FrontSight','WPN_RearSight']:
        while n:
            names.add(n);n=parents[n]
    return {n:parent for n,parent in parents.items() if n in names}
def snapshot(anim,parents,mesh):
    m=chain(parents);names=list(m)
    return {'parent':m,'raw':dict(zip(names,map(tr,u.AnimationLibrary.get_bone_poses_for_time(anim,names,0,False,mesh))))}
layers={}
for family,spec in profile_paths.items():
    asset=u.load_asset(spec['path'])
    clips={c.get_editor_property('base').get_name():c for c in asset.get_editor_property('clips') if c.get_editor_property('base')}
    def tracks(clip):return {str(t.get_editor_property('bone')):t for t in clip.get_editor_property('tracks')}
    ec=clips['A_M24_equip'];ic=clips['A_M24_idle']
    if ec.get_editor_property('base')!=equip or ec.get_editor_property('retained') or 'VM_Root' in tracks(ec):
        raise RuntimeError('Nonshared root in '+family)
    layers[family]={}
    for n,t in tracks(ic).items():
        if n in chain(hier):
            layers[family][n]=list(t.get_editor_property('values'))[:10]
model=equip.get_editor_property('data_model_interface');fps=model.get_frame_rate();fps=fps.numerator/fps.denominator;num=model.get_number_of_keys()
rootkeys=[tr(u.AnimationLibrary.get_bone_poses_for_time(equip,['VM_Root'],k/fps,False,host)[0]) for k in range(num)]
snap={'equip':equip_path,'sha256':digest(equip_path),'fps':fps,'root':rootkeys,'duration':equip.get_play_length(),'force_root_lock':equip.get_editor_property('force_root_lock'),'enable_root_motion':equip.get_editor_property('enable_root_motion'),'idle':snapshot(idle,hier,host),'reference':snapshot(ref,refparents,None),'profiles':layers}
(O/'live_source.json').write_text(json.dumps(snap,separators=(',',':')))
print('EQUIP_REFERENCE_INPUT',fps,num,len(layers),snap['force_root_lock'],snap['enable_root_motion'],flush=True)
