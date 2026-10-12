"""Restore the pants-hidden waist on both existing capri meshes, without PIE."""
import importlib.util,json
from pathlib import Path
import unreal as u

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/PlayerWaistSeam20261012'
AUTHOR=P/'SourceAssets/SmokeGreyCapri20261004'
R.mkdir(parents=True,exist_ok=True)
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.EditorLevelLibrary.get_pie_worlds(False):
    raise RuntimeError('Stop PIE before saving the waist repair')
spec=importlib.util.spec_from_file_location('capri_native_waist',str(P/'Tools/SmokeGreyCapri/native_waist.py'))
recipe=importlib.util.module_from_spec(spec);spec.loader.exec_module(recipe)
cfg=json.loads((P/'Content/ColdSteelData/modular_outfits.json').read_text(encoding='utf-8-sig'))
body_cfg=json.loads((P/'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
item=cfg['items']['ue_smoke_grey_capri']
base_path=cfg['profiles'][body_cfg['body_mesh']]['base']
covers=set(item['rig_world_covers']['Jason'])
G=u.GeometryScript_AssetUtils;Q=u.GeometryScript_MeshQueries;L=u.GeometryScript_List
B=u.GeometryScript_BoneWeights;E=u.GeometryScript_MeshEdits;LIB=u.EditorAssetLibrary
S=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem) or u.new_object(u.SkeletalMeshEditorSubsystem)

def copy_mesh(mesh):
    dm,status=G.copy_mesh_from_skeletal_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot read '+mesh.get_path_name())
    return dm

body=u.load_asset(base_path)
if not body:raise RuntimeError('Missing native body '+base_path)
dm=copy_mesh(body)
_,vectors,_=Q.get_all_vertex_positions(dm,False);ps=L.convert_vector_list_to_array(vectors)
_,indices,_=Q.get_all_triangle_indices(dm,False);ts=L.convert_triangle_list_to_array(indices)
_,bone_info=B.get_all_bones_info(dm)
faces=[];normals=[];uvs=[];skin_material=None
for ti,t in enumerate(ts):
    slot=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)[0]
    ids=[t.x,t.y,t.z]
    if slot not in covers or max(ps[i].z for i in ids)<=90.:continue
    material=body.materials[slot].material_interface
    if skin_material and material!=skin_material:raise RuntimeError('Waist crosses different skin materials')
    skin_material=material
    a,b,c,ok=Q.get_triangle_u_vs(dm,0,ti)
    if not ok:raise RuntimeError('Native waist UV missing')
    _,n0,n1,n2,ok=Q.get_triangle_normals(dm,ti)
    if not ok:raise RuntimeError('Native waist normals missing')
    faces.append(ids);uvs.append([[v.x,v.y] for v in [a,b,c]])
    normals.append([[v.x,v.y,v.z] for v in [n0,n1,n2]])
if not faces:raise RuntimeError('Native hidden waist faces missing')
used=sorted({vi for f in faces for vi in f});remap={vi:i for i,vi in enumerate(used)};weights=[]
for vi in used:
    _,ws,ok=B.get_vertex_bone_weights(dm,vi)
    if not ok:raise RuntimeError('Native waist binding missing')
    weights.append([[w.bone_index,w.weight] for w in ws if w.weight>0])
patch=dict(source=base_path,revision=recipe.REVISION,positions=[[ps[i].x,ps[i].y,ps[i].z] for i in used],
    triangles=[[remap[i] for i in f] for f in faces],weights=weights,uv=uvs,normals=normals,
    bones=[dict(index=b.index,name=str(b.name)) for b in bone_info],material=skin_material.get_path_name(),
    covered_sections=sorted(covers),inside_overlap_min_z_cm=90.)
(R/'native_waist.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')
(AUTHOR/'native_waist.json').write_text(json.dumps(patch,separators=(',',':')),encoding='utf-8')

paths=[item['rig_meshes']['Jason']]
for mapping in item.get('shoe_fit_meshes',{}).values():
    if mapping.get('Jason') and mapping['Jason'] not in paths:paths.append(mapping['Jason'])
