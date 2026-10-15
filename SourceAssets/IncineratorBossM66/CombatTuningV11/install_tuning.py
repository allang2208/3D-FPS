"""Apply M66's lord-referenced attack balance without changing accepted motion."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/CombatTuningV11')
PATH='/Game/Monsters/IncineratorBossM66/BP_M66RigPreview';E=u.EditorAssetLibrary
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('End PIE before saving M66 combat defaults; no changes made')
if any(p.get_path_name()==PATH for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('M66 character has unsaved user changes; no changes made')
bp=u.load_asset(PATH)
if not bp:raise RuntimeError('M66 character asset missing')
cdo=u.get_default_object(bp.generated_class())
settings={'sweep_damage':90.,'sweep_trigger_range':350.,'sweep_hit_radius':24.,
          'sweep_cooldown':3.6,'stopping_distance':270.}
before={key:float(cdo.get_editor_property(key)) for key in settings}
for key,value in settings.items():cdo.set_editor_property(key,value)
E.set_metadata_tag(bp,'M66.CombatBalance','V11: 90 physical damage; 350 cm entry; 270 cm stop; 24 cm swept claw radius; 3.6 s start-to-start cooldown')
E.set_metadata_tag(bp,'M66.AcceptedVisual','User accepted V10 mesh/drape and existing V08 sweep on 2026-10-15; balance tuning only')
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not E.save_loaded_asset(bp,False):raise RuntimeError('M66 combat defaults save failed')
report={'complete':True,'saved':[bp.get_path_name()],'before':before,'configured':settings,
        'damage_semantics':'physical raw attack, before player defense/block mitigation; once per target per sweep',
        'reference_assets':['/Game/Monsters/BoundCongregate/BP_BoundCongregate','/Game/Monsters/M10Mawcrawler/BP_M10Mawcrawler'],
        'accepted_visuals_preserved':True,'rank_and_health_preserved':True,
        'contact_seconds':[1.,1.35],'animation_seconds':2.6,
        'native_code_changed':False,'dll_build_required':False,'runtime_tested':False,'multiplayer_tested':False}
(ROOT/'Records/character_install.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('M66_COMBAT_V11_SAVED '+json.dumps(report,ensure_ascii=False))
