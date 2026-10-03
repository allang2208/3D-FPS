"""Separate Jason's duplicated face/proxy surfaces from the replaceable head."""
import json
from pathlib import Path
import unreal as u
import runpy
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/JasonPlayer20261003')
saved=json.loads((ROOT/'outfit_assets_saved.json').read_text())
base=u.load_asset(saved['base']);native=u.load_asset('/Game/AsianMale_Jason/Mesh/Body/SKM_Jason_body')
dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(base,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
remove=[]
for ti in range(dm.get_triangle_count()):
    material,valid=u.GeometryScript_Materials.get_triangle_material_id(dm,ti)
    if valid and material in (5,6):remove.append(ti)
u.GeometryScript_MeshEdits.delete_triangles_from_mesh(dm,u.GeometryScript_List.convert_array_to_index_list(remove),True)
_,status=u.GeometryScript_AssetUtils.copy_mesh_to_skeletal_mesh(dm,base,
    u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=True),u.GeometryScriptMeshWriteLOD())
if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError('Body write failed')
base.set_editor_property('post_process_anim_blueprint',native.get_editor_property('post_process_anim_blueprint'))
u.FPSModularOutfitComponent.configure_outfit_lods(base)
if not u.SkeletalMeshEditorSubsystem.regenerate_lod(base,3,True,False):raise RuntimeError('Body LOD build failed')
if not u.EditorAssetLibrary.save_loaded_asset(base,False):raise RuntimeError('Body save failed')
face_material=runpy.run_path('D:/FPS3D/FPSGAME/Tools/PlayerBody/build_jason_face_material.py')['build']()
receipt={'body':base.get_path_name(),'removed_duplicate_face_and_proxy_triangles':len(remove),
    'body_triangles':dm.get_triangle_count(),'body_lods':u.SkeletalMeshEditorSubsystem.get_lod_count(base),
    'head':'/Game/AsianMale_Jason/Mesh/Head/SKM_Jason_head.SKM_Jason_head',
    'head_face_material':face_material.get_path_name(),
    'head_lods':1,'ml_deformer_enabled':False}
(ROOT/'body_saved.json').write_text(json.dumps(receipt,indent=2))
print('JASON_MODULAR_BODY_SAVED '+json.dumps(receipt),flush=True)
