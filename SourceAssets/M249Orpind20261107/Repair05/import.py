"""Import the rail fit and update only the two optical landmark tracks."""
from pathlib import Path
import unreal as u,json,hashlib
r=Path(__file__).resolve().parent;root=r.parent;project=root.parents[1]
E=u.EditorAssetLibrary
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE is running; preserve its session before saving M249 assets')
dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith('/Game/Weapons/M249/')]
if dirty:raise RuntimeError('Preserve unsaved M249 packages '+str(dirty))
before=json.loads((r/'before_hashes.json').read_text(encoding='utf8'))
changed=[n for n,h in before.items() if n.endswith('.uasset') and hashlib.sha256((project/n).read_bytes()).hexdigest()!=h]
if changed:raise RuntimeError('M249 asset changed since this fit began: '+str(changed))
mesh_path='/Game/Weapons/M249/SK_M249_V7';host=u.load_asset(mesh_path);skeleton=host.skeleton
saved=[]
def save(asset):
    if not E.save_loaded_asset(asset,False):raise RuntimeError('Cannot save '+asset.get_path_name())
    saved.append(asset.get_path_name())
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    for path,skeletal in ((mesh_path,True),('/Game/Weapons/M249/Assembly/SM_M249_magnifier',False)):
        previous=u.load_asset(path);prop='materials' if skeletal else 'static_materials'
        materials={str(s.material_slot_name):s.material_interface for s in previous.get_editor_property(prop)}
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False
        opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH if skeletal else u.FBXImportType.FBXIT_STATIC_MESH
        opt.import_as_skeletal=skeletal;opt.import_mesh=True;opt.import_materials=False;opt.import_textures=False;opt.import_animations=False;opt.create_physics_asset=False
        if skeletal:
            opt.skeleton=skeleton;data=opt.skeletal_mesh_import_data
            data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('use_t0_as_ref_pose',False)
            data.set_editor_property('import_morph_targets',True);previous.get_editor_property('asset_import_data').set_editor_property('import_morph_targets',True)
        else:
            data=opt.static_mesh_import_data;data.set_editor_property('combine_meshes',True);data.set_editor_property('auto_generate_collision',False)
        data.set_editor_property('normal_import_method',u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
        folder,name=path.rsplit('/',1);task=u.AssetImportTask()
        task.filename=str(root/'Exports'/(name+'.fbx'));task.destination_path=folder;task.destination_name=name
        task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=True;task.options=opt;task.factory=u.FbxFactory()
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task]);task.get_objects()
        asset=u.load_asset(path);slots=asset.get_editor_property(prop)
        for i,slot in enumerate(slots):
            slot.material_interface=materials[str(slot.material_slot_name)];slots[i]=slot
        asset.set_editor_property(prop,slots);save(asset)
    save(skeleton)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
tracks=json.loads((r/'sight_tracks.json').read_text(encoding='utf8'))
for role,bones in tracks.items():
    clip=u.load_asset('/Game/Weapons/M249/Animations/A_M249_'+role);ctl=clip.get_editor_property('controller')
    ctl.open_bracket('Seat M249 optical landmarks on its rail',False)
    try:
        for bone,rows in bones.items():
            if not ctl.set_bone_track_keys(bone,[u.Vector(*v[:3]) for v in rows],[u.Quat(*v[3:7]) for v in rows],[u.Vector(*v[7:]) for v in rows],False):
                raise RuntimeError('Missing optical landmark '+role+'/'+bone)
    finally:ctl.close_bracket(False)
    if not u.WeaponAnimationAuthoring.finalize_authored_animation(clip):raise RuntimeError('Cannot finalize '+role)
    save(clip)
(r/'import_receipt.json').write_text(json.dumps({'saved':saved,'updated_tracks':['WPN_FrontSight','WPN_RearSight']},indent=2),encoding='utf8')
print('M249_RAIL_FIT_SAVED',len(saved),flush=True)
