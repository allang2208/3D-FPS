"""Read the saved apartment map in the isolated publication host. No package writes."""
from pathlib import Path
from datetime import datetime
import json, unreal as u
R=Path(__file__).resolve().parent
world=u.EditorLoadingAndSavingUtils.load_map('/Game/GameMaps/L_CyberpunkApartment')
if not world:raise RuntimeError('Formal map snapshot did not load')
sm_editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.get_default_object(u.StaticMeshEditorSubsystem)
rows=[]; inventory=[]; meshes={};errors=[]
def v(x):return list(x.to_tuple())
def tr(t):return dict(p=v(t.translation),q=v(t.rotation),s=v(t.scale3d))
def prop(o,n,default=None):
    try:return o.get_editor_property(n)
    except Exception:return default
def mesh_info(sm):
    p=sm.get_path_name()
    if p in meshes:return
    b=sm.get_bounding_box();bs=prop(sm,'body_setup')
    info=dict(min=v(b.min),max=v(b.max),materials=[m.material_interface.get_path_name() if m.material_interface else None for m in sm.static_materials],lods=sm.get_num_lods())
    info['collision_trace']=str(prop(bs,'collision_trace_flag')) if bs else None
    info['simple_collision_count']=sm_editor.get_simple_collision_count(sm)
    meshes[p]=info
    # Exact road, sidewalk and manufactured ground surface geometry; mesh bounds alone
    # cannot prove connectivity at curved intersections.
    want=any(t in p for t in ['/Roads/','/Road/Kit_Sidewalk','/Meshes/JunctionAsphalt','/Meshes/BuildingPads','/Meshes/ParkGround','NearBank20261028/Meshes/'])
    if want:
        try:
            dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
            u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(sm,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
            q=u.GeometryScript_MeshQueries;lu=u.GeometryScript_List
            positions=next(x for x in q.get_all_vertex_positions(dm,False) if isinstance(x,u.GeometryScriptVectorList))
            triangles=next(x for x in q.get_all_triangle_indices(dm,False) if isinstance(x,u.GeometryScriptTriangleList))
            info['vertices']=[v(a) for a in lu.convert_vector_list_to_array(positions)]
            info['triangles']=[[a.x,a.y,a.z] for a in lu.convert_triangle_list_to_array(triangles)]
        except Exception as e:errors.append(dict(mesh=p,error=str(e)))
for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
    label=a.get_actor_label();loc,extent=a.get_actor_bounds(False)
    inventory.append(dict(label=label,cls=a.get_class().get_path_name(),p=v(loc),extent=v(extent)))
    native=label.startswith('NBPCG_');bank=label.startswith('NB28_')
    nearby=(loc.x+extent.x>=-55000 and loc.x-extent.x<=55000 and loc.y+extent.y>=-56000 and loc.y-extent.y<=13000 and loc.z+extent.z>=-12500)
    if not(native or bank or nearby):continue
    for c in a.get_components_by_class(u.StaticMeshComponent):
        sm=c.static_mesh
        if not sm:continue
        if isinstance(c,u.InstancedStaticMeshComponent):
            transforms=[tr(c.get_instance_transform(i,True)) for i in range(c.get_instance_count())]
            stride=c.get_editor_property('num_custom_data_floats')
            custom_count=len(c.get_editor_property('per_instance_sm_custom_data'))
        else:transforms=[tr(c.get_world_transform())];stride=custom_count=0
        if not transforms:continue
        mesh_info(sm)
        rows.append(dict(actor=label,component=c.get_name(),native=native,mesh=sm.get_path_name(),materials=[m.get_path_name() if m else None for m in c.get_materials()],transforms=transforms,collision=str(c.get_collision_enabled()),profile=str(c.get_collision_profile_name()),mobility=str(prop(c,'mobility')),visible=prop(c,'visible'),hidden_in_game=prop(c,'hidden_in_game'),custom_stride=stride,custom_count=custom_count))
result=dict(map=world.get_path_name(),captured_at=datetime.now().astimezone().isoformat(),rows=rows,meshes=meshes,actors=inventory,geometry_errors=errors,saves_performed=False)
(R/'saved_scene.json').write_text(json.dumps(result,separators=(',',':')),encoding='utf8')
print('APARTMENT_AUDIT_CAPTURED',len(inventory),len(rows),len(meshes),sum(len(x['transforms']) for x in rows if x['native']),'geometry_errors',len(errors),flush=True)
if errors:print('GEOMETRY_ERRORS',errors[:4],flush=True)
