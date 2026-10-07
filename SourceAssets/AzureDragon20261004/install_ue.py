"""Restore only the shared Fab normal atlas (read by the live V10 Fab claw material).
The V9-era shared translucent claw material was retired on 2026-10-07 (Docs/Publication/AzureDragon20261007).
Runs in a background commandlet or the existing editor batch bridge; no previews/tests.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
DEST = '/Game/Weapons/AzureDragon20261004'
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
TAG, REVISION = 'AzureDragonRevision', '1'
receipt = {'complete': False, 'saved_assets': [], 'runtime_tested': False, 'rendered': False,
           'source_listing': 'https://www.fab.com/listings/2d436c6f-7d26-4a80-8469-884b97613e5a',
           'source_author': 'CaptainHC', 'source_file': str(ROOT / 'Original/Fisto.glb')}


def record():
    (ROOT / 'install-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')


def owned(path):
    if any(str(p.get_name()) == path for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError('Preserve unsaved target ' + path)
    asset = u.load_asset(path)
    if asset and E.get_metadata_tag(asset, TAG) != REVISION:
        raise RuntimeError('Preserve unowned asset ' + path)
    return asset


def save(asset):
    E.set_metadata_tag(asset, TAG, REVISION)
    E.set_metadata_tag(asset, 'SourceListing', receipt['source_listing'])
    if not E.save_loaded_asset(asset, False):
        raise RuntimeError('Cannot save ' + asset.get_path_name())
    receipt['saved_assets'].append(asset.get_path_name())
    record()


def import_asset(filename, folder, name, options=None):
    owned(DEST + '/' + folder + '/' + name)
    task = u.AssetImportTask()
    for key, value in {'filename': str(filename), 'destination_path': DEST + '/' + folder,
                       'destination_name': name, 'automated': True, 'replace_existing': True,
                       'save': False}.items():
        task.set_editor_property(key, value)
    if options:
        task.set_editor_property('options', options)
    A.import_asset_tasks([task])
    asset = u.load_asset(DEST + '/' + folder + '/' + name)
    if not asset:
        raise RuntimeError('Cannot import ' + name)
    return asset


record()
normal = import_asset(ROOT / 'Export/T_AzureDragonNormal.png', 'Textures', 'T_AzureDragonNormal')
normal.set_editor_property('srgb', False)
normal.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_NORMALMAP)
save(normal)

receipt["complete"] = True
record()
print("AZURE_SHARED_SURFACE_SAVED assets=1 runtime_tested=false rendered=false")
