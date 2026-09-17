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
# Receiver-front right-hand tab: the charging handle, bound so the empty
# reload can work the bolt instead of leaving it frozen in the receiver.
CHARGING_HANDLE_SOURCE_BBOX = ((2.817, -1.198, 1.163), (3.708, -0.898, 2.749))
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
# Left-arm offset window for the tactical reload, in source frames: (ramp-in
# start, ramp-out start, ramp-in frames, ramp-out frames). Only the tactical
# reload still plays the accepted M4 support-hand move; the empty reload is
# authored from the reference below and does not use it.
RELOAD_GRAB = {"reload": (10, 92, 14, 12)}

# --- bullpup empty reload (reference 2:06-2:10, 2026-09-17) ------------------
# The reference rolls the receiver about its own axis toward the shooter's left,
# keeps the support hand clamped on the handguard and gives the whole magazine
# job to the firing hand: grip -> well -> insert -> charging handle -> grip. The
# accepted M4 clips do the opposite (upright gun, support hand works the
# magazine), so none of the mechanical layers below can be inherited.
#
# One clock. The runtime fires this reload's cues at clip frames 21 (magazine
# out), 54 (insert), 80 (seat) and 130 (bolt release) -- the accepted M4 frames
# on a 162-frame clip. Retiming the clip (as an earlier pass did) pulls the pose
# off those cues, so every beat below is authored on the M4's own clock and the
# clip keeps its length.
BULLPUP_CLIPS = ("reload_empty",)

# Receiver frame: +X the shooter's left, +Y toward the stock, +Z up. It is the
# local frame of WPN_root, so anything authored here rides the roll for free.
# Magazine travel measured from its socket, receiver-local metres.
MAG_PATH = [
    (0.0, 0.000, 0.000, 0.000),
    (21.0, 0.000, 0.000, 0.000),      # cue: magazine out
    (30.0, 0.004, 0.010, -0.090),
    (38.0, 0.013, 0.026, -0.190),
    (46.0, 0.022, 0.042, -0.250),     # clear of the well, dropping out of frame
    (54.0, 0.008, 0.024, -0.120),     # cue: the fresh magazine meets the well mouth
    (62.0, 0.004, 0.014, -0.070),
    (72.0, 0.001, 0.005, -0.026),
    (80.0, 0.000, 0.000, 0.000),      # cue: seated
    (162.0, 0.000, 0.000, 0.000),
]
# Firing hand: inside the carry window it is locked to the magazine, outside it
# follows the grip / charging handle anchors sampled off the accepted hold.
HAND_CARRY = (21.0, 80.0)
MAG_GRIP = Vector((0.004, -0.004, -0.105))     # where the hand takes the magazine
# Receiver performance authored from the reference: the receiver rolls about its
# own axis toward the shooter's left while the magazine is worked, so the well
# and the charging handle both turn toward the firing hand. (frame, pitch, yaw,
# roll, back, down) in degrees and metres.
RECEIVER_CURVE = [
    (0.0, 0.0, 0.0, 0.0, 0.000, 0.000),
    (14.0, 1.0, 0.5, 16.0, 0.003, 0.002),
    (21.0, 2.0, 1.0, 38.0, 0.007, 0.004),
    (40.0, 3.5, 2.0, 60.0, 0.011, 0.006),
    (80.0, 4.0, 2.0, 58.0, 0.011, 0.006),
    (110.0, 3.0, 1.5, 44.0, 0.009, 0.005),
    (130.0, 2.0, 1.0, 26.0, 0.006, 0.003),
    (150.0, 0.8, 0.4, 8.0, 0.002, 0.001),
    (162.0, 0.0, 0.0, 0.0, 0.000, 0.000),
]
# Charging handle: met by the firing hand, pulled straight back along the
# receiver, then let fly. (frame, metres).
HANDLE_PULL = [(0.0, 0.0), (114.0, 0.0), (122.0, 0.055), (128.0, 0.058), (132.0, 0.058), (135.0, 0.0), (162.0, 0.0)]
# Bolt: held back by the bolt catch for the whole empty reload, then released
# with the handle and driven home. (frame, metres back from rest).
# Magazine seat snap at the seat cue. The reference jolts the whole viewmodel at
# the moment the magazine lands; its camera stays steady (background phase
# correlation over the reload measured 0.00-0.01 px), so the snap belongs to the
# pose, not to a camera shake. (first frame, peak pitch degrees, peak metres
# back, decay frames).
JOLT = {"reload_empty": (80.0, 2.5, 0.008, 5.0)}
BOLT_RELEASE = 130.0
# How the weapon roll is split between forearm pronation and the wrist. All of
# it on the wrist alone reads as a broken joint; none of it leaves the gun
# turning inside a locked hand.
TWIST_SHARE = 0.55
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
WEAPON_BONES = [b for b in _descendants("WPN_root") if b != "WPN_root"] + ["WPN_root"]

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

