"""GuanLei V11: new primary volumes and carved curved shoulders; exact native interface bands."""
import bpy,bmesh,math,json
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent
for f in ('Export','Previews'):(P/f).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
CX=-.0004452141;CZ=.911
parts=[];context=[]
def material(name):
 m=bpy.data.materials.new('M_GuanLei11_'+name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
 for kind in ('BaseColor','ORM','Normal'):
  file=P/'Textures'/('T_GuanLei11_Metal_Normal.png' if kind=='Normal' else 'T_GuanLei11_'+name+'_'+kind+'.png')
  t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(file),check_existing=True);t.image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
  if kind=='BaseColor':l.new(t.outputs['Color'],bs.inputs['Base Color'])
  elif kind=='ORM':
   s=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],s.inputs[0]);l.new(s.outputs['Green'],bs.inputs['Roughness']);l.new(s.outputs['Blue'],bs.inputs['Metallic'])
  else:
   nm=n.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.20;l.new(t.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs[0],bs.inputs['Normal'])
 return m
steel=material('Steel');silver=material('Silver');recess=material('Recess');inlay=material('Inlay')
blue=bpy.data.materials.new('M_GuanLei11_ThunderInlay');blue.use_nodes=True
bs=blue.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.025,.17,.30,1);bs.inputs['Metallic'].default_value=.55;bs.inputs['Roughness'].default_value=.27;bs.inputs['Emission Color'].default_value=(.01,.3,.7,1);bs.inputs['Emission Strength'].default_value=.7
def mesh(name,verts,faces,mat=steel,uvs=None,smooth=True):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(mat)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 for p in me.polygons:p.use_smooth=smooth
 uv=me.uv_layers.new(name='UVMap')
 for p in me.polygons:
  ax=max(range(3),key=lambda a:abs(p.normal[a]));axes=[a for a in range(3) if a!=ax]
  for li in p.loop_indices:
   co=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]]/.055,co[axes[1]]/.055)
 parts.append(o);return o
