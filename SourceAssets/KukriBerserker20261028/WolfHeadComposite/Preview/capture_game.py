import unreal as u, json
from pathlib import Path
P=Path(globals().get('__file__') or r'D:/FPS3D/FPSGAME/SourceAssets/KukriBerserker20261028/WolfHeadComposite/Preview/capture_game.py').resolve().parent
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if not world: raise RuntimeError('Game preview is not running')
pawn=u.GameplayStatics.get_player_pawn(world,0)
if not pawn: raise RuntimeError('Player pawn is not ready')
components=pawn.get_components_by_class(u.load_class(None,'/Script/FPSGAME.AzureDragonEnergyComponent'))
print('ENERGY_COMPONENTS',[x.get_path_name() for x in components])
if not components:raise RuntimeError('Current equipped weapon has no energy HUD; preserve loadout')
hud=components[-1]
material=u.load_asset('/Game/Weapons/Kukri20261020/Berserker20261028/M_BerserkerEnergyHud')
record={'pawn':pawn.get_path_name(),'world':world.get_path_name(),'hud':hud.get_path_name(),
    'configured_material':material.get_path_name(),
    'capture':'actual game viewport with UI','equipment_modified':False,'savegame_modified_by_script':False}
(P/'game-capture.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
u.SystemLibrary.execute_console_command(world,'Shot SHOWUI filename='+str(P/'berserker-in-game.png').replace('\\','/')+' -nosuffix')
print('BERSERKER_ACTUAL_GAME_SCREENSHOT_REQUESTED',json.dumps(record))
