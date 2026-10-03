"""Persist M07 Surface Deform bindings and skeletal cloth collision sources.

This is a production authoring pass. It never advances the simulation, renders,
exports FBX, opens UE, or runs an acceptance test. Default saved cloth mode is OFF.
"""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector, Matrix

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
AUTHORING = ROOT / 'Authoring'
MASTER = AUTHORING / 'M07_Separated_Master.blend'
RECEIPT = AUTHORING / 'blender_cloth_binding.json'
TEXT_NAME = 'M07_ClothAuthoringMode.py'
COLLECTION_NAME = 'M07_BodyCollisionSource'

# Saved in the blend as an editable Text block. Running the block defines the
# functions; it intentionally does not activate cloth or change frames.
MODE_SCRIPT = '''import bpy

def set_m07_cloth_authoring_mode(enabled=False):
    """Switch deformation sources only; never advances the scene frame."""
    enabled = bool(enabled)
    for index in range(1, 7):
        display = bpy.data.objects.get(f'M07_GillDisplay_{index:02d}')
        proxy = bpy.data.objects.get(f'M07_GillSimulationProxy_{index:02d}')
        if display is None or proxy is None:
            raise RuntimeError(f'M07 panel {index:02d} is missing')
        for modifier in display.modifiers:
            if modifier.type == 'ARMATURE':
                modifier.show_viewport = not enabled
                modifier.show_render = not enabled
            elif modifier.name == 'M07_SurfaceDeform':
                modifier.show_viewport = enabled
                modifier.show_render = enabled
        for modifier in proxy.modifiers:
            if modifier.type == 'ARMATURE':
                modifier.show_viewport = True
                modifier.show_render = True
            elif modifier.type == 'CLOTH':
                modifier.show_viewport = enabled
                modifier.show_render = enabled
        proxy.hide_set(not enabled)
        proxy.hide_render = True
        proxy.display_type = 'WIRE'
    collision = bpy.data.collections.get('M07_BodyCollisionSource')
    if collision is not None:
        collision.hide_viewport = not enabled
        collision.hide_render = True
        for collider in collision.objects:
            collider.hide_set(not enabled)
            collider.hide_render = True
            collider.display_type = 'WIRE'
    scene = bpy.context.scene
    scene['m07_cloth_authoring_mode'] = enabled
    scene['m07_cloth_simulation_played_by_authoring'] = False
    bpy.context.view_layer.update()
    return {'enabled': enabled, 'simulation_frame_advanced': False}

def enable_m07_cloth_authoring_mode():
    return set_m07_cloth_authoring_mode(True)

def disable_m07_cloth_authoring_mode():
    return set_m07_cloth_authoring_mode(False)
'''


def capsule_geometry(a, b, radius, bone_matrix, radial_segments=12, cap_rings=4):
    """Closed triangulated capsule, endpoints/radius in bone-local metres."""
    axis = b - a
    if axis.length < 1e-8:
        raise RuntimeError('Cannot author a zero-length body capsule')
    axis.normalize()
    reference = Vector((1, 0, 0)) if abs(axis.x) < .8 else Vector((0, 0, 1))
    u = axis.cross(reference).normalized()
    v = axis.cross(u).normalized()
    vertices = [bone_matrix @ (a - axis * radius)]
    ring_starts = []
    for center, angles in [
        (a, [-math.pi / 2 + step * math.pi / (2 * cap_rings)
             for step in range(1, cap_rings + 1)]),
        (b, [step * math.pi / (2 * cap_rings) for step in range(cap_rings)])
    ]:
        for theta in angles:
            ring_starts.append(len(vertices))
            ring_center = center + axis * (radius * math.sin(theta))
            ring_radius = radius * math.cos(theta)
            for segment in range(radial_segments):
                phi = segment * 2 * math.pi / radial_segments
                p = ring_center + ring_radius * (u * math.cos(phi) + v * math.sin(phi))
                vertices.append(bone_matrix @ p)
    end_pole = len(vertices)
    vertices.append(bone_matrix @ (b + axis * radius))
    faces = []
    first = ring_starts[0]
    for segment in range(radial_segments):
        nxt = (segment + 1) % radial_segments
        faces.append((0, first + nxt, first + segment))
    for lower, upper in zip(ring_starts[:-1], ring_starts[1:]):
        for segment in range(radial_segments):
            nxt = (segment + 1) % radial_segments
            faces.append((lower + segment, lower + nxt, upper + nxt))
            faces.append((lower + segment, upper + nxt, upper + segment))
    last = ring_starts[-1]
    for segment in range(radial_segments):
        nxt = (segment + 1) % radial_segments
        faces.append((last + segment, last + nxt, end_pole))
    return vertices, faces


