"""Authoring preview from the game camera (vertical FOV 75, 16:9, viewmodel at the camera).

blender -b --factory-startup --python render_preview.py -- <poses.json> <out_dir> [width]
poses.json: {"poses": {name: {"bones": {bone: [px,py,pz,qw,qx,qy,qz,sx,sy,sz]}, "kukri": [...]}}}
Transforms are UE mesh component space (cm).  Uses the V7 FrostArms editable rig for the skin
(same skeleton/bind as the in-game SK_FrostSword_Arms; the in-game skin is V9).
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).resolve().parent
argv = sys.argv[sys.argv.index('--') + 1:]
POSES = json.loads(Path(argv[0]).read_text('utf-8'))
OUT = Path(argv[1]); OUT.mkdir(parents=True, exist_ok=True)
WIDTH = int(argv[2]) if len(argv) > 2 else 640
ARMS = Path(r"D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BarePalmV7\Editable\FrostArms_BareArmsV7.blend")
DUMP = json.loads((P / 'Work' / 'ue_sword_dump.json').read_text('utf-8'))
C = Matrix.Diagonal(Vector((1, -1, 1)))

def ue(v):
    p = Vector(v[0:3]); q = Quaternion(v[3:7]); s = Vector(v[7:10])
    return p, q, s

def canonical(v, unit_scale=False):
    p, q, s = ue(v)
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

with bpy.data.libraries.load(str(P / 'Kukri_Editable.blend')) as (src, dst):
    dst.objects = ['SM_Kukri']
kukri = dst.objects[0]
scene.collection.objects.link(kukri)

skin_mat = bpy.data.materials.new('PreviewSkin')
skin_mat.use_nodes = True
bsdf = skin_mat.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = (.62, .42, .32, 1)
bsdf.inputs['Roughness'].default_value = .55
skin.data.materials.clear()
skin.data.materials.append(skin_mat)

scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x, scene.render.resolution_y = WIDTH, WIDTH * 9 // 16
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
scene.world = bpy.data.worlds.new('PreviewSky')
scene.world.use_nodes = True
bg = next(nd for nd in scene.world.node_tree.nodes if nd.type == 'BACKGROUND')
bg.inputs['Color'].default_value = (.32, .38, .45, 1)
bg.inputs['Strength'].default_value = 1.0
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
sun.data.energy = 3.5
sun.rotation_euler = (math.radians(50), math.radians(-20), math.radians(30))
scene.collection.objects.link(sun)
# Ground plane 1.6 m below the eye for horizon reference.
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 10, -1.62))
ground = bpy.context.active_object
gm = bpy.data.materials.new('Ground'); gm.use_nodes = True
gm.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (.35, .32, .28, 1)
ground.data.materials.append(gm)

cam = bpy.data.objects.new('GameCamera', bpy.data.cameras.new('GameCamera'))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.sensor_fit = 'VERTICAL'
cam.data.angle_y = math.radians(75)
cam.data.clip_start = .02
cam.location = (0, 0, 0)
cam.rotation_euler = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0))).to_euler()

for name, pose in POSES['poses'].items():
    world = {n: canonical(pose['bones'][n]) @ correction[n] for n in rest if n in pose['bones']}
    for bone in rig.pose.bones:
        if bone.name not in world:
            continue
        parent = world[bone.parent.name] if bone.parent and bone.parent.name in world else Matrix.Identity(4)
        bone.matrix_basis = local_rest[bone.name].inverted() @ parent.inverted() @ world[bone.name]
    kukri.matrix_world = canonical(pose['kukri'], unit_scale=True)
    bpy.context.view_layer.update()
    scene.render.filepath = str(OUT / (name + '.png'))
    bpy.ops.render.render(write_still=True)
    print('KUKRI_PREVIEW ' + name, flush=True)
