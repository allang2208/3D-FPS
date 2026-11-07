import hashlib
import json
import shutil
import traceback
from datetime import datetime, timezone
from pathlib import Path

import unreal as u


TASK = Path('D:/FPS3D/FPSGAME/SourceAssets/M24CarbonMaterialIconInstall20261106')
ROOT = Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/AttachmentIcons20260913')
NAME = 'ue_m24_stock_m24_carbon_spine_stock'
PACKAGE_ROOT = '/Game/ColdSteelData/AttachmentIcons20260913'
SELECTED = TASK / 'Selected.png'
RECEIPT = TASK / 'installed.json'
TARGETS = [
    (ROOT / (NAME + '.png'), PACKAGE_ROOT),
    (ROOT / 'FramedFirearms' / (NAME + '.png'), PACKAGE_ROOT + '/FramedFirearms'),
]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_receipt(data):
    RECEIPT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    baseline = json.loads((TASK / 'baseline.json').read_text(encoding='utf-8-sig'))
    if RECEIPT.exists():
        raise RuntimeError('Installation receipt already exists; preserve previous operation.')
    if digest(SELECTED) != baseline['selected_sha256']:
        raise RuntimeError('Selected image changed after preparation.')

    headless = '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
    if not headless and u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError('PIE active; preserve user session.')
    packages = {folder + '/' + NAME for _, folder in TARGETS}
    dirty = {package.get_name() for package in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if packages & dirty:
        raise RuntimeError('Target packages have unsaved changes: ' + ', '.join(sorted(packages & dirty)))
    for entry in baseline['files']:
        if digest(entry['path']) != entry['sha256']:
            raise RuntimeError('Target changed after backup: ' + entry['path'])

    state = {
        'complete': False,
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'selected_image': str(SELECTED),
        'selected_sha256': baseline['selected_sha256'],
        'pngs_replaced': [],
        'assets_saved': [],
        'runtime_tested': False,
    }
    write_receipt(state)
    try:
        textures = []
        asset_tools = u.AssetToolsHelpers.get_asset_tools()
        for png, folder in TARGETS:
            shutil.copyfile(SELECTED, png)
            state['pngs_replaced'].append(str(png))
            write_receipt(state)
            task = u.AssetImportTask()
            task.filename = str(png)
            task.destination_path = folder
            task.destination_name = NAME
            task.automated = True
            task.replace_existing = True
            task.replace_existing_settings = True
            task.save = False
            task.factory = u.TextureFactory()
            asset_tools.import_asset_tasks([task])
            objects = task.get_objects()
            if len(objects) != 1 or not isinstance(objects[0], u.Texture2D):
                raise RuntimeError('Texture import did not return one Texture2D: ' + str(png))
            texture = objects[0]
            expected_path = folder + '/' + NAME + '.' + NAME
            if texture.get_path_name() != expected_path:
                raise RuntimeError('Unexpected imported asset path: ' + texture.get_path_name())
            texture.set_editor_property('compression_settings', u.TextureCompressionSettings.TC_EDITOR_ICON)
            texture.set_editor_property('lod_group', u.TextureGroup.TEXTUREGROUP_UI)
            texture.set_editor_property('srgb', True)
            texture.set_editor_property('never_stream', True)
            textures.append(texture)

        if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost() for texture in textures], False):
            raise RuntimeError('Saving the imported texture packages failed.')
        state['assets_saved'] = [texture.get_path_name() for texture in textures]
        state['files'] = [
            {'path': entry['path'], 'sha256': digest(entry['path']), 'bytes': Path(entry['path']).stat().st_size}
            for entry in baseline['files']
        ]
        state['texture_settings'] = {
            'compression': 'TC_EDITOR_ICON',
            'lod_group': 'TEXTUREGROUP_UI',
            'srgb': True,
            'never_stream': True,
        }
        state['complete'] = True
        state['finished_utc'] = datetime.now(timezone.utc).isoformat()
        write_receipt(state)
        u.log('M24 carbon material icon: both PNGs replaced and both Texture2D packages saved.')
    except Exception:
        state['error'] = traceback.format_exc()
        write_receipt(state)
        raise


main()
