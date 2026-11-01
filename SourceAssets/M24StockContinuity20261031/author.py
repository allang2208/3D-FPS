"""M24-only continuity pass. All dimensions are source metres; sockets stay fixed."""
import bpy,bmesh,json,math,ast
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).resolve().parent;OLD=O.parent/'M24ReceiverGripRebuild20261031'
bpy.ops.wm.open_mainfile(filepath=str(OLD/'M24_ReceiverGrip_Editable.blend'),load_ui=False,use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
spec=json.loads((OLD/'geometry_contract.json').read_text());report={'exports':{},'materials':dict(spec['materials']),'grips':{},'source':str(OLD),'animations_changed':False}
(O/'Exports').mkdir(exist_ok=True)
# Reuse the established FBX coordinate contract and normal/UV authoring functions.
tree=ast.parse((OLD/'author_geometry.py').read_text())
for n in tree.body:
 if isinstance(n,ast.FunctionDef) and n.name in ('mat','geometry','normals_uv','export','loops'):
  exec(compile(ast.Module(body=[n],type_ignores=[]),str(OLD/'author_geometry.py'),'exec'))
coat=mat('M24_NewReceiverMetal',(.026,.029,.032),1,.48)
for ob in list(bpy.data.objects):
 if ob.name.startswith(('Native_receiver_exact_seat','Advanced_receiver_exact_seat')) or ob.name=='M24_NewReceiverAndGripSeat':bpy.data.objects.remove(ob,do_unlink=True)
stock=bpy.data.objects['M24_SkeletonStock_ReferenceProportion']
# Level the actual continuous lower rail, not a butt-pad bounding-box centre.
p=np.array([v.co[:] for v in stock.data.vertices]);samples=[]
for y in np.linspace(-.185,-.120,20):
 q=p[np.abs(p[:,1]-y)<.001]
 samples.append((y,float(np.min(q[:,2]))))
slope,intercept=np.polyfit(np.array(samples)[:,0],np.array(samples)[:,1],1)
angle=-math.atan(slope);pivot=Vector((0,-.04,.081))
stock.data.transform(Matrix.Translation(pivot)@Matrix.Rotation(angle,4,'X')@Matrix.Translation(-pivot))
report['stock']={'rail_before_degrees':math.degrees(-angle),'correction_degrees':math.degrees(angle),'pivot':list(pivot),'beam_samples_before':samples}
# Create one genuine interface on the Meshy hinge, retaining its UVs elsewhere.
cut=-.043
bm=bmesh.new();bm.from_mesh(stock.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,cut,0),plane_no=(0,1,0),dist=.0000001,clear_outer=True)
boundary=[e for e in bm.edges if e.is_boundary and all(abs(v.co.y-cut)<.000001 for v in e.verts)]
raw=[tuple(tuple(round(c,7) for c in v.co) for v in e.verts) for e in boundary]
rings=loops(raw)
ring=max(rings,key=lambda a:abs(sum(a[i][0]*a[(i+1)%len(a)][2]-a[(i+1)%len(a)][0]*a[i][2] for i in range(len(a)))))
caps=bmesh.ops.holes_fill(bm,edges=boundary,sides=0)['faces']
for f in caps:
 for layer in bm.loops.layers.uv.values():
  for loop in f.loops:loop[layer].uv=(loop.vert.co.x*20,loop.vert.co.z*20)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(stock.data);bm.free()
report['stock']['cut_interface_ring']=ring
rc=np.mean(np.array(ring),axis=0);lo=np.min(np.array(ring),axis=0);hi=np.max(np.array(ring),axis=0)
zc=(lo[2]+hi[2])*.5
angles=[math.atan2(v[2]-zc,v[0]) for v in ring]
def rounded_section(y,width,bottom,top):
 # Superellipse gives flat manufactured faces with a small eased perimeter.
 out=[];half=(top-bottom)*.5;center=(top+bottom)*.5
 for a in angles:
  x,z=math.cos(a),math.sin(a);r=(abs(x/width)**8+abs(z/half)**8)**(-1/8)
  out.append((r*x,y,center+r*z))
 return out
