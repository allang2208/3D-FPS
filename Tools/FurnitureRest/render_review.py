"""Render read-back UE animation keys and real geometry, with neutral review materials."""
import bpy,json,sys,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
DATA=Path('D:/FPS3D/FPSGAME/SourceAssets/FurnitureRest20261022/Review20261023')
ROOT=(Path(args[args.index('--review')+1]) if '--review' in args else DATA).resolve()
ROOT.mkdir(parents=True,exist_ok=True)
still='--still' in args
candidate='--candidate' in args
rig_path=Path(args[args.index('--rig')+1]) if '--rig' in args else ROOT.parent/'authored.json' if candidate else ROOT/'saved_poses.json'
rig=json.loads(rig_path.read_text())
body_path=next(p for p in (ROOT/'body.json',ROOT.parent/'ReviewSaved/body.json',DATA/'body.json') if p.exists())
geo=json.loads(body_path.read_text())
if candidate or '--v2' in args:
 config_path=Path(args[args.index('--config')+1]) if '--config' in args else ROOT.parent/'furniture_rest.json'
 config=json.loads(config_path.read_text(encoding='utf-8'))
 originals=json.loads((DATA/'furniture.json').read_text(encoding='utf-8'))
 profiles={k:next(p for p in config['furniture'] if p['mesh']==v['mesh']) for k,v in originals.items()}
 if '--all' in args:
  profiles={kind:next(p for p in config['furniture'] if any(s['kind']==kind for s in p['slots'])) for kind in config['types'] if 'Rest.'+kind+'.Enter' in rig['clips']}
else:profiles=json.loads((ROOT/'furniture.json').read_text(encoding='utf-8'))
head_path=next(p for p in (ROOT/'head.json',ROOT.parent/'ReviewSaved/head.json',Path('D:/FPS3D/FPSGAME/SourceAssets/JasonPlayer20261003/head_geometry.json')) if p.exists())
headgeo=json.loads(head_path.read_text());headpoints=np.array(headgeo['positions'])
names=rig['names'];parents=rig['parents'];ix={n:i for i,n in enumerate(names)}
def fk(f):
 q=f[:,3:7];x,y,z,w=q.T
 m=np.zeros((len(f),4,4));m[:,3,3]=1
 m[:,:3,:3]=np.stack([1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)],axis=1).reshape(-1,3,3)*f[:,None,7:]
 m[:,:3,3]=f[:,:3]
 for i,p in enumerate(parents):
  if p>=0:m[i]=m[p]@m[i]
 return m
ref=np.array(rig['reference']);ibind=np.linalg.inv(fk(ref));points=np.array(geo['positions']);tri=np.array(geo['triangles'],dtype=int)
influences={}
for v,ws in enumerate(geo['weights']):
 for bone,weight in ws:
  bone=ix[geo['bone_names'][bone]];influences.setdefault(bone,[]).append((v,weight))
influences={b:(np.array(rows)[:,0].astype(int),np.array(rows)[:,1,None]) for b,rows in influences.items()}
def skin(f):
 m=fk(f)@ibind;result=np.zeros_like(points)
 for b,(ids,weights) in influences.items():result[ids]+=(points[ids]@m[b,:3,:3].T+m[b,:3,3])*weights
 return result

head_influences={}
for v,ws in enumerate(headgeo.get('weights',[])):
 for b,weight in ws:head_influences.setdefault(ix[headgeo['bone_names'][b]],[]).append((v,weight))
head_influences={b:(np.array(rows)[:,0].astype(int),np.array(rows)[:,1,None]) for b,rows in head_influences.items()}
def skinhead(f):
 m=fk(f)@ibind
 if not head_influences:return headpoints@m[ix['head'],:3,:3].T+m[ix['head'],:3,3]
 result=np.zeros_like(headpoints)
 for b,(ids,weights) in head_influences.items():result[ids]+=(headpoints[ids]@m[b,:3,:3].T+m[b,:3,3])*weights
 return result
def setrot(f,b,rot):
 w=fk(f);p=parents[b]
 local=w[p,:3,:3].T@rot if p>=0 else rot
 q=Matrix(local.tolist()).to_quaternion();f[b,3:7]=[q.x,q.y,q.z,q.w]
