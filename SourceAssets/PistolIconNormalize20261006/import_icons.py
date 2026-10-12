"""Re-import the normalized pistol catalog PNGs as their UE texture twins.

Runs headless: UnrealEditor-Cmd FPSGAME.uproject -run=pythonscript -script=<this> -NullRHI -unattended -nop4 -nosplash -nosound
Keeps the per-icon .uasset in sync with the PNG the game actually loads.
"""
import hashlib
import json
import struct
from pathlib import Path
import unreal as u

out = Path(__file__).resolve().parent
project = out.parents[1]
folder = '/Game/ColdSteelData/Icons'
definitions = ['ue_g18', 'ue_pit_viper2011']

if Path(u.Paths.project_dir()).resolve() != project:
    raise RuntimeError('Wrong project')

dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for name in definitions:
    if folder + '/' + name in dirty:
        raise RuntimeError(name + ' icon has unsaved editor edits; preserve them')

report = {'saved': [], 'icons': {}, 'runtime_tested': False}
for name in definitions:
    png = project / 'Content' / 'ColdSteelData' / 'Icons' / (name + '.png')
    data = png.read_bytes()
    width, height = struct.unpack('>II', data[16:24])
    if (width, height) != (480, 320):
        raise RuntimeError('%s icon is %dx%d, expected 480x320 catalog canvas' % (name, width, height))
    task = u.AssetImportTask()
    task.filename = str(png)
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = u.load_asset(folder + '/' + name)
    if not texture:
        raise RuntimeError('Icon import failed ' + name)
    texture.srgb = True
    texture.compression_settings = u.TextureCompressionSettings.TC_EDITOR_ICON
    texture.lod_group = u.TextureGroup.TEXTUREGROUP_UI
    texture.mip_gen_settings = u.TextureMipGenSettings.TMGS_NO_MIPMAPS
    texture.never_stream = True
    u.EditorAssetLibrary.set_metadata_tag(texture, 'PistolIconNormalize',
        '20261006: re-exported via ColdSteelWeaponIconCatalog; footprint canvas 480x320, dominant-axis 91% fill')
    if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()], False):
        raise RuntimeError('Icon save failed ' + name)
    report['saved'].append(texture.get_path_name())
    report['icons'][name] = {'asset': texture.get_path_name(), 'png': str(png),
        'size': [width, height], 'sha256': hashlib.sha256(data).hexdigest()}
report['status'] = 'pistol_icons_normalized_saved'
(out / 'import_receipt.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print('PISTOL_ICONS_NORMALIZED ' + json.dumps(report, ensure_ascii=False), flush=True)
