"""Authoring preview of the dual-kukri hold from the game camera (vertical FOV 75, 16:9, viewmodel at the camera).

blender -b --factory-startup --python render_idle.py -- <poses.json> <out_dir> [width] [--blend] [--skin] [--norender] [--hunter]
poses.json: {"poses": {name: {"bones": {bone: [p, q, s]}, "kukri_r": [...], "kukri_l": [...]}}}
Transforms are UE mesh component space (cm).  --skin also writes <name>_skin.npz: the evaluated (posed, skinned)
arm vertices in UE mesh space (cm) and each vertex's dominant deform bone, for contact checks (contact_dual.py).  Same skin/camera set-up as Kukri20261020/render_preview.py
(V7 FrostArms editable rig, same skeleton/bind as the in-game SK_FrostSword_Arms; the in-game skin is V9).
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

P = Path(__file__).resolve().parent
KUKRI = P.parent / 'Kukri20261020'
argv = sys.argv[sys.argv.index('--') + 1:]
POSES = json.loads(Path(argv[0]).read_text('utf-8'))
OUT = Path(argv[1]).resolve(); OUT.mkdir(parents=True, exist_ok=True)   # absolute: Blender resolves relative paths elsewhere
WIDTH = int(argv[2]) if len(argv) > 2 and argv[2].isdigit() else 960
ARMS = Path(r"D:\FPS3D\FPSGAME\SourceAssets\ModularOutfit20260925\BarePalmV7\Editable\FrostArms_BareArmsV7.blend")
DUMP = json.loads((KUKRI / 'Work' / 'ue_sword_dump.json').read_text('utf-8'))
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

with bpy.data.libraries.load(str(KUKRI / 'Kukri_Editable.blend')) as (src, dst):
    dst.objects = ['SM_Kukri']
kukri_r = dst.objects[0]
scene.collection.objects.link(kukri_r)
kukri_l = kukri_r.copy()
scene.collection.objects.link(kukri_l)
# The editable blend's textures point at the cleared Fab cache; give both blades a plain steel/wood look.
steel = bpy.data.materials.new('PreviewSteel'); steel.use_nodes = True
sb = steel.node_tree.nodes.get('Principled BSDF')
sb.inputs['Base Color'].default_value = (.55, .56, .58, 1); sb.inputs['Metallic'].default_value = .9; sb.inputs['Roughness'].default_value = .35
for ob in (kukri_r, kukri_l):
    ob.data = ob.data.copy()
    ob.data.materials.clear(); ob.data.materials.append(steel)
# --hunter (R16): the 猎手刀身 long blade module over both kukris (same grip frame; KukriHunterBlade20261027).
if '--hunter' in argv:
    HUNTER = KUKRI.parent / 'KukriHunterBlade20261027' / 'Kukri_Hunter_Editable.blend'
    with bpy.data.libraries.load(str(HUNTER)) as (src, dst):
        dst.objects = ['SM_Kukri_Blade_Hunter']
    hunter = dst.objects[0]
    rel = kukri_r.matrix_world.inverted() @ hunter.matrix_world
    for ob in (kukri_r, kukri_l):
        h = hunter.copy(); h.data = hunter.data.copy()
        h.data.materials.clear(); h.data.materials.append(steel)
        scene.collection.objects.link(h)
        h.parent = ob; h.matrix_parent_inverse = Matrix.Identity(4); h.matrix_basis = rel

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
bg.inputs['Color'].default_value = (.10, .12, .15, 1)
bg.inputs['Strength'].default_value = 1.0
sun = bpy.data.objects.new('Sun', bpy.data.lights.new('Sun', 'SUN'))
sun.data.energy = 3.5
sun.rotation_euler = (math.radians(50), math.radians(-20), math.radians(30))
scene.collection.objects.link(sun)
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 10, -1.62))
ground = bpy.context.active_object
gm = bpy.data.materials.new('Ground'); gm.use_nodes = True
gm.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (.16, .15, .13, 1)
ground.data.materials.append(gm)

cam = bpy.data.objects.new('GameCamera', bpy.data.cameras.new('GameCamera'))
scene.collection.objects.link(cam)
scene.camera = cam
cam.data.sensor_fit = 'VERTICAL'
cam.data.angle_y = math.radians(75)
cam.data.clip_start = .02
cam.location = (0, 0, 0)
cam.rotation_euler = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0))).to_euler()

# Dominant deform bone per skin vertex (contact checks group vertices by side and hand/forearm).
GROUPS = [g.name for g in skin.vertex_groups]
DOMINANT = [max(v.groups, key=lambda e: e.weight).group if len(v.groups) else -1 for v in skin.data.vertices]

for name, pose in POSES['poses'].items():
    world = {n: canonical(pose['bones'][n]) @ correction[n] for n in rest if n in pose['bones']}
    for bone in rig.pose.bones:
        if bone.name not in world:
            continue
        parent = world[bone.parent.name] if bone.parent and bone.parent.name in world else Matrix.Identity(4)
        bone.matrix_basis = local_rest[bone.name].inverted() @ parent.inverted() @ world[bone.name]
    kukri_r.matrix_world = canonical(pose['kukri_r'], unit_scale=True)
    kukri_l.matrix_world = canonical(pose['kukri_l'], unit_scale=True)
    # Optional detail camera: {"loc": camera-space cm, "look": camera-space cm, "fov": vertical deg}.
    view = pose.get('camera')
    if view:
        b = lambda v: Vector((v[1], v[0], v[2])) * .01   # camera space (x fwd, y right, z up) -> Blender
        cam.location = b(view['loc'])
        cam.rotation_euler = (b(view['look']) - cam.location).to_track_quat('-Z', 'Y').to_euler()
        cam.data.angle_y = math.radians(view.get('fov', 75))
    else:
        cam.location = (0, 0, 0)
        cam.rotation_euler = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0))).to_euler()
        cam.data.angle_y = math.radians(75)
    bpy.context.view_layer.update()
    if '--skin' in argv:
        import numpy as np
        dg = bpy.context.evaluated_depsgraph_get()
        ev = skin.evaluated_get(dg)
        me = ev.to_mesh()
        mw = skin.matrix_world
        X = np.array([tuple(C @ (mw @ v.co) * 100.0) for v in me.vertices])
        ev.to_mesh_clear()
        np.savez_compressed(OUT / (name + '_skin.npz'), X=X, bone=DOMINANT, names=np.array(GROUPS))
    if '--norender' not in argv:
        scene.render.filepath = str(OUT / (name + '.png'))
        bpy.ops.render.render(write_still=True)
    print('DUAL_PREVIEW ' + name, flush=True)
    if '--blend' in argv and name.endswith('_eye'):
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT / (name + '.blend')), copy=True)
