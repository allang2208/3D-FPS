"""Read disconnected donor shells to separate the HK416 rail shoe for fitting."""
import bpy,bmesh,json
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME/SourceAssets/BlessedLaser20261006/Model')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=str(P/'Sources/HK416.fbx'))
rows=[]
for ob in bpy.context.scene.objects:
    if ob.type!='MESH':continue
    bm=bmesh.new();bm.from_mesh(ob.data)
    seen=set()
    for vertex in bm.verts:
        if vertex in seen:continue
        component={vertex};pending=[vertex];seen.add(vertex)
        while pending:
            v=pending.pop()
            for edge in v.link_edges:
                other=edge.other_vert(v)
                if other not in seen:seen.add(other);component.add(other);pending.append(other)
        pts=[ob.matrix_world@v.co for v in component]
        rows.append({'vertices':len(pts),'min':[min(p[i] for p in pts) for i in range(3)],'max':[max(p[i] for p in pts) for i in range(3)]})
    bm.free()
(P/'Sources/hk416-shells.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(sorted(rows,key=lambda x:-x['vertices'])[:12]))
