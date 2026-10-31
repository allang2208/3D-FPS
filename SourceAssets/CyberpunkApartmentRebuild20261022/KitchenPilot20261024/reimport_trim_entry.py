import unreal as u, json
E=u.EditorAssetLibrary
BASE='/Game/Props/CyberpunkApartmentKitchen20261024/Meshes'
rows=[('FridgeLowerDoor',r'D:\FPS3D\FPSGAME\SourceAssets\CyberpunkApartmentRebuild20261022\KitchenPilot20261024/FBX/SM_KP_KIT_FridgeLowerDoorTrim.fbx'),
      ('FridgeUpperDoor',r'D:\FPS3D\FPSGAME\SourceAssets\CyberpunkApartmentRebuild20261022\KitchenPilot20261024/FBX/SM_KP_KIT_FridgeUpperDoorTrim.fbx')]
out={}
for name,src in rows:
    t=u.AssetImportTask();t.filename=src;t.destination_path=BASE;t.destination_name='SM_KP_'+name
    t.automated=True;t.replace_existing=True;t.replace_existing_settings=True;t.save=True;t.factory=u.FbxFactory()
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
    opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.import_as_skeletal=False
    d=opt.static_mesh_import_data
    for k,v in dict(combine_meshes=True,convert_scene=True,convert_scene_unit=True,transform_vertex_to_absolute=True,auto_generate_collision=False,generate_lightmap_u_vs=True,import_uniform_scale=1.).items():d.set_editor_property(k,v)
    t.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t])
    m=u.load_asset(BASE+'/SM_KP_'+name);b=m.get_bounding_box()
    out[name]=dict(min=[b.min.x,b.min.y,b.min.z],max=[b.max.x,b.max.y,b.max.z])
    E.save_loaded_asset(m,False)
print('TRIM_REIMPORT '+json.dumps(out))
