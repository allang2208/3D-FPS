"""Production input: sample each actual grip in assembly coordinates, no render."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'apprentice_staff_modular.blend'))
deps=bpy.context.evaluated_depsgraph_get()
result={'units':'cm','z':[22.01+i*(19.98/80) for i in range(81)],'angle_count':128,'variants':{}}
for variant in ('false','alloy_grip','pine_grip','sandalwood_grip'):
    obj=bpy.data.objects['SM_Staff_grip_lining_'+variant].evaluated_get(deps)
    mesh=obj.to_mesh()
    vertices=[obj.matrix_world@v.co for v in mesh.vertices]
    tree=BVHTree.FromPolygons(vertices,[list(f.vertices) for f in mesh.polygons])
    rows=[]
    for z in result['z']:
        ring=[]
        for i in range(result['angle_count']):
            a=math.tau*i/result['angle_count'];d=Vector((math.cos(a),math.sin(a),0))
            hit=tree.ray_cast(Vector((0,0,z))+d*12,-d,12)
            if hit[0] is None:raise RuntimeError(f'{variant}: no grip surface at {z}/{i}')
            ring.append(hit[0].xy.length)
        rows.append(ring)
    result['variants'][variant]={'radii':rows,'object':obj.name,'vertex_count':len(vertices)}
    obj.to_mesh_clear()
(P/'grip-surfaces.json').write_text(json.dumps(result),encoding='utf-8')
print('STAFF_V12_GRIP_SURFACES_SAVED',list(result['variants']))
