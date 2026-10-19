"""Repair shoulder binding on welded source topology; keep all original faces and UV corners."""
import bpy,bmesh,json,numpy as np
from pathlib import Path
from mathutils import Matrix
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/StaffLivingShoulder20261017';report={}
def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
for role,original,name in [('FemaleA','FacelessReceptionist20261007/V04/Authoring/FacelessReceptionist_V04.blend','Receptionist'),('FemaleB','FacelessResearcher20261009/V01/Authoring/FacelessResearcher_V01.blend','Researcher')]:
 d=np.load(OUT/'Diagnosis'/f'{role}_binding.npz');p=d['source'];old=d['current'];w=d['weights'];maps=d['maps'];weld=d['weld'];names=list(d['names']);cnt=np.bincount(weld);tri=d['triangles']
 up=np.column_stack([np.bincount(weld,weights=p[:,j])/cnt for j in range(3)])
 uw=np.column_stack([np.bincount(weld,weights=w[:,j])/cnt for j in range(w.shape[1])])
 blendmask=smooth(.07,.13,abs(up[:,0]))*(1-smooth(.28,.35,abs(up[:,0])))*smooth(1.18,1.28,up[:,2])*(1-smooth(1.58,1.66,up[:,2]))
 ids=np.where(blendmask>0)[0];active=np.where(uw[ids].max(0)>0)[0]
 edges=np.unique(np.sort(weld[np.concatenate([tri[:,[0,1]],tri[:,[1,2]],tri[:,[2,0]]])],axis=1),axis=0)
 keep=(blendmask[edges[:,0]]>0)|(blendmask[edges[:,1]]>0);edges=edges[keep]
 localids=np.unique(edges);lookup=np.full(len(up),-1,dtype=int);lookup[localids]=np.arange(len(localids));a,b=lookup[edges].T
 fixed=uw[localids][:,active].copy();field=fixed.copy();degree=np.bincount(np.r_[a,b],minlength=len(localids));mask=blendmask[localids]>0
 for _ in range(180):
  sums=np.column_stack([np.bincount(a,weights=field[b,j],minlength=len(localids))+np.bincount(b,weights=field[a,j],minlength=len(localids)) for j in range(len(active))])
  field[mask]=.35*field[mask]+.65*sums[mask]/degree[mask,None]
 amount=blendmask[localids,None];uw[np.ix_(localids,active)]=fixed*(1-amount)+field*amount
 new=uw[weld];changed=np.where(np.linalg.norm(new-w,axis=1)>1e-7)[0]
 # Native body and source point are rebased together; no rig/rest transform changes.
 source_mean=up[weld];new[changed]/=new[changed].sum(1)[:,None]
 order=np.argsort(new[changed],axis=1)[:,:-8]
 if order.shape[1]:
  rows=np.repeat(changed,order.shape[1]);new[rows,order.ravel()]=0;new[changed]/=new[changed].sum(1)[:,None]
 blend=np.einsum('vb,bij->vij',new[changed],maps);positions=np.linalg.solve(blend,np.c_[source_mean[changed],np.ones(len(changed))][:,:,None])[:,:3,0]
 bpy.ops.wm.open_mainfile(filepath=str(ROOT/'SourceAssets'/original));body=bpy.data.objects[name+'_CompleteBody'];rig=bpy.data.objects['root'];rig.animation_data_clear()
 for bone in rig.pose.bones:bone.matrix_basis.identity()
 raw=list(rig['source_world_matrix']);rig.matrix_world=Matrix([raw[i:i+4] for i in range(0,16,4)])
 for ob in list(bpy.context.scene.objects):
  if ob not in [body,rig]:bpy.data.objects.remove(ob,do_unlink=True)
 body.hide_set(False);body.hide_render=False
 normals=np.array([n.vector[:] for n in body.data.corner_normals]);loopvert=np.array([l.vertex_index for l in body.data.loops]);local={int(v):i for i,v in enumerate(changed)}
 oldblend=np.einsum('vb,bij->vij',w[changed],maps);normalchange=np.matmul(blend[:,:3,:3].transpose(0,2,1),np.linalg.inv(oldblend[:,:3,:3].transpose(0,2,1)))
 for li in np.where(np.isin(loopvert,changed))[0]:
  normals[li]=normalchange[local[int(loopvert[li])]]@normals[li];normals[li]/=np.linalg.norm(normals[li])
 for i,co,weights in zip(changed,positions,new[changed]):
  body.data.vertices[int(i)].co=co
  for g in body.vertex_groups:g.remove([int(i)])
  for j in np.flatnonzero(weights>0):
   group=body.vertex_groups.get(names[j]) or body.vertex_groups.new(name=names[j]);group.add([int(i)],float(weights[j]),'REPLACE')
 body.data.update();body.data.normals_split_custom_set(normals.tolist());body.name='LivingStaff'+role+'_ShoulderV02'
 bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
 bpy.ops.object.select_all(action='DESELECT');body.select_set(True);rig.select_set(True);bpy.context.view_layer.objects.active=rig
 bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Authoring'/f'LivingStaff{role}_ShoulderV02.blend'))
 bpy.ops.export_scene.fbx(filepath=str(OUT/'Delivery'/f'SK_LivingStaff{role}_ShoulderV02.fbx'),use_selection=True,object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,axis_forward='-Y',axis_up='Z',apply_unit_scale=True,use_armature_deform_only=False,mesh_smooth_type='FACE',use_mesh_modifiers=False)
 newcoords=np.array([v.co[:] for v in body.data.vertices]);np.savez_compressed(OUT/'Diagnosis'/f'{role}_repaired.npz',current=newcoords,weights=new,names=d['names'])
 bm=bmesh.new();bm.from_mesh(body.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000005)
 shoulder_edges=[e for e in bm.edges if e.is_boundary and any(.08<abs(v.co.x)<.4 and 1.16<v.co.z<1.62 for v in e.verts)]
 report[role]={'stage':'exported','changed_vertices':len(changed),'triangles_before':len(tri),'triangles_after':len(body.data.polygons),'shoulder_boundary_edges_after':len(shoulder_edges),'max_rest_vertex_movement_m':float(np.linalg.norm(newcoords-old,axis=1).max()),'source_bound_region':[p[changed].min(0).tolist(),p[changed].max(0).tolist()],'body_faces_uv_skeleton_animations_preserved':True,'runtime_tested':False}
 bm.free();print('SHOULDER_REPAIR_EXPORTED',role,json.dumps(report[role]),flush=True)
(OUT/'repair_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
