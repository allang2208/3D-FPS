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
BOLT_COMPONENT = 79
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
BULLPUP_CLIPS = ("reload_empty", "reload")

# Receiver frame: +X the shooter's left, +Y toward the stock, +Z up. It is the
# local frame of WPN_root, so anything authored here rides the roll for free.
#
# Geometry that the beats below have to live inside (measured off the fitted
# rig): the firing shoulder sits 0.34 m behind and 0.21 m above the receiver
# origin with 0.55 m of arm, and the support hand already holds the rail at 97%
# of its reach in the accepted idle. So the firing hand can dip about 0.17 m
# below the magazine socket and no further; past that the magazine is released
# and finishes the extraction on its own, which is also what the accepted M4
# contract does with the old magazine.
# Magazine travel measured from its socket, receiver-local metres. The reference
# (2:06-2:10) changes the magazine inside one continuous hand move -- the
# receiver barely moves, the firing hand takes the old magazine down and brings
# the fresh one straight back up -- so the magazine stays in the hand from the
# out cue to the seat cue instead of being flung out of frame.
MAG_PATH = [
    (0.0, 0.000, 0.000, 0.000),
    (21.0, 0.000, 0.000, 0.000),      # cue: magazine out
    (30.0, 0.004, 0.008, -0.070),
    (40.0, 0.010, 0.020, -0.150),
    (46.0, 0.012, 0.024, -0.168),     # fully clear of the well, still in hand
    (52.0, 0.008, 0.016, -0.115),
    (54.0, 0.006, 0.014, -0.098),     # cue: the fresh magazine meets the well mouth
    (66.0, 0.003, 0.007, -0.042),
    (80.0, 0.000, 0.000, 0.000),      # cue: seated
    (162.0, 0.000, 0.000, 0.000),
]
# Firing hand: inside a carry window it is locked to the magazine, outside it
# follows the grip / charging handle anchors sampled off the accepted hold.
HAND_CARRY = ((21.0, 80.0),)
# Where the knuckles have to land on the magazine: the exposed body below the
# stock's bottom line, which is the only part a hand can close on. The wrist is
# then placed from the measured knuckle offset, exactly as for the handle.
MAG_GRAB_POINT = Vector((0.004, 0.006, -0.105))
MAG_GRIP_BIAS = Vector((0.000, 0.006, -0.008))

# The reference grips the handle from above, palm down. The handle patch is
# the real tab's top/outboard face; the bias only lifts the wrist clear of the
# receiver and puts it slightly behind the tab so the fingers wrap forward.
HANDLE_GRIP_BIAS = Vector((-0.005, 0.005, 0.010))
# The support hand holds the rail a touch further back than the accepted idle
# does: that pose is already at 97% of the arm's reach, and the roll would push
# it past full extension.
LEFT_BIAS = Vector((0.000, 0.024, -0.004))
# Receiver performance authored from the reference: the receiver tips toward the
# shooter's left and holds that tilt while the magazine is worked, then rolls
# deepest at the charging handle -- the roll is what turns the handle out to the
# firing hand, and it is also what swings the magazine's exposed length clear of
# the stock. Measured from the eye (sweep_mag_visibility.py): below 30 degrees of
# roll the magazine is completely hidden by the stock, 45 degrees shows about a
# quarter of it, and that is the ceiling -- only the bottom 35% of a bullpup
# magazine is outside the stock at all. (frame, pitch, yaw, roll, back, down).
RECEIVER_CURVE = [
    (0.0, 0.0, 0.0, 0.0, 0.000, 0.000),
    (13.0, -3.0, 0.5, 38.0, 0.004, 0.002),
    (21.0, -5.0, 0.8, 44.0, 0.007, 0.004),     # cue: magazine out
    (54.0, -7.0, 1.2, 48.0, 0.010, 0.006),     # cue: fresh magazine at the mouth
    (80.0, -7.0, 1.4, 50.0, 0.011, 0.006),     # cue: seated
    (105.0, -6.0, 1.6, 56.0, 0.012, 0.006),
    (122.0, -5.0, 1.8, 62.0, 0.012, 0.006),    # deepest: the handle faces the hand
    (136.0, -4.0, 1.4, 50.0, 0.009, 0.005),
    (150.0, -1.5, 0.6, 22.0, 0.004, 0.002),
    (162.0, 0.0, 0.0, 0.0, 0.000, 0.000),
]
# Where the firing hand's elbow should swing, receiver frame. Left at zero the
# IK keeps the accepted hold's elbow, which is right on the grip but drives the
# forearm through the stock on the way to the well; on the handle the elbow goes
# outboard instead so the arm crosses above the receiver.
RIGHT_POLE = [
    (0.0, 0.00, 0.00, 0.00),
    (14.0, 0.00, 0.35, -0.94),
    (80.0, 0.00, 0.35, -0.94),
    (96.0, -0.70, 0.20, -0.60),
    (108.0, -0.95, 0.12, -0.26),
    (140.0, -0.95, 0.12, -0.26),
    (152.0, 0.00, 0.00, 0.00),
    (162.0, 0.00, 0.00, 0.00),
]
# How far the firing hand's hold turns toward the receiver while it works the
# charging handle, degrees about the receiver's up axis. The hand keeps the
# accepted grip curl, so without this it reaches the handle palm-up as if
# placing the hand on top of the receiver instead of taking the handle sideways.
# The reference hand is rolled over the top of the handle, not yawed onto its
# side: rotate about the receiver's pull axis (+Y) so the palm faces the
# handle's top face.  The old 42-degree yaw about +Z is what read as a hand
# pasted onto the side of the receiver.
HANDLE_ROLL_DEGREES = 80.0
RIGHT_HAND_ROLL = [
    (0.0, 0.0),
    (96.0, 0.0),
    (108.0, HANDLE_ROLL_DEGREES),
    (140.0, HANDLE_ROLL_DEGREES),
    (152.0, 0.0),
    (162.0, 0.0),
]
# Charging handle: met by the firing hand, pulled straight back along the
# receiver, then let fly. (frame, metres).
HANDLE_PULL = [(0.0, 0.0), (108.0, 0.0), (118.0, 0.058), (126.0, 0.058), (133.0, 0.0), (162.0, 0.0)]
# Bolt: held back by the bolt catch for the whole empty reload, then released
# with the handle and driven home. (frame, metres back from rest).
# Magazine seat snap at the seat cue. The reference jolts the whole viewmodel at
# the moment the magazine lands; its camera stays steady (background phase
# correlation over the reload measured 0.00-0.01 px), so the snap belongs to the
# pose, not to a camera shake. (first frame, peak pitch degrees, peak metres
# back, decay frames).
JOLT = {"reload_empty": (80.0, 2.5, 0.008, 5.0),
        "reload": (95.0, 2.0, 0.006, 5.0)}
