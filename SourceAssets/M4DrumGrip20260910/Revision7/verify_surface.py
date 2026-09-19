import bpy,json
from pathlib import Path
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumMatch_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene
hand=bpy.data.objects['SK_Manny_Arms_Export']
with bpy.data.libraries.load(str(O.parent.parent/'M4Drum20260909/M4_Drum_Optimized.blend'),link=False) as (src,dst):dst.meshes=['SM_M4_LargeDrum'] if 'SM_M4_LargeDrum' in src.meshes else []
if not dst.meshes:
 with bpy.data.libraries.load(str(O.parent.parent/'M4Drum20260909/M4_Drum_Optimized.blend'),link=False) as (src,dst):dst.objects=['SM_M4_LargeDrum']
 mesh=dst.objects[0].data
else:mesh=dst.meshes[0]
groups={g.index for g in hand.vertex_groups if g.name.endswith('_l') and g.name.startswith(('hand','thumb','index','middle','ring','pinky'))}
ids={v.index for v in hand.data.vertices if sum(g.weight for g in v.groups if g.group in groups)>.7}
faces=[tuple(p.vertices) for p in hand.data.polygons if all(i in ids for i in p.vertices)]
restinv=r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted()
rows=[]
for f in range(88*2,148*2+1):
 a=bpy.data.actions['A_M4_DrumMatch_reload_empty'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0]
 s.frame_set(f//2,subframe=f%2/2);bpy.context.view_layer.update()
 D=r.matrix_world@r.pose.bones['WPN_SOCKET_Magazine'].matrix@restinv
 db=BVHTree.FromPolygons([D@v.co for v in mesh.vertices],[tuple(p.vertices) for p in mesh.polygons])
 ev=hand.evaluated_get(bpy.context.evaluated_depsgraph_get());m=ev.to_mesh()
 hb=BVHTree.FromPolygons([ev.matrix_world@v.co for v in m.vertices],faces)
 pairs=db.overlap(hb);overlaps=len(pairs)
 if f==232:
  hit={i for _,j in pairs for i in faces[j]};print('HITGROUPS',[(hand.vertex_groups[max(hand.data.vertices[i].groups,key=lambda x:x.weight).group].name,list(m.vertices[i].co)) for i in list(hit)[:12]])
 ev.to_mesh_clear()
 rows.append({'frame':f/2,'triangle_pairs':overlaps})
(O/'surface_contact.json').write_text(json.dumps({'mesh':mesh.name,'rows':rows,'max_pairs':max(x['triangle_pairs'] for x in rows)},indent=2))
assert max(x['triangle_pairs'] for x in rows)==0, 'New hand/drum surface intersection'
print('SURFACE',max(x['triangle_pairs'] for x in rows))
