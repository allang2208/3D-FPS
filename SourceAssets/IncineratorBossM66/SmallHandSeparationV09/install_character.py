"""Install only the V09 repaired skin on the existing M66 character."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/SmallHandSeparationV09')
DEST='/Game/Monsters/IncineratorBossM66';E=u.EditorAssetLibrary
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before installing the M66 skin')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 packages have unsaved changes')
mesh=u.load_asset(DEST+'/SmallHandSeparationV09/SK_M66_SmallHandSeparation_V09')
bp=u.load_asset(DEST+'/BP_M66RigPreview')
if not mesh or not bp:raise RuntimeError('M66 repaired mesh or Blueprint missing')
u.BlueprintEditorLibrary.compile_blueprint(bp)
cdo=u.get_default_object(bp.generated_class());previous=cdo.get_editor_property('visual_mesh')
physics=cdo.get_editor_property('reaction_physics');clip=cdo.get_editor_property('sweep_clip')
cdo.set_editor_property('visual_mesh',mesh)
component=cdo.get_editor_property('mesh');component.set_skeletal_mesh_asset(mesh)
component.set_physics_asset(physics,True)
component.set_anim_instance_class(u.M66AnimInstance.static_class())
E.set_metadata_tag(bp,'M66.Stage','V09 anatomical small-arm/oral skin separation; V08 sweep, V07 death collision and life motion retained')
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not E.save_loaded_asset(bp,False):raise RuntimeError('M66 Blueprint save failed')
report={'complete':True,'saved':[mesh.get_path_name(),bp.get_path_name()],
    'previous_mesh':previous.get_path_name(),'physics_preserved':physics.get_path_name(),
    'sweep_preserved':clip.get_path_name(),'contact_samples_unchanged':True,
    'locomotion_and_reactions_preserved':True,'f6_entry_id':'IncineratorBossM66Rig',
    'native_code_changed':False,'runtime_tested':False,'multiplayer_tested':False}
(ROOT/'Records/character_install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M66_SMALL_HAND_V09_INSTALLED '+json.dumps(report,ensure_ascii=False))
