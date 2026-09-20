"""Publish the authored portrait PNG and refresh its existing UE texture asset."""
from pathlib import Path
import shutil
import unreal

root = Path(unreal.Paths.project_dir()).resolve()
source = root / 'SourceAssets/AxeImpactInventory20260919/axe_upright.png'
destination = root / 'Content/ColdSteelData/ProductionTools/axe.png'
shutil.copy2(source, destination)

task = unreal.AssetImportTask()
task.filename = str(destination)
task.destination_path = '/Game/ColdSteelData/ProductionTools'
task.destination_name = 'axe'
task.automated = True
task.replace_existing = True
task.replace_existing_settings = False
task.save = True
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
print('AXE_UPRIGHT_ICON_IMPORTED', task.imported_object_paths)
