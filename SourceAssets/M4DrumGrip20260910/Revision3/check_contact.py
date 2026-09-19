import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent;bpy.ops.wm.open_mainfile(filepath=str(O/'M4_DrumGrip_Rebuilt.blend'));r=bpy.data.objects['SK_M4_Infima'];s=bpy.context.scene;hm=bpy.data.objects['SK_Manny_Arms_Export']
data=json.loads(Path('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909/build.json').read_text());G=Matrix(data['source_to_component']);center=Vector(data['center']);bind=r.data.bones['WPN_SOCKET_Magazine'].matrix_local.copy()
groupids={g.index for g in hm.vertex_groups if g.name.endswith('_l') and g.name.startswith(('hand','thumb','index','middle','ring','pinky'))}
ids=np.array([v.index for v in hm.data.vertices if sum(g.weight for g in v.groups if g.group in groupids)>.7]);report={}
for clip,end in [('reload',126),('reload_empty',162)]:
 a=bpy.data.actions['A_M4_DrumGrip_'+clip];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];samples=[]
 for t in range(end+1):
  s.frame_set(t);bpy.context.view_layer.update();D=r.pose.bones['WPN_SOCKET_Magazine'].matrix@bind.inverted()@G@Matrix.Translation(center)
  ev=hm.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=ev.to_mesh();coords=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',coords)
  vertices=coords.reshape(-1,3)[ids];p=(np.array(D.inverted()@ev.matrix_world)@np.column_stack((vertices,np.ones(len(vertices)))).T).T[:,:3];ev.to_mesh_clear()
  q=np.stack((np.sqrt(p[:,0]**2+(p[:,2]+.085)**2)-.070,np.abs(p[:,1])-.0355),axis=1)
  distance=np.linalg.norm(np.maximum(q,0),axis=1)+np.minimum(np.maximum(q[:,0],q[:,1]),0)
  samples.append({'frame':t,'vertices_inside_1mm':int(np.sum(distance<-.001)),'depth_mm':float(max(0,-distance.min())*1000)})
 worst=sorted(samples,key=lambda v:v['depth_mm'],reverse=True)[:12];report[clip]={'vertices_checked':len(ids),'frames':end+1,'worst':worst,'samples':samples}
 print(clip,json.dumps(worst),flush=True)
(O/'full_motion_contact.json').write_text(json.dumps(report,indent=2))
