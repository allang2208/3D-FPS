"""Publish only the four existing third-person heavy-release animations."""
import json,shutil,hashlib,math
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;TASK=P.parent;ROOT=TASK.parents[1]
baseline=json.loads((P/'read-receipt.json').read_text())['assets']
previous=json.loads((P/'saved-assets.json').read_text()) if (P/'saved-assets.json').exists() else {}
targets={info['path'].split('.')[0] for rows in baseline.values() for info in rows.values()}
dirty={a.get_path_name() for a in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if targets.intersection(dirty):raise RuntimeError('Target animation has unsaved changes; retained')
for label,rows in baseline.items():
    for role,info in rows.items():
        disk=ROOT/'Content'/(info['path'].split('.')[0].removeprefix('/Game/')+'.uasset')
        expected=previous.get(label,{}).get(role,{}).get('sha256',info['sha256'])
        if hashlib.sha256(disk.read_bytes()).hexdigest()!=expected:raise RuntimeError('Target changed since read: '+str(disk))

def changed(a,b):
    tr=max(abs(a[j]-b[j]) for j in (0,1,2,7,8,9))
    rotation=min(max(abs(a[j]-b[j]) for j in range(3,7)),max(abs(a[j]+b[j]) for j in range(3,7)))
    return max(tr,rotation)>1.e-7

receipt={}
for label in ('Jason','Kaitlin'):
    data=json.loads((P/(label+'-moves.json')).read_text());before=json.loads((P/(label+'-source.json')).read_text());receipt[label]={}
    for role,frames in data['clips'].items():
        old=before['clips'][role]['frames'];path=baseline[label][role]['path'].split('.')[0];clip=u.load_asset(path)
        if not clip or len(old)!=len(frames) or abs(clip.get_play_length()-(len(frames)-1)/60)>.0001:raise RuntimeError('Timing mismatch '+path)
        edits=[]
        for i,bone in enumerate(data['names']):
            if not any(changed(a[i],b[i]) for a,b in zip(frames,old)):continue
            if any(changed(a[i],b[i]) for a,b in zip(frames[:42],old[:42])):raise RuntimeError('Cut/low hold changed '+bone)
            if bone in ('upperarm_r','upperarm_l','lowerarm_r','lowerarm_l','hand_r','hand_l'):
                if max(abs(a[i][j]-b[i][j]) for a,b in zip(frames,old) for j in (0,1,2,7,8,9))>1.e-7:raise RuntimeError('Primary bone length changed '+bone)
            edits.append((i,bone))
        disk=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        backup=P/'BeforeAssets'/(path.removeprefix('/Game/')+'.uasset');backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(disk,backup)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation preparation failed '+path)
        controller=clip.get_editor_property('controller');controller.open_bracket('Natural third-person hatchet pull elbow and forearm',False)
        try:
            for i,bone in edits:
                keys=[f[i] for f in frames]
                if not controller.set_bone_track_keys(bone,[u.Vector(*k[:3]) for k in keys],[u.Quat(*k[3:7]) for k in keys],[u.Vector(*k[7:]) for k in keys],False):raise RuntimeError('Track write failed '+bone)
        finally:controller.close_bracket(False)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip) or not u.EditorAssetLibrary.save_loaded_asset(clip,False):raise RuntimeError('Save failed '+path)
        receipt[label][role]=dict(asset=clip.get_path_name(),changed_tracks=[n for _,n in edits],seconds=clip.get_play_length(),sha256=hashlib.sha256(disk.read_bytes()).hexdigest())
        (P/'saved-assets.json').write_text(json.dumps(receipt,indent=2),'utf8')
u.log('THIRD_PERSON_PULL_ANATOMY_SAVED assets=4 first_person_untouched')
