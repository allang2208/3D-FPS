"""Swap the magazine slot icon to the lengthened QBZ-191 magazine render.

The previous icon PNG is kept next to the new one so the old presentation can
be restored without re-rendering.
"""
import unreal as u
import json
import shutil
from pathlib import Path

P = Path(__file__).parent
ICONDIR = Path(r"D:\FPS3D\FPSGAME\Content\ColdSteelData\AttachmentIcons20260913")
new_src = P / 'Reference' / 'icon_magazine_ext_mag_qbz40.png'
live = ICONDIR / 'magazine_ext_mag.png'
backup = P / 'Reference' / 'icon_magazine_ext_mag_before_qbz40.png'

if live.exists() and not backup.exists():
    shutil.copy2(live, backup)
shutil.copy2(new_src, live)

A = u.AssetToolsHelpers.get_asset_tools()
task = u.AssetImportTask()
task.filename = str(live)
task.destination_path = '/Game/ColdSteelData/AttachmentIcons20260913'
task.destination_name = 'magazine_ext_mag'
task.automated = True
task.replace_existing = True
task.save = False
A.import_asset_tasks([task])
asset = u.load_asset(task.destination_path + '/' + task.destination_name)
if not isinstance(asset, u.Texture2D):
    raise RuntimeError('Icon texture import failed')
u.EditorAssetLibrary.save_loaded_asset(asset, False)
u.log('QBZ40_ICON ' + json.dumps({'icon': asset.get_path_name(), 'backup': str(backup)}))
