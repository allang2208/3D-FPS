"""Read requested grip interfaces from the saved FBX; no render or game."""
import bpy,json,numpy as np
from pathlib import Path
from mathutils.bvhtree import BVHTree
from mathutils import Vector
O=Path(__file__).parent;bindings=json.loads((O/'bindings.json').read_text());out={};bpy.ops.wm.read_factory_settings(use_empty=True)
for key in ['Body','stable','balanced','phantom']:
 old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Exports'/('After_'+key+'.fbx')),use_anim=False);obs=set(bpy.data.objects)-old
 ob=max((o for o in obs if o.type=='MESH' and not o.name.startswith(('UCX_','UBX_'))),key=lambda o:len(o.data.vertices));me=ob.data
 if key=='Body':
  rig=next(o for o in obs if o.type=='ARMATURE');root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local;xf=root.inverted()@ob.matrix_world
  p=next(p for p in bindings if '/Cover10/SK_' in p)
 else:
  xf=ob.matrix_world;p=next(p for p in bindings if '/SM_LMG201_'+('stable_antislip' if key=='stable' else key)+'_reargrip.' in p)
 names=list(bindings[p]);v=np.array([(xf@q.co)[:] for q in me.vertices]);me.calc_loop_triangles();f=np.array([t.vertices[:] for t in me.loop_triangles]);mi=np.array([t.material_index for t in me.loop_triangles])
 if len(names)!=len(me.materials):raise RuntimeError('Export slot order changed '+key)
 seatids=[i for i,n in enumerate(names) if n=='M_LMG201_FactoryRearGrip_G43_Seat' or key!='Body' and n=='LMG20122_Interface'];seatfaces=f[np.isin(mi,seatids)];sv=v[np.unique(seatfaces)]
 report={'seat_bounds_m':[sv.min(0).tolist(),sv.max(0).tolist()],'seat_triangles':len(seatfaces),'material':{names[i]:bindings[p][names[i]] for i in seatids}}
 if key=='Body':
  bodyids=[i for i,n in enumerate(names) if not any(s in n for s in ['Manny','FactoryRearGrip','Cloth33','Feed__'])];receiver=BVHTree.FromPolygons([Vector(q) for q in v],f[np.isin(mi,bodyids)].tolist(),all_triangles=True);seat=BVHTree.FromPolygons([Vector(q) for q in v],seatfaces.tolist(),all_triangles=True);samples=[]
  for x in [-.013,-.008,.0008,.0096,.0146]:
   for y in [-.005,.008,.024,.034]:
    a=seat.ray_cast(Vector((x,y,.08)),Vector((0,0,-1)),.16)[0];b=receiver.ray_cast(Vector((x,y,-.03)),Vector((0,0,1)),.15)[0]
    if a is not None and b is not None:samples.append({'x':x,'y':y,'seat_top':a.z,'body_under':b.z,'gap_m':b.z-a.z})
  report['interface_samples']=samples
 out[key]=report
(O/'saved_contacts.json').write_text(json.dumps(out,indent=2));print('G43_SAVED_CONTACTS',json.dumps(out),flush=True)
