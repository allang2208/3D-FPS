"""Install the fixed hills vegetation variants with one write to the live palette."""
import json
import runpy
import shutil
from pathlib import Path

import unreal as ue


TOOLS = Path(__file__).resolve().parent
PROJECT = TOOLS.parents[1]
PACKAGE = "/Game/WorldGeneration/TemperateHills/DA_TemperateHillsStreaming"
OUTPUT = PROJECT / "Saved/HillsLandscapePass20261120"


def install():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    palette = ue.load_asset(PACKAGE)
    if not palette:
        raise RuntimeError("Missing fixed hills vegetation palette")
    package_file = PROJECT / "Content" / (PACKAGE.removeprefix("/Game/") + ".uasset")
    backup = OUTPUT / "DA_TemperateHillsStreaming.before.uasset"
    if not backup.exists():
        shutil.copy2(package_file, backup)

    roles = ("river_pebbles", "quarry_shore_chips", "rainforest_twigs", "rainforest_herbs",
             "river_ground_cover", "backdrop_trees", "wet_bank_saplings")
    before = {role: len(palette.get_editor_property(role)) for role in roles}
    ground = runpy.run_path(str(TOOLS / "hills_ground_palette.py"))["assign_ground_palette"](palette)
    crowns = runpy.run_path(str(TOOLS / "build_hills_alder_canopy.py"))["apply_palette"](palette)
    saplings = runpy.run_path(str(TOOLS / "build_hills_wet_saplings.py"))["apply_palette"](palette)
    if not ue.EditorAssetLibrary.save_loaded_asset(palette, False):
        raise RuntimeError("Could not save " + PACKAGE)

    lods = {}
    for paths in ground.values():
        for path in paths:
            mesh = ue.load_asset(path)
            lods[path] = [mesh.get_num_triangles(i) for i in range(mesh.get_num_lods())]
    counts = {role: {"before": before[role], "after": len(palette.get_editor_property(role))}
              for role in roles}
    receipt_file = OUTPUT / "SceneryPalette.json"
    if receipt_file.exists():
        baseline = json.loads(receipt_file.read_text(encoding="utf-8")).get("role_counts", {})
        for role in counts.keys() & baseline.keys():
            counts[role]["before"] = baseline[role]["before"]
    receipt = {"palette": PACKAGE, "role_counts": counts, "ground": ground, "ground_lod_triangles": lods,
               "crowns": crowns, "wet_saplings": saplings}
    receipt_file.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    ue.log("HILLS_SCENERY_PALETTE_SAVED " + PACKAGE)


if __name__ == "__main__":
    install()
