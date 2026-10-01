"""Background import/save of the actual revised mesh, clips, skin and fitted physics."""
import unreal as u, json, sys, runpy
from pathlib import Path
OUT=Path(__file__).resolve().parent;SOURCE=OUT/'Delivery'
PROJECT=OUT.parents[2];DEST='/Game/Monsters/HundredEyedSlag/PolishV2'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if u.EditorLevelLibrary.get_game_world() is not None:raise RuntimeError('Preserving active PIE')
LIB=u.EditorAssetLibrary;TOOLS=u.AssetToolsHelpers.get_asset_tools()
REV='HundredEyedSlagPolish20260930V2'
report={'revision':REV,'saved':[],'animations':{},'runtime_tested':False}
def save(asset):
    LIB.set_metadata_tag(asset,'HundredEyedSlag.Revision',REV)
    if not LIB.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+asset.get_path_name())
    report['saved'].append(asset.get_path_name())
def imp(file,name,folder,options):
    if LIB.does_asset_exist(folder+'/'+name):
        asset=u.load_asset(folder+'/'+name)
        if LIB.get_metadata_tag(asset,'HundredEyedSlag.Revision')!=REV:raise RuntimeError('Unowned asset '+folder+'/'+name)
        return asset
    task=u.AssetImportTask();task.filename=str(file);task.destination_name=name;task.destination_path=folder
    task.automated=True;task.save=False;task.replace_existing=False;task.options=options
    TOOLS.import_asset_tasks([task]);asset=u.load_asset(folder+'/'+name)
    if not asset:raise RuntimeError('Import failed '+str(file))
    return asset
sys.path.insert(0,str(PROJECT/'Tools/InfectedDog'))
from meshy_animation_units import match_bind_root_scale
cvar='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(cvar)
u.SystemLibrary.execute_console_command(None,cvar+' 0')
try:
    skeleton=u.load_asset('/Game/Monsters/HundredEyedSlag/V1/SK_HundredEyedSlag_V1_Skeleton')
    op=u.FbxImportUI();op.automated_import_should_detect_type=False
    op.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH;op.import_as_skeletal=True
    op.import_mesh=True;op.import_animations=False;op.import_materials=False;op.import_textures=False
    op.create_physics_asset=False;op.skeleton=skeleton
    data=op.skeletal_mesh_import_data
    data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    data.set_editor_property('use_t0_as_ref_pose',False);data.set_editor_property('update_skeleton_reference_pose',False)
    mesh=imp(SOURCE/'SK_HundredEyedSlag_V2.fbx','SK_HundredEyedSlag_V2',DEST,op)
    if LIB.get_metadata_tag(mesh,'HundredEyedSlag.Revision')!=REV:
        mesh.set_editor_property('enable_per_poly_collision',False)
        save(mesh)
    runpy.run_path(str(OUT/'fix_material.py'),run_name='__main__')
    physics=None
    if hasattr(u.HundredEyedSlagMonster,'build_fitted_physics_asset'):
        physics=u.HundredEyedSlagMonster.build_fitted_physics_asset(mesh)
        if not physics:raise RuntimeError('Fitted physics asset failed')
        save(physics);save(mesh)
    contracts=json.loads((OUT/'animation_contract.json').read_text())['actions']
    for row in contracts:
        op=u.FbxImportUI();op.automated_import_should_detect_type=False
        op.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION;op.import_as_skeletal=True
        op.import_mesh=False;op.import_animations=True;op.import_materials=False;op.import_textures=False;op.skeleton=skeleton
        op.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        op.anim_sequence_import_data.set_editor_property('custom_sample_rate',30)
        clip=imp(SOURCE/'Animations'/(row['action']+'.fbx'),row['action'],DEST+'/Animations',op)
        units=match_bind_root_scale(clip,mesh);clip.set_preview_skeletal_mesh(mesh)
        save(clip);report['animations'][row['role']]={'path':clip.get_path_name(),'root_units':units,'seconds':clip.get_play_length()}
    # Bind V1 to the repaired surface too: already placed instances can retain their old mesh reference.
    material=u.load_asset(DEST+'/Materials/M_HundredEyedSlag_Skin_V2')
    save(material)
    old_mesh=u.load_asset('/Game/Monsters/HundredEyedSlag/V1/SK_HundredEyedSlag_V1')
    slots=list(old_mesh.get_editor_property('materials'))
    for i,slot in enumerate(slots):slot.material_interface=material;slots[i]=slot
    old_mesh.set_editor_property('materials',slots)
    if not LIB.save_loaded_asset(old_mesh,False):raise RuntimeError('V1 compatibility binding failed')
    report.update(mesh=mesh.get_path_name(),material=material.get_path_name(),physics=physics.get_path_name() if physics else None,
        stage='polish_assets_saved' if physics else 'mesh_skin_clips_saved_pending_native_physics_build')
    (OUT/'ue_installation.json').write_text(json.dumps(report,indent=2))
    u.log('SLAG_POLISH_SAVED '+json.dumps(report))
finally:u.SystemLibrary.execute_console_command(None,cvar+' '+str(previous))
