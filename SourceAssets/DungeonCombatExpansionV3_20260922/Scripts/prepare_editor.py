import unreal as u,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
AA=u.get_editor_subsystem(u.EditorActorSubsystem);UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
data={'world':UE.get_editor_world().get_path_name(),'play_running':bool(UE.get_game_world()),'actors':[]}
for a in AA.get_all_level_actors():
    if not (a.get_actor_label().startswith('DGN_RS_') or a.get_actor_label()=='DGN_Prop_GoddessStatue_01'):continue
    p=a.get_actor_location();r=a.get_actor_rotation()
    data['actors'].append(dict(path=a.get_path_name(),label=a.get_actor_label(),location=[p.x,p.y,p.z],rotation=dict(pitch=r.pitch,yaw=r.yaw,roll=r.roll)))
(ROOT/'Receipts/scene-before.json').write_text(json.dumps(data,indent=2))
if UE.get_game_world():u.get_editor_subsystem(u.LevelEditorSubsystem).editor_request_end_play()
u.SystemLibrary.execute_console_command(UE.get_editor_world(),'LiveCoding.CompileSync')
print('DUNGEON_NATIVE_UPDATE_REQUEST_FINISHED',len(data['actors']))
