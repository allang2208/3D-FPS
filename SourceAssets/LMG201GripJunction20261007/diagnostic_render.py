"""Offline junction diagnosis for the explicitly requested investigation."""
import bpy,json
from pathlib import Path
import numpy as np
from mathutils import Vector
O=Path(__file__).parent
(O/'Diagnosis').mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=24
scene.render.resolution_x=1400;scene.render.resolution_y=850;scene.render.resolution_percentage=100
scene.world.color=(.18,.18,.18)
scene.view_settings.view_transform='AgX'
def material(name,col,rough):
 m=bpy.data.materials.new(name);m.diffuse_color=(*col,1);m.use_nodes=True
 bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(*col,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=.12
 return m
gripmat=material('Neutral geometry comparison',(.24,.31,.36),.35)
receivermat=material('Receiver reference',(.09,.1,.115),.45)
camdata=bpy.data.cameras.new('Camera');cam=bpy.data.objects.new('Camera',camdata);scene.collection.objects.link(cam);scene.camera=cam
target=Vector((0,.023,-.009));direction=Vector((4,-3,1.3)).normalized();cam.location=target+direction*.55
cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();camdata.type='ORTHO';camdata.ortho_scale=.195
right=cam.rotation_euler.to_quaternion()@Vector((1,0,0))
up=cam.rotation_euler.to_quaternion()@Vector((0,1,0))
for name,loc,energy,size in [('Key',(0,-.2,.24),10,.16),('Rim',(.16,.18,.12),14,.12),('Fill',(-.19,-.02,.03),4,.18)]:
 d=bpy.data.lights.new(name,'AREA');d.energy=energy*.16;d.shape='DISK';d.size=size
 ob=bpy.data.objects.new(name,d);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(target-ob.location).to_track_quat('-Z','Y').to_euler()
def obj(name,p,t,n,mat,offset):
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(p.tolist(),[],t.tolist());mesh.update()
 ob=bpy.data.objects.new(name,mesh);scene.collection.objects.link(ob);ob.location=offset;mesh.materials.append(mat)
 for poly in mesh.polygons:poly.use_smooth=True
 if n is not None:mesh.normals_split_custom_set(n.reshape(-1,3).tolist())
 return ob
ref=json.loads((O/'Input/factory.json').read_text())['receiver'];ids=list(ref['vertices']);remap={int(v):i for i,v in enumerate(ids)}
rp=np.array([ref['vertices'][i] for i in ids]);rt=np.array([[remap[v] for v in t] for t in ref['triangles']])
for kind in ('phantom','balanced','stable'):
 with (O/'Input'/(kind+'.bin')).open('rb') as f:
  h=json.loads(f.readline());nv,nt=h['vertices'],h['triangles'];p=np.fromfile(f,'<f4',nv*3).reshape(-1,3);t=np.fromfile(f,'<i4',nt*3).reshape(-1,3);np.fromfile(f,'<i4',nt);n=np.fromfile(f,'<f4',nt*9).reshape(-1,3,3)
 after=p.copy();an=n.copy()
 with (O/'Plans'/(kind+'.bin')).open('rb') as f:
  h=json.loads(f.readline());vi=np.fromfile(f,'<i4',h['moved']);after[vi]=np.fromfile(f,'<f4',len(vi)*3).reshape(-1,3);ti=np.fromfile(f,'<i4',h['normal_triangles']);an[ti]=np.fromfile(f,'<f4',len(ti)*9).reshape(-1,3,3)
 at=t.copy();flip=np.array(h.get('orientation_flip_ids',[]),dtype=int)
 if len(flip):at[flip]=at[flip][:,[1,0,2]];an[flip]=an[flip][:,[1,0,2]]
 objects=[]
 for index,(label,v,normal,faces) in enumerate([('BEFORE',p,n,t),('AFTER',after,an,at)]):
  keep=np.max(v[faces][:,:,2],axis=1)>-3.8;tt=faces[keep].copy();nn=normal[keep].copy()*np.array([1,-1,1]);vv=v*np.array([.01,-.01,.01])
  offset=right*((index-.5)*.098)
  objects.append(obj(label,vv,tt,nn,gripmat,offset))
  curve=bpy.data.curves.new(label,'FONT');curve.body=kind.upper()+'  '+label;curve.size=.004;curve.align_x='CENTER'
  text=bpy.data.objects.new(label,curve);scene.collection.objects.link(text);text.location=target+offset+up*.055+direction*.01;text.rotation_euler=cam.rotation_euler;objects.append(text)
 scene.render.filepath=str(O/'Diagnosis'/(kind+'_geometry.png'));bpy.ops.render.render(write_still=True)
 for ob in objects:bpy.data.objects.remove(ob,do_unlink=True)
