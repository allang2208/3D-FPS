"""Import only the rustic pickaxe's overhead strike/recovery and phase timing."""
import json
import re
import shutil
from pathlib import Path

import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
SOURCE = ROOT/'SourceAssets/PickaxeSightline20260919'
DEST = '/Game/Items/ProductionTools/RusticPickaxe20260919'
CFG = json.loads((SOURCE/'motion.json').read_text(encoding='utf-8'))
EAL = u.EditorAssetLibrary
targets = {DEST+'/A_RusticPickaxe_'+clip for clip in ('Swing', 'HitRecover')}
is_commandlet = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
if not is_commandlet and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
    raise RuntimeError('Stop PIE before importing the pickaxe overhead attack. No assets changed.')
dirty = [p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_name() in targets]
if dirty:
    raise RuntimeError('Save the pickaxe animations first: '+', '.join(dirty))
backup = SOURCE/'Before'
backup.mkdir(parents=True, exist_ok=True)
for clip in ('Swing', 'HitRecover'):
    name = 'A_RusticPickaxe_'+clip+'.uasset'
    old = ROOT/'Content/Items/ProductionTools/RusticPickaxe20260919'/name
    if old.exists() and not (backup/name).exists():
        shutil.copy2(old, backup/name)
catalogue = ROOT/'Content/ColdSteelData/production_tools.json'
if not (backup/catalogue.name).exists():
    shutil.copy2(catalogue, backup/catalogue.name)
mesh = u.load_asset(DEST+'/SK_RusticPickaxe')
skeleton = mesh.get_editor_property('skeleton')
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')
receipt = {'revision': CFG['revision'], 'saved': [], 'runtime_tested': False, 'preview_rendered': False}
for clip in ('Swing', 'HitRecover'):
    name = 'A_RusticPickaxe_'+clip
    options = u.FbxImportUI()
    options.automated_import_should_detect_type = False
    options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
    options.import_mesh = False
    options.import_animations = True
    options.import_materials = False
    options.import_textures = False
    options.skeleton = skeleton
    options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
    options.anim_sequence_import_data.set_editor_property('custom_sample_rate', CFG['fps'])
    task = u.AssetImportTask()
    task.filename = str(SOURCE/'Export'/(name+'.fbx'))
    task.destination_path = DEST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    task.options = options
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Import did not produce '+name)
    animation = u.load_asset(DEST+'/'+name)
    if compression:
        animation.set_editor_property('bone_compression_settings', compression)
    if not EAL.save_loaded_asset(animation, False):
        raise RuntimeError('Could not save '+name)
    receipt['saved'].append(animation.get_path_name())
# Keep unrelated catalogue formatting and parallel axe/shovel edits intact.
text = catalogue.read_text(encoding='utf-8')
match = re.search(r'"tool_pickaxe"\s*:\s*\{[^}]*\}', text)
if not match:
    raise RuntimeError('Could not locate the pickaxe definition')
block = match.group()
for field in ('swing_seconds', 'contact_seconds'):
    block, count = re.subn(r'("'+field+r'"\s*:\s*)[0-9.]+',
        lambda m: m.group(1)+str(CFG[field]), block)
    if count != 1:
        raise RuntimeError('Could not update pickaxe '+field)
updated = text[:match.start()]+block+text[match.end():]
if updated != text:
    catalogue.write_text(updated, encoding='utf-8')
receipt['swing_seconds'] = CFG['swing_seconds']
receipt['contact_seconds'] = CFG['contact_seconds']
(SOURCE/'import_receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
u.log('PICKAXE_OVERHEAD_IMPORTED')