def activate(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def bevel(o,w=.0008,segments=4):
 activate(o);m=o.modifiers.new('True machined edge radii','BEVEL');m.width=w;m.segments=segments;m.limit_method='ANGLE';m.angle_limit=.38
 bpy.ops.object.modifier_apply(modifier=m.name)
 for p in o.data.polygons:p.use_smooth=True
 m=o.modifiers.new('Area weighted broad-face normals','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=35
 bpy.ops.object.modifier_apply(modifier=m.name)
 return o
def extrude(name,poly,yfront,yback,mat=steel,w=.0006):
 N=len(poly);vs=[(x+CX,y,z) for y in (yfront,yback) for x,z in poly];fs=[tuple(range(N-1,-1,-1)),tuple(range(N,2*N))]+[(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]
 return bevel(mesh(name,vs,fs,mat, smooth=False),w)
def interp_path(points,n=160):
 # Cubic Hermite centreline, with finite endpoint tangents.
 pts=np.asarray(points,float);out=[]
 for i in range(len(pts)-1):
  p0=pts[max(0,i-1)];a=pts[i];b=pts[i+1];p3=pts[min(len(pts)-1,i+2)];m0=(b-p0)*.5;m1=(p3-a)*.5
  for t in np.linspace(0,1,max(4,n//(len(pts)-1)),endpoint=False):out.append((2*t**3-3*t*t+1)*a+(t**3-2*t*t+t)*m0+(-2*t**3+3*t*t)*b+(t**3-t*t)*m1)
 out.append(pts[-1]);return np.array(out)
def ribbon(name,coords,width,depth,mat=silver,closed=False,normal_axis=1):
 # A broad rectangular-section relief strip with finite closed thickness.
 pts=np.asarray(coords,float);N=len(pts);vs=[]
 for i,p in enumerate(pts):
  t=pts[(i+1)%N]-pts[i-1] if closed else pts[min(i+1,N-1)]-pts[max(0,i-1)]
  pn=np.eye(3)[normal_axis];side=np.cross(pn,t);side/=max(np.linalg.norm(side),1e-9)
  for a,d in [(-1,0),(1,0),(1,depth),(-1,depth)]:vs.append(tuple(p+side*width*.5*a+pn*d))
 fs=[]
 for i in range(N if closed else N-1):
  j=(i+1)%N
  for k in range(4):fs.append((i*4+k,j*4+k,j*4+(k+1)%4,i*4+(k+1)%4))
 if not closed:fs.extend([(3,2,1,0),tuple((N-1)*4+k for k in range(4))])
 return bevel(mesh(name,vs,fs,mat),min(width*.14,.00016),2)
def lathe_y(name,profile,cx=CX,cz=CZ,mat=silver,segments=192):
 vs=[];L=len(profile)
 for i in range(segments):
  a=i*math.tau/segments
  for r,y in profile:vs.append((cx+r*math.cos(a),y,cz+r*math.sin(a)))
 fs=[(i*L+j,((i+1)%segments)*L+j,((i+1)%segments)*L+(j+1)%L,i*L+(j+1)%L) for i in range(segments) for j in range(L)]
 o=mesh(name,vs,fs,mat)
 for p in o.data.polygons:
  if abs(p.normal.y)>.999:p.use_smooth=False
 return o
def round_body():
 # Lathed rounded-rectangle cross-sections build the full solid; not a flat plate.
 knots=np.array([[.849,.040,.031],[.855,.043,.034],[.869,.044,.037],[.887,.055,.041],[.911,.059,.044],[.939,.058,.042],[.963,.052,.037],[.982,.044,.030]])
 path=interp_path(knots,120);N=128;vs=[]
 for z,rx,ry in path:
  for a in np.linspace(0,math.tau,N,endpoint=False):
   c=math.cos(a);s=math.sin(a);vs.append((CX+rx*np.sign(c)*abs(c)**.56,ry*np.sign(s)*abs(s)**.56,z))
 fs=[(i*N+j,i*N+(j+1)%N,(i+1)*N+(j+1)%N,(i+1)*N+j) for i in range(len(path)-1) for j in range(N)]
 fs.extend([tuple(range(N-1,-1,-1)),tuple((len(path)-1)*N+j for j in range(N))]);return mesh('01_ContinuousForgedCore',vs,fs,steel)
round_body()
for sign in (-1,1):
 yz=[(-.029,.872),(.029,.872),(.034,.887),(.034,.946),(.026,.959),(-.026,.959),(-.034,.946),(-.034,.887)]
 vv=[(CX+sign*x,y,z) for x in (.048,.0625) for y,z in yz];nn=len(yz)
 ff=[tuple(range(nn-1,-1,-1)),tuple(range(nn,nn*2))]+[(i,(i+1)%nn,(i+1)%nn+nn,i+nn) for i in range(nn)]
 bevel(mesh('01_HeadInterfaceLoadWeb',vv,ff,steel),.0012,4)
print('CORE_BUILT',flush=True)
def shoulder(sign,face):
 path=interp_path([[.030,.978,.025],[.047,.967,.025],[.044,.953,.022],[.046,.939,.017],[.053,.919,.019],[.053,.900,.020],[.045,.882,.023],[.034,.864,.020]],266)
 # Shoulder surface uses material-embedded carved rails and woven return patterns.
 NU=len(path);NV=161;vs=[];mids=[]
 for i,(x,z,w) in enumerate(path):
  tangent=path[min(i+1,NU-1),:2]-path[max(0,i-1),:2];tangent/=np.linalg.norm(tangent);normal=np.array([-tangent[1],tangent[0]])
  u=i/(NU-1);full=.045+.003*math.sin(math.pi*u)
  for j,v in enumerate(np.linspace(-1,1,NV)):
   pos=np.array([x,z])+normal*v*w*.5
   h=.0028*(1-v**8)
   # Closed return track folds across width near its ends.
   rail=.46*np.sqrt(max(0,1-((u-.5)/.44)**8)) if .06<u<.94 else 0
   d=abs(abs(v)-abs(rail))
   groove=max(0,1-d/.12)*.00065 if .06<u<.94 else 0
   yy=full+h-groove
   vs.append((CX+sign*pos[0],face*yy,pos[1]))
   mids.append(1 if .80<abs(v)<.90 else 0)
 fs=[];mi=[]
 for i in range(NU-1):
  for j in range(NV-1):
   k=i*NV+j;fs.append((k,k+1,k+1+NV,k+NV));mi.append(mids[k])
 boundary=list(range(NV))+[i*NV+NV-1 for i in range(1,NU)]+[(NU-1)*NV+j for j in range(NV-2,-1,-1)]+[i*NV for i in range(NU-2,0,-1)]
 base=[]
 for k in boundary:
  p=vs[k];base.append(len(vs));vs.append((p[0],face*.026,p[2]))
 for k in range(len(boundary)):fs.append((boundary[k],base[k],base[(k+1)%len(base)],boundary[(k+1)%len(base)]));mi.append(0)
 fs.append(tuple(reversed(base)));mi.append(0)
 o=mesh('02_ReturnShoulder_'+str(sign)+'_'+str(face),vs,fs,steel)
 o.data.materials.append(silver);o.data.materials.append(recess);o.data.materials.append(blue)
 for p,m in zip(o.data.polygons,mi):p.material_index=m
 for p in o.data.polygons:
  for li in p.loop_indices:
   vi=o.data.loops[li].vertex_index
   if vi<NU*NV:o.data.uv_layers[0].data[li].uv=((vi%NV)/(NV-1)*.42,(vi//NV)/(NU-1)*2.45)
 # Exact continuous inlay boundaries remove material-grid stair stepping.
 loop=[]
 for direction in (1,-1):
  us=np.linspace(.0601,.9399,250)
  if direction<0:us=us[::-1]
  for u in us:
   ind=u*(NU-1);ii=min(int(ind),NU-2);q=ind-ii;p=path[ii]*(1-q)+path[ii+1]*q
   t=path[min(ii+1,NU-1),:2]-path[max(ii-1,0),:2];t/=np.linalg.norm(t);n=np.array([-t[1],t[0]])
   v=direction*.46*math.sqrt(max(0,1-((u-.5)/.44)**8));xz=p[:2]+n*v*p[2]*.5
   yy=.045+.003*math.sin(math.pi*u)+.0028*(1-v**8)-.00015
   loop.append((CX+sign*xz[0],face*yy,xz[1]))
 ribbon('02_ContinuousSilverReturnChannel',loop,.00135,-face*.0007,inlay,True)
 ribbon('02_RecessedThunderChannel',[(x,y+face*.00004,z) for x,y,z in loop],.00045,-face*.0004,blue,True)
 # Fine integral woven ornament follows the broad shoulder top, terminating in its root.
 for phase in (0,math.tau/3,2*math.tau/3):
  pts=[]
  for q in np.linspace(.02,.25,100):
   ind=q*(NU-1);ii=min(int(ind),NU-2);r=ind-ii;p=path[ii]*(1-r)+path[ii+1]*r
   t=path[min(ii+1,NU-1),:2]-path[max(ii-1,0),:2];t/=np.linalg.norm(t);normal=np.array([-t[1],t[0]])
   v=.36*math.asin(.985*math.sin((q-.02)/.23*math.tau*2+phase))/math.asin(.985);xz=p[:2]+normal*v*p[2]*.5
   yy=.045+.003*math.sin(math.pi*q)+.0028*(1-v**8)+.00016+.00012*math.cos((q-.02)/.23*math.tau*4)
   pts.append((CX+sign*xz[0],face*yy,xz[1]))
  # Front strips are seated shallowly into the carved shoulder, closed at the roots.
  ribbon('03_ShoulderWovenInlay',pts,.00105,-face*.00055,inlay)
for sx in (-1,1):
 for fy in (-1,1):shoulder(sx,fy)
print('FOUR_CURVED_SHOULDERS_BUILT',flush=True)
# Native top geometry is replaced with a stepped casting and recessed carved panels.
cap=[(-.049,.970),(.049,.970),(.051,.979),(.044,.989),(-.044,.989),(-.051,.979)]
extrude('04_LowForgedCap',cap,-.037,.037,steel,.001)
def panel(name,cx,cz,width,height,face,depth,cycles=4):
 NU=300;NV=66;us=np.linspace(-1,1,NU);vs0=np.linspace(-1,1,NV);U,V=np.meshgrid(us,vs0,indexing='ij')
 waves=[np.arcsin(.985*np.sin((U+1)*math.pi*cycles+phase))/math.asin(.985)*.62 for phase in (0,math.tau/3,2*math.tau/3)]
 d=np.minimum.reduce([abs(V-wave) for wave in waves])
 end=np.clip((1-abs(U))*12,0,1)*np.clip((1-abs(V))*10,0,1)
 cut=np.clip(1-d/.20,0,1)*.00065*end
 silvermask=(d<.07)&(abs(U)<.94)&(abs(V)<.85)
 vv=[(CX+cx+u*width*.5,face*(depth-cut[i,j]),cz+v*height*.5) for i,u in enumerate(us) for j,v in enumerate(vs0)]
 fs=[(i*NV+j,i*NV+j+1,(i+1)*NV+j+1,(i+1)*NV+j) for i in range(NU-1) for j in range(NV-1)]
 mi=[1 if silvermask[i,j] else 0 for i in range(NU-1) for j in range(NV-1)]
 edge=list(range(NV))+[i*NV+NV-1 for i in range(1,NU)]+[(NU-1)*NV+j for j in range(NV-2,-1,-1)]+[i*NV for i in range(NU-2,0,-1)]
 back=[]
 for k in edge:
  a=vv[k];back.append(len(vv));vv.append((a[0],face*(depth-.004),a[2]))
 for k in range(len(edge)):fs.append((edge[k],back[k],back[(k+1)%len(back)],edge[(k+1)%len(edge)]));mi.append(0)
 fs.append(tuple(reversed(back)));mi.append(0)
 o=mesh(name,vv,fs,recess);o.data.materials.append(inlay)
 for p,m in zip(o.data.polygons,mi):p.material_index=m
 return o
for f in (-1,1):
 panel('05_CapRecessedKnotwork',0,.980,.070,.010,f,.0384,3)
 for z in (.9738,.9862):
  ribbon('06_CapSilverChiselEdge',[(CX+x,f*.0387,z) for x in np.linspace(-.037,.037,8)],.00085,-f*.0009,silver)
for x in (-.041,.041):
 extrude('07_CapCornerForging',[(x-.0035,.9695),(x+.0035,.9695),(x+.004,.988),(x-.0035,.990)],-.0395,.0395,silver,.00065)
for phase in (0,math.pi):
 pts=[(CX+x,.010*math.asin(.99*math.sin((x+.033)/.066*math.tau*2+phase))/math.asin(.99),.98925) for x in np.linspace(-.033,.033,180)]
 ribbon('07_TopCapDiamondWeave',pts,.0011,-.0008,inlay,normal_axis=2)
# Beveled shield panel and closed back interlace.
backshape=[(-.032,.964),(.032,.964),(.037,.949),(.033,.887),(.022,.867),(0,.858),(-.022,.867),(-.033,.887),(-.037,.949)]
extrude('08_BackForgedShield',backshape,.041,.047,steel,.0013)
for phase in (0,math.pi):
 pts=[]
 for t in np.linspace(0,1,200):
  x=.014*math.sin(t*math.tau*2+phase);z=.961-.092*t;y=.048+.00035*math.cos(t*math.tau*4+phase)
  pts.append((CX+x,y,z))
 ribbon('09_BackClosedReturnKnot',pts,.0018,-.0013,inlay)
for side in (-1,1):
 pts=interp_path([[side*.030,.959],[side*.032,.934],[side*.029,.900],[side*.020,.875],[0,.864]],90)
 ribbon('10_BackInsetBorder',[(CX+x,.0478,z) for x,z in pts],.0011,-.0012,silver)
# Thin, detailed medallion; no extra swollen torus.
disk_profile=[(.0001,-.042),(.040,-.042),(.041,-.048),(.0404,-.0515),(.0396,-.0523),(.0001,-.0523)]
lathe_y('11_RecessedRuneMedallion',disk_profile,mat=recess)
rim=[(.040,-.052),(.040,-.0556),(.0405,-.0572),(.0411,-.0578),(.0428,-.0578),(.0435,-.0571),(.0440,-.0557),(.0440,-.0515)]
lathe_y('12_OriginalScaleSilverBezel',rim,mat=silver)
lathe_y('13_BezelInnerDarkEngraving',[(.04155,-.05782),(.04155,-.0580),(.04185,-.0580),(.04185,-.05782)],mat=recess)
# Sixty-four tiny chisel-cut witness marks, seated in the existing narrow bezel.
for i in range(64):
 a=i*math.tau/64;pts=[(CX+r*math.cos(a),-.05786,CZ+r*math.sin(a)) for r in (.04225,.04272)]
 ribbon('14_BezelChisel',pts,.00022,.0002,recess)
# Three separated, intersecting triangular bands with alternating over/under relief.
for ti,(tx,tz) in enumerate([(-.009,.918),(.009,.915),(0,.904)]):
 tri=np.array([[tx,tz+.024],[tx-.023,tz-.016],[tx+.023,tz-.016]])
 pts=[]
 for i in range(3):
  a=tri[i];b=tri[(i+1)%3]
  for t in np.linspace(0,1,25,endpoint=False):
   q=a*(1-t)+b*t;pts.append((CX+q[0],-.0562-ti*.00025,q[1]))
 ribbon('15_ValknutForgedTriangle_'+str(ti),pts,.0036,.0014,silver,True)
 ribbon('16_ValknutRecessedBlue_'+str(ti),[(x,y-.00006,z) for x,y,z in pts],.0011,.0005,blue,True)
for a in (0,math.pi*.5,math.pi,math.pi*1.5):
 x=.044*math.cos(a);z=CZ+.044*math.sin(a);s=.0023
 extrude('17_BezelDiamondSeat',[(x,z+s),(x+s*.7,z),(x,z-s),(x-s*.7,z)],-.059,-.054,silver,.00025)
extrude('17_UpperForgedDiamond',[(0,.970),(.003,.963),(0,.956),(-.003,.963)],-.0485,-.037,silver,.00045)
extrude('17_UpperDiamondInlay',[(0,.967),(.001,.963),(0,.959),(-.001,.963)],-.04865,-.048,blue,.00015)
# Lower engraved apron and collar retain the broad native neck connection.
for f in (-1,1):
 panel('18_LowerWovenApron',0,.859,.061,.013,f,.0368,2)
def collar():
 N=192;profile=[(.850,.041,.034),(.851,.042,.035),(.853,.042,.035),(.854,.040,.0335),(.862,.040,.0335),(.863,.0415,.0347),(.865,.0415,.0347),(.866,.040,.0335)]
 v=[]
 for z,rx,ry in profile:
  for t in np.linspace(0,math.tau,N,endpoint=False):v.append((CX+rx*math.cos(t),ry*math.sin(t),z))
 fs=[(i*N+j,i*N+(j+1)%N,(i+1)*N+(j+1)%N,(i+1)*N+j) for i in range(len(profile)-1) for j in range(N)]
 fs.extend([tuple(range(N-1,-1,-1)),tuple((len(profile)-1)*N+j for j in range(N))]);mesh('19_NeckSeatedTransition',v,fs,steel)
collar()
print('ORNAMENT_AND_MEDALLION_BUILT',flush=True)
# Load ONLY the known factory modules; unrelated scenes/armatures remain untouched.
names=['SM_ThunderGodHammer_'+s+'_factory' for s in ('head_mount','hammer_heads','neck','shaft')]
with bpy.data.libraries.load(str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),link=False) as(a,b):b.objects=names
factory=None
for o in b.objects:
 bpy.context.collection.objects.link(o)
 if o.name=='SM_ThunderGodHammer_head_mount_factory':factory=o
 else:context.append(o)
# Original packed PBR data is authoritative for original adjoining modules.
for obj in [factory,*context]:
 obj.hide_render=False;obj.hide_set(False)
 for m in obj.data.materials:
  if not m or not m.use_nodes:continue
  for n in m.node_tree.nodes:
   if n.type=='TEX_IMAGE' and n.image:
    if 'normal' in n.image.name.lower():n.image.colorspace_settings.name='Non-Color'
# Restore the actual original color/PBR images; the old icon-author scene may
# contain grayscale material edits. These are separate local material instances.
hostmat=bpy.data.materials.new('M_OriginalHammer_ContextPBR');hostmat.use_nodes=True
ns=hostmat.node_tree.nodes;ls=hostmat.node_tree.links;bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
for kind,file in [('base','BaseColor.jpg'),('orm','MetallicRoughness.jpg'),('normal','Normal.jpg')]:
 tex=ns.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(P.parent/'Textures'/file),check_existing=True);tex.image.colorspace_settings.name='sRGB' if kind=='base' else 'Non-Color'
 if kind=='base':
  tint=ns.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1.;tint.inputs[2].default_value=(.30,.29,.27,1);ls.new(tex.outputs['Color'],tint.inputs[1]);ls.new(tint.outputs[0],bs.inputs['Base Color'])
 elif kind=='orm':
  sep=ns.new('ShaderNodeSeparateColor');ls.new(tex.outputs['Color'],sep.inputs[0]);ls.new(sep.outputs['Green'],bs.inputs['Roughness']);ls.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 else:
  nm=ns.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.65;ls.new(tex.outputs['Color'],nm.inputs['Color']);ls.new(nm.outputs[0],bs.inputs['Normal'])
for obj in [factory,*context]:
 for i in range(len(obj.data.materials)):obj.data.materials[i]=hostmat
# The original native rune relief is part of the weapon's identity. Retain it,
# with its original UV and per-corner normals, inside the newly forged bezel.
for o in list(parts):
 if o.name.startswith(('12_','13_','14_','15_','16_','17_BezelDiamondSeat')):parts.remove(o);bpy.data.objects.remove(o,do_unlink=True)
me=factory.data.copy();seal=bpy.data.objects.new('15_OriginalRuneRelief',me);bpy.context.collection.objects.link(seal)
me.materials.append(recess)
bm=bmesh.new();bm.from_mesh(me);nl=bm.loops.layers.float_vector.new('NativeSealNormal')
for face,poly in zip(bm.faces,me.polygons):
 for loop,li in zip(face.loops,poly.loop_indices):loop[nl]=me.corner_normals[li].vector
def seal_cut(co,no):
 result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=co,plane_no=no,clear_outer=True)
 edges=[e for e in result['geom_cut'] if isinstance(e,bmesh.types.BMEdge) and e.is_boundary]
 caps=bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces'] if edges else []
 uv=bm.loops.layers.uv[0]
 for face in caps:
  face.normal_update();face.material_index=1
  for loop in face.loops:loop[nl]=face.normal;loop[uv].uv=(loop.vert.co.x/.055,loop.vert.co.z/.055)
seal_cut((0,-.025,0),(0,1,0))
for a in np.linspace(0,math.tau,64,endpoint=False):
 co=(CX+.049*math.cos(a),0,.9095+.038*math.sin(a));no=(math.cos(a)/.049,0,math.sin(a)/.038)
 seal_cut(co,no)
for v in bm.verts:v.co.x=CX+(v.co.x-CX)*.80;v.co.z=CZ+(v.co.z-.9095)*.95
ns=[]
for face in bm.faces:
 for loop in face.loops:
  n=loop[nl].copy();n.x/=.80;n.z/=.95;ns.append(tuple(n.normalized()))
bm.to_mesh(me);bm.free()
for poly in me.polygons:poly.use_smooth=True
me.normals_split_custom_set(ns);parts.append(seal)
def interface_band(name,axis,cut,keep_positive):
 me=factory.data.copy();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o)
 me.materials.append(recess)
 bm=bmesh.new();bm.from_mesh(me);layer=bm.loops.layers.float_vector.new('NativeNormals')
 for f,p in zip(bm.faces,me.polygons):
  for l,li in zip(f.loops,p.loop_indices):l[layer]=me.corner_normals[li].vector
 co=[0.,0.,0.];co[axis]=cut;normal=[0.,0.,0.];normal[axis]=1.
 result=bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=co,plane_no=normal,clear_inner=keep_positive,clear_outer=not keep_positive)
 if axis==0:
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,.966),plane_no=(0,0,1),clear_outer=True)
 edges=[e for e in bm.edges if e.is_boundary]
 caps=bmesh.ops.holes_fill(bm,edges=edges,sides=0)['faces']
 for f in caps:
  f.normal_update();f.material_index=1
  for l in f.loops:l[layer]=f.normal;l[bm.loops.layers.uv[0]].uv=(l.vert.co.y/.055,l.vert.co.z/.055)
 ns=[tuple(l[layer]) for f in bm.faces for l in f.loops];bm.to_mesh(me);bm.free()
 for p in me.polygons:p.use_smooth=True
 me.normals_split_custom_set(ns);parts.append(o)
 return o
