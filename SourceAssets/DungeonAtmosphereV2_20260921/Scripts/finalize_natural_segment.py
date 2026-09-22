"""Save art revision and its requested screenshots without gameplay tests."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonAtmosphereV2_20260921')
state=json.loads((ROOT/'Receipts/natural-segment-capture-state.json').read_text())
if state['status']!='complete':raise RuntimeError('Natural segment captures are not complete')
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if UE.get_game_world() or UE.get_editor_world().get_path_name().split('.')[0]!=state['map']:raise RuntimeError('Editor context changed; current state preserved')
pos=u.Vector(180,-210,165);target=u.Vector(2050,-210,175)
UE.set_level_viewport_camera_info(pos,u.MathLibrary.find_look_at_rotation(pos,target))
if not u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level():raise RuntimeError('Map save failed')
receipt=json.loads((ROOT/'Receipts/natural-segment-import.json').read_text())
receipt['screenshots']=state['shots'];receipt['visual_acceptance']='pending user review';receipt['tests_run']=False
(ROOT/'Receipts/natural-segment-import.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
scene=json.loads((ROOT/'Receipts/scene-build.json').read_text())
scene['natural_segment']={'receipt':str(ROOT/'Receipts/natural-segment-import.json'),'scope':'Entrance 8.3 m north / 4.4 m south; 2 wall actors replaced; 1 decorative debris actor added','visual_acceptance':'pending user review','tests_run':False}
(ROOT/'Receipts/scene-build.json').write_text(json.dumps(scene,indent=2),encoding='utf-8')
print('NATURAL_SEGMENT_DELIVERED_WITH_SIX_UE_CAPTURES; gameplay tests not run')
