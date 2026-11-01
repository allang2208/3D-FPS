"""JiLei V14: angular gathering shoulders and forged spine from the V10 concept.
Only native mating bands, the native seal and its seating disk are reused.
This is an isolated authoring candidate; no game assets or catalogs are changed.
"""
import bpy,bmesh,math,json
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;SOURCE=P.parent/'GuanLeiClosedCrownV12'
for d in ('Export','Previews'):(P/d).mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE/'GuanLei_V12_Editable.blend'))
bpy.context.preferences.filepaths.save_version=0
prior=json.loads((SOURCE/'model_manifest.json').read_text(encoding='utf-8'))
keep=('01_HeadInterfaceLoadWeb','11_RecessedRuneMedallion','15_OriginalRuneRelief','20_NativeLeftHeadInterface','21_NativeRightHeadInterface','22_NativeNeckInterface')
parts=[];context=[bpy.data.objects[n] for n in prior['context']]
for name in prior['objects']:
 o=bpy.data.objects.get(name)
 if name.startswith(keep):parts.append(o)
 elif o:bpy.data.objects.remove(o,do_unlink=True)
old=bpy.data.objects.get(prior['mesh'])
if old:bpy.data.objects.remove(old,do_unlink=True)
CX=-.0004452141;CZ=.911

def material(name):
 m=bpy.data.materials.new('M_JiLei14_'+name);m.use_nodes=True;ns=m.node_tree.nodes;ls=m.node_tree.links
 bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
 for kind in ('BaseColor','ORM','Normal'):
  tex=ns.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(P/'Textures'/('T_JiLei14_'+name+'_'+kind+'.png')))
  tex.image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
  if kind=='BaseColor':ls.new(tex.outputs['Color'],bs.inputs['Base Color'])
  elif kind=='ORM':
   s=ns.new('ShaderNodeSeparateColor');ls.new(tex.outputs['Color'],s.inputs[0]);ls.new(s.outputs['Green'],bs.inputs['Roughness']);ls.new(s.outputs['Blue'],bs.inputs['Metallic'])
  else:
   nm=ns.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.8;ls.new(tex.outputs['Color'],nm.inputs['Color']);ls.new(nm.outputs[0],bs.inputs['Normal'])
 return m
