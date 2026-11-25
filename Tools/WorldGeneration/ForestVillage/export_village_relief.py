"""Read the two official sublevels without changing them. Run with Unreal's Python commandlet."""
import json
import os
from pathlib import Path

import unreal as u


def load(path):
    if not u.EditorLoadingAndSavingUtils.load_map(path):
        raise RuntimeError(f"Cannot load {path}")
    return u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()


out = Path(os.environ["FPS_VILLAGE_RELIEF_SOURCE"])
out.mkdir(parents=True, exist_ok=True)
if os.environ.get("FPS_VILLAGE_CONTACTS_ONLY") != "1":
    forest = load("/Game/ForestPathStudy/Maps/L_ForestPathForest")
    land = next(a for a in forest if isinstance(a, u.Landscape))
    if not u.ForestVillageRegion.export_forest_surface(land, str(out / "reference.f32")):
        raise RuntimeError("Could not export slope and village reference elevations")

# This sublevel is authored around its local floor at Z=0. Store contact boxes
# in village-local metres, independently of the level instance's runtime transform.
actors = load("/Game/WorldGeneration/TemperateHills/AbandonedVillage/L_AbandonedVillage")
contacts = []
for actor in actors:
    for comp in actor.get_components_by_class(u.StaticMeshComponent):
        mesh = comp.get_editor_property("static_mesh")
        if not mesh or "/ExteriorLOD/" in mesh.get_path_name():
            continue
        box = mesh.get_bounding_box()
        corners = [u.Vector(x, y, z) for x in (box.min.x, box.max.x)
                   for y in (box.min.y, box.max.y) for z in (box.min.z, box.max.z)]
        instanced = isinstance(comp, u.InstancedStaticMeshComponent)
        for i in range(comp.get_instance_count() if instanced else 1):
            tr = comp.get_instance_transform(i, world_space=True) if instanced else comp.get_world_transform()
            points = [u.MathLibrary.transform_location(tr, c) for c in corners]
            if min(p.z for p in points) > 75 or max(p.z for p in points) < -85:
                continue
            xy = [round(v * .01, 3) for v in (min(p.x for p in points), min(p.y for p in points),
                                               max(p.x for p in points), max(p.y for p in points))]
            if xy[2] < -75 or xy[0] > 72 or xy[3] < -60 or xy[1] > 60:
                continue
            contacts.append([*xy, mesh.get_name(), instanced])
(out / "contacts.json").write_text(json.dumps(contacts, separators=(",", ":")), encoding="utf8")
