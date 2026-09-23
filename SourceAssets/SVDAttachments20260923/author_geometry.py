"""Create SVD-specific interfaces, keeping donor UV0, normals and contact shapes."""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
O=Path(__file__).parent;D=O/'Exports';D.mkdir(exist_ok=True)
src=json.loads((O/'sources.json').read_text());inputs=json.loads((O/'geometry_inputs.json').read_text())
bpy.context.preferences.filepaths.save_version=0
report={'meshes':{},'tested':False,'frame':'metres, SVD WPN_root rest, -Y forward +Z up'}
def select(obs):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in obs:ob.hide_set(False);ob.select_set(True)
 bpy.context.view_layer.objects.active=obs[0]
def export(obs,name,rig=False):
 select(obs);bpy.ops.export_scene.fbx(filepath=str(D/(name+'.fbx')),use_selection=True,object_types={'MESH','ARMATURE'} if rig else {'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
def material(name):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True
 bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.027,.034,.041,1);bs.inputs['Metallic'].default_value=.84;bs.inputs['Roughness'].default_value=.31
 return m
def finish_uv(ob):
 # UV0/UV1 remain intact. UV2 is only the SVD coating, 5 cm per repeat.
 while len(ob.data.uv_layers)<3:ob.data.uv_layers.new(name='SVD_CoatingUV' if len(ob.data.uv_layers)==2 else 'InterfaceUV')
 uv=ob.data.uv_layers[2]
 for face in ob.data.polygons:
  axis=max(range(3),key=lambda i:abs(face.normal[i]));axes=[i for i in range(3) if i!=axis]
  for li in face.loop_indices:
   p=ob.data.vertices[ob.data.loops[li].vertex_index].co
   uv.data[li].uv=(p[axes[0]]/.05,p[axes[1]]/.05)
 ob.data.uv_layers.active_index=0
def cube(name,loc,size,mat):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);ob=bpy.context.object;ob.name=name;ob.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);ob.data.materials.append(mat)
 mod=ob.modifiers.new('MachinedEdges','BEVEL');mod.width=min(.00065,min(size)*.2);mod.segments=3;bpy.ops.object.modifier_apply(modifier=mod.name)
 mod=ob.modifiers.new('FaceNormals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 mod=ob.modifiers.new('ExportTriangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
 ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4);finish_uv(ob);return ob
