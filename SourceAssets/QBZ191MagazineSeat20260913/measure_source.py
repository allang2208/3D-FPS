"""Read supplied assembly and current authoring contact before editing."""
import bpy,json
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent
def bounds(points):return {'min':[min(v[j] for v in points) for j in range(3)],'max':[max(v[j] for v in points) for j in range(3)]}
source=json.loads((S/'QBZ19120260912/components.json').read_text())
report={'source_objects':[{'name':x['name'],'vertices':x['vertices'],'materials':x['materials'],'components':len(x['components'])} for x in source]}
bpy.ops.wm.open_mainfile(filepath=str(S/'QBZ19120260912/SourceInspect.blend'))
src=bpy.data.objects['QBZ'];xf=Matrix.Translation((-.005,-.11,.065))
report['source_components']={str(i):{'vertices':source[0]['components'][i]['vertices'],**bounds([xf@src.matrix_world@src.data.vertices[v].co for v in source[0]['components'][i]['ids']])} for i in [0,85,89,91,92,93,94]}
report['source_material_counts']={m.name:sum(1 for p in src.data.polygons if p.material_index==i) for i,m in enumerate(src.data.materials)}
source_mag=[xf@src.matrix_world@src.data.vertices[v].co for v in source[0]['components'][93]['ids']]
top=max(p.z for p in source_mag);report['source_mag_top_12mm']=bounds([p for p in source_mag if p.z>top-.012])
receiver=[xf@src.matrix_world@src.data.vertices[v].co for v in source[0]['components'][0]['ids']]
report['receiver_lip_vertices']=[list(p) for p in receiver if -.175<p.y<-.088 and p.z<.042]
points=[xf@src.matrix_world@v.co for v in src.data.vertices]
tree=BVHTree.FromPolygons(points,[list(p.vertices) for p in src.data.polygons if p.material_index==0])
report['well_vertical_rays']={}
for x in [-.015,.000688,.016]:
 for y in [-.16,-.145,-.13,-.115,-.10]:
  hit,normal,index,distance=tree.ray_cast(Vector((x,y,-.05)),Vector((0,0,1)),.15)
  report['well_vertical_rays'][f'{x},{y}']=list(hit) if hit else None
bpy.ops.wm.open_mainfile(filepath=str(S/'QBZ191Folding20260913/QBZ191_Folding_Editable.blend'))
r=bpy.data.objects['SK_M4_Infima'];gun=bpy.data.objects['QBZ191_Export'];s=bpy.context.scene
magindices={i for i,m in enumerate(gun.data.materials) if m.name=='M_QBZ191_Magazine'}
ids={v for p in gun.data.polygons if p.material_index in magindices for v in p.vertices}
weights={}
for i in ids:
 for group in gun.data.vertices[i].groups:
  name=gun.vertex_groups[group.group].name
  row=weights.setdefault(name,{'vertices':0,'min':1.,'max':0.});row['vertices']+=1;row['min']=min(row['min'],group.weight);row['max']=max(row['max'],group.weight)
report['current_magazine']={'vertices':len(ids),'weights':weights,'parent':r.data.bones['WPN_SOCKET_Magazine'].parent.name,'samples':{}}
for frame in [0,68,76,91,95,98,110]:
 a=bpy.data.actions['QBZ191_base_reload'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(frame);bpy.context.view_layer.update()
 inv=r.pose.bones['WPN_root'].matrix.inverted();mag=r.pose.bones['WPN_SOCKET_Magazine'].matrix
 points=[inv@mag@r.data.bones['WPN_SOCKET_Magazine'].matrix_local.inverted()@gun.data.vertices[i].co for i in ids]
 report['current_magazine']['samples'][str(frame)]={'bounds':bounds(points),'mag_in_root':[list(x) for x in inv@mag],'hand_in_mag':[list(x) for x in mag.inverted()@r.pose.bones['hand_l'].matrix]}
report['current_magazine']['root_local_bind_bounds']=bounds([r.data.bones['WPN_root'].matrix_local.inverted()@gun.data.vertices[i].co for i in ids])
(O/'source-contact.json').write_text(json.dumps(report,indent=2));print('SOURCE_CONTACT',json.dumps(report),flush=True)
