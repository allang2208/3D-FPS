"""Retain each installed receiver interface and fit the approved stock body.

No host weapon is edited. Geometry is exported in the WPN_root physical frame;
the runtime cancels the native root scale once. No previews or tests are run.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector,Quaternion
P=Path(__file__).resolve().parents[3];O=P/'SourceAssets/LegendaryStock20261006';I=O/'Integration'
for d in ('Editable','Exports'):(I/d).mkdir(parents=True,exist_ok=True)
sources=json.loads((I/'fitting-sources.json').read_text())
F=Vector((0,-1,0));U=Vector((0,0,1));L=Vector((1,0,0))
B=Matrix(((0,1,0),(-1,0,0),(0,0,1))).to_4x4()
flip=Matrix.Diagonal((1,-1,1))
report={'models':{},'frame':'WPN_root physical metres, FBX centimetres; root scale cancelled once',
        'reference':'Model/TacticalStock_Editable.blend','game_tested':False}
report['visual_revision']=json.loads((O/'authoring.json').read_text(encoding='utf-8')).get('visual_revision','V1')

def select(ob):
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob

def bone_frame(spec):
 q=Quaternion((spec[6],spec[3],spec[4],spec[5]));r=flip@q.to_matrix()@flip
 m=r.to_4x4();m.translation=Vector((spec[0],-spec[1],spec[2]))/100
 return m

def root_transform(family,spec):
 if family in ('M4','AKM'):
  m=Matrix.Rotation(math.pi/2,4,'Z')
  m.translation=Vector((.0008,.083,.035) if family=='AKM' else (0,.0385,.0725))
  return m
 if family=='HK416':return bone_frame(spec['bones']['WPN_root']).inverted()
 return Matrix.Identity(4)

def hull(points):
 pts=sorted(set((round(p[0],7),round(p[1],7)) for p in points))
 def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
 low=[];high=[]
 for p in pts:
  while len(low)>1 and cross(low[-2],low[-1],p)<=0:low.pop()
  low.append(p)
 for p in reversed(pts):
  while len(high)>1 and cross(high[-2],high[-1],p)<=0:high.pop()
  high.append(p)
 return [Vector(p) for p in low[:-1]+high[:-1]]

def radial(poly,center,angle):
 ray=Vector((math.cos(angle),math.sin(angle)))
 def cross(a,b):return a.x*b.y-a.y*b.x
 ts=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  edge=b-a;den=cross(ray,edge)
  if abs(den)<1e-10:continue
  t=cross(a-center,edge)/den;v=cross(a-center,ray)/den
  if t>=0 and -.00001<=v<=1.00001:ts.append(t)
 return center+ray*min(ts)

def mesh(name,verts,faces,material):
 data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
 ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob);data.materials.append(material)
 bm=bmesh.new();bm.from_mesh(data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free()
 return ob

def surface(ob):
 select(ob)
 tri=ob.modifiers.new('Interface triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
 data=ob.data
 for layer in list(data.uv_layers):data.uv_layers.remove(layer)
 uv=data.uv_layers.new(name='SurfaceUV')
 for face in data.polygons:
  axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(face.normal[i]))]
  for li in face.loop_indices:
   v=data.vertices[data.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]]/.035,v[axes[1]]/.035)

for family,spec in sources.items():
 bpy.ops.wm.open_mainfile(filepath=str(O/'Model/TacticalStock_Editable.blend'))
 bpy.context.preferences.filepaths.save_version=0
 originals=[ob for ob in bpy.context.scene.objects if ob.type=='MESH']
 before=set(bpy.data.objects)
 bpy.ops.import_scene.fbx(filepath=spec['fbx'],use_anim=False)
 imported=[ob for ob in bpy.data.objects if ob not in before and ob.type=='MESH']
 transform=root_transform(family,spec)
 for ob in imported:
  ob.data.transform(transform@ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4);ob.modifiers.clear()
 points=[v.co.copy() for ob in imported for v in ob.data.vertices]
 front=max(p.dot(F) for p in points)
 # A short source segment retains the receiver-specific face and fasteners.
 depth={'M4':.018,'AKM':.020,'QBZ191':.015,'M16':.019,'A762':.018,
        'SVD':.020,'PKM':.020,'LMG201':.018,'HK416':.019}[family]
 cut=front-depth;crossings=[]
 for ob in imported:
  for edge in ob.data.edges:
   a,b=[ob.data.vertices[n].co for n in edge.vertices];sa=a.dot(F)-cut;sb=b.dot(F)-cut
   if sa*sb<=0 and abs(sa-sb)>1e-9:
    p=a.lerp(b,sa/(sa-sb));crossings.append((p.dot(L),p.dot(U)))
 outline=hull(crossings)
 if len(outline)<3:raise RuntimeError('No source interface cross section: '+family)
 center=Vector(((min(p.x for p in outline)+max(p.x for p in outline))/2,
                (min(p.y for p in outline)+max(p.y for p in outline))/2))
 # Match the front shape, then transition over a short solid neck to the
 # already-authored closed mount. Only the connecting surfaces are rebuilt.
 transition=.010
 pivot=F*(cut-transition)+L*center.x+U*(center.y+.003)
 frame=B.copy();frame.translation=pivot
 for ob in originals:
  ob.data.transform(frame@ob.matrix_world);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
 retained=[]
 for ob in imported:
  bm=bmesh.new();bm.from_mesh(ob.data)
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,
    plane_co=F*cut,plane_no=F,clear_inner=True,clear_outer=False)
  border=[edge for edge in bm.edges if edge.is_boundary and all(abs(v.co.dot(F)-cut)<2e-6 for v in edge.verts)]
  if border:bmesh.ops.holes_fill(bm,edges=border,sides=0)
  bm.to_mesh(ob.data);bm.free()
  if not ob.data.polygons:bpy.data.objects.remove(ob,do_unlink=True);continue
  ob.name=family+'_RetainedReceiverInterface';ob.data.materials.clear();ob.data.materials.append(bpy.data.materials['Stock_Graphite'])
  for poly in ob.data.polygons:poly.material_index=0
  surface(ob);retained.append(ob)
 source=[];target=[];n=64
 rectangle=[Vector((-.0125,-.012)),Vector((.0125,-.012)),Vector((.0125,.012)),Vector((-.0125,.012))]
 for j in range(n):
  angle=math.tau*j/n;p=radial(outline,center,angle);q=radial(rectangle,Vector((0,0)),angle)
  source.append(tuple(F*(cut+.0002)+L*p.x+U*p.y))
  target.append(tuple(pivot-F*.001+L*q.x+U*(q.y-.003)))
 faces=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]
 faces.extend((j,(j+1)%n,(j+1)%n+n,j+n) for j in range(n))
 neck=mesh(family+'_ContinuousTransition',source+target,faces,bpy.data.materials['Stock_Graphite'])
 surface(neck)
 selected=originals+retained+[neck]
 for ob in list(bpy.context.scene.objects):
  if ob.type!='MESH':bpy.data.objects.remove(ob,do_unlink=True)
 # Each native fitting keeps the same body scale; only the adapter differs.
 bpy.context.scene['WeaponFamily']=family
 bpy.context.scene['HostSource']=spec['host']
 bpy.context.scene['AssemblyFrame']='WPN_root, physical metres, native bone scale cancelled once'
 bpy.ops.wm.save_as_mainfile(filepath=str(I/'Editable'/(family+'_TacticalStock.blend')))
 select(selected[0])
 for ob in selected:ob.select_set(True)
 bpy.ops.object.join();ob=bpy.context.object;ob.name='SM_TacticalStock_'+family
 bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
 file=I/'Exports'/(ob.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
                         bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 ob.data.calc_loop_triangles()
 report['models'][family]={'name':ob.name,'fbx':str(file),'triangles':len(ob.data.loop_triangles),
   'host':spec['host'],'source_interface':spec['source'],'source_front':front,'interface_cut':cut,
   'retained_depth':depth,'stock_mount_blender_m':list(pivot),'body_scale':1.0,
   'root_rest_scale':spec['bones']['WPN_root'][7:10],
   'materials':[m.name for m in ob.data.materials],
   'asset':'/Game/Weapons/LegendaryStock20261006/Fitted/'+ob.name}
 (I/'fitted-models.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
 print('TACTICAL_STOCK_FITTED '+family+' '+json.dumps({'mount':list(pivot),'source_front':front,'triangles':len(ob.data.loop_triangles)}),flush=True)