BOLT_RELEASE = 130.0
# How the weapon roll is split between forearm pronation and the wrist. All of
# it on the wrist alone reads as a broken joint; none of it leaves the gun
# turning inside a locked hand.
TWIST_SHARE = 0.55
# Firing-wrist compensation, degrees. Measured against the accepted M4
# reference the hand-to-grip alignment is already within 5 degrees, so this
# stays at zero; the constant exists for a later hand-pose pass.
WRIST_BEND_DEGREES = 0.0

# The bullpup stock reaches 0.46 m behind the receiver's origin, so the accepted
# M4 hold puts the firing forearm inside it -- and in ADS that same arm sits
# 4.6 cm from the camera, which is the "blob of hand" the player sees on screen.
# Every clip re-solves the elbow outboard of the stock; the hand does not move.
RIGHT_ARM_POLE = (-0.95, 0.12, -0.26)
# ADS-arm clearance, world metres in the aim pose (muzzle +Y, shooter -Y, up
# +Z). The shoulder root itself sits ~6 cm in front of the ADS eye and 3 cm
# below it, so even with the elbow solved outboard the upper-arm skin crosses
# the sight line: hundreds of arm vertices land inside the 55-degree ADS
# frustum near screen centre-right -- the arm in every real capture. The elbow
# pole cannot move that skin (the hand is pinned and the forearm is already
# clear of the stock), so the root itself moves behind the camera plane and
# down instead: the whole upper arm then reaches in from below the frame like
# a standard FPS viewmodel. Aimed with probe_ads_shoulder.py; verified again
# after every change because the shift also re-solves the elbow.
RIGHT_SHOULDER_SHIFT = (-0.01, -0.12, -0.10)

# --- reload retiming: stretch the magazine swap, keep everything else --------
# The authored beat tables stay in M4 source frames; this only slows the
# EXPORTED clock so the magazine work reads at a calmer pace (user request of
# 2026-09-19: lengthen the reloads, the empty one especially in the pull and
# insert beats). Segments are (start, end, rate) in source frames; rate > 1
# means the exported action spends more time on that span.
BULLPUP_RETIME = {
    "reload_empty": [(0.0, 14.0, 1.0), (14.0, 86.0, 1.30), (86.0, 96.0, 1.0),
                     (96.0, 150.0, 1.20), (150.0, 162.0, 1.0)],
    "reload": [(0.0, 18.0, 1.0), (18.0, 95.0, 1.18), (95.0, 126.0, 1.0)],
}


