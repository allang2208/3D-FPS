import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent;E=u.EditorAssetLibrary
D='/Game/Weapons/SkeletonSniperStock20261031'
flag='Interchange.FeatureFlags.Import.FBX';prev=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH;opt.import_mesh=True;opt.import_as_skeletal=False;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False
    imp=opt.static_mesh_import_data;imp.combine_meshes=True;imp.auto_generate_collision=False;imp.generate_lightmap_u_vs=False;imp.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=str(O/'Exports/SM_SniperSkeleton_SVD.fbx');task.destination_path=D+'/Meshes';task.destination_name='SM_SniperSkeleton_SVD';task.options=opt;task.factory=u.FbxFactory();task.automated=True;task.replace_existing=True;task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh=u.load_asset(D+'/Meshes/SM_SniperSkeleton_SVD')
    for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,u.load_asset(D+'/Materials/MI_'+str(slot.material_slot_name)))
    sub=u.get_editor_subsystem(u.StaticMeshEditorSubsystem) or u.new_object(u.StaticMeshEditorSubsystem)
    for i in range(sub.get_lod_count(mesh)):
        bs=sub.get_lod_build_settings(mesh,i);bs.recompute_tangents=True;bs.use_mikk_t_space=False;bs.use_full_precision_u_vs=True;bs.use_high_precision_tangent_basis=True
        if i==0:bs.recompute_normals=False
        sub.set_lod_build_settings(mesh,i,bs)
    u.ASH12AttachmentAssetTools.disable_runtime_fast_build(mesh)
    if not E.save_loaded_asset(mesh,False):raise RuntimeError('SVD stock finish not saved')
    (O/'svd_finish_receipt.json').write_text(json.dumps(dict(saved=True,path=mesh.get_path_name(),native_fit_unchanged=True,recomputed_tangents_all_lods=True),indent=2))
    print('SVD_STOCK_SURFACE_FINISH_SAVED')
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prev))
