import bpy, json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(next((P/'Original').rglob('*.fbx'))))
for o in bpy.context.scene.objects:
    if o.type!='MESH': continue
    points=[o.matrix_world@v.co for v in o.data.vertices]
    lo=[min(p[a] for p in points) for a in range(3)]
    hi=[max(p[a] for p in points) for a in range(3)]
    axis=max(range(3),key=lambda a:hi[a]-lo[a])
    slices=[]
    for i in range(32):
        z0=lo[axis]+(hi[axis]-lo[axis])*i/32
        z1=lo[axis]+(hi[axis]-lo[axis])*(i+1)/32
        part=[p for p in points if z0<=p[axis]<=z1]
        if part: slices.append({'longitudinal':[z0,z1],'bounds':[[min(p[a] for p in part),max(p[a] for p in part)] for a in range(3)]})
    print('SOURCE_GEOMETRY',json.dumps({'object':o.name,'vertices':len(points),'polygons':len(o.data.polygons),'min':lo,'max':hi,'axis':axis,'slices':slices}),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'OriginalSource.blend'))
