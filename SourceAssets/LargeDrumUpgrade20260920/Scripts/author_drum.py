"""Author a visual-only drum shell from the two supplied reference photographs.

No internal feed mechanism is modeled. Existing game interfaces and frames are retained.
"""
import bpy,bmesh,json,math,sys
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parents[1]
guns=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['M4','AKM','QBZ191']
frames=json.loads((O/'Reference/author_frames.json').read_text())
profiles=json.loads((O.parent/'TacticalVerticalForegrip20260919/Integration/finish_profiles.json').read_text())
bpy.context.preferences.filepaths.save_version=0

def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def finish(o,material,bevel=0,segments=3):
 o.data.materials.clear();o.data.materials.append(material)
 for f in o.data.polygons:f.material_index=0;f.use_smooth=True
 active(o)
 if bevel:
  m=o.modifiers.new('Moulded edge radii','BEVEL');m.width=bevel;m.segments=segments
  bpy.ops.object.modifier_apply(modifier=m.name)
 m=o.modifiers.new('Face weighted normals','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=50
 bpy.ops.object.modifier_apply(modifier=m.name)
 return o
def box(name,loc,size,material,bevel=.001,rotation=None):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.scale=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if rotation:o.rotation_euler=rotation
 return finish(o,material,bevel)
def prism(name,outline,y0,y1,material,bevel=.001):
 n=len(outline);verts=[(x,y,z) for y in [y0,y1] for x,z in outline]
 faces=[tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
 faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 return finish(ob,material,bevel)
def revolve(name,profile,material,center=(0,0,-.085),segments=96):
 # Closed radial section revolved about Y. Radius zero rings are merged below.
 verts=[];faces=[]
 for radius,depth in profile:
  for j in range(segments):
   a=2*math.pi*j/segments;verts.append((center[0]+radius*math.cos(a),center[1]+depth,center[2]+radius*math.sin(a)))
 for i in range(len(profile)):
  ni=(i+1)%len(profile)
  for j in range(segments):faces.append((i*segments+j,i*segments+(j+1)%segments,ni*segments+(j+1)%segments,ni*segments+j))
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.0000001)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);return finish(ob,material)
def material(name,color,rough,metal=0,slot=0,grain=True):
 m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1);m['drum_slot']=slot
 n=m.node_tree.nodes;l=m.node_tree.links;bs=next(x for x in n if x.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(*color,1)
 bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal
 if grain:
  geo=n.new('ShaderNodeNewGeometry');noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=2100;noise.inputs['Detail'].default_value=2
  l.new(geo.outputs['Position'],noise.inputs['Vector'])
  ramp=n.new('ShaderNodeValToRGB');ramp.color_ramp.elements[0].color=(*(v*.88 for v in color),1);ramp.color_ramp.elements[1].color=(*(v*1.10 for v in color),1)
  l.new(noise.outputs['Fac'],ramp.inputs['Fac']);l.new(ramp.outputs['Color'],bs.inputs['Base Color'])
  roughmap=n.new('ShaderNodeMapRange');roughmap.inputs['To Min'].default_value=rough-.045;roughmap.inputs['To Max'].default_value=rough+.045
  l.new(noise.outputs['Fac'],roughmap.inputs['Value']);l.new(roughmap.outputs['Result'],bs.inputs['Roughness'])
  bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.000045
  l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],bs.inputs['Normal'])
 return m

