"""Save the ground AOE configuration on the original M66."""
import json,unreal as u
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/SlamWaveV15');DEST='/Game/Monsters/IncineratorBossM66';E=u.EditorAssetLibrary
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before saving M66 ground AOE')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 packages have unsaved changes')
bp=u.load_asset(DEST+'/BP_M66RigPreview');mat=u.load_asset(DEST+'/SlamWaveV15/M_M66GroundWave')
if not bp or not mat:raise RuntimeError('M66 character or wave material missing')
cdo=u.get_default_object(bp.generated_class())
settings={'slam_area_radius':400.,'slam_wave_seconds':.55,'slam_stun_seconds':2.,'slam_wave_material':mat}
for name,value in settings.items():cdo.set_editor_property(name,value)
E.set_metadata_tag(bp,'M66.GroundSlam','V15: closed-fist impact at 1.63 s releases one 4 m expanding AOE; 135 physical and 2 s stun on actual damage; no extra fist hit')
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not E.save_loaded_asset(bp,False):raise RuntimeError('M66 AOE character save failed')
report={'complete':True,'saved':[bp.get_path_name()],'material':mat.get_path_name(),'radius_cm':400,'expansion_seconds':.55,'stun_seconds':2,
    'physical_damage':cdo.get_editor_property('slam_damage'),'cooldown_seconds':cdo.get_editor_property('slam_cooldown'),
    'slam_clip':cdo.get_editor_property('slam_clip').get_path_name(),'visual_mesh':cdo.get_editor_property('visual_mesh').get_path_name(),
    'sweep_preserved':cdo.get_editor_property('sweep_clip').get_path_name(),'back_smoke_enabled':cdo.get_editor_property('enable_back_smoke'),
    'runtime_tested':False,'multiplayer_tested':False,'rendered':False}
(ROOT/'Records/character_install.json').write_text(json.dumps(report,indent=2))
print('M66_SLAM_AOE_V15_SAVED '+json.dumps(report))
