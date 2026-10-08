from pathlib import Path
import bpy,bmesh,json
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/BoundCongregateMeshy20261006')
for file in ['RigRepairV3/BoundCongregate_RigV3.blend','TentacleRepairV2/BoundCongregate_TentacleV2.blend']:
    bpy.ops.wm.open_mainfile(filepath=str(ROOT/file))
    for name in ['BC_Flesh','BC_AttackTentacle']:
        ob=bpy.data.objects.get(name)
        if not ob:continue
        bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000025)
        edges={e for e in bm.edges if e.is_boundary};rows=[]
        while edges:
            found={edges.pop()};pending=list(found)
            while pending:
                edge=pending.pop()
                for v in edge.verts:
                    for e in v.link_edges:
                        if e in edges:edges.remove(e);found.add(e);pending.append(e)
            points=[v.co for e in found for v in e.verts]
            verts={v for e in found for v in e.verts}
            odd=[{'p':list(v.co),'degree':sum(e in found for e in v.link_edges)} for v in verts if sum(e in found for e in v.link_edges)!=2]
            rows.append({'edges':len(found),'min':[round(min(p[i] for p in points),4) for i in range(3)],'max':[round(max(p[i] for p in points),4) for i in range(3)],'odd':odd})
        print('BOUNDARIES',file,name,json.dumps(rows),flush=True);bm.free()
