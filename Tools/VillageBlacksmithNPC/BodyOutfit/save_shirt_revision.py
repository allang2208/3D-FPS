"""Replace only the blacksmith's owned workwear LOD0 and regenerate its existing LODs."""
import json
import unreal as u
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit'
FOLDER='/Game/Characters/VillageBlacksmithNPC20261118'
o=u.load_asset(FOLDER+'/SK_Smith_Outfit')
source=u.load_asset(FOLDER+'/SK_Smith_Body')
g=u.GeometryScript_AssetUtils
bones=u.GeometryScript_BoneWeights
read=u.GeometryScriptMeshReadLOD(lod_index=0)
ref,status=g.copy_mesh_from_skeletal_mesh(source,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),read)
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise ValueError('Cannot read R4 bindings')
d=json.loads((OUT/'outfit.json').read_text())
if 'Workshirt yoke' not in d['parts']:raise ValueError('Missing workshirt pattern')
pos=[];norm=[];uv=[];weight=[];triangles=[];reuse={}
for fi,tri in enumerate(d['triangles']):
    out=[]
    for j,i in enumerate(tri):
        n=d['normals'][fi][j];tc=d['uv'][fi][j]
        key=(i,*[round(v,5) for v in n+tc])
        if key not in reuse:
            reuse[key]=len(pos);pos.append(u.Vector(*d['positions'][i]));norm.append(u.Vector(*n));uv.append(u.Vector2D(*tc));weight.append(d['weights'][i])
        out.append(reuse[key])
    triangles.append(u.IntVector(*out))
mesh=u.DynamicMesh()
u.GeometryScript_MeshEdits.append_buffers_to_mesh(mesh,u.GeometryScriptSimpleMeshBuffers(vertices=pos,normals=norm,uv0=uv,triangles=triangles),0,True)
bones.copy_bones_from_mesh(ref,mesh);bones.mesh_create_bone_weights(mesh)
for i,row in enumerate(weight):bones.set_vertex_bone_weights(mesh,i,[u.GeometryScriptBoneWeight(bone_index=int(k),weight=float(v)) for k,v in row if v>0])
for i,slot in enumerate(d['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(mesh,i,slot,True)
mats=[u.load_asset(FOLDER+'/BodyOutfit/Materials/M_Smith_'+slot) for slot in d['material_slots']]
if not all(mats):raise ValueError('Missing existing workwear material')
opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,new_material_slot_names=d['material_slots'],enable_recompute_normals=False,enable_recompute_tangents=True,bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
_,status=g.copy_mesh_to_skeletal_mesh(mesh,o,opts,u.GeometryScriptMeshWriteLOD(lod_index=0))
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise ValueError('Revised shirt fit write failed')
sub=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
if not sub.regenerate_lod(o,sub.get_lod_count(o),True,False):raise ValueError('Workwear LOD generation failed')
if not u.EditorAssetLibrary.save_loaded_asset(o,False):raise ValueError('Revised outfit package save failed')
print('SMITH_REVISED_SHIRT_SAVED',o.get_path_name(),flush=True)

