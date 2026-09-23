import unreal as u,json,gc
from pathlib import Path
root=Path(__file__).resolve().parents[1];ue=u.get_editor_subsystem(u.UnrealEditorSubsystem);ed=u.get_editor_subsystem(u.LevelEditorSubsystem);aa=u.get_editor_subsystem(u.EditorActorSubsystem)
if ue.get_game_world():raise RuntimeError('Preserve running game')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved map')
if not ed.load_level('/Game/GameMaps/L_Dungeon_Randomized'):raise RuntimeError('Cannot open dungeon source')
data=[];seen=set()
for a in aa.get_all_level_actors():
    label=a.get_actor_label()
    if label=='DGN_RouteGenerator':
        (root/'Receipts/active-catalog.json').write_text(a.get_editor_property('module_catalog_json'))
    if not label.startswith(('DGN_G_','DGN_Link_')):continue
    for c in a.get_components_by_class(u.StaticMeshComponent):
        if not c.static_mesh:continue
        path=c.static_mesh.get_path_name()
        if path in seen:continue
        if not any(s in path for s in ('Threshold','Transit','Distribution_Shell')) and not label.startswith('DGN_Link_'):continue
        seen.add(path);b=c.static_mesh.get_bounding_box();t=c.get_world_transform()
        data.append(dict(label=label,mesh=path,bounds_min=[b.min.x,b.min.y,b.min.z],bounds_max=[b.max.x,b.max.y,b.max.z],transform=str(t)))
(root/'Receipts/interface-sources.json').write_text(json.dumps(data,indent=2))
print(json.dumps(data))
