"""Read the fitted ASH-12 rig so the bullpup reload can be authored against it.

Prints, for the saved working blend: the weapon/arm bone tree, the receiver-local
grip and handguard anchors, and what the accepted M4 empty reload actually
animates. Run:

  blender --background --factory-startup --python-exit-code 1 --python inspect_bullpup_reload.py
"""
import math
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["SK_M4_Infima"]
bpy.context.view_layer.objects.active = rig

rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parents = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}

print("\n=== BONES ===")
for name in sorted(rest):
    h = rest[name].translation
    print("  %-24s parent=%-22s head=(%.4f, %.4f, %.4f)" % (name, parents[name], h.x, h.y, h.z))

WPN = [n for n in rest if n.startswith(("WPN", "weapon", "bolt", "Bolt"))]
print("\n=== WEAPON BONES ===")
for name in sorted(WPN):
    h = rest[name].translation
    print("  %-24s parent=%-22s head=(%.4f, %.4f, %.4f)" % (name, parents[name], h.x, h.y, h.z))


def fcurves(action):
    if hasattr(action, "layers") and action.layers:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for fc in bag.fcurves:
                        yield fc
    else:
        for fc in action.fcurves:
            yield fc


print("\n=== ACTIONS ===")
for action in bpy.data.actions:
    paths = {}
    for fc in fcurves(action):
        paths[fc.data_path] = paths.get(fc.data_path, 0) + 1
    fr = action.frame_range
    mag = {k: v for k, v in paths.items() if "Magazine" in k or "ChargingHandle" in k or "bolt" in k.lower()}
    print("  %-26s frames=%.0f-%.0f channels=%d" % (action.name, fr[0], fr[1], len(paths)))
    for k in sorted(mag):
        print("        %-60s %d curves" % (k, mag[k]))
    for extra in ("WPN_root", "WPN_Trigger"):
        for k in sorted(paths):
            if extra in k:
                print("        %-60s %d curves" % (k, paths[k]))


def sample(action, frame):
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


def report_hand(action, frame, label):
    pose = sample(action, frame)
    root = pose["WPN_root"]
    inv = root.inverted()
    out = ["  %-10s f=%5.1f" % (label, frame)]
    for name in ("hand_l", "hand_r"):
        w = pose[name].translation
        loc = inv @ w
        out.append("    %s world=(%.3f,%.3f,%.3f) recv=(%.3f,%.3f,%.3f)"
                   % (name, w.x, w.y, w.z, loc.x, loc.y, loc.z))
    print("\n".join(out))
    return pose


print("\n=== ACCEPTED M4 EMPTY RELOAD: HANDS ===")
empty = bpy.data.actions["M4_HK416_reload_empty"]
idle = bpy.data.actions["M4_idle"]
for f in (0, 5, 10, 21, 43, 54, 80, 88, 130, 148, 162):
    report_hand(empty, f, "empty")
print("\n=== M4 IDLE: HANDS ===")
for f in (0, 60):
    report_hand(idle, f, "idle")

print("\n=== ASH-12 ANCHORS (receiver frame, rest) ===")
root_rest = rest["WPN_root"]
inv_root = root_rest.inverted()
for name in ("WPN_SOCKET_Magazine", "WPN_ChargingHandle", "WPN_bolt", "WPN_Trigger",
             "WPN_SOCKET_Muzzle", "WPN_SOCKET_Eject", "WPN_RearSight", "WPN_FrontSight"):
    if name in rest:
        loc = inv_root @ rest[name].translation
        print("  %-24s recv=(%.4f, %.4f, %.4f)" % (name, loc.x, loc.y, loc.z))
        print("      root-local axes X=(%.2f,%.2f,%.2f) Y=(%.2f,%.2f,%.2f) Z=(%.2f,%.2f,%.2f)"
              % tuple(list((inv_root @ rest[name]).col[0][:3]) + list((inv_root @ rest[name]).col[1][:3])
                      + list((inv_root @ rest[name]).col[2][:3])))

pose0 = sample(empty, 0)
print("\n=== FRAME 0 RECEIVER FRAME ===")
q = pose0["WPN_root"].to_quaternion()
print("  root world=(%.4f,%.4f,%.4f) quat=(%.4f,%.4f,%.4f,%.4f)"
      % (pose0["WPN_root"].translation.x, pose0["WPN_root"].translation.y, pose0["WPN_root"].translation.z,
         q.w, q.x, q.y, q.z))
print("  root Y axis (muzzle dir)=(%.3f,%.3f,%.3f)" % tuple(q @ Vector((0.0, 1.0, 0.0))))
print("  root X axis=(%.3f,%.3f,%.3f)" % tuple(q @ Vector((1.0, 0.0, 0.0))))
print("  root Z axis=(%.3f,%.3f,%.3f)" % tuple(q @ Vector((0.0, 0.0, 1.0))))

# Where the magazine body sits relative to the well, so a pull-out path can be authored.
gun = bpy.data.objects.get("ASH12_Export")
if gun:
    groups = {g.name: g.index for g in gun.vertex_groups}
    bounds = {}
    for v in gun.data.vertices:
        for g in v.groups:
            for name, idx in groups.items():
                if g.group == idx and name in ("WPN_SOCKET_Magazine", "WPN_ChargingHandle"):
                    b = bounds.setdefault(name, [Vector((1e9,) * 3), Vector((-1e9,) * 3)])
                    b[0] = Vector((min(b[0][i], v.co[i]) for i in range(3)))
                    b[1] = Vector((max(b[1][i], v.co[i]) for i in range(3)))
    print("\n=== BOUND PARTS (own bone frame) ===")
    for name, (lo, hi) in bounds.items():
        print("  %-24s lo=(%.4f,%.4f,%.4f) hi=(%.4f,%.4f,%.4f)" % (name, lo.x, lo.y, lo.z, hi.x, hi.y, hi.z))
    mag = bounds.get("WPN_SOCKET_Magazine")
    handle = bounds.get("WPN_ChargingHandle")
    if mag:
        # The magazine's own bone points down the well; report the receiver-local span.
        m = rest["WPN_SOCKET_Magazine"]
        lo_w = m @ mag[0]
        hi_w = m @ mag[1]
        lo_l = inv_root @ lo_w
        hi_l = inv_root @ hi_w
        print("  magazine body in receiver frame: lo=(%.3f,%.3f,%.3f) hi=(%.3f,%.3f,%.3f)"
              % (lo_l.x, lo_l.y, lo_l.z, hi_l.x, hi_l.y, hi_l.z))
        print("  magazine local extent: %.4f x %.4f x %.4f m"
              % ((mag[1] - mag[0]).x, (mag[1] - mag[0]).y, (mag[1] - mag[0]).z))
    if handle:
        c = (handle[0] + handle[1]) / 2.0
        hw = rest["WPN_ChargingHandle"] @ c
        hl = inv_root @ hw
        print("  charging handle centre receiver-local=(%.3f,%.3f,%.3f)" % (hl.x, hl.y, hl.z))
        print("  handle local extent: %.4f x %.4f x %.4f m"
              % ((handle[1] - handle[0]).x, (handle[1] - handle[0]).y, (handle[1] - handle[0]).z))

print("\nASH12_RELOAD_INSPECT_COMPLETE")