def author_collision_sources(rig, entries):
    collection = bpy.data.collections.get(COLLECTION_NAME)
    if collection is None:
        collection = bpy.data.collections.new(COLLECTION_NAME)
        bpy.context.scene.collection.children.link(collection)
    collection.hide_viewport = False
    collection.hide_render = True
    records = []
    for index, entry in enumerate(entries, 1):
        bone_name = entry['bone']
        bone = rig.data.bones.get(bone_name)
        if bone is None:
            raise RuntimeError(f'Collision source bone does not exist: {bone_name}')
        a = Vector((entry['a_cm'][0], -entry['a_cm'][1], entry['a_cm'][2])) / 100
        b = Vector((entry['b_cm'][0], -entry['b_cm'][1], entry['b_cm'][2])) / 100
        radius = float(entry['radius_cm']) / 100
        vertices, faces = capsule_geometry(a, b, radius, bone.matrix_local)
        name = f'M07_BodyCollision_{index:02d}_{bone_name}'
        previous = bpy.data.objects.get(name)
        if previous is not None:
            bpy.data.objects.remove(previous, do_unlink=True)
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(name, mesh)
        collection.objects.link(obj)
        obj.parent = rig
        obj.matrix_parent_inverse = Matrix.Identity(4)
        group = obj.vertex_groups.new(name=bone_name)
        group.add(list(range(len(vertices))), 1.0, 'REPLACE')
        armature = obj.modifiers.new('M07_ColliderArmature', 'ARMATURE')
        armature.object = rig
        obj.modifiers.new('M07_ClothCollision', 'COLLISION')
        obj.collision.thickness_outer = .008
        obj.collision.thickness_inner = .003
        obj.collision.damping = .35
        obj.collision.cloth_friction = 3
        obj.display_type = 'WIRE'
        obj.hide_render = True
        obj['display_export_excluded'] = True
        obj['source'] = 'cloth_ue_manifest.json bone-local centimetre capsule'
        obj['closed_capsule_authoring'] = True
        records.append({'name': name, 'bone': bone_name, 'vertices': len(vertices),
                        'triangles': len(faces), 'radius_m': radius,
                        'skeletal_vertex_weight': 1.0})
    return collection, records


def produce():
    bpy.ops.wm.open_mainfile(filepath=str(MASTER))
    rig = next(obj for obj in bpy.data.objects
               if obj.type == 'ARMATURE' and obj.data.name == 'M07_HumanoidAndGills')
    scene = bpy.context.scene
    manifest = json.loads((AUTHORING / 'cloth_ue_manifest.json').read_text(encoding='utf-8'))
    collision, collider_records = author_collision_sources(rig, manifest['collision_capsules'])
    receipt = {'stage': 'local cloth binding production in progress',
               'saved_blend': str(MASTER), 'bindings': [],
               'body_collision_sources': collider_records,
               'tested': False, 'rendered': False,
               'cloth_simulation_played': False, 'fbx_reexported': False,
               'semantic_seams_user_accepted': False, 'inter_panel_collision': False}
    text = bpy.data.texts.get(TEXT_NAME) or bpy.data.texts.new(TEXT_NAME)
    text.clear()
    text.write(MODE_SCRIPT)
    bpy.ops.object.select_all(action='DESELECT')
    for index in range(1, 7):
        display = bpy.data.objects[f'M07_GillDisplay_{index:02d}']
        proxy = bpy.data.objects[f'M07_GillSimulationProxy_{index:02d}']
        display.hide_set(False)
        proxy.hide_set(False)
        proxy.hide_render = True
        proxy.display_type = 'WIRE'
        for mod in proxy.modifiers:
            if mod.type == 'ARMATURE':
                mod.show_viewport = True
                mod.show_render = True
            elif mod.type == 'CLOTH':
                mod.show_viewport = False
                mod.show_render = False
                mod.collision_settings.collection = collision
                mod.collision_settings.use_collision = True
                mod.collision_settings.use_self_collision = False
        for mod in display.modifiers:
            if mod.type == 'ARMATURE':
                mod.show_viewport = False
                mod.show_render = False
        surface = display.modifiers.get('M07_SurfaceDeform')
        if surface is None:
            surface = display.modifiers.new('M07_SurfaceDeform', 'SURFACE_DEFORM')
        surface.target = proxy
        surface.falloff = 4
        surface.strength = 1
        surface.show_viewport = True
        surface.show_render = True
        display.select_set(True)
        bpy.context.view_layer.objects.active = display
        bpy.context.view_layer.update()
        if not surface.is_bound:
            result = bpy.ops.object.surfacedeform_bind(modifier=surface.name)
        else:
            result = {'FINISHED'}
        # is_bound is the result of the requested binder operation, not a test.
        if 'FINISHED' not in result or not surface.is_bound:
            receipt['stage'] = 'local cloth binding blocked by Surface Deform production error'
            receipt['production_error'] = {'panel': f'{index:02d}', 'operation_result': list(result),
                                            'is_bound': bool(surface.is_bound)}
            break
        display['blender_display_to_proxy_deformation_bound'] = True
        display['blender_cloth_double_skeletal_motion_prevented_by_mode_switch'] = True
        receipt['bindings'].append({'panel': f'{index:02d}', 'display': display.name,
                                    'proxy': proxy.name, 'modifier': surface.name,
                                    'is_bound': True})
        print(f'M07 Surface Deform binding authored for panel {index:02d}', flush=True)
        display.select_set(False)
    namespace = {}
    exec(MODE_SCRIPT, namespace)
    namespace['set_m07_cloth_authoring_mode'](False)
    scene['m07_cloth_authoring_text'] = TEXT_NAME
    scene['m07_display_surface_deform_bindings_authored'] = len(receipt['bindings'])
    if len(receipt['bindings']) == 6:
        receipt['stage'] = 'six local Surface Deform mappings and body collision sources saved'
    receipt['default_cloth_authoring_mode'] = False
    receipt['saved_frame'] = scene.frame_current
    receipt['simulation_frame_advanced'] = False
    receipt['limitations'] = [
        'Cloth mode is saved OFF; original display Armature deformation stays active.',
        'The bound mapping and collision sources have not been simulated or visually reviewed.',
        'Semantic panel seams, anatomical fit and skin weights remain preliminary.',
        'Six independent panels currently have no inter-panel collision.',
        'These Blender colliders are authoring sources; UE cloth asset creation is a separate stage.'
    ]
    bpy.ops.wm.save_as_mainfile(filepath=str(MASTER))
    RECEIPT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'stage': receipt['stage'], 'bound_panels': len(receipt['bindings']),
                      'saved_blend': str(MASTER), 'receipt': str(RECEIPT)}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    produce()
