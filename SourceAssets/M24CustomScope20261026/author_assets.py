"""Prepare the selected M24 and its attributed native animation source.

Asset preparation only: no gameplay registration or existing weapon replacement.
Run with Blender --background --factory-startup --python author_assets.py.
"""
import json
import sys
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

O = Path(__file__).resolve().parent
X = O / 'Exports'
X.mkdir(exist_ok=True)
(X / 'Parts').mkdir(exist_ok=True)
(X / 'Animations').mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(O / 'Donor/Source/source/arms@sniper.fbx'))
s = bpy.context.scene
s.render.fps = 30
s.frame_set(1)
donor = {o.name: o for o in s.objects}
dr = donor['Armature']
I = Matrix.Identity(4)

def rigid(m):
    p, q, _ = m.decompose()
    return Matrix.LocRotScale(p, q, Vector((1, 1, 1)))

def rows(m):
    return [list(row) for row in m]

rest = {'root': I.copy()}
parent = {'root': None}
lengths = {'root': .04}
for b in dr.data.bones:
    rest[b.name] = rigid(dr.matrix_world @ b.matrix_local)
    parent[b.name] = b.parent.name if b.parent else 'root'
    lengths[b.name] = max(.005, b.length * .01)
parts = {
    'base': 'WPN_root',
    'boltrear': 'WPN_BoltCarrier',
    'bolt': 'WPN_BoltHandle',
    'cheekrest': 'WPN_CheekRest',
    'trigger': 'WPN_Trigger',
    'clip': 'WPN_Magazine',
    'bullet': 'WPN_Cartridge',
    'silencer': 'WPN_Suppressor',
}
source_for_bone = {'WPN_root': 'sniper', **{b: n for n, b in parts.items() if n != 'base'}}
parents = {
    'WPN_root': 'root', 'WPN_BoltCarrier': 'WPN_root',
    'WPN_BoltHandle': 'WPN_BoltCarrier', 'WPN_CheekRest': 'WPN_root',
    'WPN_Trigger': 'WPN_root', 'WPN_Magazine': 'WPN_root',
    'WPN_Cartridge': 'WPN_Magazine', 'WPN_Suppressor': 'WPN_root',
}
for bone, name in source_for_bone.items():
    rest[bone] = rigid(donor[name].matrix_world)
    parent[bone] = parents[bone]
    lengths[bone] = .025
samples = []
for f in range(1, 202):
    s.frame_set(f)
    row = {'root': I.copy()}
    row.update({b.name: rigid(dr.matrix_world @ b.matrix) for b in dr.pose.bones})
    row.update({bone: rigid(donor[name].matrix_world) for bone, name in source_for_bone.items()})
    samples.append(row)
s.frame_set(1)
donor_base_matrix = donor['base'].matrix_world.copy()
donor_part_matrices = {n: donor[n].matrix_world.copy() for n in parts}
donor_vertices = {n: [v.co.copy() for v in donor[n].data.vertices] for n in parts}

# Preserve the supplied native skin as an explicitly named source asset.
# The project V9 hand is not replaced or registered by this import batch.
arm = donor['armmesh'].copy()
arm.data = donor['armmesh'].data.copy()
s.collection.objects.link(arm)
arm.name = 'M24_SourceNativeArms'
arm.data.transform(donor['armmesh'].matrix_world)
arm.parent = None
arm.matrix_world = I
arm.modifiers.clear()
arm.animation_data_clear()
for m in list(arm.data.materials):
    m.name = 'M24_SourceArms'
for obj in list(donor.values()):
    bpy.data.objects.remove(obj, do_unlink=True)

