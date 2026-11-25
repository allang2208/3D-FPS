"""Refresh the packed wear mask shared by the two terrain materials."""
import hashlib
from pathlib import Path

import unreal as u

root = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
directory = '/Game/WorldGeneration/TemperateHills/AbandonedVillage'
name = 'T_VillageRoadMask'
package = directory+'/'+name
disk = root/'Content'/(package.removeprefix('/Game/')+'.uasset')
source = (root/'SourceAssets/TemperateHillsVillage/RoadMask.png').resolve()
before = hashlib.sha256(disk.read_bytes()).digest()

task = u.AssetImportTask()
task.filename = str(source)
task.destination_path = directory
task.destination_name = name
task.automated = True
task.replace_existing = True
task.replace_existing_settings = False
task.save = False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture = next((obj for obj in task.get_objects() if isinstance(obj,u.Texture2D)
                and obj.get_path_name()==package+'.'+name),None)
if not texture:
    raise RuntimeError('Road wear texture import failed')
texture.srgb = False
texture.compression_no_alpha = False
texture.compression_settings = u.TextureCompressionSettings.TC_MASKS
texture.address_x = texture.address_y = u.TextureAddress.TA_CLAMP
if hashlib.sha256(disk.read_bytes()).digest()!=before:
    raise RuntimeError('Road texture changed on disk during import')
if not u.EditorAssetLibrary.save_loaded_asset(texture,False):
    raise RuntimeError('Cannot save '+package)
u.log('VILLAGE_WEAR_SAVED '+texture.get_path_name())
