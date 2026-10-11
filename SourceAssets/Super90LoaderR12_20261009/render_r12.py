"""Authoring frames from the reconstructed Super90 hip camera (not a game capture).

Blender background on Super90_Speedloader_R12.blend. Writes PNGs to
D:/FPS3D/test/super90_r12_diag/<tag>/ for qualitative authoring review only.
Usage: blender -b -P render_r12.py -- <tag> <action> <frame> [<frame> ...]
"""
import bpy, sys, json, math, os
from pathlib import Path
from mathutils import Matrix, Vector, Quaternion
O = Path(__file__).parent; S = O.parent
args = sys.argv[sys.argv.index('--') + 1:]
tag, action = args[0], args[1]; frames = [int(a) for a in args[2:]]
OUT = Path('D:/FPS3D/test/super90_r12_diag') / tag; OUT.mkdir(parents=True, exist_ok=True)
live = {}
if os.environ.get('R12_LIVE') == '1':
    g = {'__file__': str(O / 'r12_core.py')}
    for part in ('r12_core.py', 'skin_arm.py', 'r12_motion.py'):
        exec(compile((O / part).read_text(encoding='utf-8'), str(O / part), 'exec'), g)
    cycle = action.endswith('cycle')
    count = 1 if cycle else int(action.split('_')[-1]); empty = 'empty' in action
    family = os.environ.get('R12_FAMILY', 'base')
    live = {f: g['cycle_pose'](f, family) if cycle else g['pose'](f, count, empty, family)[0] for f in frames}
    if not cycle:
        detail=[]
        for f in range(g['duration'](count,empty)+1):
            p=g['pose'](f,count,empty,family)[0]
            detail.append(dict(frame=f,stats=p['_stats'],camera={n:list(g['cam'](p[n].translation)) for n in ('upperarm_l','lowerarm_l','hand_l')}))
        (OUT/'arm_details.json').write_text(json.dumps(detail,indent=2))
    (OUT / 'pose_details.json').write_text(json.dumps({f:{n:[list(row) for row in m] for n,m in p.items() if n != '_stats'} for f,p in live.items()}))
bpy.ops.wm.open_mainfile(filepath=str(O / 'Super90_Speedloader_R12.blend'))
scene = bpy.context.scene; rig = bpy.data.objects['SK_Super90']
rig.animation_data.action = bpy.data.actions[action]; rig.animation_data.action_slot = rig.animation_data.action.slots[0]
keep = {'SK_Super90', 'Super90_V7_M4_BareArmsV6', 'Super90_body', 'Super90_bolt', 'Super90_loading_gate', 'Super90_trigger',
        'SM_Super90_LoaderGuide', 'SpeedloaderTube', 'SpeedloaderPlunger'}
for ob in scene.objects:
    vis = ob.name in keep
    ob.hide_render = not vis; ob.hide_set(not vis)
guide = bpy.data.objects['SM_Super90_LoaderGuide']
if not any(m.type == 'ARMATURE' for m in guide.modifiers):
    vg = guide.vertex_groups.new(name='WPN_root'); vg.add(list(range(len(guide.data.vertices))), 1., 'REPLACE')
    guide.parent = rig; guide.matrix_parent_inverse = Matrix.Identity(4); guide.matrix_basis = Matrix.Identity(4)
    mod = guide.modifiers.new('Socket', 'ARMATURE'); mod.object = rig
cam_data = json.loads((S / 'Super90LoaderRepair20261008/author_geometry_r3.json').read_text())['camera']
CQ = Quaternion(cam_data['rotation']); CP = Vector(cam_data['location'])
Sinv = Matrix.Diagonal((.01, -.01, .01))
def world_dir(c): return (Sinv @ (CQ.inverted() @ Vector(c))).normalized()
eye = Sinv @ (CQ.inverted() @ (-CP))
fwd, right, up = world_dir((1, 0, 0)), world_dir((0, 1, 0)), world_dir((0, 0, 1))
right = fwd.cross(up).normalized() if fwd.cross(up).dot(right) > 0 else right
up = right.cross(fwd).normalized()
rot = Matrix((right, up, -fwd)).transposed()
camd = bpy.data.cameras.new('GameHip'); camd.sensor_fit = 'VERTICAL'; camd.angle_y = math.radians(75); camd.clip_start = .01
cam = bpy.data.objects.new('GameHip', camd); scene.collection.objects.link(cam)
cam.matrix_world = rig.matrix_world @ Matrix.LocRotScale(eye, rot.to_quaternion(), Vector((1, 1, 1)))
scene.camera = cam
scene.render.engine = 'BLENDER_WORKBENCH'; scene.render.resolution_x = 1280; scene.render.resolution_y = 720
shading = scene.display.shading; shading.light = 'STUDIO'; shading.color_type = 'MATERIAL'
shading.show_cavity = True; shading.cavity_type = 'BOTH'; shading.show_shadows = False
try: shading.show_object_outline = True
except Exception: pass
scene.render.film_transparent = False
for f in frames:
    scene.frame_set(f)
    if live:
        rig.animation_data_clear()
        p = live[f]
        for b in rig.pose.bones:
            n = b.name; par = b.parent.name if b.parent else None
            b.matrix_basis = g['rest'][n].inverted() @ g['rest'][par] @ p[par].inverted() @ p[n] if par else g['rest'][n].inverted() @ p[n]
    count = int(action.split('_')[-1]) if not action.endswith('cycle') else 0
    for n in ('SpeedloaderTube','SpeedloaderPlunger'):
        bpy.data.objects[n].hide_render = count == 0 or not 74 <= f <= 90 + 4 * (count - 1) + 13
    bpy.context.view_layer.update()
    scene.render.filepath = str(OUT / f'{action}_{f:03d}.png')
    bpy.ops.render.render(write_still=True)
print('R12_RENDERED', tag, action, frames, flush=True)
