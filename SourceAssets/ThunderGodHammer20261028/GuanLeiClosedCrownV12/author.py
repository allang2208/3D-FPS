"""V12: a single swept solid joins both flowing shoulders over the crown."""
import bpy,bmesh,math,json
import numpy as np
from pathlib import Path
from mathutils import Vector
P=Path(__file__).resolve().parent;OLD=P.parent/'GuanLeiPrecisionV11'
for d in ('Export','Previews'):(P/d).mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(OLD/'GuanLei_V11_Editable.blend'));bpy.context.preferences.filepaths.save_version=0
old=json.loads((OLD/'model_manifest.json').read_text(encoding='utf-8'));parts=[]
context=[bpy.data.objects[n] for n in old['context']]
for name in old['objects']:
 o=bpy.data.objects.get(name)
 if not o:continue
 if name.startswith(('02_','03_','04_','05_','06_','07_')):bpy.data.objects.remove(o,do_unlink=True)
 else:parts.append(o)
oldexport=bpy.data.objects.get(old['mesh'])
if oldexport:bpy.data.objects.remove(oldexport,do_unlink=True)
CX=-.0004452141
def material(name):
 m=bpy.data.materials.new('M_GuanLei12_'+name);m.use_nodes=True;ns=m.node_tree.nodes;ls=m.node_tree.links;bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
 for kind in ('BaseColor','ORM','Normal'):
  tex=ns.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(P/'Textures'/('T_GuanLei12_'+name+'_'+kind+'.png')));tex.image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
  if kind=='BaseColor':ls.new(tex.outputs['Color'],bs.inputs['Base Color'])
  elif kind=='ORM':
   sep=ns.new('ShaderNodeSeparateColor');ls.new(tex.outputs['Color'],sep.inputs[0]);ls.new(sep.outputs['Green'],bs.inputs['Roughness']);ls.new(sep.outputs['Blue'],bs.inputs['Metallic'])
  else:
   normal=ns.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.8;ls.new(tex.outputs['Color'],normal.inputs['Color']);ls.new(normal.outputs[0],bs.inputs['Normal'])
 return m
mats={n:material(n) for n in ('Steel','Silver','Recess','Inlay')};steel=mats['Steel'];silver=mats['Silver'];inlay=mats['Inlay'];recess=mats['Recess'];blue=bpy.data.materials['M_GuanLei11_ThunderInlay']
for o in parts:
 for i,m in enumerate(o.data.materials):
  if m and m.name.startswith('M_GuanLei11_') and m.name.removeprefix('M_GuanLei11_') in mats:o.data.materials[i]=mats[m.name.removeprefix('M_GuanLei11_')]
