"""Pack textures, save the .blend, and report a scene summary."""
from __future__ import annotations

import os

import bpy

BLEND = r"D:\CyberpunkApartment\CyberpunkApartment.blend"


def build() -> dict:
    scn = bpy.context.scene
    scn.camera = bpy.data.objects["CAM_hero"]

    # pack every external image so the .blend is self-contained
    packed, failed = 0, []
    for img in bpy.data.images:
        if img.source != "FILE":
            continue
        try:
            img.pack()
            packed += 1
        except Exception as exc:  # noqa: BLE001
            failed.append(img.name + ": " + str(exc)[:40])

    objs = [o for o in scn.objects]
    tris = 0
    verts = 0
    for o in objs:
        if o.type != "MESH":
            continue
        me = o.data
        verts += len(me.vertices)
        tris += sum(max(0, len(p.vertices) - 2) for p in me.polygons)
    colls = {c.name: len(c.objects) for c in bpy.data.collections}
    mats = len(bpy.data.materials)
    imgs = len(bpy.data.images)
    lights = [o for o in objs if o.type == "LIGHT"]
    cams = [o.name for o in objs if o.type == "CAMERA"]

    # material bookkeeping: how many have image textures / normal maps
    tex_mats, norm_mats, emis_mats = 0, 0, 0
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        kinds = [n.type for n in m.node_tree.nodes]
        if "TEX_IMAGE" in kinds:
            tex_mats += 1
        if "NORMAL_MAP" in kinds:
            norm_mats += 1
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        if bsdf is not None and bsdf.inputs["Emission Strength"].default_value > 0.0:
            emis_mats += 1

    bpy.ops.wm.save_as_mainfile(filepath=BLEND, compress=True)
    return {
        "saved": BLEND,
        "size_mb": round(os.path.getsize(BLEND) / 1048576, 1),
        "objects": len(objs),
        "mesh_objects": sum(1 for o in objs if o.type == "MESH"),
        "verts": verts, "tris": tris,
        "materials": mats, "textured_mats": tex_mats,
        "normal_mapped": norm_mats, "emissive_mats": emis_mats,
        "images": imgs, "packed": packed, "pack_failed": failed[:4],
        "lights": len(lights), "cameras": len(cams),
        "collections": colls,
        "engine": scn.render.engine,
        "resolution": [scn.render.resolution_x, scn.render.resolution_y],
        "samples": scn.cycles.samples,
        "look": scn.view_settings.look,
    }


_result = build()
print(_result, flush=True)