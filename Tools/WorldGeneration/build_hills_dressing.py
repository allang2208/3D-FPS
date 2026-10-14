"""Fill the Phase-1 dressing fields on DA_TemperateHillsStreaming.

Assigns meadow flowers, forest-floor deadwood, hillside cliffs, backdrop canopy
meshes and leaves every scalar at its code default. Run with the updated
FPSGAMEEditor module and -run=pythonscript -nullrhi. Asset authoring only; it
does not load a map or run gameplay.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
BASE = '/Game/WorldGeneration/TemperateHills'
RURAL = '/Game/RuralAustralia/StaticMeshes'
PN = '/Game/PN_FoliageCollection/Meshes'
OUT = ROOT / 'Saved/HillsDressing20261014'
OUT.mkdir(parents=True, exist_ok=True)
EAL = u.EditorAssetLibrary
REPORT = {'fields': {}, 'missing': [], 'saved': []}


def load(path):
    obj = u.load_asset(path)
    if obj is None:
        REPORT['missing'].append(path)
        u.log_error('HILLS_DRESSING missing ' + path)
    return obj


def meshes(prefix, names):
    out = []
    for name in names:
        base = name.rsplit('/', 1)[-1]
        obj = load(f'{prefix}/{name}.{base}')
        if obj is not None and 'StaticMesh' in obj.get_class().get_name():
            out.append(obj)
        elif obj is not None:
            REPORT['missing'].append(prefix + '/' + name + ' (not a StaticMesh)')
    return out


CONFIG_PATH = BASE + '/DA_TemperateHillsStreaming'
target = ROOT / 'Content/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming.uasset'
backup = OUT / ('DA_TemperateHillsStreaming-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.uasset')
shutil.copy2(target, backup)

assets = load(CONFIG_PATH)

# One variant per species keeps meadow colour distinct instead of near-dupes.
flowers = meshes(PN + '/flowerMesh', [
    'flower_01_01', 'flower_02_01', 'flower_03_01', 'flower_04_01',
    'flower_05_01', 'flower_06_01', 'flower_07_01', 'flower_08_01',
    'flower_09_01', 'flower_10_01', 'flower_11_01', 'flower_12_01',
    'flower_13_01', 'flower_14_01', 'flower_15_01', 'flower_16_01'])
if flowers:
    assets.set_editor_property('meadow_flowers', flowers)
REPORT['fields']['meadow_flowers'] = len(flowers)

logs = meshes(RURAL + '/Vegetation', [
    'Log_L_01/SM_Log_L_01', 'Log_M_01/SM_Log_M_01',
    'Log_S_01/SM_Log_S_01', 'Log_S_02/SM_Log_S_02'])
roots = meshes(RURAL + '/Vegetation', ['Roots_01/SM_Roots_01'])
if logs:
    assets.set_editor_property('fallen_logs', logs)
if roots:
    assets.set_editor_property('forest_roots', roots)
REPORT['fields']['fallen_logs'] = len(logs)
REPORT['fields']['forest_roots'] = len(roots)

cliffs = meshes(RURAL + '/Rocks', [
    'Cliff_L_01/SM_Cliff_L_01_A', 'Cliff_L_01/SM_Cliff_L_01_B',
    'Cliff_M_01/SM_Cliff_M_01_A', 'Cliff_M_01/SM_Cliff_M_01_B',
    'Cliff_M_02/SM_Cliff_M_02_A', 'Cliff_M_02/SM_Cliff_M_02_B',
    'Cliff_M_02/SM_Cliff_M_02_C', 'Cliff_M_03/SM_Cliff_M_03'])
if cliffs:
    assets.set_editor_property('cliffs', cliffs)
REPORT['fields']['cliffs'] = len(cliffs)

# Static eucalypts read as treeline silhouettes on the backdrop rings.
canopy = meshes(RURAL + '/Vegetation', [
    'Tree_L_01/SM_Tree_L_01', 'Tree_M_01/SM_Tree_M_01', 'Tree_M_02/SM_Tree_M_02',
    'Tree_M_03/SM_Tree_M_03', 'Tree_M_04/SM_Tree_M_04', 'Tree_S_01/SM_Tree_S_01'])
if canopy:
    assets.set_editor_property('backdrop_trees', canopy)
REPORT['fields']['backdrop_trees'] = len(canopy)

if REPORT['missing']:
    u.log_warning('HILLS_DRESSING skipped ' + str(len(REPORT['missing'])) + ' entries')
EAL.save_loaded_asset(assets, False)
REPORT['saved'].append(CONFIG_PATH)
u.log('HILLS_DRESSING_COMPLETE ' + json.dumps(REPORT['fields']))
(OUT / 'report.json').write_text(json.dumps(REPORT, indent=2))
