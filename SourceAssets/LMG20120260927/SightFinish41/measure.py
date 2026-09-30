import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(O/'Exports/Before_Body.fbx'),use_anim=False)
rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local;slots=json.loads((O/'capture.json').read_text())['Body']['slots'];out={}
for ob in list(bpy.data.objects):
 if ob.type!='MESH':continue
 me=ob.data;me.calc_loop_triangles();xf=root.inverted()@ob.matrix_world
 verts=[xf@v.co for v in me.vertices];faces=[t.vertices[:] for t in me.loop_triangles if slots[t.material_index]['slot']=='M_LMG201_H39_Receiver'];bv=BVHTree.FromPolygons(verts,faces,all_triangles=True)
 out['underside']=[]
 for y in np.linspace(-.082,.010,24):
  row={'y':float(y),'hits':[]}
  for x in [-.008,-.004,.0008,.005,.010]:
   p,n,i,d=bv.ray_cast(Vector((x,float(y),-.060)),Vector((0,0,1)),.13)
   row['hits'].append({'x':x,'z':p.z if p is not None else None})
  out['underside'].append(row)
(O/'interfaces.json').write_text(json.dumps(out,indent=2));print('S41_INTERFACE_READ',flush=True)
