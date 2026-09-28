import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).parent/'SpawnRepair'
results={}
for name in ['SM_GodSpaceStructure','SM_MarbleFloorTiles']:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(R/(name+'.fbx')))
    rows=[]
    for o in bpy.context.scene.objects:
        if o.type!='MESH':continue
        v=[o.matrix_world@p.co for p in o.data.vertices]
        tree=BVHTree.FromPolygons(v,[p.vertices[:] for p in o.data.polygons])
        probes=[(13,38),(13,-38)] if name=='SM_GodSpaceStructure' else [(4,-2),(0,0)]
        hits=[]
        for x,y in probes:
            loc,n,idx,d=tree.ray_cast(Vector((x,y,20)),Vector((0,0,-1)),40)
            hits.append({'xy':[x,y],'z':loc.z if loc else None,'normal':list(n) if n else None})
        rows.append({'object':o.name,'vertices':len(v),'min':[min(p[i] for p in v) for i in range(3)],'max':[max(p[i] for p in v) for i in range(3)],'hits':hits})
    results[name]=rows
(R/'fbx-geometry.json').write_text(json.dumps(results,indent=2))
print('SPAWN_FBX '+json.dumps(results))
