import unreal as u,json,shutil
from pathlib import Path
O=Path(__file__).parent
path='/Game/Weapons/RearGripFinish20260913/M4/balanced/SM_BalancedRearGrip'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
mesh=u.load_asset(path)
bindings={str(s.material_slot_name):s.material_interface for s in mesh.static_materials}
src=Path(r'D:\FPS3D\FPSGAME\Content\Weapons\RearGripFinish20260913\M4\balanced\SM_BalancedRearGrip.uasset')
backup=O/'Before_SM_BalancedRearGrip.uasset'
if not backup.exists():shutil.copy2(src,backup)
t=u.AssetImportTask();t.filename=str(O/'SM_BalancedRearGrip.fbx');t.destination_path=path.rsplit('/',1)[0];t.destination_name='SM_BalancedRearGrip';t.automated=True;t.replace_existing=True;t.save=False
opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
d=opt.static_mesh_import_data;d.combine_meshes=True;d.auto_generate_collision=False;d.generate_lightmap_u_vs=False;d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS;d.vertex_color_import_option=u.VertexColorImportOption.REPLACE;t.options=opt
A.import_asset_tasks([t]);mesh=u.load_asset(path);slots=mesh.static_materials
for i,s in enumerate(slots):s.material_interface=bindings[str(s.material_slot_name)];slots[i]=s
mesh.set_editor_property('static_materials',slots)
E.set_metadata_tag(mesh,'BalancedM4ForwardFit','body -Y 5mm; receiver collar fixed; 20260913')
if not E.save_loaded_asset(mesh,False):raise RuntimeError('Cannot save adjusted M4 grip')
(O/'installed.json').write_text(json.dumps({'mesh':path,'body_forward_mm':5,'materials':{k:v.get_path_name() for k,v in bindings.items()},'game_tested':False},indent=2))
u.log('M4_BALANCED_FORWARD_FIT_INSTALLED')
