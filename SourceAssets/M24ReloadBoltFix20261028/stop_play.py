import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent;rows=[];world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
  v=a.get_editor_property('akm_viewmodel')
  rows.append({'mesh':v.get_editor_property('skeletal_mesh_asset').get_path_name(),'visible':v.is_visible(),'reload':a.get_editor_property('reload_duration'),'empty_reload':a.get_editor_property('empty_reload_duration'),'state':str(a.get_weapon_state())})
(O/'pre_save_runtime.json').write_text(json.dumps(rows,indent=2))
if world:u.EditorLevelLibrary.editor_end_play()
print('M24_USER_AUTHORIZED_END_PIE',json.dumps(rows),flush=True)
