"""Apply only the legendary edge layer to current normal and whirlwind surfaces."""
import json
import runpy
from pathlib import Path
import unreal as u

root = Path(u.Paths.project_dir()).resolve()
here = root / "SourceAssets/Zhanmadao20261018/LegendaryRunesV1"
data = root / "Content/ColdSteelData"
blades = json.loads((data / "zhanmadao-modules.json").read_bytes())["slots"]["blade_1"]
temporal = json.loads((data / "whirlwind-temporal-materials.json").read_bytes())
profiles = json.loads((root / "SourceAssets/ZhanmadaoDamascus20261111/profiles.json").read_bytes())
apply = runpy.run_path(str(here / "edge_material.py"))["apply"]
targets = {}
for key, row in blades.items():
    for path in row["materials"].values():
        if "M_TangDaoBladeRuneSurface" in path:
            targets[path] = targets[temporal[path]] = key

if "-run=pythonscript" not in u.SystemLibrary.get_command_line().lower():
    if u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor():
        raise RuntimeError("PIE active")
    dirty = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty.intersection(path.split(".")[0] for path in targets):
        raise RuntimeError("A target material has unsaved editor changes")

for path, key in targets.items():
    material = u.load_asset(path)
    if not material:
        raise RuntimeError("Missing blade material " + path)
    apply(material, profiles[key])
    errors = u.MaterialEditingLibrary.recompile_material(material)
    if errors:
        raise RuntimeError("Material compile failed " + path + " " + str(errors))
    if not u.EditorAssetLibrary.save_loaded_asset(material, False):
        raise RuntimeError("Could not save " + path)
    print("DAO_EDGE_SAVED " + path, flush=True)
print("DAO_EDGE_COMPLETE " + str(len(targets)), flush=True)
