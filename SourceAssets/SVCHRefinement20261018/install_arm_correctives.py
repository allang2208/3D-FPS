"""Restore the native V9 arm corrective shapes lost by the FBX handoff.

Exact rest-position correspondence transfers only arm vertices. The shared
runtime JointCorrective component already drives these JC_ names.
"""
from pathlib import Path
import json,math,itertools
import unreal as u
O=Path(__file__).parent
P=Path(u.Paths.project_dir()).resolve()
source=json.loads((P/'SourceAssets/BareSkinV9Rollout_20261017/Work/batch1/a0cd930b648e.json').read_text(encoding='utf-8'))
mesh=u.load_asset(globals().get('TARGET_MESH','/Game/Weapons/SVCH/Refined20261018/SK_SVCH_Refined_R4'))
G,Q,LU=u.GeometryScript_AssetUtils,u.GeometryScript_MeshQueries,u.GeometryScript_List
def pick(r,t):return next(v for v in r if isinstance(v,t))
def read_mesh():
    dm=u.DynamicMesh();lod=u.GeometryScriptMeshReadLOD();lod.lod_type=u.GeometryScriptLODType.SOURCE_MODEL
    G.copy_mesh_from_skeletal_mesh(mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(),lod)
    return dm
dm=read_mesh()
pos=LU.convert_vector_list_to_array(pick(Q.get_all_vertex_positions(dm,True),u.GeometryScriptVectorList))
tris=LU.convert_triangle_list_to_array(pick(Q.get_all_triangle_indices(dm,True),u.GeometryScriptTriangleList))
slots=LU.convert_index_list_to_array(pick(u.GeometryScript_Materials.get_all_triangle_material_i_ds(dm),u.GeometryScriptIndexList))
arms={i for t,s in zip(tris,slots) if s>=9 for i in (t.x,t.y,t.z)}
cell=.001
def key(p):return tuple(math.floor(x/cell) for x in p)
grid={}
for i in arms:grid.setdefault(key((pos[i].x,pos[i].y,pos[i].z)),[]).append(i)
baseline=dict(zip(source['vertex_ids'],source['positions']))
mapping={};max_error=0.
needed={int(row[0]) for rows in source['morphs'].values() for row in rows}
for vid in needed:
    p=baseline[vid];k=key(p);found=[]
    for offset in itertools.product((-1,0,1),repeat=3):
        for target in grid.get(tuple(k[j]+offset[j] for j in range(3)),[]):
            v=pos[target];error=math.sqrt(sum((a-b)**2 for a,b in zip((v.x,v.y,v.z),p)))
            if error<.0001:found.append(target);max_error=max(max_error,error)
    if not found:raise RuntimeError('Native corrective rest vertex has no exact SVCH correspondence: '+str(vid))
    mapping[vid]=found
names=list(source['morphs']);receipt={'asset':mesh.get_path_name(),'source':source['path'],
    'max_rest_match_error_cm':max_error,'morphs':{},'saved':False}
for index,name in enumerate(names):
    md=read_mesh();changed={}
    for vid,x,y,z,nx,ny,nz in source['morphs'][name]:
        origin=baseline[vid]
        delta=(x-origin[0],y-origin[1],z-origin[2])
        for target in mapping[vid]:changed[target]=(delta,(nx,ny,nz))
    for target,(delta,normal) in changed.items():
        v=pos[target]
        u.GeometryScript_MeshEdits.set_vertex_position(md,target,u.Vector(v.x+delta[0],v.y+delta[1],v.z+delta[2]),True)
        u.GeometryScript_Normals.update_vertex_normal(md,target,True,u.Vector(*normal),False,u.Vector(1,0,0),u.Vector(0,1,0),False,True)
    options=u.GeometryScriptCopyMorphTargetToAssetOptions(overwrite_existing_target=True,emit_transaction=False,
        defer_mesh_post_edit_change=index!=len(names)-1,copy_normals=True)
    result=G.copy_morph_target_to_skeletal_mesh(md,mesh,name,options,u.GeometryScriptMeshWriteLOD())
    if u.GeometryScriptOutcomePins.SUCCESS not in result:raise RuntimeError('Cannot copy '+name)
    receipt['morphs'][name]=len(changed)
saved_names={m.get_name() for m in mesh.get_editor_property('morph_targets')}
if not set(names)<=saved_names:raise RuntimeError('Corrective names missing')
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save arm correctives')
receipt['saved']=True
Path(globals().get('RECEIPT_PATH',O/'arm_correctives_receipt.json')).write_text(json.dumps(receipt,indent=1))
print('SVCH_NATIVE_ARM_CORRECTIVES_SAVED',json.dumps(receipt),flush=True)
