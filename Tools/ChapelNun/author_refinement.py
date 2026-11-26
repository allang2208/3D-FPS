"""Preserve the Meshy face; author its interfaces and native-donor black bun."""
import bpy, json, math, random, bisect, sys
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
P=Path('D:/FPS3D/FPSGAME');N=P/'SourceAssets/ChapelNun20261115';R=N/'RefinementR4';O=R/'Authored'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
head=read(N/'OriginalMeshyFaceR3/Authored/head.json');robe=read(N/'ProductionR1/Inputs/native_robe.json');body=read(N/'ProductionR1/Inputs/native_body.json')
bpy.ops.wm.read_factory_settings(use_empty=True)
source_faces=[t[::-1] for t,m in zip(head['triangles'],head['triangle_materials']) if m==0]
source_uv=[u[::-1] for u,m in zip(head['uv'],head['triangle_materials']) if m==0]
bvh=BVHTree.FromPolygons([Vector(p) for p in head['positions']],source_faces,all_triangles=True)
full_surface=BVHTree.FromPolygons([Vector(p) for p in head['positions']],[t[::-1] for t,m in zip(head['triangles'],head['triangle_materials']) if m!=2],all_triangles=True)
# Retain the original uncut Meshy neck texture field below the old 145 cm seam.
bpy.ops.import_scene.gltf(filepath=str(N/'MeshyHeadR1/Source/NunHead_R1_glb.glb'))
raw_ob=next(o for o in bpy.data.objects if o.type=='MESH');bpy.context.view_layer.objects.active=raw_ob
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);raw_me=raw_ob.data;raw_me.calc_loop_triangles()
ring_ids={i for t,m in zip(head['triangles'],head['triangle_materials']) if m==1 for i in t if abs(head['positions'][i][2]-144.5)<.002}
ring=sorted([Vector(head['positions'][i]) for i in ring_ids],key=lambda p:math.atan2(p.y-1,p.x));angles=[math.atan2(p.y-1,p.x) for p in ring]
raw_positions=[]
for v in raw_me.vertices:
 p=Vector((v.co.x*15.8,-v.co.y*15.8+1.4,v.co.z*15.8+168.0523223876953-.94961101*15.8))
 if p.z<149:
  theta=math.atan2(p.y-1,p.x);k=bisect.bisect_left(angles,theta);a=ring[(k-1)%len(ring)];b=ring[k%len(ring)];ta=angles[(k-1)%len(ring)];tb=angles[k%len(ring)]
  if tb<ta:tb+=math.tau
  if theta<ta:theta+=math.tau
  q=a.lerp(b,(theta-ta)/max(1e-6,tb-ta));t=max(0,min(1,(149-p.z)/4));t=t*t*(3-2*t);p.x=p.x*(1-t)+q.x*t;p.y=p.y*(1-t)+q.y*t
 raw_positions.append(p)
raw_faces=[list(t.vertices)[::-1] for t in raw_me.loop_triangles]
raw_uv=[[[raw_me.uv_layers.active.data[li].uv.x,1-raw_me.uv_layers.active.data[li].uv.y] for li in list(t.loops)[::-1]] for t in raw_me.loop_triangles]
raw_bvh=BVHTree.FromPolygons(raw_positions,raw_faces,all_triangles=True);bpy.data.objects.remove(raw_ob,do_unlink=True)
center=Vector((0,.1,158.9))
def scalp(d,lift=0):
 d=Vector(d).normalized();p,n,i,dist=bvh.ray_cast(center,d,30)
 if p is None:raise RuntimeError('No head surface '+str(d))
 return p+d*lift
def bary(p,a,b,c):
 v0=b-a;v1=c-a;v2=p-a;d00=v0.dot(v0);d01=v0.dot(v1);d11=v1.dot(v1);d20=v2.dot(v0);d21=v2.dot(v1);den=d00*d11-d01*d01
 if abs(den)<1e-14:return (1,0,0)
 v=(d11*d20-d01*d21)/den;w=(d00*d21-d01*d20)/den;return (1-v-w,v,w)
