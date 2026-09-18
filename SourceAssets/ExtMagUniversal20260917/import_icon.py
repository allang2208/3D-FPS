import unreal as u, json
from pathlib import Path
P = Path(__file__).parent
A = u.AssetToolsHelpers.get_asset_tools()
task = u.AssetImportTask()
task.filename = r"D:\FPS3D\FPSGAME\Content\ColdSteelData\AttachmentIcons20260913\magazine_ext_mag.png"
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
(P / 'import_receipt.json').write_text(json.dumps({'icon': asset.get_path_name()}, indent=2))
u.log('EXTMAG_ICON_IMPORTED')