before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(O / 'Original/Source/source/M24 Custom Scope.fbx'), use_anim=False)
imported = [o for o in bpy.data.objects if o not in before]
custom = {o.name: o for o in imported}
C = donor_base_matrix @ custom['base'].matrix_world.inverted()
registration = {}
meshes = []
mat_names = {
    'sniper': 'M24_Body', 'Scope.002': 'M24_Scope',
    'ScopeGlass.002': 'M24_ScopeGlass', 'Plexiglass.002': 'M24_TopGlass',
}
scope_bones = {
    'MainScope_Lowpoly': 'WPN_Scope', 'ExtraScope_Lowpoly': 'WPN_TopSight',
    'Laser_Lowpoly': 'WPN_Laser', 'LaserHolder_Lowpoly': 'WPN_LaserMount',
    'ScopeGlass_Lowpoly': 'WPN_ScopeGlass', 'TopGlass_Lowpoly': 'WPN_TopGlass',
}
for obj in imported:
    if obj.type != 'MESH':
        continue
    name = obj.name
    if name in parts:
        source = donor_vertices[name]
        # Both downloads contain exactly the same eight original rifle meshes.
        # Their object offsets differ in the static remix; restore their native
        # mechanical pivots instead of treating the remix's scale as metres.
        if len(source) != len(obj.data.vertices):
            raise RuntimeError('The source part topology changed: ' + name)
        delta = max((v.co - source[i]).length for i, v in enumerate(obj.data.vertices))
        if delta > 1e-5:
            raise RuntimeError('A source part needs a new registration: ' + name)
        transform = donor_part_matrices[name]
        bone = parts[name]
        registration[name] = {'source_vertex_delta': delta, 'bone': bone}
    else:
        transform = C @ obj.matrix_world
        bone = scope_bones[name]
        rest[bone] = rigid(transform)
        parent[bone] = 'WPN_root'
        lengths[bone] = .025
        for row in samples:
            row[bone] = row['WPN_root'] @ rest['WPN_root'].inverted() @ rest[bone]
    obj.data.transform(transform)
    obj.parent = None
    obj.matrix_world = I
    obj.modifiers.clear()
    obj.animation_data_clear()
    obj.vertex_groups.clear()
    obj.vertex_groups.new(name=bone).add(list(range(len(obj.data.vertices))), 1, 'REPLACE')
    for slot in obj.material_slots:
        if slot.material:
            old = slot.material.name
            for original, final in mat_names.items():
                if old == original or old == final or old.startswith(original + '.'):
                    slot.material.name = final
                    break
    obj.name = 'M24_' + name
    meshes.append(obj)
for obj in imported:
    if obj.type != 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)

# Rebind native armature and rigid mechanical nodes to one centimetre-safe FBX.
data = bpy.data.armatures.new('M24_SourceRig')
rig = bpy.data.objects.new('M24_SourceRig', data)
s.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
for name, m in rest.items():
    b = data.edit_bones.new(name)
    b.matrix = m
    b.length = lengths[name]
for name, p in parent.items():
    if p:
        data.edit_bones[name].parent = data.edit_bones[p]
bpy.ops.object.mode_set(mode='OBJECT')
for ob in [arm, *meshes]:
    ob.parent = rig
    ob.matrix_parent_inverse = I
    ob.matrix_basis = I
    ob.modifiers.new('M24 Native Skin', 'ARMATURE').object = rig
for p in rig.pose.bones:
    p.rotation_mode = 'QUATERNION'

def apply(row):
    for b in data.bones:
        p = parent[b.name]
        local_rest = rest[p].inverted() @ rest[b.name] if p else rest[b.name]
        local_pose = row[p].inverted() @ row[b.name] if p else row[b.name]
        rig.pose.bones[b.name].matrix_basis = local_rest.inverted() @ local_pose
    bpy.context.view_layer.update()

def select(objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]

def export(path, objects, anim=False):
    select(objects)
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True,
        object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False,
        use_armature_deform_only=False, axis_forward='-Z', axis_up='Y',
        apply_unit_scale=True, mesh_smooth_type='FACE', use_tspace=False,
        bake_anim=anim, bake_anim_use_nla_strips=False,
        bake_anim_use_all_actions=False, bake_anim_simplify_factor=0,
        bake_anim_step=1, path_mode='AUTO')

