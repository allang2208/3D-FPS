"""Rebuild all four R2 hair silhouettes using individually combed, editable locks."""
import bpy, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
N=Path('D:/FPS3D/FPSGAME/SourceAssets/ChapelNun20261115')
R=N/'HairFullReferenceR8';O=R/'Authored';O.mkdir(parents=True,exist_ok=True)
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
native_roots=[];native_uv=[]
for g in read(N/'RefinementR4/Inputs/native_hair.json')['groups']:
 prefix=N/'RefinementR4/Inputs'/g['prefix'];pts=np.fromfile(str(prefix)+'_points.bin','<f4').reshape(-1,3)
 counts=np.fromfile(str(prefix)+'_counts.bin','<u2');offset=np.r_[0,np.cumsum(counts[:-1])]
 native_roots.append(pts[offset]);native_uv.append(np.fromfile(str(prefix)+'_rootuv.bin','<f4').reshape(-1,2))
native_roots=np.concatenate(native_roots);native_uv=np.concatenate(native_uv)
angle=.27;rot=np.array([[math.cos(angle),0,math.sin(angle)],[0,1,0],[-math.sin(angle),0,math.cos(angle)]])
def part_root(f,side):
 a=.78-1.58*f;d=np.array([math.sin(angle)*math.cos(a)+side*.024,math.sin(a),math.cos(angle)*math.cos(a)])
 return skin(d,.06)
core=[];core_uv=[];guides=[];regions=[]
def emit_lock(label,control,hairs=420,width=.55,depth=.24,wave=.12,protect=True,twist=.25):
 guide=spline(control);q=np.linspace(0,1,len(guide))
 if protect:
  v=guide-C;sd=surface_distance(v);raw=np.linalg.norm(v,axis=1)-sd
  # Keep the complete outer comb supported by the scalp. Unbounded control
  # points create detached ribbon arches instead of the reference's soft waves.
  h=np.clip(raw,.09,.62)+.12*np.sin(q*math.tau*1.6+len(guides)*.55)*np.sin(math.pi*q)
  root_blend=np.clip(q/.08,0,1);root_blend=root_blend*root_blend*(3-2*root_blend)
  h=.06+(h-.06)*root_blend;guide=C+unit(v)*(sd+h)[:,None]
 tangent=unit(np.gradient(guide,axis=0));normal=unit(np.cross(tangent,unit(guide-C)))
 bad=np.linalg.norm(normal,axis=1)<.5
 normal[bad]=unit(np.cross(tangent[bad],np.tile([0.,0.,1.],(bad.sum(),1))))
 binormal=unit(np.cross(tangent,normal))
 # Fibres form an overlapping continuous volume, without seven tight sub-clumps.
 # Broad root distributions and staggered ends avoid pointed, separated ribbons.
 az=rng.uniform(0,math.tau,hairs);rr=np.sqrt(rng.uniform(0,1,hairs))
 offsets=np.stack((rr*np.cos(az),rr*np.sin(az)),axis=1)
 phase=rng.uniform(0,math.tau,(hairs,1));sub=rng.uniform(0,7,hairs)
 taper=.82+.18*np.sin(math.pi*q);taper[-8:]*=np.linspace(1,.38,8)
 spin=twist*q*math.tau
 a=offsets[:,0,None]*np.cos(spin)-offsets[:,1,None]*np.sin(spin)
 b=offsets[:,0,None]*np.sin(spin)+offsets[:,1,None]*np.cos(spin)
 p=guide[None]+normal[None]*(a*width*taper)[...,None]+binormal[None]*(b*depth*taper)[...,None]
 wobble=(wave*np.sin(q[None]*math.tau*1.7+sub[:,None]*.75)+.045*np.sin(q[None]*49+phase))*np.sin(math.pi*q)[None]
 p+=normal[None]*wobble[...,None]
 if protect:
  p=outside(p,.035);p[:,0]=skin(p[:,0]-C,.055)
 core.append(p);core_uv.append(native_uv[rng.integers(0,len(native_uv),hairs)])
 guides.append((label,guide));regions.append({'name':label,'strands':hairs,'width_cm':width})

