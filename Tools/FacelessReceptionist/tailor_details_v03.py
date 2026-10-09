"""Author V03 tailored seams, notched lapels, buttons, pockets and nameplate."""
import bpy,bmesh,math,json
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\FacelessReceptionist20261007\V03')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V03_Fit.blend'))
s=bpy.context.scene;rig=bpy.data.objects['root'];body=bpy.data.objects['Receptionist_CompleteBody']
s.frame_set(0);rig.animation_data.action=None
for track in rig.animation_data.nla_tracks:track.mute=True
raw=list(rig['source_world_matrix']);rig.matrix_world=Matrix([raw[i:i+4] for i in range(0,16,4)])
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
suit=bpy.data.materials['Receptionist_Suit'];shirt=bpy.data.materials['Receptionist_Shirt']
metal=bpy.data.materials['Receptionist_Badge'];trim=bpy.data.materials['Receptionist_Trim'];leather=bpy.data.materials['Receptionist_Shoes']
jacket=bpy.data.objects['Receptionist_Blazer_Continuous'];skirt=bpy.data.objects['Receptionist_Skirt']
def normalise(ws):
 ws={n:w for n,w in sorted(ws.items(),key=lambda kv:-kv[1])[:8] if w>1e-5}
 total=sum(ws.values());return {n:w/total for n,w in ws.items()} if total else {'pelvis':1}
def weights(o,v):return {o.vertex_groups[g.group].name:g.weight for g in v.groups if g.weight>1e-5}
def bind(o,values):
 o.vertex_groups.clear()
 for n in sorted({n for w in values for n in w}):o.vertex_groups.new(name=n)
 for v,ws in zip(o.data.vertices,values):
  for n,w in ws.items():o.vertex_groups[n].add([v.index],w,'REPLACE')
 o.parent=rig;o.matrix_parent_inverse=rig.matrix_world.inverted()
 if not any(m.type=='ARMATURE' for m in o.modifiers):
  m=o.modifiers.new('NurseNativeSkin','ARMATURE');m.object=rig
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):
 active(o);bpy.ops.object.modifier_apply(modifier=m.name)
def shell(o,thickness):
 m=o.modifiers.new('TailoredThickness','SOLIDIFY');m.thickness=thickness;m.offset=0;apply(o,m)
# Relax voxel-cut cloth surfaces with a volume-preserving Taubin pass.
# Body geometry and skin weights stay intact; move both sides of each shell equally.
for garment in [jacket,bpy.data.objects['Receptionist_Shirt_Continuous']]:
 count=len(garment.data.vertices)//2
 source=np.array([v.co[:] for v in garment.data.vertices[:count]])
 edge_use={}
 for face in garment.data.polygons:
  ids=list(face.vertices)
  if not all(i<count for i in ids):continue
  for a,b in zip(ids,ids[1:]+ids[:1]):
   key=tuple(sorted((a,b)));edge_use[key]=edge_use.get(key,0)+1
 border_edges=[e for e,n in edge_use.items() if n==1]
 border={i for edge in border_edges for i in edge}
 a=[];b=[]
 for i,j in edge_use:
  if i not in border or (i,j) in border_edges:a.append(i);b.append(j)
  if j not in border or (i,j) in border_edges:a.append(j);b.append(i)
 a=np.array(a);b=np.array(b);degree=np.bincount(a,minlength=count)
 points=source.copy()
 for iteration in range(32):
  for factor in [.47,-.49]:
   sums=np.zeros_like(points);np.add.at(sums,a,points[b])
   means=np.divide(sums,degree[:,None],out=points.copy(),where=degree[:,None]>0)
   points+=(means-points)*factor
 delta=points-source
 limit=np.where(source[:,2]>1.37,.020,.012)
 lengths=np.linalg.norm(delta,axis=1)
 delta*=np.minimum(1,limit/np.maximum(lengths,1e-8))[:,None]
 for i,d in enumerate(delta):
  garment.data.vertices[i].co+=Vector(d);garment.data.vertices[i+count].co+=Vector(d)
 # A clean V-cut replaces the stair steps left by trimming dense source triangles.
 if garment==jacket:
  for i in border:
   v=garment.data.vertices[i];q=v.co.copy()
   if 1.10<q.z<1.526 and abs(q.x)<.125 and q.y<-.034:
    target=np.interp(q.z,[1.10,1.17,1.30,1.42,1.49,1.526],[.0005,.0005,.038,.072,.080,.065])
    dx=math.copysign(target,q.x)-q.x
    v.co.x+=dx;garment.data.vertices[i+count].co.x+=dx
 garment.data.update()
 garment.data.normals_split_custom_set([(0,0,0)]*len(garment.data.loops))
