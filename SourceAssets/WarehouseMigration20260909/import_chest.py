import json
from pathlib import Path
import unreal
out=Path('D:/FPS3D/FPSGAME/SourceAssets/WarehouseMigration20260909');dest='/Game/ColdSteelUI/Warehouse20260909'
task=unreal.AssetImportTask();task.filename=str(out/'warehouse_chest_rigid.glb');task.destination_path=dest;task.automated=True;task.replace_existing=False;task.save=True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
assets=[unreal.EditorAssetLibrary.load_asset(p) for p in unreal.EditorAssetLibrary.list_assets(dest,recursive=True,include_folder=False)]
meshes=[a for a in assets if isinstance(a,unreal.SkeletalMesh)];animations=[a for a in assets if isinstance(a,unreal.AnimSequence)]
assert len(meshes)==1,[(a.get_name(),a.get_class().get_name()) for a in assets]
result={'mesh':meshes[0].get_path_name()}
for a in animations:
 name=a.get_name().lower()
 for key,duration in [('open',.9),('close',.7)]:
  if key in name:
   assert abs(a.get_play_length()-duration)<.04,(name,a.get_play_length());result[key]=a.get_path_name()
assert 'open' in result and 'close' in result,result
Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/warehouse_assets.json').write_text(json.dumps(result,indent=2))
(out/'import_report.json').write_text(json.dumps(result,indent=2));unreal.log('WAREHOUSE_IMPORT_PASS '+str(result))
