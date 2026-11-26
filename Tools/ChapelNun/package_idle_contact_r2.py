"""Editable native armature/garment animation source, without rendering."""
import json
from pathlib import Path
import bpy
from mathutils import Matrix, Vector, Quaternion

ROOT = Path(__file__).resolve().parents[2]
NUN = ROOT/'SourceAssets/ChapelNun20261115'
OUT = NUN/'IdleHandsFrontR2'
read = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
d = read(OUT/'authored.json')
body = read(NUN/'IdleBackReviewR2/InputsAfter/body.json')
robe = read(NUN/'IdleBackReviewR2/InputsAfter/robe.json')
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .01
scene.render.fps = d['rate']
scene.frame_start, scene.frame_end = 1, len(d['frames'])
names, parents = d['names'], d['parents']


def local(value):
    return Matrix.LocRotScale(Vector(value[:3]), Quaternion((value[6], *value[3:6])), Vector(value[7:]))


def fk(frame):
    out = [local(v) for v in frame]
    for i, p in enumerate(parents):
        if p >= 0:
            out[i] = out[p] @ out[i]
    return out


bind = fk(d['reference'])
armature = bpy.data.armatures.new('Kaitlin_Nun_Idle_Native')
rig = bpy.data.objects.new('Nun_Idle_HandsFront_Rig', armature)
scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for i, name in enumerate(names):
    bone = armature.edit_bones.new(name)
    bone.head = bind[i].translation
    bone.tail = bone.head + bind[i].to_3x3().col[0] * 2.0
    bone.align_roll(bind[i].to_3x3().col[2])
    if parents[i] >= 0:
        bone.parent = armature.edit_bones[names[parents[i]]]
bpy.ops.object.mode_set(mode='OBJECT')
rest = [armature.bones[n].matrix_local.copy() for n in names]


def material(name, color):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.)
    m.use_nodes = True
    shader = m.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1.)
    shader.inputs['Roughness'].default_value = .8
    return m


skin = material('AnimationSource_Skin', (.43, .25, .18))
cloth = material('AnimationSource_BlackHabit', (.018, .018, .019))
for data, name, mat in ((body, 'Nun_NativeBody', skin), (robe, 'Nun_NativeRobe', cloth)):
    geo = bpy.data.meshes.new(name)
    # Match the runtime's hidden inner/covered sections in this working source.
    hidden = {0, 1, 3, 7, 8, 9, 10, 14, 15, 16, 22, 23, 24} if data is body else {9}
    triangles = [t[::-1] for t, m in zip(data['triangles'], data['triangle_materials']) if m not in hidden]
    geo.from_pydata(data['positions'], [], triangles)
    geo.materials.append(mat)
    for polygon in geo.polygons:
        polygon.use_smooth = True
    obj = bpy.data.objects.new(name, geo)
    scene.collection.objects.link(obj)
    for b in data['bones']:
        obj.vertex_groups.new(name=b['name'])
    for vertex, weights in enumerate(data['weights']):
        for bone, weight in weights:
            obj.vertex_groups[bone].add([vertex], weight, 'REPLACE')
    obj.parent = rig
    obj.modifiers.new('NativeSkin', 'ARMATURE').object = rig

# Pose matrices are converted by the rest-basis difference. The bone's visual
# length/roll in Blender never changes the UE-native local animation channels.
for k, frame in enumerate(d['frames']):
    world = fk(frame)
    desired = [world[i] @ bind[i].inverted() @ rest[i] for i in range(len(names))]
    for i, name in enumerate(names):
        pb = rig.pose.bones[name]
        parent = parents[i]
        relative_rest = rest[parent].inverted() @ rest[i] if parent >= 0 else rest[i]
        relative_pose = desired[parent].inverted() @ desired[i] if parent >= 0 else desired[i]
        pb.rotation_mode = 'QUATERNION'
        pb.matrix_basis = relative_rest.inverted() @ relative_pose
        if k not in (0, len(d['frames'])-1) and all(abs(v-w) < 1e-8 for v, w in zip(frame[i], d['frames'][0][i])):
            continue
        for channel in ('location', 'rotation_quaternion', 'scale'):
            pb.keyframe_insert(data_path=channel, frame=k+1, group=name)
    if k % 60 == 0:
        print('NUN_SOURCE_FRAME', k, flush=True)
rig.animation_data.action.name = 'Nun_HandsFront_QuietBreathing_12s'
rig['source'] = d['source']
rig['native_animation_asset'] = '/Game/Characters/ChapelNun20261115/Animations/A_Nun_Idle_HandsFront_R2'
rig['cloth_note'] = 'Production retains existing UE Chaos skirt and secondary cuff motion; this source contains skeletal animation only.'
text = bpy.data.texts.new('Native_Animation_Contract.json')
text.write(json.dumps({k: d[k] for k in ('source', 'source_idle', 'duration', 'rate', 'hand_targets_cm', 'root_motion', 'runtime_tested')}, indent=2))
image = bpy.data.images.load(str(OUT/'standing_reference.png'))
image.pack()
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Nun_HandsFront_Idle_R2.blend'))
print('NUN_IDLE_BLEND_SAVED', flush=True)
