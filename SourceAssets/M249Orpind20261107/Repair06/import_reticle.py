"""Import the subpixel-visibility correction without changing native clips."""
from pathlib import Path
import unreal as u,json
r=Path(__file__).resolve().parent;root=r.parent;E=u.EditorAssetLibrary
if '-run=' not in u.SystemLibrary.get_command_line().lower() and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE is running; preserve its session before saving M249 assets')
dirty=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith('/Game/Weapons/M249/')]
if dirty:raise RuntimeError('Preserve unsaved M249 packages '+str(dirty))
host=u.load_asset('/Game/Weapons/M249/SK_M249_V7');skeleton=host.skeleton
old_morphs={m.get_name() for m in host.get_editor_property('morph_targets')}
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag);saved=[]
try:
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    for path,skeletal in (('/Game/Weapons/M249/SK_M249_V7',True),('/Game/Weapons/M249/Assembly/SM_M249_magnifier',False)):
        previous=u.load_asset(path);prop='materials' if skeletal else 'static_materials'
        materials={str(s.get_editor_property('imported_material_slot_name')):s.material_interface for s in previous.get_editor_property(prop)}
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
            identity=str(slot.get_editor_property('imported_material_slot_name'))
            slot.material_interface=materials[identity];slot.material_slot_name=identity;slots[i]=slot
        asset.set_editor_property(prop,slots)
        if skeletal and {m.get_name() for m in asset.get_editor_property('morph_targets')}!=old_morphs:
            raise RuntimeError('Joint corrective preservation failed')
        if not E.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+path)
        saved.append(path)
finally:u.SystemLibrary.execute_console_command(None,flag+' '+str(prior))
(r/'reticle_saved.json').write_text(json.dumps({'saved':saved,'radius_cm':.055,'morphs':len(old_morphs)},indent=2),encoding='utf8')
print('M249_RETICLE_GEOMETRY_SAVED',flush=True)
