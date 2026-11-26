"""Read-only original GLB versus authored head comparison in a shared frame."""
import bpy,json,hashlib,math
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.kdtree import KDTree
N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115');O=N/'FaceDiagnosisR1';O.mkdir(exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
bpy.ops.wm.read_factory_settings(use_empty=True)
source=N/'MeshyHeadR1/Source/NunHead_R1_glb.glb';bpy.ops.import_scene.gltf(filepath=str(source))
ob=next(o for o in bpy.data.objects if o.type=='MESH');bpy.context.view_layer.objects.active=ob;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
mesh=ob.data;mesh.calc_loop_triangles();material=mesh.materials[0]
raw=np.array([v.co[:] for v in mesh.vertices]);zoff=168.0523223876953-.94961101*15.8
converted=raw*np.array([15.8,-15.8,15.8])+np.array([0,1.4,zoff])
d=read(N/'RefinementR4/Authored/head.json');pos=np.array(d['positions']);tri=np.array(d['triangles']);matids=np.array(d['triangle_materials'])
tree=KDTree(len(converted))
for i,p in enumerate(converted):tree.insert(p,i)
tree.balance()
face_ids=np.unique(tri[np.isin(matids,[0,2])]);above=face_ids[pos[face_ids,2]>149.1]
mouth=above[(np.abs(pos[above,0])<3.3)&(pos[above,2]>149.2)&(pos[above,2]<153)&(pos[above,1]>6.5)]
def match(ids):
 errors=[];missing=[]
 for vi in ids:
  _,rawi,distance=tree.find(pos[vi]);error=float(np.linalg.norm(pos[vi]-converted[rawi]))
  if error>5e-5:missing.append(int(vi))
  else:errors.append(error)
 return dict(vertices=len(ids),matched=len(errors),unmatched=len(missing),max_error_cm=max(errors,default=None),unmatched_first=missing[:12])
def orientation(j):
 p=np.array(j['positions']);t=np.array(j['triangles'],dtype=int);n=np.array(j['normals']).mean(axis=1)
 cross=np.cross(p[t[:,1]]-p[t[:,0]],p[t[:,2]]-p[t[:,0]]);den=np.linalg.norm(cross,axis=1)*np.linalg.norm(n,axis=1);valid=den>1e-10;dot=(cross*n).sum(axis=1)[valid]/den[valid]
 return dict(positive=int((dot>.1).sum()),negative=int((dot<-.1).sum()),median=float(np.median(dot)))
report={'original':str(source),'original_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'original_mesh_vertices':len(raw),'original_triangles':len(mesh.loop_triangles),'visible_face':match(above),'mouth':match(mouth),'authored_winding_vs_normal':orientation(d),'native_winding_vs_normal':orientation(read(N/'ProductionR1/Inputs/native_head.json')),'current_surface_materials':d['material_slots'],'scope':'Original GLB versus R4 authoring geometry only; independent UE readback follows'}
(O/'source_comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)
# Compare raw GLB and final authored geometry under exactly the same Blender shader,
# lighting and camera; reconstruct the latter back in the original source frame.
inverse=(pos-np.array([0,1.4,zoff]))/np.array([15.8,-15.8,15.8])
me=bpy.data.meshes.new('CurrentHeadInOriginalFrame');me.from_pydata(inverse,[],tri);me.update();me.materials.append(material);me.uv_layers.new(name='UVMap')
for f,uv in zip(me.polygons,d['uv']):
 f.use_smooth=True
 for li,xy in zip(f.loop_indices,uv):me.uv_layers.active.data[li].uv=(xy[0],1-xy[1])
normals=np.array(d['normals'])*np.array([1,-1,1]);me.normals_split_custom_set(normals.reshape(-1,3).tolist())
current=bpy.data.objects.new('CurrentAuthoredHead',me);bpy.context.collection.objects.link(current)
# Original model orientation: front is -Y after glTF import.
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=48;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
for device in prefs.devices:device.use=device.type=='OPTIX'
scene.cycles.device='GPU';scene.render.resolution_x=960;scene.render.resolution_y=960;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('NeutralSourceWorld');scene.world.use_nodes=True;bg=next(n for n in scene.world.node_tree.nodes if n.type=='BACKGROUND');bg.inputs['Color'].default_value=(.25,.25,.25,1);bg.inputs['Strength'].default_value=.4
scene.view_settings.view_transform='AgX';scene.view_settings.exposure=0
target=np.array([0.,0.,(157-zoff)/15.8]);mouth_target=np.array([0.,(1.4-7.8)/15.8,(150.8-zoff)/15.8])
def area(name,loc,energy,size):
 light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.size=size;o=bpy.data.objects.new(name,light);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
area('Key',(-2.5,-3,3),160,3);area('Fill',(2,-2,1),90,3)
cam=bpy.data.cameras.new('CompareCamera');camera=bpy.data.objects.new('CompareCamera',cam);bpy.context.collection.objects.link(camera);scene.camera=camera;cam.type='ORTHO';cam.clip_end=100
for title,active in [('original',ob),('authored',current)]:
 ob.hide_render=active is not ob;current.hide_render=active is not current
 for view,center,scale in [('face',target,1.8),('mouth',mouth_target,.55)]:
  camera.location=Vector(center)+Vector((0,-5,.02));camera.rotation_euler=(Vector(center)-camera.location).to_track_quat('-Z','Y').to_euler();cam.ortho_scale=scale;scene.render.filepath=str(O/(title+'_'+view+'.png'));bpy.ops.render.render(write_still=True)
print('ORIGINAL_FACE_DIAGNOSIS_RENDERED',flush=True)
