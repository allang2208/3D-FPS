"""Export the apartment to glTF for Unreal import.

glTF (not FBX) because it carries the PBR texture set with correct names, and
Unreal's glTF importer maps base colour / normal / roughness-metallic for us.
Units: scene is metric with scale 1.0, glTF is metres - 1:1 into UE.
"""
import os

import bpy

ROOT = r"D:\CyberpunkApartment"
OUT = os.path.join(ROOT, "export")
os.makedirs(OUT, exist_ok=True)

# select only what should travel to UE: all mesh objects, no lights/cameras
bpy.ops.object.select_all(action="DESELECT")
meshes = [o for o in bpy.data.objects if o.type == "MESH"]
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]

path = os.path.join(OUT, "CyberpunkApartment.gltf")
bpy.ops.export_scene.gltf(
    filepath=path,
    export_format="GLTF_SEPARATE",      # .gltf + .bin + textures/ (UE-friendly)
    use_selection=True,
    export_apply=True,                  # bake modifiers
    export_yup=True,                    # glTF Y-up, importer converts back
    export_materials="EXPORT",
    export_image_format="AUTO",
    export_texcoords=True,
    export_normals=True,
    export_tangents=False,
    export_cameras=False,
    export_lights=False,
    export_extras=True,
)

size = 0
count = 0
for dirpath, _, files in os.walk(OUT):
    for f in files:
        size += os.path.getsize(os.path.join(dirpath, f))
        count += 1

_result = {"gltf": path, "files": count, "mb": round(size / 1048576, 1),
           "meshes": len(meshes)}
print(_result, flush=True)