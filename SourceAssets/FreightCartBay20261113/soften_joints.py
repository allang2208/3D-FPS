"""Reimport the calibrated coverage map with the original working shader and sRGB/alpha settings."""
import unreal as u
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def apply(w,row):
    if row.get('load_only'):return
    task=u.AssetImportTask();task.filename=str(ROOT/'T_PlatformFinishCoverage.png')
    task.destination_path='/Game/SceneTests/FreightCartBay20261113/Textures'
    task.destination_name='T_PlatformPatinaColor';task.replace_existing=True;task.replace_existing_settings=False;task.automated=True;task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    asset=u.load_asset(task.destination_path+'/'+task.destination_name)
    if not asset or not task.get_objects():raise RuntimeError('Coverage import failed')
    asset.modify();asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT);asset.set_editor_property('srgb',True)
    if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Coverage not saved')
