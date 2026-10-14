"""Produce anatomical live hit bodies and save Root Crown boss defaults. No runtime tests."""
import json,traceback
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/RootCrown20261014')
DEST='/Game/Monsters/RootCrown';E=u.EditorAssetLibrary
RECEIPT=ROOT/'Reports/ue-combat-import.json'
report={'stage':'building_hit_surface','saved':[],'gameplay_tested':False,'multiplayer_tested':False}
def record():RECEIPT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
def save(asset):
    if not asset or not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+str(asset))
    report['saved'].append(asset.get_path_name());record()
try:
    if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve active PIE')
    if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved Root Crown assets')
    body=u.load_asset(DEST+'/RigV01/SK_RootCrown')
    hit=u.RootCrownRigPreview.build_hit_surface_physics(body,DEST+'/CombatV01/PA_RootCrown_HitSurface')
    if not hit:raise RuntimeError('Root Crown hit surface authoring failed')
    save(hit)
    bp=u.load_asset(DEST+'/BP_RootCrownRigPreview');u.BlueprintEditorLibrary.compile_blueprint(bp)
    defaults=u.get_default_object(bp.generated_class())
    values={'hit_surface_physics':hit,'max_health':4200.,'level':12,'rank':u.MonsterRank.BOSS,'experience_reward':600,
            'slash_damage':70.,'needle_damage':24.,'root_damage':60.,'root_knot_health':80.,
            'slash_cooldown':5.,'needle_cooldown':8.,'root_cooldown':14.,'walk_speed':150.,'turn_speed':150.,'corpse_seconds':25.}
    for key,value in values.items():defaults.set_editor_property(key,value)
    u.BlueprintEditorLibrary.compile_blueprint(bp);save(bp)
    report.update(stage='combat_saved',blueprint=bp.get_path_name(),hit_asset=hit.get_path_name(),
                  health=4200,level=12,rank='Boss',physical_defense=45,magical_defense=30,critical_resistance=25,toughness=1000,base_experience=600,
                  damage={'slash':70,'needle_per_wave':24,'mine_maximum':60},
                  weakpoint_bones=['Stem_Upper','Crown_Base'],history_samples=32,history_hz=30,
                  preserved_body_material=defaults.get_editor_property('slash_material').get_path_name(),
                  preserved_attacks=[defaults.get_editor_property(key).get_path_name() for key in ('slash_clip','needle_clip','root_clip')])
    record();print('ROOT_CROWN_COMBAT_SAVED '+json.dumps(report,ensure_ascii=False))
except Exception:
    report.update(stage='failed',error=traceback.format_exc());record();raise
