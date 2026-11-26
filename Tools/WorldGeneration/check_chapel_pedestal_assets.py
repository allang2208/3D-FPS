"""User-requested read-only check of the saved shrine support assets."""
import gc
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
import unreal as u

ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/ChapelShrineForecourt20261116/WallStoneR3/Check'
OUT.mkdir(parents=True,exist_ok=True)
G,Q,L=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List
E=u.MaterialEditingLibrary
report={'checks':{},'statues':[],'visual_runtime_checked':False}
xyz=lambda v:[v.x,v.y,v.z]
def check(name,ok,detail=None):
    report['checks'][name]={'pass':bool(ok),'detail':detail}
def geometry(mesh):
    dm,status=G.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(mesh.get_path_name())
    _,vs,_=Q.get_all_vertex_positions(dm,False)
    _,ts,_=Q.get_all_triangle_indices(dm,False)
    return dm,list(L.convert_vector_list_to_array(vs)),list(L.convert_triangle_list_to_array(ts))
mesh=u.load_asset('/Game/WorldGeneration/HillsNightRaid/SM_ChapelShrineRockPedestal')
dm,vs,ts=geometry(mesh)
edges=Counter();bad_winding=bad_uv=degenerate=top=0
for ti,t in enumerate(ts):
    points=[vs[int(i)] for i in (t.x,t.y,t.z)]
    cross=(points[1]-points[0]).cross(points[2]-points[0])
    if cross.length()<.0001:degenerate+=1
    _,na,nb,nc,valid=Q.get_triangle_normals(dm,ti)
    if not valid or cross.dot(na+nb+nc)>=0:bad_winding+=1
    a,b,c,valid=Q.get_triangle_u_vs(dm,0,ti)
    if not valid or abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))<1e-10:bad_uv+=1
    if all(abs(p.z-34.)<.001 for p in points):
        top+=1
        if cross.z>=0 or min(na.z,nb.z,nc.z)<.99:bad_winding+=1
    keys=[tuple(round(v,3) for v in xyz(p)) for p in points]
    for a,b in ((0,1),(1,2),(2,0)):edges[tuple(sorted((keys[a],keys[b])))]+=1
check('closed_non_degenerate_mesh',not degenerate and all(n==2 for n in edges.values()),{'triangles':len(ts),'degenerate':degenerate,'unpaired_edges':sum(n!=2 for n in edges.values())})
check('outward_ue_winding_and_top_normals',bad_winding==0 and top>0,{'bad_faces':bad_winding,'top_triangles':top})
check('non_degenerate_uv0',bad_uv==0,{'bad_faces':bad_uv})
check('complex_support_collision',mesh.get_editor_property('body_setup').get_editor_property('collision_trace_flag')==u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
b=mesh.get_bounding_box();support=-4.-b.min.z+b.max.z
report['pedestal']={'min':xyz(b.min),'max':xyz(b.max),'support_above_ground_cm':support}
check('support_height',abs(support-30.)<.001)
mat=mesh.get_material(0)
check('dedicated_stone_bound',mat.get_name()=='M_ChapelShrinePedestalStone')
check('opaque_surface_without_decal_response',mat.get_editor_property('material_domain')==u.MaterialDomain.MD_SURFACE and mat.get_editor_property('blend_mode')==u.BlendMode.BLEND_OPAQUE and mat.get_editor_property('material_decal_response')==u.MaterialDecalResponse.MDR_NONE)
nodes=list(E.get_material_expressions(mat));graph=[];textures=[]
for n in nodes:
    row={'name':n.get_name(),'class':n.get_class().get_name(),'inputs':[x.get_name() if x else None for x in E.get_inputs_for_material_expression(mat,n)]}
    if isinstance(n,u.MaterialExpressionTextureSample):
        tex=n.get_editor_property('texture');row['texture']=tex.get_path_name() if tex else None
        row['sampler']=str(n.get_editor_property('sampler_type'));textures.append(row['texture'])
    if isinstance(n,u.MaterialExpressionTextureCoordinate):row['uv_index']=n.get_editor_property('coordinate_index')
    graph.append(row)
report['material_graph']=graph
expected=['/Game/UnrealNormandy/Textures/T_StoneSurface_01A_'+suffix+'.T_StoneSurface_01A_'+suffix for suffix in ('BaseColor','Normal','RHAOM','Height')]
check('all_stone_textures_present',sorted(textures)==sorted(expected),textures)
check('no_world_projection_nodes',not any(any(token in r['class'] for token in ('WorldPosition','RuntimeVirtualTexture','Decal','SceneTexture')) for r in graph))
props={}
for name in ('BASE_COLOR','NORMAL','ROUGHNESS','AMBIENT_OCCLUSION','SPECULAR','WORLD_POSITION_OFFSET'):
    prop=getattr(u.MaterialProperty,'MP_'+name);n=E.get_material_property_input_node(mat,prop)
    props[name]={'node':n.get_name() if n else None,'output':str(E.get_material_property_input_node_output_name(mat,prop)) if n else None}
report['material_outputs']=props
check('surface_outputs_connected',all(props[p]['node'] for p in ('BASE_COLOR','NORMAL','ROUGHNESS','AMBIENT_OCCLUSION','SPECULAR')))
check('no_vertex_displacement',not props['WORLD_POSITION_OFFSET']['node'])
del dm,vs,ts;gc.collect()
source=(ROOT/'Source/FPSGAME/WorldGeneration/ChapelShrine.cpp').read_text(encoding='utf-8')
seat=float(re.search(r'constexpr double StatueSeatDepth=([\d.]+);',source).group(1))
report['statue_seat_depth_cm']=seat
for row in json.loads((ROOT/'Content/ColdSteelData/shrines.json').read_text(encoding='utf-8'))['statues']:
    statue=u.load_asset(row['mesh']);sb=statue.get_bounding_box();sdm,positions,_=geometry(statue)
    actual_min=min(v.z for v in positions)
    gap=(actual_min-sb.min.z)*2.-seat
    radius=max(180.,(math.hypot(sb.max.x-sb.min.x,sb.max.y-sb.min.y)+25.)/.82)
    report['statues'].append({'id':row['id'],'actual_contact_gap_cm':gap,'pedestal_radius_cm':radius,'ground_to_statue_min_cm':support+gap})
    check('contact_'+row['id'],-1.1<=gap<=.1,{'gap_cm':gap})
    del sdm,positions;gc.collect()
report['asset_sha256']={name:hashlib.sha256((ROOT/'Content/WorldGeneration/HillsNightRaid'/(name+'.uasset')).read_bytes()).hexdigest() for name in ('SM_ChapelShrineRockPedestal','M_ChapelShrinePedestalStone')}
report['passed']=all(c['pass'] for c in report['checks'].values())
(OUT/'saved-assets.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('CHAPEL_SUPPORT_ASSET_CHECK '+json.dumps({'passed':report['passed'],'checks':len(report['checks']),'failed':[k for k,v in report['checks'].items() if not v['pass']]}))
if not report['passed']:raise RuntimeError('Saved asset check failed; see saved-assets.json')
