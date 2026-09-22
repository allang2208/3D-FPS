from pathlib import Path
import json
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkshopTools20260921')
for name in ('Sources','Authored','Receipts'): (ROOT/name).mkdir(parents=True,exist_ok=True)
UE=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=UE.get_editor_world()
if UE.get_game_world():raise RuntimeError('Gameplay active: '+UE.get_game_world().get_path_name())
if not world or world.get_path_name().split('.')[0]!='/Game/GameMaps/L_Dungeon_Prototype':
    dirty=u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
    if dirty:raise RuntimeError('Preserve unsaved maps: '+', '.join(p.get_name() for p in dirty))
    if not u.get_editor_subsystem(u.LevelEditorSubsystem).load_level('/Game/GameMaps/L_Dungeon_Prototype'):raise RuntimeError('Dungeon load failed')
    world=UE.get_editor_world()
rows=[]
for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
    label=a.get_actor_label()
    if '_WS_' not in label and label not in ('DGN_AV2_LightFixtures','DGN_AV2_Light_Workshop'):continue
    c=a.get_component_by_class(u.StaticMeshComponent);origin,extent=a.get_actor_bounds(False)
    row={'label':label,'location':list(a.get_actor_location().to_tuple()),'rotation':list(a.get_actor_rotation().to_tuple()),
         'scale':list(a.get_actor_scale3d().to_tuple()),'bounds_center':list(origin.to_tuple()),'bounds_extent':list(extent.to_tuple()),
         'hidden':a.get_editor_property('hidden')}
    if c:
        row.update(mesh=c.static_mesh.get_path_name() if c.static_mesh else None,
                   materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())])
        if label=='DGN_AV2_LightFixtures':
            task=u.AssetExportTask();task.object=c.static_mesh;task.filename=str(ROOT/'Sources/current_fixtures.fbx')
            task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
            if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Fixture source export failed')
            row['export']=task.filename
    light=a.get_component_by_class(u.LightComponent)
    if light:row.update(intensity=light.get_editor_property('intensity'),light_color=str(light.get_editor_property('light_color')))
    rows.append(row)
state={'map':world.get_path_name(),'gameplay_active':bool(UE.get_game_world()),'actors':rows,
       'dirty_maps':[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()]}
(ROOT/'Receipts/inputs.json').write_text(json.dumps(state,indent=2),encoding='utf-8')
print(json.dumps({'actors':len(rows),'dirty_maps':state['dirty_maps'],'gameplay_active':state['gameplay_active'],
  'placement':[r for r in rows if any(k in r['label'] for k in ('Light','RepairMotor','Workbench'))]}))
