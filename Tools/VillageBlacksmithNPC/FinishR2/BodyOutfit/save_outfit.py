"""Rebuild this revision's private skeletal workwear package against the same R4 skeleton."""
import json
from pathlib import Path
import unreal as u

root=Path(__file__).resolve().parents[4]
out=root/'SourceAssets/VillageBlacksmithNPC20261118/FinishR2/BodyOutfit'
folder='/Game/Characters/VillageBlacksmithNPC20261118'
target=u.load_asset(folder+'/SK_Smith_Outfit')
body=u.load_asset(folder+'/SK_Smith_Body')
g=u.GeometryScript_AssetUtils
binding=u.GeometryScript_BoneWeights
ref,result=g.copy_mesh_from_skeletal_mesh(body,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD(lod_index=0))
if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('R4 reference mesh unavailable')
d=json.loads((out/'outfit.json').read_text())
points=[];normals=[];uvs=[];weights=[];triangles=[];lookup={}
for i,tri in enumerate(d['triangles']):
    row=[]
    for k,v in enumerate(tri):
        uv=d['uv'][i][k];n=d['normals'][i][k];key=(v,*uv,*n)
        if key not in lookup:
            lookup[key]=len(points)
            points.append(u.Vector(*d['positions'][v]));normals.append(u.Vector(*n));uvs.append(u.Vector2D(*uv));weights.append(d['weights'][v])
        row.append(lookup[key])
    triangles.append(u.IntVector(*row))
dm=u.DynamicMesh()
buf=u.GeometryScriptSimpleMeshBuffers(vertices=points,normals=normals,uv0=uvs,triangles=triangles)
u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,buf,0,True)
binding.copy_bones_from_mesh(ref,dm);binding.mesh_create_bone_weights(dm)
for i,ww in enumerate(weights):
    binding.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=idx,weight=w) for idx,w in ww])
api=u.GeometryScript_Materials
set_materials=next(getattr(api,name) for name in dir(api) if name.lower().replace('_','')=='setalltrianglematerialids')
set_materials(dm,u.GeometryScript_List.convert_array_to_index_list(d['triangle_materials'],u.GeometryScriptIndexType.MATERIAL_ID),True)
names=d['material_slots']
mats=[u.load_asset(folder+'/BodyOutfit/Materials/M_Smith_'+name) for name in names]
if not all(mats):raise RuntimeError('Missing workwear material')
opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=names,
    enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_,result=g.copy_mesh_to_skeletal_mesh(dm,target,opts,u.GeometryScriptMeshWriteLOD(lod_index=0))
if result!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot replace workwear LOD0')
sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
lod_count=sub.get_lod_count(target)
if lod_count!=3 or not sub.regenerate_lod(target,lod_count,True,False):raise RuntimeError('Workwear LOD generation failed')
if not u.EditorAssetLibrary.save_loaded_asset(target,False):raise RuntimeError('UE did not save workwear')
report={'asset':target.get_path_name(),'skeleton':target.skeleton.get_path_name(),'lod_count':lod_count,'authored_triangles':len(triangles),'materials':[m.get_path_name() for m in mats]}
(out/'mesh_saved.json').write_text(json.dumps(report,indent=2))
print('SMITH_PATTERN_R2_SAVED',target.get_path_name(),lod_count,flush=True)

