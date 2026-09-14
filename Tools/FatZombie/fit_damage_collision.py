"""Fit hit capsules to the existing skin, without changing the Blender source."""
import json
from pathlib import Path
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/FatZombieMeshy20260913')
frames = json.loads((ROOT / 'damage_collision_rig.json').read_text(encoding='utf-8'))
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'FatZombie_Meshy_Source.blend'))
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
# Recover the FBX axis/unit conversion from the matching reference joints.
names = [b.name for b in rig.data.bones if b.name in frames]
source = np.array([list(rig.matrix_world @ rig.data.bones[n].head_local) + [1.] for n in names])
target = np.array([frames[n]['location'] for n in names])
conversion = np.linalg.lstsq(source, target, rcond=None)[0]
body_names = {'Hips', 'Spine02', 'Spine01', 'Spine', 'neck', 'Head',
              'LeftArm', 'LeftForeArm', 'LeftHand', 'RightArm', 'RightForeArm', 'RightHand',
              'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'RightUpLeg', 'RightLeg', 'RightFoot'}
points = {n: [] for n in body_names}
inverse_frames = {}
for n in body_names:
    f = frames[n]
    x, y, z, w = f['quaternion_xyzw']
    inverse_frames[n] = Matrix.LocRotScale(Vector(f['location']), Quaternion((w,x,y,z)), Vector(f['scale'])).inverted()
for mesh in (o for o in bpy.data.objects if o.type == 'MESH'):
    groups = {g.index: g.name for g in mesh.vertex_groups}
    for vertex in mesh.data.vertices:
        influences = [g for g in vertex.groups if groups[g.group] in rig.data.bones]
        if not influences:
            continue
        bone = rig.data.bones[groups[max(influences, key=lambda g:g.weight).group]]
        while bone and bone.name not in body_names:
            bone = bone.parent
        if not bone:
            continue
        world = list(mesh.matrix_world @ vertex.co) + [1.]
        ue = np.array(world) @ conversion
        points[bone.name].append(list(inverse_frames[bone.name] @ Vector(ue)))

shapes = []
for name, vertices in sorted(points.items()):
    if len(vertices) < 4:
        continue
    p = np.array(vertices)
    mean = p.mean(axis=0)
    eigenvalues, basis = np.linalg.eigh(np.cov((p-mean).T))
    axis = basis[:, np.argmax(eigenvalues)]
    along = (p-mean) @ axis
    center = mean + axis * ((along.min()+along.max())*.5)
    offsets = p-center
    radial = offsets - np.outer(offsets @ axis, axis)
    radius = float(np.linalg.norm(radial, axis=1).max())
    length = max(0., float(along.max()-along.min())-radius)
    # Capsule Z follows the principal axis; UE Rotator conversion happens in UE.
    shapes.append({'bone': name, 'center': center.tolist(), 'axis': axis.tolist(),
                   'radius': radius, 'length': length, 'skin_vertices': len(vertices)})
(ROOT / 'damage_collision_shapes.json').write_text(json.dumps(shapes, indent=2), encoding='utf-8')
print('FAT_DAMAGE_SHAPES_AUTHORED', len(shapes))
