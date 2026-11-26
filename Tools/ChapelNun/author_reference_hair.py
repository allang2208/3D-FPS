"""R2 reference: off-centre sweep, waved temple locks and a loose low twisted bun."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path('D:/FPS3D/FPSGAME');N=P/'SourceAssets/ChapelNun20261115';R=N/'HairReferenceR5';O=R/'Authored';O.mkdir(parents=True,exist_ok=True)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
bpy.ops.wm.read_factory_settings(use_empty=True)
head=read(N/'FaceOriginalRestoreR6/Authored/head.json');center=np.array([0.,.1,158.9]);rng=np.random.default_rng(161125)
bvh=BVHTree.FromPolygons([Vector(p) for p in head['positions']],[t[::-1] for t,m in zip(head['triangles'],head['triangle_materials']) if m in (0,2)],all_triangles=True)
def direction(theta,phi):return np.stack((np.sin(phi)*np.sin(theta),np.sin(phi)*np.cos(theta),np.cos(phi)),axis=-1)
def skin(d,lift=0.):
 d=np.asarray(d,dtype=float);d=d/np.linalg.norm(d,axis=-1,keepdims=True);shape=d.shape
 flat=d.reshape(-1,3);out=[]
 for v in flat:
  p,n,i,dist=bvh.ray_cast(Vector(center),Vector(v),35)
  if p is None:
   p,n,i,dist=bvh.find_nearest(Vector(center+v*8))
  out.append(np.asarray(p)+v*lift)
 return np.asarray(out).reshape(shape)
def outside(points,clearance=.035):
 points=np.asarray(points);d=points-center;norm=np.linalg.norm(d,axis=-1,keepdims=True);surface=skin(d,clearance)
 replace=(norm[...,0]<np.linalg.norm(surface-center,axis=-1))&(points[...,2]>148.)
 return np.where(replace[...,None],surface,points)
def spline(control,count):
 c=np.asarray(control,dtype=float);c=np.concatenate((c[:1],c,c[-1:]));t=np.linspace(0,len(c)-3,count);i=np.minimum(t.astype(int),len(c)-4);u=(t-i)[:,None]
 a,b,c1,d=c[i],c[i+1],c[i+2],c[i+3]
 return .5*((2*b)+(-a+c1)*u+(2*a-5*b+4*c1-d)*u*u+(-a+3*b-3*c1+d)*u*u*u)
def limit(theta):
 return np.interp(np.abs(theta),[0,.6,1.1,1.65,2.2,math.pi],[.97,1.03,1.25,1.50,1.87,2.13])+.012*np.sin(theta*17)+.007*np.sin(theta*39)
roots=[];uvs=[]
for g in read(N/'RefinementR4/Inputs/native_hair.json')['groups']:
 prefix=N/'RefinementR4/Inputs'/g['prefix'];pts=np.fromfile(str(prefix)+'_points.bin','<f4').reshape(-1,3);counts=np.fromfile(str(prefix)+'_counts.bin','<u2');offsets=np.r_[0,np.cumsum(counts[:-1])]
 roots.append(pts[offsets]);uvs.append(np.fromfile(str(prefix)+'_rootuv.bin','<f4').reshape(-1,2))
native_roots=np.concatenate(roots);native_uv=np.concatenate(uvs)
d=native_roots-center;d/=np.linalg.norm(d,axis=1,keepdims=True)
# Move the native part to the reference's viewer-right side; never pile rejected roots onto one edge.
angle=.255;rot=np.array([[math.cos(angle),0,math.sin(angle)],[0,1,0],[-math.sin(angle),0,math.cos(angle)]])
d=d@rot.T;theta=np.arctan2(d[:,0],d[:,1]);phi=np.arccos(np.clip(d[:,2],-1,1));valid=(phi<limit(theta))&(rng.random(len(d))<.80)
d=d[valid];uv=native_uv[valid];theta=theta[valid];phi=phi[valid]
# The tied-back style closes the native long hairstyle's rear centre part.
rear_theta=rng.choice([-1,1],1500)*rng.uniform(math.pi-.32,math.pi,1500);rear_phi=rng.uniform(.38,1.93,1500)
d=np.concatenate((d,direction(rear_theta,rear_phi)));theta=np.r_[theta,rear_theta];phi=np.r_[phi,rear_phi]
uv=np.concatenate((uv,native_uv[rng.integers(0,len(native_uv),1500)]));count=len(d)
# The donor long-hair scalp leaves a broad crown opening. Fill the tied style's
# crown with rooted fibres, retaining only the narrow off-centre part itself.
fill_phi=np.arccos(rng.uniform(math.cos(.88),1.,4200));fill_theta=rng.uniform(-math.pi,math.pi,4200)
fill=direction(fill_theta,fill_phi)@rot.T
fill=fill[np.abs(fill[:,0]-fill[:,2]*math.tan(angle))>.018]
# Give the temple hairline a continuous soft root layer beneath the swept locks.
edge_theta=rng.choice([-1,1],2200)*rng.uniform(.75,1.80,2200)
edge_phi=limit(edge_theta)-rng.uniform(.025,.18,2200)
fill=np.concatenate((fill,direction(edge_theta,edge_phi)))
d=np.concatenate((d,fill));theta=np.arctan2(d[:,0],d[:,1]);phi=np.arccos(np.clip(d[:,2],-1,1))
uv=np.concatenate((uv,native_uv[rng.integers(0,len(native_uv),len(fill))]));count=len(d)
# Six interleaved locks form a soft knot rather than a cylindrical coil.
bun_controls=[
 [(-3,-7.5,153.7),(-4.4,-9.3,153.8),(-2.9,-11.7,155.1),(.8,-13.0,154.5),(3.8,-12.1,151.7),(1.3,-12.4,148.9),(-2.3,-10.1,149.5),(-1.0,-8.7,151.4)],
 [(3,-7.5,153.5),(4.3,-9.5,152.6),(2.3,-12.4,149.5),(-1.2,-12.8,148.6),(-4.1,-11.5,151.1),(-2.8,-10.6,154.0),(.5,-10.7,153.4),(1.2,-8.8,151.7)],
 [(-1,-8.0,154.3),(-3.9,-10.2,153.2),(-2.2,-12.4,150.0),(.4,-13.5,148.9),(3.5,-11.9,150.5),(3.1,-10.8,153.8),(0,-10.0,154.6),(-.8,-8.7,152.2)],
 [(1,-8.0,154.0),(3.6,-10.4,154.6),(.6,-12.6,155.2),(-3.6,-12.6,152.8),(-3.0,-12.2,149.8),(.4,-10.9,149.4),(2.8,-10.2,151.6),(1,-8.8,152.5)],
 [(-3.2,-7.5,152.8),(-4.6,-10.0,151.0),(-2.0,-12.8,148.5),(1.2,-13.3,149.7),(3.8,-11.8,152.7),(1.4,-11.0,154.6),(-1.8,-10,152.7),(-.6,-9,150.3)],
 [(3.1,-7.8,153.8),(4.6,-10.1,153.2),(2.4,-12.2,155.0),(-1.4,-13.0,153.3),(-3.9,-12.0,150.2),(-.6,-11.8,148.6),(2.9,-10.2,150.3),(1,-8.9,152.0)]
]
bun=np.stack([spline(c,25) for c in bun_controls]);bun[:,:,1]+=1.45;bun[:,:,2]+=.55
side=np.where(d[:,0]-d[:,2]*math.tan(angle)<0,-1,1)
bundle=(np.floor((theta+math.pi)*9)+np.floor(phi*8)).astype(int)%3*2+(side>0)
# Fill the knot volume with overlapping locks of different radii. The previous
# six identical loops left an artificial open ring in the middle.
knot_center=np.array([0.,-9.85,152.55]);radial_scale=rng.uniform(.28,1.02,(count,1,1))
tail=knot_center+(bun[bundle]-knot_center)*rng.uniform(.40,1.02,(count,1,1))
# Rounded crossed locks with independent fibres, rather than one flat disk.
tail[:,:,1]-=.35*np.sin(np.linspace(0,math.pi,25))[None,:]
tail+=rng.normal(0,.22,(count,1,3))
ttail=np.linspace(0,1,25)[None,:];tp=rng.uniform(0,math.tau,(count,1))
tail[:,:,0]+=.16*np.sin(ttail*24+tp)*np.sin(math.pi*ttail)
tail[:,:,2]+=.13*np.cos(ttail*21+tp)*np.sin(math.pi*ttail)
entry=tail[:,0]-center;entry/=np.linalg.norm(entry,axis=1,keepdims=True);u=np.linspace(0,1,41)[None,:,None]
dot=np.clip(np.sum(d*entry,axis=1),-.9999,.9999);omega=np.arccos(dot)[:,None,None]
flow=np.sin((1-u)*omega)/np.sin(omega)*d[:,None,:]+np.sin(u*omega)/np.sin(omega)*entry[:,None,:]
def routed(start):
 mid=direction(side*1.85,np.clip(phi*.34+.87,1.03,1.47))
 def arc(a,b,t):
  w=np.arccos(np.clip(np.sum(a*b,axis=1),-.9999,.9999))[:,None,None]
  return np.sin((1-t)*w)/np.sin(w)*a[:,None,:]+np.sin(t*w)/np.sin(w)*b[:,None,:]
 first=arc(start,mid,np.minimum(u/.64,1));second=arc(mid,entry,np.maximum((u-.64)/.36,0))
 return np.where(u<.64,first,second)
route_front=((d[:,1]>.35)&(phi>.65))[:,None,None];flow=np.where(route_front,routed(d),flow)
clump_theta=np.round(theta/.15)*.15;clump_phi=np.round(phi/.14)*.14;phase=clump_theta*13+clump_phi*17
gd=direction(clump_theta,clump_phi);go=np.arccos(np.clip(np.sum(gd*entry,axis=1),-.9999,.9999))[:,None,None]
gf=np.sin((1-u)*go)/np.sin(go)*gd[:,None,:]+np.sin(u*go)/np.sin(go)*entry[:,None,:]
gf=np.where(route_front,routed(gd),gf)
attract=.42*np.sin(math.pi*u)**.60;flow=flow*(1-attract)+gf*attract;flow/=np.linalg.norm(flow,axis=-1,keepdims=True)
wave=np.sin(2.2*math.pi*u[...,0]+phase[:,None])*.12*np.sin(math.pi*u[...,0])
ft=np.arctan2(flow[...,0],flow[...,1])+wave
fp=np.arccos(np.clip(flow[...,2],-1,1))+.028*np.sin(3.2*math.pi*u[...,0]+phase[:,None]) *np.sin(math.pi*u[...,0])
flow=direction(ft,fp)
# A low-resolution radial field preserves the fitted head while allowing broad sculpted waves.
TW,PH=384,192;angles=np.linspace(-math.pi,math.pi,TW);polar=np.linspace(0,2.40,PH);tt,pp=np.meshgrid(angles,polar)
grid_d=direction(tt,pp);radii=np.linalg.norm(skin(grid_d)-center,axis=-1)
def project_field(d,lift):
 th=(np.arctan2(d[...,0],d[...,1])+math.pi)/(2*math.pi)*(TW-1);ph=np.clip(np.arccos(np.clip(d[...,2],-1,1))/2.40*(PH-1),0,PH-1)
 x=np.clip(th.astype(int),0,TW-2);y=np.clip(ph.astype(int),0,PH-2);fx=th-x;fy=ph-y
 rad=radii[y,x]*(1-fx)*(1-fy)+radii[y,x+1]*fx*(1-fy)+radii[y+1,x]*(1-fx)*fy+radii[y+1,x+1]*fx*fy
 return center+d*(rad+lift)[...,None]
front=np.clip(d[:,1],0,1);crown=np.clip(d[:,2],0,1);clump_height=.08*np.sin(phase)
strand_layer=rng.uniform(.12,.80,(count,1))
lift=.06+(.24+.45*front+.25*crown+clump_height)[:,None]*np.sin(math.pi*u[...,0])**.90
lift+=strand_layer*np.sin(math.pi*u[...,0])**.7
lift+=.10*np.sin(phase[:,None]+u[...,0]*13)*np.sin(math.pi*u[...,0])
body=project_field(flow,lift)
body[:,-1]=tail[:,0]
core=np.concatenate((body,tail[:,1:]),axis=1);core_uv=uv.copy()
print('R5_BASE_COMB',count,flush=True)
# Layered, asymmetric front ribbons follow the silhouette of the approved R2 sheet.
front_paths=[];front_uv=[];guides=[]
for side_sign,guide_count,strands in [(-1,18,180),(1,12,140)]:
 for gi in range(guide_count):
  f=gi/max(1,guide_count-1);alpha=.72-1.17*f
  root_direction=np.array([math.sin(angle)*math.cos(alpha)+side_sign*.018,math.sin(alpha),math.cos(angle)*math.cos(alpha)])
  root=skin(root_direction,.06)
  if side_sign<0:
   control=[root,(.7,7.8-4.4*f,166.7+1.7*f),(-2.4,8.7-3.0*f,164.5+1.6*f),(-5.2,6.3-2.7*f,161.7+2.0*f),(-6.7,3.0-2.0*f,158.4+2.1*f),(-7.2,.1-2.3*f,156.7+1.8*f),(-6.8,-3.6,154.8),(-3.8,-7.8,153.8)]
  else:
   control=[root,(4.0,7.0-3.0*f,165.6+1.3*f),(5.9,5.4-2.1*f,162.5+1.8*f),(7.1,2.7-2.1*f,159.1+1.5*f),(7.4,.1-1.7*f,157.0+1.2*f),(7.0,-3.6,155.7),(3.9,-7.8,153.7)]
  guide=spline(control,41);gd=guide-center;gd/=np.linalg.norm(gd,axis=1,keepdims=True)
  progress=np.linspace(0,1,41);height=.04+(.33+.28*f)*np.sin(math.pi*progress)**.85
  guide=project_field(gd,height)
  bi=(gi%3)*2+(side_sign>0);guide[-1]=bun[bi,0];guide=np.concatenate((guide,bun[bi,1:]),axis=0);guides.append(guide)
  tang=np.gradient(guide,axis=0);tang/=np.linalg.norm(tang,axis=1,keepdims=True);normal=np.cross(tang,np.tile([0,0,1.],(len(guide),1)));normal/=np.maximum(.001,np.linalg.norm(normal,axis=1,keepdims=True));binorm=np.cross(tang,normal)
  q=np.linspace(0,1,len(guide));width=.02+.12*np.sin(math.pi*q)**.6;offsets=rng.normal(0,.85,(strands,2))
  p=guide[None,:,:]+width[None,:,None]*(offsets[:,0,None,None]*normal+offsets[:,1,None,None]*binorm)
  p+=normal[None,:,:]*(.025*np.sin(q[None,:]*43+rng.uniform(0,math.tau,(strands,1)))*np.sin(math.pi*q)[None,:])[...,None]
  p[:,0]=np.array([skin(x-center,.04) for x in p[:,0]])
  front_paths.append(p);front_uv.append(native_uv[rng.integers(0,len(native_uv),strands)])
core=np.concatenate((core,*front_paths));core_uv=np.concatenate((core_uv,*front_uv))
# Keep a true rooted comb, with coherent waves and finer strand irregularity.
# The front locks are rooted at the approved side part and swept across the
# upper forehead, rather than pulling every visible strand straight backwards.
for k in np.linspace(0,count-1,120).astype(int):guides.append(core[k])
count=len(core);q=np.linspace(0,1,65);phase2=rng.uniform(0,math.tau,(count,1))
core[:,:,0]+=.035*np.sin(q[None,:]*48+phase2)*np.sin(math.pi*q)[None,:]
core[:,:,2]+=.035*np.cos(q[None,:]*43+phase2)*np.sin(math.pi*q)[None,:]
# Irregular flyaways follow clumps; longer temple strands hang beside the cheek, not across the eyes.
loose=[];loose_uv=[]
for i in range(1500):
 k=int(rng.integers(0,len(core)));length=int(rng.integers(5,15));p=core[k,:length];guide=spline(p,28);t=np.linspace(0,1,28)
 radial=guide-center;radial/=np.linalg.norm(radial,axis=1,keepdims=True);guide+=radial*(rng.uniform(.12,.44)*np.sin(math.pi*t))[:,None];guide[:,2]-=.35*t*t
 loose.append(guide);loose_uv.append(core_uv[k])
for sign,n in [(-1,280),(1,220)]:
 for i in range(n):
  f=rng.random();root=skin(np.array([sign*5.7,4.7,162.0])+rng.normal(0,.28,3)-center,.04)
  p=spline([root,(sign*(6.8+.30*f),5.1,159.6),(sign*(7.1+.40*f),5.0,157.0-f),(sign*(6.7+.45*f),5.8,154.4-f),(sign*(6.5+.50*f),5.4,152.0-f*1.8),(sign*(6.8+.40*f),4.9,151.2-f*1.2)],28)
  sample=np.linspace(0,.65+.35*f,28);p=np.stack([np.interp(sample,np.linspace(0,1,28),p[:,axis]) for axis in range(3)],axis=1)
  t=np.linspace(0,1,28);p+=rng.normal(0,.17,(1,3))*np.sin(math.pi*t)[:,None]
  p[:,0]+=.20*np.sin(t*8+f*3)*np.sin(math.pi*t);p[:,1]+=.16*np.sin(t*7+f*4)*np.sin(math.pi*t)
  loose.append(p);loose_uv.append(native_uv[int(rng.integers(0,len(native_uv)))])
loose=np.asarray(loose);loose_uv=np.asarray(loose_uv)
def export(name,points,uv):
 curve=bpy.data.curves.new(name,'CURVE');curve.dimensions='3D';curve.resolution_u=1;ob=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(ob);ob['groom_group_id']=0;ob['groom_guide']=0
 for p in points:
  sp=curve.splines.new('POLY');sp.points.add(len(p)-1);sp.points.foreach_set('co',np.c_[p,np.ones(len(p))].ravel())
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 bpy.ops.wm.alembic_export(filepath=str(O/(name+'.abc')),start=1,end=1,selected=True,as_background_job=False,export_custom_properties=True,curves_as_mesh=False,global_scale=1.)
 uv.astype('<f4').tofile(O/(name+'_rootuv.bin'));np.save(O/(name+'_points.npy'),points.astype('<f4'))
 ob.hide_render=True
 hc=bpy.data.hair_curves.new(name+'_Preview');hc.add_curves([points.shape[1]]*len(points));hc.attributes['position'].data.foreach_set('vector',points.astype('f').ravel())
 radius=hc.attributes.new('radius','FLOAT','POINT');rr=np.tile(.0032*(1-.91*np.linspace(0,1,points.shape[1])**3),len(points));radius.data.foreach_set('value',rr.astype('f'))
 preview=bpy.data.objects.new(name+'_Preview',hc);bpy.context.collection.objects.link(preview)
 print('R5_GROOM_EXPORTED',name,len(points),points.shape[1],flush=True)
export('Nun_LowBun_Core_R5',core,core_uv);export('Nun_LowBun_Loose_R5',loose,loose_uv)
guide_curve=bpy.data.curves.new('Editable_SweepGuides','CURVE');guide_curve.dimensions='3D'
for g in guides:
 sp=guide_curve.splines.new('POLY');sp.points.add(len(g)-1);sp.points.foreach_set('co',np.c_[g,np.ones(len(g))].ravel())
guide_ob=bpy.data.objects.new('Editable_SweepGuides',guide_curve);bpy.context.collection.objects.link(guide_ob);guide_ob.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Nun_ReferenceHair_R5.blend'))
report={'reference':str(N/'Design/NunHead_R2.png'),'design':'Young R2: rooted asymmetric forehead fringe, soft temple locks, continuous side part, covered crown and low interleaved bun','hairstyle_revision':'YoungReferenceR7','material_preserved_from_user_accepted_version':True,'color':'black','core_curves':len(core),'loose_curves':len(loose),'core_points_per_curve':core.shape[1],'core_bounds_min':core.min(axis=(0,1)).tolist(),'core_bounds_max':core.max(axis=(0,1)).tolist(),'face_and_outfit_edited':False,'native_effect_source':read(N/'RefinementR4/Inputs/native_hair.json')['asset']}
(R/'authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('REFERENCE_HAIR_AUTHORED',flush=True)
