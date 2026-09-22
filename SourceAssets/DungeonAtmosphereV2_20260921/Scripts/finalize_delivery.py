"""Leave the completed dungeon saved and framed at its entrance."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonAtmosphereV2_20260921')
state=json.loads((ROOT/'Receipts/capture-state.json').read_text(encoding='utf-8-sig'))
if state['status']!='complete':raise RuntimeError('Requested captures have not completed')
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if UE.get_editor_world().get_path_name().split('.')[0]!=state['map'] or UE.get_game_world():
    raise RuntimeError('Editor context changed after capture; leave it intact')
eye=u.Vector(180,-210,165);target=u.Vector(2050,-210,175)
UE.set_level_viewport_camera_info(eye,u.MathLibrary.find_look_at_rotation(eye,target))
if not u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level():raise RuntimeError('Final dungeon save failed')
receipt=json.loads((ROOT/'Receipts/scene-build.json').read_text())
receipt['requested_scene_captures']=state['shots'];receipt['visual_acceptance']='pending user review'
receipt['corrections_from_captures']=['outward prism winding and mirrored side-wall winding','cabinet and side-bay valve facing']
(ROOT/'Receipts/scene-build.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('V2_DELIVERY_SAVED_WITH_FIVE_ENGINE_CAPTURES')