# Straighten the sewn jacket hem without flattening the full lower panel.
N=len(jacket.data.vertices)//2
edge_counts={}
for f in jacket.data.polygons:
 ids=list(f.vertices)
 if not all(i<N for i in ids):continue
 for a,b in zip(ids,ids[1:]+ids[:1]):
  key=tuple(sorted((a,b)));edge_counts[key]=edge_counts.get(key,0)+1
boundary={i for edge,n in edge_counts.items() if n==1 for i in edge}
hem=[i for i in boundary if jacket.data.vertices[i].co.z<1.05 and abs(jacket.data.vertices[i].co.x)<.30]
hem_z=float(np.median([jacket.data.vertices[i].co.z for i in hem]))
for i in hem:
 delta=hem_z-jacket.data.vertices[i].co.z
 jacket.data.vertices[i].co.z+=delta;jacket.data.vertices[i+N].co.z+=delta
jacket.data.update();jacket.data.normals_split_custom_set([(0,0,0)]*len(jacket.data.loops))
def surface(o):
 o.data.calc_loop_triangles();pts=[v.co.copy() for v in o.data.vertices];ts=[tuple(t.vertices) for t in o.data.loop_triangles]
 ws=[weights(o,v) for v in o.data.vertices]
 return (BVHTree.FromPolygons(pts,ts,all_triangles=True),pts,ts,ws)
