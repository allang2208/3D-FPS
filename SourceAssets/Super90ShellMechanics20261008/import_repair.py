"""Save the mounted-shell section and only the inspect bolt track."""
import unreal as u,json,shutil,hashlib
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];E=u.EditorAssetLibrary
R='/Game/Weapons/Super90/Cransh20261006'
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():
    raise RuntimeError('Exit PIE before saving the shell section and inspection; no assets changed.')
M=json.loads((O/'authoring.json').read_text(encoding='utf-8'))
receipt={'completed':False,'saved':[],'runtime_tested':False}

def record():
    (O/'import_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def load(path):
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    return obj
def backup(path):
    relative=path.split('.')[0].removeprefix('/Game/')+'.uasset'
    src=P/'Content'/relative;dst=O/'Before/Content'/relative
    if src.exists() and not dst.exists():
        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
def save(obj):
    if not E.save_loaded_asset(obj,False):raise RuntimeError('Save failed '+obj.get_path_name())
    receipt['saved'].append(obj.get_path_name());record()
def material_paths(mesh):
    return {str(slot.material_slot_name):slot.material_interface.get_path_name()
            for slot in mesh.get_editor_property('materials')}

mesh_path=R+'/SK_Super90_V7';mesh=load(mesh_path);backup(mesh_path)
materials=material_paths(mesh);materials['12gauge_mounted']=materials['12gauge']
skeleton=mesh.skeleton
inspect_path=R+'/Animations/A_Super90_inspect'
inspect_paths={load(inspect_path).get_path_name()}
# Retained clips, when present, are full playback assets rather than deltas.
# Keep only plain paths before any animation is modified.
def retained_inspects(profile):
    paths=[]
    for clip in profile.get_editor_property('clips'):
        base=clip.get_editor_property('base')
        if base and base.get_path_name().split('.')[0]==inspect_path:
            retained=clip.get_editor_property('retained')
            if retained:paths.append(retained.get_path_name())
    return paths
for family in ('vertical','canted','prism','angled'):
    profile=load('/Game/Weapons/Super90/Foregrips20261007/Profiles/DA_Super90_'+family)
    inspect_paths.update(retained_inspects(profile))
for path in inspect_paths:backup(path)

flag='Interchange.FeatureFlags.Import.FBX';previous=u.SystemLibrary.get_console_variable_int_value(flag)
u.SystemLibrary.execute_console_command(None,flag+' 0')
try:
    opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
    opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
    opt.import_mesh=True;opt.import_as_skeletal=True;opt.import_animations=False
    opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=skeleton
    opt.skeletal_mesh_import_data.set_editor_property('update_skeleton_reference_pose',False)
    opt.skeletal_mesh_import_data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
    task=u.AssetImportTask();task.filename=M['mesh'];task.destination_name='SK_Super90_V7';task.destination_path=R
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=True;task.save=False
    task.factory=u.FbxFactory();task.options=opt;u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:raise RuntimeError('Super90 section export was not imported')
    mesh=load(mesh_path);slots=list(mesh.get_editor_property('materials'))
    for i,slot in enumerate(slots):
        key=str(slot.material_slot_name)
        if key not in materials and 'Manny_S90_'+key in materials:
            key='Manny_S90_'+key;slot.material_slot_name=key
        slot.material_interface=load(materials[key]);slots[i]=slot
    mesh.set_editor_property('materials',slots);mesh.set_editor_property('physics_asset',None)
    editor=u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem);settings=editor.get_lod_build_settings(mesh,0)
    settings.use_full_precision_u_vs=True;settings.use_high_precision_tangent_basis=True
    settings.recompute_normals=False;settings.recompute_tangents=False
    editor.set_lod_build_settings(mesh,0,settings)
    E.set_metadata_tag(mesh,'Super90ShellSections','Mounted root shell: 12gauge_mounted; loose animated cartridge: 12gauge')
    E.set_metadata_tag(mesh,'Super90SourceSHA256',hashlib.sha256(Path(M['mesh']).read_bytes()).hexdigest())
    save(mesh)
finally:
    u.SystemLibrary.execute_console_command(None,flag+' '+str(previous))

idle=load(R+'/Animations/A_Super90_idle')
options=u.AnimPoseEvaluationOptions();options.evaluation_type=u.AnimDataEvalType.SOURCE
options.optional_skeletal_mesh=mesh
pose=u.AnimPoseExtensions.get_anim_pose_at_time(idle,0.,options)
closed=u.AnimPoseExtensions.get_bone_pose(pose,'WPN_bolt',u.AnimPoseSpaces.LOCAL)
receipt['closed_bolt_local']=[closed.translation.x,closed.translation.y,closed.translation.z,
    closed.rotation.x,closed.rotation.y,closed.rotation.z,closed.rotation.w]
for path in sorted(inspect_paths):
    clip=load(path);controller=clip.get_editor_property('controller')
    count=clip.get_editor_property('data_model_interface').get_number_of_keys()
    controller.open_bracket('Keep Super90 inspection closed without moving the hands',False)
    try:
        if not controller.set_bone_track_keys('WPN_bolt',[closed.translation]*count,
                [closed.rotation]*count,[closed.scale3d]*count,False):
            raise RuntimeError('Could not save inspection bolt track '+path)
    finally:controller.close_bracket(False)
    E.set_metadata_tag(clip,'Super90InspectBolt','Idle closed position; source donor last-round check removed; hands/timing retained')
    save(clip)

# Reimport may append/reorder a surface slot; preserve outfit masking by name.
config_path=P/'Content/ColdSteelData/modular_outfits.json'
dst=O/'Before/Content/ColdSteelData/modular_outfits.json';dst.parent.mkdir(parents=True,exist_ok=True)
if not dst.exists():shutil.copy2(config_path,dst)
config=json.loads(config_path.read_text(encoding='utf-8-sig'))
config['profiles'][mesh.get_path_name()]['hide_source_materials']=[i for i,s in enumerate(mesh.materials)
    if str(s.material_slot_name).startswith('Manny_S90_')]
config_path.write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
receipt['mounted_material']=materials['12gauge_mounted'];receipt['inspect_assets']=sorted(inspect_paths)
receipt['completed']=True;record()
print('SUPER90_SHELL_AND_INSPECT_SAVED',len(receipt['saved']),flush=True)
