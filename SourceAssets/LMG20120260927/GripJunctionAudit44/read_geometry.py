"""Requested read-only audit of G43 grip junctions and separate surfaces."""
import bpy,json,numpy as np
from pathlib import Path
O=Path(__file__).parent;O.mkdir(exist_ok=True);S=O.parent/'GripFinish43';bindings=json.loads((S/'bindings.json').read_text());out={};bpy.ops.wm.read_factory_settings(use_empty=True)
for key in ['Body','stable','balanced','phantom']:
 old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(S/'Exports'/('After_'+key+'.fbx')),use_anim=False);obs=set(bpy.data.objects)-old
 ob=max((o for o in obs if o.type=='MESH' and not o.name.startswith(('UCX_','UBX_'))),key=lambda o:len(o.data.vertices));me=ob.data
 if key=='Body':
  rig=next(o for o in obs if o.type=='ARMATURE');root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local;xf=root.inverted()@ob.matrix_world;p=next(p for p in bindings if '/Cover10/SK_' in p)
 else:xf=ob.matrix_world;p=next(p for p in bindings if '/SM_LMG201_'+('stable_antislip' if key=='stable' else key)+'_reargrip.' in p)
 names=list(bindings[p]);v=np.array([(xf@q.co)[:] for q in me.vertices]);me.calc_loop_triangles();f=np.array([t.vertices[:] for t in me.loop_triangles]);mi=np.array([t.material_index for t in me.loop_triangles]);uv=np.array([me.uv_layers.active.data[l].uv[:] for t in me.loop_triangles for l in t.loops]).reshape(-1,3,2)
 if len(names)!=len(me.materials):raise RuntimeError('Export slot order changed '+key)
 entry={'asset':p,'slots':{}}
 for i,name in enumerate(names):
  if key=='Body' and 'FactoryRearGrip' not in name:continue
  sel=mi==i;ff=f[sel]
  if len(ff)==0:continue
  vv=v[np.unique(ff)];cross=np.cross(v[ff[:,1]]-v[ff[:,0]],v[ff[:,2]]-v[ff[:,0]]);area=np.linalg.norm(cross,axis=1)*.5;uvv=uv[sel];uvarea=np.abs(np.cross(uvv[:,1]-uvv[:,0],uvv[:,2]-uvv[:,0]))*.5;valid=area>1e-12
  density=np.sqrt(uvarea[valid]/area[valid]);entry['slots'][name]={'material':bindings[p][name],'triangles':len(ff),'bounds_m':[vv.min(0).tolist(),vv.max(0).tolist()],'uv_per_m_quantiles':np.quantile(density,[.1,.5,.9]).tolist(),'sections':[]}
  for z in [-.030,-.024,-.020,-.016,-.012,-.008,-.006,0,.004]:
   points=[]
   for tri in v[ff]:
    for a,b in [(0,1),(1,2),(2,0)]:
     if (tri[a,2]-z)*(tri[b,2]-z)<0:
      t=(z-tri[a,2])/(tri[b,2]-tri[a,2]);points.append(tri[a]+(tri[b]-tri[a])*t)
   if points:
    points=np.array(points);entry['slots'][name]['sections'].append({'z':z,'min':points.min(0).tolist(),'max':points.max(0).tolist()})
 out[key]=entry
(O/'geometry.json').write_text(json.dumps(out,indent=2));print('GRIP_JUNCTION_AUDIT',json.dumps(out),flush=True)
