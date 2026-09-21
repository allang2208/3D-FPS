"""Replace only Witch body/animations with the authored cloud-based revision."""
import json
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/WitchMeshy20260919')
DEST='/Game/Monsters/WitchMeshy'; LIB=u.EditorAssetLibrary
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor.get_game_world():
    raise RuntimeError('Stop PIE before importing the Witch mesh and animations.')
mesh=u.load_asset(DEST+'/SK_Witch_Meshy')
skeleton=mesh.skeleton; physics=mesh.get_editor_property('physics_asset')
materials=list(mesh.get_editor_property('materials'))
staff=u.load_asset(DEST+'/Props/SM_Witch_Staff')
staff_materials=list(staff.get_editor_property('static_materials'))
roles=['Idle','Walk','CastPoison','ThrowPoisonBottle','DeathBackward']
paths=[DEST+'/SK_Witch_Meshy',DEST+'/Props/SM_Witch_Staff']+[DEST+'/Animations/A_Witch_'+r for r in roles]
for path in paths:
    backup=DEST+'/PreviousLocalRetargetV01/'+path.rsplit('/',1)[1]
    if not LIB.does_asset_exist(backup):
        if not LIB.duplicate_asset(path,backup): raise RuntimeError('Cannot preserve previous asset '+path)

tasks=[]
for role in ['Body','Staff']+roles:
    body=role=='Body'
    prop=role=='Staff'
    task=u.AssetImportTask(); task.automated=True; task.save=False; task.replace_existing=True
    task.replace_existing_settings=True
    filename='SK_Witch_GripBodyV02.fbx' if body else 'SM_Witch_StaffGripV02.fbx' if prop else f'A_Witch_{role}_CloudGripV02.fbx'
    task.filename=str(ROOT/'Delivery/CloudGripV02'/filename)
    task.destination_path=DEST if body else DEST+'/Props' if prop else DEST+'/Animations'
    task.destination_name='SK_Witch_Meshy' if body else 'SM_Witch_Staff' if prop else 'A_Witch_'+role
    options=u.FbxImportUI(); options.automated_import_should_detect_type=False
    options.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if body else u.FBXImportType.FBXIT_STATIC_MESH if prop else u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh=body or prop; options.import_animations=not(body or prop)
    options.import_as_skeletal=not prop; options.import_materials=False; options.import_textures=False
    options.skeleton=skeleton; options.create_physics_asset=False
    if body:
        options.physics_asset=physics
        options.skeletal_mesh_import_data.convert_scene_unit=True
        options.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
    elif prop:
        options.static_mesh_import_data.convert_scene_unit=True
        options.static_mesh_import_data.combine_meshes=True
        options.static_mesh_import_data.auto_generate_collision=False
    else:
        data=options.anim_sequence_import_data; data.convert_scene_unit=True
        data.set_editor_property('use_default_sample_rate',False)
        data.set_editor_property('custom_sample_rate',120)
        data.set_editor_property('animation_length',u.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
    task.options=options; tasks.append(task)
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
for task in tasks:
    if not task.imported_object_paths: raise RuntimeError('Import produced no asset: '+task.filename)
mesh=u.load_asset(DEST+'/SK_Witch_Meshy')
mesh.set_editor_property('materials',materials); mesh.set_editor_property('physics_asset',physics)
LIB.set_metadata_tag(mesh,'GripRevision','CloudGripV02: local left wrist weights and static curled grip; same 24-bone skeleton')
for role in roles:
    asset=u.load_asset(DEST+'/Animations/A_Witch_'+role)
    asset.set_preview_skeletal_mesh(mesh)
    asset.set_editor_property('loop',role in ['Idle','Walk'])
    asset.set_editor_property('enable_root_motion',False)
    asset.set_editor_property('force_root_lock',True)
    LIB.set_metadata_tag(asset,'Source','Meshy cloud-applied character animation; local timing/left grip fit; 120 FPS')
    LIB.set_metadata_tag(asset,'Status','CloudGripV02 candidate; not runtime or visually tested')
    if not LIB.save_loaded_asset(asset,False): raise RuntimeError('Save failed '+role)
if not LIB.save_loaded_asset(mesh,False): raise RuntimeError('Mesh save failed')
staff=u.load_asset(DEST+'/Props/SM_Witch_Staff')
staff.set_editor_property('static_materials',staff_materials)
if not LIB.save_loaded_asset(staff,False): raise RuntimeError('Staff save failed')
LIB.save_directory(DEST+'/PreviousLocalRetargetV01',only_if_is_dirty=True,recursive=True)
LIB.save_loaded_asset(skeleton,True)
report={'assets':paths,'source':'CloudGripV02','previous_assets':DEST+'/PreviousLocalRetargetV01',
        'physics_preserved':physics.get_path_name(),'tested':False}
(ROOT/'ue_cloud_grip_v02.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