surfaces={o.name:surface(o) for o in [body,jacket,skirt,bpy.data.objects['Receptionist_Shirt_Continuous']]}
def skin_at(p,o=jacket):
 tree,pts,ts,ws=surfaces[o.name];h=tree.find_nearest(p);ids=ts[h[2]]
 b=barycentric_transform(h[0],*(pts[i] for i in ids),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
 out={}
 for i,f in zip(ids,b):
  for n,w in ws[i].items():out[n]=out.get(n,0)+w*max(0,float(f))
 return normalise(out)
def facepoint(x,z,o=jacket,back=False,ease=.002):
 tree=surfaces[o.name][0]
 h=tree.ray_cast(Vector((x,.8 if back else -.8,z)),Vector((0,-1 if back else 1,0)),1.6)
 if h[0] is None or (h[1].y<.03 if back else h[1].y>-.03):
  h=tree.find_nearest(Vector((x,.24 if back else -.24,z)))
 # Keep the authored cutline coordinates even when the ray passed the V opening.
 return Vector((x,h[0].y+(ease if back else -ease),z)),h[1]
created=[]
def mesh(name,verts,faces,mat,source=jacket,constant=None):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
 o=bpy.data.objects.new(name,me);s.collection.objects.link(o);me.materials.append(mat)
 for f in me.polygons:f.use_smooth=True
 uv=me.uv_layers.new(name='UVMap')
 for loop in me.loops:
  p=me.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(p.x*3,p.z*3)
 bind(o,[constant or skin_at(v.co,source) for v in me.vertices]);created.append(o);return o
def tube(name,paths,mat=trim,source=jacket,radius=.00085,segments=6):
 verts=[];faces=[]
 for path in paths:
  if len(path)<2:continue
  start=len(verts)
  for i,p in enumerate(path):
   p=Vector(p);t=(Vector(path[min(i+1,len(path)-1)])-Vector(path[max(0,i-1)])).normalized()
   axis=Vector((0,0,1)) if abs(t.z)<.9 else Vector((0,1,0))
   u=t.cross(axis).normalized();v=t.cross(u).normalized()
   for k in range(segments):verts.append(tuple(p+radius*(u*math.cos(k*2*math.pi/segments)+v*math.sin(k*2*math.pi/segments))))
  for j in range(len(path)-1):
   for k in range(segments):
    a=start+j*segments+k;b=start+j*segments+(k+1)%segments
    faces.append((a,b,b+segments,a+segments))
 return mesh(name,verts,faces,mat,source)
def stitch_paths(path,spacing=.006,length=.0028):
 path=[Vector(p) for p in path]
 lengths=[0.]
 for a,b in zip(path,path[1:]):lengths.append(lengths[-1]+(b-a).length)
 def point(d):
  i=max(0,min(len(path)-2,int(np.searchsorted(lengths,d))-1));f=(d-lengths[i])/max(1e-9,lengths[i+1]-lengths[i])
  return path[i].lerp(path[i+1],f)
 return [[point(d),point(d+length/2),point(d+length)] for d in np.arange(.002,max(.002,lengths[-1]-length),spacing)]
# Reform the independent lapels with a notch and shallow rolled edge.
lapel_edges=[]
for side in ['-1','1']:
 old=bpy.data.objects['Receptionist_Lapel_'+side];sign=int(side)
 rows=48;verts=[];faces=[]
 for j,z in enumerate(np.linspace(1.161,1.492,rows)):
  x=float(np.interp(z,[1.16,1.17,1.30,1.42,1.49,1.526],[.0004,.0005,.038,.072,.080,.065]))
  width=float(np.interp(z,[1.162,1.30,1.44,1.475,1.486,1.526],[.002,.027,.035,.028,.019,.026]))
  for k in range(7):
   f=k/6
   point,normal=facepoint(sign*(x+width*f),float(z),ease=.003+.0045*math.sin(math.pi*f))
   verts.append(tuple(point))
  if j<rows-1:
   for k in range(6):a=j*7+k;faces.append((a,a+1,a+8,a+7))
 # Smooth depth along each strip while keeping the designed cutline intact.
 for _ in range(10):
  oldverts=[Vector(v) for v in verts]
  for j in range(1,rows-1):
   for k in range(7):
    i=j*7+k;p=oldverts[i].copy()
    p.y=.5*p.y+.25*(oldverts[i-7].y+oldverts[i+7].y);verts[i]=tuple(p)
 left=[Vector(verts[j*7]) for j in range(rows)]
 right=[Vector(verts[j*7+6]) for j in range(rows)]
 bpy.data.objects.remove(old,do_unlink=True)
 o=mesh('Receptionist_Lapel_'+side,verts,faces,suit);shell(o,.0025)
 lapel_edges.extend([left,right])
tube('Receptionist_Lapel_EdgeRoll',lapel_edges,source=jacket,radius=.0009)
tube('Receptionist_Lapel_TopStitch',[p for edge in lapel_edges for p in stitch_paths(edge)],source=jacket,radius=.00028,segments=4)
# Build a subtle cloth placket down the center of the visible shirt.
sh=bpy.data.objects['Receptionist_Shirt_Continuous'];path=[]
for z in np.linspace(1.17,1.475,42):p,n=facepoint(0,z,sh,ease=.0015);path.append(p)
tube('Receptionist_Shirt_Placket',[path],shirt,sh,.0015)
# Round, rimmed jacket buttons; each whole button uses its attachment weights.
old_buttons=[o for o in s.objects if o.name.startswith('Receptionist_Blazer_Button')]
button_centers=[sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices) for o in old_buttons]
for o in old_buttons:bpy.data.objects.remove(o,do_unlink=True)
buttonhole_paths=[]
for index,c in enumerate(sorted(button_centers,key=lambda p:-p.z)):
 c,n=facepoint(c.x,c.z,ease=.0035)
 u=Vector((1,0,0));u=(u-n*u.dot(n)).normalized();v=n.cross(u).normalized()
 # Ring face and inset center use the same solid mesh/material regions.
 verts=[];faces=[];steps=24
 for r,depth in [(.0058,0),(.0062,.0011),(.0051,.0020),(.0014,.0020)]:
  for k in range(steps):verts.append(tuple(c+(u*math.cos(k*2*math.pi/steps)+v*math.sin(k*2*math.pi/steps))*r+n*depth))
 for j in range(3):
  for k in range(steps):a=j*steps+k;b=j*steps+(k+1)%steps;faces.append((a,b,b+steps,a+steps))
 faces.append(tuple(range(3*steps,4*steps)))
 o=mesh('Receptionist_ButtonRound_'+str(index),verts,faces,metal,constant=skin_at(c))
 # Twin dark thread holes and a center fastening thread are real local geometry.
 holepaths=[]
 for side in [-1,1]:
  cc=c+u*(side*.0013)+n*.0022
  holepaths.append([cc+u*.0004,cc-u*.0004])
 tube('Receptionist_ButtonThread_'+str(index),holepaths,trim,jacket,.00065,6)
 ph,nh=facepoint(c.x+.014,c.z,ease=.002)
 buttonhole_paths.append([ph+Vector((0,0,-.004)),ph+Vector((0,0,.004))])
