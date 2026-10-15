import json,unreal as u
from pathlib import Path
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/FurnaceBreathV17');DEST='/Game/Monsters/IncineratorBossM66';VERSION=DEST+'/FurnaceBreathV17'
E=u.EditorAssetLibrary;A=u.AssetToolsHelpers.get_asset_tools()
if not globals().get('M66_COMMANDLET',False) and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():raise RuntimeError('End PIE before M66 furnace import')
if any(p.get_path_name().startswith(DEST) for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):raise RuntimeError('M66 packages have unsaved changes')
manifest=json.loads((ROOT/'Records/skin_manifest.json').read_text());bp=u.load_asset(DEST+'/BP_M66RigPreview');cdo=u.get_default_object(bp.generated_class())
original=cdo.get_editor_property('visual_mesh');physics=cdo.get_editor_property('reaction_physics');path=VERSION+'/SK_M66_Furnace_V17'
old=u.SystemLibrary.get_console_variable_int_value('Interchange.FeatureFlags.Import.FBX');u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX 0')
try:
    revised=u.load_asset(path) if E.does_asset_exist(path) else None
    if not revised:
        opt=u.FbxImportUI();opt.automated_import_should_detect_type=False;opt.mesh_type_to_import=u.FBXImportType.FBXIT_SKELETAL_MESH
        opt.import_as_skeletal=True;opt.import_mesh=True;opt.import_animations=False;opt.import_materials=False;opt.import_textures=False;opt.create_physics_asset=False;opt.skeleton=original.skeleton
        data=opt.skeletal_mesh_import_data;data.convert_scene=True;data.convert_scene_unit=True;data.force_front_x_axis=True;data.import_uniform_scale=1.
        data.normal_import_method=u.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS;data.set_editor_property('update_skeleton_reference_pose',False);data.set_editor_property('import_morph_targets',True)
        task=u.AssetImportTask();task.filename=manifest['fbx'];task.destination_path=VERSION;task.destination_name='SK_M66_Furnace_V17';task.automated=True;task.save=False;task.options=opt;task.factory=u.FbxFactory()
        A.import_asset_tasks([task]);revised=u.load_asset(path)
        if not revised:raise RuntimeError('M66 furnace mesh import failed')
    slots=list(original.get_editor_property('materials'));materials=[]
    for index,slot in enumerate(slots):
        source=slot.material_interface
        if not isinstance(source,u.Material):raise RuntimeError('M66 body material needs explicit instance-parent adaptation')
        name='M_M66FurnaceBody_'+str(index);material=u.load_asset(VERSION+'/'+name) if E.does_asset_exist(VERSION+'/'+name) else A.duplicate_asset(name,VERSION,source)
        material.set_editor_property('used_with_morph_targets',True);material.set_editor_property('used_with_skeletal_mesh',True)
        if u.MaterialEditingLibrary.recompile_material(material):raise RuntimeError('M66 morph body material compilation failed')
        materials.append(material);slot.material_interface=material
    if not u.PoisonMaggotMonster.compile_material_assets(materials):raise RuntimeError('M66 morph materials not compiled')
    revised.set_editor_property('materials',slots);revised.set_editor_property('physics_asset',physics);u.SkeletalMeshEditorSubsystem.set_allow_cpu_access(revised,True)
    morphs=[m.get_name() for m in revised.get_editor_property('morph_targets')]
    mouth=next((n for n in morphs if 'M66_FurnaceOpen' in n),None)
    if not mouth:raise RuntimeError('Authored mouth-opening morph missing after import')
    saved=[]
    for asset in materials+[revised.skeleton,revised]:
        if not E.save_loaded_asset(asset,False):raise RuntimeError('M66 mesh save failed '+asset.get_path_name())
        saved.append(asset.get_path_name())
    # Only packages dirtied by this controlled import, after the initial dirty gate.
    for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
        if p.get_path_name().startswith(DEST+'/'):
            asset=E.load_asset(p.get_path_name())
            if asset and not E.save_loaded_asset(asset,False):raise RuntimeError('M66 skeleton dependency save failed')
    report={'complete':True,'saved':saved,'morph_name':mouth,'morphs':morphs,'previous_mesh':original.get_path_name(),'physics_preserved':physics.get_path_name(),'runtime_tested':False}
    (ROOT/'Records/skin_import.json').write_text(json.dumps(report,indent=2));print('M66_FURNACE_SKIN_SAVED '+json.dumps(report))
finally:u.SystemLibrary.execute_console_command(None,'Interchange.FeatureFlags.Import.FBX '+str(old))