interface_band('20_NativeLeftHeadInterface',0,CX-.0595,False)
interface_band('21_NativeRightHeadInterface',0,CX+.0595,True)
interface_band('22_NativeNeckInterface',2,.851,False)
bpy.data.objects.remove(factory,do_unlink=True)
for o in context:o.hide_render=True;o.hide_set(True)
# Keep source pieces editable. Produce a separate joined export without changing them.
source_collection=bpy.data.collections.new('GuanLei_V11_EditableParts');bpy.context.scene.collection.children.link(source_collection)
for o in parts:
 for col in list(o.users_collection):col.objects.unlink(o)
 source_collection.objects.link(o)
print('GEOMETRY_READY',len(parts),flush=True)
export_parts=[]
for o in parts:
 c=o.copy();c.data=o.data.copy();bpy.context.scene.collection.objects.link(c);export_parts.append(c)
bpy.ops.object.select_all(action='DESELECT')
for o in export_parts:o.select_set(True)
bpy.context.view_layer.objects.active=export_parts[0];bpy.ops.object.join();joined=bpy.context.object;joined.name='SM_ThunderGodHammer_head_mount_guan_lei_seat_V11'
joined.data.calc_loop_triangles();triangles=len(joined.data.loop_triangles)
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(joined.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,path_mode='STRIP')
bpy.ops.export_scene.gltf(filepath=str(P/'Export'/'GuanLei_V11.glb'),export_format='GLB',use_selection=True,export_apply=True)
joined.hide_render=True;joined.hide_set(True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'GuanLei_V11_Editable.blend'))
(P/'model_manifest.json').write_text(json.dumps(dict(revision='GuanLeiPrecisionV11',concept='../SeatConceptV10/GuanLei_Design_V10.png',method='new parametric closed core and carved swept shoulders; shallow native interface bands only',mesh=joined.name,triangles=triangles,objects=[o.name for o in parts],context=[o.name for o in context],interfaces=dict(left_x=CX-.065,right_x=CX+.065,neck_z=.842,band_width=.0055),status='candidate for user inspection; not imported',normal_maps='dedicated tangent-space metal normal; macro ornament modeled in geometry'),indent=2),encoding='utf-8')
print('GUANLEI_V11_SAVED',triangles,flush=True)
