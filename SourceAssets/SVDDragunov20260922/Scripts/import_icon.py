"""Import the SVD icon as a texture, matching the settings of the accepted M4A1 icon.

The Icons folder holds both a .png (shipped with the data) and a UE texture of the same
name, so the new icon has to reproduce the existing one's texture settings rather than
whatever the importer defaults to.

Run:
    UnrealEditor-Cmd.exe <uproject> -run=pythonscript -script=<this file> -unattended -nop4 -nosplash -nullrhi
"""
import json
from pathlib import Path

import unreal as u

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path('D:/FPS3D/FPSGAME')
DEST = '/Game/ColdSteelData/Icons'
REFERENCE = DEST + '/ue_m4a1'
NAME = 'ue_svd'
PNG = PROJECT / 'Content' / 'ColdSteelData' / 'Icons' / ('%s.png' % NAME)

E = u.EditorAssetLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()

if not PNG.exists():
    raise RuntimeError('missing icon png: %s' % PNG)

reference = u.load_asset(REFERENCE)
if not isinstance(reference, u.Texture2D):
    raise RuntimeError('reference icon not found: %s' % REFERENCE)

def read_settings(texture):
    """Copy what the accepted icon uses; names differ between engine versions, so a missing
    property is recorded rather than aborting the import."""
    out, failures = {}, []
    for key in ('srgb', 'compression_settings', 'lod_group', 'mip_gen_settings',
                'never_stream', 'texture_group', 'compression_no_alpha'):
        try:
            out[key] = texture.get_editor_property(key)
        except Exception as exc:  # noqa: BLE001
            failures.append('%s: %s' % (key, exc))
    return out, failures


settings, failures = read_settings(reference)
if failures:
    print('REFERENCE_SETTINGS_MISSING ' + json.dumps(failures))
print('REFERENCE_SETTINGS ' + json.dumps(settings, default=str))

task = u.AssetImportTask()
task.filename = str(PNG).replace('\\', '/')
task.destination_path = DEST
task.destination_name = NAME
task.automated = True
task.replace_existing = True
task.save = True
factory = u.TextureFactory()
task.factory = factory
TOOLS.import_asset_tasks([task])

texture = u.load_asset(DEST + '/' + NAME)
if not isinstance(texture, u.Texture2D):
    raise RuntimeError('icon import failed: %s' % NAME)

for key, value in settings.items():
    try:
        texture.set_editor_property(key, value)
    except Exception as exc:  # noqa: BLE001
        print('SET_FAILED %s: %s' % (key, exc))

if not E.save_loaded_asset(texture, False):
    raise RuntimeError('icon save failed')

report = {
    'icon': texture.get_path_name().split('.')[0],
    'size': [int(texture.blueprint_get_size_x()), int(texture.blueprint_get_size_y())],
    'srgb': bool(settings.get('srgb')) if 'srgb' in settings else None,
    'compression_settings': str(texture.get_editor_property('compression_settings')),
    'lod_group': str(texture.get_editor_property('lod_group')),
    'matches_reference': str(texture.get_editor_property('compression_settings'))
        == str(settings.get('compression_settings')),
    'settings_missing': failures,
    'png': str(PNG),
}
(ROOT / 'Receipts' / 'icon_import.json').write_text(json.dumps(report, indent=2, default=str), encoding='utf-8')
print('ICON_IMPORT ' + json.dumps(report, default=str))
