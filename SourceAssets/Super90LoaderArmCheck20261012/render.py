import bpy, json, math, sys
import numpy as np
from pathlib import Path
from mathutils import Quaternion
O=Path(__file__).parent;C=O/'Capture';R=O/'Renders';R.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def matrices(rows):
 a=np.asarray(rows,dtype=float);m=np.broadcast_to(np.eye(4),(len(a),4,4)).copy()
 for i,v in enumerate(a):m[i,:3,:3]=np.array(Quaternion((v[6],v[3],v[4],v[5])).to_matrix())*v[None,7:]
 m[:,:3,3]=a[:,:3];return m
def matrix(v):return matrices([v])[0]
def transform(p,m):return p@m[:3,:3].T+m[:3,3]
G=read(C/'geometry.json');names=G['names'];vertices=sorted(G['vertices'],key=lambda v:v['index']);points=np.array([v['p'] for v in vertices]);faces=np.array(G['triangles'],dtype=int);rest=matrices(G['rest'])
weights=np.zeros((len(points),len(names)))
for i,v in enumerate(vertices):
 total=sum(w for b,w in v['w'])
 for b,w in v['w']:weights[i,b]=w/total
groups={}
for b in range(len(names)):
 ids=np.flatnonzero(weights[:,b]>0)
 if len(ids):groups[b]=(ids,weights[ids,b],np.c_[points[ids],np.ones(len(ids))]@np.linalg.inv(rest[b]).T)
def skin(bones):
 m=matrices(bones);out=np.zeros_like(points)
 for b,(ids,ws,local) in groups.items():out[ids]+=(local@m[b].T)[:,:3]*ws[:,None]
 return out,m
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.render.resolution_percentage=100
scene.display.shading.light='STUDIO';scene.display.shading.studiolight_rotate_z=.4
scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=True
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH'
scene.display.shading.show_specular_highlight=False;scene.display.shading.show_backface_culling=True
scene.world=bpy.data.worlds.new('Diagnostic World');scene.display.shading.background_type='WORLD';scene.world.color=(.075,.095,.13)
scene.view_settings.view_transform='Standard';scene.render.image_settings.file_format='PNG'
cdata=bpy.data.cameras.new('MeasuredCamera');camera=bpy.data.objects.new('MeasuredCamera',cdata);scene.collection.objects.link(camera);scene.camera=camera
camera.location=(0,0,0);camera.rotation_euler=(0,0,0);cdata.clip_start=.01;cdata.clip_end=100;cdata.sensor_fit='HORIZONTAL'
mesh=bpy.data.meshes.new('SavedV7LOD0');mesh.from_pydata(points.tolist(),[],faces[:,:3].tolist());mesh.update()
obj=bpy.data.objects.new('SavedV7',mesh);scene.collection.objects.link(obj)
for i,name in enumerate(G['materials']):
 mat=bpy.data.materials.new(name)
 if 'Skin' in name:mat.diffuse_color=(.57,.38,.30,1)
 elif '12gauge' in name:mat.diffuse_color=(.5,.018,.012,1)
 elif 'Metal' in name or 'Steel' in name:mat.diffuse_color=(.12,.14,.16,1)
 else:mat.diffuse_color=(.045,.054,.066,1)
 mesh.materials.append(mat)
for poly,face in zip(mesh.polygons,faces):poly.material_index=int(face[3]);poly.use_smooth='Skin' in G['materials'][face[3]]
convert=np.array([[0,1,0],[0,0,1],[-1,0,0]],dtype=float)/100
seat=np.eye(4);seat[:3,:3]=[[0,1,0],[-1,0,0],[0,0,1]];seat[:3,3]=[0,-16,-80.15]
root=names.index('WPN_root');grip_objects={}
for family in ['vertical','canted','prism','angled']:
 g=read(C/(family+'_grip.json'));gm=bpy.data.meshes.new(family);gm.from_pydata(g['positions'],[],g['triangles']);gm.update();go=bpy.data.objects.new(family,gm);scene.collection.objects.link(go)
 mat=bpy.data.materials.new(family+'_gray');mat.diffuse_color=(.055,.065,.075,1);gm.materials.append(mat);go.hide_render=True
 grip_objects[family]=(go,np.array(g['positions']))
manifest=read(C/'capture_manifest.json');report=read(O/'analysis.json');jobs=[]
quick='--quick' in sys.argv
if quick:
 jobs=[('vertical_empty_7',158.,0),('vertical_empty_7',158.,1)]
else:
 for case in report['cases']:
  if not case['key'].endswith('_7'):continue
  for view in range(2):
   frames=sorted(set([108.,125.,136.,144.,float(case['views'][view]['clearance_frame'])]+([154.,164.] if '_empty_' in case['key'] else [140.,148.])))
   for f in frames:jobs.append((case['key'],f,view))
 if '--animation' in sys.argv:
  jobs=[]
  for family in ['base','vertical','canted','prism','angled']:
   for kind,end in [('empty',164),('normal',148)]:
    for f in range(108,end+1,2):jobs.append((family+'_'+kind+'_7',float(f),0))
cache={}
for key,frame,view in jobs:
 if key not in cache:cache[key]=read(C/(key+'.json'))
 case=cache[key];sample=next(s for s in case['samples'] if s['frame']==frame)
 posed,bones=skin(sample['bones']);cam=np.linalg.inv(matrix(sample['cameras'][view]))@matrix(case['mesh_frame'])
 output=transform(posed,cam)@convert.T;mesh.vertices.foreach_set('co',output.astype(np.float32).ravel());mesh.update()
 for family,(go,gpoints) in grip_objects.items():
  go.hide_render=case['family']!=family
  if not go.hide_render:
   gpos=transform(gpoints,cam@bones[root]@np.linalg.inv(rest[root])@seat)@convert.T;go.data.vertices.foreach_set('co',gpos.astype(np.float32).ravel());go.data.update()
 scene.render.resolution_x=768;scene.render.resolution_y=432 if view==0 else 504
 cdata.angle=math.radians(manifest['horizontal_fovs'][view]);bpy.context.view_layer.update()
 scene.render.filepath=str(R/(key+('_default_' if view==0 else '_wide_')+str(frame).replace('.','p')+'.png'))
 bpy.ops.render.render(write_still=True)
 print('AUDIT_RENDER',key,frame,view,flush=True)