def sample_uv(theta,z):
 direction=Vector((math.sin(theta),math.cos(theta),0));p,n,i,dist=raw_bvh.ray_cast(Vector((0,1,max(139.2,z))),direction,30)
 if p is None:raise RuntimeError('No original neck texel')
 weights=bary(p,*[raw_positions[v] for v in raw_faces[i]])
 return sum((Vector(uv)*w for uv,w in zip(raw_uv[i],weights)),Vector((0,0)))
texture_dir=O/'Textures';texture_dir.mkdir(exist_ok=True)
for channel in ('base_color','metallic_roughness'):
 src=bpy.data.images.load(str(N/'OriginalMeshyFaceR3/Source'/('MeshyOriginal_'+channel+'.jpg')))
 if channel!='base_color':src.colorspace_settings.name='Non-Color'
 w,h=src.size;pixels=np.array(src.pixels[:],dtype=np.float32).reshape(h,w,4)
 out=np.empty((256,1024,4),dtype=np.float32)
 for y in range(256):
  z=129+16.25*y/255
  for x in range(1024):
   uv=sample_uv(-math.pi+math.tau*x/1023,z);xx=float(uv.x)*(w-1);yy=(1-float(uv.y))*(h-1)
   xi=max(0,min(w-2,int(xx)));yi=max(0,min(h-2,int(yy)));fx=xx-xi;fy=yy-yi
   out[y,x]=pixels[yi,xi]*(1-fx)*(1-fy)+pixels[yi,xi+1]*fx*(1-fy)+pixels[yi+1,xi]*(1-fx)*fy+pixels[yi+1,xi+1]*fx*fy
 im=bpy.data.images.new('Neck_'+channel,width=1024,height=256,alpha=False,float_buffer=False)
 im.colorspace_settings.name='sRGB' if channel=='base_color' else 'Non-Color';im.pixels.foreach_set(out.ravel());im.filepath_raw=str(texture_dir/('Neck_'+channel+'.png'));im.file_format='PNG';im.save()

# Original visible facial coordinates, UVs and normals are copied verbatim.
# Only micro-lash/lip triangles receive a separate shadow policy, with identical shader inputs.
new={k:head[k] for k in ('binding_source','skeleton','bones','positions','weights')}
new.update(triangles=[],uv=[],normals=[],triangle_materials=[],material_slots=['MeshyOriginal','MatchedNeck','FineSurface'])
fine_count=0
for t,uv,n,m in zip(head['triangles'],head['uv'],head['normals'],head['triangle_materials']):
 if m==2:continue
 c=sum((Vector(head['positions'][i]) for i in t),Vector())/3
 if m==0:
  eye=((abs(c.x)-3.05)/1.7)**2+((c.z-157.43)/.78)**2<1 and c.y>6.1
  lip=(c.x/2.7)**2+((c.z-150.72)/.9)**2<1 and c.y>7.8
  if eye or lip:m=2;fine_count+=1
 else:
  uv=[]
  for i in t:
   x,y,z=head['positions'][i];uv.append([(math.atan2(x,y-1)+math.pi)/math.tau,1-(z-129)/16.25])
  if max(v[0] for v in uv)-min(v[0] for v in uv)>.5:
   uv=[[u+1 if u<.5 else u,v] for u,v in uv]
 new['triangles'].append(t);new['uv'].append(uv);new['normals'].append(n);new['triangle_materials'].append(m)
(O/'head.json').write_text(json.dumps(new,separators=(',',':')),encoding='utf-8')

