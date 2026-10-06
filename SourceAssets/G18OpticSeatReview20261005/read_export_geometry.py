import bpy, json
from pathlib import Path
O = Path(__file__).parent
rows = {}
for name in ('host', 'holographic', 'panoramic_red_dot'):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(O / (name + '.fbx')))
    objects = []
    for ob in bpy.context.scene.objects:
        r = {'name': ob.name, 'type': ob.type, 'matrix': [list(v) for v in ob.matrix_world]}
        if ob.type == 'MESH':
            vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
            r.update(vertices=len(vs), faces=len(ob.data.polygons), materials=[m.name for m in ob.data.materials],
                     bounds=[[min(v[i] for v in vs) for i in range(3)], [max(v[i] for v in vs) for i in range(3)]])
        if ob.type == 'ARMATURE':
            r['bones'] = {b.name: [list(v) for v in ob.matrix_world @ b.matrix_local]
                          for b in ob.data.bones if b.name in ('WPN_root', 'WPN_Slide', 'WPN_RearSight', 'WPN_FrontSight')}
        objects.append(r)
    rows[name] = objects
(O / 'export_geometry.json').write_text(json.dumps(rows, indent=2))
print('G18_EXPORTED_GEOMETRY_READ', flush=True)
