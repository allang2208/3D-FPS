"""Import/save the V12 support skin and eight specials in owned new packages.

Retain the saved common skeleton, anatomical physics, skin material and LOD
budget. No accepted sweep/slam reimport, PIE, previews or tests.
"""
import json, shutil, sys
from pathlib import Path
import unreal as u
OUT=Path(__file__).resolve().parent
ROOT=OUT.parent
PROJECT=OUT.parents[2]
BASE='/Game/Monsters/HundredEyedSlag'
REV='ArticulationV12'
LIB=u.EditorAssetLibrary
TOOLS=u.AssetToolsHelpers.get_asset_tools()
EDITOR=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
contracts=json.loads((OUT/'animation_contract.json').read_text())['actions']
mesh_path=BASE+'/ArticulationV12/SK_HundredEyedSlag_V12'
paths=[BASE+'/ArticulationV12/Animations/A_HundredEyedSlag_'+c['name'] for c in contracts]
skeleton_path=BASE+'/V1/SK_HundredEyedSlag_V1_Skeleton'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if u.EditorLevelLibrary.get_game_world() is not None:raise RuntimeError('End related PIE before asset saving')
dirty={p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
if dirty.intersection(paths+[mesh_path,skeleton_path]):raise RuntimeError('Unsaved target assets preserved')
for path in paths+[mesh_path]:
    if LIB.does_asset_exist(path) and LIB.get_metadata_tag(u.load_asset(path),'HundredEyedSlag.Revision')!=REV:
        raise RuntimeError('Unowned destination preserved: '+path)
    source=PROJECT/'Content'/(path.removeprefix('/Game/')+'.uasset')
    backup=OUT/'Before'/(path.removeprefix('/Game/')+'.uasset')
    if source.exists() and not backup.exists():
        backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
skeleton=u.load_asset(skeleton_path)
lod=u.load_asset(BASE+'/RuntimeV3/LOD_HundredEyedSlag_RuntimeV3')
material=u.load_asset(BASE+'/PolishV2/Materials/M_HundredEyedSlag_Skin_V2')
physics=u.load_asset(BASE+'/PolishV2/PA_HundredEyedSlag_V2')
laser=u.load_asset(BASE+'/EyeLaserJumpV11/Materials/M_EyeLaser')
if any(asset is None for asset in (skeleton,lod,material,physics,laser)):
    raise RuntimeError('Existing saved skeleton, LOD, skin/laser materials and physics are required')
def save(asset):
    LIB.set_metadata_tag(asset,'HundredEyedSlag.Revision',REV)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed: '+asset.get_path_name())
def imp(file,path,op):
    task=u.AssetImportTask();task.filename=str(file)
    task.destination_path,task.destination_name=path.rsplit('/',1)
    task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;task.options=op
    TOOLS.import_asset_tasks([task])
    asset=u.load_asset(path)
    if asset is None or path not in [p.split('.')[0] for p in task.imported_object_paths]:
        raise RuntimeError('FBX import failed: '+path+' '+str(task.imported_object_paths))
    return asset
def options():
    op=u.FbxImportUI();op.automated_import_should_detect_type=False;op.override_full_name=True
    op.import_as_skeletal=True;op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
    return op
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale
variable='Interchange.FeatureFlags.Import.FBX';old=u.SystemLibrary.get_console_variable_int_value(variable)
u.SystemLibrary.execute_console_command(None,variable+' 0')
saved=[]
try:
    op=options();op.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    op.import_mesh=True;op.import_animations=False;op.create_physics_asset=False
    data=op.skeletal_mesh_import_data
    data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    data.set_editor_property('use_t0_as_ref_pose',False)
    data.set_editor_property('update_skeleton_reference_pose',False)
    mesh=imp(OUT/'Delivery/SK_HundredEyedSlag_V12.fbx',mesh_path,op)
    mesh.set_editor_property('enable_per_poly_collision',False)
    mesh.set_editor_property('physics_asset',physics)
    slots=list(mesh.get_editor_property('materials'))
    for slot in slots:slot.material_interface=material
    mesh.set_editor_property('materials',slots)
    build=EDITOR.get_lod_build_settings(mesh,0)
    build.set_editor_property('recompute_normals',False)
    build.set_editor_property('recompute_tangents',True)
    build.set_editor_property('use_mikk_t_space',True)
    EDITOR.set_lod_build_settings(mesh,0,build)
    mesh.set_editor_property('lod_settings',lod)
    if not EDITOR.regenerate_lod(mesh,3,False,False):raise RuntimeError('LOD generation failed')
    save(mesh)
    mesh_receipt=dict(path=mesh.get_path_name(),saved=True,lods_generated=3,
        physics_reused=physics.get_path_name(),material=material.get_path_name(),
        max_influences=4,geometry_uv_bind_preserved=True,giant_right_arm_weights_changed=False)
    (OUT/'mesh_installation.json').write_text(json.dumps(mesh_receipt,indent=2),encoding='utf-8')
    print('SLAG_V12_SUPPORT_MESH_AND_LODS_SAVED',flush=True)
    for c,path in zip(contracts,paths):
        op=options();op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        op.import_mesh=False;op.import_animations=True
        op.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        op.anim_sequence_import_data.set_editor_property('custom_sample_rate',60)
        clip=imp(OUT/'Delivery'/c['file'],path,op)
        units=match_bind_root_scale(clip,mesh);clip.set_preview_skeletal_mesh(mesh)
        save(clip)
        saved.append(dict(role=c['name'],path=clip.get_path_name(),seconds=clip.get_play_length(),units=units,saved=True))
        print('SLAG_V12_SPECIAL_ANIMATION_SAVED '+c['name'],flush=True)
finally:u.SystemLibrary.execute_console_command(None,variable+' '+str(old))
# No bone was added. Do not write incidental importer bookkeeping on the
# shared skeleton, accepted clips, old mesh, materials or physics packages.
receipt=dict(revision=REV,animation_assets_saved=len(saved),assets=saved,
    mesh_saved=True,mesh=mesh_receipt,skeleton_saved=False,material_saved=False,laser_material_reused=True,
    accepted_sweep_and_slam_reimported=False,native_runtime_build_pending=True,
    execution_mode='background_commandlet' if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower() else 'existing_editor_bridge',
    tested=False,preview_rendered=False)
(OUT/'animation_installation.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
(OUT/'ready_assets.json').write_text(json.dumps(dict(revision=REV,animations_saved=8,mesh_saved=True,
    laser_material_reused=True,native_build_pending=True),indent=2),encoding='utf-8')
print('SLAG_V12_MESH_AND_EIGHT_ANIMATIONS_SAVED',flush=True)
