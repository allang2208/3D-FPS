"""Install only the two Inspect sequences, preserving each grip's idle family."""
import json, shutil, hashlib
from pathlib import Path
import unreal as u

P = Path(__file__).parent
ROOT = P.parents[2]
NAME = 'A_RuneSword_Inspect'
TARGETS = [
    ('Standard', '/Game/Weapons/AzureRunesword20260913', P/'ExportV80'/f'{NAME}.fbx'),
    ('LongGrip', '/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations', P/'ExportV80/LongGrip'/f'{NAME}.fbx'),
]
flag = 'Interchange.FeatureFlags.Import.FBX'
previous = u.SystemLibrary.get_console_variable_int_value(flag)
dirty = {p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
mesh = u.load_asset('/Game/Weapons/AzureRunesword20260913/SK_AzureRunesword_Manny')
rows = []
for variant, dest, source in TARGETS:
    if dest+'/'+NAME in dirty:
        raise RuntimeError('Unsaved target package; retained without modification: '+dest+'/'+NAME)
    if not source.exists():
        raise RuntimeError('Missing authored FBX: '+str(source))
try:
    u.SystemLibrary.execute_console_command(None, flag+' 0')
    for variant, dest, source in TARGETS:
        path = dest+'/'+NAME
        current = u.load_asset(path)
        if not current:
            raise RuntimeError('Missing installed Inspect: '+path)
        disk = ROOT/'Content'/dest.removeprefix('/Game/')/(NAME+'.uasset')
        backup = P/'BeforeV80'/variant/(NAME+'.uasset')
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            shutil.copy2(disk, backup)
        before_hash = hashlib.sha256(backup.read_bytes()).hexdigest()
        ui = u.FbxImportUI()
        ui.automated_import_should_detect_type = False
        ui.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
        ui.import_mesh = False
        ui.import_animations = True
        ui.import_materials = False
        ui.import_textures = False
        ui.skeleton = mesh.skeleton
        ui.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
        ui.anim_sequence_import_data.set_editor_property('custom_sample_rate', 120)
        task = u.AssetImportTask()
        task.filename = str(source)
        task.destination_path = dest
        task.destination_name = NAME
        task.automated = True
        task.replace_existing = True
        task.save = True
        task.options = ui
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        sequence = u.load_asset(path)
        if not task.imported_object_paths or not sequence:
            raise RuntimeError('Import did not produce '+path)
        if compression:
            sequence.set_editor_property('bone_compression_settings', compression)
        sequence.modify()
        if not u.EditorAssetLibrary.save_loaded_asset(sequence, False):
            if not u.EditorLoadingAndSavingUtils.save_packages([sequence.get_package()], False):
                raise RuntimeError('Asset save failed: '+path)
        rows.append({'variant':variant, 'asset':path, 'source':str(source),
                     'seconds':sequence.get_play_length(), 'saved':True,
                     'backup':str(backup), 'before_sha256':before_hash,
                     'after_sha256':hashlib.sha256(disk.read_bytes()).hexdigest()})
        (P/'import_receipt_v80.json').write_text(json.dumps({
            'revision':'V80', 'assets':rows, 'runtime_tested':False,
        }, indent=2), encoding='utf-8')
finally:
    u.SystemLibrary.execute_console_command(None, flag+' '+str(previous))
print('INSPECT_V80_SAVED', json.dumps(rows), flush=True)
