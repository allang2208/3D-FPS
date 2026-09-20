"""M16-only, source-seated carry-handle adapter, separate optic glass and grip collar."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;S=O.parent;U=S/'M16UniversalAttachments20260920';bpy.context.preferences.filepaths.save_version=0
I=json.loads((O/'blender_inspection.json').read_text());src=json.loads((U/'sources.json').read_text())
bpy.ops.wm.open_mainfile(filepath=str(S/'M16Gameplay20260919/M16_Manny_Editable.blend'),use_scripts=False)
r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['M16_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
root=r.matrix_world@r.pose.bones['WPN_root'].matrix;old=bpy.data.objects['M16A2_PistolGrip'];ev=old.evaluated_get(bpy.context.evaluated_depsgraph_get());data=bpy.data.meshes.new_from_object(ev);data.transform(root.inverted()@old.matrix_world);factory=data.copy()
receiver=I['parts']['M16A2_Receiver'];tree=BVHTree.FromPolygons([Vector(v) for v in receiver['vertices']],receiver['faces'])
# Save standalone factory interface while replacing the scene.
factoryverts=[v.co.copy() for v in factory.vertices];factoryfaces=[list(p.vertices) for p in factory.polygons];factoryuv=[tuple(v.uv) for v in factory.uv_layers[0].data]
sourceuv={}
for key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','balanced_reargrip']:
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=src[key]['fbx']);o=next(o for o in bpy.context.scene.objects if o.type=='MESH');sourceuv[key]=[layer.name for layer in o.data.uv_layers][:3]
bpy.ops.wm.open_mainfile(filepath=str(U/'M16_CommonAttachments_Editable.blend'),use_scripts=False)
metal=bpy.data.materials.get('M16_InterfaceMetal');glass=bpy.data.materials.new('M16_HoloGlass');glass.diffuse_color=(.12,.29,.32,.16)
def activate(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]
def object_mesh(name,verts,faces,mat=metal):
 m=bpy.data.meshes.new(name);m.from_pydata(verts,[],faces);m.materials.append(mat);m.update();o=bpy.data.objects.new(name,m);bpy.context.collection.objects.link(o);return o
def bevel(o,w=.00025):
 activate([o]);b=o.modifiers.new('Machined radii','BEVEL');b.width=w;b.segments=3;bpy.ops.object.modifier_apply(modifier=b.name)
def extrude(name,profile,x0,x1):
 n=len(profile);vs=[(x,y,z) for x in (x0,x1) for y,z in profile];fs=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 o=object_mesh(name,vs,fs);bevel(o,.00015);return o
def cylinder(name,loc,radius,depth,n=48):
 bpy.ops.mesh.primitive_cylinder_add(vertices=n,radius=radius,depth=depth,location=loc);o=bpy.context.object;o.name=name;o.data.materials.append(metal);bevel(o,.00025);o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4);return o
def clip(o,z,upper):
 bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000003)
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,z),plane_no=(0,0,1),clear_inner=upper,clear_outer=not upper,dist=.0000001)
 bm.to_mesh(o.data);bm.free();o.data.update()
def uv(o,preferred=None):
 names=preferred or [layer.name for layer in o.data.uv_layers][:3]
 saved=[[tuple(d.uv) for d in o.data.uv_layers[n].data] for n in names if n in o.data.uv_layers]
 for layer in list(o.data.uv_layers):o.data.uv_layers.remove(layer)
 # Blender joins UV sets by NAME, while UE materials address them by INDEX.
 # Every body and newly made fitting must share this exact four-set schema.
 for i in range(4):
  layer=o.data.uv_layers.new(name='M16_UV'+str(i))
  if i<len(saved):
   for j,p in enumerate(saved[i]):layer.data[j].uv=p
 layer=o.data.uv_layers[3]
 for f in o.data.polygons:
  axis=max(range(3),key=lambda k:abs(f.normal[k]));aa,bb=[k for k in range(3) if k!=axis]
  for j in f.loop_indices:
   p=o.data.vertices[o.data.loops[j].vertex_index].co;layer.data[j].uv=(p[aa]/.04,p[bb]/.04)
def adapter():
 parts=[]
 # Rail top remains the optic's existing zero mounting plane. The adapter
 # below it follows the measured carry-handle trough, including its cross hole.
 parts.append(extrude('Rail spine',[(-.0074,-.0054),(.0074,-.0054),(.0086,-.0034),(-.0086,-.0034)],-.0635,.0635))
 profile=[(-.0086,-.0034),(.0086,-.0034),(.0103,-.0020),(.0103,-.0010),(.0093,0),(-.0093,0),(-.0103,-.0010),(-.0103,-.0020)]
 # Consistent transverse slots; no isolated rectangular raised plates.
 for j in range(13):
  x=-.060+j*.010;parts.append(extrude('Rail tooth',profile,max(-.0635,x-.002385),min(.0635,x+.002385)))
 parts.append(extrude('Sight tunnel roof',[(-.0084,-.0092),(.0084,-.0092),(.0084,-.0054),(-.0084,-.0054)],-.060,.063))
 for side in [-1,1]:
  vs=[];stations=17
  for i in range(stations):
   x=-.060+i*.123/(stations-1);yroot=-.105-x
   # An inset foot seats on the original channel. No replacement receiver.
   for yy,top in [(side*.0059,False),(side*.0083,False),(side*.0083,True),(side*.0059,True)]:
    hit=tree.ray_cast(Vector((yy,yroot,.19)),Vector((0,0,-1)),.045)[0]
    z=(hit.z+.00008 if hit else .1625)-.1815 if not top else -.0088
    vs.append((x,yy,z))
  fs=[(3,2,1,0),(4*(stations-1),4*(stations-1)+1,4*(stations-1)+2,4*(stations-1)+3)]
  for i in range(stations-1):
   for k in range(4):fs.append((4*i+k,4*i+(k+1)%4,4*(i+1)+(k+1)%4,4*(i+1)+k))
  o=object_mesh('Contoured channel foot',vs,fs);bevel(o,.00018);parts.append(o)
 # Actual model's through-hole is at receiver Y=-.110, leaving the sight
 # tunnel open above the bolt. Knurled nut sits under the carry handle.
 parts.append(cylinder('Through stud',(.005,0,-.0235),.0023,.018))
 parts.append(cylinder('Locking thumb nut',(.005,0,-.0328),.0085,.0045,64))
 for j in range(24):
  angle=j*math.tau/24;parts.append(cylinder('Knurled edge',(.005+.0084*math.cos(angle),.0084*math.sin(angle),-.0328),.00055,.0035,8))
 return parts
def export(key,obs):
 for i,o in enumerate(obs):uv(o,sourceuv.get(key) if i==0 else None)
 activate(obs);bpy.ops.object.join();o=bpy.context.object;o.name='SM_M16_'+key;o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
 file=O/'Meshes'/(o.name+'.fbx');file.parent.mkdir(exist_ok=True)
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE')
 o.hide_set(True);return {'name':o.name,'file':str(file),'slots':[m.name for m in o.data.materials]}
report={}
for key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x']:
 o=bpy.data.objects['SM_M16_'+key];o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
 bm=bmesh.new();bm.from_mesh(o.data);remove=[f for f in bm.faces if o.data.materials[f.material_index].name=='M16_InterfaceMetal'];bmesh.ops.delete(bm,geom=remove,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(o.data);bm.free()
 if key=='holographic':
  comps=json.loads((O/'geometry_inspection.json').read_text())[key]
  # Both source window shells are disconnected from the housing. Find them
  # by measured geometry, never by arbitrary UV colour or broad material alpha.
  o.data.materials.append(glass);gi=len(o.data.materials)-1;count=0
  for p in o.data.polygons:
   coords=[o.data.vertices[v].co for v in p.vertices]
   # Front glass and rear glass: the thin curved lens components measured
   # during inspection, within the open window and above the battery housing.
   if all(abs(v.y)<.02025 and .0348<=v.z<=.0664 for v in coords) and all(-.0032<v.x<-.0004 or -.0298<v.x<-.0221 for v in coords):p.material_index=gi;count+=1
  report['glass_faces']=count
 report[key]=export(key,[o]+adapter())
# Rebuild just the balanced grip's neck from the factory receiver contact.
# The accepted gripping surface below the collar retains all proportions.
old=bpy.data.objects['SM_M16_balanced_reargrip'];old.hide_set(True);old.name='Before_BalancedRearGrip'
before=set(bpy.context.scene.objects);bpy.ops.import_scene.fbx(filepath=src['balanced_reargrip']['fbx']);o=next(o for o in bpy.context.scene.objects if o not in before and o.type=='MESH');o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
for i,s in enumerate(src['balanced_reargrip']['slots']):o.data.materials[i]=bpy.data.materials.get(s['slot']) or bpy.data.materials.new(s['slot'])
bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if 'Collar' in o.data.materials[f.material_index].name],context='FACES');bm.to_mesh(o.data);bm.free();clip(o,-.010,False)
factorymat=bpy.data.materials.new('M16_FactoryGripInterface');cap=object_mesh('Factory seated grip collar',factoryverts,factoryfaces,factorymat);layer=cap.data.uv_layers.new(name='UVMap')
for j,uvco in enumerate(factoryuv):layer.data[j].uv=uvco
clip(cap,-.002,True)
for p in cap.data.polygons:p.use_smooth=True
def contour(ob,z):
 pts=sorted(set((round(v.co.x,7),round(v.co.y,7)) for v in ob.data.vertices if abs(v.co.z-z)<.00001))
 def cross(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
 def chain(points):
  h=[]
  for p in points:
   while len(h)>1 and cross(h[-2],h[-1],p)<=0:h.pop()
   h.append(p)
  return h
 hull=[Vector((x,y,z)) for x,y in chain(pts)[:-1]+chain(pts[::-1])[:-1]];c=sum(hull,Vector())/len(hull);result=[]
 for j in range(96):
  angle=j*math.tau/96;direction=Vector((math.cos(angle),math.sin(angle),0));hits=[]
  for a,b in zip(hull,hull[1:]+hull[:1]):
   edge=b-a;den=direction.x*edge.y-direction.y*edge.x
   if abs(den)<1e-10:continue
   delta=a-c;t=(delta.x*edge.y-delta.y*edge.x)/den;u=(delta.x*direction.y-delta.y*direction.x)/den
   if t>=0 and 0<=u<=1:hits.append(t)
  result.append(c+direction*max(hits))
 return result
lower=contour(o,-.010);upper=contour(cap,-.002);verts=[];rings=7
for k in range(rings):
 t=k/(rings-1);w=t*t*(3-2*t)
 for a,b in zip(lower,upper):v=a.lerp(b,w);v.z=-.010+.008*t;verts.append(v)
faces=[(k*96+j,k*96+(j+1)%96,(k+1)*96+(j+1)%96,(k+1)*96+j) for k in range(rings-1) for j in range(96)]
neck=object_mesh('Continuous grip shoulder',verts,faces,bpy.data.materials.get('M_BalancedRearGrip_Collar'))
for p in neck.data.polygons:p.use_smooth=True
report['balanced_reargrip']=export('balanced_reargrip',[o,cap,neck]);report['adapter_reference']='https://armsmounts.com/shop/mounts/a-r-m-s-02-m16-scope-mount/';report['mount_unchanged']=[-.000038,-.105,.1815]
(O/'models.json').write_text(json.dumps(report,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(O/'M16_Interfaces_Editable.blend'));print('M16_INTERFACES_REBUILT',report['glass_faces'],flush=True)
