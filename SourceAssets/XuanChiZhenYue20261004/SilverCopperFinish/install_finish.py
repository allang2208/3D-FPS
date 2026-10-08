"""Reimport four finish maps in place, preserving material graphs and mesh bindings."""
import json,shutil
from pathlib import Path
import unreal as u

P=Path(__file__).resolve().parent;S=P.parent;ROOT=P.parents[2]
D='/Game/Weapons/XuanChiZhenYue20261004'
if '-run=pythonscript' not in u.SystemLibrary.get_command_line().lower():
    editor=u.get_editor_subsystem(u.LevelEditorSubsystem)
    if editor and editor.is_in_play_in_editor():
        raise RuntimeError('Finish PIE before replacing the four sword finish textures; nothing was imported')

receipt={'complete':False,'saved':[],'game_tested':False,'rendered':False,
    'finish':{'blade_srgb':[208,216,224],'hilt_metal_srgb':[222,157,109]},
    'scope':'BaseColor and ORM only; existing normals, relief, materials, geometry and tassel motion retained'}
out=P/'import_receipt.json'
out.write_text(json.dumps(receipt,indent=2))
assets=[]
for revision,family,version in [('BladeV3','Blade','V3'),('SurfaceV2','Hilt','V2')]:
    for channel in ['BaseColor','ORM']:
        name='T_XuanChi_'+family+'_'+channel+'_'+version
        folder=D+'/'+revision+'/Textures'
        asset=u.load_asset(folder+'/'+name)
        if not asset:raise RuntimeError('Missing existing texture: '+folder+'/'+name)
        filename=S/revision/'Textures'/(family+'_'+channel+'.png')
        if not filename.is_file():raise RuntimeError('Missing authored texture: '+str(filename))
        backup=P/'Before/UE'/revision/(name+'.uasset')
        backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():
            shutil.copy2(ROOT/'Content/Weapons/XuanChiZhenYue20261004'/revision/'Textures'/(name+'.uasset'),backup)
        properties={key:asset.get_editor_property(key) for key in [
            'lod_group','never_stream','max_texture_size','lod_bias',
            'address_x','address_y','mip_gen_settings']}
        assets.append((asset,filename,name,folder,channel,properties))

for asset,filename,name,folder,channel,properties in assets:
    task=u.AssetImportTask()
    task.filename=str(filename);task.destination_name=name;task.destination_path=folder
    task.automated=True;task.replace_existing=True;task.replace_existing_settings=False;task.save=False
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    if not task.imported_object_paths:
        raise RuntimeError('Texture import did not return an asset: '+name)
    texture=u.load_asset(folder+'/'+name)
    for key,value in properties.items():texture.set_editor_property(key,value)
    texture.set_editor_property('srgb',channel=='BaseColor')
    texture.set_editor_property('compression_settings',u.TextureCompressionSettings.TC_BC7 if channel=='BaseColor' else u.TextureCompressionSettings.TC_MASKS)
    if not u.EditorLoadingAndSavingUtils.save_packages([texture.get_outermost()],False):
        raise RuntimeError('Could not save imported texture: '+name)
    receipt['saved'].append(texture.get_path_name())
    out.write_text(json.dumps(receipt,indent=2))
receipt['complete']=True
out.write_text(json.dumps(receipt,indent=2))
print('XUANCHI_SILVER_COPPER_FINISH_SAVED '+json.dumps(receipt))
