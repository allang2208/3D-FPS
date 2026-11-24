"""Install prepared forged-sword cards as same-source workbench PNGs and UI textures."""
import json
from pathlib import Path
import shutil
import unreal as u


def install_stock_icons():
    cards = {}
    for slot in ('blade_1', 'guard', 'grip', 'pommel', 'blade_material'):
        for suffix in ('category_' + slot, slot + '_false'):
            cards[suffix] = slot + '_factory'
    return install_cards(cards)


def install_exclusive_icons():
    manifest = Path(__file__).with_name('exclusive_cards.json')
    keys = json.loads(manifest.read_text(encoding='utf-8'))['parts']
    return install_cards({key: key for key in keys})


def install_cards(cards):
    sources = Path(__file__).resolve().parent / 'Icons'
    folder = '/Game/ColdSteelData/AttachmentIcons20260913'
    content = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_content_dir())) / folder.removeprefix('/Game/')
    content.mkdir(parents=True, exist_ok=True)
    saved = []
    for suffix, art in cards.items():
        key = 'ue_forged_steel_greatsword_' + suffix
        target = content / (key + '.png')
        temp = target.with_suffix('.forged-icon.tmp')
        source = sources / (art + '.png')
        shutil.copyfile(source, temp)
        task = u.AssetImportTask()
        task.filename = str(source)
        task.destination_path = folder
        task.destination_name = key
        task.automated = True
        task.replace_existing = True
        task.save = False
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        expected = folder + '/' + key + '.' + key
        if expected not in task.imported_object_paths:
            raise RuntimeError('Icon import did not return ' + expected)
        icon = u.load_asset(expected)
        icon.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
        icon.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
        icon.set_editor_property('mip_gen_settings', u.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        icon.set_editor_property('srgb', True)
        icon.set_editor_property('never_stream', True)
        if not u.EditorAssetLibrary.save_loaded_asset(icon, False):
            raise RuntimeError('Could not save ' + expected)
        temp.replace(target)
        saved.append(expected)
    return saved
