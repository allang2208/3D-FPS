"""Bake only the measured finger-joint rotations; preserve original keys/timing/settings."""
import json,math,hashlib,shutil,bisect
from pathlib import Path
import unreal as u
P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/ModularOutfit20260926/FingerlessHuntV2';ROOT=R/globals().get('CORRECTION_DIRECTORY','FingerClearance');BEFORE=ROOT/'Before';BEFORE.mkdir(exist_ok=True)
manifest=json.loads((ROOT/'manifest.json').read_text());receipt_path=ROOT/'installed.json';receipt=json.loads(receipt_path.read_text()) if receipt_path.exists() else {}
cfg=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'));profiles={v['rig_profile']:k for k,v in cfg['profiles'].items()}
def disk(asset):return P/'Content'/(asset.split('.')[0].removeprefix('/Game/')+'.uasset')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pack(tr):return dict(p=[tr.translation.x,tr.translation.y,tr.translation.z],q=[tr.rotation.x,tr.rotation.y,tr.rotation.z,tr.rotation.w],s=[tr.scale3d.x,tr.scale3d.y,tr.scale3d.z])
def angle_at(t,times,values):
    i=max(0,min(len(times)-2,bisect.bisect_right(times,t)-1));a=(t-times[i])/max(times[i+1]-times[i],1e-8);a=max(0,min(1,a))
    return values[i]*(1-a)+values[i+1]*a
def delta_at(t,times,c):
    i=max(0,min(len(times)-2,bisect.bisect_right(times,t)-1));alpha=max(0,min(1,(t-times[i])/max(times[i+1]-times[i],1e-8)))
    def key(j):
        angle=math.radians(c['angles'][j])*.5;axis=c.get('axes',[c['axis']]*len(times))[j]
        return [axis[0]*math.sin(angle),axis[1]*math.sin(angle),axis[2]*math.sin(angle),math.cos(angle)]
    a=key(i);b=key(i+1);dot=sum(x*y for x,y in zip(a,b))
    if dot<0:b=[-v for v in b];dot=-dot
    if dot>.9995:q=[x*(1-alpha)+y*alpha for x,y in zip(a,b)]
    else:
        theta=math.acos(max(-1,min(1,dot)));x=math.sin((1-alpha)*theta)/math.sin(theta);y=math.sin(alpha*theta)/math.sin(theta);q=[v*x+w*y for v,w in zip(a,b)]
    length=math.sqrt(sum(v*v for v in q));return u.Quat(*[v/length for v in q])
for entry in manifest:
    path=entry['asset'];data=json.loads((ROOT/(entry['profile']+'__'+entry['label']+'.json')).read_text())
    expected=receipt.get(path,{}).get('after_sha256',data['source_sha256'])
    if sha(disk(path))!=expected:raise RuntimeError('Animation changed since clearance sampling: '+path)
    if path in receipt:continue
    if data['remaining_sample_cross_mm']>.05:raise RuntimeError('Unresolved finger contact: '+path)
    asset=u.load_asset(path);mesh=u.load_asset(profiles[data['profile']]);model=asset.get_editor_property('data_model_interface');count=model.get_number_of_keys();duration=asset.get_play_length()
    opts=u.AnimPoseEvaluationOptions();opts.evaluation_type=u.AnimDataEvalType.SOURCE;opts.optional_skeletal_mesh=mesh
    before={bn:[] for bn in data['corrections']};after={bn:[] for bn in data['corrections']}
    for i in range(count):
        time=duration*i/max(1,count-1);pose=u.AnimPoseExtensions.get_anim_pose_at_time(asset,time,opts)
        for bn,correction in data['corrections'].items():
            tr=u.AnimPoseExtensions.get_bone_pose(pose,bn,u.AnimPoseSpaces.LOCAL);before[bn].append(pack(tr))
            delta=delta_at(time,data['times'],correction)
            tr.rotation=tr.rotation*delta;after[bn].append(pack(tr))
    backup=BEFORE/'Packages'/disk(path).relative_to(P/'Content');backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():shutil.copy2(disk(path),backup)
    (BEFORE/(entry['profile']+'__'+entry['label']+'_tracks.json')).write_text(json.dumps(dict(asset=path,duration=duration,keys=count,before=before,after=after),separators=(',',':')))
    controller=asset.get_editor_property('controller')
    if controller is None:controller=u.AnimDataController();controller.set_model(model)
    controller.open_bracket('Finger clearance: preserve grip roots, relax measured palm penetration',False)
    try:
        for bn,keys in after.items():
            if not controller.set_bone_track_keys(bn,[u.Vector(*v['p']) for v in keys],[u.Quat(*v['q']) for v in keys],[u.Vector(*v['s']) for v in keys],False):raise RuntimeError('Cannot write '+bn)
    finally:controller.close_bracket(False)
    u.EditorAssetLibrary.set_metadata_tag(asset,'FingerClearanceRevision','20260926')
    asset.modify()
    if not (u.EditorLoadingAndSavingUtils.save_packages([asset.get_outer()],False) or u.EditorAssetLibrary.save_loaded_asset(asset,False)):raise RuntimeError('Cannot save '+path)
    receipt[path]=dict(after_sha256=sha(disk(path)),before_sha256=data['source_sha256'],bones=list(after),keys=count,duration=duration,max_degrees=data['max_angle'])
    receipt_path.write_text(json.dumps(receipt,indent=2));print('FINGER_CLEARANCE_SAVED',path,flush=True)
print('FINGER_CLEARANCE_INSTALL_COMPLETE',len(receipt),flush=True)