tube('Receptionist_Buttonholes',buttonhole_paths,trim,jacket,.00085)
# Double-welt pockets, a shadowed opening and understated stitching.
for sign in [-1,1]:
 name='Receptionist_PocketWelt_'+str(sign)
 old=bpy.data.objects.get(name)
 center=sum((v.co for v in old.data.vertices),Vector())/len(old.data.vertices)
 bpy.data.objects.remove(old,do_unlink=True)
 paths=[]
 for dz in [-.004,.004]:
  path=[]
  for x in np.linspace(center.x-.034,center.x+.034,18):
   p,n=facepoint(float(x),center.z+dz,ease=.003);path.append(p)
  paths.append(path)
 tube(name,paths,suit,jacket,.0022,8)
 opening=[]
 for x in np.linspace(center.x-.031,center.x+.031,18):
  p,n=facepoint(float(x),center.z,ease=.0015);opening.append(p)
 tube('Receptionist_PocketOpening_'+str(sign),[opening],trim,jacket,.0011)
 tube('Receptionist_PocketStitch_'+str(sign),[p for line in paths for p in stitch_paths(line,.004,.002)],trim,jacket,.00027,4)
# Jacket hem, back center seam, sleeve seams, cuff edges.
hem_vertices=[jacket.data.vertices[i].co.copy() for i in hem]
angles=np.array([math.atan2(p.x,-(p.y-.027)) for p in hem_vertices])
radii=np.array([math.hypot(p.x,p.y-.027) for p in hem_vertices])
order=np.argsort(angles);angles=angles[order];radii=radii[order]
theta=np.linspace(-math.pi,math.pi,192,endpoint=False)
radius=np.interp(theta,angles,radii,period=2*math.pi)
for _ in range(8):radius=(2*radius+np.roll(radius,1)+np.roll(radius,-1))/4
hem_path=[Vector((r*math.sin(t),.027-r*math.cos(t),hem_z+.001)) for r,t in zip(radius+.0018,theta)]
hem_path.append(hem_path[0].copy())
tube('Receptionist_Blazer_HemFinish',[hem_path],suit,jacket,.0014,6)
tube('Receptionist_Blazer_HemStitch',stitch_paths(hem_path,.006,.0025),trim,jacket,.0003,4)
back_path=[facepoint(0,float(z),back=True,ease=.0018)[0] for z in np.linspace(hem_z+.018,1.487,72)]
tube('Receptionist_Blazer_BackSeam',[back_path],trim,jacket,.0008)
tube('Receptionist_Blazer_BackStitch',stitch_paths(back_path,.006,.0026),trim,jacket,.00028,4)
for side in ['l','r']:
 a,b,c=[rig.matrix_world@rig.data.bones[n+'_'+side].head_local for n in ['upperarm','lowerarm','hand']]
 line=[]
 for t in np.linspace(.12,.98,60):
  center=a.lerp(b,t*2) if t<.5 else b.lerp(c,(t-.5)*2)
  h=surfaces[jacket.name][0].ray_cast(center,Vector((0,1,0)),.20)
  if h[0] is not None:line.append(h[0]+h[1]*.0018)
 tube('Receptionist_SleeveSeam_'+side,[line],trim,jacket,.0007)
 cuff=bpy.data.objects['Receptionist_Shirt_Cuff_'+side];surfaces[cuff.name]=surface(cuff)
 for row in [0,4]:
  ring=[cuff.data.vertices[row*49+i].co.copy() for i in range(49)]
  ring=[p+surfaces[cuff.name][0].find_nearest(p)[1]*.001 for p in ring]
  tube('Receptionist_CuffStitch_'+side+'_'+str(row),stitch_paths(ring,.0045,.0022),trim,cuff,.00027,4)
