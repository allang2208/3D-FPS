"""Configure the four visible LG_A slots and bind the foliage-enabled forest material."""
import json
from pathlib import Path
import unreal as u

assets = u.EditorAssetLibrary
edit = u.MaterialEditingLibrary
receipt = json.loads((Path(u.Paths.convert_relative_path_to_full(u.Paths.project_saved_dir())) / "forest-scan-assets.json").read_text("utf8"))
grass = u.load_asset("/Game/Landscape/Materials/LandscapeGrass/LG_A")
slots = []
# Density values use LandscapeGrassType's native instances per ten square metres.
for key,density,small,large in [
    ("xisgcic",5.,1.,1.), ("xjiifd1",94.380165,.2,.5),
    ("relu7",241.404968,.3,.8), ("rioqm",59.586777,.2,.8)
]:
    mesh = u.load_asset(receipt[key][0])
    item = u.GrassVariety()
    item.set_editor_property("grass_mesh", mesh)
    value = item.get_editor_property("grass_density")
    value.set_editor_property("default",density)
    item.set_editor_property("grass_density",value)
    item.set_editor_property("scale_x",u.FloatInterval(min=small,max=large))
    slots.append(item)
grass.set_editor_property("grass_varieties",slots)
if not assets.save_loaded_asset(grass,False):
    raise RuntimeError("Could not save the four landscape grass slots")
base = "/Game/ForestPathStudy/Materials/MI_ForestPathLandscape"
out = "/Game/ForestPathStudy/Materials/MI_ForestPathForest"
material = u.load_asset(out) if assets.does_asset_exist(out) else assets.duplicate_asset(base,out)
names = edit.get_static_switch_parameter_names(material)
switch = next(n for n in names if str(n).strip().rstrip("?").lower() == "material a foliage")
edit.set_material_instance_static_switch_parameter_value(material,switch,True)
edit.update_material_instance(material)
if not assets.save_loaded_asset(material,False):
    raise RuntimeError("Forest landscape material save failed")
landscape = next(a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors() if isinstance(a,u.Landscape))
landscape.set_editor_property("landscape_material",material)
