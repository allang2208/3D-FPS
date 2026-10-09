"""V04 motion-corrective garment surfaces; complete Meshy body stays intact."""
import bpy,bmesh,math,json,shutil,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessReceptionist20261007/V04')
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'V03/Authoring/FacelessReceptionist_V03.blend'))
s=bpy.context.scene;body=bpy.data.objects['Receptionist_CompleteBody'];rig=bpy.data.objects['root']
rig.animation_data.action=None
for tr in rig.animation_data.nla_tracks:tr.mute=True
s.frame_set(0)
raw=list(rig['source_world_matrix']);rig.matrix_world=Matrix([raw[i:i+4] for i in range(0,16,4)])
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
for f in (ROOT.parent/'V03/Textures').glob('*.png'):shutil.copy2(f,ROOT/'Textures'/f.name)
for im in bpy.data.images:
 f=ROOT/'Textures'/Path(bpy.path.abspath(im.filepath)).name
 if f.exists():im.filepath=str(f)
names=list(np.load(ROOT/'MotionSources/deform_attack.npz')['names']);index={n:i for i,n in enumerate(names)}
def pts(o):return np.array([v.co[:] for v in o.data.vertices],np.float64)
def skin(o):
 w=np.zeros((len(o.data.vertices),len(names)))
 for v in o.data.vertices:
  for g in v.groups:
   n=o.vertex_groups[g.group].name
   if n in index:w[v.index,index[n]]=g.weight
 return w
def compact(w):return [(j,np.where(w[:,j]>1e-7)[0],w[w[:,j]>1e-7,j]) for j in range(w.shape[1]) if np.any(w[:,j]>1e-7)]
def deform(p,w,m):
 out=np.zeros_like(p)
 for j,ids,ws in w:out[ids]+=((p[ids]@m[j,:3,:3].T)+m[j,:3,3])*ws[:,None]
 return out
def setskin(o,w):
 o.vertex_groups.clear()
 for j in np.where(w.max(axis=0)>1e-7)[0]:
  g=o.vertex_groups.new(name=names[j])
  for i in np.where(w[:,j]>1e-7)[0]:g.add([int(i)],float(w[i,j]),'REPLACE')
def smooth(a,b,x):
 t=np.clip((x-a)/(b-a),0,1);return t*t*(3-2*t)
bp=pts(body);bw=skin(body);bc=compact(bw)
body.data.calc_loop_triangles();tri=np.array([t.vertices[:] for t in body.data.loop_triangles])
bvh=BVHTree.FromPolygons([Vector(p) for p in bp],tri,all_triangles=True)
# Rebuild a continuous shoulder yoke from the matching body's own topology.
# It overlaps the outer sleeve/chest seams and closes the old voxel-cut openings.
yoke=body.copy();yoke.data=body.data.copy();s.collection.objects.link(yoke);yoke.name='Receptionist_ShoulderYoke'
yoke.data.materials.clear();yoke.data.materials.append(bpy.data.materials['Receptionist_Suit'])
bm=bmesh.new();bm.from_mesh(yoke.data)
remove=[]
for f in bm.faces:
 c=f.calc_center_median()
 if not (1.345<c.z<1.545 and abs(c.x)<.269 and (abs(c.x)>.053 or c.y>.007)):remove.append(f)
