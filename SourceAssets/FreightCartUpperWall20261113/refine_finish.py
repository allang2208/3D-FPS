"""Finish the photographed bay without editing any project-wide material or light."""
from pathlib import Path
import runpy,unreal as u
ROOT=Path(__file__).resolve().parent;BASE='/Game/SceneTests/FreightCartUpperWall20261113'
def apply(world,row):
    runpy.run_path(str(ROOT/'distribute.py'))['apply'](world,dict(corner=5.4,raking=5.0,return_power=3.3))
    if row.get('load_only'):return
    for suffix in ['Color','Normal']:
        name='T_CastBay_'+suffix;task=u.AssetImportTask()
        task.filename=str(ROOT/(name+'.png'));task.destination_name=name;task.destination_path=BASE+'/Textures'
        task.automated=True;task.save=False;task.replace_existing=True;task.replace_existing_settings=False
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        if not task.get_objects():raise RuntimeError('Import failed '+name)
        asset=u.load_asset(task.destination_path+'/'+name);asset.modify()
        asset.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_DEFAULT if suffix=='Color' else u.TextureCompressionSettings.TC_NORMALMAP)
        asset.set_editor_property('srgb',suffix=='Color')
        if not u.EditorAssetLibrary.save_loaded_asset(asset,False):raise RuntimeError('Save failed '+name)
