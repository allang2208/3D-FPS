"""Export the two installed village surfaces for the A/B road palette."""
from pathlib import Path
import os
import unreal as u

out = Path(os.environ['FPS_FOREST_REFERENCE_SOURCE']) / 'Village'
out.mkdir(parents=True, exist_ok=True)
sets = [
    ('ChapelEarth', '/Game/WorldGeneration/TemperateHills/OldChapel/Textures/Surfaces/T_ChapelEarth_', ('B','N','ORM','H')),
    ('RockyRoad', '/Game/UnrealNormandy/Textures/T_LC_GroundRockyRoad_00A_', ('Albedo','Normal','RHAOM','Height')),
]
for label, prefix, channels in sets:
    for ch in channels:
        asset = u.load_asset(prefix+ch)
        if not asset:
            raise RuntimeError(prefix+ch)
        task = u.AssetExportTask()
        task.object = asset
        task.filename = str(out/(label+'_'+ch+('.png' if ch=='Height' else '.tga')))
        task.automated = True
        task.prompt = False
        task.replace_identical = True
        if not u.Exporter.run_asset_export_task(task):
            raise RuntimeError(task.filename)

