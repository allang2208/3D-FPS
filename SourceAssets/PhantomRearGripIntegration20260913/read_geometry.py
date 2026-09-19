import bpy,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent;S=P.parent
sources={'M4':S/'M4HK416Replica20260910/M4_HK416_Adapted_Editable.blend','AKM':S/'SkeletonStock20260912/AKM_StockSections_Editable.blend','QBZ191':S/'QBZ191Attachments20260913/QBZ191_Attachments_Editable.blend'}
out={}
def bounds(points):return {'lo':[min(p[i] for p in points) for i in range(3)],'hi':[max(p[i] for p in points) for i in range(3)]}
for key,path in sources.items():
    bpy.ops.wm.open_mainfile(filepath=str(path));rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='REST';bpy.context.view_layer.update()
    inv=(rig.matrix_world@rig.data.bones['WPN_root'].matrix_local).inverted()
    result=[]
    for ob in bpy.context.scene.objects:
        if ob.type!='MESH' or 'Manny' in ob.name or len(ob.data.vertices)==0:continue
        if key=='M4' and not (ob.name.startswith('M4_') and ob.name.endswith('_Export')):continue
        if key=='AKM' and ob.name!='AKM_Soviet_Native':continue
        if key=='QBZ191' and ob.name not in bpy.data.collections['QBZ_LOW'].objects:continue
        points=[inv@ob.matrix_world@v.co for v in ob.data.vertices]
        item={'name':ob.name,'vertices':len(points),'materials':[m.name if m else '' for m in ob.data.materials],**bounds(points)}
        if key=='AKM':
            adj=[[] for v in points]
            for e in ob.data.edges:a,b=e.vertices;adj[a].append(b);adj[b].append(a)
            seen=set();groups=[]
            for idx in range(len(points)):
                if idx in seen:continue
                stack=[idx];seen.add(idx);ids=[]
                while stack:
                    v=stack.pop();ids.append(v)
                    for n in adj[v]:
                        if n not in seen:seen.add(n);stack.append(n)
                groups.append({'id':len(groups),'count':len(ids),**bounds([points[i] for i in ids])})
            item['components']=groups
        result.append(item)
    out[key]={'source':str(path),'objects':result}
(P/'geometry_sources.json').write_text(json.dumps(out,indent=2))
