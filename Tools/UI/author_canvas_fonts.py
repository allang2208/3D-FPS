"""Save the project's two engine Canvas sizes without changing the source Font Face."""
import os
from pathlib import Path
import unreal as u

batch = Path(os.environ['FPS_TEXT_BATCH'])
if Path(u.Paths.project_dir()).resolve() != (batch / 'Host').resolve():
    raise RuntimeError('Expected private authoring host')
source = '/Game/UI/GunsmithWorkbench/Fonts/NotoSansSC-Regular_Font'
for points in (8, 10):
    dest = '/Game/UI/GunsmithWorkbench/WorldText/F_ColdSteelCanvas' + str(points)
    library = u.EditorAssetLibrary
    font = u.load_asset(dest) if library.does_asset_exist(dest) else library.duplicate_asset(source, dest)
    if not font:
        raise RuntimeError(dest)
    font.set_editor_property('legacy_font_size', points)
    if not library.save_loaded_asset(font,False):
        raise RuntimeError('Could not save ' + dest)
    print('CANVAS_FONT_SAVED', font.get_path_name(), points)
