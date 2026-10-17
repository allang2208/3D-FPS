"""Save the Hundred-Eyed Slag donor sweep on Warden, keeping the current body."""
import unreal as u
import json, shutil
from pathlib import Path

BASE=Path(__file__).resolve().parents[1]
P=BASE/'V12HundredEyeSweep'
DEST='/Game/Monsters/NightWarden/V09Melee/HundredEyeSweepV12'
ENTRY='/Game/Monsters/NightWarden/BP_NightWarden'
E=u.EditorAssetLibrary
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
 if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
  raise RuntimeError('End PIE before saving the new Warden sweep')
 if any(p.get_path_name().startswith('/Game/Monsters/NightWarden') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
  raise RuntimeError('Preserve unsaved Warden assets')
manifest=json.loads((P/'Records/melee_manifest.json').read_text(encoding='utf-8'))
tracks=json.loads((P/'Motion/attack_keys.json').read_text(encoding='utf-8'))
bp=u.load_asset(ENTRY)
cdo=u.get_default_object(bp.generated_class())
mesh=cdo.get_editor_property('mesh').get_editor_property('skeletal_mesh')
backup=P/'Records/BP_NightWarden.before_v12.uasset'
if not backup.exists():
 shutil.copy2(BASE.parents[1]/'Content/Monsters/NightWarden/BP_NightWarden.uasset',backup)
report={'stage':'saving_hundred_eye_sweep','complete':False,'saved':[],
 'previous_attack':cdo.get_editor_property('attack_clip').get_path_name(),
 'mesh_preserved':mesh.get_path_name(),'game_tested':False,'rendered':False}
def record():
 (P/'Records/ue_delivery.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def save(asset):
 if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
 report['saved'].append(asset.get_path_name());record()
record()
path=DEST+'/Animations/A_NightWarden_HundredEyeSweep_V12'
if E.does_asset_exist(path):
 clip=u.load_asset(path)
else:
 # The native Rampage output uses 29 fps. A fresh target-skeleton sequence
 # accepts the authored 60 Hz tracks without resampling a populated donor model.
 factory=u.AnimSequenceFactory()
 factory.set_editor_property('target_skeleton',mesh.skeleton)
 factory.set_editor_property('preview_skeletal_mesh',mesh)
 directory,name=path.rsplit('/',1)
 clip=u.AssetToolsHelpers.get_asset_tools().create_asset(name,directory,u.AnimSequence,factory)
if not clip:raise RuntimeError('Cannot create Warden sweep animation')
controller=clip.get_editor_property('controller')
controller.open_bracket('Hundred-Eyed full-body sweep: native limb rotations and original action schedule',False)
try:
 controller.remove_all_bone_tracks(False)
 controller.set_frame_rate(u.FrameRate(numerator=tracks['fps'],denominator=1),False)
 controller.set_number_of_frames(u.FrameNumber(value=tracks['frames']-1),False)
 for name,rows in tracks['keys'].items():
  if not controller.add_bone_curve(name,False):raise RuntimeError('Cannot add bone '+name)
  if not controller.set_bone_track_keys(name,[u.Vector(*r['p']) for r in rows],[u.Quat(*r['q']) for r in rows],[u.Vector(*r['s']) for r in rows],False):
   raise RuntimeError('Cannot write bone '+name)
finally:
 controller.close_bracket(False)
clip.set_preview_skeletal_mesh(mesh)
for name,value in [('rate_scale',1.),('loop',False),('enable_root_motion',False),('force_root_lock',False)]:
 clip.set_editor_property(name,value)
E.set_metadata_tag(clip,'NightWarden.Source',manifest['source_asset'])
E.set_metadata_tag(clip,'NightWarden.HundredEyeReference',manifest['hundred_eye_asset'])
E.set_metadata_tag(clip,'NightWarden.MotionStyle',manifest['approach'])
E.set_metadata_tag(clip,'NightWarden.ContactSeconds',str([manifest['contact_start'],manifest['contact_end']]))
u.SystemLibrary.execute_console_command(None,'NightWarden.FinishMotion "'+clip.get_path_name()+'"')
save(clip);save(mesh.skeleton)
bp.modify();cdo.modify()
properties={'attack_clip':clip,'attack_range':manifest['attack_range_cm'],
 'stopping_distance':manifest['stopping_distance_cm'],
 'contact_start':manifest['contact_start'],'contact_end':manifest['contact_end'],
 'facing_lock_time':manifest['facing_lock_time'],'trace_sample_rate':manifest['fps'],
 'trace_radius':manifest['trace_radius_cm'],
 'forearm_trace':[u.Vector(*p) for p in manifest['forearm_trace']],
 'palm_trace':[u.Vector(*p) for p in manifest['palm_trace']]}
for name,value in properties.items():cdo.set_editor_property(name,value)
E.set_metadata_tag(bp,'NightWarden.Version','V12HundredEyeSweep')
E.set_metadata_tag(bp,'NightWarden.Stage','Hundred-Eyed Slag full biped sweep; native joints; 1.4 seconds; current body and yaw retained')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
cdo=u.get_default_object(bp.generated_class())
yaw=cdo.get_editor_property('character_movement').get_editor_property('rotation_rate')
report.update(stage='hundred_eye_sweep_animation_and_ai_saved',complete=True,
 animation=clip.get_path_name(),duration=clip.get_play_length(),blueprint=bp.get_path_name(),
 source=manifest['source_asset'],hundred_eye_reference=manifest['hundred_eye_asset'],
 contact_window=[manifest['contact_start'],manifest['contact_end']],
 attack_range_cm=manifest['attack_range_cm'],stopping_distance_cm=manifest['stopping_distance_cm'],
 trace_radius_cm=manifest['trace_radius_cm'],manual_limb_rotation_corrections=False,
 yaw_degrees_per_second=yaw.yaw,damage=cdo.get_editor_property('attack_damage'),
 idle=cdo.get_editor_property('idle_clip').get_path_name(),walk=cdo.get_editor_property('walk_clip').get_path_name(),
 cloth='No clothing added; preserve the current mesh configuration',
 acceptance='Saved candidate using the user-selected Hundred-Eyed sweep; not a visual or gameplay acceptance')
record()
print('NW12_HUNDRED_EYE_SWEEP_SAVED '+json.dumps(report),flush=True)