stations=[(cut+.0015,float(max(abs(lo[0]),abs(hi[0]))),float(lo[2]),float(hi[2])),(-.035,.0185,.062,.1068),(-.026,.0200,.077,.107),(-.014,.0225,.084,.107),(.004,.023,.084,.107),(.025,.023,.084,.107),(.05455,.023,.084,.107)]
# Interpolate stations with smooth easing; the measured mating loop is untouched.
sections=[ring]
previous=(cut,float(max(abs(lo[0]),abs(hi[0]))),float(lo[2]),float(hi[2]))
for end in stations:
 for j in range(1,6):
  t=j/5;s=t*t*(3-2*t);state=[previous[k]*(1-s)+end[k]*s for k in range(4)]
  sec=rounded_section(*state)
  if len(sections)<=5:
   blend=s;sec=[(a[0]*(1-blend)+b[0]*blend,state[0],a[2]*(1-blend)+b[2]*blend) for a,b in zip(ring,sec)]
  sections.append(sec)
 previous=end
n=len(ring);verts=[p for s in sections for p in s];faces=[]
for k in range(len(sections)-1):
 for i in range(n):faces.append((k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i))
faces += [tuple(range(n-1,-1,-1)),tuple((len(sections)-1)*n+i for i in range(n))]
core=geometry('M24_ContinuousReceiverSeat',verts,faces,coat);normals_uv(core)
# Same bolt clearance as the current accepted mechanism, no socket/path movement.
bpy.ops.mesh.primitive_cylinder_add(vertices=64,radius=.012,depth=.165,location=(0,.027,.114),rotation=(math.pi/2,0,0));tool=bpy.context.object
bpy.context.view_layer.objects.active=core;mod=core.modifiers.new('Retained bolt clearance','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=tool;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(tool,do_unlink=True)
normals_uv(core)
# Open coincident assembly interfaces have continuous side normals; a hidden cap
# must not contribute a perpendicular normal and draw a black line over the join.
def remove_interface_caps(ob,ys):
 bm=bmesh.new();bm.from_mesh(ob.data)
 cap=[f for f in bm.faces if any(all(abs(v.co.y-y)<.000001 for v in f.verts) for y in ys)]
 bmesh.ops.delete(bm,geom=cap,context='FACES_ONLY');bm.to_mesh(ob.data);bm.free()
 if ob.data.has_custom_normals:
  bpy.context.view_layer.objects.active=ob;bpy.ops.mesh.customdata_custom_splitnormals_clear()
 for p in ob.data.polygons:p.use_smooth=True
remove_interface_caps(core,[cut,.05455])
def transition(name,ring,rear,curved=True):
 n=len(ring);rows=[]
 for j in range(17):
  t=j/16;s=t*t*(3-2*t) if curved else t
  rows += [(a[0]*(1-s)+b[0]*s,a[1]*(1-t)+b[1]*t,a[2]*(1-s)+b[2]*s) for a,b in zip(ring,rear)]
 fs=[(k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i) for k in range(16) for i in range(n)]
 fs += [tuple(range(n-1,-1,-1)),tuple(16*n+i for i in range(n))]
 ob=geometry(name,rows,fs,coat);normals_uv(ob)
 remove_interface_caps(ob,[float(ring[0][1]),float(rear[0][1])]);return ob
advanced=[]
for j,r in enumerate(spec['advanced_boundary_loops']):
 a=np.array(r)
 if a[:,2].max()<.06:
  # The trigger-guard root is retained as a thin separate functional strut.
  center=float(a[:,2].mean());rear=[(p[0],.0375,.045+(p[2]-center)) for p in r]
 else:
  bottom=float(a[:,2].min());top=float(a[:,2].max())
  rear=[(p[0]*.023/.0261,.05455,.084+(p[2]-bottom)/(top-bottom)*.023) for p in r]
 advanced.append(transition('M24_ContinuousAdvancedSeat_'+str(j),r,rear))
native=[]
for j,r in enumerate(spec['native_boundary_loops']):
 a=np.array(r);c=a.mean(0);rear=[]
 for p in r:
  angle=math.atan2(p[2]-c[2],p[0]-c[0]);x,z=math.cos(angle),math.sin(angle);rad=(abs(x/.023)**8+abs(z/.0115)**8)**(-1/8)
  rear.append((rad*x,.05455,.0955+rad*z))
 native.append(transition('M24_ContinuousNativeSeat_'+str(j),r,rear))
grips=[]
for key in ('Default','balanced','phantom','stable'):
 ob=bpy.data.objects['M24_PistolGrip_'+key];p=np.array([v.co[:] for v in ob.data.vertices]);before=[p.min(0).tolist(),p.max(0).tolist()]
 # Add usable heel length below the finger web, keeping palm/neck contacts fixed.
 extension={'Default':.012,'balanced':.017,'phantom':.010,'stable':.009}[key]
 top=.018;low=float(p[:,2].min());changed=0
 for v in ob.data.vertices:
  if v.co.z>=top:continue
  t=max(0,min(1,(top-v.co.z)/(top-low)));s=t*t*(3-2*t)
  v.co.z-=extension*s;changed+=1
 # Restrained edge rounding of the original low-poly default; donor high-poly
 # grips retain their UV/topology and cannot be globally subdivided.
 if key=='Default':
  normals_uv(ob,.0008)
  if ob.data.has_custom_normals:
   bpy.context.view_layer.objects.active=ob;bpy.ops.mesh.customdata_custom_splitnormals_clear()
  for p in ob.data.polygons:p.use_smooth=True
 else:normals_uv(ob)
 q=np.array([v.co[:] for v in ob.data.vertices]);report['grips'][key]={'before':before,'after':[q.min(0).tolist(),q.max(0).tolist()],'heel_extension_mm':extension*1000,'unchanged_above_z':top,'vertices_adjusted':changed}
 grips.append(ob);export('SM_M24_PistolGrip_'+key,[ob])
front=bpy.data.objects['M24_AdvancedFront_ForIndependentGrip']
export('SM_M24_ReceiverStock_Native',[stock,core]+native)
export('SM_M24_ReceiverStock_Advanced',[stock,core]+advanced)
export('SM_M24_AdvancedFront_ForIndependentGrip',[front])
visible=[stock,core,front,grips[0]]+advanced
for ob in bpy.data.objects:
 if ob.type=='MESH':ob.hide_set(ob not in visible);ob.hide_render=ob not in visible
# Preview materials represent the same new finish targets, not legacy FBX colours.
for m in bpy.data.materials:
 if m.name.startswith('M24_Advanced_'):metal=0 if m.name.endswith('_1') else 1;color=(.009,.011,.012) if metal==0 else (.026,.029,.032);rough=.61 if metal==0 else .48
 elif m.name=='SniperStock_MeshySurface':metal=1;color=(.026,.029,.032);rough=.48
 elif m.name=='M24_NewReceiverMetal':continue
 elif m.name.startswith(('M24_Grip','M24_NewPistolGrip')):metal=0;color=(.018,.020,.021);rough=.59
 else:continue
 m.use_nodes=True;nodes=m.node_tree.nodes;bs=next((n for n in nodes if n.type=='BSDF_PRINCIPLED'),None)
 if not bs:continue
 for pin,val in [('Base Color',(*color,1)),('Metallic',metal),('Roughness',rough)]:
  for link in list(bs.inputs[pin].links):m.node_tree.links.remove(link)
  bs.inputs[pin].default_value=val
# Confirm the corrected source rail and unchanged contact band for this requested pass.
p=np.array([v.co[:] for v in stock.data.vertices]);rail=[]
for y in np.linspace(-.185,-.120,20):
 q=p[np.abs(p[:,1]-y)<.001];rail.append((y,float(q[:,2].min())))
report['stock']['rail_after_degrees']=math.degrees(math.atan(np.polyfit(np.array(rail)[:,0],np.array(rail)[:,1],1)[0]))
(O/'geometry_contract.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_StockContinuity_Editable.blend'))
print('M24_CONTINUITY_AUTHORED',len(report['exports']),report['stock']['rail_after_degrees'],flush=True)
