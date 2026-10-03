"""Save the native third-person sword grip; no gameplay or preview is started."""
import hashlib,json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=Path(__file__).resolve().parent
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('Stop PIE before saving the grip')
d=json.loads((R/'grip.json').read_text())
dest='/Game/Characters/JasonPlayer20261003/Grip/A_Jason_SwordGrip'
lib=u.EditorAssetLibrary
if lib.does_asset_exist(dest): raise RuntimeError('Grip destination already exists; keep saved authoring intact')
asset=lib.duplicate_asset(d['body_idle'],dest)
if not asset: raise RuntimeError('Could not create grip clip')
c=asset.get_editor_property('controller')
c.open_bracket('Jason native sword fingers and half-joint support',False)
try:
    c.remove_all_bone_tracks(False)
    c.set_frame_rate(u.FrameRate(30,1),False)
    c.set_number_of_frames(u.FrameNumber(1),False)
    for name,k in d['tracks'].items():
        if not c.add_bone_curve(name,False): raise RuntimeError('Cannot add '+name)
        if not c.set_bone_track_keys(name,[u.Vector(*k['p'])]*2,[u.Quat(*k['q'])]*2,[u.Vector(*k['s'])]*2,False):
            raise RuntimeError('Cannot write '+name)
finally: c.close_bracket(False)
asset.set_preview_skeletal_mesh(u.load_asset(d['body']))
asset.set_editor_property('enable_root_motion',False)
if not lib.save_loaded_asset(asset,False): raise RuntimeError('Could not save grip clip')
path=P/'Content'/Path(dest.removeprefix('/Game/')+'.uasset')
(R/'saved.json').write_text(json.dumps(dict(asset=asset.get_path_name(),saved=True,
    sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    author_sha256=hashlib.sha256((R/'grip.json').read_bytes()).hexdigest(),runtime_tested=False),indent=2))
print('JASON_SWORD_GRIP_SAVED',asset.get_path_name(),flush=True)