def bolt(loc,axis,mat):
 bpy.ops.mesh.primitive_cylinder_add(vertices=12,radius=.0027,depth=.0016,location=loc);ob=bpy.context.object;ob.name='SVD_InterfaceBolt'
 ob.rotation_mode='QUATERNION';ob.rotation_quaternion=Vector((0,0,1)).rotation_difference(Vector(axis));ob.data.materials.append(mat)
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 mod=ob.modifiers.new('RimBevel','BEVEL');mod.width=.00025;mod.segments=2;bpy.ops.object.modifier_apply(modifier=mod.name)
 mod=ob.modifiers.new('ExportTriangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
 ob.data.transform(ob.matrix_world);ob.matrix_world=Matrix.Identity(4);finish_uv(ob);return ob
bpy.ops.wm.open_mainfile(filepath=str(O/'SVD_Modular_Editable.blend'))
r=bpy.data.objects[inputs['rig']];body=bpy.data.objects['SM_SVD_Body'];inv=(r.matrix_world@r.data.bones['WPN_root'].matrix_local).inverted()
points=[inv@body.matrix_world@v.co for v in body.data.vertices]
surface=BVHTree.FromPolygons(points,[tuple(p.vertices) for p in body.data.polygons])
def hit(origin,direction):
 p,n,face,d=surface.ray_cast(Vector(origin),Vector(direction))
 if p is None:raise RuntimeError('No SVD connection surface '+str(origin))
 return p
under=[hit((x,y,-.08),(0,0,1)) for x in [-.006,.006] for y in [-.36,-.31]]
# Donor AKM rail seat Z=.030. Seat below the actual SVD lower shell.
gz=min(p.z for p in under)-.0015-.030;G=Matrix.Translation((-.0007636,-.035,gz))
report['grip_transform']=[list(row) for row in G];report['under_contacts']=[list(p) for p in under]
side=[hit((.09,y,.050),(-1,0,0)) for y in [-.42,-.39]]
sx=max(p.x for p in side)+.0015-.017424142
T=Matrix.Translation((sx,-.095,0));report['tactical_transform']=[list(row) for row in T];report['side_contacts']=[list(p) for p in side]
receiver=[hit((.08,y,z),(-1,0,0)) for y in [-.14,-.08] for z in [.035,.050]]
report['optic_contacts']=[list(p) for p in receiver]
report['optic_mounts']={key:[.0000364,along,.086] for key,along in [('holographic',.035),('panoramic_red_dot',.035),('prism_scope_2x',.030),('lpvo_1_6x',.020)]}
report['muzzle_mount']=[.0000364133,.80120006,.0389192775]
# Select the complete factory flash hider by its actual connected shells.
factory=set()
for row in inputs['islands']:
 lo,hi=row['min'],row['max']
 if hi[1]<-.80118 and (lo[1]<-.808 or abs(lo[1]+.80120006)<.000004):factory.update(row['indices'])
factory_mat=body.data.materials[0].copy();factory_mat.name='SVD_FactoryMuzzle';body.data.materials.append(factory_mat);idx=len(body.data.materials)-1
for face in body.data.polygons:
 if all(i in factory for i in face.vertices):face.material_index=idx
report['factory_muzzle_faces']=sum(f.material_index==idx for f in body.data.polygons)
if not report['factory_muzzle_faces']:raise RuntimeError('No factory muzzle partition')
r.data.pose_position='REST';bpy.context.view_layer.update()
parts=[o for o in bpy.context.scene.objects if o.type=='MESH' and (o.name.startswith('SM_SVD_') or o.name=='SK_Manny_Arms_Export')]
export(parts+[r],'SK_SVD_Modular',True)
report['body_materials']=dict(src['svd']['materials']);report['body_materials']['SVD_FactoryMuzzle']=next(v for k,v in src['svd']['materials'].items() if 'body' in k.lower())
r.data.pose_position='POSE';bpy.context.scene.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVD_Modular_Editable.blend'))

for key,info in src['meshes'].items():
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=info['source'][0])
 obs=[o for o in bpy.context.scene.objects if o.type=='MESH'];bindings={};indices={}
 xf=G if key in ['vertical','tactical_vertical','canted','prism','angled'] else T if key in ['laser','flashlight'] else Matrix.Identity(4)
 for ob in obs:
  ob.data.transform(xf@ob.matrix_world);ob.matrix_world=Matrix.Identity(4)
  for i,m in enumerate(ob.data.materials):
   # Two donor exports retain unused slots: map by identity, not index clamp.
   j=i
   if key=='tactical_vertical':j=0 if i==0 else 1
   if key=='angled':j=0
   label='SVD_'+key+'_'+str(i);m.name=label
   bindings[label]=info['materials'][j]['path'];indices[label]=j
  finish_uv(ob)
 mat=material('SVD_InterfaceSteel');bindings[mat.name]='SVD_STEEL'
 if key in ['vertical','tactical_vertical','canted','prism','angled']:
  for p in under:
   bottom=.030+gz-.001;top=p.z+.0006
   obs.append(cube('SVD_UnderRailContact',(p.x,p.y,(bottom+top)/2),(.008,.011,top-bottom),mat))
  for y in [-.36,-.31]:obs.append(bolt((.0000364,y,.030+gz-.001),(0,0,-1),mat))
 elif key in ['laser','flashlight']:
  for p in side:
   outer=.017424142+sx+.001
   obs.append(cube('SVD_SideRailContact',((p.x+outer)/2,p.y,.050),(outer-p.x+.001,.018,.014),mat))
   obs.append(bolt((outer+.0008,p.y,.050),(1,0,0),mat))
 else:bindings.pop(mat.name)
 sockets={}
 for name,pos in info.get('sockets',{}).items():
  v=xf@Vector((pos[0]/100,-pos[1]/100,pos[2]/100));sockets[name]=[v.x*100,-v.y*100,v.z*100]
 name='SM_SVD_'+key;export(obs,name)
 report['meshes'][key]={'name':name,'materials':bindings,'source_slot_indices':indices,'sockets':sockets,'source':info['asset']}
 bpy.ops.wm.save_as_mainfile(filepath=str(O/(name+'.blend')))
 print('SVD_ATTACH_GEOMETRY',key,flush=True)

# Closed left-side receiver adapter, with a forward rail cantilever over the cover.
bpy.ops.wm.read_factory_settings(use_empty=True);mat=material('SVD_InterfaceSteel');obs=[]
left=max(p.x for p in receiver)+.004
for p in receiver:obs.append(cube('SVD_ReceiverPad',((p.x+left)/2,p.y,p.z),(left-p.x+.001,.018,.012),mat))
obs.append(cube('SVD_SideSpine',(left,-.110,.047),(.007,.096,.030),mat))
for y in [-.14,-.08]:
 obs.append(cube('SVD_RailBridge',(left/2,y,.079),(left+.008,.019,.010),mat))
 obs.append(cube('SVD_RailUpright',(left,y,.064),(.007,.019,.030),mat))
 obs.append(bolt((left+.004,y,.047),(1,0,0),mat))
obs.append(cube('SVD_OpticRailWeb',(.0000364,-.035,.080),(.019,.220,.009),mat))
for n in range(21):obs.append(cube('SVD_OpticRailTooth',(.0000364,-.135+n*.010,.084),(.021,.0055,.004),mat))
name='SM_SVD_optic_bridge';export(obs,name);bpy.ops.wm.save_as_mainfile(filepath=str(O/(name+'.blend')))
report['meshes']['optic_bridge']={'name':name,'materials':{'SVD_InterfaceSteel':'SVD_STEEL'},'source_slot_indices':{},'sockets':{},'source':'SVD receiver raycast contacts / new machined interface'}
(O/'authoring.json').write_text(json.dumps(report,indent=2))
print('SVD_ATTACH_GEOMETRY_COMPLETE',flush=True)
