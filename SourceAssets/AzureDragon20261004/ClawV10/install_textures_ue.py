"""Import and save the two reference textures the live Fab claw reads from /ClawV10/Textures:
T_AzureDragonClawVeins (claw glass veins) and T_AzureDragonClawSmoke (author_textures.py, Export/).

Split out of the retired V10.1 original-claw installer (2026-10-07, see Docs/Publication/AzureDragon20261007);
same ownership tag, so the textures it saved stay replaceable. Background commandlet or editor batch bridge.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(__file__).resolve().parent
DEST = '/Game/Weapons/AzureDragon20261004/ClawV10'
TAG, REV = 'AzureDragonClawV10Revision', '10'
E = u.EditorAssetLibrary
A = u.AssetToolsHelpers.get_asset_tools()
receipt = dict(complete=False, saved_assets=[], runtime_tested=False, rendered=False)


def record():
    (ROOT / 'install-textures-receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


def owned(path):
    asset = u.load_asset(path) if E.does_asset_exist(path) else None
    dirty = any(str(p.get_name()) == path.rsplit('.', 1)[0]
                for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    if dirty and (not asset or E.get_metadata_tag(asset, 'AzureDragonPending') != REV):
        raise RuntimeError('Preserve unsaved asset ' + path)
    if asset and E.get_metadata_tag(asset, TAG) != REV:
        raise RuntimeError('Preserve unowned asset ' + path)
    return asset


def import_texture(name):
    path = DEST + '/Textures/' + name
    owned(path)
    task = u.AssetImportTask()
    for key, value in dict(filename=str(ROOT / 'Export' / (name + '.png')), destination_path=DEST + '/Textures',
                           destination_name=name, automated=True, replace_existing=True, save=False).items():
        task.set_editor_property(key, value)
    A.import_asset_tasks([task])
    tex = u.load_asset(path)
    if not tex:
        raise RuntimeError('Import failed ' + name)
    E.set_metadata_tag(tex, TAG, REV)
    E.set_metadata_tag(tex, 'AzureDragonPending', REV)
    for key, value in dict(srgb=False, compression_settings=u.TextureCompressionSettings.TC_BC7,
                           lod_group=u.TextureGroup.TEXTUREGROUP_EFFECTS, never_stream=True,
                           address_x=u.TextureAddress.TA_WRAP, address_y=u.TextureAddress.TA_WRAP).items():
        tex.set_editor_property(key, value)
    E.set_metadata_tag(tex, 'AzureDragonPending', '')
    E.set_metadata_tag(tex, 'SourceAuthoring', 'AzureDragon20261004/ClawV10/author_textures.py')
    if not E.save_loaded_asset(tex, False):
        E.set_metadata_tag(tex, 'AzureDragonPending', REV)
        raise RuntimeError('Cannot save ' + path)
    receipt['saved_assets'].append(tex.get_path_name())
    record()


if u.EditorLevelLibrary.get_game_world() is not None:
    raise RuntimeError('Stop the current PIE before importing/saving the claw textures; editor preserved.')
record()
import_texture('T_AzureDragonClawVeins')
import_texture('T_AzureDragonClawSmoke')
receipt['complete'] = True
record()
print('AZURE_DRAGON_CLAW_TEXTURES_SAVED assets=' + str(len(receipt['saved_assets'])) + ' runtime_tested=false rendered=false')
