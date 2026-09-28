"""Read the reported spawn's saved geometry and export source meshes for repair."""
import unreal as u,json
from pathlib import Path
R=Path(__file__).parent/'SpawnRepair';R.mkdir(exist_ok=True)
w=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/DayNight_Lighting')
def vec(p):return [p.x,p.y,p.z]
rows=[];paths=set()
for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
    p=a.get_actor_location()
    relevant=isinstance(a,u.PlayerStart) or a.get_actor_label() in ['GodSpaceStructure','GodSpace_Fountain'] or ((abs(p.x+1100)<1800 and abs(p.y+5100)<1200) and isinstance(a,u.StaticMeshActor))
    if not relevant:continue
    row={'name':a.get_name(),'label':a.get_actor_label(),'location':vec(p),'scale':vec(a.get_actor_scale3d()),'meshes':[]}
    for c in a.get_components_by_class(u.StaticMeshComponent):
        m=c.static_mesh
        if not m:continue
        b=m.get_bounding_box();bs=m.get_editor_property('body_setup')
        d={'mesh':m.get_path_name(),'bounds':[vec(b.min),vec(b.max)],'component_transform':str(c.get_world_transform()),'collision':str(c.get_collision_enabled()),'profile':str(c.get_collision_profile_name()),'lod':c.get_editor_property('forced_lod_model'),'trace':str(bs.get_editor_property('collision_trace_flag')) if bs else None,'boxes':[]}
        if bs:
            ag=bs.get_editor_property('agg_geom')
            for box in ag.get_editor_property('box_elems'):
                d['boxes'].append({'center':vec(box.get_editor_property('center')),'x':box.get_editor_property('x'),'y':box.get_editor_property('y'),'z':box.get_editor_property('z')})
        row['meshes'].append(d);paths.add(m.get_path_name())
    rows.append(row)
    (R/'inputs.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
for path in paths:
    if 'SM_GodSpaceStructure' not in path and 'SM_MarbleFloorTiles' not in path:continue
    m=u.load_asset(path);task=u.AssetExportTask();task.object=m;task.filename=str(R/(m.get_name()+'.fbx'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.StaticMeshExporterFBX()
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export failed '+path)
(R/'inputs.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
print('SPAWN_GEOMETRY_INPUTS '+str(len(rows)))
