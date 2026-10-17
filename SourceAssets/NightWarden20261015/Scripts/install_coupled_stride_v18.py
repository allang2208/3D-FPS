"""Save the fitted Rampage biped walk and its measured movement speed on existing AI."""
import unreal as u,json,shutil
from pathlib import Path
BASE=Path(__file__).resolve().parents[1];P=BASE/'V18CoupledLocomotion'
DEST='/Game/Monsters/NightWarden/V07WaistStride/CoupledLocomotionV18'
ENTRY='/Game/Monsters/NightWarden/BP_NightWarden';E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before saving the new Warden walk')
    if any(p.get_path_name().startswith('/Game/Monsters/NightWarden') for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved Night Warden assets')
motion=json.loads((P/'Records/motion_manifest.json').read_text(encoding='utf-8'))
tracks=json.loads((P/'Motion/coupled_keys.json').read_text(encoding='utf-8'))
bp=u.load_asset(ENTRY);cdo=u.get_default_object(bp.generated_class())
mesh=cdo.get_editor_property('mesh').get_skeletal_mesh_asset()
if '/V14BareBodyHand/' not in mesh.get_path_name():raise RuntimeError('Preserve unexpected active mesh; Rampage biped stride targets the repaired V14 body')
backup=P/'Records/BP_NightWarden.before_v18.uasset'
if not backup.exists():shutil.copy2(BASE.parents[1]/'Content/Monsters/NightWarden/BP_NightWarden.uasset',backup)
report={'stage':'saving_coupled_stride','complete':False,'saved':[],
    'previous_walk':cdo.get_editor_property('walk_clip').get_path_name(),
    'previous_speed_cm_s':cdo.get_editor_property('walk_speed'),'game_tested':False,'rendered':False}
def record():(P/'Records/ue_delivery.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    report['saved'].append(asset.get_path_name());record()
record();name='A_NightWarden_CoupledStride_V18';path=DEST+'/Animations/'+name
clip=u.load_asset(path) if E.does_asset_exist(path) else None
if not clip:
    factory=u.AnimSequenceFactory();factory.set_editor_property('target_skeleton',mesh.skeleton)
    factory.set_editor_property('preview_skeletal_mesh',mesh)
    clip=A.create_asset(name,DEST+'/Animations',u.AnimSequence,factory)
if not clip:raise RuntimeError('Cannot create Rampage biped animation')
c=clip.get_editor_property('controller');c.open_bracket('Rampage biped locomotion on original Warden bones',False)
try:
    c.remove_all_bone_tracks(False);c.set_frame_rate(u.FrameRate(numerator=60,denominator=1),False)
    c.set_number_of_frames(u.FrameNumber(value=tracks['frames']-1),False)
    for name,rows in tracks['keys'].items():
        if not c.add_bone_curve(name,False):raise RuntimeError('Cannot add bone '+name)
        if not c.set_bone_track_keys(name,[u.Vector(*r['p']) for r in rows],[u.Quat(*r['q']) for r in rows],[u.Vector(*r['s']) for r in rows],False):raise RuntimeError('Cannot write bone '+name)
finally:c.close_bracket(False)
for side,values in tracks['plant_curves'].items():
    curve='NW_Plant_'+side
    if u.AnimationLibrary.does_curve_exist(clip,curve,u.RawCurveTrackTypes.RCT_FLOAT):u.AnimationLibrary.remove_curve(clip,curve)
    u.AnimationLibrary.add_curve(clip,curve)
    u.AnimationLibrary.add_float_curve_keys(clip,curve,[i/tracks['fps'] for i in range(tracks['frames'])],values)
clip.set_preview_skeletal_mesh(mesh)
compression_path=DEST+'/Compression/BCS_NightWarden_PlantPrecision_V18'
compression=u.load_asset(compression_path) if E.does_asset_exist(compression_path) else A.create_asset('BCS_NightWarden_PlantPrecision_V18',DEST+'/Compression',u.AnimBoneCompressionSettings,u.AnimBoneCompressionSettingsFactory())
codec=u.new_object(u.load_class(None,'/Script/Engine.AnimCompress_BitwiseCompressOnly'),outer=compression)
# Engine defaults for this codec: unquantized translations and Float96NoW
# rotations. It keeps nontrivial keys; legacy format fields are not Python-exposed.
compression.set_editor_property('codecs',[codec])
compression.set_editor_property('error_threshold',.001)
compression.set_editor_property('force_below_threshold',True)
save(compression)
clip.set_editor_property('bone_compression_settings',compression)
clip.set_editor_property('allow_frame_stripping',False)
platform_rate=clip.get_editor_property('platform_target_frame_rate')
platform_rate.set_editor_property('default',u.FrameRate(numerator=tracks['fps'],denominator=1))
for name,value in [('rate_scale',1.),('loop',True),('enable_root_motion',False),('force_root_lock',False)]:clip.set_editor_property(name,value)
E.set_metadata_tag(clip,'NightWarden.Source','Paragon Rampage Jog_Biped_Fwd')
E.set_metadata_tag(clip,'NightWarden.Attribution','Epic Games Paragon Rampage; existing project content; adapted on original Warden skeleton')
E.set_metadata_tag(clip,'NightWarden.NominalSpeedCmS',str(motion['nominal_speed_cm_s']))
u.SystemLibrary.execute_console_command(None,'NightWarden.FinishMotion "'+clip.get_path_name()+'"')
save(clip);save(mesh.skeleton)
bp.modify();cdo.modify();cdo.set_editor_property('walk_clip',clip)
for prop in ['source_walk_speed','walk_speed']:cdo.set_editor_property(prop,motion['nominal_speed_cm_s'])
movement=cdo.get_editor_property('character_movement');movement.modify()
movement.set_editor_property('max_walk_speed',motion['nominal_speed_cm_s'])
E.set_metadata_tag(bp,'NightWarden.Version','V18CoupledLocomotion')
E.set_metadata_tag(bp,'NightWarden.Stage','Coupled native body phase, planted soles, source-shaped swing and runtime plant curves; original body and attack retained')
u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
cdo=u.get_default_object(bp.generated_class())
report.update(stage='coupled_stride_and_matching_ai_speed_saved',complete=True,blueprint=bp.get_path_name(),
    animation=clip.get_path_name(),duration=clip.get_play_length(),mesh=mesh.get_path_name(),
    source_walk_speed_cm_s=cdo.get_editor_property('source_walk_speed'),walk_speed_cm_s=cdo.get_editor_property('walk_speed'),
    yaw_degrees_per_second=cdo.get_editor_property('character_movement').get_editor_property('rotation_rate').yaw,
    idle=cdo.get_editor_property('idle_clip').get_path_name(),attack=cdo.get_editor_property('attack_clip').get_path_name(),
    clothing=False,plant_curves=['NW_Plant_L','NW_Plant_R'],source_asset=motion['source_asset'],source_provenance='Existing project Paragon Rampage pack')
record();print('NW18_COUPLED_STRIDE_SAVED '+json.dumps(report),flush=True)
