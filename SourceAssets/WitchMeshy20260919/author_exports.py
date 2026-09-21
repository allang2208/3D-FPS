"""Package downloaded Meshy candidates into editable Blender sources and UE FBX.

Production only: no camera, rendering, test scene, or runtime acceptance.
"""
import bpy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RAW = ROOT / 'Meshy'
AUTHOR = ROOT / 'Authoring'
DELIVERY = ROOT / 'Delivery'
PLAN = json.loads((ROOT / 'motion_plan.json').read_text(encoding='utf-8'))


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 1.0
    bpy.context.scene.render.fps = 120


def downloaded(name, preferred):
    files = list((RAW / name / 'downloads').glob('*.glb'))
    for term in preferred:
        for path in files:
            if term in path.name:
                return path
    raise RuntimeError(f'No required GLB downloaded for {name}')


def curves(action):
    if hasattr(action, 'fcurves'):
        yield from action.fcurves
    else:
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag = strip.channelbag(slot)
                    if bag:
                        yield from bag.fcurves


def export_fbx(path, animated):
    bpy.ops.object.select_all(action='DESELECT')
    objects = [o for o in bpy.context.scene.objects if o.type in {'ARMATURE', 'MESH', 'EMPTY'}]
    for obj in objects:
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = next((o for o in objects if o.type == 'ARMATURE'), objects[0])
    bpy.ops.export_scene.fbx(filepath=str(path), use_selection=True,
        object_types={'ARMATURE', 'MESH', 'EMPTY'}, add_leaf_bones=False,
        use_armature_deform_only=False, bake_anim=animated,
        bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
        bake_anim_force_startend_keying=True, bake_anim_simplify_factor=0,
        axis_forward='-Y', axis_up='Z', apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_UNITS', mesh_smooth_type='FACE',
        path_mode='COPY', embed_textures=True)


def save_blend(path):
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(path))


def motion(name):
    action_plan = next(a for a in PLAN['actions'] if a['name'] == name)
    source = downloaded('animation_' + name, ['animation_glb'])
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(source))
    # glTF may park its action in an NLA track; bind that action directly so
    # retiming changes key time without retaining the old strip scale/range.
    for obj in bpy.context.scene.objects:
        data = obj.animation_data
        if not data:
            continue
        active = data.action
        slot = data.action_slot if active else None
        if not active:
            strip = next((s for t in data.nla_tracks for s in t.strips if s.action), None)
            if strip:
                active, slot = strip.action, strip.action_slot
        for track in list(data.nla_tracks):
            data.nla_tracks.remove(track)
        if active:
            data.action = active
            if slot:
                data.action_slot = slot
    actions = list(bpy.data.actions)
    if not actions:
        raise RuntimeError(f'No editable action in generated {name} file')
    # Read source key range in order to author the requested duration.
    start = min(float(a.frame_range[0]) for a in actions)
    end = max(float(a.frame_range[1]) for a in actions)
    duration = action_plan['target_duration_seconds']
    frames = round(duration * 120)
    scale = frames / (end - start)
    for index, action in enumerate(actions):
        action.name = 'A_Witch_' + name + (f'_{index}' if index else '')
        action['source_task'] = json.loads((RAW / ('animation_' + name) / 'task.json').read_text())['task_id']
        action['intended_loop'] = action_plan['loop']
        for curve in curves(action):
            for key in curve.keyframe_points:
                original = (key.co.x, key.handle_left.x, key.handle_right.x)
                key.co.x = (original[0] - start) * scale
                key.handle_left.x = (original[1] - start) * scale
                key.handle_right.x = (original[2] - start) * scale
            curve.update()
    scene = bpy.context.scene
    scene.frame_start = 0
    scene.frame_end = frames
    scene.frame_set(0)
    for event, seconds in action_plan.get('events_seconds', {}).items():
        scene.timeline_markers.new(event, frame=round(seconds * 120))
    scene['stage'] = 'Meshy generated motion with duration remap; contacts and appearance not tested'
    scene['source_seconds'] = (end - start) / 120
    scene['target_seconds'] = duration
    save_blend(AUTHOR / f'Witch_{name}_Candidate_v01.blend')
    export_fbx(DELIVERY / f'A_Witch_{name}_Candidate_v01.fbx', animated=True)
    return {'name': name, 'source': str(source.relative_to(ROOT)), 'target_seconds': duration,
            'source_seconds': (end - start) / 120, 'loop_intent': action_plan['loop'],
            'events_seconds': action_plan.get('events_seconds', {}),
            'contacts_fitted': False, 'runtime_tested': False}