# Continuous follicle field: every fibre is rooted across the actual scalp.
# The comb flow passes around the sides and crown, never across the face.
count=88000
th=rng.uniform(-math.pi,math.pi,220000);ph=np.arccos(rng.uniform(-.56,1,220000))
limit=np.interp(np.abs(th),[0,.45,.85,1.15,1.55,1.9,2.4,math.pi],[.94,.99,1.12,1.37,1.55,1.78,2.02,2.10])
limit+=.12*np.exp(-((th+.88)/.40)**2)
chosen=rng.choice(np.flatnonzero(ph<limit),count,replace=False)
d=sphere(th[chosen],ph[chosen]);local=d@rot
start_th=np.arctan2(local[:,0],local[:,1])[:,None]
start_ph=np.arccos(np.clip(local[:,2],-1,1))[:,None]
side=np.where(start_th<0,-1.,1.)
q=np.linspace(0,1,65)[None,:]
end_th=side*(math.pi+rng.uniform(-.20,.20,(count,1)))
end_ph=rng.uniform(1.97,2.12,(count,1))
flow_th=start_th+(end_th-start_th)*q**rng.uniform(.9,1.12,(count,1))
flow_ph=start_ph+(end_ph-start_ph)*q-.07*np.sin(math.pi*q)
phase=rng.uniform(0,math.tau,(count,1))
flow_th+=.022*np.sin(19*q+phase)*np.sin(math.pi*q)
flow_ph+=.016*np.sin(22*q+phase*1.7)*np.sin(math.pi*q)
flow=sphere(flow_th,flow_ph)@rot.T
radius=surface_distance(flow)
# Small continuous surface waves, independent strand noise and variable lift.
# No repeated thick parent locks or disconnected clump roots.
layer=rng.uniform(.22,.88,(count,1))
broad_wave=.30*np.sin(4*flow_th+2.2*flow_ph)+.16*np.sin(7*flow_th-2.8*flow_ph)
noise=rng.uniform(.025,.10,(count,1))*np.sin(q*rng.uniform(14,24,(count,1))+phase)
noise+=.025*np.sin(47*q+phase*1.4)
rise=1-np.exp(-q*45)
height=.04+rise*np.maximum(.09,layer+broad_wave+noise)
p=C+flow*(radius+height)[...,None]
core.append(p);core_uv.append(native_uv[rng.integers(0,len(native_uv),count)])
regions.append({'name':'continuous_waved_follicle_field','strands':count})
for i in np.linspace(0,count-1,120).astype(int):guides.append(('continuous_comb_'+str(i),p[i]))
# Dense forehead sweep with continuously distributed roots. Individual guides
# overlap closely and remain within the continuous field instead of sitting on it.
for side,num in [(-1,80),(1,50)]:
 for k in range(num):
  f=(k+rng.random())/num;root=part_root(f*.60,side)
  root=skin(root-C+rng.normal(0,.12,3),.045)
  if side<0:
   c=[root,[-.9,7.5-4.3*f,166.5+1.2*f],[-4.4,7.0-3.2*f,164.1+2.0*f],[-6.8,4.8-2.4*f,161.0+2.5*f],[-7.5,1.0-1.7*f,159.9+1.6*f],[-7.6,-3.4,157.0],[-4,-7,154.0],[-1.0,-7.5,152.5]]
  else:
   c=[root,[4.0,6.1-3.4*f,166.6+1.1*f],[6.4,3.7-2.3*f,164.0+1.7*f],[7.6,.7-1.2*f,161.0+1.5*f],[7.4,-3.5,157.7],[4.0,-6.8,154.0],[1.0,-7.5,152.5]]
  emit_lock(('left_forehead_' if side<0 else 'right_sweep_')+str(k),c,65,.28,.21,.16,True,.03)

# Irregular, low chignon: crossing C-shaped folds of different depth and radius.
# These are closed, rooted hair paths, not a torus or a cylinder projected from the nape.
bun_paths=[
 [(-3.5,-6.8,155),(-4.0,-8.7,155.3),(-2.0,-10.9,156.2),(1.3,-11.4,155.3),(3.7,-10.8,152.7),(2.2,-11.3,149.5),(-1.0,-10.8,148.5),(-2.7,-8.5,150.5),(-.5,-7.6,152.3)],
 [(3.5,-6.8,154.7),(4.1,-9.1,154.6),(2.6,-11.6,153.1),(-.6,-11.9,151.3),(-3.6,-10.8,149.1),(-3.8,-9.4,151.0),(-1.5,-10.5,153.4),(1.5,-9.6,154.7),(1.0,-7.6,152.5)],
 [(-2.0,-7.0,154.2),(-4.0,-9.3,152.5),(-3.0,-11.3,150.1),(-.4,-11.8,148.6),(2.7,-10.6,149.3),(3.4,-10.0,151.5),(1.8,-11.2,153.4),(-1.2,-10.1,154.4),(-1.0,-7.7,152.0)],
 [(2.0,-7.0,154.0),(3.8,-9.7,152.2),(2.3,-11.9,150.0),(-.2,-11.7,149.4),(-2.5,-10.5,151.6),(-2.1,-10.8,154.2),(.5,-11.1,155.6),(2.0,-8.5,154.0),(1.0,-7.7,152.0)],
 [(-4.3,-6.5,154.5),(-2.5,-9.2,154.4),(.2,-11.7,153.0),(2.2,-11.3,150.7),(1.1,-10.3,149.0),(-1.8,-10.8,150.4),(-1.2,-10.6,153.0),(.8,-8.1,153.2)],
 [(4.3,-6.5,154.2),(2.5,-9.3,155.1),(-.8,-11.8,154.2),(-2.9,-11.4,151.9),(-1.5,-11.0,149.3),(1.2,-10.6,150.2),(1.5,-9.3,152.7),(.5,-7.6,152.4)],
 [(-3,-6.7,152.2),(-4.3,-8.8,151.6),(-2.7,-10.8,149.7),(.0,-11.6,150.2),(1.4,-11.1,152.4),(-.2,-10.1,154.2),(-2.1,-8.6,153.7),(-1,-7.5,152.0)],
 [(3,-6.7,152.3),(4.0,-8.8,151.6),(2.4,-10.7,149.7),(-.2,-11.5,150.2),(-1.4,-11.0,152.2),(.1,-10.0,154.0),(2.0,-8.6,153.5),(1,-7.5,152.0)]]