def solvefoot(f,side,drop):
 a,b,c=[ix[n+'_'+side] for n in ('thigh','calf','foot')];w=fk(f);h=w[a,:3,3];k=w[b,:3,3];end=w[c,:3,3];endrot=w[c,:3,:3].copy();target=end-[0,0,drop]
 l1=np.linalg.norm(k-h);l2=np.linalg.norm(end-k);direction=target-h;dist=np.clip(np.linalg.norm(direction),.01,l1+l2-.001);direction/=np.linalg.norm(direction)
 pole=np.array([0.,100.,-25.]);bend=pole-direction*(pole@direction);bend/=np.linalg.norm(bend)
 along=(l1*l1+dist*dist-l2*l2)/(2*dist);knee=h+along*direction+math.sqrt(max(0,l1*l1-along*along))*bend
 delta=Vector(k-h).rotation_difference(Vector(knee-h));setrot(f,a,np.array(delta.to_matrix())@w[a,:3,:3]);w=fk(f)
 delta=Vector(w[c,:3,3]-w[b,:3,3]).rotation_difference(Vector(target-w[b,:3,3]));setrot(f,b,np.array(delta.to_matrix())@w[b,:3,:3]);setrot(f,c,endrot)
def mix(a,b,t):
 f=a*(1-t)+b*t;q=b[:,3:7].copy();q[np.sum(a[:,3:7]*q,axis=1)<0]*=-1
 f[:,3:7]=a[:,3:7]*(1-t)+q*t;f[:,3:7]/=np.linalg.norm(f[:,3:7],axis=1)[:,None];return f
def ease(t):t=np.clip(t,0,1);return t*t*(3-2*t)
def frame(kind,phase,t):
 d=rig['clips'][f'Rest.{kind}.{phase}'];a=np.array(d['frames']);sample=np.clip(t/d['duration'],0,1)*(len(a)-1);i=min(int(sample),len(a)-2)
 f=mix(a[i],a[i+1],sample-i)
 profile=profiles[kind];slot=profile['slots'][len(profile['slots'])//2]
 if slot['kind']!=kind:slot=next(s for s in profile['slots'] if s['kind']==kind)
 seat=np.array(slot['seat'])*np.array(profile.get('scale',[1,1,1]));z=seat[2]-46
 if candidate or '--v2' in args:z=seat[2]-config['types'][kind]['surface_height']
 else:
  if phase=='Enter':z*=ease(t/.85)
  if phase=='Exit':z*=1-ease(t/d['duration'])
  if kind in ('Chair','Sofa'):
   for side in ('l','r'):solvefoot(f,side,z)
 v=skin(f);angle=math.radians(slot['yaw']-90);rot=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]])
 hp=skinhead(f)
 return v@rot.T+[seat[0],seat[1],z],hp@rot.T+[seat[0],seat[1],z]
def mesh(name,p,t,color):
 me=bpy.data.meshes.new(name);me.from_pydata((np.array(p)*[1,-1,1]/100).tolist(),[],np.array(t,dtype=int)[:,::-1].tolist());me.update()
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);ob.color=(*color,1)
 for face in me.polygons:face.use_smooth=True
 return ob