# Skirt seams respect the motion-authored cloth weights and rear vent.
for sign in [-1,1]:
 line=[]
 for z in np.linspace(.50,1.09,72):
  h=surfaces[skirt.name][0].ray_cast(Vector((0,.027,float(z))),Vector((sign,0,0)),.6)
  if h[0] is not None:line.append(h[0]+h[1]*.0015)
 tube('Receptionist_SkirtSideSeam_'+str(sign),[line],trim,skirt,.0008)
back=[facepoint(0,float(z),skirt,True,.0015)[0] for z in np.linspace(.723,1.09,48)]
tube('Receptionist_SkirtBackSeam',[back],trim,skirt,.0008)
for sign in [-1,1]:
 line=[facepoint(sign*.021,float(z),skirt,True,.0015)[0] for z in np.linspace(.499,.697,32)]
 tube('Receptionist_VentFinish_'+str(sign),[line],suit,skirt,.0012)
# Enamel/brass reception badge with readable raised lettering.
old=bpy.data.objects['Receptionist_NameBadge'];center=sum((v.co for v in old.data.vertices),Vector())/len(old.data.vertices)
for name in ['Receptionist_NameBadge','Receptionist_BadgeLettering']:
 bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
center,n=facepoint(center.x,center.z,ease=.004)
u=Vector((1,0,0));u=(u-n*u.dot(n)).normalized();v=n.cross(u).normalized()
if v.z<0:v=-v
badge_skin=skin_at(center)
verts=[tuple(center+u*x+v*z+n*d) for d in [0,.0016] for x,z in [(-.0375,-.013),(.0375,-.013),(.0375,.013),(-.0375,.013)]]
faces=[(3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
plaque=mesh('Receptionist_NameBadge',verts,faces,metal,constant=badge_skin)
border=[center+u*x+v*z+n*.0018 for x,z in [(-.036,-.0115),(.036,-.0115),(.036,.0115),(-.036,.0115),(-.036,-.0115)]]
tube('Receptionist_BadgeBorder',[border],metal,jacket,.0007,6)
field=mesh('Receptionist_BadgeEnamel',[tuple(center+u*x+v*z+n*.0019) for x,z in [(-.0345,-.010),(.0345,-.010),(.0345,.010),(-.0345,.010)]],[(0,1,2,3)],trim,constant=badge_skin)
def badge_text(name,text,size,z):
 curve=bpy.data.curves.new(name,'FONT');curve.body=text;curve.align_x='CENTER';curve.size=size;curve.extrude=.00012;curve.resolution_u=3
 o=bpy.data.objects.new(name,curve);s.collection.objects.link(o)
 basis=Matrix(((u.x,v.x,n.x),(u.y,v.y,n.y),(u.z,v.z,n.z))).to_4x4()
 basis.translation=center+v*z+n*.00215;o.matrix_world=basis
 active(o);bpy.ops.object.convert(target='MESH')
 world=o.matrix_world.copy()
 for vertex in o.data.vertices:vertex.co=world@vertex.co
 o.matrix_world=Matrix.Identity(4);o.data.materials.append(shirt)
 bind(o,[badge_skin for _ in o.data.vertices]);created.append(o)
badge_text('Receptionist_BadgeLettering','RECEPTION',.0076,.0005)
badge_text('Receptionist_BadgeSubline','M  /  STAFF',.0038,-.0072)
# Directional twill maps, with normal and roughness derived from one height field.
def write_map(name,pixels,data=False):
 h,w=pixels.shape[:2];im=bpy.data.images.get(name) or bpy.data.images.new(name,width=w,height=h,alpha=False)
 if tuple(im.size)!=(w,h):im.scale(w,h)
 if data:im.colorspace_settings.name='Non-Color'
 a=np.ones((h,w,4),np.float32);a[:,:,:3]=pixels
 im.pixels.foreach_set(a.ravel());im.filepath_raw=str(ROOT/'Textures'/(name+'.png'));im.file_format='PNG';im.save()
 return im
size=1024;y,x=np.mgrid[:size,:size];rng=np.random.default_rng(2038)
warp=np.sin(x*math.pi/2.4);weft=np.sin(y*math.pi/2.4)
mask=((np.floor(x/4)+np.floor(y/4))%4<2).astype(float)
height=.26*(warp*mask+weft*(1-mask))+.10*np.sin((x-y)*math.pi/8)
dy,dx=np.gradient(height);normals=np.stack([-dx*.12,-dy*.12,np.ones_like(height)],-1);normals/=np.linalg.norm(normals,axis=-1)[...,None]
for name,color,rough,metallic in [('Receptionist_Suit',(.064,.079,.101),.77,0),('Receptionist_Shirt',(.67,.66,.605),.83,0),('Receptionist_Trim',(.035,.045,.058),.81,0),('Receptionist_Badge',(.32,.285,.21),.43,.75)]:
 relief=height if name!='Receptionist_Badge' else height*.06
 noise=rng.normal(0,.0035,(size,size))
 base=np.clip(np.array(color)[None,None,:]*(1+(relief*.055+noise)[:,:,None]),0,1)
 orm=np.empty_like(base);orm[:,:,0]=1;orm[:,:,1]=np.clip(rough-relief*.023,0,1);orm[:,:,2]=metallic
 images={'color':write_map(name+'_BaseColor',base),'normal':write_map(name+'_Normal',normals*.5+.5,True),'orm':write_map(name+'_ORM',orm,True)}
 mat=bpy.data.materials[name]
 for node in mat.node_tree.nodes:
  if node.type!='TEX_IMAGE' or not node.image:continue
  role='normal' if '_Normal' in node.image.name else 'orm' if '_ORM' in node.image.name else 'color'
  node.image=images[role]
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V03.blend'))
parts=[o for o in s.objects if o.type=='MESH' and o!=body]
report={'version':'V03','stage':'authored','body_triangles':sum(len(f.vertices)-2 for f in body.data.polygons),'parts':[{'name':o.name,'triangles':sum(len(f.vertices)-2 for f in o.data.polygons)} for o in parts],'new_details':[o.name for o in created],'materials':6,'runtime_tested':False,'motion_authoring':'motion_authoring.json','appearance':['Notched rolled lapels with topstitch','Straight sewn hem and jacket/side/back/cuff seams','Rounded rimmed buttons and buttonholes','Double-welt pockets','Enamel/brass RECEPTION nameplate','Twill color, roughness and normal from a shared height field']}
(ROOT/'authoring_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('V03_DETAILS_AUTHORED '+json.dumps({'parts':len(parts),'clothing_triangles':sum(p['triangles'] for p in report['parts'])}),flush=True)
