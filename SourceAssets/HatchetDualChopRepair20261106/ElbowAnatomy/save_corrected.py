"""Save only the six existing third-person animation helper tracks."""
import json,shutil,hashlib
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent;TASK=P.parent;ROOT=TASK.parents[1]
saved=json.loads((TASK/'saved-assets.json').read_text())
readback=json.loads((TASK/'ElbowReview/read-receipt.json').read_text())
previous=json.loads((P/'saved-assets.json').read_text()) if (P/'saved-assets.json').exists() else {}
targets=[saved[label][role]['asset'].split('.')[0] for label in ('Jason','Kaitlin') for role in ('DualCharge','DualRelease','Combo3')]
dirty={a.get_path_name() for a in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(targets):raise RuntimeError('Unsaved third-person animation; retained.')
for label in ('Jason','Kaitlin'):
    for role in ('DualCharge','DualRelease'):
        path=saved[label][role]['asset'].split('.')[0]
        disk=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        expected_hash=previous.get(label,{}).get(role,{}).get('sha256',readback[label]['clips'][role]['sha256'])
        if hashlib.sha256(disk.read_bytes()).hexdigest()!=expected_hash:
            raise RuntimeError('Animation changed since scoped review: '+path)
receipt={}
for label in ('Jason','Kaitlin'):
    data=json.loads((P/(label+'-moves.json')).read_text())
    before=json.loads((P/'Inputs'/(label+'-moves.json')).read_text());receipt[label]={}
    for role,frames in data['clips'].items():
        path=saved[label][role]['asset'].split('.')[0];clip=u.load_asset(path)
        disk=ROOT/'Content'/(path.removeprefix('/Game/')+'.uasset')
        backup=P/'BeforeAssets'/(path.removeprefix('/Game/')+'.uasset');backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():shutil.copy2(disk,backup)
        if not clip or abs(clip.get_play_length()-(len(frames)-1)/60)>.0001:raise RuntimeError('Clip timing mismatch '+path)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Animation not ready '+path)
        changed=[];controller=clip.get_editor_property('controller')
        controller.open_bracket('Anatomical third-person elbow skin support',False)
        try:
            for i,bone in enumerate(data['names']):
                delta=max(abs(a[i][j]-b[i][j]) for a,b in zip(frames,before['clips'][role]) for j in range(10))
                if delta<1.e-7:continue
                if bone in ('upperarm_r','upperarm_l','lowerarm_r','lowerarm_l','hand_r','hand_l'):raise RuntimeError('Primary chain must be preserved '+bone)
                keys=[f[i] for f in frames]
                if not controller.set_bone_track_keys(bone,[u.Vector(*k[:3]) for k in keys],[u.Quat(*k[3:7]) for k in keys],[u.Vector(*k[7:]) for k in keys],False):raise RuntimeError('Track write failed '+bone)
                changed.append(bone)
        finally:controller.close_bracket(False)
        if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip) or not u.EditorAssetLibrary.save_loaded_asset(clip,False):raise RuntimeError('Save failed '+path)
        receipt[label][role]=dict(asset=clip.get_path_name(),changed_tracks=changed,seconds=clip.get_play_length(),sha256=hashlib.sha256(disk.read_bytes()).hexdigest())
        (P/'saved-assets.json').write_text(json.dumps(receipt,indent=2),'utf8')
u.log('THIRD_PERSON_ELBOW_SKIN_SAVED assets=6 first_person_untouched')
