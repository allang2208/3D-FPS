"""Read the authored loaf surface and native V7 palm for grip authoring.

This supplies production geometry only; it does not run animation tests or render.
"""
import json
from pathlib import Path
import bpy
from mathutils import Matrix, Vector

ROOT = Path('D:/FPS3D/FPSGAME')
OUT = Path(__file__).resolve().parent
hand_path = ROOT / 'SourceAssets/ModularOutfit20260925/BarePalmV7/Editable/AKM_BareArmsV7.blend'
bpy.ops.wm.open_mainfile(filepath=str(hand_path))
rig = next(o for o in bpy.context.scene.objects if o.type == 'ARMATURE')
rest = {b.name: b.matrix_local.copy() for b in rig.data.bones}
origin = rest['hand_l'].translation
x = (rest['middle_01_l'].translation - origin).normalized()
z = (rest['pinky_01_l'].translation - origin).cross(rest['index_01_l'].translation - origin).normalized()
z = (z - x * z.dot(x)).normalized()
# The mirrored author frame preserves the UE semantic palm: X along fingers,
# Y across the hand, Z toward the grasped object.
frame = Matrix((x, x.cross(z), z)).transposed()
geometry = {'hand_source': str(hand_path), 'digits': {}, 'loaves': {}}
for digit in ('index', 'middle', 'ring', 'pinky', 'thumb'):
    joints = []
    for segment in (1, 2, 3):
        bone = rig.data.bones[f'{digit}_{segment:02}_l']
        head = frame.inverted() @ (bone.head_local - origin) * 100
        tail = frame.inverted() @ (bone.tail_local - origin) * 100
        joints.append({'head_cm': list(head), 'tail_cm': list(tail), 'length_cm': (tail-head).length})
    geometry['digits'][digit] = joints
for definition, folder, name in (
    ('bread', 'Bread20261003', 'Bread'),
    ('baguette_bread', 'Baguette20261003', 'Baguette'),
):
    path = ROOT / 'SourceAssets' / folder / f'{name}_Authored.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path))
    loaf = bpy.data.objects[f'SM_{name}']
    points = [loaf.matrix_world @ v.co * 100 for v in loaf.data.vertices]
    slices = []
    for height in ((4.5, 5.5, 6.5) if definition == 'bread' else (13.5, 15, 16.5)):
        section = [p for p in points if abs(p.z-height) < .75]
        slices.append({'height_cm': height, 'low_cm': [min(p[i] for p in section) for i in range(2)],
            'high_cm': [max(p[i] for p in section) for i in range(2)]})
    geometry['loaves'][definition] = {'source': str(path), 'slices': slices}
(OUT/'contact_geometry.json').write_text(json.dumps(geometry, indent=2), encoding='utf-8')
print('FOOD_GRIP_GEOMETRY_SAVED', json.dumps(geometry))
