"""Update only the saved village road coverage texture after the runtime corner fix."""
from pathlib import Path
import hashlib,json
import unreal as u

root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
out=root/'Saved/VillageRuntimeReview/20261114'
asset='Content/WorldGeneration/TemperateHills/AbandonedVillage/T_VillageRoadMask.uasset'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
if sha(root/asset)!=sha(out/'RoadFixBefore'/asset):
    raise RuntimeError('Road mask changed since this repair backup; preserve newer asset')
task=u.AssetImportTask()
task.filename=str(root/'SourceAssets/TemperateHillsVillage/RoadMask.png')
task.destination_path='/Game/WorldGeneration/TemperateHills/AbandonedVillage'
task.destination_name='T_VillageRoadMask'
task.automated=True
task.replace_existing=True
task.replace_existing_settings=False
u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture=u.load_asset(task.destination_path+'/'+task.destination_name)
if not texture:raise RuntimeError('Road texture import did not return an asset')
texture.srgb=False
texture.compression_settings=u.TextureCompressionSettings.TC_MASKS
texture.address_x=texture.address_y=u.TextureAddress.TA_CLAMP
if not u.EditorAssetLibrary.save_loaded_asset(texture,False):raise RuntimeError('Texture save failed')
(out/'road-fix-saved.json').write_text(json.dumps(dict(asset=texture.get_path_name(),saved=True,
    sha256_before=sha(out/'RoadFixBefore'/asset),sha256_after=sha(root/asset),
    village_map_unchanged=True,changed='Eastern courtyard road dogleg; no wall or house transforms changed'),indent=2),encoding='utf-8')
u.log('VILLAGE_RUNTIME_ROAD_FIX_SAVED')
