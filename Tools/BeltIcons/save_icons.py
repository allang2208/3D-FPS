"""Import only the three production UI textures through the existing editor."""
import hashlib
import json
import shutil
from pathlib import Path
import unreal as u

P = Path('D:/FPS3D/FPSGAME')
R = P / 'SourceAssets/BeltIcons20261025/ArcaneFrontR1'
policy = json.loads((P / 'Tools/BeltIcons/policy.json').read_text(encoding='utf-8'))
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    level = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if level and level.is_in_play_in_editor():
        raise RuntimeError('Preserve active PIE; belt icon imports are ready but not saved')
result = {'completed': False, 'revision': policy['revision'], 'textures': {}, 'runtime_tested': False}
for key, row in policy['items'].items():
    folder = R / key
    rendered = json.loads((folder / 'rendered.json').read_text(encoding='utf-8'))
    if rendered['grid'] != [policy['grid_w'], policy['grid_h']] or rendered['camera_offset'] != policy['camera_offset']:
        raise RuntimeError('Render the current belt layout before importing: ' + key)
    source = folder / (key + '.png')
    package = P / 'Content' / (row['texture'][6:] + '.uasset')
    backup = R / 'Before' / key
    backup.mkdir(parents=True, exist_ok=True)
    for original in (package, package.with_suffix('.uexp'), package.with_suffix('.ubulk')):
        if original.exists() and not (backup / original.name).exists():
            shutil.copy2(original, backup / original.name)
    task = u.AssetImportTask()
    task.filename = str(source)
    task.destination_path, task.destination_name = row['texture'].rsplit('/', 1)
    task.automated = True
    task.replace_existing = True
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = u.load_asset(row['texture'])
    if not texture:
        raise RuntimeError('UI texture import failed: ' + key)
    for prop, value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,
                            compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,
                            mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS, srgb=True).items():
        texture.set_editor_property(prop, value)
    if not u.EditorAssetLibrary.save_loaded_asset(texture, False):
        raise RuntimeError('UI texture save failed: ' + key)
    result['textures'][key] = {'asset': texture.get_path_name(), 'icon_sha256': hashlib.sha256(source.read_bytes()).hexdigest()}
    (R / 'saved_icons.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
result['completed'] = True
(R / 'saved_icons.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('BELT_UI_TEXTURES_SAVED', len(result['textures']))
