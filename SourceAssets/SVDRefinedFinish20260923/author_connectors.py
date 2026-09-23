"""Local SVD adapter refinement. Original grip geometry and weapon rig stay intact."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;S=O.parent;D=O/'Exports';D.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
report={'meshes':{},'game_tested':False,'frame':'SVD WPN_root rest metres; -Y forward, +Z up'}

def active(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]

def material(name,color=(.024,.030,.041),rough=.37):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
 bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=.83;bs.inputs['Roughness'].default_value=rough
 return m

def project_uv(ob):
 while len(ob.data.uv_layers)<3:ob.data.uv_layers.new(name=['InterfaceUV','InterfaceUV1','SVD_CoatingUV'][len(ob.data.uv_layers)])
 for face in ob.data.polygons:
  axis=max(range(3),key=lambda i:abs(face.normal[i]));axes=[i for i in range(3) if i!=axis]
  for li in face.loop_indices:
   p=ob.data.vertices[ob.data.loops[li].vertex_index].co
   for layer in ob.data.uv_layers:layer.data[li].uv=(p[axes[0]]/.05,p[axes[1]]/.05)
 ob.data.uv_layers.active_index=0

def finish(ob,bevel=.00025):
 active([ob]);bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
 for p in ob.data.polygons:p.use_smooth=True
 if bevel:
  mod=ob.modifiers.new('SmallMachinedRadius','BEVEL');mod.width=bevel;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=.52;mod.harden_normals=True
  bpy.ops.object.modifier_apply(modifier=mod.name)
 bm=bmesh.new();bm.from_mesh(ob.data)
 for e in bm.edges:e.smooth=e.is_manifold and e.calc_face_angle()<.65
 bm.to_mesh(ob.data);bm.free()
 mod=ob.modifiers.new('WeightedMachinedNormals','WEIGHTED_NORMAL');mod.keep_sharp=True;mod.weight=50
 bpy.ops.object.modifier_apply(modifier=mod.name)
 mod=ob.modifiers.new('ExportTriangles','TRIANGULATE');mod.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4);project_uv(ob);return ob

def mesh(name,verts,faces,mats,indices=None,bevel=.00025):
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob)
 for m in mats:me.materials.append(m)
 if indices:
  for f,i in zip(me.polygons,indices):f.material_index=i
 return finish(ob,bevel)

def extrude(name,profile,axis,lo,hi,mat,bevel=.0003):
 axes=[i for i in range(3) if i!=axis];verts=[]
 for t in [lo,hi]:
  for a,b in profile:
   p=[0,0,0];p[axis]=t;p[axes[0]]=a;p[axes[1]]=b;verts.append(p)
 n=len(profile);faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]
 faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return mesh(name,verts,faces,[mat],bevel=bevel)

def box(name,loc,size,mat,bevel=.0003):
 x,y,z=loc;dx,dy,dz=[v/2 for v in size]
 return extrude(name,[(x-dx,y-dy),(x+dx,y-dy),(x+dx,y+dy),(x-dx,y+dy)],2,z-dz,z+dz,mat,bevel)

def screw(name,base,axis,radius,depth,steel,dark):
 # Continuous closed socket head: outer bevel, real hex recess and inset floor.
 n=48;verts=[];rot=Vector((0,0,1)).rotation_difference(Vector(axis));base=Vector(base)
 def hexr(a,r):
  sector=(a+math.pi/6)%(math.pi/3)-math.pi/6
  return r*math.cos(math.pi/6)/math.cos(sector)
 rings=[(radius*.9,0,False),(radius,.00015,False),(radius,depth-.0002,False),
        (radius-.0002,depth,False),(radius*.47,depth,True),(radius*.40,depth-.00018,True),
        (radius*.40,depth*.30,True)]
 for r,z,h in rings:
  for i in range(n):
   a=2*math.pi*i/n;rr=hexr(a,r) if h else r
   verts.append(tuple(base+rot@Vector((rr*math.cos(a),rr*math.sin(a),z))))
 faces=[tuple(reversed(range(n)))];ids=[0]
 for j in range(len(rings)-1):
  for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i));ids.append(1 if j>=4 else 0)
 faces.append(tuple(range((len(rings)-1)*n,len(rings)*n)));ids.append(1)
 return mesh(name,verts,faces,[steel,dark],ids,bevel=0)

def output(obs,name,key,rig=None):
 active(obs+([rig] if rig else []))
 bpy.ops.export_scene.fbx(filepath=str(D/(name+'.fbx')),use_selection=True,
  object_types={'MESH','ARMATURE'} if rig else {'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,
  bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
 bpy.ops.wm.save_as_mainfile(filepath=str(O/(name+'.blend')))
 report['meshes'][key]={'name':name,'source':str(D/(name+'.fbx')),'skeletal':bool(rig),
  'vertices':sum(len(o.data.vertices) for o in obs),'faces':sum(len(o.data.polygons) for o in obs)}
 (O/'connectors.json').write_text(json.dumps(report,indent=2));print('SVD_CONNECTOR_EXPORTED',key,flush=True)

for key in ['vertical','tactical_vertical','canted','prism','angled']:
 bpy.ops.wm.open_mainfile(filepath=str(S/'SVDAttachments20260923'/('SM_SVD_'+key+'.blend')))
 for ob in list(bpy.context.scene.objects):
  if ob.name.startswith(('SVD_UnderRailContact','SVD_InterfaceBolt')):bpy.data.objects.remove(ob,do_unlink=True)
 donor=[o for o in bpy.context.scene.objects if o.type=='MESH'];steel=material('SVD_InterfaceSteel')
 fast=material('SVD_AdapterFastener',(.052,.059,.066),.29);dark=material('SVD_AdapterRecess',(.012,.015,.02),.43)
 # Same original seating plane; front/back corner relief and uninterrupted support.
 x=.0000364;profile=[(x-.006,-.368),(x+.006,-.368),(x+.008,-.366),(x+.008,-.304),
                    (x+.006,-.302),(x-.006,-.302),(x-.008,-.304),(x-.008,-.366)]
 added=[extrude('SVD_ContinuousUnderSaddle',profile,2,.011830178,.01470,steel,.00025)]
 # Small contact shoulders, not a second stand-off or a change of grip position.
 for side in [-1,1]:
  added.append(box('SVD_ClampLip',(x+side*.0073,-.335,.0119),(.0014,.057,.002),steel,.0002))
 for y in [-.36,-.31]:added.append(screw('SVD_RecessedUnderFastener',(x,y,.01175),(0,0,-1),.0027,.0015,fast,dark))
 output(donor+added,'SM_SVD_'+key,key)
 report['meshes'][key]['preserved']='All donor grip vertices, UVs, normals and origin; only old interface blocks and bolts replaced'

# Modern optic side bridge: contact seats and rail crown remain at original coordinates.
bpy.ops.wm.read_factory_settings(use_empty=True)
steel=material('SVD_InterfaceSteel');fast=material('SVD_AdapterFastener',(.052,.059,.066),.29);dark=material('SVD_AdapterRecess',(.012,.015,.02),.43)
old=json.loads((S/'SVDAttachments20260923/authoring.json').read_text());contacts=old['optic_contacts'];left=max(p[0] for p in contacts)+.004
obs=[]
for x,y,z in contacts:
 obs.append(box('SVD_FittedReceiverSeat',((x+left)/2,y,z),(left-x+.001,.018,.012),steel,.0005))
outline=[(-.158,.039),(-.151,.032),(-.069,.032),(-.062,.039),(-.062,.055),(-.069,.062),(-.151,.062),(-.158,.055)]
obs.append(extrude('SVD_ChamferedSidePlate',outline,0,left-.0035,left+.0035,steel,.0006))
for y in [-.14,-.08]:
 # One continuous bent support profile in XZ, relieved with an angled inner transition.
 profile=[(left-.0035,.049),(left+.0035,.049),(left+.0035,.082),(.003,.084),(-.004,.083),
          (-.004,.0755),(.010,.0755),(left-.0035,.066)]
 obs.append(extrude('SVD_TaperedBridgeRib',profile,1,y-.0095,y+.0095,steel,.00055))
 obs.append(screw('SVD_RecessedSideFastener',(left+.0033,y,.047),(1,0,0),.0033,.0018,fast,dark))
 # A fine bedding washer perimeter remains visible around the screw.
 for z in [.037,.057]:
  obs.append(box('SVD_SidePlateEndDetail',(left+.0036,y,z),(.0006,.010,.001),steel,.00012))
x=.0000364
railprofile=[(x-.007,.0755),(x+.007,.0755),(x+.0095,.078),(x+.0095,.0824),
             (x-.0095,.0824),(x-.0095,.078)]
obs.append(extrude('SVD_ProfiledRailSpine',railprofile,1,-.145,.075,steel,.00035))
tooth=[(x-.008,.082),(x+.008,.082),(x+.0105,.0842),(x+.0095,.086),
       (x-.0095,.086),(x-.0105,.0842)]
for n in range(21):
 y=-.135+n*.010;obs.append(extrude('SVD_DovetailRailCrown',tooth,1,y-.00275,y+.00275,steel,.00016))
output(obs,'SM_SVD_optic_bridge','optic_bridge')
report['meshes']['optic_bridge']['preserved']='Receiver contact coordinates; rail crown Z=0.086 m and original pitch, span and origin'

# Factory PSO mount: retain original shell and glass seam repair, enrich its four real fasteners.
bpy.ops.wm.open_mainfile(filepath=str(S/'SVDStockAdapter20260923/SVD_StockModular_Editable.blend'))
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE' and 'WPN_root' in o.data.bones)
rig.data.pose_position='REST';bpy.context.view_layer.update()
fast=material('SVD_ScopeMountFastener',(.052,.059,.066),.29);dark=material('SVD_ScopeMountRecess',(.012,.015,.02),.43)
root=rig.matrix_world@rig.data.bones['WPN_root'].matrix_local
for y in [-.10712339,-.03428912]:
 for z in [.02655261,.01891337]:
  ob=screw('SM_SVD_ScopeMountSocketHead',(.02512,y,z),(1,0,0),.00310,.00135,fast,dark)
  # Root-space addition bound to WPN_root, same rest frame as all original rigid parts.
  ob.data.transform(rig.matrix_world.inverted()@root);ob.parent=rig;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
  vg=ob.vertex_groups.new(name='WPN_root');vg.add(list(range(len(ob.data.vertices))),1.,'REPLACE')
  mod=ob.modifiers.new('SVDExistingRig','ARMATURE');mod.object=rig
parts=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name.startswith('SM_SVD_') or o.name=='SK_Manny_Arms_Export')]
output(parts,'SK_SVD_ModularStock','viewmodel',rig)
report['meshes']['viewmodel']['preserved']='Original arm and weapon meshes, rig, weights, UVs and PSO glass; four mount socket-head additions only; no animations exported'
(O/'connectors.json').write_text(json.dumps(report,indent=2))
print('SVD_CONNECTORS_AUTHORING_COMPLETE',flush=True)
