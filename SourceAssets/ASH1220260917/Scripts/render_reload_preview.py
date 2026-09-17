"""Author-position preview of the authored clips, for the reload beats.

Three views per frame:
  player  camera behind and above the receiver, the angle the player reads
  side    orthographic from the shooter's right, for arm and elbow shapes
  well    gun-relative close-up on whatever the firing hand is working

Run: ASH12_FRAMES="reload_empty:21,reload_empty:46" ASH12_VIEWS="player,side" \
     blender --background --factory-startup --python-exit-code 1 --python render_reload_preview.py
Writes Reference/preview_<clip>_<frame>_<view>.png
"""
import os

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
O = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(O, "Reference")
FRAMES = os.environ.get("ASH12_FRAMES", "reload_empty:0,reload_empty:21,reload_empty:34,reload_empty:46,"
                                         "reload_empty:54,reload_empty:80,reload_empty:100,reload_empty:122,"
                                         "reload_empty:150,reload_empty:162")
VIEWS = os.environ.get("ASH12_VIEWS", "player,well")

bpy.ops.wm.open_mainfile(filepath=os.path.join(O, "ASH12_Editable.blend"))
scene = bpy.context.scene
rig = bpy.data.objects["SK_M4_Infima"]
KEEP = ("SK_M4_Infima", "SK_Manny_Arms_Export", "ASH12_Export")
for obj in scene.objects:
    obj.hide_render = obj.name not in KEEP
for obj in list(scene.objects):
    if obj.type in ("CAMERA", "LIGHT"):
        bpy.data.objects.remove(obj, do_unlink=True)

try:
    scene.render.engine = "BLENDER_EEVEE_NEXT"
except TypeError:
    scene.render.engine = "BLENDER_EEVEE"
scene.view_settings.view_transform = "Standard"
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.image_settings.file_format = "PNG"
world = bpy.data.worlds.new("Preview")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.20, 0.22, 0.25, 1.0)

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam


def aim(location, target):
    cam.location = location
    cam.rotation_euler = (Vector(target) - Vector(location)).to_track_quat("-Z", "Y").to_euler()


def set_action(name, frame):
    action = bpy.data.actions[name]
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()
    return {b.name: b.matrix.copy() for b in rig.pose.bones}


# The player's eye, read off the shipped ADS calibration instead of guessed: the
# runtime puts the camera ADSRearEyeDistance behind the rear sight, along the
# sight axis. The same eye then watches the hip reload, because lowering the
# weapon does not move the head.
if not rig.animation_data:
    rig.animation_data_create()
_aim = set_action("ASH12_aim", 0)
_rear = _aim["WPN_RearSight"].translation.copy()
_front = _aim["WPN_FrontSight"].translation.copy()
EYE_FWD = (_front - _rear).normalized()
EYE = _rear - EYE_FWD * 0.18
EYE_UP = (Vector((0.0, 0.0, 1.0)) - EYE_FWD * Vector((0.0, 0.0, 1.0)).dot(EYE_FWD)).normalized()
EYE_RIGHT = EYE_FWD.cross(EYE_UP)
print("ASH12_EYE pos=%s fwd=%s" % (tuple(round(c, 4) for c in EYE), tuple(round(c, 4) for c in EYE_FWD)))


for spec in FRAMES.split(","):
    clip, frame = spec.split(":")
    frame = float(frame)
    action = bpy.data.actions["ASH12_" + clip]
    rig.animation_data.action = action
    if action.slots:
        rig.animation_data.action_slot = action.slots[0]
    scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()

    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    root = pose["WPN_root"].translation.copy()
    spin = pose["WPN_root"].to_quaternion()
    up = (spin @ Vector((0.0, 0.0, 1.0))).normalized()
    # The receiver's own +Y points at the stock, so ``rear`` is the way the
    # shooter's eye lies; the muzzle is the other way.
    rear = (spin @ Vector((0.0, 1.0, 0.0))).normalized()
    left = (spin @ Vector((1.0, 0.0, 0.0))).normalized()
    # The eye sits above and behind the accepted hip pose; keep that relationship
    # to the receiver so the preview keeps the angle the player reads.
    # The game draws the viewmodel 7 cm right and 7 cm down of the camera
    # (M4HipViewmodelLocation), so the camera sits up and to the left of the
    # receiver's rear, looking down the bore.
    eye = root + rear * 0.34 + up * 0.30 - left * 0.06

    for light_spec in ((1.2, -0.4, 1.2, 320), (-1.0, -0.3, 0.6, 220), (0.4, 1.2, 0.2, 140)):
        lamp = bpy.data.lights.new("area", "AREA")
        lamp.energy = light_spec[3]
        lamp.size = 1.6
        holder = bpy.data.objects.new("area", lamp)
        scene.collection.objects.link(holder)
        holder.location = root + Vector(light_spec[:3])
        holder.rotation_euler = (root - holder.location).to_track_quat("-Z", "Y").to_euler()

    for view in VIEWS.split(","):
        if view == "player":
            # Game framing: the viewmodel is drawn 7 cm right and 7 cm down of
            # the camera (M4HipViewmodelLocation), so the camera sits the other
            # way. 18 mm on a 36 mm sensor is the viewmodel's wide FOV.
            cam_data.type = "PERSP"
            cam_data.lens = 18.0
            at = EYE - EYE_RIGHT * 0.07 + EYE_UP * 0.07
            aim(at, at + EYE_FWD)
        elif view == "side":
            cam_data.type = "ORTHO"
            cam_data.ortho_scale = 1.25
            aim(root - left * 1.8 + up * 0.10, root + up * 0.02)
        elif view == "sky":
            # Straight down in world space: a rolled receiver shows its side
            # surface from above, an upright one shows a thin silhouette.
            cam_data.type = "ORTHO"
            cam_data.ortho_scale = 1.2
            aim(root + Vector((0.0, 0.0, 1.6)), root)
        elif view == "world":
            # Fixed to the world, not to the receiver, so the roll itself is
            # visible; looks at the shooter's right side, where the bullpup
            # magazine well and the charging handle end up.
            cam_data.type = "PERSP"
            cam_data.lens = 32.0
            aim(root + Vector((0.62, -0.16, 0.30)), root + Vector((0.0, 0.05, -0.02)))
        elif view == "handle":
            handle = pose["WPN_ChargingHandle"].translation.copy()
            cam_data.type = "PERSP"
            cam_data.lens = 45.0
            aim(handle - left * 0.30 + up * 0.22 + rear * 0.05, handle + up * 0.01)
        elif view == "well":
            well = pose["WPN_SOCKET_Magazine"].translation.copy()
            cam_data.type = "PERSP"
            cam_data.lens = 40.0
            aim(well + up * 0.24 - left * 0.34 - rear * 0.05, well - rear * 0.02)
        scene.render.filepath = os.path.join(OUT, "preview_%s_%g_%s.png" % (clip, frame, view))
        bpy.ops.render.render(write_still=True)
        print("ASH12_PREVIEW", scene.render.filepath)

    for obj in [o for o in scene.objects if o.type == "LIGHT"]:
        bpy.data.objects.remove(obj, do_unlink=True)

print("ASH12_PREVIEW_DONE")
