"""Import fixed QBZ body and hinged heads using the existing private skeleton."""
import unreal as u, json
from pathlib import Path
O=Path(__file__).parent;D='/Game/Weapons/QBZ191/Folding20260913'
reference=u.load_asset('/Game/Weapons/QBZ191/Calibrated/SK_QBZ191_Manny')
bindings={str(m.material_slot_name):m.material_interface for m in reference.materials}
assets=u.AssetToolsHelpers.get_asset_tools();receipt={}
for name,skeletal in [('SK_QBZ191_Manny',True),('SM_QBZ191_RearSight',False),('SM_QBZ191_FrontSight',False)]:
    options=u.FbxImportUI();options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
    options.import_as_skeletal=skeletal;options.import_mesh=True;options.import_animations=False
    options.import_materials=False;options.import_textures=False;options.create_physics_asset=False
    if skeletal:
        options.skeleton=reference.skeleton
        data=options.skeletal_mesh_import_data
        data.set_editor_property('update_skeleton_reference_pose',False)
    else:
        data=options.static_mesh_import_data;data.combine_meshes=True;data.auto_generate_collision=False
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    data.normal_generation_method=u.FBXNormalGenerationMethod.MIKK_T_SPACE
    task=u.AssetImportTask();task.filename=str(O/(name+'.fbx'));task.destination_path=D;task.destination_name=name
    task.options=options;task.automated=True;task.replace_existing=True;task.save=False
    assets.import_asset_tasks([task]);mesh=u.load_asset(D+'/'+name)
    if not mesh:raise RuntimeError('Mesh import failed: '+name)
    if skeletal:
        slots=mesh.materials
        for i,slot in enumerate(slots):slot.material_interface=bindings[str(slot.material_slot_name)];slots[i]=slot
        mesh.set_editor_property('materials',slots)
    else:
        for i,slot in enumerate(mesh.static_materials):mesh.set_material(i,bindings[str(slot.material_slot_name)])
    if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Mesh save failed: '+name)
    receipt[name]=mesh.get_path_name()
(O/'import.json').write_text(json.dumps({'assets':receipt,'skeleton':reference.skeleton.get_path_name(),'status':'imported; no gameplay or screenshot test'},indent=2))
u.log('QBZ_FOLDING_IMPORT_COMPLETE')
