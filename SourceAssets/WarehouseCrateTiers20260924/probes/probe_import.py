import unreal as u
ROOT='/Game/Props/WarehouseCrateTiers20260924'
print('EXISTS_T1', u.EditorAssetLibrary.does_asset_exist(ROOT+'/SM_WarehouseCrate_T1_Wood'))
pkg = u.load_package(ROOT+'/SM_WarehouseCrate_T1_Wood')
print('PKG', pkg, 'loaded' if pkg and True else 'notloaded')
# what does the leftover package contain?
if pkg:
    for o in pkg.get_objects():
        print('OBJ', o.get_fname(), o.get_class().get_name())
AT = u.AssetToolsHelpers.get_asset_tools()
options = u.FbxImportUI()
options.automated_import_should_detect_type=False
options.import_mesh=True; options.import_as_skeletal=False
options.mesh_type_to_import = u.FBXImportType.FBXIT_STATIC_MESH
options.import_materials=False; options.import_textures=False; options.import_animations=False; options.create_physics_asset=False
d=options.static_mesh_import_data; d.convert_scene=True; d.convert_scene_unit=True; d.import_uniform_scale=1
d.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
d.combine_meshes=True; d.auto_generate_collision=True; d.generate_lightmap_u_vs=True
task=u.AssetImportTask(); task.filename=r'D:\FPS3D\FPSGAME\SourceAssets\WarehouseCrateTiers20260924\Authored\SM_WarehouseCrate_T1_Wood.fbx'
task.destination_path=ROOT; task.destination_name='SM_WarehouseCrate_T1_Wood_probe'
task.automated=True; task.save=False; task.replace_existing=False
task.set_editor_property('async_', False); task.factory=u.FbxFactory(); task.options=options
flag='Interchange.FeatureFlags.Import.FBX'; prev=u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None, flag+' 0')
    AT.import_asset_tasks([task])
finally:
    u.SystemLibrary.execute_console_command(None, flag+' '+str(prev))
print('STATUS', task.get_import_status() if hasattr(task,'get_import_status') else 'n/a')
for o in task.get_objects(): print('IMPORTED', o.get_path_name(), o.get_class().get_name())