def make_retimer(segments):
    """Return (forward, backward, new_length) between source and exported frames."""
    def forward(f):
        out = 0.0
        for start, end, rate in segments:
            if f <= end:
                return out + max(0.0, f - start) * rate
            out += (end - start) * rate
        return out

    def backward(g):
        out = 0.0
        for start, end, rate in segments:
            span = (end - start) * rate
            if g <= out + span:
                return start + (g - out) / rate
            out += span
        return segments[-1][1]

    return forward, backward, forward(segments[-1][1])


for _kind, _segments in BULLPUP_RETIME.items():
    _forward, _backward, _length = make_retimer(_segments)
    _cues = (21.0, 54.0, 80.0, 130.0) if _kind == "reload_empty" else (29.0, 76.0, 95.0)
    print("ASH12_RETIME %s new_length=%.1f frames (%.3f s) cues %s -> %s"
          % (_kind, _length, _length / 60.0,
             [int(c) for c in _cues], [int(round(_forward(c))) for c in _cues]))
# How far the outboard pole is allowed to bend toward the natural wrist axis.
# 0.0 keeps the old (twisted) pole exactly; 1.0 ignores the stock clearance.
# The accepted WristNatural pass used 0.8 for its support hand, so use the
# same share here and let the twist bones absorb the remaining roll.
ARM_NATURAL_BLEND = 0.8
# A fist for the charging handle. The accepted grip leaves the trigger finger
# lying along the receiver, which reads as one finger sticking out once the hand
# turns toward the handle, so the fingers are curled evenly instead. Values are
# the local Z rotation of each joint, the axis the M4 poses curl on.
HANDLE_FIST = {"01": 58.0, "02": 62.0, "03": 34.0}
# How much of that fist is closed, per frame: closes as the hand leaves the
# magazine and opens again once it is back on the grip.
# Closed twice: once around the magazine and once around the charging handle.
HANDLE_FIST_BLEND = [(0.0, 0.0), (14.0, 0.0), (26.0, 1.0), (74.0, 1.0), (86.0, 0.0),
                     (98.0, 0.0), (110.0, 1.0), (140.0, 1.0), (150.0, 0.0), (162.0, 0.0)]
# Share of the hand's turn that the forearm takes instead of the wrist.
TURN_SHARE = 0.6

# --- tactical reload: same bullpup mechanism, closed bolt -------------------
# The cues are 29 (magazine out), 76 (fresh magazine at the well mouth) and
# 95 (seated). There is no charging-handle phase because the bolt never opens.
RECEIVER_CURVE_RELOAD = [
    (0.0, 0.0, 0.0, 0.0, 0.000, 0.000),
    (14.0, -3.0, 0.5, 36.0, 0.004, 0.002),
    (29.0, -5.0, 0.8, 46.0, 0.007, 0.004),     # cue: magazine out
    (52.0, -6.0, 1.0, 48.0, 0.008, 0.005),
    (76.0, -7.0, 1.2, 50.0, 0.010, 0.006),     # cue: fresh magazine at the mouth
    (95.0, -7.0, 1.4, 50.0, 0.011, 0.006),     # cue: seated
    (110.0, -4.0, 1.0, 32.0, 0.007, 0.004),
    (120.0, -1.5, 0.5, 12.0, 0.003, 0.002),
    (126.0, 0.0, 0.0, 0.0, 0.000, 0.000),
]
MAG_PATH_RELOAD = [
    (0.0, 0.000, 0.000, 0.000),
    (29.0, 0.000, 0.000, 0.000),      # cue: magazine out
    (38.0, 0.004, 0.008, -0.070),
    (48.0, 0.010, 0.020, -0.150),
    (54.0, 0.012, 0.024, -0.168),     # fully clear of the well, still in hand
    (62.0, 0.008, 0.016, -0.115),
    (76.0, 0.006, 0.014, -0.098),     # cue: the fresh magazine meets the well mouth
    (88.0, 0.003, 0.007, -0.042),
    (95.0, 0.000, 0.000, 0.000),      # cue: seated
    (126.0, 0.000, 0.000, 0.000),
]
HAND_CARRY_RELOAD = ((29.0, 95.0),)
RIGHT_POLE_RELOAD = [
    (0.0, 0.00, 0.00, 0.00),
    (14.0, 0.00, 0.35, -0.94),
    (95.0, 0.00, 0.35, -0.94),
    (110.0, 0.00, 0.00, 0.00),
    (126.0, 0.00, 0.00, 0.00),
]
RIGHT_HAND_ROLL_RELOAD = [(0.0, 0.0), (126.0, 0.0)]
HANDLE_FIST_BLEND_RELOAD = [(0.0, 0.0), (14.0, 0.0), (26.0, 1.0), (90.0, 1.0),
                            (104.0, 0.0), (126.0, 0.0)]

