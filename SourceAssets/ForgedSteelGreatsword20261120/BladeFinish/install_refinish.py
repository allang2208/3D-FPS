"""Replace the two shared blade maps in place and publish the five revised factory cards."""
import json
from pathlib import Path
import runpy
import unreal as u

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TEXTURES = '/Game/Weapons/ForgedSteelGreatsword20261120/V1/Textures'
if Path(u.Paths.project_dir()).resolve() != ROOT:
    raise RuntimeError('Unexpected destination project')
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('PIE is active')
for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages():
    if package.get_name().startswith((TEXTURES + '/', '/Game/ColdSteelData/AttachmentIcons20260913/ue_forged_steel_greatsword_')):
        raise RuntimeError('Preserving unsaved changes to ' + package.get_name())

saved = []
for channel in ('BaseColor', 'MetallicRoughness'):
    name = 'T_ForgedSteelGreatsword_' + channel + '_V1'
    source = HERE / ('ForgedSteelGreatsword_' + channel + '.png')
    task = u.AssetImportTask()
    task.filename = str(source)
    task.destination_path = TEXTURES
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    expected = TEXTURES + '/' + name + '.' + name
    if expected not in task.imported_object_paths:
        raise RuntimeError('Texture import did not return ' + expected)
    texture = u.load_asset(expected)
    texture.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_WEAPON)
    texture.set_editor_property('srgb', channel == 'BaseColor')
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_BC7 if channel == 'BaseColor'
                                else u.TextureCompressionSettings.TC_MASKS)
    texture.set_editor_property('never_stream', False)
    if not u.EditorAssetLibrary.save_loaded_asset(texture, False):
        raise RuntimeError('Could not save ' + expected)
    saved.append(expected)

icons = runpy.run_path(str(HERE.parent/'CommonMods/install_stock_icons.py'))['install_stock_icons']()
(HERE/'import_receipt.json').write_text(json.dumps({'maps': saved, 'icons': icons, 'saved': True,
                                                    'game_tested': False}, indent=2) + '\n', encoding='utf-8')
print('FORGED_SWORD_REFINISH_SAVED', flush=True)
