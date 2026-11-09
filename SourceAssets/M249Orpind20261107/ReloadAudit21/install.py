"""Publish only the two box reloads and their five profile rows."""
from pathlib import Path
import unreal as u,json,gzip,hashlib,zipfile
r=Path(__file__).resolve().parent;p=r.parents[2];E=u.EditorAssetLibrary
profiles={family:('/Game/Weapons/M249/Bipod/DA_M249_SupportGrip' if family=='base' else '/Game/Weapons/M249/CommonParts20261108/Profiles/DA_M249_'+family) for family in ('base','vertical','canted','prism','angled')}
motions=[json.load(gzip.open(f,'rt')) for f in sorted((r/'Motion').glob('*.json.gz'))]
targets=[m['asset'] for m in motions]+list(profiles.values())
receipt=r/'install_receipt.json';report=dict(saved={},animations=[],profiles=[],complete=False)
def disk(path):return p/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
def load(path):
 a=u.load_asset(path)
 if not a:raise RuntimeError('Missing '+path)
 return a
def save(a):
 if not E.save_loaded_asset(a,False):raise RuntimeError('Save '+a.get_path_name())
 path=a.get_path_name().split('.')[0];report['saved'][path]=hashlib.sha256(disk(path).read_bytes()).hexdigest();receipt.write_text(json.dumps(report,indent=2))
original=json.loads((r/'current_assets.json').read_text())
if not (r/'Before.zip').exists():
 for path in targets:
  if hashlib.sha256(disk(path).read_bytes()).hexdigest()!=original[path]['current']:raise RuntimeError('Changed asset retained '+path)
 with zipfile.ZipFile(r/'Before.zip','w',zipfile.ZIP_DEFLATED) as z:
  for path in targets:z.write(disk(path),str(disk(path).relative_to(p)))
else:
 previous=json.loads(receipt.read_text())['saved'] if receipt.exists() else {}
 for path in targets:
  if hashlib.sha256(disk(path).read_bytes()).hexdigest()!=previous.get(path,original[path]['current']):raise RuntimeError('Changed asset retained '+path)
for data in motions:
    clip=load(data['asset']);ctl=clip.get_editor_property('controller');ctl.open_bracket('M249 anatomical elbow and receiver response',False)
    try:
        ctl.set_frame_rate(u.FrameRate(numerator=data['fps'],denominator=1),False);ctl.set_number_of_frames(u.FrameNumber(value=round(data['duration']*data['fps'])),False)
        for bone,rows in data['tracks'].items():
            if not bone.startswith(('clavicle','upperarm','lowerarm','hand','thumb','index','middle','ring','pinky','ik_hand','WPN_','PKM_','New_')):continue
            if not ctl.set_bone_track_keys(bone,[u.Vector(*v[:3]) for v in rows],[u.Quat(*v[3:7]) for v in rows],[u.Vector(*v[7:]) for v in rows],False):raise RuntimeError('Track '+bone)
    finally:ctl.close_bracket(False)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Compression '+clip.get_path_name())
    save(clip);report['animations'].append(data['asset']);print('M249_REPAIR20_ACTION_SAVED',clip.get_name(),flush=True)
for family,path in profiles.items():
    a=load(path);incoming=json.load(gzip.open(r/(family+'.json.gz'),'rt'))['clips'];keys={c['base'].split('.')[0] for c in incoming};rows=[];kept=[]
    for c in a.get_editor_property('clips'):
        base=c.get_editor_property('base');retained=c.get_editor_property('retained')
        if base.get_path_name().split('.')[0] in keys:continue
        if retained:kept.append((base,retained));continue
        rows.append(dict(base=base.get_path_name(),duration=c.get_editor_property('duration'),tracks=[dict(bone=str(t.get_editor_property('bone')),times=list(t.get_editor_property('times')),values=list(t.get_editor_property('values'))) for t in c.get_editor_property('tracks')]))
    if not a.set_shared_clips_from_json(json.dumps(dict(family=family,clips=rows+incoming))):raise RuntimeError('Profile '+family)
    for base,retained in kept:a.keep_clip(base,retained)
    save(a);report['profiles'].append(path)
report['complete']=True;receipt.write_text(json.dumps(report,indent=2));print('M249_RELOAD21_SAVED',len(report['saved']),flush=True)
