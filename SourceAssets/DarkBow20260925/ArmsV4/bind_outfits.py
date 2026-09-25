"""Bind existing accepted clothes to the new Bow skeleton and register its profile."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).parent;ROOT=P.parents[2];D='/Game/Weapons/DarkBow20260925/ArmsV4'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools();G=u.GeometryScript_AssetUtils
Q=u.GeometryScript_MeshQueries;B=u.GeometryScript_BoneWeights
path=ROOT/'Content/ColdSteelData/modular_outfits.json'
config=json.loads(path.read_text(encoding='utf-8-sig'))
source_profile=next(v for v in config['profiles'].values() if v['rig_profile']=='M4')
bow=u.load_asset(D+'/SK_Bow_BareArmsV7')
native,status=G.copy_mesh_from_skeletal_mesh(bow,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
_,bones=B.get_all_bones_info(native);ids={str(b.name):b.index for b in bones}
receipt_path=P/'outfit_receipt.json'
result=json.loads(receipt_path.read_text())['saved'] if receipt_path.exists() else {}
def rotate(p):return u.Vector(-p.y,p.x,p.z)
for label,source in (('Sleeves',source_profile['shirt']),('FieldGloves',source_profile['gloves']),('OriginalGlovedArms',source_profile['original_gloved_arms'])):
    name='SK_Bow_'+label;target=D+'/Outfits/'+name
    if label in result:continue
    if E.does_asset_exist(target):raise RuntimeError('Preserve existing outfit candidate '+target)
    original=u.load_asset(source)
    dm,status=G.copy_mesh_from_skeletal_mesh(original,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read outfit '+label)
    _,bones=B.get_all_bones_info(dm);names={b.index:str(b.name) for b in bones}
    _,pos,_=Q.get_all_vertex_positions(dm,False);positions=u.GeometryScript_List.convert_vector_list_to_array(pos)
    _,tris,_=Q.get_all_triangle_indices(dm,False);faces=u.GeometryScript_List.convert_triangle_list_to_array(tris)
    vertex_weights={}
    used={v for f in faces for v in (f.x,f.y,f.z)}
    for i in used:
        _,weights,valid=B.get_vertex_bone_weights(dm,i)
        vertex_weights[i]=[u.GeometryScriptBoneWeight(bone_index=ids[names[w.bone_index]],weight=w.weight) for w in weights if w.weight>0]
    vertices=[];normals=[];uvs=[[],[],[],[]];weights=[];triangles=[];mats=[]
    channels=min(4,Q.get_num_uv_sets(dm))
    for i,f in enumerate(faces):
        base=len(vertices)
        _,a,b,c,valid=Q.get_triangle_normals(dm,i);normals.extend(rotate(v) for v in (a,b,c))
        for vi in (f.x,f.y,f.z):vertices.append(rotate(positions[vi]));weights.append(vertex_weights[vi])
        for ch in range(4):
            if ch<channels:
                a,b,c,valid=Q.get_triangle_u_vs(dm,ch,i);uvs[ch].extend((a,b,c))
            else:uvs[ch].extend([u.Vector2D(0,0)]*3)
        mats.append(u.GeometryScript_Materials.get_triangle_material_id(dm,i)[0]);triangles.append(u.IntVector(base,base+1,base+2))
    out=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(out,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uvs[0],uv1=uvs[1],uv2=uvs[2],uv3=uvs[3],triangles=triangles),0,True)
    B.copy_bones_from_mesh(native,out);B.mesh_create_bone_weights(out)
    for i,w in enumerate(weights):B.set_vertex_bone_weights(out,i,w)
    for i,m in enumerate(mats):u.GeometryScript_Materials.set_triangle_material_id(out,i,m,True)
    asset=A.duplicate_asset(name,D+'/Outfits',bow)
    options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,
        new_materials=[s.material_interface for s in original.materials],new_material_slot_names=[s.material_slot_name for s in original.materials],
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(out,asset,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot bind outfit '+label)
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save outfit '+label)
    result[label]=asset.get_path_name()
    (P/'outfit_receipt.json').write_text(json.dumps({'saved':result,'runtime_tested':False},indent=2),encoding='utf-8')
# Read the shared config again at publication time; preserve parallel entries.
config=json.loads(path.read_text(encoding='utf-8-sig'))
base=bow.get_path_name()
config['profiles'][base]={'rig_profile':'Bow','base':base,'native_bare_skin':base,'bare_arms_candidate':base,
    'native_bare_arms':True,'hide_source_materials':[0,1,2],'shirt_covers':[0,1],'glove_covers':[2],
    'shirt':result['Sleeves'],'gloves':result['FieldGloves'],'original_gloved_arms':result['OriginalGlovedArms']}
for key,recipe in config['items'].items():
    if 'rig_meshes' in recipe and recipe['rig_meshes'].get('M4'):
        recipe['rig_meshes']['Bow']=result['Sleeves' if recipe['part']=='shirt' else 'FieldGloves']
path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('BOW_OUTFITS_BOUND_AND_PROFILE_SAVED',len(result))