saved=[]
for path in paths:
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing wearable capri '+path)
    if LIB.get_metadata_tag(mesh,recipe.REVISION)=='saved':
        saved.append(dict(asset=path,already_saved=True,added_triangles=len(faces),skin_material=patch['material'],lods=S.get_lod_count(mesh)));continue
    if len(mesh.materials)<=5 or mesh.materials[5].material_interface!=skin_material:
        raise RuntimeError('Unexpected native skin material on '+path)
    target=copy_mesh(mesh);_,bones=B.get_all_bones_info(target)
    destination={str(b.name):b.index for b in bones}
    bone_map={b['index']:destination[b['name']] for b in patch['bones']}
    # Keep the existing cloth/crotch/calf intact. Only append missing body faces.
    vertices=[];vertex_normals=[];vertex_uvs=[];vertex_weights=[];triangles=[];lookup={}
    for fi,face in enumerate(patch['triangles']):
        row=[]
        for ci,vi in enumerate(face):
            n=patch['normals'][fi][ci];uv=patch['uv'][fi][ci]
            key=(vi,*n,*uv)
            if key not in lookup:
                lookup[key]=len(vertices);vertices.append(u.Vector(*patch['positions'][vi]))
                vertex_normals.append(u.Vector(*n));vertex_uvs.append(u.Vector2D(*uv))
                vertex_weights.append([u.GeometryScriptBoneWeight(bone_index=bone_map[bi],weight=w) for bi,w in patch['weights'][vi]])
            row.append(lookup[key])
        triangles.append(u.IntVector(*row))
    buffer=u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=vertex_normals,uv0=vertex_uvs,triangles=triangles)
    _,new_list=E.append_buffers_to_mesh(target,buffer,5,True)
    new_ids=L.convert_index_list_to_array(new_list)
    if len(new_ids)!=len(triangles):raise RuntimeError('Incomplete waist append '+path)
    for ti,source_tri in zip(new_ids,triangles):
        indices,valid=Q.get_triangle_indices(target,ti)
        if not valid:raise RuntimeError('Missing appended waist face')
        for vi,source_vi in zip([indices.x,indices.y,indices.z],[source_tri.x,source_tri.y,source_tri.z]):
            _,valid=B.set_vertex_bone_weights(target,vi,vertex_weights[source_vi])
            if not valid:raise RuntimeError('Cannot bind native waist')
    options=u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(target,mesh,options,u.GeometryScriptMeshWriteLOD())
    if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot write waist '+path)
    # Retain the existing distance budget and locked boundary edges in each LOD.
    if not u.FPSModularOutfitComponent.configure_outfit_lods(mesh):raise RuntimeError('Cannot configure capri LODs')
    if not S.regenerate_lod(mesh,3,True,False):raise RuntimeError('Cannot rebuild capri LODs')
    LIB.set_metadata_tag(mesh,recipe.REVISION,'saved')
    LIB.set_metadata_tag(mesh,'NativeWaistSource',base_path)
    LIB.set_metadata_tag(mesh,'NativeWaistMethod','Pants-hidden faces only; unchanged native position, UV, normal and binding; inward waistband overlap')
    if not LIB.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save '+path)
    saved.append(dict(asset=path,added_triangles=len(faces),skin_material=patch['material'],lods=S.get_lod_count(mesh)))
    print('CAPRI_WAIST_SAVED '+path,flush=True)

# Update editable source data as well, so a later capri rebuild retains the fix.
for name in ['Jason_SmokeGreyCapri','Jason_SmokeGreyCapri_HighBootsFit']:
    file=AUTHOR/(name+'.json');data=json.loads(file.read_text(encoding='utf-8'))
    recipe.append_native_waist(data,patch)
    file.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
(R/'saved.json').write_text(json.dumps(dict(revision=recipe.REVISION,source=base_path,assets=saved,
    runtime_tested=False,source_geometry_updated=True,icon_and_pickup_unchanged=True),indent=2),encoding='utf-8')
print('CAPRI_WAIST_REPAIR_COMPLETE',flush=True)
