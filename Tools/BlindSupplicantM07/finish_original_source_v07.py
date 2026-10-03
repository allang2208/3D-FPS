"""Add editable hidden body collision to the original-source cloth master.

This does not modify or re-export the visible original surfaces or motions.
No simulation, render or runtime testing is performed.
"""
import json
import math
from pathlib import Path
import bpy
import numpy as np
from mathutils import Vector, Matrix

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001/RecoveryOriginalV07')
SOURCE = ROOT/'M07_Original_Skinned_Master_V07.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
manifest = json.loads((ROOT/'cloth_ue_manifest_original_v07.json').read_text(encoding='utf-8'))
collection = bpy.data.collections.new('M07_OriginalBodyCollisionSource')
bpy.context.scene.collection.children.link(collection)
colliders = []
for spec in manifest['collision_capsules']:
    name = spec['bone']
    bone = rig.data.bones[name]
    def world(point):
        return bone.matrix_local @ Vector((point[0], -point[1], point[2]))
    a, b = world(spec['a_cm']), world(spec['b_cm'])
    direction = (b-a).normalized()
    u = direction.orthogonal().normalized()
    v = direction.cross(u).normalized()
    radius = spec['radius_cm']
    positions = []
    for center, angles in ((a, [-math.pi/2, -3*math.pi/8, -math.pi/4, -math.pi/8, 0]),
                            (b, [0, math.pi/8, math.pi/4, 3*math.pi/8, math.pi/2])):
        for angle in angles:
            for step in range(12):
                azimuth = step*2*math.pi/12
                positions.append(center + direction*(radius*math.sin(angle)) +
                    (u*math.cos(azimuth)+v*math.sin(azimuth))*(radius*math.cos(angle)))
    faces = []
    for ring in range(9):
        for step in range(12):
            n = (step+1)%12
            faces.append((ring*12+step, ring*12+n, (ring+1)*12+n, (ring+1)*12+step))
    mesh = bpy.data.meshes.new('M07_OriginalCollision_'+name)
    mesh.from_pydata(positions, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(mesh.name, mesh)
    collection.objects.link(obj)
    obj.parent = rig
    obj.matrix_parent_inverse = Matrix.Identity(4)
    group = obj.vertex_groups.new(name=name)
    group.add(list(range(len(mesh.vertices))), 1.0, 'REPLACE')
    skin = obj.modifiers.new('OriginalBodyCollisionSkin', 'ARMATURE')
    skin.object = rig
    obj.modifiers.new('OriginalBodyClothCollision', 'COLLISION')
    obj.collision.thickness_outer = 1.0
    obj.collision.thickness_inner = .5
    obj.hide_render = True
    obj.display_type = 'WIRE'
    obj['simulation_collision_only'] = True
    obj['display_export_excluded'] = True
    obj.hide_set(True)
    colliders.append(obj.name)
bpy.context.scene['m07_blender_cloth_authoring'] = 'Default skin view. To author cloth enable proxy Cloth and display ProxyAuthoring, disable display OriginalSkin; unhide hidden collider objects if required by viewport.'
bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE), compress=True)
record = json.loads((ROOT/'anatomy_delivery.json').read_text(encoding='utf-8'))
record.update({'blender_body_collision_objects': colliders,
    'blender_body_collision_count': len(colliders),
    'source_finish_script': str(Path(__file__)),
    'animation_source': str(ROOT/'rig_motion/M07_OriginalRigAndMotion_V07.blend'),
    'combined_original_surface_and_motion_source': str(SOURCE), 'tested': False})
(ROOT/'anatomy_delivery.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
print('M07_ORIGINAL_EDITABLE_SKIN_CLOTH_AND_BODY_COLLISION_SAVED', flush=True)
