"""Publish only the two requested catalog PNGs and their existing UI textures."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

import unreal as u

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[1]
E = u.EditorAssetLibrary
ROWS = [('axe', 'ProductionTools/axe'), ('ue_m249', 'Icons/ue_m249')]
dirty = {package.get_path_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for _, relative in ROWS:
    if '/Game/ColdSteelData/' + relative in dirty:
        raise RuntimeError('Preserve unsaved icon asset: ' + relative)

before = ROOT / 'Before'
before.mkdir(exist_ok=True)
receipt = []
for name, relative in ROWS:
    source = ROOT / 'Artwork' / (name + '.png')
    destination = PROJECT / 'Content/ColdSteelData' / (relative + '.png')
    texture_path = '/Game/ColdSteelData/' + relative
    for original in [destination, destination.with_suffix('.uasset')]:
        backup = before / (name + original.suffix)
        if original.exists() and not backup.exists():
            shutil.copy2(original, backup)
    raw = source.read_bytes()
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix='.inventory-icon-', suffix='.tmp', delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, destination)
    folder, asset_name = texture_path.rsplit('/', 1)
    task = u.AssetImportTask()
    task.filename = str(destination)
    task.destination_path = folder
    task.destination_name = asset_name
    task.automated = True
    task.replace_existing = True
    task.replace_existing_settings = False
    task.save = False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    texture = u.load_asset(texture_path)
    if not task.imported_object_paths or not isinstance(texture, u.Texture2D):
        raise RuntimeError('Icon import did not complete: ' + texture_path)
    for prop, value in dict(lod_group=u.TextureGroup.TEXTUREGROUP_UI,
                            compression_settings=u.TextureCompressionSettings.TC_EDITOR_ICON,
                            mip_gen_settings=u.TextureMipGenSettings.TMGS_NO_MIPMAPS,
                            srgb=True, never_stream=True, max_texture_size=0).items():
        texture.set_editor_property(prop, value)
    if not E.save_loaded_asset(texture, False):
        raise RuntimeError('Icon asset was not saved: ' + texture_path)
    receipt.append(dict(png=str(destination), texture=texture.get_path_name(),
                        png_sha256=hashlib.sha256(raw).hexdigest(), runtime_tested=False))
    (ROOT / 'saved-icons.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print('INVENTORY_ICON_SAVED', name, texture.get_path_name(), flush=True)