bmesh.ops.delete(bm,geom=remove,context='FACES')
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000015)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
bm.normal_update()
for v in bm.verts:v.co+=v.normal*.022
bmesh.ops.smooth_vert(bm,verts=list(bm.verts),factor=.35,use_axis_x=True,use_axis_y=True,use_axis_z=True)
for _ in range(12):bmesh.ops.smooth_vert(bm,verts=list(bm.verts),factor=.32,use_axis_x=True,use_axis_y=True,use_axis_z=True)
bm.to_mesh(yoke.data);bm.free()
for f in yoke.data.polygons:f.material_index=0;f.use_smooth=True
yoke.data.normals_split_custom_set([(0,0,0)]*len(yoke.data.loops))
yoke_weights=np.zeros((len(yoke.data.vertices),len(names)))
for vertex in yoke.data.vertices:
 p=vertex.co;side='l' if p.x>0 else 'r';arm=float(smooth(.07,.245,abs(p.x)));clav=.22*math.sin(math.pi*arm)
 yoke_weights[vertex.index,index['spine_05']]=1-arm-clav*.5
 yoke_weights[vertex.index,index['upperarm_'+side]]=arm-clav*.5
 yoke_weights[vertex.index,index['clavicle_'+side]]=clav
setskin(yoke,yoke_weights)
# Replace the inner shoulder cap instead of allowing two nearby shells to fight.
jacket_obj=bpy.data.objects['Receptionist_Blazer_Continuous']
bm=bmesh.new();bm.from_mesh(jacket_obj.data);remove=[]
for f in bm.faces:
 c=f.calc_center_median()
 if c.z>1.39 and abs(c.x)<.235 and (abs(c.x)>.070 or c.y>.005):remove.append(f)