# Per-clip bullpup tables. ``hand_keys`` is completed in prepare_bullpup,
# because its grip/well/mid anchors are measured off the fitted rig.
BULLPUP_SPECS = {
    "reload_empty": {
        "receiver": RECEIVER_CURVE,
        "mag": MAG_PATH,
        "carry": HAND_CARRY,
        "pole": RIGHT_POLE,
        "turn": RIGHT_HAND_ROLL,
        "fist": HANDLE_FIST_BLEND,
        "handle_pull": HANDLE_PULL,
        "bolt_back": True,
    },
    "reload": {
        "receiver": RECEIVER_CURVE_RELOAD,
        "mag": MAG_PATH_RELOAD,
        "carry": HAND_CARRY_RELOAD,
        "pole": RIGHT_POLE_RELOAD,
        "turn": RIGHT_HAND_ROLL_RELOAD,
        "fist": HANDLE_FIST_BLEND_RELOAD,
        "handle_pull": None,
        "bolt_back": False,
    },
}

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
bolt_verts = set(groups[BOLT_COMPONENT])
print("ASH12_COMPONENTS", len(groups), "trigger_verts", len(trigger_verts))

mag_slots = {i for i, m in enumerate(me.materials) if m and m.name in MAGAZINE_MATERIALS}

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
    elif all(v in bolt_verts for v in poly.vertices):
        bone = "WPN_bolt"
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

# The reference video grips the charging handle from above, palm down.  The
# handle mesh is bound to WPN_ChargingHandle with an offset, so measure the
# real handle's receiver-local top/outboard patch instead of aiming at the
# bone head.  This keeps the hand on the actual tab while leaving the roll and
# timing to the authored tables below.
handle_verts = [i for i, bone in bone_for.items() if bone == "WPN_ChargingHandle"]
handle_local_points = [rest["WPN_root"].inverted() @ (fit_matrix @ verts[i]) for i in handle_verts]
handle_top_z = max(p.z for p in handle_local_points)
handle_top_points = [p for p in handle_local_points if p.z >= handle_top_z - 0.010]
handle_outboard_x = min(p.x for p in handle_top_points)
handle_grip_points = [p for p in handle_top_points if p.x <= handle_outboard_x + 0.004]
HANDLE_GRIP_LOCAL = sum(handle_grip_points, Vector((0.0, 0.0, 0.0))) / len(handle_grip_points)
print("ASH12_HANDLE_GEOMETRY verts=%d grip_local=%s"
      % (len(handle_verts), tuple(round(c, 4) for c in HANDLE_GRIP_LOCAL)))

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
normal_matrices = {}
for i, v in enumerate(verts):
    bone = bone_for.get(i, "WPN_root")
    bind = rest[bone] @ base[bone].inverted() @ base["WPN_root"] @ xf
    newverts.append(bind @ v)
    normal_matrices[bone] = bind.to_3x3().inverted().transposed()

# Only the vertices the kept faces reference; the deferred parts drop out here.
used = sorted({v for p in keep_polys for v in me.polygons[p].vertices})
remap = {old: new for new, old in enumerate(used)}
newverts = [newverts[i] for i in used]
faces = [[remap[v] for v in me.polygons[p].vertices] for p in keep_polys]
loop_normals = []
for p in keep_polys:
    poly = me.polygons[p]
    for li in range(poly.loop_start, poly.loop_start + poly.loop_total):
        bone = bone_for.get(me.loops[li].vertex_index, "WPN_root")
        loop_normals.append((normal_matrices[bone] @ corner_normals[li]).normalized())

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


