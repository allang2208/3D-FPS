"""Import only the corrected camera into an unused revision namespace."""
from pathlib import Path
import json,unreal as u
ROOT=Path(__file__).resolve().parents[1]
if Path(u.Paths.project_dir()).resolve()!=(ROOT/'UEImportHost').resolve():raise RuntimeError('Use owned content-only import host')
spec=json.loads((ROOT/'model_manifest.json').read_text('utf-8'))['assets']['Camera']
dest='/Game/Items/StaffLivingCollectibles20261016/V2/Meshes';path=dest+'/'+spec['mesh']
E=u.EditorAssetLibrary
if E.does_asset_exist(path):raise RuntimeError('Preserve existing V2 revision')
options=u.FbxImportUI();options.import_mesh=True;options.import_as_skeletal=False;options.import_materials=False;options.import_textures=False
options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
d=options.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.one_convex_hull_per_ucx=True
d.generate_lightmap_u_vs=False;d.convert_scene=True;d.convert_scene_unit=True;d.force_front_x_axis=False
d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;d.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
task=u.AssetImportTask();task.filename=spec['fbx'];task.destination_path=dest;task.destination_name=spec['mesh'];task.automated=True;task.save=False;task.replace_existing=False;task.options=options;task.factory=u.FbxFactory()
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);mesh=u.load_asset(path)
if not mesh:raise RuntimeError('Camera import failed')
mat=u.load_asset('/Game/Items/StaffLivingCollectibles20261016/V1/Materials/M_Living_Surface')
if not mat:raise RuntimeError('Existing surface material is missing')
for index in range(len(mesh.static_materials)):mesh.set_material(index,mat)
u.load_module('StaticMeshEditor');SM=u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
if not SM:SM=u.new_object(u.StaticMeshEditorSubsystem)
settings=SM.get_lod_build_settings(mesh,0);settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True;settings.recompute_tangents=True;settings.recompute_normals=False;settings.use_mikk_t_space=True;SM.set_lod_build_settings(mesh,0,settings)
nanite=mesh.get_editor_property('nanite_settings');nanite.enabled=True;nanite.explicit_tangents=True;nanite.generate_fallback=u.NaniteGenerateFallback.ENABLED;nanite.fallback_target=u.NaniteFallbackTarget.PERCENT_TRIANGLES;nanite.fallback_percent_triangles=1.;nanite.fallback_relative_error=0.;SM.set_nanite_settings(mesh,nanite,True)
E.set_metadata_tag(mesh,'LivingCollectibles.Owner','StaffLivingCollectibles20261016')
if not E.save_loaded_asset(mesh,False):raise RuntimeError('Camera package save failed')
report={'stage':'camera_v2_saved','path':mesh.get_path_name(),'source':spec['source'],'fbx':spec['fbx'],'change':'Rear MENU, DISP and playback legends oriented upright towards +Y','preview_rerendered':False,'game_run':False}
(ROOT/'Receipts/camera-text-v2-import.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('LIVING_CAMERA_V2_SAVED '+mesh.get_path_name())