def activate(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def mesh(name,vs,fs,mat,uvs=None):
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(o);me.materials.append(mat)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 for p in me.polygons:p.use_smooth=True
 uv=me.uv_layers.new(name='UVMap')
 for p in me.polygons:
  for li in p.loop_indices:
   vi=me.loops[li].vertex_index;co=me.vertices[vi].co;uv.data[li].uv=uvs[vi] if uvs else (co.x/.055,co.z/.055)
 parts.append(o);return o
def bevel(o,w=.00012):
 activate(o);mod=o.modifiers.new('Soft chisel edges','BEVEL');mod.width=w;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=.4;bpy.ops.object.modifier_apply(modifier=mod.name)
 mod=o.modifiers.new('Stable metal face normals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=40;bpy.ops.object.modifier_apply(modifier=mod.name)
def ribbon(name,pts,width,depth,mat,closed=False):
 vs=[];N=len(pts)
 for i,p in enumerate(pts):
  p=np.asarray(p);t=np.asarray(pts[(i+1)%N])-np.asarray(pts[i-1]) if closed else np.asarray(pts[min(N-1,i+1)])-np.asarray(pts[max(0,i-1)])
  n=np.cross((0,1,0),t);n/=max(np.linalg.norm(n),1e-9)
  for a,d in [(-1,0),(1,0),(1,depth),(-1,depth)]:vs.append(tuple(p+n*a*width*.5+(0,d,0)))
 fs=[]
 for i in range(N if closed else N-1):
  j=(i+1)%N
  for k in range(4):fs.append((i*4+k,j*4+k,j*4+(k+1)%4,i*4+(k+1)%4))
 if not closed:fs.extend([(3,2,1,0),tuple((N-1)*4+k for k in range(4))])
 o=mesh(name,vs,fs,mat);bevel(o,min(.00012,width*.12));return o
def interpolate(points,samples=640):
 ps=np.asarray(points,float);out=[]
 for i in range(len(ps)-1):
  a=ps[i];b=ps[i+1];m0=(b-ps[max(0,i-1)])*.5;m1=(ps[min(len(ps)-1,i+2)]-a)*.5
  for t in np.linspace(0,1,max(4,samples//(len(ps)-1)),endpoint=False):out.append((2*t**3-3*t*t+1)*a+(t**3-2*t*t+t)*m0+(-2*t**3+3*t*t)*b+(t**3-t*t)*m1)
 out.append(ps[-1]);return np.asarray(out)
left=[[.034,.864,.020],[.045,.882,.023],[.053,.900,.020],[.053,.919,.019],[.046,.939,.017],[.044,.953,.022],[.047,.967,.025],[.030,.980,.024],[.012,.984,.022]]
knots=[[-x,z,w] for x,z,w in left]+[[0,.9848,.022]]+list(reversed(left))
path=interpolate(knots);NU=len(path);NV=101
arc=np.concatenate(([0.],np.cumsum(np.linalg.norm(np.diff(path[:,:2],axis=0),axis=1))))
def sample(u,v):
 index=np.clip(u,0,1)*(NU-1);i=min(int(index),NU-2);t=index-i;p=path[i]*(1-t)+path[i+1]*t
 tangent=path[min(i+1,NU-1),:2]-path[max(0,i-1),:2];tangent/=np.linalg.norm(tangent);normal=np.array([-tangent[1],tangent[0]])
 xz=p[:2]+normal*v*p[2]*.5
 full=.045+.0035*math.sin(math.pi*u);y=full+.0028*(1-v**8)
 return xz,y,p,tangent
def lane(u):return .52*math.sqrt(max(0,1-((u-.5)/.485)**16)) if .015<u<.985 else 0
verts=[];uvs=[];indices=[]
for face in (-1,1):
 for i in range(NU):
  u=i/(NU-1)
  for v in np.linspace(-1,1,NV):
   xz,y,p,tan=sample(u,v);d=abs(abs(v)-lane(u));cut=max(0,1-d/.115)*.00065 if .015<u<.985 else 0
   verts.append((CX+xz[0],face*(y-cut),xz[1]));uvs.append((v*p[2]/(.055*2),arc[i]/.055));indices.append(1 if .82<abs(v)<.90 else 0)
fs=[];mi=[];plane=NU*NV
for side in range(2):
 off=side*plane
 for i in range(NU-1):
  for j in range(NV-1):
   k=off+i*NV+j;fs.append((k,k+1,k+1+NV,k+NV));mi.append(indices[k])
# Connect front to back along both width edges. The top bridge and both shoulders
# share vertices in ONE closed volume, with no hidden butt joint or added cover.
for i in range(NU-1):
 for j in (0,NV-1):
  a=i*NV+j;b=(i+1)*NV+j;fs.append((a,b,b+plane,a+plane));mi.append(0)
for i in (0,NU-1):
 for j in range(NV-1):
  a=i*NV+j;fs.append((a,a+plane,a+plane+1,a+1));mi.append(0)
frame=mesh('02_ClosedCrownAndShoulders',verts,fs,steel,uvs);frame.data.materials.append(silver)
for p,m in zip(frame.data.polygons,mi):p.material_index=m
# The return walls have a separate two-dimensional UV strip. Reusing the
# face UVs here collapses both depth edges to a line and stretches the normal.
face_count=2*(NU-1)*(NV-1)
uv=frame.data.uv_layers.active
for p in frame.data.polygons[face_count:]:
 for li in p.loop_indices:
  vi=frame.data.loops[li].vertex_index;co=frame.data.vertices[vi].co
  i=(vi%plane)//NV
  uv.data[li].uv=(co.y/.055,arc[i]/.055) if p.index<face_count+2*(NU-1) else (co.x/.055,co.y/.055)
bevel(frame,.00024)
print('ONE_PIECE_CROWN_BUILT',len(verts),flush=True)
for face in (-1,1):
 loop=[]
 for direction in (1,-1):
  us=np.linspace(.0151,.9849,500)
  if direction<0:us=us[::-1]
  for u in us:
   v=direction*lane(u);xz,y,_,_=sample(u,v);loop.append((CX+xz[0],face*(y-.00015),xz[1]))
 ribbon('03_ContinuousReturnSilver',loop,.00115,-face*.0007,inlay,True)
 ribbon('03_ContinuousReturnBlue',[(x,y+face*.00004,z) for x,y,z in loop],.00032,-face*.00045,blue,True)
 # Continuous three-strand interlace crosses the crown, within the middle land.
 for phase in (0,math.tau/3,math.tau*2/3):
  pts=[]
  for u in np.linspace(.27,.73,310):
   phase_u=(u-.27)/.46*math.tau*5+phase;v=.24*math.asin(.985*math.sin(phase_u))/math.asin(.985)
   xz,y,_,_=sample(u,v);fade=min(1,(u-.27)/.025,(.73-u)/.025);h=.00014+.00012*math.cos(phase_u*2)-.0009*(1-max(0,fade))
   pts.append((CX+xz[0],face*(y+h),xz[1]))
  ribbon('04_CrownContinuousKnotInlay',pts,.0008,-face*.00065,inlay)
# Shallow woven crown inlay also follows the true upper surface, so the
# newly closed top has crafted detail when seen from above.
upper=np.array([sample(u,1)[0] for u in np.linspace(.36,.64,700)])
def crown_z(x):return float(np.interp(x,upper[:,0],upper[:,1]))
def top_ribbon(name,pts,width,depth,mat,closed=False):
 vs=[];N=len(pts)
 for i,p in enumerate(pts):
  p=np.asarray(p);t=np.asarray(pts[(i+1)%N])-np.asarray(pts[i-1]) if closed else np.asarray(pts[min(N-1,i+1)])-np.asarray(pts[max(0,i-1)])
  n=np.cross((0,0,1),t);n/=max(np.linalg.norm(n),1e-9)
  for a,d in [(-1,0),(1,0),(1,-depth),(-1,-depth)]:
   q=p+n*a*width*.5; q[2]=crown_z(q[0]-CX)+(p[2]-crown_z(p[0]-CX))+d;vs.append(tuple(q))
 fs=[]
 for i in range(N if closed else N-1):
  j=(i+1)%N
  for k in range(4):fs.append((i*4+k,j*4+k,j*4+(k+1)%4,i*4+(k+1)%4))
 if not closed:fs.extend([(3,2,1,0),tuple((N-1)*4+k for k in range(4))])
 o=mesh(name,vs,fs,mat,[(x/.055,y/.055) for x,y,z in vs]);bevel(o,.00009);return o
for side in (-1,1):
 pts=[]
 for a in np.linspace(0,math.tau,400,endpoint=False):
  x=.044*math.cos(a);y=side*.025+.010*math.sin(a)
  pts.append((CX+x,y,crown_z(x)+.00013))
 top_ribbon('05_CrownSeatedBorder',pts,.0007,.0007,inlay,True)
 for phase in (0,math.tau/3,2*math.tau/3):
  pts=[]
  for t in np.linspace(0,1,400):
   x=(t-.5)*.080;envelope=math.sin(math.pi*t)**.5
   y=side*.025+.006*math.sin(t*math.tau*4+phase)*envelope
   h=.00017+.00009*math.cos(t*math.tau*8+phase*2)-.0009*(1-min(1,t/.06,(1-t)/.06))
   pts.append((CX+x,y,crown_z(x)+h))
  top_ribbon('06_CrownSeatedKnot',pts,.00065,.00065,inlay)
# The remaining old lower apron keeps its physical carving, with new PBR maps.
for o in parts:o.hide_render=False;o.hide_set(False)
for o in context:o.hide_render=True;o.hide_set(True)
export=[]
for o in parts:
 c=o.copy();c.data=o.data.copy();bpy.context.scene.collection.objects.link(c);export.append(c)
bpy.ops.object.select_all(action='DESELECT')
for o in export:o.select_set(True)
bpy.context.view_layer.objects.active=export[0];bpy.ops.object.join();joined=bpy.context.object;joined.name='SM_ThunderGodHammer_head_mount_guan_lei_seat_V12';joined.data.calc_loop_triangles()
bpy.ops.export_scene.fbx(filepath=str(P/'Export'/(joined.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=False,path_mode='STRIP')
bpy.ops.export_scene.gltf(filepath=str(P/'Export'/'GuanLei_V12.glb'),export_format='GLB',use_selection=True,export_apply=True)
joined.hide_render=True;joined.hide_set(True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'GuanLei_V12_Editable.blend'))
manifest=dict(revision='GuanLeiClosedCrownV12',source=str(OLD/'GuanLei_V11_Editable.blend'),mesh=joined.name,triangles=len(joined.data.loop_triangles),objects=[o.name for o in parts],context=[o.name for o in context],closure='Left and right flowing structures joined across the top as one closed swept volume; front and back share edge vertices',normal_maps='four dedicated 4096px tangent-space maps, each connected to its material Normal input',published_to_game=False,user_accepted=False)
(P/'model_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');print('GUANLEI_V12_SAVED',manifest['triangles'],flush=True)
