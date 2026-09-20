"""Private M16 fits. Metres in Blender; FBX cm; unchanged accepted bodies/UV0."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;S=O.parent
I=json.loads((O/'authoring.json').read_text());sources=json.loads((O/'sources.json').read_text())
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
(O/'Meshes').mkdir(exist_ok=True)
R=Matrix(I['rest']['WPN_root']);donorR=Matrix(I['donors']['drum']['rest']['WPN_root'])
G=Matrix(I['donors']['vertical']['mount']);G.translation.z=.0545
optic=Matrix.Rotation(-math.pi/2,4,'Z');optic.translation=Vector((-.000038,-.105,.1815))
report={'parts':{},'grip_mount': [list(v) for v in G],'optic_mount':[list(v) for v in optic],'units':'Blender metres, UE centimetres; root assets use .01 compensation'}
metal=bpy.data.materials.new('M16_InterfaceMetal');metal.diffuse_color=(.035,.038,.041,1)
def rows(m):return [list(v) for v in m]
def activate(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for o in obs:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=obs[-1]
def box(name,center,size):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.scale=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(metal)
 b=o.modifiers.new('Machined edge','BEVEL');b.width=.00035;b.segments=3;bpy.ops.object.modifier_apply(modifier=b.name);return o
def tube(name,center,length,rx,rz,axis='Y'):
 n=64;verts=[]
 for y in [-length/2,length/2]:
  for skin in [0,.0015]:
   for j in range(n):
    a=j*math.tau/n;v=Vector(((rx+skin)*math.cos(a),y,(rz+skin)*math.sin(a)))
    if axis=='X':v=Vector((v.y,v.x,v.z))
    verts.append(v+Vector(center))
 faces=[]
 for j in range(n):
  k=(j+1)%n
  faces.extend([(j,k,2*n+k,2*n+j),(n+j,3*n+j,3*n+k,n+k),(j,n+j,n+k,k),(2*n+j,2*n+k,3*n+k,3*n+j)])
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.materials.append(metal);o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);return o
def load(key):
 before=set(bpy.context.scene.objects);bpy.ops.import_scene.fbx(filepath=sources[key]['fbx'],use_custom_normals=True)
 obs=[o for o in bpy.context.scene.objects if o not in before and o.type=='MESH' and not o.name.startswith(('UCX_','UBX_','UCP_','USP_'))]
 for o in obs:o.data.transform(o.matrix_world);o.parent=None;o.matrix_world=Matrix.Identity(4)
 activate(obs)
 if len(obs)>1:bpy.ops.object.join()
 o=bpy.context.object
 # FBX exporter disambiguates material labels. Restore source slot identity.
 for index,s in enumerate(sources[key]['slots']):
  material=bpy.data.materials.get(s['slot']) or bpy.data.materials.new(s['slot'])
  if index<len(o.data.materials):o.data.materials[index]=material
  else:o.data.materials.append(material)
 return o
def uv(o,index):
 while len(o.data.uv_layers)<=index:o.data.uv_layers.new(name='M16Coating'+str(len(o.data.uv_layers)))
 layer=o.data.uv_layers[index]
 for f in o.data.polygons:
  axis=max(range(3),key=lambda k:abs(f.normal[k]));a,b=[i for i in range(3) if i!=axis]
  for li in f.loop_indices:
   p=o.data.vertices[o.data.loops[li].vertex_index].co;layer.data[li].uv=(p[a]/.04,p[b]/.04)
def export(key,obs,bindings,frame='root',sockets=None):
 for o in obs:
  # Source UV0/1/2 and the coating UV3 have fixed runtime indices. Blender
  # joins by layer name; normalize names before adding interface geometry.
  coords=[[tuple(d.uv) for d in layer.data] for layer in list(o.data.uv_layers)[:3]]
  for layer in list(o.data.uv_layers):o.data.uv_layers.remove(layer)
  for i in range(4):
   layer=o.data.uv_layers.new(name='M16_UV'+str(i))
   if i<len(coords):
    for j,p in enumerate(coords[i]):layer.data[j].uv=p
  if not o.data.uv_layers:uv(o,0)
  uv(o,3)
 activate(obs)
 if len(obs)>1:bpy.ops.object.join()
 o=bpy.context.object;o.name='SM_M16_'+key
 file=O/'Meshes'/(o.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
 bb=[[min(v.co[i] for v in o.data.vertices),max(v.co[i] for v in o.data.vertices)] for i in range(3)]
 report['parts'][key]={'name':o.name,'file':str(file),'frame':frame,'bindings':bindings,'source':sources[key]['source'] if key in sources else 'M16 factory magazine','bounds_m':bb,'sockets':sockets or {}}
 o.hide_set(True)
for key in sources:
 o=load(key);obs=[o];bindings={s['slot']:s['material'] for s in sources[key]['slots']};bindings['M16_InterfaceMetal']=None;frame='root';sockets={}
 if key in ('vertical','tactical_vertical','canted','prism','angled'):
  if key=='angled':o.data.transform(Matrix(I['donors']['angled']['mount']).inverted()@Matrix(I['donors']['angled']['rest']['WPN_root']).inverted())
  o.data.transform(G)
  # Split elliptical bands follow the round handguard; the rail crown remains
  # at the accepted donor contact height. No scaling of grip or fingers.
  for y in [-.286,-.324]:obs.append(tube('Foreend clamp',(-.000038,y,.09155),.008,.0357,.0349))
  obs.append(box('Lower rail',(-.000038,-.305,.0545),(.021,.058,.004)))
  for y in [-.286,-.324]:obs.append(box('Clamp lug',(-.000038,y,.056),(.027,.008,.006)))
 elif key in ('holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x'):
  frame='optic'
  obs.extend([box('Carry handle rail',(0,0,-.003),(.17,.021,.006)),box('Carry handle saddle',(.012,0,-.0075),(.105,.013,.005))])
  for x in [-.060,-.032,-.004,.024,.052]:obs.append(box('Rail lug',(x,0,-.0008),(.009,.023,.0016)))
  # Central underside locking bar occupies the carry handle channel.
  obs.append(box('Handle locking shoe',(.008,0,-.016),(.024,.018,.004)))
 elif key=='lpvo_ring':frame='optic_ring'
 elif key in ('skeleton','qr_performance','core_stock','tactical_telescopic'):
  T=Matrix.Rotation(math.pi/2,4,'Z');T.translation=Vector((-.000038,.041045,.0917));o.data.transform(T)
  obs.append(tube('M16 stock receiver collar',(-.000038,.046,.0917),.018,.017,.017))
 elif key.endswith('reargrip'):
  # Keep the accepted gripping surface; fit only the neck above the hand.
  top=max(v.co.z for v in o.data.vertices)
  for v in o.data.vertices:
   if v.co.z>.008:v.co.z=.008+(v.co.z-.008)*(.01657-.008)/(top-.008)
  obs.append(box('Grip tang',(-.000038,-.007,.015),(.022,.028,.005)))
 elif key=='large_drum':
  o.data.transform(donorR.inverted())
  shift=Vector(json.loads((S/'M16Gameplay20260919/build.json').read_text())['magazine_contact_shift_m'])
  o.data.transform(Matrix.Translation(shift));o.data.transform(R)
  frame='mesh_bind'
 elif key in ('laser','flashlight'):
  # Both accepted emitter bodies already use root coordinates. Slide the
  # inner rail out to the M16 round fore-end and keep their optical axis.
  shift=Vector((.025,-.100,.01355));o.data.transform(Matrix.Translation(shift))
  for y in [-.403,-.435]:obs.append(tube('Tactical band',(-.000038,y,.09155),.007,.0344,.0348))
  obs.append(box('Side rail',(.038,-.419,.09155),(.006,.068,.021)))
  for name,data in sources[key]['sockets'].items():
   p=data['location'];sockets[name]={'location':[p[0]+shift.x*100,p[1]-shift.y*100,p[2]+shift.z*100],'rotation':data['rotation']}
 else:frame='muzzle'
 export(key,obs,bindings,frame,sockets)
# Factory extended magazine: keep throat and original UV0; only lower portion
# gets longer. Its original curved direction is retained in the socket frame.
with bpy.data.libraries.load(str(S/'M16Gameplay20260919/M16_Manny_Editable.blend'),link=False) as (src,dst):dst.objects=['M16A2_Magazine']
o=dst.objects[0];bpy.context.collection.objects.link(o);o.hide_set(False)
o.data.transform(o.matrix_world);o.parent=None;o.matrix_world=Matrix.Identity(4);o.modifiers.clear();o.vertex_groups.clear()
o.data.transform(R.inverted())
for v in o.data.vertices:
 t=max(0,min(1,(.01-v.co.z)/.105));v.co.z-=.052*t;v.co.y-=.019*t*t
o.data.transform(R)
export('ext_mag',[o],{m.name:'/Game/Weapons/M16A2Migration/Materials/M_M16A2_PBR' for m in o.data.materials},'mesh_bind')
(O/'models.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M16_CommonAttachments_Editable.blend'))
print('M16_COMMON_MODELS_AUTHORED',len(report['parts']),flush=True)
