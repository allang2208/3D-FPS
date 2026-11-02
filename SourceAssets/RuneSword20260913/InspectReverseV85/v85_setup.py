"""Open the accepted WristLocked V4 idle, attach the V7 surface and measure the grip contacts (V85, from V84)."""
import math
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector

from visible_bare import attach as attach_bare
import v85_hand as Hd

HERE = Path(__file__).parent
WPN = 'WPN_root'
VIEW = Vector((0.0, 1.0, 0.0))
UP = Vector((0.0, 0.0, 1.0))
SPIN_AXIS_RAW = Vector((0.90, 1.00, 0.06))  # V54-V82 safe plane (tip stays out of the lens)


class Ctx:
    pass


def nearest_pair(arms, posed_arms, ids, points):
    best = None
    for i in ids:
        a = arms.matrix_world @ posed_arms.vertices[i].co
        for p in points:
            d = (a - p).length
            if best is None or d < best[0]:
                best = (d, i, a.copy(), p.copy())
    return best


def load(variant):
    c = Ctx()
    src = HERE.parents[1] / 'RuneSwordWristLocked20260920' / variant / 'Sword_Idle_WristLockedV4.blend'
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.open_mainfile(filepath=str(src))
    c.source = src
    c.scene = bpy.context.scene
    c.rig = rig = bpy.data.objects['SK_RuneSword_Rig']
    if any(abs(rig.matrix_world[i][j] - (1.0 if i == j else 0.0)) > 1e-6 for i in range(4) for j in range(4)):
        raise RuntimeError('Rig object transform is not identity; skin math assumes rig space')
    c.sword = sword = bpy.data.objects['RuneSword_Blade']
    c.rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
    c.parent = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
    c.local_rest = {n: (c.rest[c.parent[n]].inverted() @ c.rest[n]) if c.parent[n] else c.rest[n] for n in c.rest}
    c.names = list(c.rest)
    c.source_action = rig.animation_data.action
    rig.animation_data.action_slot = c.source_action.slots[0]
    c.scene.frame_set(int(c.source_action.frame_range[0]))
    bpy.context.view_layer.update()
    c.idle = {b.name: b.matrix.copy() for b in rig.pose.bones}
    c.idle_scale = {n: c.idle[n].to_scale() for n in c.names}
    idle, rest = c.idle, c.rest
    # Idle-local translation/scale of every bone (keys keep these) and of the right fingers.
    c.idle_local = {}
    for n in c.names:
        pw = idle[c.parent[n]] if c.parent[n] else Matrix.Identity(4)
        c.idle_local[n] = (c.local_rest[n].inverted() @ (pw.inverted() @ idle[n])).decompose()
    c.finger_r = Hd.finger_bones('r', c.parent)
    c.finger_l = Hd.finger_bones('l', c.parent)
    c.finger_idle_r = {n: (c.idle_local[n][0], c.idle_local[n][2]) for n in c.finger_r}

    # Blade axis, tip and pommel from the posed sword.
    dg = bpy.context.evaluated_depsgraph_get()
    m = sword.evaluated_get(dg).to_mesh()
    pts = [sword.matrix_world @ v.co for v in m.vertices]
    sword.evaluated_get(dg).to_mesh_clear()
    c.blade_axis = (idle[WPN].to_3x3().normalized() @ Vector((0.0, 0.0, 1.0))).normalized()
    centre = sum(pts, Vector()) / len(pts)
    tip = max(pts, key=lambda p: (p - centre).dot(c.blade_axis))
    pommel = min(pts, key=lambda p: (p - centre).dot(c.blade_axis))
    c.mesh_bind = idle[WPN] @ rest[WPN].inverted()
    c.tip_bind = c.mesh_bind.inverted() @ tip
    c.pommel_bind = c.mesh_bind.inverted() @ pommel

    legacy = bpy.data.objects.get('SK_Manny_Arms_Export')
    if legacy:
        legacy.hide_render = True
        legacy.hide_set(True)
    c.arms = arms = attach_bare(rig)
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    pa = arms.evaluated_get(dg).to_mesh()
    ps = sword.evaluated_get(dg).to_mesh()
    spts = [sword.matrix_world @ v.co for v in ps.vertices]
    wl = idle[WPN].inverted()
    upper_hilt = [p for p in spts if -0.060 < (wl @ p).z < -0.032]
    hilt = [p for p in spts if -0.130 < (wl @ p).z < -0.032]

    def group_ids(name, w=0.35):
        gi = arms.vertex_groups[name].index
        return [v.index for v in arms.data.vertices if any(g.group == gi and g.weight > w for g in v.groups)]

    web = nearest_pair(arms, pa, group_ids('thumb_01_r'), upper_hilt)
    near = sorted(upper_hilt, key=lambda p: (p - web[3]).length)[:96]
    index = nearest_pair(arms, pa, group_ids('index_01_r'), near)
    hook = nearest_pair(arms, pa, group_ids('middle_02_r'), hilt)
    arms.evaluated_get(dg).to_mesh_clear()
    sword.evaluated_get(dg).to_mesh_clear()
    if web is None or index is None or hook is None:
        raise RuntimeError('V7 grip contacts could not be measured')
    c.contact_sword = web[3]
    c.contact_hand_local = idle['hand_r'].inverted() @ c.contact_sword
    c.contact_bone_local = idle[WPN].inverted() @ c.contact_sword
    c.grip_r = idle[WPN].inverted() @ idle['hand_r']
    c.grip_l = idle[WPN].inverted() @ idle['hand_l']
    # Each contact: skin vertex, hilt station z, skin-to-axis distance and direction in its dominant bone.
    c.contacts = {}
    groups = {g.index: g.name for g in arms.vertex_groups}
    for key, row in (('web', web), ('index', index), ('hook', hook)):
        vid, skin = row[1], row[2]
        sl = wl @ skin
        foot = idle[WPN] @ Vector((0.0, 0.0, sl.z))
        dom = max(arms.data.vertices[vid].groups, key=lambda g: g.weight)
        bone = groups[dom.group]
        c.contacts[key] = {'vid': vid, 'z': sl.z, 'd': math.hypot(sl.x, sl.y), 'bone': bone,
                           'dir': idle[bone].to_quaternion().inverted() @ (foot - skin).normalized(),
                           'gap_idle_m': row[0]}
    c.contact_skin = Hd.Skin(arms, rest, [c.contacts[k]['vid'] for k in ('web', 'index', 'hook')])
    hand_bones = {'hand_r'} | set(c.finger_r)
    fore_bones = {'lowerarm_r', 'lowerarm_twist_01_r', 'lowerarm_twist_02_r'}
    gidx = {g.index: g.name for g in arms.vertex_groups}
    hand_ids, fore_ids = [], []
    for v in arms.data.vertices:
        w = {gidx[g.group]: g.weight for g in v.groups}
        if sum(w.get(b, 0.0) for b in hand_bones) > 0.3:
            hand_ids.append(v.index)
        elif sum(w.get(b, 0.0) for b in fore_bones) > 0.3:
            fore_ids.append(v.index)
    c.hand_skin = Hd.Skin(arms, rest, hand_ids)
    c.fore_skin = Hd.Skin(arms, rest, fore_ids)
    c.field = Hd.SwordField(sword, rest[WPN])

    # Counter-clockwise screen turn (V82 direction): the tip leaves blade-up toward the left.
    axis = SPIN_AXIS_RAW.normalized()
    probe = Quaternion(axis, math.radians(8.0)) @ (tip - c.contact_sword)
    if probe.x > (tip - c.contact_sword).x:
        axis = -axis
    c.spin_axis = axis
    flat = c.blade_axis - axis * c.blade_axis.dot(axis)
    c.flatten_q = c.blade_axis.rotation_difference(flat.normalized())
    fwd = VIEW - axis * VIEW.dot(axis)
    c.fwd_dir = fwd.normalized()
    c.right_dir = Vector((1.0, 0.0, 0.0))
    # Roll about the blade that lays the 36 cm guard bar inside the spin plane (its component along the spin
    # axis is constant through the turn, so one roll keeps the swept guard a thin disc beside the forearm).
    base = c.flatten_q @ idle[WPN].to_quaternion()
    c.roll_inplane_deg = min(
        (round(abs((base @ Quaternion((0.0, 0.0, 1.0), math.radians(d)) @ Vector((1.0, 0.0, 0.0))).dot(axis)), 3),
         abs(d), d) for d in [x * 0.5 for x in range(-180, 181)])[2]
    return c
