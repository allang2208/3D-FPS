"""Replace only the standard/long-grip sprint attacks in their active folders."""
import json,shutil,hashlib
from pathlib import Path
import unreal as u

P=Path(__file__).parent;ROOT=Path(u.Paths.project_dir()).resolve()
NAME='A_RuneSword_Overhead'
FX='/Game/Weapons/AzureRunesword20260913/SprintOverhead20260920'
FX_NAME='SM_RuneRift_Overhead'
targets={
 'Standard':('/Game/Weapons/AzureRunesword20260913','/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny'),
 'LongGrip':('/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations',
             '/Game/Weapons/FrostCrystalSword20260915/Modules20260915/SK_FrostSword_Arms'),
}
if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('PIE is still active; finish the requested end-play before importing.')
paths={folder+'/'+NAME for folder,mesh in targets.values()}
paths.add(FX+'/'+FX_NAME)
dirty=[p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in paths]
if dirty:raise RuntimeError('Target animation has unsaved edits; preserved without overwrite: '+', '.join(dirty))
receipt_path=P/'import_receipt.json'
receipt=json.loads(receipt_path.read_text(encoding='utf-8')) if receipt_path.exists() else {
    'revision':'SwordPickaxeOverheadImpactV2','seconds':2.60,'contact_window':[1.22,1.40],
    'saved':{},'backups':{},'runtime_tested':False,'acceptance_rendered':False}
for variant,(folder,mesh_path) in targets.items():
    file=ROOT/'Content'/((folder+'/'+NAME).removeprefix('/Game/')+'.uasset')
    backup=P/'Before'/variant/file.name;backup.parent.mkdir(parents=True,exist_ok=True)
    if file.exists() and not backup.exists():shutil.copy2(file,backup)
    if backup.exists():receipt['backups'][variant]={'path':str(backup),'sha256':hashlib.sha256(backup.read_bytes()).hexdigest()}
receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
flag='Interchange.FeatureFlags.Import.FBX';prior=u.SystemLibrary.get_console_variable_int_value(flag)
try:
    u.SystemLibrary.execute_console_command(None,flag+' 0')
    for variant,(folder,mesh_path) in targets.items():
        source_hash=hashlib.sha256((P/variant/(NAME+'.fbx')).read_bytes()).hexdigest()
        if receipt['saved'].get(variant,{}).get('source_sha256')==source_hash:continue
        mesh=u.load_asset(mesh_path)
        if not mesh:raise RuntimeError('Missing target skeleton mesh: '+mesh_path)
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_ANIMATION
        options.import_mesh=False;options.import_animations=True;options.import_materials=False;options.import_textures=False
        options.skeleton=mesh.get_editor_property('skeleton')
        options.anim_sequence_import_data.set_editor_property('use_default_sample_rate',False)
        options.anim_sequence_import_data.set_editor_property('custom_sample_rate',120)
        task=u.AssetImportTask();task.filename=str(P/variant/(NAME+'.fbx'))
        task.destination_path=folder;task.destination_name=NAME
        task.automated=True;task.replace_existing=True;task.save=False;task.options=options
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        if not task.imported_object_paths:raise RuntimeError('Import failed: '+variant)
        animation=u.load_asset(folder+'/'+NAME)
        compression=u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
        if compression:animation.set_editor_property('bone_compression_settings',compression)
        animation.set_preview_skeletal_mesh(mesh)
        u.EditorAssetLibrary.set_metadata_tag(animation,'SprintOverhead.Revision','PickaxeImpactV2')
        u.EditorAssetLibrary.set_metadata_tag(animation,'SprintOverhead.Source','PickaxeSightline20260919')
        if not u.EditorAssetLibrary.save_loaded_asset(animation,False):raise RuntimeError('Save failed: '+variant)
        receipt['saved'][variant]={'asset':animation.get_path_name(),'source':task.filename,'source_sha256':source_hash,'duration':animation.get_play_length()}
        receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        u.log('SWORD_PICKAXE_OVERHEAD_IMPORTED '+variant)
    if not receipt.get('fx_saved'):
        options=u.FbxImportUI();options.automated_import_should_detect_type=False
        options.mesh_type_to_import=u.FBXImportType.FBXIT_STATIC_MESH
        options.import_as_skeletal=False;options.import_mesh=True;options.import_materials=False;options.import_textures=False
        options.static_mesh_import_data.combine_meshes=True;options.static_mesh_import_data.auto_generate_collision=False
        task=u.AssetImportTask();task.filename=str(P/(FX_NAME+'.fbx'));task.destination_path=FX;task.destination_name=FX_NAME
        task.automated=True;task.replace_existing=True;task.save=False;task.options=options
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        if not task.imported_object_paths:raise RuntimeError('Vertical rift import failed')
        mesh=u.load_asset(FX+'/'+FX_NAME)
        mesh.set_material(0,u.load_asset('/Game/Weapons/AzureRunesword20260913/WristRiftV3/M_RuneRift'))
        if not u.EditorAssetLibrary.save_loaded_asset(mesh,False):raise RuntimeError('Vertical rift save failed')
        receipt['fx_saved']=mesh.get_path_name()
        receipt_path.write_text(json.dumps(receipt,indent=2),encoding='utf-8')
        u.log('SWORD_OVERHEAD_VERTICAL_RIFT_IMPORTED')
finally:
    u.SystemLibrary.execute_console_command(None,f'{flag} {prior}')
