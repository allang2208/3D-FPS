import bpy,json,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;pose=json.loads((O/'pose_inputs.json').read_text());F=Matrix.Diagonal((1,-1,1,1));bpy.ops.wm.read_factory_settings(use_empty=True);out={}
def mat(t):
 q=t['q'];return F@Matrix.LocRotScale(Vector(t['p']),Quaternion((q[3],q[0],q[1],q[2])),Vector(t['s']))@F
for key in ['Body','stable','balanced','phantom']:
 old=set(bpy.data.objects);bpy.ops.import_scene.fbx(filepath=str(O/'Exports'/('Before_'+key+'.fbx')),use_anim=False);obs=set(bpy.data.objects)-old
 if key=='Body':rig=next(o for o in obs if o.type=='ARMATURE');root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
 ob=max((o for o in obs if o.type=='MESH' and not o.name.startswith(('UCX_','UBX_'))),key=lambda o:len(o.data.vertices));me=ob.data;xf=root.inverted()@ob.matrix_world if key=='Body' else ob.matrix_world;v=np.array([(xf@p.co)[:] for p in me.vertices]);me.calc_loop_triangles();f=np.array([t.vertices[:] for t in me.loop_triangles]);mi=np.array([t.material_index for t in me.loop_triangles]);names=[m.name for m in me.materials]
 if key=='Body':
  slots=json.loads((O/'capture.json').read_text())['meshes']['/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10']['slots']
  if len(slots)!=len(names):raise RuntimeError('Export slots differ from input manifest')
  names=[s['slot'] for s in slots]
  deltas={b:mat(pose['clips']['idle']['bones'][b])@mat(t).inverted() for b,t in pose['reference'].items()};groups={g.index:g.name for g in ob.vertex_groups};vp=v.copy();hand=[]
  for i,p in enumerate(me.vertices):
   ps=Vector((0,0,0));wt=0;right=0
   for g in p.groups:
    n=groups[g.group]
    if n in deltas:ps+=(deltas[n]@Vector(v[i]))*g.weight;wt+=g.weight
    if n.endswith('_r') and any(s in n for s in ['hand','index','thumb','middle','ring','pinky']):right+=g.weight
   if wt:vp[i]=ps/wt
   if right>.5:hand.append(i)
  np.savez_compressed(O/'HandContact.npz',v=vp[hand]);out['hand_bounds']=[vp[hand].min(0).tolist(),vp[hand].max(0).tolist()]
  ids=[i for i,n in enumerate(names) if 'FactoryRearGrip' in n];keep=np.isin(mi,ids);vid,remap=np.unique(f[keep],return_inverse=True);vf=v[vid];ff=remap.reshape(-1,3);np.savez_compressed(O/'factory.npz',v=vf,f=ff);out['factory']={'materials':[names[i] for i in ids],'bounds':[vf.min(0).tolist(),vf.max(0).tolist()]}
  for n in ['index','middle','ring','pinky','thumb']:
   out[n]=[[b,t['p'][0],-t['p'][1],t['p'][2]] for b,t in pose['clips']['idle']['bones'].items() if n in b and b.endswith('_r')]
  continue
 np.savez_compressed(O/(key+'.npz'),v=v,f=f);out[key]={'materials':names,'bounds':[v.min(0).tolist(),v.max(0).tolist()],'sections':[]}
 for z in [-.005,-.012,-.025,-.040,-.060,-.080]:
  vv=v[abs(v[:,2]-z)<.002]
  if len(vv):out[key]['sections'].append({'z':z,'min':vv.min(0).tolist(),'max':vv.max(0).tolist()})
(O/'geometry_inputs.json').write_text(json.dumps(out,indent=2));print('G43_GEOMETRY_INPUTS',flush=True)
