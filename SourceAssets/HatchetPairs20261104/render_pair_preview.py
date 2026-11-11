"""Authoring preview of the hatchet pairs / lone off-hand blade from the game camera (vertical FOV 75, 16:9).

blender -b --factory-startup --python render_pair_preview.py -- <poses.json> <out_dir> [width]
poses.json: {"poses": {name: {"bones": {bone: [px,py,pz,qw,qx,qy,qz,sx,sy,sz]}, "weapon_r": [...], "weapon_r_kind":
"hatchet"|"kukri", "weapon_l": [...], "weapon_l_kind": ..., "hide_right": bool}}}
Same camera, light, skin and bone mapping as HatchetEquip20261101/render_hatchet_preview.py (V7 FrostArms editable rig, the
in-game skeleton/bind).  Weapons: SM_TacticalHatchet (OneHandAxe20261101/TacticalHatchet_Editable.blend) and SM_Kukri
(Kukri20261020/Kukri_Editable.blend), both in the shared grip frame.  hide_right masks the vertices the right arm chain
(clavicle_r and below) dominates -- the runtime hides that arm for the lone off-hand blade.
"""
import bpy, json, math, sys
from pathlib import Path
from mathutils import Matrix, Quaternion, Vector

ROOT = Path(r"D:\FPS3D\FPSGAME\SourceAssets")
argv = sys.argv[sys.argv.index('--') + 1:]
POSES = json.loads(Path(argv[0]).read_text('utf-8'))
OUT = Path(argv[1]).resolve(); OUT.mkdir(parents=True, exist_ok=True)
WIDTH = int(argv[2]) if len(argv) > 2 else 640
ARMS = ROOT / 'ModularOutfit20260925' / 'BarePalmV7' / 'Editable' / 'FrostArms_BareArmsV7.blend'
DUMP = json.loads((ROOT / 'Kukri20261020' / 'Work' / 'ue_sword_dump.json').read_text('utf-8'))
SOURCES = {'hatchet': (ROOT / 'OneHandAxe20261101' / 'TacticalHatchet_Editable.blend', 'SM_TacticalHatchet'),
           'kukri': (ROOT / 'Kukri20261020' / 'Kukri_Editable.blend', 'SM_Kukri')}
C = Matrix.Diagonal(Vector((1, -1, 1)))
FALLBACK = {'kukri': {'BaseColor': ('T_Kukri_BaseColor.png', None), 'Normal': ('T_Kukri_Normal.png', None),
                      'Roughness': ('T_Kukri_ORM.png', 'G'), 'Metallic': ('T_Kukri_ORM.png', 'B')}}


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

# One object per weapon kind and hand.
weapons = {}
for kind, (blend, obj) in SOURCES.items():
    before = set(bpy.data.images)
    with bpy.data.libraries.load(str(blend)) as (src, dst):
        dst.objects = [obj]
    # Appended images keep paths relative to their own .blend ("//Textures/..."): resolve them there, or the weapon
    # renders with the missing-texture magenta.
    for img in set(bpy.data.images) - before:
        if img.filepath.startswith('//') and not img.packed_file:
            img.filepath = str((blend.parent / img.filepath[2:]).resolve())
            img.reload()
    base = dst.objects[0]
    # Kukri_Editable.blend still points at the retired Fab cache: use the project's own maps (UE ORM packing).
    if kind in FALLBACK:
        for slot in base.material_slots:
            tree = slot.material.node_tree if slot.material else None
            for node in list(tree.nodes) if tree else []:
                if node.type != 'TEX_IMAGE' or not node.image or node.image.packed_file or Path(node.image.filepath).exists():
                    continue
                key = next((k for k in FALLBACK[kind] if k in node.image.name), None)
                if key is None:
                    continue
                file, channel = FALLBACK[kind][key]
                node.image = bpy.data.images.load(str(blend.parent / 'Textures' / file), check_existing=True)
                if key != 'BaseColor':
                    node.image.colorspace_settings.name = 'Non-Color'
                if channel:
                    split = tree.nodes.new('ShaderNodeSeparateColor')
                    # (linking into an occupied input replaces its old link)
                    for target in [l.to_socket for l in tree.links if l.from_node == node]:
                        tree.links.new(split.outputs['Green' if channel == 'G' else 'Blue'], target)
                    tree.links.new(node.outputs['Color'], split.inputs['Color'])
    for side in ('r', 'l'):
        o = base if side == 'r' else base.copy()
        if side == 'l':
            o.data = base.data
        scene.collection.objects.link(o)
        o.hide_render = True
        weapons[(kind, side)] = o

# Right-arm mask (lone off-hand blade): vertices whose dominant weight belongs to the right arm chain.
right_bones = set()
def collect(b):
    right_bones.add(b.name)
    for c in b.children:
        collect(c)
collect(rig.data.bones['clavicle_r'])
group_bones = {g.index: g.name for g in skin.vertex_groups}
mask_group = skin.vertex_groups.new(name='PreviewRightArm')
for v in skin.data.vertices:
    weights = {group_bones[g.group]: g.weight for g in v.groups if g.group in group_bones}
    total = sum(weights.values())
    right = sum(w for n, w in weights.items() if n in right_bones)
    if total > 0 and right / total > .5:
        mask_group.add([v.index], 1.0, 'REPLACE')
mask = skin.modifiers.new('PreviewHideRight', 'MASK')
mask.vertex_group = mask_group.name
mask.invert_vertex_group = True
mask.show_render = False

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
cam.matrix_world = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0))).to_4x4()

for name, pose in POSES['poses'].items():
    world = {n: canonical(pose['bones'][n]) @ correction[n] for n in rest if n in pose['bones']}
    for bone in rig.pose.bones:
        if bone.name not in world:
            continue
        parent = world[bone.parent.name] if bone.parent and bone.parent.name in world else Matrix.Identity(4)
        bone.matrix_basis = local_rest[bone.name].inverted() @ parent.inverted() @ world[bone.name]
    mask.show_render = bool(pose.get('hide_right'))
    for (kind, side), o in weapons.items():
        key = 'weapon_' + side
        shown = key in pose and pose.get(key + '_kind') == kind
        o.hide_render = not shown
        if shown:
            o.matrix_world = canonical(pose[key], unit_scale=True)
    bpy.context.view_layer.update()
    scene.render.filepath = str(OUT / (name + '.png'))
    bpy.ops.render.render(write_still=True)
    print('PAIR_PREVIEW ' + name, flush=True)
