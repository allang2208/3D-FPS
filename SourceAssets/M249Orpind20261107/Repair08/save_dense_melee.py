from pathlib import Path
import unreal as u,json,gzip,hashlib,runpy
r=Path(__file__).resolve().parent;project=r.parents[2]
path='/Game/Weapons/M249/Animations/A_M249_quick_melee'
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE blocks save')
if path in {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}:raise RuntimeError('Preserve unsaved melee asset')
file=project/'Content/Weapons/M249/Animations/A_M249_quick_melee.uasset'
if hashlib.sha256(file.read_bytes()).hexdigest()!=(r/'melee_before_dense.sha256').read_text().strip():raise RuntimeError('Concurrent melee change')
clip=u.load_asset(path)
with gzip.open(r/'quick_melee.json.gz','rt') as f:data=json.load(f)
ctl=clip.get_editor_property('controller');ctl.open_bracket('M249 frame-interpolation grip correction',False)
try:
    ctl.set_frame_rate(u.FrameRate(numerator=data['fps'],denominator=1),False)
    ctl.set_number_of_frames(u.FrameNumber(value=round(data['duration']*data['fps'])),False)
    for bone,rows in data['tracks'].items():
        if not ctl.set_bone_track_keys(bone,[u.Vector(*v[:3]) for v in rows],[u.Quat(*v[3:7]) for v in rows],[u.Vector(*v[7:]) for v in rows],False):raise RuntimeError(bone)
finally:ctl.close_bracket(False)
if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip) or not u.EditorAssetLibrary.save_loaded_asset(clip,False):raise RuntimeError('Save failed')
receipt=json.loads((r/'import_receipt.json').read_text());receipt['melee_fps']=data['fps'];receipt['melee_final_sha256']=hashlib.sha256(file.read_bytes()).hexdigest()
(r/'import_receipt.json').write_text(json.dumps(receipt,indent=2))
print('M249_DENSE_MELEE_SAVED',data['fps'],flush=True)
runpy.run_path(str(r/'read_saved_melee.py'))
