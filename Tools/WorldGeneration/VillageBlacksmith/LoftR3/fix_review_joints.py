"""Save repaired masonry joint backing observed in the in-game loft review."""
import json,runpy,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/LoftR3/ReviewFixR4'
before=OUT/'L_AbandonedVillage.before-joint-fix.umap'
if not before.exists():shutil.copy2(ROOT/'Content/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage.umap',before)
runpy.run_path(str(HERE/'publish_revision.py'),run_name='__main__')
(OUT/'joints-saved.json').write_text(json.dumps(dict(map_saved=True,joints=8,
    material='/Game/UnrealNormandy/MaterialInstances/MI_Main_Mortar_00A',
    repair_only=True,window_openings_unchanged=True),indent=2),encoding='utf-8')
