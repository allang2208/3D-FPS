"""Extend the existing persistent world without saving any of its referenced sublevels."""
import hashlib
import json
import os
import runpy
import subprocess
from pathlib import Path

import unreal as u

batch = Path(os.environ["FPS_FOREST_VILLAGE_BATCH"])
directory = Path(os.environ["FPS_FOREST_REGION_SOURCE"])
directory.mkdir(parents=True, exist_ok=True)
root = Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
terrain_folder = root / "Content/ForestPathStudy/VillageRegion/Terrain"
terrain_folder.mkdir(parents=True, exist_ok=True)
target = "/Game/GameMaps/L_ForestPathVillage"
file = root / "Content/GameMaps/L_ForestPathVillage.umap"
initial = hashlib.sha256(file.read_bytes()).hexdigest()
world = u.EditorLoadingAndSavingUtils.load_map(target)
if not world:
    raise RuntimeError("Could not open the forest village")
actors = u.get_editor_subsystem(u.EditorActorSubsystem)
scene = actors.get_all_level_actors()
land = next(a for a in scene if isinstance(a, u.Landscape) and "/L_ForestPathForest." in a.get_path_name())
if not u.ForestVillageRegion.export_forest_surface(land, str(directory / "study.f32")):
    raise RuntimeError("Cannot read the original terrain or village apron")
comps = land.get_components_by_class(u.LandscapeComponent)
centers = [(u.SystemLibrary.get_component_bounds(c)[0], c) for c in comps]
layer = u.load_asset("/Game/Example/Maps/NaniteExample_sharedassets/C_LayerInfo")
if not layer:
    raise RuntimeError("Missing source dirt layer")
border = bytearray()
for edge in range(4):
    for i in range(-252, 253):
        p = ((i, -252), (i, 252), (-252, i), (252, i))[edge]
        x, y = (max(-25199.95,min(25199.95,a*100.)) for a in p)
        c = min(centers, key=lambda e: (e[0].x-x)**2+(e[0].y-y)**2)[1]
        weight = c.editor_get_paint_layer_weight_at_location(u.Vector(x,y,0.), layer)
        border.append(round(255*min(1.,max(0.,weight))))
(directory / "edge_dirt.u8").write_bytes(border)
recipe = root / "Tools/WorldGeneration/ForestVillage/generate_region.py"
# Unreal embeds Python and sets its own environment. Use the production Python
# interpreter for SciPy and keep its interpreter search paths isolated.
env = dict(os.environ)
for key in ("PYTHONHOME","PYTHONPATH"):
    env.pop(key, None)
with (batch / "region-generator.log").open("w",encoding="utf-8") as out:
    subprocess.run([os.environ["FPS_REGION_PYTHON"], "-I", str(recipe), str(directory)],
                   env=env,stdout=out,stderr=subprocess.STDOUT,check=True)

templates = [c for a in scene if isinstance(a,u.PCGVolume)
             for c in a.get_components_by_class(u.InstancedStaticMeshComponent)]
region = next((a for a in scene if isinstance(a,u.ForestVillageRegion) and
               a.get_path_name().startswith(target+".")),None)
if not region:
    region = actors.spawn_actor_from_class(u.ForestVillageRegion,u.Vector(0,0,0))
if not region or not region.get_path_name().startswith(target+"."):
    raise RuntimeError("Could not place the region in the persistent map")
region.set_actor_label("Village Surroundings - Meadows and Ridges")
if not region.bake_ground(str(directory)):
    raise RuntimeError("Could not save the surrounding terrain meshes")
sample_info = None
if u.EditorAssetLibrary.does_asset_exist("/Game/ForestPathStudy/VillageRegion/SurfaceSample/M_ForestVillageSurface"):
    apply = runpy.run_path(str(recipe.with_name("author_surface_sample.py")))["apply"]
    sample_info = apply(region,templates,directory,directory/"SurfaceSample",batch)
elif not region.bake_vegetation(str(directory/"planting.bin"), templates):
    raise RuntimeError("Could not build the planting clusters")
if not u.HillsNavigationSystem.install_on_map(world):
    raise RuntimeError("Could not extend the navigation bounds")
if hashlib.sha256(file.read_bytes()).hexdigest()!=initial:
    raise RuntimeError("Persistent map changed on disk during the bake")
if not u.EditorLoadingAndSavingUtils.save_map(world,target):
    raise RuntimeError("Could not save forest village")
info = json.loads((directory/"generation.json").read_text())
if sample_info:
    info["surface_sample"] = sample_info
info.update(map=target, source_directory=str(directory), previous_sha256=hashlib.sha256((batch/"Before/Content/GameMaps/L_ForestPathVillage.umap").read_bytes()).hexdigest(),
            planting_graph="/Game/ForestPathStudy/VillageRegion/PCG_ForestVillageSurroundings",
            sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
            terrain_packages=len(list(terrain_folder.glob("SM_ForestGround_*.uasset"))))
(batch/"published.json").write_text(json.dumps(info,indent=2),encoding="utf-8")
print("FOREST_VILLAGE_REGION_SAVED", info)
