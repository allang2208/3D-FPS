"""Bind the oden ASH-12 geometry to the accepted Manny arms and author the clips.

Fit frame (armature space, metres): +Y runs toward the muzzle, +Z is up and
+X is the shooter's right. The oden source is authored with +X muzzle, +Z up
and the shooter's right on -Y, so the fit is a +90 degree turn about Z, one
scale and one translation. The translation is anchored on the pistol grip:
the rear face of the grip lands on the accepted M4 grip and the grip heel
lands on the M4 grip heel, which puts the trigger within 6 mm of the M4
trigger and the support hand on the front rail.

Run: blender --background --factory-startup --python-exit-code 1 --python build.py
"""
import json
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))
ARMS = r"D:\FPS3D\FPSGAME\SourceAssets\M4TacticalToss20260910\M4_Hand_MAT_Editable.blend"
SOURCE_ROOT = r"D:\FPS3D\资产\oden先辈"
SOURCE = os.path.join(SOURCE_ROOT, "fbx", "weapon.FBX")

# --- fit -------------------------------------------------------------------
SCALE = 0.0242          # source units -> metres (34.68 units -> 0.839 m)
TARGET = Vector((0.0559, 0.16607, -0.04817))

# Vertices of these components ride their own bone instead of WPN_root.
TRIGGER_COMPONENT = 78
MAGAZINE_MATERIALS = ("10 - Default", "14 - Default")   # mag.tga, xmag.tga

# Source-space markers, mapped through the fit transform.
MARKERS = {
    "WPN_RearSight": (-5.600, 0.0, 4.260),
    "WPN_FrontSight": (1.400, 0.0, 4.260),
    "WPN_SOCKET_Muzzle": (14.600, 0.0, 0.580),
    "WPN_SOCKET_Eject": (4.500, -0.900, 1.300),
    "WPN_Trigger": (0.430, 0.0, -1.600),
}
MAG_SOCKET_SOURCE = (-8.400, 0.0, -3.000)

MATERIAL_MAP = {
    "13 - Default": "M_ASH12_Upper",
    "09 - Default": "M_ASH12_Lower",
    "08 - Default": "M_ASH12_Front",
    "11 - Default": "M_ASH12_Sights",
    "07 - Default": "M_ASH12_Flash_Hider",
    "14 - Default": "M_ASH12_Magazine",
    "10 - Default": "M_ASH12_Magazine_Base",
}
# Held-back for the attachment pass; excluded from the game mesh.
DEFERRED_MATERIALS = ("12 - Default", "15 - Default", "16 - Default")   # stubby, laser, laser glass

CLIPS = {
    "idle": ("M4_idle", 180),
    "aim": ("M4_aim", 2),
    "fire": ("M4_fire", 46),
    "aim_fire": ("M4_aim_fire", 46),
    "reload": ("M4_HK416_reload", 126),
    "reload_empty": ("M4_HK416_reload_empty", 162),
    "equip_charge": ("M4_HK416_equip_charge", 38),
}
# Sockets ride the receiver rigidly; the trigger keeps whatever the clip drives.
PINNED_MARKERS = ("WPN_RearSight", "WPN_FrontSight", "WPN_SOCKET_Muzzle", "WPN_SOCKET_Eject")
# Left-arm offset window per clip, in source frames: (ramp-in start, ramp-out
# start, ramp-in frames, ramp-out frames). The support hand leaves the rail
# around frame 10 in both clips and returns at 104 (reload) / 148 (empty, after
# the bolt-release slap), so the offset tracks those two moves.
RELOAD_GRAB = {"reload": (10, 92, 14, 12), "reload_empty": (10, 132, 14, 16)}
# Beat retiming, measured from the reference clip (2:06-2:10 of the supplied
# video): magazine out early, deliberate insert, then the seat. Fractions are
# of the clip, map source time -> this clip's time so the rhythm matches while
# the clip keeps its authored length (the catalog reload durations stay valid).
# Magazine seat snap. The reference jolts the whole viewmodel at the moment the
# magazine lands; its camera stays steady (background phase correlation over the
# reload measured 0.00-0.01 px), so the snap belongs to the pose, not to a camera
# shake. (first frame, peak pitch degrees, peak metres back, decay frames).
JOLT = {"reload_empty": (118.0, 2.5, 0.008, 5.0)}

