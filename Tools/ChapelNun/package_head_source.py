"""Package the downloaded Meshy source in an editable Blender scene; no renders."""
import bpy
import json
from pathlib import Path
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2] / "SourceAssets" / "ChapelNun20261115"
RUN = ROOT / "MeshyHeadR1"
OUT = RUN / "Authoring"
OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(RUN / "Source" / "NunHead_R1_glb.glb"))
source = bpy.data.collections.new("SOURCE_Meshy_Head_R1")
bpy.context.scene.collection.children.link(source)
meshes = []
for obj in list(bpy.context.scene.objects):
    for collection in list(obj.users_collection):
        collection.objects.unlink(obj)
    source.objects.link(obj)
    if obj.type == "MESH":
        obj.name = "NunHead_R1_Source" + ("" if not meshes else "_" + str(len(meshes)))
        meshes.append(obj)
        obj["production_stage"] = "Meshy high-detail source; facial topology and neck fitting pending"
        obj["concept"] = "NunHead_R2"
        obj["hair_is_separate"] = True

# Keep original Meshy topology, UVs, transforms and materials intact.
# Pack textures so the source can be opened without temporary CDN files.
for img in bpy.data.images:
    if img.source == "FILE":
        img.pack()
design = bpy.data.collections.new("REFERENCES_Approved_Concept")
bpy.context.scene.collection.children.link(design)
design.hide_render = True
design.hide_viewport = True
for i, relative in enumerate(["Design/NunHead_R2.png",
    "MeshyHeadR1/Inputs/01_front.png", "MeshyHeadR1/Inputs/02_three_quarter.png",
    "MeshyHeadR1/Inputs/03_profile.png", "MeshyHeadR1/Inputs/04_back.png"]):
    img = bpy.data.images.load(str(ROOT / relative), check_existing=True)
    img.pack()
    obj = bpy.data.objects.new(Path(relative).stem, None)
    obj.empty_display_type = "IMAGE"
    obj.data = img
    obj.empty_display_size = 2.0
    obj.location = (3.0 + i * 2.4, 0.0, 0.0)
    obj.hide_render = True
    design.objects.link(obj)

note = bpy.data.texts.new("PRODUCTION_STATE.json")
brief = json.loads((ROOT / "design-brief.json").read_text(encoding="utf-8"))
note.write(json.dumps({
    "concept": brief["concept"], "mesh_source": "../Source/NunHead_R1_glb.glb",
    "scope": "Independent head source; no hair, facial rig or game integration yet",
    "body_target": brief["bodySource"],
    "head_compatibility_reference": brief["headSourceForCompatibility"],
    "hair": brief["productionIntent"]["hair"],
    "remaining": ["facial retopology", "independent eyes and mouth interior",
                  "Kaitlin neck seam", "facial skeleton and skin weights",
                  "low bun groom and binding", "UE asset import"],
    "source_geometry_modified": False
}, ensure_ascii=False, indent=2))
for obj in bpy.context.selected_objects:
    obj.select_set(False)
for obj in meshes:
    obj.select_set(True)
if meshes:
    bpy.context.view_layer.objects.active = meshes[0]
    bounds = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    center = sum(bounds, Vector()) / len(bounds)
    extent = max((max(p[i] for p in bounds) - min(p[i] for p in bounds)) for i in range(3))
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                area.spaces.active.region_3d.view_location = center
                area.spaces.active.region_3d.view_distance = extent * 1.6
                area.spaces.active.shading.type = "MATERIAL"
path = OUT / "NunHead_R1_source.blend"
bpy.ops.wm.save_as_mainfile(filepath=str(path))
receipt = {
    "file": str(path), "source": str(RUN / "Source" / "NunHead_R1_glb.glb"),
    "source_geometry_modified": False, "packed_images": True,
    "mesh_objects": [{"name": obj.name, "vertices": len(obj.data.vertices),
                     "polygons": len(obj.data.polygons),
                     "materials": [slot.material.name if slot.material else None for slot in obj.material_slots]}
                    for obj in meshes],
    "renders_created": False, "ue_imported": False
}
(OUT / "saved_source.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("NUN_HEAD_SOURCE_SAVED " + str(path), flush=True)
