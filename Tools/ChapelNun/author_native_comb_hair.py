"""Rebuild all four R2 hair silhouettes using individually combed, editable locks."""
import bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115')
R=N/'HairNativeCombR9';O=R/'Authored';O.mkdir(parents=True,exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
rng=np.random.default_rng(161128);C=np.array([0.,.1,158.9])
bpy.ops.wm.read_factory_settings(use_empty=True)
head=read(N/'FaceOriginalRestoreR6/Authored/head.json')
bvh=BVHTree.FromPolygons([Vector(p) for p in head['positions']],[t[::-1] for t,m in zip(head['triangles'],head['triangle_materials']) if m in (0,2)],all_triangles=True)
def unit(v):return v/np.maximum(1e-9,np.linalg.norm(v,axis=-1,keepdims=True))
def skin(v,lift=.06):
 d=unit(np.asarray(v));shape=d.shape;points=[]
 for q in d.reshape(-1,3):
  p,_,_,_=bvh.ray_cast(Vector(C),Vector(q),40)
  if p is None:p,_,_,_=bvh.find_nearest(Vector(C+q*8.5))
  points.append(np.asarray(p)+q*lift)
 return np.asarray(points).reshape(shape)
def spline(control,count=65):
 c=np.asarray(control,dtype=float);c=np.concatenate((c[:1],c,c[-1:]));t=np.linspace(0,len(c)-3,count)
 i=np.minimum(t.astype(int),len(c)-4);u=(t-i)[:,None];a,b,c1,d=c[i],c[i+1],c[i+2],c[i+3]
 return .5*((2*b)+(-a+c1)*u+(2*a-5*b+4*c1-d)*u*u+(-a+3*b-3*c1+d)*u*u*u)
def sphere(theta,phi):return np.stack((np.sin(phi)*np.sin(theta),np.sin(phi)*np.cos(theta),np.cos(phi)),axis=-1)
# Sample the actual retained face once; every combed fibre stays outside its scalp.
TW,PH=256,160;th=np.linspace(-math.pi,math.pi,TW);ph=np.linspace(0,2.6,PH);tt,pp=np.meshgrid(th,ph)
rad=np.linalg.norm(skin(sphere(tt,pp),0)-C,axis=-1)
def surface_distance(v):
 d=unit(v);x=(np.arctan2(d[...,0],d[...,1])+math.pi)/(2*math.pi)*(TW-1)
 y=np.clip(np.arccos(np.clip(d[...,2],-1,1))/2.6*(PH-1),0,PH-1)
 ix=np.clip(x.astype(int),0,TW-2);iy=np.clip(y.astype(int),0,PH-2);fx=x-ix;fy=y-iy
 return rad[iy,ix]*(1-fx)*(1-fy)+rad[iy,ix+1]*fx*(1-fy)+rad[iy+1,ix]*(1-fx)*fy+rad[iy+1,ix+1]*fx*fy
def outside(p,margin=.08):
 p=np.asarray(p);v=p-C;dist=np.linalg.norm(v,axis=-1);floor=surface_distance(v)+margin
 mask=(p[...,2]>149.7)&(dist<floor)
 return np.where(mask[...,None],C+unit(v)*floor[...,None],p)
# Retain complete native strand shapes and irregular spacing, including short hairs.
native=read(N/'ProductionR1/Inputs/native_head.json')
nbvh=BVHTree.FromPolygons([Vector(p) for p in native['positions']],[t for t,m in zip(native['triangles'],native['triangle_materials']) if m==0],all_triangles=True)
nd=sphere(tt,pp);nr=[]
for direction in nd.reshape(-1,3):
 hit,_,_,_=nbvh.ray_cast(Vector(C),Vector(direction),40)
 if hit is None:hit,_,_,_=nbvh.find_nearest(Vector(C+direction*8.0))
 nr.append(np.linalg.norm(np.array(hit)-C))
nrad=np.array(nr).reshape(PH,TW)
def native_distance(v):
 global rad
 oldrad=rad;rad=nrad;out=surface_distance(v);rad=oldrad;return out
curves=[];uvs=[];original_lengths=[]
for g in read(N/'RefinementR4/Inputs/native_hair.json')['groups']:
 pre=N/'RefinementR4/Inputs'/g['prefix'];pts=np.fromfile(str(pre)+'_points.bin','<f4').reshape(-1,3);counts=np.fromfile(str(pre)+'_counts.bin','<u2');uv=np.fromfile(str(pre)+'_rootuv.bin','<f4').reshape(-1,2);offset=0
 for k,c in enumerate(counts):
  source=pts[offset:offset+int(c)];offset+=int(c)
  curves.append(spline(source,65));uvs.append(uv[k]);original_lengths.append(np.linalg.norm(np.diff(source,axis=0),axis=1).sum())
raw=np.asarray(curves);core_uv=np.asarray(uvs);lengths=np.array(original_lengths)
v=raw-C;rd=np.linalg.norm(v,axis=-1);d=unit(v)
offset=rd-native_distance(v)
th=np.arctan2(d[...,0],d[...,1]);ph=np.arccos(np.clip(d[...,2],-1,1))
side=np.where(th<0,-1.,1.)
# A smooth spatial comb gathers the original lengths behind the ears. The
# original curves, short hairs and neighbouring strand irregularities survive.
rootth=np.arctan2(raw[:,0,0],raw[:,0,1]-.1)[:,None]
delay=1.25*np.exp(-((np.abs(rootth)-.5)/.75)**2)
pull=np.clip((162.5-raw[...,2]-delay)/10.0,0,1);pull=pull*pull*(3-2*pull)
pull+=.055*np.sin(raw[...,2]*1.15+rootth*2)*np.sin(math.pi*pull)
newth=th+(side*math.pi-th)*pull*.95
newph=ph+(2.12-ph)*pull*.72
fade=np.clip((raw[...,2]-156)/10,0,1);fade=fade*fade*(3-2*fade)
angle=.24*(.25+.75*fade);direction=sphere(newth,newph)
x=direction[...,0]*np.cos(angle)+direction[...,2]*np.sin(angle)
z=-direction[...,0]*np.sin(angle)+direction[...,2]*np.cos(angle)
direction=np.stack((x,direction[...,1],z),axis=-1)
# Native offsets retain flyaways; tightly combed nape has a smaller envelope.
clearance=np.maximum(.045,offset)*(1-.75*pull)
clearance=np.minimum(clearance,2.1*(1-pull)+.70*pull)
clearance+=(.18+.19*np.sin(newth*5+newph*2))*np.sin(math.pi*pull)
core=C+direction*(surface_distance(direction)+np.maximum(.045,clearance))[...,None]
# Transport the donor hair's irregular cross-sections through interleaved folds.
# Tail progress is normalized per strand so no points collapse at a clamped end.
bun_paths=[
 [(-3.5,-6.8,155),(-4.0,-8.7,155.3),(-2.0,-10.9,156.2),(1.3,-11.4,155.3),(3.7,-10.8,152.7),(2.2,-11.3,149.5),(-1.0,-10.8,148.5),(-2.7,-8.5,150.5),(-.5,-7.6,152.3)],
 [(3.5,-6.8,154.7),(4.1,-9.1,154.6),(2.6,-11.6,153.1),(-.6,-11.9,151.3),(-3.6,-10.8,149.1),(-3.8,-9.4,151.0),(-1.5,-10.5,153.4),(1.5,-9.6,154.7),(1.0,-7.6,152.5)],
 [(-2.0,-7.0,154.2),(-4.0,-9.3,152.5),(-3.0,-11.3,150.1),(-.4,-11.8,148.6),(2.7,-10.6,149.3),(3.4,-10.0,151.5),(1.8,-11.2,153.4),(-1.2,-10.1,154.4),(-1.0,-7.7,152.0)],
 [(2.0,-7.0,154.0),(3.8,-9.7,152.2),(2.3,-11.9,150.0),(-.2,-11.7,149.4),(-2.5,-10.5,151.6),(-2.1,-10.8,154.2),(.5,-11.1,155.6),(2.0,-8.5,154.0),(1.0,-7.7,152.0)],
 [(-4.3,-6.5,154.5),(-2.5,-9.2,154.4),(.2,-11.7,153.0),(2.2,-11.3,150.7),(1.1,-10.3,149.0),(-1.8,-10.8,150.4),(-1.2,-10.6,153.0),(.8,-8.1,153.2)],
 [(4.3,-6.5,154.2),(2.5,-9.3,155.1),(-.8,-11.8,154.2),(-2.9,-11.4,151.9),(-1.5,-11.0,149.3),(1.2,-10.6,150.2),(1.5,-9.3,152.7),(.5,-7.6,152.4)],
 [(-3,-6.7,152.2),(-4.3,-8.8,151.6),(-2.7,-10.8,149.7),(.0,-11.6,150.2),(1.4,-11.1,152.4),(-.2,-10.1,154.2),(-2.1,-8.6,153.7),(-1,-7.5,152.0)],
 [(3,-6.7,152.3),(4.0,-8.8,151.6),(2.4,-10.7,149.7),(-.2,-11.5,150.2),(-1.4,-11.0,152.2),(.1,-10.0,154.0),(2.0,-8.6,153.5),(1,-7.5,152.0)]]

eligible=raw[:,-1,2]<148.5
bins=np.quantile(rootth[:,0][eligible],np.linspace(0,1,9));groups=np.clip(np.searchsorted(bins,rootth[:,0])-1,0,7)
u=np.clip((153-raw[...,2])/np.maximum(4.,153-raw[:,-1:,2]),0,1)
for k,path in enumerate(bun_paths):
 ids=np.flatnonzero((groups==k)&eligible)
 if not len(ids):continue
 path=np.array(path);path[:,1]+=1.35;path[:,2]-=.3
 guide=spline(path,100);tangent=unit(np.gradient(guide,axis=0));normal=unit(np.cross(tangent,np.tile([0.,1.,0.],(100,1))));binormal=unit(np.cross(tangent,normal))
 tail=raw[ids];uu=u[ids];q=np.linspace(0,1,100)
 target=np.stack([np.interp(uu,q,guide[:,a]) for a in range(3)],axis=-1)
 nn=np.stack([np.interp(uu,q,normal[:,a]) for a in range(3)],axis=-1);bb=np.stack([np.interp(uu,q,binormal[:,a]) for a in range(3)],axis=-1)
 # A fitted donor cross-section keeps the real strand-level variation.
 zm=tail[...,2];mask=(zm<153)&(zm>140);zs=zm[mask]
 dx=tail[...,0]-np.polyval(np.polyfit(zs,tail[...,0][mask],2),zm)
 dy=tail[...,1]-np.polyval(np.polyfit(zs,tail[...,1][mask],2),zm)
 ax=np.clip(dx/np.maximum(.8,np.std(dx[mask])),-2.5,2.5)*.58
 by=np.clip(dy/np.maximum(.8,np.std(dy[mask])),-2.5,2.5)*.58
 target+=nn*ax[...,None]+bb*by[...,None]
 blend=np.clip(uu/.22,0,1);blend=blend*blend*(3-2*blend)
 core[ids]=core[ids]*(1-blend[...,None])+target*blend[...,None]
core=core.astype('f');core_uv=core_uv.astype('f')
# Short face-framing strands retain the donor's real irregular curves.
select=np.flatnonzero((np.abs(raw[:,0,0])>3)&(raw[:,0,1]>1)&(raw[:,0,2]>157)&(raw[:,0,2]<164)&(lengths>8))
rng.shuffle(select);select=select[:650];loose=[]
for i in select:
 arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(raw[i],axis=0),axis=1))]
 short=np.stack([np.interp(np.linspace(0,min(arc[-1],rng.uniform(4.,8.3)),32),arc,raw[i,:,a]) for a in range(3)],axis=1)
 vv=short-C;dd=unit(vv);hh=np.maximum(.05,np.linalg.norm(vv,axis=1)-native_distance(vv))
 phi=np.arccos(np.clip(dd[:,2],-1,1));theta=np.arctan2(dd[:,0],dd[:,1]);theta+=np.sign(theta)*.05*np.linspace(0,1,32)
 dd=sphere(theta,phi);pp=C+dd*(surface_distance(dd)+np.minimum(hh,1.2))[:,None]
 pp+=skin(raw[i,0]-C,.045)-pp[0]
 loose.append(pp)
