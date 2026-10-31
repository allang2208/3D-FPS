"""User-requested bedroom component inventory and exact SourceModel LOD0 export."""
import unreal as u,json,hashlib,gc
from pathlib import Path
R=Path(__file__).resolve().parent
PHASE=globals().get('CAPTURE_PHASE','before')
OUT=R/'Audit'/PHASE;OUT.mkdir(parents=True,exist_ok=True)
MAP='/Game/GameMaps/L_CyberpunkApartment'
world=u.EditorLoadingAndSavingUtils.load_map(MAP)
rows=[];meshes={};containers=[]
def xyz(v):return [v.x,v.y,v.z]
def transform(t):
    p=u.MathLibrary.transform_location(t,u.Vector())
    return dict(origin=xyz(p),axes=[xyz(u.MathLibrary.transform_location(t,u.Vector(*v))-p) for v in [(1,0,0),(0,1,0),(0,0,1)]])
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    label=a.get_actor_label()
    for c in a.get_components_by_class(u.StaticMeshComponent):
        mesh=c.static_mesh
        if not mesh:continue
        bounds=mesh.get_bounding_box();t=c.get_world_transform()
        corners=[u.MathLibrary.transform_location(t,u.Vector(x,y,z)) for x in (bounds.min.x,bounds.max.x) for y in (bounds.min.y,bounds.max.y) for z in (bounds.min.z,bounds.max.z)]
        lo=[min(getattr(p,k) for p in corners) for k in ('x','y','z')];hi=[max(getattr(p,k) for p in corners) for k in ('x','y','z')]
        overlap=all(hi[i]>=lower and lo[i]<=upper for i,(lower,upper) in enumerate([(2120,2990),(-1025,0),(-10,560)]))
        if not (label.startswith('BP_') or 'Bed2' in label or overlap):continue
        if label.startswith(('CITY_','BAY_','AP8_','AP9_','AP16_','AP17_','AP18_','AP19_','AP20_')):continue
        hidden=bool(c.get_editor_property('hidden_in_game')) or not c.is_visible()
        path=mesh.get_path_name();key=hashlib.sha1(path.encode()).hexdigest()[:16]
        row=dict(actor=label,component=c.get_name(),mesh=path,key=key,transform=transform(t),bounds_cm=[lo,hi],hidden=hidden,
                 collision=str(c.get_collision_enabled()),slots=[str(s.material_slot_name) for s in mesh.static_materials],
                 materials=[m.get_path_name() if m else None for m in c.get_materials()],tags=[str(v) for v in a.tags])
        rows.append(row)
        if key in meshes:continue
        dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0))
        if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Source geometry unavailable '+path)
        _,pv,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
        _,tv,_=u.GeometryScript_MeshQueries.get_all_triangle_indices(dm,False)
        _,mv,_=u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm)
        data=dict(path=path,vertices=[xyz(v) for v in u.GeometryScript_List.convert_vector_list_to_array(pv)],
                  triangles=[xyz(v) for v in u.GeometryScript_List.convert_triangle_list_to_array(tv)],
                  materials=list(u.GeometryScript_List.convert_index_list_to_array(mv)))
        (OUT/(key+'.json')).write_text(json.dumps(data,separators=(',',':')),encoding='utf8')
        meshes[key]=dict(path=path,triangles=len(data['triangles']),vertices=len(data['vertices']))
        dm=None;pv=None;tv=None;mv=None;data=None;gc.collect()
        print('BEDROOM_SOURCE_CAPTURE',label,c.get_name())
    if 'Bed2' in label and isinstance(a,u.ColdSteelSceneContainer):
        hinge=a.get_editor_property('door_hinge')
        travel=a.get_editor_property('drawer_travel');zero=u.MathLibrary.transform_location(a.get_actor_transform(),u.Vector())
        end=u.MathLibrary.transform_location(a.get_actor_transform(),travel)
        containers.append(dict(actor=label,motion=str(a.get_editor_property('opening_motion')),travel_world=xyz(end-zero),
            opened_yaw=a.get_editor_property('opened_yaw'),hinge_world=xyz(hinge.get_world_location()),initial_fraction=a.get_editor_property('initial_open_fraction')))
(OUT/'components.json').write_text(json.dumps(dict(map=MAP,phase=PHASE,components=rows,meshes=meshes,containers=containers),indent=2),encoding='utf8')
print('BEDROOM_INVENTORY_SAVED',len(rows),len(meshes))