mats={n:material(n) for n in ('Steel','Silver','Recess','Inlay')}
steel,silver,recess,inlay=[mats[n] for n in ('Steel','Silver','Recess','Inlay')]
edge=steel.copy();edge.name='M_JiLei14_BurnishedEdge'
en=edge.node_tree.nodes;el=edge.node_tree.links;eb=next(n for n in en if n.type=='BSDF_PRINCIPLED');source=eb.inputs['Base Color'].links[0].from_socket
tint=en.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=1.;tint.inputs[2].default_value=(1.35,1.35,1.35,1)
el.new(source,tint.inputs[1]);el.new(tint.outputs[0],eb.inputs['Base Color'])
blue=bpy.data.materials['M_GuanLei11_ThunderInlay'].copy();blue.name='M_JiLei14_ColdLightningInlay'
bs=next(n for n in blue.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
bs.inputs['Base Color'].default_value=(.017,.072,.12,1);bs.inputs['Emission Color'].default_value=(.02,.24,.46,1);bs.inputs['Emission Strength'].default_value=.22;bs.inputs['Roughness'].default_value=.40;bs.inputs['Metallic'].default_value=.7
for o in parts:
 for i,m in enumerate(o.data.materials):
  if m and m.name.startswith('M_GuanLei12_'):
   suffix=m.name.removeprefix('M_GuanLei12_')
   if suffix in mats:o.data.materials[i]=mats[suffix]

def activate(o):
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o

def mesh(name,vs,fs,mat=steel,register=True):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(o);me.materials.append(mat)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 uv=me.uv_layers.new(name='UVMap')
 for p in me.polygons:
  axis=max(range(3),key=lambda a:abs(p.normal[a]));axes=[a for a in range(3) if a!=axis]
  for li in p.loop_indices:
   q=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=(q[axes[0]]/.055,q[axes[1]]/.055)
 if register:parts.append(o)
 return o

def bevel(o,width=.00045,segments=4):
 activate(o);m=o.modifiers.new('Forged edge radius','BEVEL');m.width=width;m.segments=segments;m.limit_method='ANGLE';m.angle_limit=.37
 bpy.ops.object.modifier_apply(modifier=m.name)
 for p in o.data.polygons:p.use_smooth=True
 m=o.modifiers.new('Stable broad metal planes','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=50;bpy.ops.object.modifier_apply(modifier=m.name)
 return o

def inset(poly,d):
 p=np.asarray(poly,float)
 # Signed polygon area determines inward normals, even for concave profiles.
 winding=1 if sum(p[i,0]*p[(i+1)%len(p),1]-p[(i+1)%len(p),0]*p[i,1] for i in range(len(p)))>0 else -1
 out=[]
 for i,q in enumerate(p):
  a=q-p[i-1];a/=np.linalg.norm(a);b=p[(i+1)%len(p)]-q;b/=np.linalg.norm(b)
  na=np.array([-a[1],a[0]])*winding;nb=np.array([-b[1],b[0]])*winding
  n=na+nb;delta=n*d/max(np.dot(n,na),.1)
  if np.linalg.norm(delta)>d*3:delta*=d*3/np.linalg.norm(delta)
  out.append(q+delta)
 return np.array(out)

def plate(name,poly,face=1,front=.049,back=.030,chamfer=.0014,mat=steel):
 poly=np.asarray(poly,float);inside=inset(poly,chamfer);N=len(poly)
 vs=[(CX+x,face*y,z) for ring,y in ((poly,back),(poly,front-chamfer*.55),(inside,front)) for x,z in ring]
 fs=[tuple(range(N-1,-1,-1))];mi=[0]
 for j in range(2):
  for i in range(N):fs.append((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i));mi.append(1 if j==1 else 0)
 fs.append(tuple(range(2*N,3*N)));mi.append(0)
 o=mesh(name,vs,fs,mat);o.data.materials.append(edge)
 for p,m in zip(o.data.polygons,mi):p.material_index=m
 return bevel(o,min(chamfer*.18,.00028),3)

def cross_loft(name,poly,rings,mat=steel):
 # Ring tuple: Y, X scale, Z offset. Complete enclosed three-dimensional body.
 N=len(poly);vs=[(CX+x*s,y,z+dz) for y,s,dz in rings for x,z in poly]
 fs=[tuple(range(N-1,-1,-1)),tuple((len(rings)-1)*N+i for i in range(N))]
 fs.extend((j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(len(rings)-1) for i in range(N))
 return bevel(mesh(name,vs,fs,mat),.0006,5)

def path(points,n=130):
 ps=np.asarray(points,float);out=[]
 for i in range(len(ps)-1):
  a=ps[i];b=ps[i+1];m0=(b-ps[max(0,i-1)])*.25;m1=(ps[min(len(ps)-1,i+2)]-a)*.25
  for t in np.linspace(0,1,max(4,n//(len(ps)-1)),endpoint=False):out.append((2*t**3-3*t*t+1)*a+(t**3-2*t*t+t)*m0+(-2*t**3+3*t*t)*b+(t**3-t*t)*m1)
 out.append(ps[-1]);return np.asarray(out)

def ribbon(name,points,width,front,back,face,mat,closed=False,register=True,taper=(False,False)):
 ps=np.asarray(points,float);N=len(ps);vs=[]
 arc=np.concatenate(([0.],np.cumsum(np.linalg.norm(np.diff(ps,axis=0),axis=1))));length=arc[-1]
 for i,p in enumerate(ps):
  t=ps[(i+1)%N]-ps[i-1] if closed else ps[min(i+1,N-1)]-ps[max(0,i-1)]
  n=np.array([-t[1],t[0]]);n/=max(np.linalg.norm(n),1e-8)
  envelope=1.
  for enabled,distance in ((taper[0],arc[i]),(taper[1],length-arc[i])):
   if enabled:
    u=min(1.,distance/.004);envelope*=.18+.82*u*u*(3-2*u)
  for a,y in ((-1,front),(1,front),(1,back),(-1,back)):
   q=p+n*a*width*envelope*.5;vs.append((CX+q[0],face*y,q[1]))
 fs=[]
 for i in range(N if closed else N-1):
  j=(i+1)%N
  for k in range(4):fs.append((i*4+k,j*4+k,j*4+(k+1)%4,i*4+(k+1)%4))
 if not closed:fs.extend([(3,2,1,0),tuple((N-1)*4+k for k in range(4))])
 o=mesh(name,vs,fs,mat,register)
 if register:bevel(o,min(width*(.04 if any(taper) else .12),.00012),3)
 return o

def channel(obj,points,face,front,width=.0025,name='GatheringChannel'):
 pts=path(points)
 cutter=ribbon('TEMP_cut',pts,width,front+.003,front-.00135,face,recess,register=False,taper=(True,True))
 # These tapered shoulders require the manifold solver: the exact solver
 # deletes the entire operand at their close coplanar chamfer transitions.
 activate(obj);tri=obj.modifiers.new('Explicit planar face triangulation','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
 m=obj.modifiers.new('True recessed channel','BOOLEAN');m.operation='DIFFERENCE';m.solver='MANIFOLD' if obj.name.startswith('02_Ascending') else 'EXACT';m.object=cutter
 bpy.ops.object.modifier_apply(modifier=m.name)
 if not obj.data.vertices:raise RuntimeError('Channel removed its supporting volume: '+obj.name)
 bpy.data.objects.remove(cutter,do_unlink=True)
 ribbon(name+'_SilverSeat',pts,width*.60,front-.00060,front-.0016,face,inlay,taper=(True,True))
 ribbon(name+'_BlueInner',pts[2:-2],width*.14,front-.00053,front-.0016,face,blue,taper=(True,True))

def solid_union(target,other):
 activate(target);m=target.modifiers.new('Continuous forged junction','BOOLEAN');m.operation='UNION';m.solver='MANIFOLD';m.object=other;bpy.ops.object.modifier_apply(modifier=m.name)
 if other in parts:parts.remove(other)
 bpy.data.objects.remove(other,do_unlink=True)
 if not target.data.vertices:raise RuntimeError('Joined inlay volume was lost')

def fillet_path(points,radius=.0025):
 ps=np.asarray(points,float);out=[ps[0]]
 def line_to(q):
  a=np.asarray(out[-1]);count=max(2,int(np.linalg.norm(q-a)/.0004)+1)
  out.extend(a*(1-t)+q*t for t in np.linspace(0,1,count)[1:])
 for i in range(1,len(ps)-1):
  a,p,b=ps[i-1],ps[i],ps[i+1];u=p-a;v=b-p;lu=np.linalg.norm(u);lv=np.linalg.norm(v);u/=lu;v/=lv
  if np.dot(u,v)>.9999:line_to(p);continue
  d=min(radius,lu*.22,lv*.22);q0=p-u*d;q1=p+v*d;line_to(q0)
  out.extend((1-t)**2*q0+2*t*(1-t)*p+t*t*q1 for t in np.linspace(0,1,14)[1:])
 line_to(ps[-1]);return np.asarray(out)

def network(name,paths,width,front,back,mat):
 pieces=[ribbon(name,fillet_path(points),width,front,back,1,mat,register=False,taper=(True,False)) for points in paths]
 obj=pieces[0]
 for other in pieces[1:]:solid_union(obj,other)
 obj.name=name;return obj

def project_network(obj,surface,face=1,on_roof=False):
 # Boolean union simplifies coplanar faces. Retessellate those faces BEFORE
 # wrapping them to the curved support; otherwise long triangles cut across
 # the curve and the blue/silver layers intersect at their thin separation.
 bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.triangulate(bm,faces=list(bm.faces))
 for _ in range(8):
  long_edges=[e for e in bm.edges if e.calc_length()>.0012]
  if not long_edges:break
  bmesh.ops.subdivide_edges(bm,edges=long_edges,cuts=1,use_grid_fill=True)
  bmesh.ops.triangulate(bm,faces=[f for f in bm.faces if len(f.verts)>3])
 bm.to_mesh(obj.data);bm.free()
 for v in obj.data.vertices:
  x=v.co.x;a=v.co.z;h=v.co.y
  origin=Vector((x,a,1.08)) if on_roof else Vector((x,face*.085,a))
  direction=Vector((0,0,-1)) if on_roof else Vector((0,-face,0))
  point=surface.ray_cast(origin,direction,.24)[0]
  if point is None:raise RuntimeError('Connected inlay left its supporting surface: '+obj.name)
  v.co=Vector((x,a,point.z+h)) if on_roof else Vector((x,point.y+face*h,a))
 bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
 for p in obj.data.polygons:
  for li in p.loop_indices:
   co=obj.data.vertices[obj.data.loops[li].vertex_index].co
   obj.data.uv_layers[0].data[li].uv=(co.x/.055,(co.y if on_roof else co.z)/.055)

def engrave_network(target,paths,name,width=.0021,face=1,on_roof=False):
 bpy.context.view_layer.update();surface=BVHTree.FromObject(target,bpy.context.evaluated_depsgraph_get())
 cut=network('TEMP_connected_cut',paths,width,.003,-.00135,recess);project_network(cut,surface,face,on_roof)
 activate(target);mod=target.modifiers.new('Joined recessed lightning network','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='MANIFOLD';mod.object=cut;bpy.ops.object.modifier_apply(modifier=mod.name)
 bpy.data.objects.remove(cut,do_unlink=True)
 if not target.data.vertices:raise RuntimeError('Supporting volume was removed by network cut')
 target.data.normals_split_custom_set([(0.,0.,0.)]*len(target.data.loops))
 for suffix,w,h,mat in [('Silver',width*.60,-.00085,inlay),('Blue',width*.14,-.00025,blue)]:
  obj=network(name+'_'+suffix,paths,w,h,-.0016,mat);project_network(obj,surface,face,on_roof);parts.append(obj)
  for p in obj.data.polygons:p.use_smooth=True
  obj.data.normals_split_custom_set([(0.,0.,0.)]*len(obj.data.loops))

def knot_panel(name,cx,cz,width,height,face,front,cycles=3):
 poly=[(cx-width/2,cz-height/2),(cx+width/2,cz-height/2),(cx+width/2,cz+height/2),(cx-width/2,cz+height/2)]
 plate(name+'_Seat',poly,face,front,front-.0025,.0007,recess)
 for phase in (0,math.tau/3,2*math.tau/3):
  pts=[]
  for t in np.linspace(0,1,320):
   x=cx+(t-.5)*(width-.005);envelope=min(1,t/.05,(1-t)/.05)
   z=cz+height*.27*math.sin(t*math.tau*cycles+phase)*envelope;pts.append((x,z))
  ribbon(name+'_WovenSilver',pts,.0007,front+.00016,front-.0007,face,inlay)

# Full volume, faceted cross sections taper into both the cap and the neck.
levels=[(.850,.038,.032),(.858,.041,.034),(.877,.045,.0355),(.900,.050,.038),(.924,.052,.038),(.946,.050,.035),(.972,.052,.0335),(.986,.046,.033)]
vs=[]
for z,rx,ry in levels:
 c=.0055
 for x,y in [(rx-c,-ry),(rx,-ry+c),(rx,ry-c),(rx-c,ry),(-rx+c,ry),(-rx,ry-c),(-rx,-ry+c),(-rx+c,-ry)]:vs.append((CX+x,y,z))
fs=[tuple(range(7,-1,-1)),tuple((len(levels)-1)*8+i for i in range(8))]
fs.extend((i*8+j,i*8+(j+1)%8,(i+1)*8+(j+1)%8,(i+1)*8+j) for i in range(len(levels)-1) for j in range(8))
bevel(mesh('01_TaperedForgedCore',vs,fs),.0008,5)

upper=[(.033,.869),(.061,.896),(.055,.916),(.062,.933),(.060,.946),(.052,.959),(.068,.970),(.073,.978),(.053,.989),(.037,.985),(.032,.965),(.028,.951),(.030,.943),(.039,.935),(.041,.918),(.041,.904),(.034,.891),(.028,.882)]
for sign in (-1,1):
 cross_loft('02_ContinuousShoulderDepth',[(sign*x,z) for x,z in upper],[(-.031,1,0),(-.018,.985,.0004),(0,.965,.0007),(.018,.985,.0004),(.031,1,0)])
for face in (-1,1):
 for sign in (-1,1):
  p=[(sign*x,z) for x,z in upper]
  shoulder=plate('02_AscendingForgedShoulder',p,face,.0505,.026,.0017)
  channel(shoulder,[(sign*x,z) for x,z in [(.0345,.879),(.049,.900),(.046,.918),(.052,.934),(.043,.948),(.039,.963),(.047,.973),(.043,.984)]],face,.0505,.00265,'03_UpperConduction')
  # A seated angular silver knot on the broad upper outside facet.
  base=np.array([sign*.058,.976]);t=np.array([sign*.76,-.65]);n=np.array([-t[1],t[0]])
  for phase in (0,math.pi):
   pts=[base+t*((q-.5)*.018)+n*(.0019*math.sin(q*math.tau*2+phase)*math.sin(math.pi*q)) for q in np.linspace(0,1,140)]
   ribbon('06_ShoulderFineInterlace',pts,.00062,.05065,.0497,face,inlay)

# Low trapezoid cap, with one short integral diamond crest.
cap=[(-.045,.974),(.045,.974),(.051,.986),(.047,.991),(.018,.992),(0,.994),(-.018,.992),(-.047,.991),(-.051,.986)]
capmesh=cross_loft('07_LowTrapezoidCap',cap,[(-.0395,1,0),(-.030,1,.0003),(0,.985,.001),(.030,1,.0003),(.0395,1,0)])
roof_paths=[[(sign*.037,face*.030),(sign*.022,face*.019),(0,face*.004),(0,0)] for face in (-1,1) for sign in (-1,1)]
roof_paths.extend([[(0,face*.030),(0,face*.015),(0,0)] for face in (-1,1)])
engrave_network(capmesh,roof_paths,'07_ConnectedCrownInlay',.0019,on_roof=True)
for face in (-1,1):
 knot_panel('08_CapInterlace',0,.9823,.063,.011,face,.0410,3)
crest=[(-.008,.991),(-.009,.995),(0,1.007),(.009,.995),(.008,.991)]
plate('09_ShortDiamondCrest',crest,-1,.006,-.006,.00125)
for face in (-1,1):
 plate('10_CrestInset',[(0,1.003),(.0038,.995),(0,.9918),(-.0038,.995)],face,.0062,.0045,.0005,recess)
 plate('10_CrestBlueInlay',[(0,1.0018),(.0017,.995),(0,.993),(-.0017,.995)],face,.0063,.0052,.00025,blue)

# Front spine rises from the original medallion toward the cap.
frontspine=[(0,.941),(.0045,.952),(.0033,.974),(0,.979),(-.0033,.974),(-.0045,.952)]
sp=plate('11_FrontConductorSpine',frontspine,-1,.0455,.031,.0008)
channel(sp,[(0,.947),(0,.961),(0,.977)],-1,.0455,.0019,'12_CentralConduction')

# Solid tapered rear shield with Y-shaped recessed channels and central keel.
NZ=181;NX=101;verts=[]
def smooth01(t):
 t=max(0,min(1,t));return t*t*(3-2*t)
for surface in (0,1):
 for z in np.linspace(.861,.976,NZ):
  width=float(np.interp(z,[.861,.874,.903,.945,.976],[.0008,.033,.043,.042,.032]))
  fade=smooth01((z-.866)/.018)*smooth01((.969-z)/.022)
  for v in np.linspace(-1,1,NX):
   x=v*width;ridge=.0018*max(0,1-(x/.014)**2)**2*fade
   yy=.0418+ridge-.0012*smooth01((abs(v)-.93)/.07) if surface==0 else .024
   verts.append((CX+x,yy,z))
plane=NZ*NX;faces=[]
for k in range(2):
 for iz in range(NZ-1):
  for ix in range(NX-1):
   a=k*plane+iz*NX+ix;faces.append((a,a+1,a+NX+1,a+NX))
for iz in range(NZ-1):
 for ix in (0,NX-1):
  a=iz*NX+ix;b=(iz+1)*NX+ix;faces.append((a,b,b+plane,a+plane))
for iz in (0,NZ-1):
 for ix in range(NX-1):
  a=iz*NX+ix;faces.append((a,a+plane,a+plane+1,a+1))
back=mesh('14_RearTaperedShield',verts,faces)
for p in back.data.polygons:p.use_smooth=p.index<2*(NZ-1)*(NX-1)
rear_paths=[[(sign*.032,.964),(sign*.022,.940),(0,.917),(0,.912)] for sign in (-1,1)]
rear_paths.append([(0,.874),(0,.894),(0,.916)])
engrave_network(back,rear_paths,'15_ConnectedRearLightning',.00215,1)

# Closed short neck transition with continuous elliptical UV and seated inlay.
N=192;profile=[(.850,.0405,.033),(.851,.042,.0345),(.853,.042,.0345),(.854,.040,.033),(.861,.040,.033),(.862,.042,.0345),(.864,.042,.0345),(.866,.040,.033)]
vs=[]
for z,rx,ry in profile:
 for a in np.linspace(0,math.tau,N,endpoint=False):vs.append((CX+rx*math.cos(a),ry*math.sin(a),z))
fs=[tuple(range(N-1,-1,-1)),tuple((len(profile)-1)*N+j for j in range(N))]
fs.extend((i*N+j,i*N+(j+1)%N,(i+1)*N+(j+1)%N,(i+1)*N+j) for i in range(len(profile)-1) for j in range(N))
neck=mesh('18_SeatedNeckTransition',vs,fs)
for poly in neck.data.polygons:
 poly.use_smooth=abs(poly.normal.z)<.95
 if len(poly.vertices)==4:
  ids=[neck.data.loops[li].vertex_index for li in poly.loop_indices];seam=max(i%N for i in ids)-min(i%N for i in ids)>N/2
  for li in poly.loop_indices:
   vi=neck.data.loops[li].vertex_index;j=vi%N;j=N if seam and j==0 else j
   neck.data.uv_layers[0].data[li].uv=(j/N*math.tau*.037/.055,(neck.data.vertices[vi].co.z-.850)/.055)
for face in (-1,1):
 knot_panel('19_LowerCrossKnot',0,.869,.055,.014,face,.0375,2)
 # The short ellipse follows the neck surface rather than hanging in front.
 for phase in (0,math.pi):
  pts=[]
  for a in np.linspace(-1.08,1.08,180):
   x=.040*math.sin(a);z=.8575+.0021*math.sin(a*9+phase)
   pts.append((x,z,.033*math.cos(a)+.00015))
  # Constant profile ribbon is built then conformed to the elliptical neck.
  obj=ribbon('20_NeckSeatedInterlace',[(x,z) for x,z,y in pts],.00062,.034,.0332,face,inlay)
  for v in obj.data.vertices:
   x=v.co.x-CX;offset=face*v.co.y-.034
   v.co.y=face*(.033*math.sqrt(max(0,1-(x/.040)**2))+.00015+offset)

# The upper shoulder faces and their engravings share one affine lean toward
# the cap. Their interfaces stay fixed; the buried volume bridges both faces.
for o in parts:
 if o.name.startswith(('02_Ascending','03_Upper','06_Shoulder')):
  face=-1 if sum(v.co.y for v in o.data.vertices)<0 else 1
  for v in o.data.vertices:v.co.y-=face*.10*max(0.,v.co.z-.940)
  activate(o);m=o.modifiers.new('Rebuild normals after forged lean','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=50;bpy.ops.object.modifier_apply(modifier=m.name)
# Fit the fine weave to the actual chamfered shoulder face, including its
# angled outer margins. Preserve finite thickness and sink the root surface.
bpy.context.view_layer.update()
shoulders=[o for o in parts if o.name.startswith('02_Ascending')]
for ornament in [o for o in parts if o.name.startswith('06_Shoulder')]:
 face=-1 if sum(v.co.y for v in ornament.data.vertices)<0 else 1
 side=-1 if sum(v.co.x-CX for v in ornament.data.vertices)<0 else 1
 target=next(o for o in shoulders if (sum(v.co.y for v in o.data.vertices)<0)==(face<0) and (sum(v.co.x-CX for v in o.data.vertices)<0)==(side<0))
 surface=BVHTree.FromObject(target,bpy.context.evaluated_depsgraph_get())
 for v in ornament.data.vertices:
  height=face*v.co.y-(.05065-.10*(v.co.z-.940))
  v.co.x=CX+side*.058+(v.co.x-CX-side*.058)*.76;v.co.z=.976+(v.co.z-.976)*.76
  point=surface.ray_cast(Vector((v.co.x,face*.080,v.co.z)),Vector((0,-face,0)),.15)[0]
  if point is None:raise RuntimeError('Shoulder weave does not meet its supporting metal')
  v.co.y=point.y+face*(height+.00010)
 activate(ornament);m=ornament.modifiers.new('Surface fitted inlay normals','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=50;bpy.ops.object.modifier_apply(modifier=m.name)
for o in context:o.hide_render=True;o.hide_set(True)
for o in parts:o.hide_render=False;o.hide_set(False)
for col in bpy.data.collections:
 if col.name=='GuanLei_V11_EditableParts':col.name='JiLei_V14_NativeInterfaces'
export=[]
for o in parts:
 c=o.copy();c.data=o.data.copy();bpy.context.scene.collection.objects.link(c);export.append(c)
bpy.ops.object.select_all(action='DESELECT')
for o in export:o.select_set(True)
bpy.context.view_layer.objects.active=export[0];bpy.ops.object.join();joined=bpy.context.object;joined.name='SM_ThunderGodHammer_head_mount_ji_lei_seat_V14';joined.data.calc_loop_triangles()
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(joined.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,path_mode='STRIP')
bpy.ops.export_scene.gltf(filepath=str(P/'Export'/'JiLei_V14.glb'),export_format='GLB',use_selection=True,export_apply=True)
joined.hide_render=True;joined.hide_set(True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'JiLei_V14_Editable.blend'))
manifest=dict(revision='JiLeiInlaidLightningV14',concept=str(P.parent/'SeatConceptV10/JiLei_Design_V10.png'),source_interfaces=str(SOURCE/'GuanLei_V12_Editable.blend'),mesh=joined.name,triangles=len(joined.data.loop_triangles),objects=[o.name for o in parts],context=[o.name for o in context],design='Continuous full-height forged shoulders and tapered recessed lightning; unioned crown and rear Y inlays; integrated rear keel; restrained satin silver and blue seams',normal_maps='four 4096px seamless tangent-space normal maps connected to their PBR materials',purpose='High resolution authoring candidate for user inspection, not runtime LOD',published_to_game=False,user_accepted=False)
(P/'model_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('JILEI_V14_SAVED',manifest['triangles'],len(parts),flush=True)
