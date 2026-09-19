"""Import the M4-only seam revision, retaining the live M4 grip material bindings."""
import unreal as u,json
from pathlib import Path
P=Path(__file__).resolve().parent
old='/Game/Weapons/RearGripFinish20260913/M4/balanced/SM_BalancedRearGrip'
dest='/Game/Weapons/RearGripFinish20260913/M4/balanced/Seam20260914'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
source=u.load_asset(old)
if not source:raise RuntimeError('M4 source grip asset is unavailable')
bindings={str(s.material_slot_name):s.material_interface for s in source.static_materials}
t=u.AssetImportTask();t.filename=str(P/'SM_BalancedRearGrip.fbx');t.destination_path=dest;t.destination_name='SM_BalancedRearGrip';t.automated=True;t.replace_existing=True;t.save=False
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE;t.options=opt
A.import_asset_tasks([t]);mesh=u.load_asset(dest+'/SM_BalancedRearGrip')
if not mesh:raise RuntimeError('M4 seam mesh import failed')
for i,s in enumerate(mesh.static_materials):mesh.set_material(i,bindings[str(s.material_slot_name)])
E.set_metadata_tag(mesh,'M4BalancedSeamRevision','Contoured bridge between existing ForwardFit grip and receiver; body transform unchanged')
E.set_metadata_tag(mesh,'WeaponFinishUV','1; existing M4 collar material and 12x5 cm projection')
if not E.save_loaded_asset(mesh,False):raise RuntimeError('Could not save M4 seam mesh')
(P/'import_results.json').write_text(json.dumps({'mesh':mesh.get_path_name(),'source_mesh':old,'materials':{k:v.get_path_name() for k,v in bindings.items()},'runtime_tested':False},indent=2))
u.log('M4_BALANCED_SEAM_IMPORTED')
