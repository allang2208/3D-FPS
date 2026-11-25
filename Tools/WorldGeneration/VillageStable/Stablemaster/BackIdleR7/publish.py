"""Save the baked loop and bind it to the existing stablemaster on its current body and face."""
from pathlib import Path
import hashlib,json,shutil
import unreal as u
project=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
source=project/'SourceAssets/HillsVillageStable/StablemasterBackIdleR7'
base='/Game/WorldGeneration/TemperateHills/VillageStable'
bp_path=base+'/StablemasterMeshyR3/BP_Stablemaster'
folder=base+'/StablemasterBackIdleR7/Animations'
name='A_Stablemaster_HandsBehindBack_R7'
E=u.EditorAssetLibrary
bp=E.load_asset(bp_path);cdo=u.get_default_object(bp.generated_class());body=cdo.mesh
mesh=body.skeletal_mesh_asset
if not mesh or not mesh.skeleton:raise ValueError('Resident has no bound native skeleton')
bp_file=project/'Content'/(bp_path[6:]+'.uasset')
def hash_file(f):return hashlib.sha256(f.read_bytes()).hexdigest()
before=hash_file(bp_file)
batch=source.resolve().parents[3]/'HillsVillageStable/StablemasterIdleAndMarketR36-20261124'
backup=batch/'BeforeBlueprint'/before/bp_file.name;backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():shutil.copy2(bp_file,backup)
previous=body.get_editor_property('animation_data').anim_to_play
path=folder+'/'+name
if E.does_asset_exist(path):seq=E.load_asset(path)
else:
    factory=u.AnimSequenceFactory();factory.target_skeleton=mesh.skeleton;factory.preview_skeletal_mesh=mesh
    seq=u.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,u.AnimSequence,factory)
if not seq or seq.get_editor_property('skeleton')!=mesh.skeleton:raise ValueError('Wrong target skeleton')
data=json.loads((source/'standing.json').read_bytes());ctl=seq.get_editor_property('controller')
ctl.open_bracket('Fit clasped back idle to the riding coat',False)
try:
    ctl.set_frame_rate(u.FrameRate(data['rate'],1),False);ctl.set_number_of_frames(u.FrameNumber(data['frame_count']),False)
    existing=set(map(str,u.AnimationLibrary.get_animation_track_names(seq)))
    for n,keys in data['tracks'].items():
        if n not in existing:ctl.add_bone_curve(n,False)
        if not ctl.set_bone_track_keys(n,[u.Vector(*k[:3]) for k in keys],[u.Quat(*k[3:7]) for k in keys],[u.Vector(*k[7:]) for k in keys],False):
            raise RuntimeError('Could not set animation track '+n)
finally:ctl.close_bracket(False)
# Hips is the first bone. Its bounded weight shift is part of the pose, not actor travel.
seq.set_editor_property('enable_root_motion',False);seq.set_editor_property('force_root_lock',False);seq.set_editor_property('loop',True)
if not E.save_loaded_asset(seq,False):raise OSError('Animation package did not save')
if before!=hash_file(bp_file):raise RuntimeError('Resident blueprint changed during baking')
bp.modify();cdo.modify();body.modify();body.set_animation_mode(u.AnimationMode.ANIMATION_SINGLE_NODE)
playing=body.get_editor_property('animation_data');playing.anim_to_play=seq;playing.saved_looping=True;playing.saved_playing=True
playing.saved_position=0.;playing.saved_play_rate=1.;body.set_editor_property('animation_data',playing)
if not E.save_loaded_asset(bp,False):raise OSError('Resident blueprint did not save')
(source/'published.json').write_text(json.dumps(dict(blueprint=bp.get_path_name(),body=mesh.get_path_name(),skeleton=mesh.skeleton.get_path_name(),previous_clip=previous.get_path_name() if previous else None,clip=seq.get_path_name(),frames=data['frame_count'],rate=data['rate'],before_sha256=before,after_sha256=hash_file(bp_file),gameplay_test=False),indent=2),encoding='utf-8')
