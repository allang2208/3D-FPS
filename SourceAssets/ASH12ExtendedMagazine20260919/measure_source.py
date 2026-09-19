import bpy,json,sys
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent
sys.path.insert(0,str(P.parent/'AttachmentIconAudit20260914'))
from icon_geometry import level_frame
bpy.ops.wm.open_mainfile(filepath=str(P.parent/'ASH12Surface20260919/ASH12_Surface_Editable.blend'))
g=bpy.data.objects['ASH12_Export'];r=bpy.data.objects['SK_M4_Infima'];r.data.pose_position='REST';bpy.context.view_layer.update();f=level_frame(r)
rows=[]
for i,m in enumerate(g.data.materials):
 if 'Magazine' not in m.name:continue
 ps=[p for p in g.data.polygons if p.material_index==i];ids=sorted({v for p in ps for v in p.vertices});vs=[f@g.matrix_world@g.data.vertices[v].co for v in ids]
 rows.append(dict(slot=i,mat=m.name,vertices=len(vs),faces=len(ps),min=[min(v[k] for v in vs) for k in range(3)],max=[max(v[k] for v in vs) for k in range(3)],z_levels=sorted(set(round(v.z,5) for v in vs)),bones=sorted({g.vertex_groups[w.group].name for v in ids for w in g.data.vertices[v].groups if w.weight>.1})))
(P/'source_measurements.json').write_text(json.dumps(dict(matrix=list(map(list,f)),object_matrix=list(map(list,g.matrix_world)),parts=rows),indent=2))
print(json.dumps(rows))
