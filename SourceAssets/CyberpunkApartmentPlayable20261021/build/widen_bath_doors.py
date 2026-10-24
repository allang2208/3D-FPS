"""Widen the two bathroom doorways in the saved .blend and re-export glTF.

The bathroom openings were authored 80 cm wide; the interior partitions are
12 cm thick, which leaves 78 cm of clear width. The player capsule is 84 cm
across (InitCapsuleSize(42, 96)), so those two rooms are unreachable no matter
how collision is configured -- it is a source geometry problem, not a physics
one.

This opens both to 96 cm of clear width (opening span 1.14-2.10 and
3.22-4.18 m, i.e. 96 cm minus the 0.4 cm bay edge on each side), then
regenerates the affected architectural meshes with the same builders the
project already uses, and re-exports the glTF that UE imports.

Run:
  blender.exe --background --factory-startup --python widen_bath_doors.py
"""
import os
import sys

import bpy

ROOT = r"D:\CyberpunkApartment"
BLEND = os.path.join(ROOT, "CyberpunkApartment.blend")
BUILD = os.path.join(ROOT, "build")
sys.path.insert(0, BUILD)

bpy.ops.wm.open_mainfile(filepath=BLEND)
print("loaded blend: objects=%d materials=%d" % (len(bpy.data.objects),
                                                 len(bpy.data.materials)))

# The door opening edits live in build/s1_arch.py (wall_run openings),
# build/s12_joinery.py (skirting gaps, thresholds, door leaves) and
# build/s13_finish.py (tiled wainscot gaps). Each module runs its own build()
# at import time, rebuilding the merged meshes from the edited source.
import importlib                                    # noqa: E402

for mod_name in ("cy_lib", "furn", "furn2"):
    if mod_name in sys.modules:
        importlib.reload(sys.modules[mod_name])

results = {}
for name in ("s1_arch", "s12_joinery", "s13_finish"):
    try:
        if name in sys.modules:
            mod = importlib.reload(sys.modules[name])
        else:
            mod = importlib.import_module(name)
        results[name] = getattr(mod, "_result", "no _result")
    except Exception as exc:                        # noqa: BLE001
        results[name] = "ERROR %s: %s" % (type(exc).__name__, exc)
        print(results[name])

print("rebuild results:", results)

# Save the .blend so the widened openings are the authored truth from now on.
bpy.ops.wm.save_mainfile(filepath=BLEND)
print("saved blend")

# Re-export for UE import (same settings as build/export_gltf.py).
OUT = os.path.join(ROOT, "export")
os.makedirs(OUT, exist_ok=True)
bpy.ops.object.select_all(action="DESELECT")
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]

bpy.ops.export_scene.gltf(
    filepath=os.path.join(OUT, "CyberpunkApartment.gltf"),
    export_format="GLTF_SEPARATE",
    use_selection=True,
    export_apply=True,
    export_yup=True,
    export_materials="EXPORT",
    export_image_format="AUTO",
    export_texcoords=True,
    export_normals=True,
    export_tangents=False,
    export_cameras=False,
    export_lights=False,
    export_extras=True,
)
print("exported glTF")
_result = results
