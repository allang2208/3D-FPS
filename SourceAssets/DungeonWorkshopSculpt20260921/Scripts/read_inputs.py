from pathlib import Path
import json, unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkshopSculpt20260921')
for n in ('Authored','Receipts','Sources'):(ROOT/n).mkdir(parents=True,exist_ok=True)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=UE.get_editor_world()
if UE.get_game_world():raise RuntimeError('Gameplay active; preserve current session')
if not world or world.get_path_name().split('.')[0]!='/Game/GameMaps/L_Dungeon_Prototype':
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved current map')
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GameMaps/L_Dungeon_Prototype'):raise RuntimeError('Map load failed')
rows=[]
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    label=a.get_actor_label()
    if not (label.startswith('DGN_Room_WS_') or label.startswith('DGN_WSTools_')):continue
    c=a.get_component_by_class(u.StaticMeshComponent)
    rows.append(dict(label=label,mesh=c.static_mesh.get_path_name() if c and c.static_mesh else None,
        location=list(a.get_actor_location().to_tuple()),rotation=list(a.get_actor_rotation().to_tuple()),scale=list(a.get_actor_scale3d().to_tuple())))
state=dict(actors=rows,dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
(ROOT/'Receipts/inputs.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print(json.dumps(state))