# Left-arm path for the bullpup empty reload, authored against the reference
# clip's beats. Waypoints are offsets in the receiver's own frame from the
# magazine well (local +Y is toward the stock, +Z up, +X the shooter's left);
# the support hand is driven onto each waypoint with the existing IK, so the
# reach, the pull, the off-screen fetch and the push all read as authored
# motion instead of the accepted M4 path translated sideways.
WELL_LOCAL = Vector((0.004, 0.181, -0.022))
RELOAD_PATH = {
    "reload_empty": [
        (0.00, (0.00, 0.00, 0.00), 0.0),
        (0.10, (0.02, 0.02, -0.10), 0.4),
        (0.20, (0.00, 0.03, -0.08), 1.0),   # grab the magazine body
        (0.32, (0.01, 0.05, -0.19), 1.0),   # pull it clear of the well
        (0.44, (0.06, 0.09, -0.30), 1.0),   # discard
        (0.58, (0.10, 0.06, -0.34), 1.0),   # fetch the fresh magazine
        (0.72, (0.01, 0.03, -0.11), 1.0),   # bring it to the well mouth
        (0.84, (0.00, 0.02, -0.03), 1.0),   # push in and seat
        (0.94, (0.02, 0.01, -0.08), 0.5),
        (1.00, (0.00, 0.00, 0.00), 0.0),
    ],
}

TIME_WARP = {
    "reload_empty": [(0.00, 0.00), (0.25, 0.12), (0.59, 0.46), (0.91, 0.74), (1.00, 1.00)],
}
# Firing-wrist compensation, degrees. Measured against the accepted M4
# reference the hand-to-grip alignment is already within 5 degrees, so this
# stays at zero; the constant exists for a later hand-pose pass.
WRIST_BEND_DEGREES = 0.0

# The source receiver is not square to its own sights: measured against the
# sight markers its rail leans 3.9 degrees to the right, and the accepted M4
# ships level (measured 0.0). ADS calibrates the sight axis but not the roll,
# so the lean is what the player sees down the sights. Cancelled here about
# the grip contact so the accepted hand fit is untouched.
BODY_ROLL_DEGREES = -4.7
GRIP_PIVOT = Vector((0.056, 0.117, -0.114))
fit_matrix = (Matrix.Translation(GRIP_PIVOT)
              @ Matrix.Rotation(math.radians(BODY_ROLL_DEGREES), 4, Vector((0.0, 1.0, 0.0)))
              @ Matrix.Translation(-GRIP_PIVOT)
              @ Matrix.Translation(TARGET) @ Matrix.Rotation(math.radians(90.0), 4, "Z") @ Matrix.Scale(SCALE, 4))


def to_fit(v):
    return fit_matrix @ Vector(v)


# ---------------------------------------------------------------------------
bpy.ops.wm.open_mainfile(filepath=ARMS)
scene = bpy.context.scene
rig = bpy.data.objects["SK_M4_Infima"]
hands = bpy.data.objects["SK_Manny_Arms_Export"]
scene.render.fps = 60

if not rig.animation_data:
    rig.animation_data_create()
rig.animation_data.action = bpy.data.actions["M4_idle"]
if rig.animation_data.action.slots:
    rig.animation_data.action_slot = rig.animation_data.action.slots[0]
scene.frame_set(0)
bpy.context.view_layer.update()

# The fit only needs the receiver's reference frame; the part bones are about
# to move, so their reference pose is sampled again after that.
root_pose = rig.pose.bones["WPN_root"].matrix.copy()
old_mag_pose = rig.pose.bones["WPN_SOCKET_Magazine"].matrix.translation.copy()
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
parents = {b.name: (b.parent.name if b.parent else None) for b in rig.data.bones}
names = list(rest)


