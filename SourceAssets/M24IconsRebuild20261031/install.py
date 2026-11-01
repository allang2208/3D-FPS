"""Publish this batch's fourteen icon keys, preserving unrelated assets."""
import hashlib
import json
import shutil
import struct
from datetime import datetime, timezone
from pathlib import Path
import unreal as u

OUT = Path(__file__).resolve().parent
PROJECT = OUT.parents[1]
DISK = PROJECT / 'Content/ColdSteelData/AttachmentIcons20260913/FramedFirearms'
DEST = '/Game/UI/AttachmentIcons20260913/FramedFirearms'
manifest = json.loads((OUT / 'production.json').read_text(encoding='utf-8'))
baseline = json.loads((OUT / 'baseline.json').read_text(encoding='utf-8'))
receipt_path = OUT / 'import_receipt.json'
if receipt_path.exists():
    raise RuntimeError('This installation has already started; preserve its receipt')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

# These are mutation prerequisites, not an extra runtime validation pass.
for name, expected in baseline['files'].items():
    if digest(Path(name)) != expected:
        raise RuntimeError('Target changed since this batch was prepared: ' + name)
dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
for item in manifest['items']:
    source = OUT / item['workspace_output']
    if not source.is_file():
        raise RuntimeError('Missing final image: ' + str(source))
    for key in item['destinations']:
        if DEST + '/T_' + key in dirty:
            raise RuntimeError('Unsaved texture is in use: ' + key)

receipt = {'complete': False, 'started_utc': datetime.now(timezone.utc).isoformat(),
           'master_images': len(manifest['items']), 'saved': [], 'runtime_tested': False,
           'tool': manifest['tool'], 'native_build_required': False}

def record():
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding='utf-8')

record()
for item in manifest['items']:
    source = OUT / item['workspace_output']
    width, height = struct.unpack('>II', source.read_bytes()[16:24])
    for key in item['destinations']:
        target = DISK / (key + '.png')
        shutil.copy2(source, target)
        task = u.AssetImportTask()
        task.filename = str(target)
        task.destination_path = DEST
        task.destination_name = 'T_' + key
        task.automated = True
        task.replace_existing = True
        task.replace_existing_settings = True
        task.save = False
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        texture = u.load_asset(DEST + '/T_' + key)
        if not isinstance(texture, u.Texture2D):
            raise RuntimeError('Texture import failed: ' + key)
        for prop, value in {
            'lod_group': u.TextureGroup.TEXTUREGROUP_UI,
            'compression_settings': u.TextureCompressionSettings.TC_EDITOR_ICON,
            'srgb': True, 'never_stream': True,
            'mip_gen_settings': u.TextureMipGenSettings.TMGS_NO_MIPMAPS,
            'max_texture_size': 1024,
        }.items():
            texture.set_editor_property(prop, value)
        if not u.EditorAssetLibrary.save_loaded_asset(texture, False):
            raise RuntimeError('Texture save failed: ' + key)
        receipt['saved'].append({
            'key': key, 'master': item['key'], 'png': str(target),
            'png_sha256': digest(target), 'texture': texture.get_path_name(),
            'source_resolution': [width, height], 'max_texture_size': 1024,
            'uasset_sha256': digest(PROJECT / 'Content/UI/AttachmentIcons20260913/FramedFirearms' / ('T_' + key + '.uasset')),
        })
        record()
receipt['complete'] = True
receipt['finished_utc'] = datetime.now(timezone.utc).isoformat()
record()
print('M24_REBUILT_ICONS_SAVED', len(receipt['saved']), flush=True)