def prepare_bullpup(source, kind):
    """Anchors for the bullpup reload, read off the accepted hold on this gun.

    Both hands are frozen as receiver-local matrices: the position travels along
    the authored path, the orientation stays the natural hold it has at frame 0.
    That keeps the M4 clip's own hand rotation out of the result and lets the
    roll carry the hands without extra maths. The receiver's frame-0 pose is kept
    too, because this clip replaces the M4 clip's weapon performance outright.
    """
    spec = BULLPUP_SPECS[kind]
    pose = sample(source, 0.0)
    inv = pose["WPN_root"].inverted()
    root0 = pose["WPN_root"].copy()
    grip = (inv @ pose["hand_r"]).copy()
    left = (inv @ pose["hand_l"]).copy()
    left.translation += LEFT_BIAS
    bolt_back = (inv @ pose["WPN_bolt"].translation) - BOLT_LOCAL
    knuckle = (inv @ pose["index_01_r"].translation) - grip.translation
    grab = WELL_LOCAL + MAG_GRAB_POINT - knuckle * 1.06 + MAG_GRIP_BIAS
    # The two hands of the charge phase share one pull table, so the handle and
    # the hand holding it cannot drift apart.
    def key(frame, point):
        return (frame, point[0], point[1], point[2])

    knuckle_rolled = (Matrix.Rotation(math.radians(HANDLE_ROLL_DEGREES), 4, "Y") @ knuckle)
    handle_grip = HANDLE_GRIP_LOCAL - knuckle_rolled * 1.06 + HANDLE_GRIP_BIAS
    print("ASH12_HANDLE_GRIP knuckle=%.3f m  mag_wrist=(%.3f, %.3f, %.3f)  handle_wrist=(%.3f, %.3f, %.3f)"
          % (knuckle.length, grab.x, grab.y, grab.z, handle_grip.x, handle_grip.y, handle_grip.z))
    # The hand goes along the receiver's right flank to reach the handle, not
    # through the receiver and not down from above: a straight line from the
    # well to the handle passes inside the lower.
    mid = Vector((-0.096, 0.010, -0.046))
    if spec["handle_pull"] is not None:
        pull = [key(f, handle_grip + Vector((0.0, m, 0.0)))
                for f, m in spec["handle_pull"] if 100.0 < f < 145.0]
        hand_keys = ([key(0.0, grip.translation), key(3.0, grip.translation),
                      key(21.0, grab), key(80.0, grab)]
                     + [key(96.0, mid)]
                     + pull
                     + [key(152.0, grip.translation), key(162.0, grip.translation)])
    else:
        # Closed-bolt tactical reload: grip -> well -> grip. The magazine and
        # the hand both remain on the receiver's centreline.
        hand_keys = [key(0.0, grip.translation), key(3.0, grip.translation),
                     key(29.0, grab), key(95.0, grab),
                     key(108.0, grip.translation), key(126.0, grip.translation)]
    arm_len = {}
    holds = {}
    # How far each finger joint has to turn to make a fist for the handle: the
    # accepted grip curls them around the pistol grip with the trigger finger
    # lying along the receiver, which reads as one finger sticking out once the
    # hand turns to take the charging handle.
    fist_delta = {}
    for name in hand_subtree("r"):
        parts = name.split("_")
        if len(parts) != 3 or parts[0] not in ("index", "middle", "ring", "pinky"):
            continue
        target = HANDLE_FIST.get(parts[1])
        if target is None:
            continue
        current = math.degrees(rig.pose.bones[name].rotation_quaternion.to_euler("XYZ").z)
        fist_delta[name] = target - current
    for side in ("l", "r"):
        upper = pose["upperarm_" + side].translation
        lower = pose["lowerarm_" + side].translation
        hand = pose["hand_" + side].translation
        arm_len[side] = (lower - upper).length + (hand - lower).length
        # The whole hand, fingers included, is frozen on the gun: the M4 clip
        # opens and closes these fingers to work a magazine under the receiver,
        # which under a bullpup is a hand doing nothing on the handguard.
        holds[side] = {name: inv @ pose[name] for name in hand_subtree(side)}
        # Where the shoulder sits in the receiver frame, so the authored targets
        # can be read against it.
        shoulder = inv @ upper
        print("ASH12_ARM_%s shoulder_recv=(%.3f, %.3f, %.3f) length=%.3f"
              % (side, shoulder.x, shoulder.y, shoulder.z, arm_len[side]))
    for side, hold in (("l", left), ("r", grip)):
        reach = ((pose["WPN_root"] @ hold).translation - pose["upperarm_" + side].translation).length / arm_len[side]
        print("ASH12_HOLD frame0 reach_%s=%.3f" % (side, reach))
    return {"left": left, "grip": grip, "grab": grab, "hand_keys": hand_keys, "holds": holds,
            "bolt_back": bolt_back, "arm_len": arm_len, "reach": {}, "root0": root0,
            "fist_delta": fist_delta, "spec": spec}


def bullpup_receiver(pose, frame, data, receiver_curve):
    """Author the receiver's own performance, replacing the M4 clip's.

    The accepted M4 reload drives the receiver through an arc of its own --
    measured roll -46 degrees at frame 18, +101 at 24, then a steady -50 through
    the middle. Adding the bullpup roll on top of that put the gun past 140
    degrees, and an inherited arc is the wrong performance for this reload
    anyway, so the receiver is driven from this clip's frame instead: the pose it
    holds at frame 0 plus the authored tip, yaw, roll and travel.
    """
    pitch, yaw, roll, back, down = curve(receiver_curve, frame)
    target = (data["root0"]
              @ Matrix.Translation(Vector((0.0, back, -down)))
              @ Quaternion(Vector((0.0, 1.0, 0.0)), math.radians(roll)).to_matrix().to_4x4()
              @ Quaternion(Vector((0.0, 0.0, 1.0)), math.radians(yaw)).to_matrix().to_4x4()
              @ Quaternion(Vector((1.0, 0.0, 0.0)), math.radians(pitch)).to_matrix().to_4x4())
    rigid = target @ pose["WPN_root"].inverted()
    for name in WEAPON_BONES:
        pose[name] = rigid @ pose[name]
    return roll


