"""Collect exact authoring inputs for the requested rework; no PIE/render/test."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonAuthoredExpansion20260922')
ROOT.mkdir(exist_ok=True)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
ED=u.get_editor_subsystem(u.LevelEditorSubsystem)
AA=u.get_editor_subsystem(u.EditorActorSubsystem)
if UE.get_game_world():raise RuntimeError('Gameplay is running; preserve the current session')
dirty=list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())+list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
if dirty:raise RuntimeError('Preserve unsaved packages: '+', '.join(p.get_name() for p in dirty[:8]))
if not ED.load_level('/Game/GameMaps/L_Dungeon_Prototype'):raise RuntimeError('Cannot open accepted sample')
rows=[]
for a in AA.get_all_level_actors():
    row=dict(label=a.get_actor_label(),name=a.get_name(),cls=a.get_class().get_path_name(),folder=str(a.get_folder_path()),location=list(a.get_actor_location().to_tuple()))
    meshes=[]
    for c in a.get_components_by_class(u.StaticMeshComponent):
        mesh=c.get_editor_property('static_mesh')
        if mesh:meshes.append(mesh.get_path_name())
    row['meshes']=meshes
    rows.append(row)
(ROOT/'baseline-actors.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
print(json.dumps(dict(actors=len(rows),boundary=[r for r in rows if any(k in r['label'] for k in ['EntryEnd','EndLanding','ServiceDoor','PlayerStart'])]),ensure_ascii=False))