CHARGING_HANDLE_SOURCE_CENTRE = tuple((a + b) / 2.0 for a, b in zip(*CHARGING_HANDLE_SOURCE_BBOX))
_hb0, _hb1 = CHARGING_HANDLE_SOURCE_BBOX
def in_handle(index):
    co = me.vertices[index].co
    return all(_hb0[i] <= co[i] <= _hb1[i] for i in range(3))

bone_for = {}
for poly in me.polygons:
    bone = "WPN_root"
    if poly.material_index in mag_slots:
        bone = "WPN_SOCKET_Magazine"
    elif all(v in trigger_verts for v in poly.vertices):
        bone = "WPN_Trigger"
    elif all(in_handle(v) for v in poly.vertices):
        bone = "WPN_ChargingHandle"
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
# Where the support hand has to meet the charging handle, in the receiver's frame.
HANDLE_LOCAL = (xf @ Vector(CHARGING_HANDLE_SOURCE_CENTRE)) - Vector(WELL_LOCAL) + Vector((-0.018, 0.010, -0.012))
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


def recv(name):
    """Anchor in the receiver's own frame (the local frame of WPN_root)."""
    return rest["WPN_root"].inverted() @ rest[name].translation


# Read off the fitted rig, so the authored beats cannot drift from the gun they
# were measured on.
WELL_LOCAL = recv("WPN_SOCKET_Magazine")
HANDLE_LOCAL = recv("WPN_ChargingHandle")
BOLT_LOCAL = recv("WPN_bolt")
print("ASH12_ANCHORS well=%s handle=%s bolt=%s"
      % (tuple(round(c, 4) for c in WELL_LOCAL), tuple(round(c, 4) for c in HANDLE_LOCAL),
         tuple(round(c, 4) for c in BOLT_LOCAL)))

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


def curve(keys, frame):
    """Smoothstep through (frame, v0, v1, ...) keys."""
    if frame <= keys[0][0]:
        return tuple(keys[0][1:])
    if frame >= keys[-1][0]:
        return tuple(keys[-1][1:])
    for k0, k1 in zip(keys, keys[1:]):
        if frame <= k1[0]:
            span = max(1e-6, k1[0] - k0[0])
            a = smooth((frame - k0[0]) / span)
            return tuple(x0 + (x1 - x0) * a for x0, x1 in zip(k0[1:], k1[1:]))
    return tuple(keys[-1][1:])


def hand_subtree(side):
    return _descendants("hand_" + side)


def prepare_bullpup(source):
    """Anchors for the bullpup reload, read off the accepted hold on this gun.

    Both hands are frozen as receiver-local matrices: the position travels along
    the authored path, the orientation stays the natural hold it has at frame 0.
    That keeps the M4 clip's own hand rotation out of the result and lets the
    roll carry the hands without extra maths.
    """
    pose = sample(source, 0.0)
    inv = pose["WPN_root"].inverted()
    grip = (inv @ pose["hand_r"]).copy()
    left = (inv @ pose["hand_l"]).copy()
    bolt_back = (inv @ pose["WPN_bolt"].translation) - BOLT_LOCAL
    grab = WELL_LOCAL + MAG_GRIP
    # The two hands of the charge phase share one pull table, so the handle and
    # the hand holding it cannot drift apart.
    pull = [(f, tuple(HANDLE_LOCAL + Vector((0.0, m, 0.0)))) for f, m in HANDLE_PULL if 100.0 < f < 145.0]
    mid = grip.translation.lerp(HANDLE_LOCAL, 0.55) + Vector((0.012, 0.010, -0.020))
    hand_keys = ([(0.0, tuple(grip.translation)), (14.0, tuple(grip.translation)), (21.0, tuple(grab)),
                  (80.0, tuple(grab)), (96.0, tuple(mid))]
                 + pull
                 + [(150.0, tuple(grip.translation)), (162.0, tuple(grip.translation))])
    arm_len = {}
    for side in ("l", "r"):
        upper = pose["upperarm_" + side].translation
        lower = pose["lowerarm_" + side].translation
        hand = pose["hand_" + side].translation
        arm_len[side] = (lower - upper).length + (hand - lower).length
    return {"left": left, "grip": grip, "grab": grab, "hand_keys": hand_keys,
            "bolt_back": bolt_back, "arm_len": arm_len, "reach": {}}


def bullpup_receiver(pose, frame):
    """Roll the receiver toward the shooter's left and let its parts ride."""
    pitch, yaw, roll, back, down = curve(RECEIVER_CURVE, frame)
    q = pose["WPN_root"].to_quaternion()
    pivot = pose["WPN_root"].translation.copy()
    lateral = (q @ Vector((1.0, 0.0, 0.0))).normalized()
    up = (q @ Vector((0.0, 0.0, 1.0))).normalized()
    bore = (q @ Vector((0.0, 1.0, 0.0))).normalized()
    rigid = (Matrix.Translation(q @ Vector((0.0, back, -down)))
             @ Matrix.Translation(pivot)
             @ Quaternion(bore, math.radians(roll)).to_matrix().to_4x4()
             @ Quaternion(up, math.radians(yaw)).to_matrix().to_4x4()
             @ Quaternion(lateral, math.radians(pitch)).to_matrix().to_4x4()
             @ Matrix.Translation(-pivot))
    for name in WEAPON_BONES:
        pose[name] = rigid @ pose[name]
    return roll


