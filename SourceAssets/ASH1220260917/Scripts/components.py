"""List connected components of the oden mesh so mechanical parts can be named,
and export the colour maps to PNG for review.

Run: blender --background --factory-startup --python-exit-code 1 --python components.py
"""
import bpy
import bmesh
import json
import os

ROOT = r"D:\FPS3D\资产\oden先辈"
SOURCE = os.path.join(ROOT, "fbx", "weapon.FBX")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "Reference"))

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=SOURCE, use_custom_normals=True)


def relink():
    for img in bpy.data.images:
        name = os.path.basename(img.filepath.replace("\\", "/"))
        if not name or os.path.exists(img.filepath):
            continue
        for sub in ("cdm", "natga"):
            cand = os.path.join(ROOT, sub, name)
            if os.path.exists(cand):
                img.filepath = cand
                img.reload()
                break


relink()

obj = next(o for o in bpy.context.scene.objects if o.type == "MESH")
me = obj.data
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()

seen = set()
groups = []
mats = [m.name if m else "-" for m in me.materials]
for vert in bm.verts:
    if vert.index in seen:
        continue
    stack = [vert]
    seen.add(vert.index)
    members = []
    while stack:
        v = stack.pop()
        members.append(v.index)
        for edge in v.link_edges:
            other = edge.other_vert(v)
            if other.index not in seen:
                seen.add(other.index)
                stack.append(other)
    groups.append(members)

slot_verts = {}
for p in me.polygons:
    for v in p.vertices:
        slot_verts.setdefault(v, {}).setdefault(p.material_index, 0)
        slot_verts[v][p.material_index] += 1

rows = []
for gi, members in enumerate(groups):
    co = [me.vertices[i].co for i in members]
    lo = [round(min(c[i] for c in co), 3) for i in range(3)]
    hi = [round(max(c[i] for c in co), 3) for i in range(3)]
    tally = {}
    for i in members:
        for s, n in slot_verts.get(i, {}).items():
            tally[mats[s]] = tally.get(mats[s], 0) + n
    dominant = max(tally.items(), key=lambda kv: kv[1])[0] if tally else "-"
    rows.append({"id": gi, "verts": len(members), "bbox_min": lo, "bbox_max": hi,
                 "material": dominant, "all_materials": sorted(tally)})

rows.sort(key=lambda r: -r["verts"])
with open(os.path.join(OUT, "components.json"), "w", encoding="utf-8") as fh:
    json.dump(rows, fh, ensure_ascii=False, indent=1)

print("ASH12_COMPONENTS_BEGIN")
for r in rows[:60]:
    print("  %-3d n=%-6d mat=%-20s min=%s max=%s" % (r["id"], r["verts"], r["material"], r["bbox_min"], r["bbox_max"]))
print("ASH12_COMPONENTS_END total=%d" % len(rows))

# Colour maps out as PNG for review.
outdir = os.path.join(OUT, "textures")
os.makedirs(outdir, exist_ok=True)
scene = bpy.context.scene
scene.render.image_settings.file_format = "PNG"
seen_files = set()
for img in bpy.data.images:
    base = os.path.basename(img.filepath.replace("\\", "/"))
    if not base.lower().endswith(".tga") or base in seen_files:
        continue
    seen_files.add(base)
    img.filepath = os.path.join(ROOT, "cdm", base)
    img.reload()
    img.scale(min(img.size[0], 1024), min(img.size[1], 1024))
    img.filepath_raw = os.path.join(outdir, base.replace(".tga", ".png"))
    img.file_format = "PNG"
    img.save()
    print("ASH12_TEX", base, img.size[0], img.size[1])