for gun in guns:
 bpy.ops.wm.open_mainfile(filepath=str(O/'Source/OriginalDrumInterfaces.blend'))
 scene=bpy.context.scene
 for ob in list(scene.objects):
  if ob.name!=gun+'_CurrentSource':bpy.data.objects.remove(ob,do_unlink=True)
 neck=bpy.data.objects[gun+'_CurrentSource'];neck.name='Retained_'+gun+'_FeedInterface';neck.hide_set(False);neck.hide_render=False
 p=profiles[gun]
 poly=material('Graphite injection-moulded polymer',(.012,.014,.016),.56)
 panel=material('Inset polymer cover',(.009,.011,.013),.49)
 dark=material('Recess and gasket polymer',(.004,.005,.006),.66,slot=2)
 steel=material(gun+' coated latch pins',tuple(p['color']),p['rough'],p['metal'],slot=1,grain=False)
 neck.data.materials.clear();neck.data.materials.append(poly)
 bm=bmesh.new();bm.from_mesh(neck.data)
 bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000001)
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,-.0215),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
 boundary=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z+.0215)<1e-5 for v in e.verts)]
 if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
 for f in bm.faces:f.material_index=0
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(neck.data);bm.free();neck.data.update()
 # Keep the fitted feed interface free of the four protruding vertical ribs.
 box('Tower lower transition',(0,0,-.024),(.047,.068,.020),poly,.003)
 for side in [-1,1]:
  box('Tower shoulder gusset',(side*.024,0,-.024),(.0045,.060,.012),poly,.0012,rotation=(0,side*.18,0))
 # A rounded drum with a flatter upper saddle and curved lower silhouette.
 outline=[(.027,-.0255)]
 outline.extend((.0605*math.sin(a),-.085+.0605*math.cos(a)) for a in [math.radians(45+i*270/72) for i in range(73)])
 outline.append((-.027,-.0255))
 prism('Continuous drum housing',outline,-.0328,.0328,poly,.0018)
 # Three-layer parting line: actual geometry rather than a dark painted stripe.
 for side in [-1,1]:
  inset=[(x*.984,-.085+(z+.085)*.984) for x,z in outline]
  y0,y1=sorted([side*.0320,side*.0342]);prism('Perimeter gasket '+str(side),inset,y0,y1,dark,.00055)
  cap=[(x*.966,-.085+(z+.085)*.966) for x,z in outline]
  y0,y1=sorted([side*.0338,side*.0370]);prism('Split end cover '+str(side),cap,y0,y1,poly,.0013)
  # Raised rim enclosing a broad recessed face, with soft injection-moulded edges.
  profile=[(.0503,side*.0368),(.0503,side*.0377),(.0510,side*.0384),(.0552,side*.0384),(.0564,side*.0372),(.0564,side*.0364)]
  revolve('Circular cover lip '+str(side),profile,poly)
  revolve('Recessed cover face '+str(side),[(0,side*.0356),(.0502,side*.0356),(.0502,side*.0370),(.0492,side*.0374),(0,side*.0374)],panel)
 # Front asymmetry from the references: a recessed central socket and curved
 # latch at the upper edge, with a shallow moulded handle on the opposite face.
 revolve('Front recessed central boss',[(.0098,-.0371),(.0100,-.0382),(.0126,-.0386),(.0140,-.0377),(.0140,-.0367)],poly)
 revolve('Front central recess floor',[(0,-.0370),(.0098,-.0370),(.0098,-.03745),(0,-.03745)],dark)
 rear_panel=[(-.024,-.048),(.024,-.048),(.030,-.057),(.028,-.112),(.019,-.122),(-.019,-.122),(-.028,-.112),(-.030,-.057)]
 prism('Rear shallow moulded panel',rear_panel,.0370,.0378,panel,.0012)
 for side in [-1,1]:
  for angle in [66,91,117,143]:
   a=math.radians(angle)*side
   x=.0604*math.sin(a);z=-.085+.0604*math.cos(a)
   box('Outer shell moulding rib',(x,0,z),(.0045,.062,.0021),poly,.0008,rotation=(0,-a,0))
 # External, closed latch assembly only. There is no functional inner mechanism.
 for x in [-.022,.022]:
  box('Latch hinge pedestal',(x,-.0359,-.037),(.010,.010,.010),poly,.0014)
  pin=revolve('Latch pin',[(0,-.002),(.0024,-.002),(.0024,.002),(0,.002)],steel,center=(x,-.0407,-.036),segments=32)
 latch=[(-.026,-.040),(-.018,-.035),(.018,-.035),(.026,-.040),(.021,-.046),(-.021,-.046)]
 prism('Upper curved latch paddle',latch,-.0424,-.0365,poly,.0016)
 for x in [-.013,-.007,0,.007,.013]:box('Latch grip notch',(x,-.0426,-.0408),(.0014,.00065,.0043),dark,.0003)
 # Small moulded witness marks on the back; no invented manufacturer branding.
 for z in [-.063,-.068,-.073]:box('Rear moulded witness',(0,.0383,z),(.012,.0005,.0007),poly,.0002)
 for ob in scene.objects:
  if ob.type=='MESH':
   active(ob);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
   ob['visual_shell_only']=True
   ob['reference_images']='user_front.png; user_rear.png'
 scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
 folder=O/gun;folder.mkdir(exist_ok=True)
 bpy.ops.wm.save_as_mainfile(filepath=str(folder/'Drum_Construction.blend'))
 print('DRUM_CONSTRUCTION_COMPLETE',gun,flush=True)
