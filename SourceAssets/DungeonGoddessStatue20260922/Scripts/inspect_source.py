"""Inspect the downloaded Diana glTF source before any processing.

Run:
    "E:/Program Files/Blender Foundation/Blender 5.1/blender.exe" --background --factory-startup \
        --python D:/FPS3D/FPSGAME/SourceAssets/DungeonGoddessStatue20260922/Scripts/inspect_source.py \
        -- <source.glb>

Prints object transforms, triangle counts, bounding boxes (Blender Z-up, metres),
material slots and image inventory. Read-only: saves nothing.
"""
import sys
import bpy


def main():
    argv = sys.argv
    src = argv[argv.index("--") + 1] if "--" in argv else None
    if not src:
        raise SystemExit("usage: ... -- <source.glb>")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    print("=" * 72)
    print("SOURCE:", src)
    print("Blender:", bpy.app.version_string)

    total_tris = 0
    for obj in bpy.context.scene.objects:
        print("-" * 72)
        print("object:", obj.name, "type:", obj.type)
        print("  location:", tuple(round(v, 4) for v in obj.location))
        print("  rotation_euler(rad):", tuple(round(v, 4) for v in obj.rotation_euler))
        print("  scale:", tuple(round(v, 4) for v in obj.scale))
        print("  matrix_world translation:", tuple(round(v, 4) for v in obj.matrix_world.translation))
        if obj.type != "MESH":
            continue
        me = obj.data
        me.calc_loop_triangles()
        tris = len(me.loop_triangles)
        total_tris += tris
        print("  verts:", len(me.vertices), "polys:", len(me.polygons), "tris:", tris)
        print("  uv_layers:", [uv.name for uv in me.uv_layers])
        print("  has_custom_normals:", me.has_custom_normals)
        print("  local bbox dims:", tuple(round(v, 4) for v in obj.dimensions))
        ws = [obj.matrix_world @ v.co for v in me.vertices]
        if ws:
            xs = [p.x for p in ws]
            ys = [p.y for p in ws]
            zs = [p.z for p in ws]
            print("  world bbox min:", (round(min(xs), 4), round(min(ys), 4), round(min(zs), 4)))
            print("  world bbox max:", (round(max(xs), 4), round(max(ys), 4), round(max(zs), 4)))
            print("  world size (X,Y,Z):", (round(max(xs) - min(xs), 4), round(max(ys) - min(ys), 4),
                                            round(max(zs) - min(zs), 4)))
        print("  material slots:", [s.material.name if s.material else None for s in obj.material_slots])
        for slot in obj.material_slots:
            mat = slot.material
            if not mat or not mat.use_nodes:
                continue
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image:
                    img = node.image
                    print("    image:", img.name, img.size[0], "x", img.size[1],
                          "channels:", img.channels, "packed:", bool(img.packed_file),
                          "filepath:", img.filepath)

    print("=" * 72)
    print("TOTAL_TRIS:", total_tris)
    print("images in file:", len(bpy.data.images))
    for img in bpy.data.images:
        print("  ", img.name, img.size[0], "x", img.size[1], img.file_format)


main()
