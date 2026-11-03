"""Author-time contact readout: skin vs hatchet surface for selected preview poses (no rendering).

blender -b --factory-startup --python check_contact.py -- <poses.json> <out.json> [name_prefix_filter]
For each pose: the right-hand skin (V7 FrostArms editable rig, same bind as the in-game arms) is evaluated, moved into
the hatchet's local frame and compared with SM_TacticalHatchet's real surface: how many skin vertices lie inside the
hatchet and how deep, and the nearest outside gap (cm).  Only vertices within 14 cm of the grip centre count.
"""
import bpy, bmesh, json, math, sys
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

ROOT = Path(r"D:\FPS3D\FPSGAME\SourceAssets")
argv = sys.argv[sys.argv.index('--') + 1:]
POSES = json.loads(Path(argv[0]).read_text('utf-8'))
OUT = Path(argv[1])
ONLY = argv[2].split(',') if len(argv) > 2 else None
ARMS = ROOT / 'ModularOutfit20260925' / 'BarePalmV7' / 'Editable' / 'FrostArms_BareArmsV7.blend'
DUMP = json.loads((ROOT / 'Kukri20261020' / 'Work' / 'ue_sword_dump.json').read_text('utf-8'))
HATCHET = ROOT / 'OneHandAxe20261101' / 'TacticalHatchet_Editable.blend'
C = Matrix.Diagonal(Vector((1, -1, 1)))


def canonical(v, unit_scale=False):
    p = Vector(v[0:3]); q = Quaternion(v[3:7]); s = Vector(v[7:10])
    r = (C @ q.to_matrix() @ C).to_quaternion()
    return Matrix.LocRotScale(C @ p * .01, r, Vector((1, 1, 1)) if unit_scale else s)


bpy.ops.wm.open_mainfile(filepath=str(ARMS))
scene = bpy.context.scene
rig = next(o for o in scene.objects if o.type == 'ARMATURE')
skin = next(o for o in scene.objects if o.type == 'MESH')
rig.animation_data_clear()
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {b.name: (b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else b.matrix_local.copy() for b in rig.data.bones}
reference = {n: canonical(DUMP['ref_world'][n]) for n in rest}
correction = {n: reference[n].inverted() @ rest[n] for n in rest}
with bpy.data.libraries.load(str(HATCHET)) as (src, dst):
    dst.objects = ['SM_TacticalHatchet']
axe = dst.objects[0]
scene.collection.objects.link(axe)
bm = bmesh.new()
bm.from_mesh(axe.data)
bvh = BVHTree.FromBMesh(bm)          # hatchet local space (m), origin at the grip centre
DIRS = [Vector(d).normalized() for d in ((1, .13, .07), (-.11, 1, .17), (.09, -.15, -1))]


def is_inside(p):
    """Majority of three crossing-parity rays (the source mesh's face winding is not reliable enough for a normal test)."""
    votes = 0
    for d in DIRS:
        crossings, o = 0, p.copy()
        for _ in range(64):
            loc, _, _, _ = bvh.ray_cast(o, d, 1.0)
            if loc is None:
                break
            crossings += 1
            o = loc + d * 1e-5
        votes += crossings % 2
    return votes >= 2


result = {}
for name, pose in POSES['poses'].items():
    if ONLY and not any(name.endswith(s) for s in ONLY):
        continue
    world = {n: canonical(pose['bones'][n]) @ correction[n] for n in rest if n in pose['bones']}
    for bone in rig.pose.bones:
        if bone.name not in world:
            continue
        parent = world[bone.parent.name] if bone.parent and bone.parent.name in world else Matrix.Identity(4)
        bone.matrix_basis = local_rest[bone.name].inverted() @ parent.inverted() @ world[bone.name]
    rig.matrix_world = Matrix.Identity(4)
    bpy.context.view_layer.update()
    to_axe = canonical(pose['kukri'], unit_scale=True).inverted() @ skin.matrix_world
    ev = skin.evaluated_get(bpy.context.evaluated_depsgraph_get())
    me = ev.to_mesh()
    inside, depth, gap, groups, radial = 0, 0.0, 1e9, {}, [0.0, 0.0, 0]
    for v in me.vertices:
        p = to_axe @ v.co
        if p.length > 0.14:
            continue
        hit = bvh.find_nearest(p)
        if hit[0] is None:
            continue
        dist = hit[3]
        if dist < 0.03 and is_inside(p):
            inside += 1
            depth = max(depth, dist)
            radial[0] += p.x; radial[1] += p.y; radial[2] += 1
            src = skin.data.vertices[v.index]
            if src.groups:
                g = max(src.groups, key=lambda e: e.weight)
                name_g = skin.vertex_groups[g.group].name
                groups[name_g] = max(groups.get(name_g, 0.0), round(dist * 100, 2))
        else:
            gap = min(gap, dist)
    ev.to_mesh_clear()
    # mean position of the inside vertices across the handle (hatchet frame, Blender axes: x edge, y = -UE y; cm)
    side = [round(radial[0] / radial[2] * 100, 2), round(-radial[1] / radial[2] * 100, 2)] if radial[2] else None
    result[name] = dict(inside=inside, depth_cm=round(depth * 100, 2), gap_cm=round(gap * 100, 2) if gap < 1e8 else None,
                        groups=groups, side_ue_xy_cm=side)
    print('HATCHET_CONTACT %s inside %d depth %.2f cm gap %s cm side(UE x,y) %s groups %s' % (
        name, inside, depth * 100, result[name]['gap_cm'], side, json.dumps(groups)), flush=True)
OUT.write_text(json.dumps(result, indent=1), encoding='utf-8')
