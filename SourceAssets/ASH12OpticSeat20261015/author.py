"""Two private ASH optic fits; keep the four already-seated native variants."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;C=json.loads((O/'capture.json').read_text());W=O/'Working';X=O/'Exports';X.mkdir(exist_ok=True)
helper=(O.parent/'M16OpticSeat20261015/author.py').read_text()
exec(compile(helper[helper.index('def active('):helper.index('def foot(')],'<hard_surface_helpers>','exec'))
R={'assets':{},'unchanged':['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring','thermal_selector'],'complete':False}
shoe_material=C['assets']['holographic']['slots'][-1]['material']
def box(name,lo,hi):
 return extrude(name,[(lo[1],lo[2]),(hi[1],lo[2]),(hi[1],hi[2]),(lo[1],hi[2])],lo[0],hi[0])
def boolean(o,other,operation):
 active(o);mod=o.modifiers.new(operation,'BOOLEAN');mod.operation=operation;mod.solver='EXACT';mod.object=other;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(other,do_unlink=True)
def support(key):
 if key=='eoth_holographic':
  # Rearward cantilever: the body clears the fixed front sight, while its
  # lower bearing stays entirely on the existing 63..125 mm rail segment.
  x0,x1=-.067,.015
  pad=box('Rearward optic support deck',(x0,-.0083,-.0011),(x1,.0083,.00133))
  lower=box('ASH rail bearing',(-.047,-.0083,-.00298),(x1,.0083,-.0009));boolean(pad,lower,'UNION')
  jaw0,jaw1=-.045,.013;top=-.00388
 else:
  x0,x1=-.025,.025
  pad=box('Thermal rail crown shoe',(x0,-.0104,-.00298),(x1,.0104,.00004))
  # Recess for the real 4.6 mm wide transverse lug on the source thermal clamp.
  pocket=box('Recoil lug pocket',(-.0024,-.0102,-.00194),(.0024,.0102,.0005));boolean(pad,pocket,'DIFFERENCE')
  jaw0,jaw1=-.021,.021;top=-.00346
 finish(pad);parts=[pad]
 for side in [-1,1]:
  section=[(side*y,z) for y,z in [(.01055,-.0047),(.01055,-.00605),(.0120,-.0070),(.0144,-.0062),(.0144,top),(.0120,top)]]
  if side<0:section.reverse()
  jaw=extrude('Lower rail clamp jaw',section,jaw0,jaw1);finish(jaw);parts.append(jaw)
  for x in [jaw0+.006,jaw1-.006]:
   # A transverse fastener head; author in its final local frame.
   bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.0016,depth=.0010,location=(x,side*.0147,-.0050),rotation=(math.pi/2,0,0))
   bolt=bpy.context.object;bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);finish(bolt);parts.append(bolt)
 return parts
for key in ['eoth_holographic','thermal_scope']:
 bpy.ops.wm.open_mainfile(filepath=str(W/(key+'.blend')),use_scripts=False);bpy.context.preferences.filepaths.save_version=0
 o=bpy.data.objects[key];me=o.data;row=C['assets'][key]
 for other in list(bpy.context.scene.objects):
  if other!=o:bpy.data.objects.remove(other,do_unlink=True)
 shift=Vector((-.034,0,0)) if key=='eoth_holographic' else Vector((0,0,0))
 vs=[tuple(v.co+shift) for v in me.vertices];fs=[tuple(f.vertices) for f in me.polygons];mids=[f.material_index for f in me.polygons];norms=[tuple(n.vector) for n in me.corner_normals]
 uvs=[[tuple(v.uv) for v in layer.data] for layer in me.uv_layers]
 while len(uvs)<4:uvs.append(uvs[0].copy())
 colors={a.name:{'domain':a.domain,'values':[tuple(v.color) for v in a.data]} for a in me.color_attributes}
 body_faces=len(fs);body_vertices=len(vs);body_loops=len(norms);parts=support(key);interface=len(me.materials)
 for part in parts:
  pm=part.data;off=len(vs);vs.extend(tuple(v.co) for v in pm.vertices);fs.extend(tuple(off+v for v in f.vertices) for f in pm.polygons);mids.extend([interface]*len(pm.polygons));norms.extend(tuple(n.vector) for n in pm.corner_normals)
  for f in pm.polygons:
   axes=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(f.normal[k]))]
   for li in f.loop_indices:
    p=pm.vertices[pm.loops[li].vertex_index].co;value=(p[axes[0]]/.04+.5,p[axes[1]]/.04+.5)
    for layer in uvs:layer.append(value)
 combined=bpy.data.meshes.new('ASH optic fitted assembly');combined.from_pydata(vs,[],fs);combined.update()
 for mat in me.materials:combined.materials.append(mat)
 combined.materials.append(bpy.data.materials.new('ASH_OpticShoe'))
 for face,mid in zip(combined.polygons,mids):face.material_index=mid;face.use_smooth=True
 for i,values in enumerate(uvs):
  layer=combined.uv_layers.new(name='UV'+str(i))
  for loop,value in zip(layer.data,values):loop.uv=value
 for name,spec in colors.items():
  attr=combined.color_attributes.new(name=name,type='FLOAT_COLOR',domain=spec['domain'])
  for i,v in enumerate(attr.data):v.color=spec['values'][i] if i<len(spec['values']) else (1,1,1,1)
 combined.normals_split_custom_set(norms);o.data=combined
 for i,name in enumerate([s['name'] for s in row['slots']]+['ASH_OpticShoe']):
  mat=combined.materials[i];other=bpy.data.materials.get(name)
  if other and other!=mat:other.name='UnusedImported_'+name
  mat.name=name
 for part in parts:bpy.data.objects.remove(part,do_unlink=True)
 active(o);fbx=X/('SM_ASH12_'+key+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,add_leaf_bones=False,mesh_smooth_type='FACE')
 bpy.ops.wm.save_as_mainfile(filepath=str(X/(key+'_Editable.blend')))
 sockets=json.loads(json.dumps(row['sockets']))
 for spec in sockets.values():spec['location']=[spec['location'][0]+shift.x*100,spec['location'][1],spec['location'][2]]
 ue_points=np.asarray(vs)*[100,-100,100]
 bounds=[list(ue_points.min(0)),list(ue_points.max(0))]
 R['assets'][key]={'fbx':str(fbx),'source':row['path'],'target':'/Game/Weapons/ASH12/UniversalAttachments20260919/Meshes/SM_ASH12_'+key,'shift_m':list(shift),'sockets':sockets,'slots':row['slots']+[{'name':'ASH_OpticShoe','material':shoe_material}],'body_faces_retained':body_faces,'adapter_faces':len(fs)-body_faces,'bounds_cm':bounds}
 print('ASH_OPTIC_AUTHORED',key,'body',body_faces,'adapter',len(fs)-body_faces,flush=True)
R['complete']=True;(O/'production.json').write_text(json.dumps(R,indent=2))
