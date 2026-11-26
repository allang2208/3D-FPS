"""Read the reported pedestal geometry, material and existing scene projections."""
import json
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ChapelShrineForecourt20261116/SupportFixR2'
OUT.mkdir(parents=True,exist_ok=True)
xyz=lambda v:[v.x,v.y,v.z]
def prop(o,k):
    try:return str(o.get_editor_property(k))
    except Exception:return None
def material(m):
    if not m:return None
    base=m.get_base_material()
    return {'path':m.get_path_name(),'base':base.get_path_name(),
            **{k:prop(base,k) for k in ('material_domain','blend_mode','two_sided','decal_response')}}
report={'meshes':{},'shrines':[],'decals':[]}
G,Q,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List
for key,path in (
    ('pedestal','/Game/WorldGeneration/HillsNightRaid/SM_ChapelShrineRockPedestal'),
    ('engine_cylinder','/Engine/BasicShapes/Cylinder')):
    mesh=u.load_asset(path)
    b=mesh.get_bounding_box()
    dm,status=G.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(path)
    _,p,_=Q.get_all_vertex_positions(dm,False)
    _,t,_=Q.get_all_triangle_indices(dm,False)
    geo={'positions':[xyz(v) for v in L.convert_vector_list_to_array(p)],
         'triangles':[xyz(v) for v in L.convert_triangle_list_to_array(t)]}
    (OUT/(key+'-before.json')).write_text(json.dumps(geo),encoding='utf-8')
    report['meshes'][key]={'path':path,'min':xyz(b.min),'max':xyz(b.max),
        'materials':[material(s.material_interface) for s in mesh.get_editor_property('static_materials')]}
world=u.EditorLevelLibrary.get_game_world()
report['game_world']=world.get_path_name() if world else None
if world:
    actors=u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
    shrines=[a for a in actors if a.get_class().get_name()=='ChapelShrine']
    for actor in shrines:
        components=[]
        for c in actor.get_components_by_class(u.StaticMeshComponent):
            mesh=c.static_mesh
            o,e,r=u.SystemLibrary.get_component_bounds(c)
            components.append({'name':c.get_name(),'mesh':mesh.get_path_name() if mesh else None,
                'relative_location':xyz(c.get_editor_property('relative_location')),
                'scale':xyz(c.get_editor_property('relative_scale3d')),'origin':xyz(o),'extent':xyz(e),
                'receives_decals':prop(c,'receives_decals'),
                'materials':[material(c.get_material(i)) for i in range(c.get_num_materials())]})
        report['shrines'].append({'actor':actor.get_path_name(),'location':xyz(actor.get_actor_location()),'components':components})
    for actor in actors:
        for c in actor.get_components_by_class(u.DecalComponent):
            loc=c.get_world_location()
            size=c.get_editor_property('decal_size')
            scale=c.get_editor_property('relative_scale3d')
            reach=max(abs(size.x*scale.x),abs(size.y*scale.y),abs(size.z*scale.z))+700.
            if any((loc-s.get_actor_location()).length()<reach for s in shrines):
                report['decals'].append({'actor':actor.get_path_name(),'component':c.get_name(),
                    'location':xyz(loc),'size':xyz(size),'scale':xyz(scale),'material':material(c.get_decal_material())})
(OUT/'defect-inputs.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('CHAPEL_SUPPORT_DEFECT_INPUTS '+json.dumps(report,ensure_ascii=False))