def hold_hand(pose, side, offset, roll_degrees, data, frame, spec):
    """Put one hand, fingers and all, exactly where the receiver says.

    ``shift_arm`` solves the reach from the untouched arm, so its segment lengths
    stay the ones the accepted clips have. The hand and its fingers are then
    placed from the keep pose sampled at frame 0, which keeps the M4 clip's own
    hand rotation and finger work out of the result. The roll arrives at the hand
    from the gun, so the forearm pays for part of it: all of it on the wrist
    alone reads as a broken joint.
    """
    hand, lower, upper = "hand_" + side, "lowerarm_" + side, "upperarm_" + side
    anchor = data["grip"] if side == "r" else data["left"]
    local = Matrix.Translation(offset) @ anchor
    turn = curl = 0.0
    hand_rot = Matrix.Identity(4)
    if side == "r":
        turn = curve(spec["turn"], frame)[0]
        curl = curve(spec["fist"], frame)[0]
        if abs(turn) > 0.05:
            # About the wrist, so the hand rolls without moving off the handle.
            # The reference grip is overhand: the hand itself has to roll, not
            # only the wrist target and the forearm.
            pivot = anchor.translation
            spin = Matrix.Rotation(math.radians(turn), 4, "Y")
            hand_rot = Matrix.Translation(pivot) @ spin @ Matrix.Translation(-pivot)
    target = pose["WPN_root"] @ local
    reach = (target.translation - pose[upper].translation).length / max(1e-6, data["arm_len"][side])
    if reach > data["reach"].get(side, (0.0, 0.0))[0]:
        data["reach"][side] = (reach, frame)
    pole = None
    if side == "r":
        hint = Vector(curve(spec["pole"], frame))
        if hint.length > 1e-6:
            pole = (pose["WPN_root"].to_quaternion() @ hint).normalized()
    shift_arm(pose, side, target.translation - pose[hand].translation, pole)
    # Whatever the hand turns by, the forearm pays most of it: the same turn all
    # at the wrist is what reads as a twisted arm.
    if abs(turn) > 0.05:
        elbow = pose[lower].translation.copy()
        axis = (pose[hand].translation - elbow).normalized()
        spin = math.radians(turn * TURN_SHARE)
        pronate = (Matrix.Translation(elbow) @ Quaternion(axis, spin).to_matrix().to_4x4()
                   @ Matrix.Translation(-elbow))
        for name in _descendants(lower):
            pose[name] = pronate @ pose[name]
    if abs(roll_degrees) > 0.05:
        elbow = pose[lower].translation.copy()
        axis = (pose[hand].translation - elbow).normalized()
        spin = math.radians(roll_degrees * TWIST_SHARE)
        pronate = (Matrix.Translation(elbow) @ Quaternion(axis, spin).to_matrix().to_4x4()
                   @ Matrix.Translation(-elbow))
        for name in _descendants(lower):
            pose[name] = pronate @ pose[name]
    for name, hold in data["holds"][side].items():
        pose[name] = pose["WPN_root"] @ Matrix.Translation(offset) @ hand_rot @ hold
        if side == "r" and curl > 0.001:
            pose[name] = pose[name] @ Matrix.Rotation(math.radians(data["fist_delta"].get(name, 0.0) * curl), 4, "Z")


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
    spec = data["spec"]
    roll = bullpup_receiver(pose, frame, data, spec["receiver"])

    # The magazine, bolt and charging handle are placed outright: the M4 clip
    # animates all three (its magazine flies a 0.7 m arc), and none of that
    # belongs to a bullpup change.
    magazine = Vector(curve(spec["mag"], frame))
    pose["WPN_SOCKET_Magazine"] = pose["WPN_root"] @ Matrix.Translation(WELL_LOCAL + magazine)

    pull = curve(spec["handle_pull"], frame)[0] if spec["handle_pull"] is not None else 0.0
    if spec["bolt_back"]:
        held = data["bolt_back"] * (1.0 - smooth((frame - BOLT_RELEASE) / 3.0))
    else:
        held = Vector((0.0, 0.0, 0.0))
    pose["WPN_bolt"] = pose["WPN_root"] @ Matrix.Translation(BOLT_LOCAL + held + Vector((0.0, pull, 0.0)))
    pose["WPN_ChargingHandle"] = pose["WPN_root"] @ Matrix.Translation(HANDLE_LOCAL + Vector((0.0, pull, 0.0)))

    if any(lo <= frame <= hi for lo, hi in spec["carry"]):
        target = data["grab"] + magazine          # locked to the magazine
    else:
        target = Vector(curve(data["hand_keys"], frame))
    hold_hand(pose, "r", target - data["grip"].translation, roll, data, frame, spec)
    hold_hand(pose, "l", Vector((0.0, 0.0, 0.0)), roll, data, frame, spec)


