"""Read saved subject inputs and support triangles for this art authoring pass."""
from pathlib import Path
import json,gzip
import unreal as u
ROOT=Path(__file__).resolve().parent
TARGET='/Game/GameMaps/Design/L_FreightTransit_Theme_Subject'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor and editor.get_game_world():raise RuntimeError('Preserve active gameplay')
if u.EditorLoadingAndSavingUtils.get_dirty_map_packages():raise RuntimeError('Preserve unsaved maps')
if any('/gamemaps/design/l_freighttransit_theme_subject/' in p.get_name().lower() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('Preserve unsaved subject actors')
previous=editor.get_editor_world().get_path_name().split('.')[0] if editor and editor.get_editor_world() else ''
w=u.EditorLoadingAndSavingUtils.load_map(TARGET)
report={'map':TARGET,'actors':[],'meshes':{}}
geometry_names={'SM_Station_Floors','SM_Station_Paving','SM_Station_TrackBed','SM_Station_Walls','SM_Station_Tiles','SM_Station_Bridge','SM_Station_Stairs','SM_Station_Ribs','SM_RS_Transit_Floors','SM_RS_Transit_Shell','SM_RS_Transit_Damage0_Tiles','SM_SW_Walls','SM_SW_PartsRack','SM_SW_RepairCart','SM_SW_DispatchDesk'}
(ROOT/'Geometry').mkdir(parents=True,exist_ok=True)
def mesh_data(m):
    path=m.get_path_name()
    if path in report['meshes']:return path
    b=m.get_bounding_box();d={'min':list(b.min.to_tuple()),'max':list(b.max.to_tuple()),'materials':[s.material_interface.get_path_name() if s.material_interface else None for s in m.static_materials]}
    report['meshes'][path]=d
    if m.get_name() in geometry_names:
        dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
        u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(m,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
        q=u.GeometryScript_MeshQueries;ls=u.GeometryScript_List
        pl=next(v for v in q.get_all_vertex_positions(dm,False) if isinstance(v,u.GeometryScriptVectorList))
        tl=next(v for v in q.get_all_triangle_indices(dm,False) if isinstance(v,u.GeometryScriptTriangleList))
        geo={'vertices':[list(v.to_tuple()) for v in ls.convert_vector_list_to_array(pl)],'indices':[i for t in ls.convert_triangle_list_to_array(tl) for i in (t.x,t.y,t.z)]}
        name=m.get_name()+'.json.gz';d['geometry']=name
        with gzip.open(ROOT/'Geometry'/name,'wt',encoding='utf8') as f:json.dump(geo,f)
    return path
for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
    center,extent=a.get_actor_bounds(False)
    if center.x+extent.x<2100:continue
    d={'name':a.get_name(),'label':a.get_actor_label(),'class':a.get_class().get_name(),'tags':[str(t) for t in a.tags],
       'position':list(a.get_actor_location().to_tuple()),'rotation':list(a.get_actor_rotation().to_tuple()),'scale':list(a.get_actor_scale3d().to_tuple()),
       'center':list(center.to_tuple()),'extent':list(extent.to_tuple()),'components':[]}
    for c in a.get_components_by_class(u.StaticMeshComponent):
        if not c.static_mesh:continue
        t=c.get_world_transform()
        d['components'].append({'name':c.get_name(),'mesh':mesh_data(c.static_mesh),'materials':[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())],
                                'position':list(t.translation.to_tuple()),'rotation':list(t.rotation.rotator().to_tuple()),'scale':list(t.scale3d.to_tuple())})
    for c in a.get_components_by_class(u.DecalComponent):
        d['decal']={'material':c.get_decal_material().get_path_name() if c.get_decal_material() else None,'size':list(c.get_editor_property('decal_size').to_tuple())}
    report['actors'].append(d)
for prior,key in [('FreightWarehouseEntranceSample20261111/authoring-inputs.json','meshes'),('FreightWarehouseDerelictPass20261111/inputs.json','extra_meshes')]:
    source=json.loads((ROOT.parent/prior).read_text('utf8'))
    # Existing manifests have already selected the native props, so avoid scanning the asset library.
    candidates=source.get(key,{})
    for path,data in candidates.items():
        candidate=data.get('path',path)
        if candidate.startswith('/Game/'):
            m=u.load_asset(candidate)
            if isinstance(m,u.StaticMesh):mesh_data(m)
for name in ('SM_Bucket01a','SM_Bucket01b','Sm_Toolbox01a','SM_Oilbottle01a','SM_Paintcan01a','SM_WoodBoard01h'):
    m=u.load_asset('/Game/UndergroundTunnel/Meshes/Props/'+name)
    if isinstance(m,u.StaticMesh):mesh_data(m)
(ROOT/'inputs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
if previous and not previous.startswith('/Temp/') and previous!=TARGET:u.EditorLoadingAndSavingUtils.load_map(previous)
print('FREIGHT_STATION_AUTHORING_INPUTS_READ '+str(len(report['actors'])),flush=True)
