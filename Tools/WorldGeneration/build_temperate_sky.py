"""Author the material for the hills' weather-compatible cloud layer.

Asset authoring, not a gameplay or visual test. Native defaults connect existing
biomes without rewriting a map or a biome asset held open by another editor.
Original engine and Fab assets are never saved.
"""
import json
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
BASE = '/Game/WorldGeneration/TemperateHills'
DEST = BASE+'/Sky'
OUT = ROOT/'Saved/TemperateSky'
OUT.mkdir(parents=True, exist_ok=True)
BACKUP = OUT/('Before-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
BACKUP.mkdir()
EAL = u.EditorAssetLibrary
LIB = u.MaterialEditingLibrary
TOOLS = u.AssetToolsHelpers.get_asset_tools()
REPORT = {'saved': [], 'scope': 'Hills sky authoring; no gameplay or visual tests'}

def load(path):
    obj = u.load_asset(path)
    if obj is None:
        raise RuntimeError('Missing sky dependency: '+path)
    return obj

def save(obj):
    if not EAL.save_loaded_asset(obj, False):
        raise RuntimeError('Could not save '+obj.get_path_name())
    REPORT['saved'].append(obj.get_path_name())

for relative in ['WorldGeneration/TemperateHills/Sky/MI_HillsClouds.uasset']:
    source = ROOT/'Content'/relative
    if source.exists():
        destination = BACKUP/relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

# Direct loading also works before the engine content asset registry has scanned.
source = load('/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst')
EAL.make_directory(DEST)
path = DEST+'/MI_HillsClouds'
cloud_mat = load(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
    'MI_HillsClouds', DEST, u.MaterialInstanceConstant, u.MaterialInstanceConstantFactoryNew())
LIB.set_material_instance_parent(cloud_mat, source)
scalars = {'Cloud_GlobalCoverage': -.10, 'Cloud_GlobalDensity': 0, 'StormClouds': 0}
REPORT['source'] = {'material': source.get_path_name(), 'parameters': {
    str(n): LIB.get_material_instance_scalar_parameter_value(source, n)
    for n in LIB.get_scalar_parameter_names(source)}}
for name, value in scalars.items():
    if name not in REPORT['source']['parameters']:
        raise RuntimeError('Cloud material does not expose '+name)
    # UE 5.8 applies the setter but leaves its return value false.
    LIB.set_material_instance_scalar_parameter_value(cloud_mat, name, value)
albedo = LIB.get_material_instance_vector_parameter_value(source, 'Cloud_AlbedoColor')
LIB.set_material_instance_vector_parameter_value(cloud_mat, 'Cloud_AlbedoColor', u.LinearColor(.96, .98, 1, albedo.a))
LIB.set_material_instance_vector_parameter_value(cloud_mat, 'Layout_WindControls', u.LinearColor(1, .32, .12, 1/3))
LIB.set_material_instance_vector_parameter_value(cloud_mat, 'Storm_LightningColor', u.LinearColor(0, 0, 0, 0))
LIB.update_material_instance(cloud_mat)
save(cloud_mat)

REPORT['cloud'] = {'runtime_component': 'HillsWeatherClouds', 'material': cloud_mat.get_path_name(),
                   'bottom_km': 2, 'height_km': 1.2, 'view_sample_scale': .7, 'scalars': scalars}
REPORT['connection'] = 'Native SkyCloudMaterial default; async activation during hills loading'
REPORT['backup'] = str(BACKUP)
(OUT/'authoring.json').write_text(json.dumps(REPORT, ensure_ascii=False, indent=2), encoding='utf-8')
u.log('TEMPERATE_SKY_AUTHORING_COMPLETE '+str(OUT/'authoring.json'))