bpy.ops.wm.read_factory_settings(use_empty=True)
body=mesh('Saved Jason body',points,tri,(.19,.44,.64))
head=mesh('Jason head geometry',headpoints,headgeo['triangles'],(.19,.44,.64))
s=bpy.context.scene;s.render.engine='BLENDER_WORKBENCH';s.display.shading.light='STUDIO';s.display.shading.color_type='OBJECT';s.display.shading.show_shadows=True
s.display.shading.show_cavity=True;s.display.shading.cavity_type='BOTH';s.display.shading.background_type='WORLD';s.world=bpy.data.worlds.new('Review studio');s.world.color=(.055,.065,.08)
s.render.resolution_x=600;s.render.resolution_y=600;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG';s.display.render_aa='8';s.view_settings.view_transform='Standard'
bpy.ops.mesh.primitive_plane_add(size=200);floor=bpy.context.object;floor.color=(.21,.23,.26,1);floor.location.z=-.008
cam=bpy.data.cameras.new('Review view');co=bpy.data.objects.new('Review view',cam);s.collection.objects.link(co);s.camera=co;cam.type='ORTHO';cam.ortho_scale=2.8
for kind in profiles:
 if '--only' in args and not kind.startswith(args[args.index('--only')+1]):continue
 if '--all' in args:
  geometry=ROOT.parent/'Geometry' if (ROOT.parent/'Geometry/index.json').exists() else DATA.parent/'RefineV2/Geometry'
  lookup=json.loads((geometry/'index.json').read_text());data=json.loads((geometry/lookup[profiles[kind]['mesh']]).read_text())
 else:data=json.loads(((ROOT if (ROOT/(kind+'.json')).exists() else DATA)/(kind+'.json')).read_text())
 furniture=mesh(kind,np.array(data['positions'])*np.array(profiles[kind].get('scale',[1,1,1])),data['triangles'],(.59,.54,.45))
 target=Vector((0,0,.9));co.location=target+Vector((3,-4,1.8));cam.ortho_scale=3.2 if kind in ('Bed','Bunk') else 2.9
 if 'Sofa' in kind:
  focus=next(slot for slot in profiles[kind]['slots'] if slot['kind']==kind)
  target=Vector((focus['seat'][0]*profiles[kind].get('scale',[1,1,1])[0]*.005,-.3,.9))
  co.location=target+Vector((3,-4,1.8));cam.ortho_scale=3.15
 if kind=='Bunk':co.location=target+Vector((-3.8,3,1.7));cam.ortho_scale=3.25
 if kind in ('BedKing','Hospital','Ward'):cam.ortho_scale=3.6
 if kind=='ApartmentBed':
  target=Vector((-.3,0,.9));co.location=target+Vector((3,-4,2.1));cam.ortho_scale=4.3
 if kind.startswith('ApartmentSofa'):cam.ortho_scale=3.65
 if '--side' in args:
  target=Vector((0,-.35,1.));co.location=target+Vector((4,0,.25));cam.ortho_scale=2.45
 if '--pose-side' in args:
  slot=next(slot for slot in profiles[kind]['slots'] if slot['kind']==kind)
  seat=np.array(slot['seat'])*np.array(profiles[kind].get('scale',[1,1,1]));seat[2]-=config['types'][kind]['surface_height']
  angle=math.radians(slot['yaw']-90);worldturn=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]])
  pelvis=fk(np.array(rig['clips'][f'Rest.{kind}.Idle']['frames'][0]))[ix['pelvis'],:3,3]
  point=(worldturn@(pelvis+[0,0,6])+seat)*[1,-1,1]/100
  target=Vector(point);co.location=target+Vector((worldturn@np.array([4.,0.,.35]))*[1,-1,1]);cam.ortho_scale=2.45
 if '--front' in args:
  slot=next(slot for slot in profiles[kind]['slots'] if slot['kind']==kind)
  seat=np.array(slot['seat'])*np.array(profiles[kind].get('scale',[1,1,1]));seat[2]-=config['types'][kind]['surface_height']
  angle=math.radians(slot['yaw']-90);worldturn=np.array([[math.cos(angle),-math.sin(angle),0],[math.sin(angle),math.cos(angle),0],[0,0,1]])
  target=Vector((worldturn@np.array([0.,20.,105.])+seat)*[1,-1,1]/100)
  co.location=target+Vector((worldturn@np.array([3.,4.,1.2]))*[1,-1,1]);cam.ortho_scale=2.25
 if '--ortho' in args:cam.ortho_scale=float(args[args.index('--ortho')+1])
 co.rotation_euler=(target-co.location).to_track_quat('-Z','Y').to_euler()
 dest=ROOT/'frames'/kind;dest.mkdir(parents=True,exist_ok=True)
 timeline=[]
 for phase in ('Enter','Idle','Exit'):
  duration=rig['clips'][f'Rest.{kind}.{phase}']['duration'] if phase!='Idle' else 1.5
  timeline.extend((phase,float(t)) for t in np.arange(0,duration,1/12))
 if still:timeline=[('Idle',0)]
 if '--poses' in args:
  duration=rig['clips'][f'Rest.{kind}.Enter']['duration'];timeline=[('Enter',float(t)) for t in np.linspace(0,duration,9)]
 if '--phase' in args:timeline=[(p,t) for p,t in timeline if p==args[args.index('--phase')+1]]
 if '--pose-times' in args:timeline=[(args[args.index('--phase')+1] if '--phase' in args else 'Enter',float(t)) for t in args[args.index('--pose-times')+1].split(',')]
 for i,(phase,t) in enumerate(timeline):
  vertices,hp=frame(kind,phase,t);body.data.vertices.foreach_set('co',(vertices*[1,-1,1]/100).ravel());body.data.update()
  head.data.vertices.foreach_set('co',(hp*[1,-1,1]/100).ravel());head.data.update()
  s.render.filepath=str(ROOT/(kind+'_hold.png')) if still else str(dest/f'{i:04d}.png')
  bpy.ops.render.render(write_still=True)
 (ROOT/(kind+'_timeline.json')).write_text(json.dumps(timeline))
 bpy.data.objects.remove(furniture,do_unlink=True)
print('REST_REVIEW_RENDERED', 'stills' if still else 'sequences')