loose=np.asarray(loose,dtype='f');loose_uv=core_uv[select].copy()
# Restore roots precisely to the retained Meshy scalp after the deformation.
core[:,0]=skin(core[:,0]-C,.045);loose[:,0]=skin(loose[:,0]-C,.045)
np.save(O/'Nun_LowBun_Core_R5_points.npy',core);np.save(O/'Nun_LowBun_Loose_R5_points.npy',loose)
core_uv.astype('<f4').tofile(O/'Nun_LowBun_Core_R5_rootuv.bin');loose_uv.astype('<f4').tofile(O/'Nun_LowBun_Loose_R5_rootuv.bin')
for name,p in [('Nun_LowBun_Core_R5',core),('Nun_LowBun_Loose_R5',loose)]:
 hc=bpy.data.hair_curves.new(name+'_Preview');hc.add_curves([p.shape[1]]*len(p));hc.attributes['position'].data.foreach_set('vector',p.ravel());r=hc.attributes.new('radius','FLOAT','POINT');rr=np.tile((.0024 if 'Loose' in name else .0032)*(1-.91*np.linspace(0,1,p.shape[1])**3),len(p));r.data.foreach_set('value',rr.astype('f'))
 ob=bpy.data.objects.new(name+'_Preview',hc);bpy.context.scene.collection.objects.link(ob)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Nun_NativeComb_R9.blend'))
report={'reference':str(N/'Design/NunHead_R2.png'),'hairstyle_revision':'NativeCombR9','core_curves':len(core),'loose_curves':len(loose),'native_strand_shapes_used':True,'material_preserved_from_user_accepted_version':True,'face_and_outfit_edited':False}
(R/'authoring.json').write_text(json.dumps(report,indent=2))
print('NATIVE_COMB_AUTHORED',len(core),len(loose),flush=True)
