"""Save just ALICE geometry/lining; retain the existing four PBR materials and mount."""
import unreal as u
import json,hashlib,shutil,importlib.util,struct
from pathlib import Path

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/BackpacksReview20261021'
data=json.loads((R/'alice_authored.json').read_text());old=json.loads((R/'alice_ue_before.json').read_text())
spec=importlib.util.spec_from_file_location('backpack_winding',P/'Tools/BackpackHarness/winding.py')
winding=importlib.util.module_from_spec(spec);spec.loader.exec_module(winding)
data=winding.to_unreal(data)
path=old['asset'];mesh=u.load_asset(path)
checks=json.loads((R/'alice_geometry_checks.json').read_text())
if not checks['passed'] or checks['sha256']!=hashlib.sha256((R/'alice_authored.json').read_bytes()).hexdigest():raise RuntimeError('Finish the requested source checks first')
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    if u.EditorLevelLibrary.get_pie_worlds(False):raise RuntimeError('Cannot replace the worn pack during PIE')
    dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if path.split('.')[0] in dirty:raise RuntimeError('ALICE has unsaved editor edits')
disk=P/'Content'/(path.split('.')[0].removeprefix('/Game/')+'.uasset')
backup=R/'Before/SM_AliceBackpack.uasset';backup.parent.mkdir(parents=True,exist_ok=True)
if not backup.exists():shutil.copy2(disk,backup)
L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary;dest=path.rsplit('/',1)[0]
mat_path=dest+'/M_Alice_PocketLining';mat=u.load_asset(mat_path)
if not mat:
    mat=u.AssetToolsHelpers.get_asset_tools().create_asset('M_Alice_PocketLining',dest,u.Material,u.MaterialFactoryNew())
    color=L.create_material_expression(mat,u.MaterialExpressionConstant3Vector);color.set_editor_property('constant',u.LinearColor(.018,.021,.014,1));L.connect_material_property(color,'',u.MaterialProperty.MP_BASE_COLOR)
    rough=L.create_material_expression(mat,u.MaterialExpressionConstant);rough.set_editor_property('r',.94);L.connect_material_property(rough,'',u.MaterialProperty.MP_ROUGHNESS)
    if L.recompile_material(mat):raise RuntimeError('Lining material compile failed')
    if not E.save_loaded_asset(mat,False):raise RuntimeError('Cannot save lining')
corrected_normals=0
# Static render positions are float32. Evaluate tiny bevel faces in that same
# precision, and repair only faces whose retained normals oppose UE winding.
for fi,face in enumerate(data['triangles']):
    p=[struct.unpack('fff',struct.pack('fff',*data['positions'][vi])) for vi in face]
    e1=[p[1][i]-p[0][i] for i in range(3)];e2=[p[2][i]-p[0][i] for i in range(3)]
    n=[e2[1]*e1[2]-e2[2]*e1[1],e2[2]*e1[0]-e2[0]*e1[2],e2[0]*e1[1]-e2[1]*e1[0]]
    length=sum(x*x for x in n)**.5
    if length<=1e-12:continue
    n=[x/length for x in n];mean=[sum(row[i] for row in data['normals'][fi])/3 for i in range(3)]
    if sum(a*b for a,b in zip(n,mean))<0:
        data['normals'][fi]=[n]*3;corrected_normals+=1
vertices=[];normals=[];uv=[];faces=[];lookup={}
for fi,face in enumerate(data['triangles']):
    ids=[]
    for ci,vi in enumerate(face):
        n=data['normals'][fi][ci];tex=data['uv'][fi][ci];key=(vi,*n,*tex)
        if key not in lookup:
            lookup[key]=len(vertices);vertices.append(u.Vector(*data['positions'][vi]));normals.append(u.Vector(*n));uv.append(u.Vector2D(*tex))
        ids.append(lookup[key])
    faces.append(u.IntVector(*ids))
dm=u.DynamicMesh();u.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,u.GeometryScriptSimpleMeshBuffers(vertices=vertices,normals=normals,uv0=uv,triangles=faces),0,True)
for fi,mi in enumerate(data['triangle_materials']):u.GeometryScript_Materials.set_triangle_material_id(dm,fi,mi,True)
mats=[u.load_asset(row['asset']) for row in old['materials']]+[mat]
options=u.GeometryScriptCopyMeshToAssetOptions(replace_materials=True,new_materials=mats,
    new_material_slot_names=[row['slot'] for row in old['materials']]+['AlicePocketLining'],enable_recompute_normals=False,enable_recompute_tangents=True)
_,status=u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm,mesh,options,u.GeometryScriptMeshWriteLOD(lod_index=0))
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Cannot save ALICE source mesh')
E.set_metadata_tag(mesh,'AliceSidePocketsRevision',data['revision'])
E.set_metadata_tag(mesh,'AliceSidePocketsSource',str(R/'alice_authored.json'))
E.set_metadata_tag(mesh,'AliceFrontFaceConvention',winding.UE_CONVENTION)
if not E.save_loaded_asset(mesh,False):raise RuntimeError('ALICE package did not save')
readback,status=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS or readback.get_triangle_count()!=dm.get_triangle_count():raise RuntimeError('ALICE saved geometry count mismatch')
receipt=dict(saved=True,asset=path,revision=data['revision'],triangles=dm.get_triangle_count(),materials=[m.get_path_name() for m in mats],
    source_sha256=hashlib.sha256((R/'alice_authored.json').read_bytes()).hexdigest(),bounds=str(mesh.get_bounds()),runtime_tested=False,
    ue_front_face_convention=winding.UE_CONVENTION,corrected_normal_faces=corrected_normals)
(R/'alice_saved_assets.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('ALICE_SIDE_POCKETS_SAVED',json.dumps(receipt),flush=True)