def shift_arm(pose, side, shift, pole_hint=None):
    upper, lower, hand = "upperarm_" + side, "lowerarm_" + side, "hand_" + side
    old_upper = pose[upper].copy()
    old_lower = pose[lower].copy()
    old_pose = {name: pose[name].copy() for name in names}
    a, b, c = [pose[n].translation.copy() for n in (upper, lower, hand)]
    goal = c + shift
    l1 = (b - a).length
    l2 = (c - b).length
    axis = (goal - a).normalized()
    d = (goal - a).length
    if d >= l1 + l2:
        a += axis * (d - l1 - l2 + 0.0001)
        d = (goal - a).length
    # Where the elbow ends up decides whether the forearm clears the receiver:
    # the accepted hold keeps it high, which sends the arm straight through the
    # stock on the way to a bullpup magazine well. A caller can name the side the
    # elbow should swing to instead.
    pole = pole_hint.copy() if pole_hint is not None else (b - a)
    pole -= axis * pole.dot(axis)
    if pole.length < 1e-6:
        pole = (b - a) - axis * (b - a).dot(axis)
    pole.normalize()
    along = (l1 * l1 - l2 * l2 + d * d) / (2 * d)
    elbow = a + axis * along + pole * math.sqrt(max(0.0, l1 * l1 - along * along))
    pose[upper] = Matrix.LocRotScale(a, (b - pose[upper].translation).rotation_difference(elbow - a) @ pose[upper].to_quaternion(), pose[upper].to_scale())
    pose[lower] = Matrix.LocRotScale(elbow, (c - b).rotation_difference(goal - elbow) @ pose[lower].to_quaternion(), pose[lower].to_scale())
    for name in names:
        if name == hand or (name.endswith("_" + side) and name.startswith(("thumb", "index", "middle", "ring", "pinky"))):
            pose[name].translation += shift
        elif name.endswith("_" + side) and name.startswith(("upperarm_twist", "lowerarm_twist")):
            # Preserve the accepted relative twist instead of resetting the
            # helper to rest. That reset is the visible firing-arm twist in the
            # bullpup reload; hold_hand still shares the explicit fore-aft roll.
            parent = parents[name]
            pose[name] = pose[parent] @ old_pose[parent].inverted() @ old_pose[name]


