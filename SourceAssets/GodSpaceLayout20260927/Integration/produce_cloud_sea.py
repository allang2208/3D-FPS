"""Save the cloud-sea material and the main hub's owning cloud-layer settings."""
import hashlib
import json
import runpy
import shutil
from datetime import datetime
from pathlib import Path
import unreal as u
ROOT=Path(__file__).parent
PROJECT=ROOT.parents[2]
MAP='/Game/GameMaps/DayNight_Lighting'
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
dirty={p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()}
if MAP in dirty:raise RuntimeError('Preserve unsaved edits to the main hub map')
world=editor.get_editor_world() if editor else None
if not world or world.get_path_name().split('.')[0]!=MAP:
    if dirty or (editor and editor.get_game_world()):
        raise RuntimeError('Cannot change the loaded level while maps are unsaved or a game is running')
    world=u.EditorLoadingAndSavingUtils.load_map(MAP)
if not world:raise RuntimeError('Cannot load the main hub editor world')
# This is the editor map package, never a PIE copy. Saving it does not start,
# stop or write the running game world.
sky=next(a for a in u.GameplayStatics.get_all_actors_of_class(world,u.Actor)
    if a.get_components_by_class(u.SkyAtmosphereComponent))
src=PROJECT/'Content/GameMaps/DayNight_Lighting.umap'
dst=PROJECT/'trash/godspace-cumulus-20260928'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')/'Content/GameMaps/DayNight_Lighting.umap'
dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
mi=runpy.run_path(str(ROOT/'build_cloud_sea.py'))['build']()
settings=runpy.run_path(str(ROOT/'configure_cloud_sea.py'))['apply'](sky,mi)
if not u.EditorLoadingAndSavingUtils.save_map(world,MAP):raise RuntimeError('Cloud layer settings could not be saved')
placements=ROOT/'placements.json'
data=json.loads(placements.read_text(encoding='utf8'))
data.update(cloud_bottom_km=.62,cloud_height_km=.70,atmosphere_ground_z_cm=-150000)
placements.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf8')
report={'saved_map':MAP,'saved_material':mi.get_path_name(),'persistent_cloud_settings':settings,
    'backup':str(dst),'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),
    'coverage_target':.8,'coverage_definition':'weather texture percentile footprint',
    'cloud_layer_bounds_below_platform_m':[180,880],
    'cloud_layers':1,'runtime_tested':False,'screen_coverage_measured':False}
report.update(material_generation='Takram-inspired cumulus with native UE lighting',view_sample_scale=3.,
    shadow_view_sample_scale=.5,performance_measured=False)
(ROOT/'Receipts/cloud-sea-map.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('GODSPACE_CLOUD_SEA_MAP_SAVED '+json.dumps(report))