bmesh.ops.delete(bm,geom=remove,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(jacket_obj.data);bm.free()
# The shirt is an inner layer: retain its visible front bib; its old closed
# shoulder/back shell intersected the coat in the photographed attack pose.
shirt_obj=bpy.data.objects['Receptionist_Shirt_Continuous']
bm=bmesh.new();bm.from_mesh(shirt_obj.data);remove=[]
for f in bm.faces:
 c=f.calc_center_median();opening=float(np.interp(c.z,[1.15,1.30,1.42,1.49,1.56],[.005,.045,.084,.093,.072]))
 if c.y>-.012 or abs(c.x)>opening:remove.append(f)
bmesh.ops.delete(bm,geom=remove,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(shirt_obj.data);bm.free()
def attachment(p):
 h=bvh.find_nearest(Vector(p));ids=tri[h[2]]
 bary=barycentric_transform(h[0],*(Vector(bp[i]) for i in ids),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
 b=np.clip(np.array(bary),0,1);b/=b.sum()
 return ids,b,np.array(h[0]),np.array(h[1])
# Rebind the shoulder surface to the body's own local support instead of diluted
# nearest-donor weights. This keeps the visible shoulder and sleeve cap together.
for name in ['Receptionist_Blazer_Continuous','Receptionist_Shirt_Continuous']:
 o=bpy.data.objects[name];p=pts(o);w=skin(o)
 for i in range(len(p)):
  if p[i,2]<1.235:continue
  ids,b,hit,n=attachment(p[i]);target=(bw[ids]*b[:,None]).sum(axis=0)
  blend=float(smooth(1.235,1.345,p[i,2]));w[i]=w[i]*(1-blend)+target*blend
 setskin(o,w)

# Garment wraps store body-surface attachment independent of the garment LBS.
# During the source pose they produce a local corrective, without editing bones.
objects=[o for o in s.objects if o.type=='MESH' and o!=body]
garments={};supported=[]
for o in objects:
 p=pts(o);w=skin(o)
 if o.name.startswith('Receptionist_Skirt') or 'VentFinish' in o.name:
  kind='skirt'
 elif o.name in ['Receptionist_Blazer_Continuous','Receptionist_Shirt_Continuous']:
  kind='upper'
 elif o.name.startswith(('Receptionist_Lapel','Receptionist_Blazer_Back','Receptionist_SleeveSeam','Receptionist_NameBadge','Receptionist_Badge')):
  kind='upper_detail'
 else:continue
 data={'object':o,'points':p,'weights':w,'packed':compact(w),'kind':kind}
 if kind.startswith('upper'):
  attached=[attachment(v) for v in p]
  data['ids']=np.array([a[0] for a in attached]);data['bary']=np.array([a[1] for a in attached]);data['rest_hit']=np.array([a[2] for a in attached]);data['rest_normal']=np.array([a[3] for a in attached])
  data['offset']=p-data['rest_hit']
  data['wrap_weights']=(bw[data['ids']]*data['bary'][:,:,None]).sum(axis=1)
  data['fade']=smooth(1.26,1.38,p[:,2])
  if kind=='upper_detail':data['fade']=smooth(1.26,1.38,p[:,2])
 garments[o.name]=data;o.shape_key_add(name='Basis');supported.append(o)

# Broad continuous skirt cage from the actual posed legs, with a closed front.
# Sections follow the mean leg line; their radii enclose both legs together.
zlevels=np.linspace(.455,1.145,48)
legids=[np.where((abs(bp[:,2]-z)<.023)&(abs(bp[:,0])<.36))[0] for z in zlevels]
centers_rest=np.array([bp[ids].mean(axis=0) for ids in legids])
theta=np.linspace(-math.pi,math.pi,128,endpoint=False)
directions=np.stack([np.sin(theta),-np.cos(theta)],axis=1)
def skirt_cage(posed,m):
 pelvis_x=m[index['pelvis'],:3,:3]@np.array([1.,0,0])
 pelvis_x[2]=0;pelvis_x/=np.linalg.norm(pelvis_x)
 x=pelvis_x;y=np.cross(np.array([0.,0.,1.]),x)
 waist=m[index['pelvis'],:3,:3]@np.array([0.,.027,1.105])+m[index['pelvis'],:3,3]
 lower=posed[(bp[:,2]<1.15)&(bp[:,2]>.23)&(abs(bp[:,0])<.35)]
 sections=[]
 for i,z in enumerate(zlevels):
  height=waist[2]+(z-1.105)*.92
  band=lower[np.abs(lower[:,2]-height)<.032]
  if len(band)<4:band=lower[np.argsort(np.abs(lower[:,2]-height))[:64]]
  c=np.array([(band[:,0].min()+band[:,0].max())*.5,(band[:,1].min()+band[:,1].max())*.5,height])
  local=np.stack([(band-c)@x,(band-c)@y],axis=1)
  support=(local@directions.T).max(axis=0)+.035
  support=np.maximum(support,.09)
  dots=directions@directions.T
  radius=np.min(np.where(dots>.02,support[None,:]/np.maximum(dots,.02),100),axis=1)
  for _ in range(4):radius=(radius*2+np.roll(radius,1)+np.roll(radius,-1))/4
  sections.append((c,x,y,radius))
 # Smooth along the cloth, retaining all envelope extrema with a small margin.
 centers=np.array([e[0] for e in sections]);radii=np.array([e[3] for e in sections])
 for _ in range(5):
  centers[1:-1]=.5*centers[1:-1]+.25*(centers[:-2]+centers[2:])
  radii[1:-1]=np.maximum(radii[1:-1],.5*radii[1:-1]+.25*(radii[:-2]+radii[2:]))
 sections=[(c,x,y,r) for c,r in zip(centers,radii)]
 return sections
def target_skirt(p,posed,sections,m):
 out=np.empty_like(p);base=deform(p,compact_current,m)
 for i,v in enumerate(p):
  f=np.clip((v[2]-zlevels[0])/(zlevels[-1]-zlevels[0])*(len(zlevels)-1),0,len(zlevels)-1-1e-6);j=int(f);t=f-j
  c,x,y,r=sections[j];c2,x2,y2,r2=sections[j+1]
  c=c*(1-t)+c2*t;x=x*(1-t)+x2*t;y=y*(1-t)+y2*t;r=r*(1-t)+r2*t
  ang=math.atan2(v[0],-(v[1]-.027));rad=float(np.interp(ang,theta,r,period=2*math.pi))
  # The original broad A-line remains minimum width in neutral poses.
  rad=max(rad,math.hypot(v[0],v[1]-.027)*.90)
  target=c+rad*(x*math.sin(ang)-y*math.cos(ang))
  f=float(smooth(1.105,1.025,v[2]))
  out[i]=base[i]*(1-f)+target*f
 return out

curves={};manifest={};checks={}
for role in ['idle','walk','attack']:
 allm=np.load(ROOT/'MotionSources'/('deform_'+role+'.npz'))['matrices'];frames=len(allm)
 samples=sorted(set(list(range(0,frames,20 if role=='idle' else 5))+[frames-1]))
 keys=[f'FR4_{role}_{f:03}' for f in samples];curves[role]={k:[] for k in keys};manifest[role]={'frames':frames,'samples':samples}
 for frame in range(frames):
  for k,sp in zip(keys,samples):curves[role][k].append(float(np.interp(frame,samples,[1. if f==sp else 0. for f in samples])))
 for frame,key in zip(samples,keys):
  m=allm[frame];posed=deform(bp,bc,m);sections=skirt_cage(posed,m)
  for name,data in garments.items():
   o=data['object'];p=data['points'];w=data['weights'];current=deform(p,data['packed'],m)
   if data['kind']=='skirt':
    compact_current=data['packed'];current_weights=w;target=target_skirt(p,posed,sections,m)
    if name in ['Receptionist_Skirt','Receptionist_Skirt_BackVentUnderlap','Receptionist_Skirt_Waistband']:
     half=len(p)//2
     target[half:]=target[:half]+(current[half:]-current[:half])
   else:
    ids=data['ids'];b=data['bary'];hit=(posed[ids]*b[:,:,None]).sum(axis=1)
    wrap_m=np.einsum('nb,bij->nij',data['wrap_weights'],m[:,:3,:3])
    offset=np.einsum('nij,nj->ni',wrap_m,data['offset'])
    normal=np.cross(posed[ids[:,1]]-posed[ids[:,0]],posed[ids[:,2]]-posed[ids[:,0]])
    normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-8)
    # Guarantee cloth-side clearance; keep existing tangential tailoring offset.
    distance=np.sum(offset*normal,axis=1)
    ease=.016 if name=='Receptionist_Blazer_Continuous' else .006 if name=='Receptionist_Shirt_Continuous' else .019
    offset+=normal*np.minimum(.008,np.maximum(0,ease-distance))[:,None]
    target=current+(hit+offset-current)*data['fade'][:,None]
   linear=np.einsum('nb,bij->nij',w,m[:,:3,:3]);delta=target-current
   corrective=np.linalg.solve(linear,delta[:,:,None])[:,:,0]
   # Morph coordinates are authored in bind space; skinning applies afterwards.
   shape=o.shape_key_add(name=key);shape.data.foreach_set('co',(p+corrective).astype(np.float32).ravel())
  if frame%20==0:print('V04_CORRECTIVE',role,frame,flush=True)

(ROOT/'corrective_curves.json').write_text(json.dumps(curves),encoding='utf-8')
(ROOT/'corrective_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

# Woven microrelief at a fixed 20 cm tile size, shared height -> normal/roughness.
# Retain original body maps; the six existing material families remain separate.
size=2048;yy,xx=np.mgrid[:size,:size];u=xx/size;v=yy/size
warp=np.sin(2*math.pi*u*256);weft=np.sin(2*math.pi*v*256)
mask=((np.floor(u*256)+np.floor(v*256))%4<2)
h=.28*np.where(mask,warp,weft)+.08*np.sin(2*math.pi*(u-v)*64)
macro=.5*np.sin(2*math.pi*u*3)*np.sin(2*math.pi*v*5)+.23*np.sin(2*math.pi*(u+v)*11)
dy,dx=np.gradient(h);normal=np.stack([-dx*.32,-dy*.32,np.ones_like(h)],axis=-1);normal/=np.linalg.norm(normal,axis=-1)[:,:,None]
def imagefile(name,array,data=False):
 im=bpy.data.images.new(name,width=size,height=size,alpha=False)
 if data:im.colorspace_settings.name='Non-Color'
 rgba=np.ones((size,size,4),np.float32);rgba[:,:,:3]=array;im.pixels.foreach_set(rgba.ravel())
 im.filepath_raw=str(ROOT/'Textures'/(name+'.png'));im.file_format='PNG';im.save();return im
for family,color,rough in [('Suit',(.080,.094,.111),.79),('Shirt',(.58,.56,.505),.86),('Trim',(.047,.052,.059),.87)]:
 name='Receptionist_'+family
 base=np.clip(np.array(color)[None,None,:]*(1+.075*h[:,:,None]+.032*macro[:,:,None]),0,1)
 orm=np.ones((size,size,3));orm[:,:,1]=np.clip(rough-.065*h+.026*macro,.60,.95);orm[:,:,2]=0
 images=[imagefile(name+'_BaseColor',base),imagefile(name+'_Normal',normal*.5+.5,True),imagefile(name+'_ORM',orm,True)]
 mat=bpy.data.materials[name]
 for n in mat.node_tree.nodes:
  if n.type=='TEX_IMAGE' and n.image:
   n.image=images[1 if '_Normal' in n.image.name else 2 if '_ORM' in n.image.name else 0]
 bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 bs.inputs['Specular IOR Level'].default_value=.27;bs.inputs['Sheen Weight'].default_value=.18 if family=='Suit' else .09
 # Each fabric UV coordinate is physical, while motion keeps it bound to cloth.
for o in objects:
 if not o.data.uv_layers:continue
 if not any(m and m.name in ['Receptionist_Suit','Receptionist_Shirt','Receptionist_Trim'] for m in o.data.materials):continue
 uv=o.data.uv_layers.active
 for loop in o.data.loops:
  p=o.data.vertices[loop.vertex_index].co
  if 'Skirt' in o.name or 'Vent' in o.name:
   angle=math.atan2(p.x,-(p.y-.027));coord=(angle*.22/.20,p.z/.20)
  elif abs(p.x)>.215 and p.z>1.13:
   side='l' if p.x>0 else 'r';a=rig.matrix_world@rig.data.bones['upperarm_'+side].head_local;c=rig.matrix_world@rig.data.bones['hand_'+side].head_local
   axis=(c-a).normalized();along=(p-a).dot(axis);q=p-a-axis*along;theta2=math.atan2(q.z,q.y);coord=(theta2*.055/.20,along/.20)
  else:coord=(p.x/.20,p.z/.20)
  uv.data[loop.index].uv=coord
for o in supported:
 for key in o.data.shape_keys.key_blocks:key.value=0
# Keep the complete body as an authoring/standalone asset. The assembled outfit
# uses a separate body display mesh with only always-covered interior faces culled.
display=body.copy();display.data=body.data.copy();s.collection.objects.link(display);display.name='Receptionist_OutfitBody'
bm=bmesh.new();bm.from_mesh(display.data)
remove=[]
for f in bm.faces:
 c=f.calc_center_median();x=abs(c.x)
 covered=(.57<c.z<1.15 and x<.30) or (1.12<c.z<1.51 and x<.32) or (1.345<c.z<1.535 and .056<x<.27)
 if covered:remove.append(f)
bmesh.ops.delete(bm,geom=remove,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(display.data);bm.free()
body.hide_render=True;body.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V04.blend'))
report={'version':'V04','complete_body_preserved':True,'bone_animation_tracks_changed':False,'corrective_keys':sum(len(v['samples']) for v in manifest.values()),'garment_objects':len(garments),'corrective_source':'current UE idle/walk/attack exports','shoulder':'body triangle support with pose corrective clearance','skirt':'continuous two-leg envelope per source pose','cloth_simulation':False,'runtime_tested':False}
(ROOT/'authoring_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('V04_AUTHOR_SAVED',json.dumps(report),flush=True)