def shift_arm_natural(pose, side, pole_hint=None, hand_target=None, natural_blend=0.8,
                      shoulder_shift=None):
    """Keep the accepted hand on the gun, but solve the arm like WristNatural.

    The old pole solver left the hand orientation untouched while it swung the
    forearm to a new elbow, so the whole correction landed on the wrist and the
    twist helper bones were reset to rest.  This ports the accepted foregrip
    fix instead: keep the hand world matrix, let the elbow move toward the
    pole, derive the natural forearm direction from that hand orientation, and
    distribute the remaining roll across the two forearm twist bones (the
    0.55 / 0.95 shares from the accepted WristNatural pass).
    """
    upper, lower, hand = "upperarm_" + side, "lowerarm_" + side, "hand_" + side
    old_upper = pose[upper].copy()
    old_lower = pose[lower].copy()
    old_hand = pose[hand].copy()
    old_pose = {name: pose[name].copy() for name in names}
    H = hand_target.copy() if hand_target is not None else old_hand.copy()
    A = old_upper.translation.copy()
    if shoulder_shift is not None:
        # Root clearance for the ADS eye (see RIGHT_SHOULDER_SHIFT): applied
        # before the IK so the elbow re-solves from the moved root and the
        # overreach guard below never has to trigger.
        A += shoulder_shift
    target = H.translation.copy()
    l1 = (rest[lower].translation - rest[upper].translation).length
    l2 = (rest[hand].translation - rest[lower].translation).length
    axis = (target - A).normalized()
    reach = (target - A).length
    if reach > l1 + l2 - 0.015:
        shift = axis * (reach - (l1 + l2 - 0.015))
        A += shift
        clavicle = "clavicle_" + side
        if clavicle in pose:
            pose[clavicle] = Matrix.Translation(shift) @ pose[clavicle]
    dist = (target - A).length
    axis = (target - A).normalized()
    pole = Vector(pole_hint) if pole_hint is not None else (old_lower.translation - A)
    pole -= axis * pole.dot(axis)
    if pole.length < 1e-6:
        pole = (old_lower.translation - A) - axis * (old_lower.translation - A).dot(axis)
    pole.normalize()
    desired = (H.to_3x3() @ rest[hand].to_3x3().inverted()
               @ (rest[hand].translation - rest[lower].translation).normalized())
    natural = target - desired * l2 - A
    natural -= axis * natural.dot(axis)
    if natural.length > 1e-6 and natural_blend > 0.0:
        pole = pole.lerp(natural.normalized(), natural_blend).normalized()
    along = (l1 * l1 - l2 * l2 + dist * dist) / (2.0 * dist)
    elbow = A + axis * along + pole * math.sqrt(max(0.0, l1 * l1 - along * along))
    u = (elbow - A).normalized()
    v = (target - elbow).normalized()
    ou = (old_lower.translation - old_upper.translation).normalized()
    ov = (old_hand.translation - old_lower.translation).normalized()
    pose[upper] = Matrix.LocRotScale(A, ou.rotation_difference(u) @ old_upper.to_quaternion(),
                                     old_upper.to_scale())
    pose[lower] = Matrix.LocRotScale(elbow, ov.rotation_difference(v) @ old_lower.to_quaternion(),
                                     old_lower.to_scale())
    # Preserve the accepted upper-arm twist instead of resetting the helpers
    # to rest (the old solver's visible skin twist).
    for name in ("upperarm_twist_01_" + side, "upperarm_twist_02_" + side):
        if name in pose:
            pose[name] = pose[upper] @ old_upper.inverted() @ old_pose[name]
    # Move the residual forearm roll off the wrist and onto the two twist bones.
    neutral = (pose[lower].to_quaternion() @ rest[lower].to_quaternion().inverted()
               @ rest[hand].to_quaternion())
    q = H.to_quaternion() @ neutral.inverted()
    twist = 2.0 * math.atan2(Vector((q.x, q.y, q.z)).dot(v), q.w)
    twist = (twist + math.pi) % (2.0 * math.pi) - math.pi
    for name, share in (("lowerarm_twist_02_" + side, 0.55), ("lowerarm_twist_01_" + side, 0.95)):
        if name in pose:
            m = pose[lower] @ rest[lower].inverted() @ rest[name]
            pose[name] = Matrix.LocRotScale(m.translation,
                                            Quaternion(v, twist * share) @ m.to_quaternion(),
                                            m.to_scale())
    # Put the hand/finger subtree back on the target without changing its grip.
    rigid = H @ old_hand.inverted()
    for name in hand_subtree(side):
        if name in old_pose:
            pose[name] = rigid @ old_pose[name]


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
    grab = None if bullpup else RELOAD_GRAB.get(kind)
    if grab:
        delta_local = mag_delta_local()
    data = prepare_bullpup(source, kind) if bullpup else None
    poses = []
    retime = BULLPUP_RETIME.get(kind)
    if bullpup and retime:
        _, backward, new_end = make_retimer(retime)
        steps = range(int(math.ceil(new_end)) * 2 + 1)
    else:
        backward, steps = None, range(end * 2 + 1)
    for step in steps:
        frame = step / 2.0
        src_frame = backward(frame) if backward else frame
        pose = sample(source, src_frame)
        wrist_bend(pose, WRIST_BEND_DEGREES)
        if bullpup:
            bullpup_reload(pose, src_frame, data)
            viewmodel_jolt(pose, kind, src_frame)
        elif grab:
            weight = smooth((frame - grab[0]) / float(grab[2])) * (1.0 - smooth((frame - grab[1]) / float(grab[3])))
            if weight > 0.0:
                # The offset lives in the receiver's frame, so it has to follow
                # this frame's receiver orientation, not the idle one.
                shift_arm(pose, "l", pose["WPN_root"].to_quaternion() @ (delta_local * weight))
        if not bullpup:
            # The bullpup stock reaches 0.46 m behind the receiver's origin, so
            # the accepted M4 hold buries the firing forearm in it; in ADS the
            # same arm ends up 4.6 cm from the camera. Re-solve the arm while
            # keeping the accepted hand matrix: the firing arm starts from the
            # outboard pole so the stock clears, then blends toward the natural
            # wrist direction and pays the residual roll on the forearm twist
            # bones (the accepted WristNatural method). The support arm uses
            # the natural pole directly.
            pole = (pose["WPN_root"].to_quaternion() @ Vector(RIGHT_ARM_POLE)).normalized()
            # World-space on purpose: the clearance is measured against the ADS
            # eye, not the receiver, and the receiver's own frame flips the
            # shooter axis between clips (see RIGHT_SHOULDER_SHIFT).
            shift_arm_natural(pose, "r", pole, pose["hand_r"].copy(), ARM_NATURAL_BLEND,
                              shoulder_shift=Vector(RIGHT_SHOULDER_SHIFT))
            shift_arm_natural(pose, "l", None, pose["hand_l"].copy(), ARM_NATURAL_BLEND)
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
        report[kind]["reach"] = {side: [round(value, 3), frame] for side, (value, frame) in data["reach"].items()}
        for side, (value, frame) in sorted(data["reach"].items()):
            if value > 1.0:
                print("ASH12_REACH_WARNING %s arm_%s %.3f of full extension at frame %.1f"
                      % (kind, side, value, frame))

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
