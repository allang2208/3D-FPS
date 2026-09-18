import unreal as u, json
from pathlib import Path
P = Path(__file__).parent
A = u.AssetToolsHelpers.get_asset_tools()
task = u.AssetImportTask()
task.filename = r"D:\FPS3D\FPSGAME\Content\ColdSteelData\AttachmentIcons20260913\magazine_large_drum.png"
task.destination_path = '/Game/ColdSteelData/AttachmentIcons20260913'
task.destination_name = 'magazine_large_drum'
task.automated = True
task.replace_existing = True
task.save = False
A.import_asset_tasks([task])
asset = u.load_asset(task.destination_path + '/' + task.destination_name)
if not isinstance(asset, u.Texture2D):
    raise RuntimeError('drum icon restore failed')
u.EditorAssetLibrary.save_loaded_asset(asset, False)
u.log('DRUM_ICON_RESTORED')
