"""Apply only two translation tracks; preserve current animations/profiles."""
import bisect,json,shutil,hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1];E=u.EditorAssetLibrary
D=json.loads((O/'translation_patch.json').read_text());REV=D['revision']
ROOT='/Game/Weapons/Super90/Speedloader20261007/Animations/'
paths={ROOT+c['name']:c for c in D['clips']}
profiles={f:'/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_'+f for f in D['profile_offsets']}
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('PIE is active; no animation packages changed')
targets=set(paths)|set(profiles.values())
dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name() in targets]
if dirty:raise RuntimeError('Preserve unsaved target assets: '+str(dirty))
receipt=dict(completed=False,revision=REV,saved=[],translation_bones=D['write_bones'],fit=D['fit'],runtime_tested=False)
def record():(O/'save_receipt.json').write_text(json.dumps(receipt,indent=2))
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def file_for(obj):return P/'Content'/(obj.get_path_name().split('.')[0].removeprefix('/Game/')+'.uasset')
def backup(obj):
    src=file_for(obj);dst=O/'Before'/src.relative_to(P)
    if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def save(obj):
    E.set_metadata_tag(obj,'Super90R24BoltRearStop',REV)
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Cannot save '+obj.get_path_name())
    receipt['saved'].append(obj.get_path_name())
    receipt.setdefault('sha256',{})[obj.get_path_name()]=hashlib.sha256(file_for(obj).read_bytes()).hexdigest();record()
def sample(track,time):
    ts=track['times'];vs=track['values'];k=max(0,min(len(ts)-1,bisect.bisect_right(ts,time)-1));j=min(k+1,len(ts)-1)
    alpha=max(0,min(1,(time-ts[k])/(ts[j]-ts[k]))) if j!=k else 0
    a=vs[k*10:k*10+10];b=vs[j*10:j*10+10]
    # The production loader delta tracks are 60 Hz. Never interpolate rotations
    # with component lerp; require matching keys and leave their values intact.
    if alpha>1e-5 and alpha<1-1e-5:raise RuntimeError('Grip source sampling changed; preserve current profile')
    return list(b if alpha>.5 else a)

mesh=load('/Game/Weapons/Super90/Cransh20261006/SK_Super90_V7')
opt=u.AnimPoseEvaluationOptions();opt.evaluation_type=u.AnimDataEvalType.SOURCE;opt.optional_skeletal_mesh=mesh
prepared=[];profile_prepared=[]
for path,spec in paths.items():
    asset=load(path)
    if E.get_metadata_tag(asset,'Super90R24BoltRearStop')==REV:continue
    if 'LoaderR23' not in E.get_metadata_tag(asset,'Super90SpeedloaderSource'):
        raise RuntimeError('Loader base changed since authoring; preserve '+path)
    count=asset.get_editor_property('data_model_interface').get_number_of_keys()
    patch=D['base_offsets'][spec['branch']]
    if count!=len(patch['hand_l']) or abs(asset.get_play_length()-spec['duration'])>.0001:
        raise RuntimeError('Loader clock changed; preserve '+path)
    tracks={n:[[],[],[]] for n in D['write_bones']}
    for frame in range(count):
        pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,frame/60.,opt)
        for n,output in tracks.items():
            local=u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.LOCAL)
            d=patch[n][frame]
            output[0].append(u.Vector(local.translation.x+d[0],local.translation.y+d[1],local.translation.z+d[2]))
            output[1].append(local.rotation);output[2].append(local.scale3d)
    prepared.append((asset,tracks))
for family,path in profiles.items():
    asset=load(path)
    if E.get_metadata_tag(asset,'Super90R24BoltRearStop')==REV:continue
    payload=dict(family=str(asset.get_editor_property('family')),clips=[]);retained={};found=[]
    for row in asset.get_editor_property('clips'):
        base=row.get_editor_property('base').get_path_name();package=base.split('.')[0]
        tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in row.get_editor_property('tracks')]
        old=row.get_editor_property('retained')
        if old:retained[base]=old.get_path_name()
        if package in paths:
            if old:raise RuntimeError('Loader switched to retained animation; preserve '+path)
            offsets=D['profile_offsets'][family][paths[package]['branch']]
            for bone,values in offsets.items():
                existing=next((t for t in tracks if t['bone']==bone),None)
                replacement=dict(bone=bone,times=[f/60. for f in range(len(values))],values=[])
                for f,delta in enumerate(values):
                    v=sample(existing,f/60.) if existing else [0.,0.,0.,0.,0.,0.,1.,0.,0.,0.]
                    for axis in range(3):v[axis]+=delta[axis]
                    replacement['values'].extend(v)
                if existing:tracks[tracks.index(existing)]=replacement
                else:tracks.append(replacement)
            found.append(package)
        payload['clips'].append(dict(base=base,duration=float(row.get_editor_property('duration')),tracks=tracks))
    if set(found)!=set(paths):raise RuntimeError('Loader entries missing; preserve '+path)
    profile_prepared.append((asset,payload,retained))
# Prepare the whole scoped batch before any write. Non-target profile entries,
# including the current R7 melee, are carried forward from the loaded asset.
for asset,_ in prepared:backup(asset)
for asset,_,_ in profile_prepared:backup(asset)
record()
for asset,tracks in prepared:
    ctl=asset.get_editor_property('controller');ctl.open_bracket('R24 receiver-contained bolt pull and matching palm translation',False)
    try:
        for n,(position,rotation,scale) in tracks.items():
            if not ctl.set_bone_track_keys(n,position,rotation,scale,False):raise RuntimeError('Cannot write '+n)
    finally:ctl.close_bracket(False)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(asset):raise RuntimeError('Animation compression failed')
    save(asset)
for asset,payload,retained in profile_prepared:
    if not asset.set_shared_clips_from_json(json.dumps(payload)):raise RuntimeError('Cannot save '+asset.get_path_name())
    if retained:
        rows=list(asset.get_editor_property('clips'))
        for i,row in enumerate(rows):
            path=row.get_editor_property('base').get_path_name()
            if path in retained:row.set_editor_property('retained',load(retained[path]));rows[i]=row
        asset.set_editor_property('clips',rows)
    receipt.setdefault('profiles',{})[asset.get_path_name()]={'clip_count':len(payload['clips']),'rack_entries_updated':8}
    save(asset)
receipt['completed']=True;record()
print('SUPER90_R24_SAVED',len(receipt['saved']),'assets; gameplay not run',flush=True)