def rig():
    source = downloaded('body_rig', ['rigged_character_glb', 'rigged_glb'])
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(source))
    for obj in bpy.context.scene.objects:
        if obj.animation_data:
            obj.animation_data_clear()
    scene = bpy.context.scene
    scene['stage'] = 'Meshy rigged body candidate; original mesh UV weights retained'
    save_blend(AUTHOR / 'Witch_Rigged_Candidate_v01.blend')
    export_fbx(DELIVERY / 'SK_Witch_Meshy_Candidate_v01.fbx', animated=False)
    return {'name': 'body_rig', 'source': str(source.relative_to(ROOT)),
            'bones': [b.name for o in scene.objects if o.type == 'ARMATURE' for b in o.data.bones],
            'runtime_tested': False}


def prop(name):
    source = downloaded(name, ['model_urls_glb'])
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    from mathutils import Vector, Matrix
    points = [o.matrix_world @ Vector(v) for o in meshes for v in o.bound_box]
    minimum = Vector(tuple(min(p[i] for p in points) for i in range(3)))
    maximum = Vector(tuple(max(p[i] for p in points) for i in range(3)))
    height = {'staff': 1.65, 'bottle': 0.18}[name]
    scale = height / (maximum.z - minimum.z)
    center = Vector(((minimum.x + maximum.x) / 2, (minimum.y + maximum.y) / 2, minimum.z))
    transform = Matrix.Diagonal((scale, scale, scale, 1.0)) @ Matrix.Translation(-center)
    for obj in [o for o in bpy.context.scene.objects if o.parent is None]:
        obj.matrix_world = transform @ obj.matrix_world
    bpy.context.view_layer.update()
    label = 'Staff' if name == 'staff' else 'PoisonBottle'
    bpy.context.scene['working_height_m'] = height
    bpy.context.scene['stage'] = 'Separate Meshy prop candidate, attachment and engine material pending'
    save_blend(AUTHOR / f'Witch_{label}_Candidate_v01.blend')
    export_fbx(DELIVERY / f'SM_Witch_{label}_Candidate_v01.fbx', animated=False)
    return {'name': name, 'source': str(source.relative_to(ROOT)), 'working_height_m': height,
            'grip_fitted': False, 'runtime_tested': False}


def raw_motion(name):
    source = next((RAW / ('motion_' + name) / 'downloads').glob('*.fbx'))
    clear_scene()
    bpy.ops.import_scene.fbx(filepath=str(source), automatic_bone_orientation=False)
    for index, action in enumerate(bpy.data.actions):
        action.name = 'MeshySource_' + name + (f'_{index}' if index else '')
    bpy.context.scene['stage'] = 'Unmodified Meshy prime source motion, before character retarget and time remap'
    bpy.context.scene['source_task_id'] = json.loads((RAW / ('motion_' + name) / 'task.json').read_text())['task_id']
    folder = AUTHOR / 'OriginalMotionSources'
    folder.mkdir(exist_ok=True)
    save_blend(folder / f'MeshySource_{name}.blend')
    return {'name': 'raw_' + name, 'source': str(source.relative_to(ROOT)), 'modified_motion': False}


AUTHOR.mkdir(exist_ok=True)
DELIVERY.mkdir(exist_ok=True)
arguments = sys.argv[sys.argv.index('--') + 1:]
records = []
for argument in arguments:
    records.append(raw_motion(argument[4:]) if argument.startswith('raw:') else rig() if argument == 'rig' else prop(argument) if argument in {'staff', 'bottle'} else motion(argument))
manifest = ROOT / 'authoring_manifest.json'
existing = json.loads(manifest.read_text()) if manifest.exists() else {'assets': {}}
for record in records:
    existing['assets'][record['name']] = record
existing['stage'] = 'production_exports_not_acceptance'
manifest.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')
print('WITCH_AUTHORING_SAVED ' + json.dumps(records))
