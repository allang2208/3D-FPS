"""Run after the native Editor DLL contains BellowSacLobber and BellowSacProjectile."""
import unreal as u, json
from pathlib import Path
BASE='/Game/Monsters/BellowSacLobber'
V2=BASE+'/V02'
LIB=u.EditorAssetLibrary
if not globals().get('BELLOW_COMMANDLET',False) and u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Finish PIE before updating the monster Blueprint')
if any(p.get_path_name().startswith(BASE) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Target monster has unsaved asset edits')
bp=u.load_asset(BASE+'/BP_BellowSacLobber')
backup=BASE+'/V01/BP_BellowSacLobber_LocomotionBackup'
if not LIB.does_asset_exist(backup):
    saved=LIB.duplicate_asset(BASE+'/BP_BellowSacLobber',backup)
    if not saved or not LIB.save_loaded_asset(saved,False):raise RuntimeError('Could not preserve locomotion Blueprint')
u.BlueprintEditorLibrary.reparent_blueprint(bp,u.BellowSacLobber)
u.BlueprintEditorLibrary.compile_blueprint(bp)
cdo=u.get_default_object(bp.generated_class())
values={'animation_set':u.load_asset(V2+'/DA_BellowSacLobber_Combat'),'monster_display_name':'鼓囊 M-09',
    'sac_mesh':u.load_asset(V2+'/Projectile/SM_BellowSacCapsule'),
    'telegraph_mesh':u.load_asset(V2+'/Projectile/SM_BellowRuptureRing'),
    'sac_material':u.load_asset(V2+'/Projectile/M_BellowSacCapsule'),
    'telegraph_material':u.load_asset(V2+'/Projectile/M_BellowRuptureRing'),
    'blast_damage':48.,'blast_radius':140.,'impact_fuse':.65,
    'lob_min_range':400.,'lob_max_range':2800.,'preferred_range':1800.,
    'shove_damage':24.,'shove_range':450.,'lob_cooldown_min':4.,'lob_cooldown_max':4.,
    'aggro_radius':3200.,'sound_sensitive':True,'hearing_radius':3600.,
    'attack_tracking_yaw_rate':120.,'howl_on_encounter':False,'use_predictive_hunting':False,
    'bite_damage':0.,'pounce_damage':0.}
for key,value in values.items():
    if value is None:raise RuntimeError('Required asset missing: '+key)
    cdo.set_editor_property(key,value)
cdo.set_editor_property('tags',[u.Name('Enemy'),u.Name('BellowSacLobber')])
LIB.set_metadata_tag(bp,'BellowSacLobber.Stage','V02: preserved locomotion, pressure lob and close shove; no dungeon spawn injection')
u.BlueprintEditorLibrary.compile_blueprint(bp)
if not LIB.save_loaded_asset(bp,False):raise RuntimeError('Blueprint save failed')
path=Path('D:/FPS3D/FPSGAME/SourceAssets/BellowSacLobberMeshy20261012/Records/ue_combat_v02.json')
report=json.loads(path.read_text(encoding='utf-8'))
report['blueprint']=bp.get_path_name();report['native_class']='BellowSacLobber'
if 'runtime_binding' not in report['stages']:report['stages'].append('runtime_binding')
report['runtime_tested']=False
path.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('BELLOW_COMBAT_INSTALLED '+bp.get_path_name())
