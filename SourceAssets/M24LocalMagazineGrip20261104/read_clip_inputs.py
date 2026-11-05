"""Capture current base animation tracks for composing the profile delta."""
import unreal as u,json,gzip,hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
profiles=json.load(gzip.open(O/'input_profiles.json.gz','rt'))
names=json.load(gzip.open(O.parent/'M24ReloadDonor20261101/before.json.gz','rt'))['names']
host=u.load_asset('/Game/Weapons/M24/MotionMagazine20261027/SK_M24_MotionV9')
def tr(t):
    p,q,s=t.translation,t.rotation,t.scale3d;return [p.x,p.y,p.z,q.x,q.y,q.z,q.w,s.x,s.y,s.z]
clips={};hashes={}
for path in sorted({c['base'] for p in profiles.values() for c in p['clips'] if c['base'].split('.')[-1] in ('A_M24_reload','A_M24_reload_empty')}):
    a=u.load_asset(path);dm=a.get_editor_property('data_model_interface');rate=dm.get_frame_rate();fps=rate.numerator/rate.denominator
    clips[path]={'path':path,'fps':fps,'keys':dm.get_number_of_keys(),'poses':{str(i):[tr(t) for t in u.AnimationLibrary.get_bone_poses_for_time(a,names,i/fps,False,host)] for i in range(dm.get_number_of_keys())}}
    hashes[path]=hashlib.sha256((Path(u.Paths.project_content_dir())/(path[6:].split('.')[0]+'.uasset')).read_bytes()).hexdigest()
with gzip.open(O/'input_clips.json.gz','wt',compresslevel=1) as f:json.dump(clips,f,separators=(',',':'))
(O/'input_clip_hashes.json').write_text(json.dumps(hashes,indent=2))
print('M24_LOCAL_GRIP_BASE_INPUTS',len(clips),flush=True)
