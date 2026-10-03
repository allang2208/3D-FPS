from pathlib import Path
import bpy,json,numpy as np,sys
from mathutils import Quaternion,Vector
P=Path(__file__).resolve().parent;mode=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'before'
clip=json.loads((P/'Inputs/base.json').read_text());rows=clip['frames'];bare=json.loads((P/'Inputs/bare.json').read_text());weapon=json.loads((P.parent/'LeftState50/Input/Weapon.json').read_text())
if mode=='after':rows=json.loads((P/'Authored/base_world.json').read_text())
def mat(t):
 q=t['q'];m=np.eye(4);m[:3,:3]=np.array(Quaternion((q[3],q[0],q[1],q[2])).to_matrix())*np.array(t['s']);m[:3,3]=t['p'];return m
bpy.ops.wm.read_factory_settings(use_empty=True);s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='MATERIAL';s.display.shading.show_shadows=False;s.display.shading.show_cavity=True;s.display.shading.background_type='WORLD';s.world=bpy.data.worlds.new('Neutral');s.world.color=(.05,.06,.07);s.render.image_settings.file_format='PNG';s.view_settings.view_transform='Standard';s.render.resolution_x=800;s.render.resolution_y=600;s.render.resolution_percentage=100
surfaces=[]
for label,d in [('arm',bare),('weapon',weapon)]:
 faces=d['triangles']
 if label=='arm':faces=[f for f in faces if all(sum(w for n,w in d['weights'][v].items() if n.endswith('_r'))>.9 for v in f)]
 else:faces=[f for f,mi in zip(faces,d['triangle_materials']) if mi not in (1,2) and '__Old' not in d['materials'][mi]]
 ids=np.array(sorted({v for f in faces for v in f}));mapping={v:i for i,v in enumerate(ids)};points=np.c_[np.array(d['positions'])[ids],np.ones(len(ids))];ws={}
 for vi,oi in enumerate(ids):
  for n,w in d['weights'][oi].items():ws.setdefault(n,[]).append((vi,w))
 ws={n:(np.array([i for i,w in vs]),np.array([w for i,w in vs])) for n,vs in ws.items()}
 inv={n:np.linalg.inv(mat(v)) for n,v in d['bones'].items()};mesh=bpy.data.meshes.new(label);mesh.from_pydata((points[:,:3]*[.01,-.01,.01]).tolist(),[],[[mapping[v] for v in f] for f in faces]);mesh.update();ob=bpy.data.objects.new(label,mesh);s.collection.objects.link(ob);m=bpy.data.materials.new(label);m.diffuse_color=(.62,.43,.30,1) if label=='arm' else (.15,.17,.18,1);mesh.materials.append(m)
 for f in mesh.polygons:f.use_smooth=label=='arm'
 surfaces.append((ob,points,ws,inv))
c=bpy.data.cameras.new('Camera');co=bpy.data.objects.new('Camera',c);s.collection.objects.link(co);s.camera=co
out=P/'Observation';out.mkdir(exist_ok=True)
for t in [4.45,4.65,4.82,5.13,5.36,5.65,5.82,6.05]:
 row=rows[round(t*120)]
 for ob,points,ws,inv in surfaces:
  result=np.zeros((len(points),3))
  for n,(ids,weights) in ws.items():result[ids]+=(points[ids]@(mat(row[n])@inv[n]).T)[:,:3]*weights[:,None]
  ob.data.vertices.foreach_set('co',(result*[.01,-.01,.01]).ravel());ob.data.update()
 for view in ['fps','joint']:
  if view=='fps':eye=Vector((0,-.10,.05));target=eye+Vector((0,1,0));c.type='PERSP';c.sensor_fit='VERTICAL';c.angle=np.radians(75)
  else:
   shoulder,elbow,wrist=[Vector(np.array(row[n]['p'])*[.01,-.01,.01]) for n in ['upperarm_r','lowerarm_r','hand_r']];target=(shoulder+elbow+wrist)/3;eye=target+Vector((.7,-.3,.2));c.type='ORTHO';c.ortho_scale=.75
  co.location=eye;co.rotation_euler=(target-eye).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(out/f'{mode}_{t:.2f}_{view}.png');bpy.context.view_layer.update();bpy.ops.render.render(write_still=True)
print('OBSERVATION_COMPLETE',mode)
