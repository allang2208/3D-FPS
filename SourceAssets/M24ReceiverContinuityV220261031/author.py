"""Continuous lower chassis fitted to the native moving trigger and Meshy hinge."""
import bpy,bmesh,json,math,ast
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent;S=O.parent;OLD=S/'M24StockContinuity20261031'
bpy.ops.wm.open_mainfile(filepath=str(OLD/'M24_StockContinuity_Editable.blend'),load_ui=False,use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
prior=json.loads((OLD/'geometry_contract.json').read_text());report={'exports':{},'materials':prior['materials'],'unchanged':['trigger bone/path','all grips','stock alignment','all poses'],'removed_components':[]}
(O/'Exports').mkdir(exist_ok=True)
tree=ast.parse((S/'M24ReceiverGripRebuild20261031/author_geometry.py').read_text())
for n in tree.body:
 if isinstance(n,ast.FunctionDef) and n.name in ('mat','geometry','normals_uv','export'):
  exec(compile(ast.Module(body=[n],type_ignores=[]),'helpers','exec'))
coat=bpy.data.materials['M24_NewReceiverMetal'];parts=[]
tree=ast.parse((S/'M24AdvancedAction20261029/DetailV2/author.py').read_text())
steel=coat;interior=coat
for n in tree.body:
 if isinstance(n,ast.FunctionDef) and n.name in ('finish','mesh','box','cylinder','prism_x','apply','cut','fastener'):
  exec(compile(ast.Module(body=[n],type_ignores=[]),'hard_surface_helpers','exec'))
stock=bpy.data.objects['M24_SkeletonStock_ReferenceProportion']
front=bpy.data.objects['M24_AdvancedFront_ForIndependentGrip']
# Delete complete old lower-housing islands, retaining untouched forend and upper action.
bm=bmesh.new();bm.from_mesh(front.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000005)
remaining=set(bm.verts);remove=[]
while remaining:
 todo=[remaining.pop()];group=[]
 while todo:
  v=todo.pop();group.append(v)
  for e in v.link_edges:
   w=e.other_vert(v)
   if w in remaining:remaining.remove(w);todo.append(w)
 p=np.array([v.co[:] for v in group]);lo=p.min(0);hi=p.max(0)
 if hi[2]<.110 and lo[1]<.276:
  remove+=group;report['removed_components'].append({'vertices':len(group),'lo':lo.tolist(),'hi':hi.tolist()})
bmesh.ops.delete(bm,geom=remove,context='VERTS');bm.to_mesh(front.data);bm.free()
# Exact stock mounting loop. The stock itself and its native branch stay unchanged.
ring=prior['stock']['cut_interface_ring'];p=np.array(ring);lo=p.min(0);hi=p.max(0)
zc=(lo[2]+hi[2])/2;angles=[math.atan2(v[2]-zc,v[0]) for v in ring]
# Stations define one receiver, not independently capped adapter segments.
states=np.array([
 [-.043,max(abs(lo[0]),abs(hi[0])),lo[2],hi[2]],
 [-.039,.0182,.064,.1068],[-.028,.0198,.0775,.107],[-.014,.0223,.084,.107],
 [.008,.023,.084,.107],[.045,.0236,.084,.107],[.055,.024,.081,.107],
 [.070,.0247,.063,.107],[.090,.0254,.057,.107],[.125,.0261,.050,.107],
 [.146,.0261,.050,.107],[.238,.0261,.057,.107],[.263,.0261,.069,.107],
 [.282,.027,.071,.107]])
def interpolate(y):
 i=max(0,min(len(states)-2,int(np.searchsorted(states[:,0],y,side='right'))-1))
 a,b=states[i:i+2];t=(y-a[0])/(b[0]-a[0]);s=t*t*(3-2*t)
 return a[1:]*(1-s)+b[1:]*s
def section(y):
 width,low,high=interpolate(y);half=(high-low)*.5;center=(high+low)*.5;out=[]
 for angle in angles:
  x,z=math.cos(angle),math.sin(angle);radius=(abs(x/width)**10+abs(z/half)**10)**(-.1)
  out.append((radius*x,y,center+radius*z))
 return out
sections=[ring]
for k in range(len(states)-1):
 for j in range(1,7):
  y=states[k,0]+(states[k+1,0]-states[k,0])*j/6;r=section(y)
  if k==0:
   t=j/6;s=t*t*(3-2*t);r=[(a[0]*(1-s)+b[0]*s,y,a[2]*(1-s)+b[2]*s) for a,b in zip(ring,r)]
  sections.append(r)
n=len(ring);vs=[v for row in sections for v in row]
fs=[(k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i) for k in range(len(sections)-1) for i in range(n)]
fs += [tuple(range(n-1,-1,-1)),tuple((len(sections)-1)*n+i for i in range(n))]
body=geometry('M24_OnePieceLowerReceiver',vs,fs,coat)
normals_uv(body)
# Functional apertures use native component positions without moving the components.
cut(body,cylinder('rear bolt clearance',(0,.03975,.114),.012,.1395,'Y',coat,64,0))
cut(body,cylinder('action clearance',(0,.195,.115),.0191,.206,'Y',coat,64,0))
cut(body,box('magazine well',(0,(.13989+.22948)/2,.049),(.0347,.0917,.114),coat,.0007))
# Native trigger root is captured inside a housing; lower blade remains exposed.
trigger_slot=[(.065,.019),(.098,.019),(.098,.0585),(.091,.0610),(.069,.0610),(.065,.057)]
cut(body,prism_x('trigger blade pocket',trigger_slot,-.0058,.0058,coat,.00025))
# A single recessed side panel spans both old join locations, with metric UVs.
panel=[(-.027,.096),(-.017,.090),(.042,.090),(.059,.085),(.079,.070),(.116,.058),
       (.143,.058),(.233,.064),(.266,.080),(.266,.100),(-.023,.100)]
for sign in (-1,1):
 # Subdivide the pocket floor along its actual changing width. A single warped
 # polygon here would triangulate across the old join and create a false facet.
 ymin=min(y for y,z in panel)+.00010;ymax=max(y for y,z in panel)-.00010
 ys=sorted(set(round(float(y),7) for y in [ymin,ymax]+[y for y,z in panel if ymin<y<ymax]+[float(y) for y in states[:,0] if ymin<y<ymax]+list(np.linspace(ymin,ymax,180))))
 v=[]
 for y in ys:
  hits=[]
  for (a,b),(c,d) in zip(panel,panel[1:]+panel[:1]):
   if abs(c-a)>1e-9 and min(a,c)<=y<=max(a,c):hits.append(b+(d-b)*(y-a)/(c-a))
  z0,z1=min(hits),max(hits);xi=sign*(interpolate(y)[0]-.00115);xo=sign*.035
  v += [(xi,y,z0),(xo,y,z0),(xo,y,z1),(xi,y,z1)]
 m=4;f=[(3,2,1,0),tuple((len(ys)-1)*4+i for i in range(4))]
 f += [(k*4+i,k*4+(i+1)%4,(k+1)*4+(i+1)%4,(k+1)*4+i) for k in range(len(ys)-1) for i in range(4)]
 cut(body,mesh('continuous side pocket tool',v,f,coat,0))
 if len(body.data.vertices)<10000:raise RuntimeError('Pocket boolean invalidated continuous receiver')
# A closed guard with a level lower bow. Its front leg is part of the receiver,
# and its rear end meets the independent grip, not a discarded stock wrist.
outer=[(.034,.048),(.043,.041),(.051,.024),(.060,.019),(.117,.019),(.130,.026),(.136,.038),(.136,.063),(.128,.063),(.128,.040),(.122,.030),(.115,.025),(.062,.025),(.057,.029),(.049,.045),(.041,.051)]
guard=prism_x('M24_CalibratedTriggerGuard',outer,-.009,.009,coat,.0007)
apply(guard)
mod=body.modifiers.new('Integral guard attachment','BOOLEAN');mod.operation='UNION';mod.solver='EXACT';mod.object=guard
bpy.context.view_layer.objects.active=body;bpy.ops.object.modifier_apply(modifier=mod.name)
parts.remove(guard);bpy.data.objects.remove(guard,do_unlink=True)
# Two restrained paired fasteners; all machining now belongs to the same plate.
for sign in (-1,1):
 for y,z in ((.018,.095),(.251,.087)):
  fastener(body,sign,y,z,float(interpolate(y)[0])-.00115,.0018)
# Clear inherited normals after booleans, then author final normals and UVs once.
if body.data.has_custom_normals:
 bpy.context.view_layer.objects.active=body;bpy.ops.mesh.customdata_custom_splitnormals_clear()
for uv in list(body.data.uv_layers):body.data.uv_layers.remove(uv)
# Do not bevel away the measured mating ring. All other machined edges get
# the same small radius, with explicit sharp breaks at unreached pocket corners.
bm=bmesh.new();bm.from_mesh(body.data);weight=bm.edges.layers.float.new('bevel_weight_edge')
for e in bm.edges:
 e[weight]=1. if e.is_manifold and e.calc_face_angle()> .5 and all(v.co.y>-.0425 for v in e.verts) else 0.
bm.to_mesh(body.data);bm.free();bpy.context.view_layer.objects.active=body
bevel=body.modifiers.new('Local edge radii preserving hinge ring','BEVEL');bevel.limit_method='WEIGHT';bevel.width=.00025;bevel.segments=3
bpy.ops.object.modifier_apply(modifier=bevel.name)
bm=bmesh.new();bm.from_mesh(body.data)
for e in bm.edges:e.smooth=not (e.is_manifold and e.calc_face_angle()>.8)
bm.to_mesh(body.data);bm.free();normals_uv(body)
details=[p for p in parts if p.type=='MESH']
for ob in details:apply(ob);normals_uv(ob)
# Weld the real matching end rings into one stock/receiver surface. Internal
# mating caps are removed; no overlapping sleeve is used to conceal the join.
assembled=[]
for ob in (stock,body):
 cp=ob.copy();cp.data=ob.data.copy();bpy.context.collection.objects.link(cp);cp.hide_set(False);assembled.append(cp)
assembled[1].data.uv_layers[0].name=assembled[0].data.uv_layers[0].name
bpy.ops.object.select_all(action='DESELECT')
for ob in assembled:ob.select_set(True)
bpy.context.view_layer.objects.active=assembled[0];bpy.ops.object.join();joined=bpy.context.object;joined.name='M24_ContinuousStockReceiver'
bm=bmesh.new();bm.from_mesh(joined.data)
caps=[f for f in bm.faces if all(abs(v.co.y+.043)<.0000003 for v in f.verts)]
bmesh.ops.delete(bm,geom=caps,context='FACES_ONLY')
seam=[v for v in bm.verts if abs(v.co.y+.043)<.0000003]
bmesh.ops.remove_doubles(bm,verts=seam,dist=.000001)
report['welded_hinge_ring_vertices']=sum(abs(v.co.y+.043)<.0000003 for v in bm.verts)
report['hinge_open_edges']=sum(e.is_boundary for e in bm.edges if all(abs(v.co.y+.043)<.0000003 for v in e.verts))
bm.to_mesh(joined.data);bm.free()
export('SM_M24_ReceiverStock_Advanced',[joined]+details)
export('SM_M24_AdvancedFront_ForIndependentGrip',[front])
visible=[joined,front,bpy.data.objects['M24_PistolGrip_Default']]+details
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.hide_set(ob not in visible);ob.hide_render=ob not in visible
# Native assembly used in previews: true moving trigger, magazine and bolt,
# plus source barrel/optic. These never enter the static chassis export.
src=S/'M24ReloadFlow20261028/M24_ReloadFlow_Editable.blend'
with bpy.data.libraries.load(str(src),link=False) as (source,target):
 target.objects=[name for name in source.objects if name in ('M24_trigger','M24_clip','M24_bolt','M24_boltrear','M24_base','M24_MainScope_Lowpoly','M24_ExtraScope_Lowpoly','M24_ScopeGlass_Lowpoly')]
preview=[]
for ob in target.objects:
 if not ob:continue
 bpy.context.collection.objects.link(ob);ob.parent=None;ob.matrix_world=Matrix.Identity(4)
 for mod in list(ob.modifiers):ob.modifiers.remove(mod)
 if ob.animation_data:ob.animation_data_clear()
 if ob.name.startswith('M24_base'):
  bm=bmesh.new();bm.from_mesh(ob.data)
  bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,.282,0),plane_no=(0,1,0),clear_inner=True,dist=.0000001)
  bm.to_mesh(ob.data);bm.free();ob.name='Preview_NativeBarrel'
 ob.hide_set(False);ob.hide_render=False;preview.append(ob)
 # Match saved private M24 metal finish, while preserving existing normals.
 for ma in ob.data.materials:
  if not ma or 'glass' in ma.name.lower():continue
  ma.use_nodes=True;bs=next((n for n in ma.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
  if not bs:continue
  for pin,value in [('Base Color',(.026,.029,.032,1)),('Roughness',.48),('Metallic',1.)]:
   for link in list(bs.inputs[pin].links):ma.node_tree.links.remove(link)
   bs.inputs[pin].default_value=value
report['receiver_stations']=states.tolist();report['trigger_bounds']=[[-.0046283,.0684125,.0265855],[.0046283,.0941598,.0644704]]
report['trigger_native_coordinates_unchanged']=True;report['hinge_ring']=ring
report['preview_native_parts']=[o.name for o in preview]
report['triangles']={o.name:sum(len(p.vertices)-2 for p in o.data.polygons) for o in [stock,front,body]+details}
(O/'geometry_contract.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_ReceiverContinuityV2_Editable.blend'))
print('M24_RECEIVER_V2_AUTHORED',report['exports'],flush=True)
