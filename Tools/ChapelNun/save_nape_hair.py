"""Author and save the skinned nape addition using the actual active head and collar."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unreal as u

project = Path(__file__).resolve().parents[2]
out = project/'SourceAssets/ChapelNun20261115/NapeHairR10'
out.mkdir(parents=True, exist_ok=True)
destination = '/Game/Characters/ChapelNun20261115/NapeHairR10'
head_path = '/Game/Characters/ChapelNun20261115/RefinementR4/Meshes/SK_Nun_OriginalMeshyFace_Final'
collar_path = '/Game/Characters/ChapelNun20261115/Meshes/SK_Nun_PlainCollar_R7'
E = u.EditorAssetLibrary
G = u.GeometryScript_AssetUtils
Q = u.GeometryScript_MeshQueries
L = u.GeometryScript_List
B = u.GeometryScript_BoneWeights
M = u.MaterialEditingLibrary
A = u.AssetToolsHelpers.get_asset_tools()

def surface(asset):
    mesh, result = G.copy_mesh_from_skeletal_mesh(asset,u.DynamicMesh(),
        u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
    if result != u.GeometryScriptOutcomePins.SUCCESS:
        raise RuntimeError('Cannot read geometry from '+asset.get_path_name())
    _, values, _ = Q.get_all_vertex_positions(mesh,False)
    return mesh, [(p.x,p.y,p.z) for p in L.convert_vector_list_to_array(values)]

def save(asset):
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Save failed '+asset.get_path_name())

head = u.load_asset(head_path)
reference, points = surface(head)
collar, collar_points = surface(u.load_asset(collar_path))
collar_top = max(p[2] for p in collar_points if p[1]<0 and abs(p[0])<8)
_, values, _ = Q.get_all_triangle_indices(reference,False)
faces=[]
for t in L.convert_triangle_list_to_array(values):
    tri=(t.x,t.y,t.z)
    if all(143 < points[i][2] < 162 and points[i][1]<3.2 for i in tri):
        faces.append(tri)
indices=sorted({i for face in faces for i in face})
remap={v:i for i,v in enumerate(indices)}
_, info=B.get_all_bones_info(reference)
bone_names={b.index:str(b.name) for b in info}
weights=[]
for i in indices:
    _, blend, valid=B.get_vertex_bone_weights(reference,i)
    if not valid:
        raise RuntimeError('Missing head skin weight '+str(i))
    weights.append([(w.bone_index,w.weight) for w in blend])
source=dict(positions=[points[i] for i in indices],triangles=[[remap[i] for i in tri] for tri in faces],
            weights=weights,bone_names=bone_names,collar_top=collar_top,head=head_path,collar=collar_path)
with tempfile.TemporaryDirectory(prefix='NunNapeHair-') as temp:
    input_file = Path(temp)/'skin.json'
    input_file.write_text(json.dumps(source,separators=(',',':')),encoding='utf-8')
    blender = os.environ.get('BLENDER_EXE','E:/Program Files/Blender Foundation/Blender 5.1/blender.exe')
    job = subprocess.run([blender,'-b','--factory-startup','--python-exit-code','1','-P',
                    str(Path(__file__).with_name('author_nape_hair.py')),'--',str(input_file),str(out)],
                   creationflags=subprocess.CREATE_NO_WINDOW,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    if job.returncode:
        raise RuntimeError('Blender nape authoring failed: '+job.stdout.decode('utf-8','replace')[-4500:])

E.make_directory(destination)
task=u.AssetImportTask()
task.filename=str(out/'T_Nun_NapeFibres_R10.png')
task.destination_path=destination
task.destination_name='T_Nun_NapeFibres_R10'
task.automated=True
task.replace_existing=True
task.save=False
A.import_asset_tasks([task])
texture=u.load_asset(destination+'/T_Nun_NapeFibres_R10')
texture.set_editor_property('compression_no_alpha', False)
texture.set_editor_property('do_scale_mips_for_alpha_coverage', True)
texture.set_editor_property('alpha_coverage_thresholds', u.Vector4(0,0,0,.30))
texture.set_editor_property('address_x', u.TextureAddress.TA_CLAMP)
texture.set_editor_property('address_y', u.TextureAddress.TA_CLAMP)
save(texture)
mat=E.load_asset(destination+'/M_Nun_NapeFibres_R10') if E.does_asset_exist(destination+'/M_Nun_NapeFibres_R10') else A.create_asset('M_Nun_NapeFibres_R10',destination,u.Material,u.MaterialFactoryNew())
M.delete_all_material_expressions(mat)
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_MASKED)
mat.set_editor_property('two_sided',True)
mat.set_editor_property('opacity_mask_clip_value',.30)
M.set_material_usage(mat,u.MaterialUsage.MATUSAGE_SKELETAL_MESH)
sample=M.create_material_expression(mat,u.MaterialExpressionTextureSample)
sample.set_editor_property('texture',texture)
def connect(node, channel, prop):
    if not M.connect_material_property(node,channel,prop):
        raise RuntimeError('Missing material output '+str(prop))
connect(sample,'RGB',u.MaterialProperty.MP_BASE_COLOR)
connect(sample,'A',u.MaterialProperty.MP_OPACITY_MASK)
for prop,value in [(u.MaterialProperty.MP_ROUGHNESS,.47),(u.MaterialProperty.MP_SPECULAR,.36)]:
    scalar=M.create_material_expression(mat,u.MaterialExpressionConstant)
    scalar.set_editor_property('r',value)
    connect(scalar,'',prop)
M.recompile_material(mat)
save(mat)
d=json.loads((out/'nape_cards.json').read_text(encoding='utf-8'))
dm=u.DynamicMesh()
buffer=u.GeometryScriptSimpleMeshBuffers(vertices=[u.Vector(*p) for p in d['positions']],
    normals=[u.Vector(*p) for p in d['normals']],uv0=[u.Vector2D(*p) for p in d['uv']],
    triangles=[u.IntVector(*tri) for tri in d['triangles']])
u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,buffer,0,True)
B.copy_bones_from_mesh(reference,dm)
B.mesh_create_bone_weights(dm)
for i,blend in enumerate(d['weights']):
    B.set_vertex_bone_weights(dm,i,[u.GeometryScriptBoneWeight(bone_index=k,weight=w) for k,w in blend])
path=destination+'/SK_Nun_NapeHair_R10'
if E.does_asset_exist(path):
    mesh=E.load_asset(path)
    opts=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=[mat],new_material_slot_names=['NapeHair'],
        enable_recompute_normals=False,enable_recompute_tangents=True,
        bone_hierarchy_mismatch_handling=u.GeometryScriptBoneHierarchyMismatchHandling.REMAP_GEOMETRY_TO_REFERENCE_SKELETON)
    _,status=G.copy_mesh_to_skeletal_mesh(dm,mesh,opts,u.GeometryScriptMeshWriteLOD())
else:
    opts=u.GeometryScriptCreateNewSkeletalMeshAssetOptions()
    opts.use_mesh_bone_proportions=True
    opts.enable_recompute_normals=False
    opts.enable_recompute_tangents=True
    opts.materials={'NapeHair':mat}
    mesh,status=u.GeometryScript_NewAssetUtils.create_new_skeletal_mesh_asset_from_mesh(dm,head.skeleton,path,opts)
if status!=u.GeometryScriptOutcomePins.SUCCESS or not mesh:
    raise RuntimeError('Failed to save skinned nape locks')
save(mesh)
(out/'saved.json').write_text(json.dumps(dict(mesh=mesh.get_path_name(),texture=texture.get_path_name(),
    material=mat.get_path_name(),leader=head.get_path_name(),source_vertices=len(d['positions']),
    triangles=len(d['triangles'])),indent=2),encoding='utf-8')
print('NUN_NAPE_ASSETS_SAVED',path,flush=True)
