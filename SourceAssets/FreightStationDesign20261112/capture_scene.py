"""Read the source poses, materials and plank contact geometry for this design."""
from pathlib import Path
import unreal as u
import json,gzip
ROOT=Path(__file__).resolve().parent
TARGET='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Active game')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages() or any('l_freighttransit_theme_subject/' in p.get_name().lower() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Unsaved scene')
prior=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
w=u.EditorLoadingAndSavingUtils.load_map(TARGET)
D={'map':TARGET,'actors':{},'source_meshes':{}}
for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
    label=a.get_actor_label()
    if not label.startswith(('WarehouseEntrance_','FreightStation_','WarehouseDerelict_','StationWorkshop_11_SM_SW_RepairCart','StationLine_AbandonedCargoWarehouse_0','StationLine_WarehouseStationLink_0','StationLine_AbandonedTransitStation_','StationWorkshop_0_SM_SW_Walls')):continue
    loc=list(a.get_actor_location().to_tuple())
    c,ext=a.get_actor_bounds(False)
    row={'label':label,'name':a.get_name(),'tags':[str(t) for t in a.tags],'p':loc,'r':list(a.get_actor_rotation().to_tuple()),'s':list(a.get_actor_scale3d().to_tuple()),'center':list(c.to_tuple())}
    for comp in a.get_components_by_class(u.StaticMeshComponent):
        m=comp.static_mesh
        if not m:continue
        row.update(mesh=m.get_path_name(),bindings=[comp.get_material(i).get_path_name() if comp.get_material(i) else None for i in range(comp.get_num_materials())])
        box=m.get_bounding_box();D['source_meshes'][row['mesh']]={'min':list(box.min.to_tuple()),'max':list(box.max.to_tuple())}
        if m.get_name() in ('SM_WoodBoard01h','SM_WoodBoard01i') and not (ROOT/(m.get_name()+'.json.gz')).exists():
            dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
            u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(m,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
            pl=next(v for v in u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False) if isinstance(v,u.GeometryScriptVectorList))
            tl=next(v for v in u.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False) if isinstance(v,u.GeometryScriptTriangleList))
            with gzip.open(ROOT/(m.get_name()+'.json.gz'),'wt',encoding='utf8') as f:json.dump({'v':[v.to_tuple() for v in u.GeometryScript_List.convert_vector_list_to_array(pl)],'t':[[t.x,t.y,t.z] for t in u.GeometryScript_List.convert_triangle_list_to_array(tl)]},f)
    for comp in a.get_components_by_class(u.DecalComponent):row.update(decal=comp.get_decal_material().get_path_name(),size=list(comp.get_editor_property('decal_size').to_tuple()))
    D['actors'][label]=row
(ROOT/'scene-inputs.json').write_text(json.dumps(D,indent=2),encoding='utf8')
if prior and prior!=TARGET and not prior.startswith('/Temp/'):u.EditorLoadingAndSavingUtils.load_map(prior)
print('DESIGN_STAGE_SOURCES_READ',flush=True)
