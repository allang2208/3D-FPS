"""Remove the rejected tropical river plants from this biome only."""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

PROJECT=Path('D:/FPS3D/FPSGAME')
ROOT=PROJECT/'SourceAssets/TemperateSpeciesCuration20261110'
PACKAGE='/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming'
if Path(u.Paths.project_dir()).resolve()!=PROJECT.resolve():raise RuntimeError('Wrong project')
if u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world():raise RuntimeError('Preserve running PIE')
if any(p.get_name()==PACKAGE for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
    raise RuntimeError('Preserve unsaved biome palette edits')
da=u.load_asset(PACKAGE)
rejected=set()
for prefix in ('/Game/PN_tropicalGroundPlants/Meshes/',
               '/Game/WorldGeneration/TemperateHills/RiverEcology/SM_River_',
               '/Game/WorldGeneration/TemperateHills/RiverEcologyDense/SM_RiverDense_'):
    for name in ('tropicalPlant_04_01','tropicalPlant_04_02','tropicalPlant_05_01','tropicalPlant_05_02'):
        rejected.add(prefix+name)
before=list(da.get_editor_property('river_understory'))
removed=[m.get_path_name() for m in before if m.get_path_name().split('.')[0] in rejected]
kept=[m for m in before if m.get_path_name().split('.')[0] not in rejected]
report={'removed':removed,'river_understory_before':len(before),'river_understory_after':len(kept),
        'saved':[],'map_modified':False,'game_run':False,'visual_tested':False}
if removed:
    relative=PACKAGE.removeprefix('/Game/')
    for suffix in ('.uasset','.uexp','.ubulk'):
        source=PROJECT/'Content'/(relative+suffix)
        target=ROOT/'Backups/Content'/(relative+suffix)
        if source.exists() and not target.exists():
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,target)
    da.set_editor_property('river_understory',kept)
    if not u.EditorAssetLibrary.save_loaded_asset(da,False):raise RuntimeError('Biome save failed')
    report['saved'].append(da.get_path_name())
report['trees']=[m.get_path_name() for m in da.get_editor_property('trees')]
report['forest_saplings']=[m.get_path_name() for m in da.get_editor_property('forest_saplings')]
report['finished_at']=datetime.now().astimezone().isoformat()
(ROOT/'Receipts/assets.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('HILLS_SPECIES_CURATION_SAVED removed='+str(len(removed)))
