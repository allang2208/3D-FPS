"""Candidate: slide the left hand up the hilt and solve a bent left elbow.

Keeps the sword, the right arm, the shoulder and the hand's grip orientation
unchanged; only the left hand's contact point along the hilt and the left
arm's joint positions change. Renders the current pose against the candidate.
"""
import bpy, math, sys
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).parent
sys.path.insert(0, str(P))
import shoulder_transport as st

BLEND = P / 'AzureRunesword_ChargedShoulderV44.blend'
OUT = P / 'ReviewBent'
OUT.mkdir(exist_ok=True)
FPS = 480.0
SHOTS = ((('HeavyCharge', 2.00), 0.080), (('HeavyCharge', 0.65), 0.080),
         (('HeavyCharge', 0.35), 0.050), (('HeavyRelease', 0.60), 0.050))

bpy.ops.wm.open_mainfile(filepath=str(BLEND))
scene = bpy.context.scene
rig = bpy.data.objects['SK_RuneSword_Rig']
arms = bpy.data.objects['SK_Manny_Arms_Export']
sword = bpy.data.objects['RuneSword_Blade']
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
for ob in scene.objects:
    keep = ob in (rig, arms, sword)
    ob.hide_render = not keep
    try:
        ob.hide_set(not keep)
    except RuntimeError:
        pass

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 820
scene.render.resolution_y = 620
scene.render.image_settings.file_format = 'PNG'
scene.view_settings.view_transform = 'AgX'
world = bpy.data.worlds.new('BentWorld')
scene.world = world
world.use_nodes = True
world.node_tree.nodes['Background'].inputs[0].default_value = (.28, .32, .38, 1)
world.node_tree.nodes['Background'].inputs[1].default_value = 1.1
for name, loc, energy, size in [('Key', (-.5, -.4, 1.1), 130, 1.3),
                                ('Fill', (.8, .4, .6), 80, 1.2),
                                ('Rim', (-.3, 1.2, .4), 100, .9)]:
    light = bpy.data.lights.new(name, 'AREA')
    light.energy = energy
    light.shape = 'DISK'
    light.size = size
    ob = bpy.data.objects.new(name, light)
    scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = (Vector((0, .2, .1)) - ob.location).to_track_quat('-Z', 'Y').to_euler()
data = bpy.data.cameras.new('BentCamera')
camera = bpy.data.objects.new(data.name, data)
scene.collection.objects.link(camera)
scene.camera = camera
data.clip_start = .002


def swing(a, b):
    return a.rotation_difference(b)


def pose_bent(pose, slide):
    """Slide the left hand up the hilt and re-solve the left arm's joints."""
    S = pose['upperarm_l'].translation
    E = pose['lowerarm_l'].translation
    W = pose['hand_l'].translation
    hilt = (pose['WPN_root'].to_quaternion() @ Vector((0, 0, 1))).normalized()
    W2 = W + hilt * slide
    a = (E - S).length
    b = (W - E).length
    d = (W2 - S).length
    u = (W2 - S).normalized()
    if d > a + b - 1e-4:
        W2 = S + u * (a + b - 1e-4)
        d = a + b - 1e-4
    cos_alpha = max(-1.0, min(1.0, (a * a + d * d - b * b) / (2 * a * d)))
    pole = (E - S) - u * ((E - S).dot(u))
    if pole.length < 1e-5:
        pole = Vector((0, 0, -1)) - u * u.z
    pole.normalize()
    alpha = math.acos(cos_alpha)
    E2 = S + (u * math.cos(alpha) + pole * math.sin(alpha)) * a
    updated = dict(pose)
    # Upper arm keeps its roll relative to the clavicle, rotated by the minimal
    # swing from the authored direction to the solved one.
    up_rot = swing((E - S).normalized(), (E2 - S).normalized()) @ pose['upperarm_l'].to_quaternion()
    updated['upperarm_l'] = Matrix.LocRotScale(S, up_rot, pose['upperarm_l'].decompose()[2])
    # Forearm keeps its roll relative to the hand, so the wrist is untouched.
    fore_rot = swing((W - E).normalized(), (W2 - E2).normalized()) @ pose['lowerarm_l'].to_quaternion()
    updated['lowerarm_l'] = Matrix.LocRotScale(E2, fore_rot, pose['lowerarm_l'].decompose()[2])
    # The hand slid along the hilt; its orientation (the grip) is unchanged.
    updated['hand_l'] = Matrix.LocRotScale(W2, pose['hand_l'].to_quaternion(),
                                           pose['hand_l'].decompose()[2])
    return updated, {'elbow_before': math.degrees(((E - S).normalized())
                                                  .angle((W - E).normalized())),
                     'elbow_after': math.degrees(((E2 - S).normalized())
                                                 .angle((W2 - E2).normalized())),
                     'wrist_before': (W - E).length, 'slide': slide,
                     'shoulder_wrist_m': d}


for (clip, seconds), slide in SHOTS:
    action = bpy.data.actions['A_RuneSword_' + clip]
    rig.animation_data.action = action
    rig.animation_data.action_slot = action.slots[0]
    f = seconds * FPS
    scene.frame_set(int(f), subframe=f - int(f))
    bpy.context.view_layer.update()
    pose = {b.name: b.matrix.copy() for b in rig.pose.bones}
    tag = '%s_%03dms' % (clip, round(seconds * 1000))
    for label in ('current', 'bent'):
        scene.frame_set(int(f), subframe=f - int(f))
        bpy.context.view_layer.update()
        if label == 'bent':
            updated, stats = pose_bent(pose, slide)
            for name in ('upperarm_l', 'lowerarm_l', 'hand_l'):
                rig.pose.bones[name].matrix = updated[name]
                bpy.context.view_layer.update()
            print('BENT', tag, stats, flush=True)
        camera.location = (0, 0, 0)
        camera.rotation_euler = Vector((0.02, 1.0, -0.06)).to_track_quat('-Z', 'Y').to_euler()
        data.type = 'PERSP'
        data.lens = 17
        scene.render.filepath = str(OUT / ('%s_%s_fp.png' % (tag, label)))
        bpy.ops.render.render(write_still=True)
        S = rig.pose.bones['upperarm_l'].matrix.translation
        E = rig.pose.bones['lowerarm_l'].matrix.translation
        W = rig.pose.bones['hand_l'].matrix.translation
        centre = (S + 2 * E + W) / 4
        camera.location = centre + Vector((-.55, -.6, .35)).normalized() * .6
        camera.rotation_euler = (Vector(centre) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        data.type = 'ORTHO'
        data.ortho_scale = .5
        scene.render.filepath = str(OUT / ('%s_%s_joint.png' % (tag, label)))
        bpy.ops.render.render(write_still=True)
    print('SHOT', tag, flush=True)
print('PROBE_BENT_DONE', flush=True)
