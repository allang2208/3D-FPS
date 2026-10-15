import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/BackSmokeV12')
PATH='/Game/Monsters/IncineratorBossM66/BP_M66RigPreview';E=u.EditorAssetLibrary
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before saving the M66 smoke configuration')
if any(p.get_path_name()==PATH for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 character has unsaved changes')
system=u.load_asset('/Game/Monsters/IncineratorBossM66/BackSmokeV12/NS_M66DescendingSoot')
bp=u.load_asset(PATH)
if not system or not bp:raise RuntimeError('M66 smoke asset or character is missing')
cdo=u.get_default_object(bp.generated_class())
settings={'enable_back_smoke':True,'back_smoke_radius':260.,'back_smoke_blind_seconds':2.,'back_smoke_hold_seconds':8.}
for key,value in settings.items():cdo.set_editor_property(key,value)
E.set_metadata_tag(bp,'M66.BackSmoke','V12: four vent rim outlets; Slag persistent black smoke and in-core blindness; independent settling world plumes')
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not E.save_loaded_asset(bp,False):raise RuntimeError('M66 smoke configuration save failed')
report={'complete':True,'saved':[bp.get_path_name()],'system':system.get_path_name(),'settings':settings,
    'visual_mesh':cdo.get_editor_property('visual_mesh').get_path_name(),
    'sweep_clip':cdo.get_editor_property('sweep_clip').get_path_name(),
    'sweep_damage':cdo.get_editor_property('sweep_damage'),'sweep_trigger_range':cdo.get_editor_property('sweep_trigger_range'),
    'outlet_bones':['M66_Vent_High_Tip','M66_Vent_Rear_Tip','M66_Vent_Front_Tip','M66_Vent_Lateral_Tip'],
    'continuous_emission':True,'adds_damage':False,'blindness_clears_on_exit':True,
    'runtime_tested':False,'multiplayer_tested':False,'rendered':False}
(ROOT/'Records/character_install.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_BACK_SMOKE_INSTALLED '+json.dumps(report))