def mesh_from_json(name,d):
 me=bpy.data.meshes.new(name);me.from_pydata(d['positions'],[],[t[::-1] for t in d['triangles']]);me.update();me.uv_layers.new(name='UVMap')
 for f,uv in zip(me.polygons,d['uv']):
  f.use_smooth=True
  for li,xy in zip(f.loop_indices,uv[::-1]):me.uv_layers.active.data[li].uv=(xy[0],1-xy[1])
 me.normals_split_custom_set([n for ns in d['normals'] for n in ns[::-1]])
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
 for bone in d['bones']:ob.vertex_groups.new(name=bone['name'])
 for i,ws in enumerate(d['weights']):
  for bi,w in ws:ob.vertex_groups[int(bi)].add([i],w,'REPLACE')
 return ob
import runpy
runpy.run_path(str(P/'Tools/ChapelNun/repair_neck_source.py'))
head_ob=mesh_from_json('SK_NunHead',read(O/'head.json'))

# Rebuild the linen collar over the outermost robe envelope, including its neckline return.
robe_tri=[t[::-1] for t,m in zip(robe['triangles'],robe['triangle_materials']) if m not in (3,9,10)]
robe_bvh=BVHTree.FromPolygons([Vector(p) for p in robe['positions']],robe_tri,all_triangles=True)
tree=KDTree(len(robe['positions']))
for i,p in enumerate(robe['positions']):tree.insert(p,i)
tree.balance()
def robe_weights(p):
 a={}
 for _,i,dist in tree.find_n(p,4):
  for b,w in robe['weights'][i]:a[b]=a.get(b,0)+w/max(.04,dist)**2
 pairs=sorted(a.items(),key=lambda q:-q[1])[:8];total=sum(w for b,w in pairs);return [[b,w/total] for b,w in pairs]
ps=[];fs=[];uvs=[];A=192;B=20
for j in range(B+1):
 v=j/B
 for i in range(A):
  angle=math.tau*i/A;z=143.65-v*(5.05+1.5*max(0,math.cos(angle)));direction=Vector((math.sin(angle),math.cos(angle),0));origin=Vector((0,1.3,z))
  candidates=[]
  for surface in (robe_bvh,full_surface):
   hit,n,idx,dist=surface.ray_cast(origin+direction*25,-direction,25)
   if hit is not None:candidates.append(hit)
  if not candidates:raise RuntimeError('Missing collar support surface')
  hit=max(candidates,key=lambda p:(p-origin).dot(direction))
  ps.append(hit+direction*.42)
for j in range(B):
 for i in range(A):
  k=(i+1)%A;fs.append((j*A+i,j*A+k,(j+1)*A+k,(j+1)*A+i));uvs.append([(i/A,j/B),((i+1)/A,j/B),((i+1)/A,(j+1)/B),(i/A,(j+1)/B)])
me=bpy.data.meshes.new('ContinuousLinenCollar');me.from_pydata(ps,[],fs);me.update();me.uv_layers.new(name='UVMap')
for f,uv in zip(me.polygons,uvs):
 f.use_smooth=True
 for li,xy in zip(f.loop_indices,uv):me.uv_layers.active.data[li].uv=xy
ob=bpy.data.objects.new('Nun_Collar',me);bpy.context.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob;ob.select_set(True)
solid=ob.modifiers.new('ContinuousFoldedThickness','SOLIDIFY');solid.thickness=.16;solid.offset=-1;solid.use_even_offset=True;bpy.ops.object.modifier_apply(modifier=solid.name)
me=ob.data;me.calc_loop_triangles()
trim=read(R/'Inputs/current_trim.json');out={k:trim[k] for k in ('bones','skeleton')};out['binding_source']=robe['source'];out['material_slots']=['IvoryLinen','BlackCord','WornIron'];out.update(positions=[list(v.co) for v in me.vertices],weights=[robe_weights(v.co) for v in me.vertices],triangles=[],uv=[],normals=[],triangle_materials=[])
for t in me.loop_triangles:
 order=list(t.loops)[::-1];out['triangles'].append(list(t.vertices)[::-1]);out['uv'].append([[me.uv_layers.active.data[i].uv.x,1-me.uv_layers.active.data[i].uv.y] for i in order]);out['normals'].append([list(me.corner_normals[i].vector) for i in order]);out['triangle_materials'].append(0)
