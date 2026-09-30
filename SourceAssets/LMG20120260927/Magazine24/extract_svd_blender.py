"""Read accepted SVD source hand without starting another UE process."""
import bpy,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[2]
bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/SVDThumbUp20260923/SVD_base_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['A_SVD_reload'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
bpy.context.scene.frame_set(220);bpy.context.view_layer.update()
out={'rest':{b.name:[list(v) for v in r.matrix_world@b.matrix_local] for b in r.data.bones},'pose':{b.name:[list(v) for v in r.matrix_world@b.matrix] for b in r.pose.bones},'parent':{b.name:b.parent.name if b.parent else None for b in r.data.bones}}
dg=bpy.context.evaluated_depsgraph_get();out['magazines']=[]
for ob in bpy.context.scene.objects:
 if ob.type!='MESH' or 'WPN_SOCKET_Magazine' not in ob.vertex_groups:continue
 group=ob.vertex_groups['WPN_SOCKET_Magazine'].index
 ids={v.index for v in ob.data.vertices if any(w.group==group and w.weight>.5 for w in v.groups)}
 if not ids:continue
 eo=ob.evaluated_get(dg);me=eo.to_mesh()
 fs=[list(p.vertices) for p in me.polygons if all(i in ids for i in p.vertices)]
 used=sorted({i for f in fs for i in f});mapping={v:i for i,v in enumerate(used)}
 out['magazines'].append({'name':ob.name,'vertices':[list(eo.matrix_world@me.vertices[i].co) for i in used],'faces':[[mapping[i] for i in f] for f in fs]})
 print('SVD_MAGAZINE_SOURCE',ob.name,len(used));eo.to_mesh_clear()
(O/'Sources/svd_blender.json').write_text(json.dumps(out));print('Accepted SVD source hand extracted')