def _descendants(root):
    found = [root]
    growing = True
    while growing:
        growing = False
        for child, parent in parents.items():
            if parent in found and child not in found:
                found.append(child)
                growing = True
    return found


FIRING_HAND = _descendants("hand_r")

# Arms keep their identity; the M4 shells are dropped, the oden gun replaces them.
for obj in list(scene.objects):
    if obj.type == "MESH" and obj is not hands:
        bpy.data.objects.remove(obj, do_unlink=True)

bpy.ops.import_scene.fbx(filepath=SOURCE, use_custom_normals=True)
src = next(o for o in scene.objects if o.type == "MESH" and o is not hands)
me = src.data

print("ASH12_SOURCE", me.name, len(me.vertices), len(me.polygons))

# Relink the texture maps the FBX points at the wrong folder for.
for img in bpy.data.images:
    base_name = os.path.basename(img.filepath.replace("\\", "/"))
    if not base_name or os.path.exists(img.filepath):
        continue
    for sub in ("cdm", "natga"):
        cand = os.path.join(SOURCE_ROOT, sub, base_name)
        if os.path.exists(cand):
            img.filepath = cand
            img.reload()
            break

# Loose parts, so the trigger can leave the receiver.
bm = bmesh.new()
bm.from_mesh(me)
bm.verts.ensure_lookup_table()
seen = set()
groups = []
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
bm.free()
trigger_verts = set(groups[TRIGGER_COMPONENT])
print("ASH12_COMPONENTS", len(groups), "trigger_verts", len(trigger_verts))

mag_slots = {i for i, m in enumerate(me.materials) if m and m.name in MAGAZINE_MATERIALS}

bone_for = {}
for poly in me.polygons:
    bone = "WPN_root"
    if poly.material_index in mag_slots:
        bone = "WPN_SOCKET_Magazine"
    elif all(v in trigger_verts for v in poly.vertices):
        bone = "WPN_Trigger"
    for v in poly.vertices:
        bone_for[v] = bone

# Source geometry that the attachment pass will take over later.
drop = {i for i, m in enumerate(me.materials) if m and m.name in DEFERRED_MATERIALS}
keep_polys = [p.index for p in me.polygons if p.material_index not in drop]

verts = [me.vertices[v].co.copy() for v in range(len(me.vertices))]
uvs = [tuple(x.uv) for x in me.uv_layers.active.data]
corner_normals = [n.vector.copy() for n in me.corner_normals]

# The fit is authored in armature space at the idle pose, so it has to be
# expressed in WPN_root's own frame before it can ride that bone.
xf = root_pose.inverted() @ fit_matrix
markers = {name: (rest["WPN_root"] @ (xf @ Vector(pos))) for name, pos in MARKERS.items()}
markers["WPN_SOCKET_Magazine"] = rest["WPN_root"] @ (xf @ Vector(MAG_SOCKET_SOURCE))
bpy.ops.object.select_all(action="DESELECT")
rig.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="EDIT")
for name, point in markers.items():
    bone = rig.data.edit_bones[name]
    delta = point - bone.head
    bone.head += delta
    bone.tail += delta
bpy.ops.object.mode_set(mode="OBJECT")

rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
local_rest = {n: (rest[parents[n]].inverted() @ rest[n] if parents[n] else rest[n]) for n in names}

# Reference pose for the binding, sampled with the final rest positions in
# place: a bone the clips leave at rest must bind at its new rest, not the old.
scene.frame_set(0)
bpy.context.view_layer.update()
base = {b.name: b.matrix.copy() for b in rig.pose.bones}

# Bind in rest space: the gun is placed in the idle pose, then re-bound rigidly
# to each part bone, so animation drives the receiver, magazine and trigger.
newverts = []
for i, v in enumerate(verts):
    bone = bone_for.get(i, "WPN_root")
    newverts.append(rest[bone] @ base[bone].inverted() @ base["WPN_root"] @ xf @ v)