base=len(out['positions']);out['positions']+=trim['positions'];out['weights']+=trim['weights']
for t,uv,n,m in zip(trim['triangles'],trim['uv'],trim['normals'],trim['triangle_materials']):
 if m==0:continue
 out['triangles'].append([i+base for i in t]);out['uv'].append(uv);out['normals'].append(n);out['triangle_materials'].append(m)
(O/'trim.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8');bpy.data.objects.remove(ob,do_unlink=True);mesh_from_json('SK_Nun_CollarCross',out)

# Continuous, opaque hosiery covers the native legs under the real leather boots.
boots=read(R/'Inputs/current_boots.json');boots['binding_source']=boots.pop('source');boots['material_slots']=[m['slot'] for m in boots['materials']]+['NunBlackStockings']
base=len(boots['positions']);bone_map={b['name']:i for i,b in enumerate(boots['bones'])};sock_ids={}
for t,uv,n,m in zip(body['triangles'],body['uv'],body['normals'],body['triangle_materials']):
 p=[Vector(body['positions'][i]) for i in t]
 if max(v.z for v in p)>40 or min(v.z for v in p)<3 or m==6:continue
 tri=[]
 for i,normal in zip(t,n):
  if i not in sock_ids:
   sock_ids[i]=len(boots['positions']);boots['positions'].append(list(Vector(body['positions'][i])+Vector(normal)*.055))
   boots['weights'].append([[bone_map[body['bones'][b]['name']],w] for b,w in body['weights'][i]])
  tri.append(sock_ids[i])
 boots['triangles'].append(tri);boots['uv'].append([[v.x/8,v.z/8] for v in p]);boots['normals'].append(n);boots['triangle_materials'].append(len(boots['materials']))
(O/'boots.json').write_text(json.dumps(boots,separators=(',',':')),encoding='utf-8')
mesh_from_json('SK_Nun_Boots',boots)
import runpy
runpy.run_path(str(P/'Tools/ChapelNun/repair_collar_envelope.py'),init_globals={'KEEP_AUTHOR_SCENE':True})
bpy.data.objects.remove(bpy.data.objects['SK_Nun_CollarCross'],do_unlink=True)
mesh_from_json('SK_Nun_CollarCross',read(O/'trim.json'))
print('R4_SURFACES_AUTHORED',fine_count,len(sock_ids),flush=True)
if '--surfaces-only' in sys.argv:
 bpy.ops.wm.save_as_mainfile(filepath=str(O/'Nun_InterfacesR4.blend'));raise SystemExit(0)

# Retain the real native groom's root distribution and root UVs, then comb into a volumetric bun.
rng=random.Random(1611264);all_curves=[]
for group in read(R/'Inputs/native_hair.json')['groups']:
 prefix=group['prefix'];points=np.fromfile(R/'Inputs'/(prefix+'_points.bin'),'<f4').reshape(-1,3);counts=np.fromfile(R/'Inputs'/(prefix+'_counts.bin'),'<u2');offsets=np.r_[0,np.cumsum(counts[:-1])];rootuv=np.fromfile(R/'Inputs'/(prefix+'_rootuv.bin'),'<f4').reshape(-1,2)
 for i,(offset,count) in enumerate(zip(offsets,counts)):
  all_curves.append((points[int(offset):int(offset)+int(count)],rootuv[i]))
def direction(theta,phi):return Vector((math.sin(phi)*math.sin(theta),math.sin(phi)*math.cos(theta),math.cos(phi)))
def limit(theta):
 a=abs(theta);knots=[(0,.96),(.60,1.01),(1.10,1.22),(1.65,1.48),(2.2,1.84),(math.pi,2.08)]
 for (a0,b0),(a1,b1) in zip(knots,knots[1:]):
  if a<=a1:
   t=(a-a0)/(a1-a0);t=t*t*(3-2*t);return b0+(b1-b0)*t
 return 2.08
