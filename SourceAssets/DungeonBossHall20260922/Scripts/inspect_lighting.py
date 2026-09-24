"""Requested boss-light diagnosis against the actual authored mesh assembly; no render."""
import json
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

root = Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root/'Authored/Dungeon_BossPumpHall.blend'))
room = json.loads((root/'Config/rooms.json').read_text(encoding='utf-8'))['rooms'][0]
deps = bpy.context.evaluated_depsgraph_get()
geometry = [(obj, BVHTree.FromObject(obj, deps)) for obj in bpy.context.scene.objects
            if obj.type == 'MESH' and obj.name.startswith('SM_RS_BossPumpHall_') and not obj.name.endswith('_Fixtures')]
rows = []
for index, spec in enumerate(room['lights']):
    point = Vector(spec['at']); point.z -= .085
    above_gallery = point.z>3.6 and ((abs(point.x)>11.15 and point.y>=5.6) or point.y>=22)
    support = 3.6 if above_gallery else 0
    nearest, obstruction = (float('inf'), None), (float('inf'), None)
    for obj, tree in geometry:
        local = obj.matrix_world.inverted() @ point
        hit, normal, face, distance = tree.find_nearest(local)
        if hit is not None and distance < nearest[0]:
            nearest = (distance, obj.name)
        hit, normal, face, distance = tree.ray_cast(local, Vector((0, 0, -1)), point.z-support+.02)
        if hit is not None and distance < obstruction[0]:
            obstruction = (distance, obj.name)
    before = min(spec['radius_cm']*.8, 300) if spec['role']=='fill' else spec['radius_cm']
    rows.append(dict(index=index, position_m=list(point), target_height_m=support,
        vertical_distance_cm=round((point.z-support)*100, 2), before_radius_cm=before,
        after_radius_cm=spec['radius_cm'], nearest_shadow_geometry_cm=round(nearest[0]*100, 3),
        nearest_geometry=nearest[1], downward_first_hit=obstruction[1],
        downward_hit_distance_cm=round(obstruction[0]*100, 3) if obstruction[1] else None))
result = dict(lights=rows, origins_within_2mm_of_shadow_geometry=any(r['nearest_shadow_geometry_cm']<.2 for r in rows),
    method='Source mesh BVH proximity/down rays, plus current authored attenuation values. No PIE or luminance capture.')
(root/'Receipts/light-diagnosis-20260923.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print('BOSS_LIGHT_DIAGNOSIS', json.dumps(result), flush=True)