for k,path in enumerate(bun_paths):
 path=[path[0],*[(x,y+.7,z-.3) for x,y,z in path[1:]]]
 start=skin(np.array(path[0])-C,.07);path=[start,*path[1:]]
 emit_lock('low_chignon_fold_'+str(k),path,1700,1.18 if k<4 else 1.0,.77,.16,False,.32)
core=np.concatenate(core).astype('f');core_uv=np.concatenate(core_uv).astype('f')

loose=[];loose_uv=[]
# A fine irregular halo is distributed over the complete style, including the bun.
for i in range(1750):
 k=int(rng.integers(0,len(core)));end=rng.uniform(.12,.68);u=np.linspace(0,end,32)
 p=np.stack([np.interp(u,np.linspace(0,1,65),core[k,:,a]) for a in range(3)],axis=1)
 q=np.linspace(0,1,32);out=unit(p-C);p+=out*(rng.uniform(.38,.78)*np.sin(math.pi*q))[:,None]
 p[:,2]-=rng.uniform(.0,.45)*q*q;loose.append(p);loose_uv.append(core_uv[k])
# Broken-length, softly curled ear-front strands. The reference shows wisps, not
# two identical solid curtain strips hanging beside the eyes.
for side,total in [(-1,145),(1,120)]:
 for k in range(total):
  f=rng.random();root=skin(np.array([side*6.1,3.8,161.2])+rng.normal(0,.30,3)-C,.06)
  c=[root,[side*(7.0+.25*f),4.7,158.3],[side*(6.8+.5*f),5.1,155.1],[side*(6.7+.4*f),5.5,152.7-f],[side*(7.1+.4*f),4.6,150.6-1.5*f]]
  p=spline(c,32);q=np.linspace(0,1,32);sample=np.linspace(0,.58+.42*f,32)
  p=np.stack([np.interp(sample,q,p[:,a]) for a in range(3)],axis=1)
  p+=rng.normal(0,.42,(1,3))*np.sin(math.pi*q)[:,None]
  p[:,0]+=.20*np.sin(q*11+rng.uniform(0,math.tau))*np.sin(math.pi*q)
  loose.append(p);loose_uv.append(native_uv[rng.integers(len(native_uv))])
for k in range(140):
 x=rng.uniform(-4.5,4.5);root=skin(np.array([x,-5.5,153.5])-C,.06)
 p=spline([root,[x,-7.0,151],[x+.4,-6.9,148],[x-.3,-6.0,145.3+rng.uniform(0,2)]],32)
 loose.append(p);loose_uv.append(native_uv[rng.integers(len(native_uv))])
loose=np.asarray(loose,dtype='f');loose_uv=np.asarray(loose_uv,dtype='f')

# Preserve the established UE Alembic axes and native female root-UV convention.
export_source=Path('D:/FPS3D/FPSGAME/Tools/ChapelNun/author_reference_hair.py').read_text(encoding='utf-8')
export_body=export_source.split('def export(name,points,uv):')[1].split("export('Nun_LowBun_Core_R5'")[0]
exec(compile('def export(name,points,uv):'+export_body,'<groom export>','exec'))
export('Nun_LowBun_Core_R5',core,core_uv);export('Nun_LowBun_Loose_R5',loose,loose_uv)
collection=bpy.data.collections.new('R2_Editable_ClumpGuides');bpy.context.scene.collection.children.link(collection)
for label,p in guides:
 curve=bpy.data.curves.new(label,'CURVE');curve.dimensions='3D';sp=curve.splines.new('POLY');sp.points.add(len(p)-1);sp.points.foreach_set('co',np.c_[p,np.ones(len(p))].ravel())
 ob=bpy.data.objects.new(label,curve);collection.objects.link(ob);ob.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Nun_FullReferenceHair_R8.blend'))
report={'reference':str(N/'Design/NunHead_R2.png'),'hairstyle_revision':'FullReferenceR8','design':'Complete loose waved side-part reconstruction with asymmetrical fringe, ear-top folds, crown waves and interwoven low chignon','color':'black','core_curves':len(core),'loose_curves':len(loose),'core_points_per_curve':65,'core_bounds_min':core.min(axis=(0,1)).tolist(),'core_bounds_max':core.max(axis=(0,1)).tolist(),'face_and_outfit_edited':False,'material_preserved_from_user_accepted_version':True,'native_effect_source':read(N/'RefinementR4/Inputs/native_hair.json')['asset'],'locks':regions}
(R/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('FULL_REFERENCE_HAIR_AUTHORED',len(core),len(loose),flush=True)