# Only the vertices the kept faces reference; the deferred parts drop out here.
used = sorted({v for p in keep_polys for v in me.polygons[p].vertices})
remap = {old: new for new, old in enumerate(used)}
newverts = [newverts[i] for i in used]
faces = [[remap[v] for v in me.polygons[p].vertices] for p in keep_polys]
loop_normals = []
for p in keep_polys:
    poly = me.polygons[p]
    for li in range(poly.loop_start, poly.loop_start + poly.loop_total):
        loop_normals.append(corner_normals[li])

mesh = bpy.data.meshes.new("ASH12_Bound")
mesh.from_pydata(newverts, [], faces)
mesh.update()
# Smooth first, then the authored split normals: setting custom normals on
# flat-shaded polygons makes Blender drop them, and the export then loses
# every hard edge (measured: 113k sharp loop pairs in the source, 0 out).
for poly in mesh.polygons:
    poly.use_smooth = True
mesh.normals_split_custom_set(loop_normals)
mesh.update()

uv_layer = mesh.uv_layers.new(name="UVMap")
k = 0
for p in keep_polys:
    for li in range(me.polygons[p].loop_start, me.polygons[p].loop_start + me.polygons[p].loop_total):
        uv_layer.data[k].uv = uvs[li]
        k += 1

# Materials, renamed for the runtime contracts ("Magazine", "Flash_Hider").
slot_remap = {}
for new_index, p in enumerate(keep_polys):
    src_slot = me.polygons[p].material_index
    if src_slot not in slot_remap:
        slot_remap[src_slot] = None
used_slots = sorted(slot_remap)
slot_index = {}
for out_index, src_slot in enumerate(used_slots):
    material = me.materials[src_slot].copy()
    material.name = MATERIAL_MAP.get(me.materials[src_slot].name, me.materials[src_slot].name)
    material.use_fake_user = True
    mesh.materials.append(material)
    slot_index[src_slot] = out_index
for poly, src_poly in zip(mesh.polygons, keep_polys):
    poly.material_index = slot_index[me.polygons[src_poly].material_index]

gun = bpy.data.objects.new("ASH12_Export", mesh)
scene.collection.objects.link(gun)
gun.parent = rig
gun.matrix_parent_inverse = Matrix.Identity(4)
gun.matrix_basis = Matrix.Identity(4)
for bone in sorted(set(bone_for.values())):
    members = [remap[i] for i, b in bone_for.items() if b == bone and i in remap]
    gun.vertex_groups.new(name=bone).add(members, 1.0, "REPLACE")
gun.modifiers.new("ASH12_Rig", "ARMATURE").object = rig

bpy.data.objects.remove(src, do_unlink=True)

# --- clips ------------------------------------------------------------------
delta_local = None
root_quat = base["WPN_root"].to_quaternion()


def set_action(action):
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]


def sample(action, frame):
    set_action(action)
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def wrist_bend(pose, degrees):
    """Rotate the firing hand about its wrist by a fixed angle.

    Every accepted clip closes the firing hand on a grip raked back 24.8 degrees;
    this receiver's grip is vertical, so the wrist carries the difference. The
    whole hand subtree is transformed together, which keeps the finger and thumb
    relationships intact.
    """
    if abs(degrees) < 0.01:
        return
    pivot = pose["hand_r"].translation.copy()
    axis = (pose["WPN_root"].to_quaternion() @ Vector((1.0, 0.0, 0.0))).normalized()
    rigid = Matrix.Translation(pivot) @ Quaternion(axis, math.radians(degrees)).to_matrix().to_4x4() @ Matrix.Translation(-pivot)
    for name in FIRING_HAND:
        pose[name] = rigid @ pose[name]


def path_hand_target(pose, kind, frame, length):
    """Interpolated support-hand target from the authored path, or None."""
    keys = RELOAD_PATH.get(kind)
    if not keys:
        return None
    t = max(0.0, min(1.0, frame / length))
    for (t0, o0, w0), (t1, o1, w1) in zip(keys, keys[1:]):
        if t <= t1:
            span = max(1e-6, t1 - t0)
            a = smooth((t - t0) / span)
            off = Vector(o0).lerp(Vector(o1), a)
            weight = w0 + (w1 - w0) * a
            return pose["WPN_root"] @ (WELL_LOCAL + off), weight
    return None