def hold_hand(pose, side, local, roll_degrees, data):
    """Drive one hand onto a receiver-local hold and roll it with the gun.

    The target already carries the roll, because it is expressed in the
    receiver's own frame. ``shift_arm`` is left to solve the reach from the
    untouched arm, so its segment lengths stay the ones the accepted clips have;
    the rotation is applied afterwards, about the wrist.
    """
    hand, lower, upper = "hand_" + side, "lowerarm_" + side, "upperarm_" + side
    target = pose["WPN_root"] @ local
    reach = (target.translation - pose[upper].translation).length / max(1e-6, data["arm_len"][side])
    data["reach"][side] = max(data["reach"].get(side, 0.0), reach)
    shift_arm(pose, side, target.translation - pose[hand].translation)
    # The roll arrives at the hand from the gun, so the forearm has to pay for
    # part of it: all of it on the wrist reads as a broken joint.
    if abs(roll_degrees) > 0.05:
        elbow = pose[lower].translation.copy()
        axis = (pose[hand].translation - elbow).normalized()
        spin = math.radians(roll_degrees * TWIST_SHARE)
        pronate = (Matrix.Translation(elbow) @ Quaternion(axis, spin).to_matrix().to_4x4()
                   @ Matrix.Translation(-elbow))
        for name in _descendants(lower):
            pose[name] = pronate @ pose[name]
    pivot = pose[hand].translation.copy()
    fix = target.to_quaternion() @ pose[hand].to_quaternion().inverted()
    turn = Matrix.Translation(pivot) @ fix.to_matrix().to_4x4() @ Matrix.Translation(-pivot)
    for name in hand_subtree(side):
        pose[name] = turn @ pose[name]


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


def bullpup_reload(pose, frame, data):
    """One frame of the bullpup empty reload, authored on the M4 cue clock."""
    roll = bullpup_receiver(pose, frame)
    q = pose["WPN_root"].to_quaternion()
    inv = pose["WPN_root"].inverted()

    magazine = Vector(curve(MAG_PATH, frame))
    pose["WPN_SOCKET_Magazine"] = Matrix.Translation(q @ magazine) @ pose["WPN_SOCKET_Magazine"]

    pull = curve(HANDLE_PULL, frame)[0]
    held = data["bolt_back"] * (1.0 - smooth((frame - BOLT_RELEASE) / 3.0))
    want = held + Vector((0.0, pull, 0.0))
    now = (inv @ pose["WPN_bolt"].translation) - BOLT_LOCAL
    pose["WPN_bolt"] = Matrix.Translation(q @ (want - now)) @ pose["WPN_bolt"]
    if pull > 1e-5:
        pose["WPN_ChargingHandle"] = (Matrix.Translation(q @ Vector((0.0, pull, 0.0)))
                                      @ pose["WPN_ChargingHandle"])

    if HAND_CARRY[0] <= frame <= HAND_CARRY[1]:
        target = data["grab"] + magazine          # locked to the magazine
    else:
        target = Vector(curve(data["hand_keys"], frame))
    right = Matrix.Translation(target - data["grip"].translation) @ data["grip"]
    hold_hand(pose, "r", right, roll, data)
    hold_hand(pose, "l", data["left"], roll, data)


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
    bullpup = kind in BULLPUP_CLIPS
    grab = RELOAD_GRAB.get(kind)
    if grab:
        delta_local = mag_delta_local()
    data = prepare_bullpup(source) if bullpup else None
    poses = []
    for step in range(end * 2 + 1):
        frame = step / 2.0
        pose = sample(source, frame)
        wrist_bend(pose, WRIST_BEND_DEGREES)
        if bullpup:
            bullpup_reload(pose, frame, data)
            viewmodel_jolt(pose, kind, frame)
        elif grab:
            weight = smooth((frame - grab[0]) / float(grab[2])) * (1.0 - smooth((frame - grab[1]) / float(grab[3])))
            if weight > 0.0:
                # The offset lives in the receiver's frame, so it has to follow
                # this frame's receiver orientation, not the idle one.
                shift_arm(pose, "l", pose["WPN_root"].to_quaternion() @ (delta_local * weight))
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
    if data:
        report[kind]["reach"] = {side: round(value, 3) for side, value in data["reach"].items()}
        for side, value in sorted(data["reach"].items()):
            if value > 1.0:
                print("ASH12_REACH_WARNING %s arm_%s %.3f of full extension" % (kind, side, value))

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
