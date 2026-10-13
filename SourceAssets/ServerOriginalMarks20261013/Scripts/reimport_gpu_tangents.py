"""Use the target engine's tangent builder for the revised GPU; preserve split normals."""
from pathlib import Path
import json
import unreal as u
ROOT=Path(__file__).resolve().parents[1]
if Path(u.Paths.project_dir()).resolve()!=(ROOT/'UEImportHost').resolve():raise RuntimeError('Staging host only')
manifest=json.loads((ROOT/'model_manifest.json').read_text('utf-8'))
report=json.loads((ROOT/'Receipts/ue-import.json').read_text('utf-8'))
spec=manifest['assets']['GPU'];name='SM_Search_TripleFanGPU_CSR3C'
dest='/Game/Items/ServerOriginalMarks20261013/Final/Meshes'
previous=next(m for m in report['meshes'] if m['item_id']==spec['id'])
options=u.FbxImportUI();options.import_mesh=True;options.import_as_skeletal=False
options.import_materials=False;options.import_textures=False;options.automated_import_should_detect_type=False
options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False
data.one_convex_hull_per_ucx=True;data.generate_lightmap_u_vs=True
data.convert_scene=True;data.convert_scene_unit=True;data.force_front_x_axis=False
data.import_uniform_scale=1;data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
task=u.AssetImportTask();task.filename=spec['fbx'];task.destination_path=dest;task.destination_name=name
task.automated=True;task.replace_existing=False;task.save=False;task.options=options;task.factory=u.FbxFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mesh=u.load_asset(dest+'/'+name)
if not mesh:raise RuntimeError('GPU import failed')
material=u.load_asset(previous['material'])
for index in range(len(mesh.static_materials)):mesh.set_material(index,material)
u.load_module('StaticMeshEditor');editor=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
settings=editor.get_lod_build_settings(mesh,0)
settings.recompute_normals=False;settings.recompute_tangents=True;settings.use_mikk_t_space=True
settings.remove_degenerates=True;settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
editor.set_lod_build_settings(mesh,0,settings)
nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=False;mesh.set_editor_property('nanite_settings',nanite)
u.EditorAssetLibrary.set_metadata_tag(mesh,'ServerOriginalMarks.Owner','ServerOriginalMarks20261013')
if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('GPU save failed')
previous.update(path=mesh.get_path_name(),tangent_frame='Imported split normals; UE MikkTSpace rebuilt tangents')
spec['mesh']=name;spec['tangent_frame']=previous['tangent_frame']
(ROOT/'model_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/'Receipts/ue-import.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
u.log('PROJECT_ORIGINAL_GPU_SAVED '+mesh.get_path_name())