def viewmodel_jolt(pose, kind, frame):
    """Snap the whole viewmodel for the magazine seat, as the reference does."""
    spec = JOLT.get(kind)
    if not spec:
        return
    start, peak_deg, peak_m, decay = spec
    if frame < start:
        return
    k = math.exp(-(frame - start) / decay)
    if k < 0.02:
        return
    q = pose["WPN_root"].to_quaternion()
    pivot = pose["WPN_root"].translation.copy()
    axis = (q @ Vector((1.0, 0.0, 0.0))).normalized()
    rigid = (Matrix.Translation(q @ Vector((0.0, peak_m * k, 0.0)))
             @ Matrix.Translation(pivot)
             @ Quaternion(axis, math.radians(peak_deg * k)).to_matrix().to_4x4()
             @ Matrix.Translation(-pivot))
    for name in names:
        pose[name] = rigid @ pose[name]


def warp_time(kind, frame, length):
    """Map this clip's time onto the source clip's time for the beat table."""
    table = TIME_WARP.get(kind)
    if not table:
        return frame
    t = max(0.0, min(1.0, frame / length))
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if t <= x1:
            span = max(1e-6, x1 - x0)
            return (y0 + (y1 - y0) * (t - x0) / span) * length
    return frame


def shift_arm(pose, side, shift):
    upper, lower, hand = "upperarm_" + side, "lowerarm_" + side, "hand_" + side
    a, b, c = [pose[n].translation.copy() for n in (upper, lower, hand)]
    goal = c + shift
    l1 = (b - a).length
    l2 = (c - b).length
    axis = (goal - a).normalized()
    d = (goal - a).length
    if d >= l1 + l2:
        a += axis * (d - l1 - l2 + 0.0001)
        d = (goal - a).length
    pole = b - a
    pole -= axis * pole.dot(axis)
    pole.normalize()
    along = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    elbow = a + axis * along + pole * math.sqrt(max(0.0, l1 * l1 - along * along))
    pose[upper] = Matrix.LocRotScale(a, (b - pose[upper].translation).rotation_difference(elbow - a) @ pose[upper].to_quaternion(), pose[upper].to_scale())
    pose[lower] = Matrix.LocRotScale(elbow, (c - b).rotation_difference(goal - elbow) @ pose[lower].to_quaternion(), pose[lower].to_scale())
    for name in names:
        if name == hand or (name.endswith("_" + side) and name.startswith(("thumb", "index", "middle", "ring", "pinky"))):
            pose[name].translation += shift
        elif name.endswith("_" + side) and name.startswith(("upperarm_twist", "lowerarm_twist")):
            pose[name] = pose[parents[name]] @ local_rest[name]


def mag_delta_local():
    """Left-hand offset that carries the accepted M4 reach onto this magazine.

    The accepted clips keep a fixed support-hand-to-well relationship, so the
    hand offset is exactly how far the well moved in the receiver's own frame.
    Re-sampling the reference pose after the bones moved makes
    ``base[socket] - to_fit(socket)`` collapse to zero, so the old offset has to
    be read from the pre-move sample instead.
    """
    old_local = root_pose.inverted() @ old_mag_pose
    new_local = rest["WPN_root"].inverted() @ rest["WPN_SOCKET_Magazine"].translation
    return new_local - old_local


