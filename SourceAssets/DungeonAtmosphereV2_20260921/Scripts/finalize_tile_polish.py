"""Save the requested screenshot delivery and leave a useful editor view."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonAtmosphereV2_20260921')
state=json.loads((ROOT/'Receipts/tile-polish-capture-state.json').read_text())
if state['status']!='complete':raise RuntimeError('Requested tile screenshots are still pending')
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if UE.get_game_world() or UE.get_editor_world().get_path_name().split('.')[0]!=state['map']:
    raise RuntimeError('Editor context changed; leaving the current context intact')
pos=u.Vector(180,-210,165);target=u.Vector(2050,-210,175)
UE.set_level_viewport_camera_info(pos,u.MathLibrary.find_look_at_rotation(pos,target))
if not u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level():raise RuntimeError('Unable to save the dungeon')
receipt=json.loads((ROOT/'Receipts/tile-polish-import.json').read_text())
receipt['screenshots']=state['shots'];receipt['visual_acceptance']='pending user review';receipt['tests_run']=False
(ROOT/'Receipts/tile-polish-import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
scene=json.loads((ROOT/'Receipts/scene-build.json').read_text())
scene['tile_polish']={'receipt':str(ROOT/'Receipts/tile-polish-import.json'),'refined_groups':8,'additional_leaks':6,'visual_acceptance':'pending user review'}
scene['counts']['damp_decals']=15
(ROOT/'Receipts/scene-build.json').write_text(json.dumps(scene,indent=2),encoding='utf-8')
print('TILE_POLISH_SAVED_WITH_FIVE_UE_SCREENSHOTS; gameplay tests not run')
