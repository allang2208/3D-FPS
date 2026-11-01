"""Save the fitted M24 mechanical sight pair; reuse the installed weapon finish."""
import json
from pathlib import Path
import unreal as u

O=Path(__file__).resolve().parent
D='/Game/Weapons/M24/IronSights20261027'
E=u.EditorAssetLibrary
A=u.AssetToolsHelpers.get_asset_tools()
row=json.loads((O/'sight_authoring.json').read_text())
R={'complete':False,'saved':[],'runtime_tested':False}
if any(p.get_name().startswith(D) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Unsaved M24 sight revision retained; refusing overwrite')
flag='Interchange.FeatureFlags.Import.FBX'
previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI()
    for key,value in {'automated_import_should_detect_type':False,'mesh_type_to_import':u.FBXImportType.FBXIT_STATIC_MESH,
                      'import_mesh':True,'import_as_skeletal':False,'import_materials':False,'import_textures':False,'import_animations':False}.items():
        opt.set_editor_property(key,value)
    imp=opt.get_editor_property('static_mesh_import_data')
    for key,value in {'combine_meshes':True,'auto_generate_collision':False,'generate_lightmap_u_vs':False,
                      'normal_import_method':u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS}.items():
        imp.set_editor_property(key,value)
    task=u.AssetImportTask()
    for key,value in {'filename':row['file'],'destination_path':D,'destination_name':'SM_M24_m24_palma_iron',
                      'automated':True,'replace_existing':True,'replace_existing_settings':True,'save':False,
                      'factory':u.FbxFactory(),'options':opt}.items():
        task.set_editor_property(key,value)
    A.import_asset_tasks([task])
    mesh=u.load_asset(D+'/SM_M24_m24_palma_iron')
    if not mesh:raise RuntimeError('Mechanical sight import failed')
    materials={}
    for i,slot in enumerate(mesh.get_editor_property('static_materials')):
        name=str(slot.get_editor_property('material_slot_name'))
        material=u.load_asset('/Game/Weapons/M24/Surface20261027/Materials/MI_'+name)
        if not material:raise RuntimeError('Missing installed M24 finish '+name)
        mesh.set_material(i,material)
        materials[name]=material.get_path_name()
    for key,point in row['sockets_ue_cm'].items():
        socket=mesh.find_socket(key)
        if not socket:
            socket=u.StaticMeshSocket(outer=mesh)
            socket.set_editor_property('socket_name',key)
            mesh.add_socket(socket)
        socket.set_editor_property('relative_location',u.Vector(*point))
    sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    settings=sub.get_lod_build_settings(mesh,0)
    for key,value in {'recompute_normals':False,'recompute_tangents':True,'use_full_precision_u_vs':True,'use_high_precision_tangent_basis':True}.items():
        settings.set_editor_property(key,value)
    sub.set_lod_build_settings(mesh,0,settings)
    u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
    E.set_metadata_tag(mesh,'M24IronRecipe','M24IronSights20261027: open bore and outward hood; default no-optic fallback')
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('Mechanical sight save failed')
    R.update(complete=True,saved=[mesh.get_path_name()],materials=materials,sockets=row['sockets_ue_cm'],triangles=row['triangles'])
    (O/'install_receipt.json').write_text(json.dumps(R,ensure_ascii=False,indent=2),encoding='utf-8')
    print('M24_MECHANICAL_SIGHTS_SAVED',mesh.get_path_name(),flush=True)
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
