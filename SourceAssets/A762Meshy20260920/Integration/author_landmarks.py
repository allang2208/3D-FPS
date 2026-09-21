"""Read source geometry and donor rig coordinates needed for the A762 fit."""
import bpy,json
from pathlib import Path
from mathutils import Vector
O=Path(__file__).parent
def bounds(points):
    return [[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]]
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'A762_Meshy_Candidate01_Editable.blend'))
out={'source':[]}
for obj in bpy.context.scene.objects:
    if obj.type!='MESH':continue
    pts=[obj.matrix_world@v.co for v in obj.data.vertices]
    out['source'].append({'name':obj.name,'bounds':bounds(pts),'faces':len(obj.data.polygons),'vertices':len(pts)})
    # Sample the long axis cross sections for assigning the visible parts.
    low,high=bounds(pts);axis=max(range(3),key=lambda i:high[i]-low[i])
    out['long_axis']=axis
    out['sections']=[]
    for k in range(25):
        lo=low[axis]+(high[axis]-low[axis])*k/25;hi=low[axis]+(high[axis]-low[axis])*(k+1)/25
        sec=[p for p in pts if lo<=p[axis]<=hi]
        if sec:out['sections'].append({'position':(lo+hi)/2,'bounds':bounds(sec)})
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/AKMSoviet20260911/AKM_Soviet_Editable.blend')
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
a=bpy.data.actions['AKM_Native_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
root=r.pose.bones['WPN_root'].matrix.copy();inv=root.inverted()
out['donor']={'fps':s.render.fps,'rig_matrix':[list(row) for row in r.matrix_world], 'actions':{a.name:list(a.frame_range) for a in bpy.data.actions},'bones':{b.name:{'head':list(inv@b.head),'tail':list(inv@b.tail)} for b in r.pose.bones if b.name.startswith('WPN_') or b.name in ['hand_l','hand_r','index_01_r']}}
for obj in s.objects:
    if obj.type=='MESH' and obj.name.startswith('AKM_Soviet'):
        dg=bpy.context.evaluated_depsgraph_get();e=obj.evaluated_get(dg);m=e.to_mesh();pts=[inv@r.matrix_world.inverted()@e.matrix_world@v.co for v in m.vertices]
        out['donor']['gun_bounds']=bounds(pts)
        out['donor']['groups']={}
        for group in obj.vertex_groups:
            ids=[v.index for v in obj.data.vertices if any(g.group==group.index and g.weight>.9 for g in v.groups)]
            if ids:out['donor']['groups'][group.name]=bounds([pts[i] for i in ids])
        e.to_mesh_clear()
(O/'author_landmarks.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print(json.dumps(out))
