"""Blender background authoring for small, instanced Quixel shoreline stones."""
from pathlib import Path

import bpy


PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / "SourceAssets/HillsQuarryRockLayout20261119"
OUTPUT = PROJECT / "SourceAssets/HillsGroundPalette"
# Separate objects from the project's licensed udqhfcyva scan set. Retain
# their original metres, UV islands, and centred ground-contact pivots.
STONES = (
    ("SM_QuarryChip01", "SM_ShoreLimestoneFlat", 240),
    ("SM_QuarryChip05", "SM_ShoreLimestoneLong", 280),
)


def export_stone(source, name, triangles):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(SOURCE / (source + ".fbx")))
    stone, = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    stone.name = name
    bpy.context.view_layer.objects.active = stone
    stone.data.calc_loop_triangles()
    decimate = stone.modifiers.new("Shore silhouette", "DECIMATE")
    decimate.ratio = triangles / len(stone.data.loop_triangles)
    decimate.use_collapse_triangulate = True
    bpy.ops.object.modifier_apply(modifier=decimate.name)
    bpy.ops.object.select_all(action="DESELECT")
    stone.select_set(True)
    bpy.ops.export_scene.fbx(
        filepath=str(OUTPUT / (name + ".fbx")), use_selection=True,
        object_types={"MESH"}, axis_forward="-Y", axis_up="Z",
        mesh_smooth_type="FACE", use_tspace=True, bake_anim=False,
    )
    stone.data.calc_loop_triangles()
    print("HILLS_GROUND_SOURCE", name, len(stone.data.loop_triangles))


OUTPUT.mkdir(parents=True, exist_ok=True)
for row in STONES:
    export_stone(*row)