apply(samples[0])
rig.animation_data_clear()
export(X / 'SK_M24_CustomScope_SourceArms.fbx', [rig, arm, *meshes])
export(X / 'SK_M24_CustomScope_Weapon.fbx', [rig, *meshes])

# Static pieces keep a common assembly origin, so their native assembly is
# recovered with identity transforms rather than independently centring parts.
static_objects = []
for ob in meshes:
    copy = ob.copy()
    copy.data = ob.data.copy()
    s.collection.objects.link(copy)
    copy.parent = None
    copy.matrix_world = I
    copy.modifiers.clear()
    copy.vertex_groups.clear()
    copy.name = 'SM_' + ob.name
    export(X / 'Parts' / (copy.name + '.fbx'), [copy])
    static_objects.append(copy)
export(X / 'SM_M24_CustomScope.fbx', static_objects)
for ob in static_objects:
    bpy.data.objects.remove(ob, do_unlink=True)

clips = {
    'source_all': (1, 201, '完整原版时间轴'),
    'fire_cycle': (1, 50, '射击后抬栓、后拉、前推与闭锁'),
    'magazine_reload': (50, 98, '原版弹匣拆卸与重新装入'),
    'bolt_cycle': (98, 148, '原版第二段独立拉栓动作'),
    'source_148_180': (148, 180, '未命名原版摆动段，保留源语义'),
    'source_180_201': (180, 201, '未命名原版快速动作段，保留源语义'),
}
manifest = {'selected_model': '84b72eaf37a54ecb945017e3955455a0',
    'animation_source': 'b48999a250b2433da59f705c371a49b2',
    'fps': 30, 'source_frames': [1, 201], 'source_duration': 200 / 30,
    'static_remix_to_source': rows(C), 'part_registration': registration,
    'source_native_arms_only': True, 'v9_gameplay_adaptation': False,
    'runtime_registered': False, 'clips': {}, 'parts': [], 'materials': {}}
for ob in meshes:
    manifest['parts'].append({'name': ob.name, 'file': str(X / 'Parts' / ('SM_' + ob.name + '.fbx')),
        'bone': ob.vertex_groups[0].name, 'vertices': len(ob.data.vertices),
        'triangles': sum(len(p.vertices) - 2 for p in ob.data.polygons)})
for role, (start, end, purpose) in clips.items():
    rig.animation_data_create()
    action = bpy.data.actions.new('A_M24_' + role)
    rig.animation_data.action = action
    for frame in range(start, end + 1):
        s.frame_set(frame - start + 1)
        apply(samples[frame - 1])
        for pb in rig.pose.bones:
            pb.keyframe_insert('location', frame=s.frame_current, group=pb.name)
            pb.keyframe_insert('rotation_quaternion', frame=s.frame_current, group=pb.name)
            pb.keyframe_insert('scale', frame=s.frame_current, group=pb.name)
    s.frame_start = 1
    s.frame_end = end - start + 1
    path = X / 'Animations' / ('A_M24_' + role + '.fbx')
    export(path, [rig], anim=True)
    action.use_fake_user = True
    manifest['clips'][role] = {'file': str(path), 'source_frames': [start, end],
        'duration': (end - start) / 30, 'purpose': purpose}
    rig.animation_data.action = None

# Keep a working editable scene with the entire original animation assigned.
rig.animation_data.action = bpy.data.actions['A_M24_source_all']
s.frame_start = 1
s.frame_end = 201
s.frame_set(1)
select([rig, arm, *meshes])
sys.path.insert(0, str(O))
from bind_source_materials import bind
bind()
bpy.ops.wm.save_as_mainfile(filepath=str(O / 'M24_CustomScope_Native_Editable.blend'))
manifest['saved_blend'] = str(O / 'M24_CustomScope_Native_Editable.blend')
(O / 'authoring.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print('M24_AUTHORING_COMPLETE', len(meshes), 'parts;', len(clips), 'source clips')