report = {}
for kind, (source_name, end) in CLIPS.items():
    source = bpy.data.actions[source_name]
    grab = RELOAD_GRAB.get(kind)
    if grab:
        delta_local = mag_delta_local()
    poses = []
    for step in range(end * 2 + 1):
        frame = step / 2.0
        source_frame = warp_time(kind, frame, end)
        pose = sample(source, source_frame)
        wrist_bend(pose, WRIST_BEND_DEGREES)
        path = path_hand_target(pose, kind, frame, end)
        if path:
            target, weight = path
            if weight > 0.0:
                shift_arm(pose, "l", (target - pose["hand_l"].translation) * weight)
        elif grab:
            weight = smooth((source_frame - grab[0]) / float(grab[2])) * (1.0 - smooth((source_frame - grab[1]) / float(grab[3])))
            if weight > 0.0:
                # The offset lives in the receiver's frame, so it has to follow
                # this frame's receiver orientation, not the idle one.
                shift_arm(pose, "l", pose["WPN_root"].to_quaternion() @ (delta_local * weight))
        viewmodel_jolt(pose, kind, frame)
        for name in PINNED_MARKERS:
            pose[name] = pose["WPN_root"] @ rest["WPN_root"].inverted() @ rest[name]
        poses.append(pose)

    action = bpy.data.actions.new("ASH12_" + kind)
    action.use_fake_user = True
    rig.animation_data.action = action
    previous = {}
    for step, pose in enumerate(poses):
        for name in names:
            local = local_rest[name].inverted() @ (pose[parents[name]].inverted() @ pose[name] if parents[name] else pose[name])
            loc, rot, scale = local.decompose()
            if name in previous and previous[name].dot(rot) < 0:
                rot.negate()
            previous[name] = rot.copy()
            bone = rig.pose.bones[name]
            bone.rotation_mode = "QUATERNION"
            bone.location = loc
            bone.rotation_quaternion = rot
            bone.scale = scale
            for prop in ("location", "rotation_quaternion", "scale"):
                bone.keyframe_insert(prop, frame=step / 2.0)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for fcurve in bag.fcurves:
                    for key in fcurve.keyframe_points:
                        key.interpolation = "LINEAR"
    scene.render.fps = 60
    scene.frame_start = 0
    scene.frame_end = end
    bpy.ops.object.select_all(action="DESELECT")
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(O, "A_ASH12_%s.fbx" % kind),
        use_selection=True, object_types={"ARMATURE"}, axis_forward="-Y", axis_up="Z",
        add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=False,
        bake_anim_use_nla_strips=False, bake_anim_force_startend_keying=True,
        bake_anim_step=0.5, bake_anim_simplify_factor=0,
    )
    report[kind] = {"source": source_name, "duration": end / 60.0, "frames": end, "fps": 60,
                    "sample_rate": 120, "left_arm_shift": bool(grab)}

set_action(bpy.data.actions["ASH12_idle"])
scene.frame_set(0)
scene.frame_end = 180

bpy.ops.object.select_all(action="DESELECT")
for obj in (rig, hands, gun):
    obj.select_set(True)
bpy.context.view_layer.objects.active = rig
bpy.ops.export_scene.fbx(filepath=os.path.join(O, "SK_ASH12_Manny.fbx"), use_selection=True,
                         object_types={"MESH", "ARMATURE"}, axis_forward="-Y", axis_up="Z", add_leaf_bones=False, bake_anim=False)

for obj in scene.objects:
    obj.hide_render = obj.name not in ("SK_M4_Infima", "SK_Manny_Arms_Export", "ASH12_Export")

bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))

with open(os.path.join(O, "build.json"), "w", encoding="utf-8") as fh:
    json.dump({
        "fit": {"scale": SCALE, "translation": list(TARGET), "rotation_z_degrees": 90.0},
        "markers_source": MARKERS,
        "magazine_socket_source": MAG_SOCKET_SOURCE,
        "markers_fitted": {k: [round(float(c), 6) for c in v] for k, v in markers.items()},
        "materials": {m.name: m.name for m in mesh.materials},
        "vertices": len(newverts), "polygons": len(faces),
        "parts": {"trigger_component": TRIGGER_COMPONENT, "magazine_materials": list(MAGAZINE_MATERIALS)},
        "deferred_parts": list(DEFERRED_MATERIALS),
        "clips": report,
        "hands_source": "M4TacticalToss20260910/SK_Manny_Arms_Export",
    }, fh, ensure_ascii=False, indent=2)

print("ASH12_BUILD_COMPLETE vertices=%d polygons=%d" % (len(newverts), len(faces)))