def constrained(d,lift):
 d=d.normalized();theta=math.atan2(d.x,d.y);phi=math.acos(max(-1,min(1,d.z)));return scalp(direction(theta,min(phi,limit(theta))),lift)
def create_groom(name,loose=False):
 curves=bpy.data.curves.new(name,'CURVE');curves.dimensions='3D';curves.resolution_u=1;obj=bpy.data.objects.new(name,curves);bpy.context.collection.objects.link(obj);obj['groom_group_id']=0;obj['groom_guide']=0;uvs=[]
 for k,(donor,uv) in enumerate(all_curves):
  if loose and k%40:continue
  d=(Vector(donor[0])-center).normalized();theta=math.atan2(d.x,d.y);phi=math.acos(max(-1,min(1,d.z)))
  # Preserve native irregular edge roots, with a small clearance at the new temples.
  phi=min(phi,limit(theta)-rng.uniform(.002,.025));d=direction(theta,phi);side=1 if d.x>=0 else -1
  phase=float(uv[0])*47+float(uv[1])*91;enddir=direction(side*(math.pi-.05),1.99)
  points=[]
  if loose:
   length=rng.uniform(.8,3.2);root=constrained(d,.025);tangent=(enddir-d*d.dot(enddir)).normalized()
   for j in range(28):
    t=j/27;p=constrained(d.slerp(enddir,min(.20,length/16*t)),.025+.14*math.sin(math.pi*t))
    p+=Vector((side*.12*math.sin(phase+t*5),-.15*t*t,-.2*t*t))*t;points.append(p)
  else:
   root_jitter=rng.uniform(-.025,.025);coil_phase=phase%math.tau;minor_phase=theta*2.3+float(uv[1])*31
   for j in range(80):
    t=j/79
    if t<.66:
     u=t/.66;dd=d.slerp(enddir,u);wave=.035*math.sin(phase+u*18)+.025*math.sin(theta*27+u*9)
     lift=.028+(.40+root_jitter+wave)*math.sin(math.pi*u)+.10*u
     p=constrained(dd,lift)
    else:
     u=(t-.66)/.34;a=coil_phase+u*math.tau*1.35;b=minor_phase+u*3.0;radius=2.1+1.1*math.cos(b)
     coil=Vector((radius*math.sin(a),-9.8-1.55*math.sin(b),153.8+radius*.88*math.cos(a)))
     start=constrained(enddir,.13);blend=min(1,u/.25);blend=blend*blend*(3-2*blend);p=start.lerp(coil,blend)
     surface=scalp(p-center,.04)
     if (p-center).length<(surface-center).length:p=surface
    points.append(p)
  sp=curves.splines.new('POLY');sp.points.add(len(points)-1);sp.points.foreach_set('co',[c for pt in points for c in (*pt,1.)])
  for j,pt in enumerate(sp.points):pt.radius=.0038*(1-.82*(j/(len(points)-1))**3)
  uvs.append(uv)
 np.asarray(uvs,dtype='<f4').tofile(O/(name+'_rootuv.bin'))
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 bpy.ops.wm.alembic_export(filepath=str(O/(name+'.abc')),start=1,end=1,selected=True,as_background_job=False,export_custom_properties=True,curves_as_mesh=False,global_scale=1.)
 print('R4_NATIVE_GROOM_AUTHORED',name,len(uvs),flush=True);return len(uvs)
counts={name:create_groom(name,loose) for name,loose in [('Nun_LowBun_Core_R4',False),('Nun_LowBun_Loose_R4',True)]}
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Nun_RefinementR4.blend'))
(O/'authoring.json').write_text(json.dumps({'original_face_positions_unchanged':True,'original_face_textures_unchanged':True,'micro_surface_shadow_triangles':fine_count,'stocking_vertices':len(sock_ids),'grooms':counts,'native_groom_source':read(R/'Inputs/native_hair.json')['asset'],'scalp_cap_removed':True},indent=2),encoding='utf-8')
print('R4_AUTHORING_COMPLETE',flush=True)
