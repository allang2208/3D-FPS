import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent/'G18Integration20260929';R={}
def box(v):return {'min':[min(p[i] for p in v) for i in range(3)],'max':[max(p[i] for p in v) for i in range(3)]}
bpy.ops.wm.open_mainfile(filepath=str(S/'Single/G18_single_Editable.blend'))
rig=bpy.data.objects['SK_G18_Manny'];inv=rig.data.bones['WPN_root'].matrix_local.inverted();ob=bpy.data.objects['G18_G18']
points=[inv@v.co for v in ob.data.vertices]
trigger=ob.vertex_groups['WPN_Trigger'].index;handle=ob.vertex_groups['WPN_root'].index
R['trigger']=box([points[v.index] for v in ob.data.vertices if any(g.group==trigger and g.weight>.5 for g in v.groups)])
guard=[points[v.index] for v in ob.data.vertices if any(g.group==handle and g.weight>.5 for g in v.groups) and -.047<points[v.index].z<-.009 and points[v.index].y<-.017]
R['guard_low_band']=box(guard)
tree=BVHTree.FromPolygons(points,[list(p.vertices) for p in ob.data.polygons])
R['under_rail']=[]
for y in (-.075,-.085,-.095,-.105,-.115,-.125):
    for x in (-.008,0,.008):
        hit=tree.ray_cast(Vector((x,y,-.09)),Vector((0,0,1)))[0]
        R['under_rail'].append([x,y,hit.z if hit else None])
for kind in ('laser','flashlight'):
    bpy.ops.wm.open_mainfile(filepath=str(S/f'Attachments/SM_G18_{kind}_Editable.blend'))
    ob=bpy.data.objects['SM_G18_'+kind];parts={}
    for p in ob.data.polygons:
        name=ob.data.materials[p.material_index].name
        parts.setdefault(name,[]).extend([ob.matrix_world@ob.data.vertices[i].co for i in p.vertices])
    R[kind]={'parts':{name:box(v) for name,v in parts.items()},'sockets':{c.name:list(c.matrix_world.translation) for c in ob.children if c.type=='EMPTY'}}
(O/'mount_dimensions.json').write_text(json.dumps(R,indent=2))
print('G18_TACTICAL_MOUNT_DIMENSIONS')
