"""Save repaired meshes, zombie clips and the existing F6 security Blueprint."""
import unreal as u,json
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008/V03')
DEST='/Game/Monsters/FacelessSecurity';LIB=u.EditorAssetLibrary;AT=u.AssetToolsHelpers.get_asset_tools()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('PIE active; preserve the running session')
bp=u.load_asset(DEST+'/BP_FacelessSecurity');cdo=u.get_default_object(bp.generated_class())
old_mesh=cdo.get_editor_property('visual_mesh');skeleton=old_mesh.get_editor_property('skeleton');physics=old_mesh.get_editor_property('physics_asset')
receipt={'meshes':{},'saved':[],'game_tested':False,'rendered':False}
u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
for role,name in [('outfit','SK_FacelessSecurity_V03'),('clothing','SK_FacelessSecurity_Clothing_V03'),('body','SK_FacelessSecurity_Body_V03')]:
    options=u.FbxImportUI();options.automated_import_should_detect_type=False;options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    options.import_as_skeletal=True;options.import_mesh=True;options.import_animations=False;options.import_materials=False;options.import_textures=False
    options.skeleton=skeleton;options.create_physics_asset=False;options.physics_asset=physics
    data=options.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.import_uniform_scale=1.
    data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
    data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    task=u.AssetImportTask();task.filename=str(ROOT/'Delivery'/(name+'.fbx'));task.destination_path=DEST;task.destination_name=name
    task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;task.options=options;task.factory=u.FbxFactory()
    AT.import_asset_tasks([task]);mesh=u.load_asset(DEST+'/'+name)
    if not mesh or not task.imported_object_paths:raise RuntimeError('Mesh import failed '+name)
    slots=list(mesh.get_editor_property('materials'))
    for slot in slots:
        imported=str(slot.get_editor_property('imported_material_slot_name'));family=imported.removeprefix('Security_').split('.')[0]
        mat=u.load_asset(DEST+'/Materials/M_FS1_'+family)
        if not mat:raise RuntimeError('Unknown material '+imported)
        slot.material_interface=mat
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',physics)
    LIB.set_metadata_tag(mesh,'SecurityGeometryRevision','V03 complete wrists and feet; capped-volume leather boot upper; rigid toe box and flexible ankle')
    if not LIB.save_loaded_asset(mesh,False):raise RuntimeError('Save failed '+name)
    receipt['saved'].append(mesh.get_path_name());receipt['meshes'][role]=mesh.get_path_name()
    (ROOT/'ue_mesh_delivery.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
new_mesh=u.load_asset(receipt['meshes']['outfit'])
cdo.set_editor_property('visual_mesh',new_mesh);cdo.get_editor_property('mesh').set_skeletal_mesh_asset(new_mesh)
# The established animation importer obtains its skeleton from the Blueprint
# CDO. All mesh and animation changes are completed in this same editor batch.
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/import_male_v02.py').read_text(encoding='utf-8').replace('V02','V03')
src=src.replace('V03 Male guard: Jason idle/walk, ZombieAnimationPack Attack_D weighted strike','V03 guard: ZombieAnimationPack Idle_A, Walk_A and Attack_D; repaired exposed extremities and complete duty boots')
src=src.replace('V03 male sources, native retarget, tailored stance, grounded boots and authored strike timing','V03 zombie sources, native retarget, broad stance, repaired boots and authored strike timing')
src=src.replace('V01 body, clothing, materials, skeleton, skin weights, physics, AI and F6 entry; only action references and matching movement/contact timing updated','V01 materials, skeleton, physics, AI and F6 entry; V03 repaired display/boots and zombie action set')
exec(compile(src,'import_security_zombie_actions','exec'))
