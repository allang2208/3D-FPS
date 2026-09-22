from pathlib import Path
import json, unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkshopSurface20260921')
for n in ('Authored','Receipts','Sources'):(ROOT/n).mkdir(parents=True,exist_ok=True)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=UE.get_editor_world()
if not world or world.get_path_name().split('.')[0]!='/Game/GameMaps/L_Dungeon_Prototype':
    if UE.get_game_world():raise RuntimeError('Gameplay active on another map; preserve it')
    if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved current map')
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GameMaps/L_Dungeon_Prototype'):raise RuntimeError('Map load failed')
rows=[]
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    label=a.get_actor_label()
    if not (label.startswith('DGN_Room_WS_') or label.startswith('DGN_WSTools_') or label.startswith('DGN_WSSculpt_')):continue
    c=a.get_component_by_class(u.StaticMeshComponent)
    if label=='DGN_Room_WS_UtilityDetail' and c and c.static_mesh:
        t=u.AssetExportTask();t.object=c.static_mesh;t.filename=str(ROOT/'Sources/current_utility_detail.fbx');t.automated=True;t.prompt=False;t.replace_identical=True;t.exporter=u.StaticMeshExporterFBX()
        if not u.Exporter.run_asset_export_task(t):raise RuntimeError('Utility detail source export failed')
    rows.append(dict(label=label,mesh=c.static_mesh.get_path_name() if c and c.static_mesh else None,
        location=list(a.get_actor_location().to_tuple()),rotation=list(a.get_actor_rotation().to_tuple()),scale=list(a.get_actor_scale3d().to_tuple())))
state=dict(actors=rows,gameplay_active=bool(UE.get_game_world()),dirty_maps=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()])
(ROOT/'Receipts/inputs.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print(json.dumps({'actors':len(rows),'dirty_maps':state['dirty_maps'],'gameplay_active':state['gameplay_active']}))
