"""Save the measured iron-sight markers in the HK416 mesh and every action."""
import unreal as u,json,hashlib
from pathlib import Path
O=Path(__file__).parent;S=O.parent/'HK416Reworked20260930'
ROOT='/Game/Weapons/HK416/Reworked20260930'
auth=json.loads((S/'authoring.json').read_text())
tools=u.AssetToolsHelpers.get_asset_tools()
mesh=u.load_asset(ROOT+'/SK_HK416_Manny');materials=list(mesh.materials)
skeleton=mesh.skeleton
report={'saved':[],'markers_source_m':{k:auth['markers_source_m'][k] for k in ('WPN_RearSight','WPN_FrontSight')},'runtime_after_tested':False}
def save(asset):
    if not u.EditorLoadingAndSavingUtils.save_packages([asset.get_outermost()],False):raise RuntimeError('Save failed '+asset.get_path_name())
    report['saved'].append(asset.get_path_name())
    (O/'import_receipt.json').write_text(json.dumps(report,indent=2))
def imported(file,folder,name,opt):
    task=u.AssetImportTask();task.filename=str(file);task.destination_path=folder;task.destination_name=name
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    task.options=opt;task.factory=u.FbxFactory();tools.import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('No imported asset: '+name)
    asset=u.load_asset(folder+'/'+name)
    # Package metadata API is restricted during PIE; import/save remains scoped.
    if not u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
        u.EditorAssetLibrary.set_metadata_tag(asset,'HK416SourceSHA256',hashlib.sha256(Path(file).read_bytes()).hexdigest())
    return asset
flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=skeleton
    opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
    opt.skeletal_mesh_import_data.set_editor_property('use_t0_as_ref_pose',False)
    opt.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',True)
    mesh=imported(auth['mesh'],ROOT,'SK_HK416_Manny',opt)
    mesh.set_editor_property('materials',materials);mesh.set_editor_property('physics_asset',None)
    system=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
    for lod in range(system.get_lod_count(mesh)):
        settings=system.get_lod_build_settings(mesh,lod);settings.use_full_precision_u_vs=True;system.set_lod_build_settings(mesh,lod,settings)
    save(mesh);save(mesh.skeleton)
    compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
    for key,entry in auth['clips'].items():
        family,kind=key.split('/');file=Path(entry['fbx'])
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        opt.import_mesh=False;opt.import_animations=True;opt.skeleton=mesh.skeleton;opt.import_materials=False;opt.import_textures=False
        opt.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False);opt.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
        anim=imported(file,ROOT+'/Animations/'+family,file.stem,opt)
        anim.set_editor_property('bone_compression_settings',compression);save(anim)
    report['complete']=True
    (O/'import_receipt.json').write_text(json.dumps(report,indent=2))
    u.log('HK416_CORRECTED_IRON_SIGHTS_SAVED '+str(len(report['saved'])))
    check=O/'inspect_imported_markers.py'
    exec(compile(check.read_text(encoding='utf8'),str(check),'exec'),{'__file__':str(check),'__name__':'__main__'})
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))
