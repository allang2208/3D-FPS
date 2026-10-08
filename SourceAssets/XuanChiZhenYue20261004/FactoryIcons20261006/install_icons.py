"""Import and save exactly three factory icon assets through the UE batch mutex."""
import json
import runpy
from pathlib import Path
import unreal as u

P = Path(__file__).resolve().parent
receipt = {'complete': False, 'saved': [], 'runtime_tested': False}

def record():
    (P / 'import_receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')

record()
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        receipt['pending'] = 'Exit PIE before importing textures'
        record()
        raise RuntimeError(receipt['pending'])

jobs = runpy.run_path(str(P / 'deploy_icons.py'))['deploy']()
for job in jobs:
    task = u.AssetImportTask()
    task.filename = job['file']
    task.destination_path, task.destination_name = job['asset'].rsplit('/', 1)
    task.automated = True
    task.replace_existing = True
    task.save = False
    task.factory = u.TextureFactory()
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = u.load_asset(job['asset'])
    if not texture or not task.imported_object_paths:
        raise RuntimeError('Texture import did not produce ' + job['asset'])
    texture.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
    texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
    texture.set_editor_property('srgb', True)
    texture.set_editor_property('never_stream', True)
    texture.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()], False):
        raise RuntimeError('Failed saving ' + job['asset'])
    receipt['saved'].append(texture.get_path_name())
    record()
receipt['complete'] = True
record()
print('XUANCHI_FACTORY_ICONS_SAVED ' + str(len(receipt['saved'])), flush=True)
