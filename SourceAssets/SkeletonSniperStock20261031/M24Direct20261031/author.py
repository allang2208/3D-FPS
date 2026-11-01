"""M24 direct receiver/stock joint with a separate, contact-preserving grip."""
import bpy,bmesh,json,gzip,math,shutil
import numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).resolve().parent;S=O.parent
(O/'Exports').mkdir(exist_ok=True);(O/'Reference').mkdir(exist_ok=True)
ref=Path('C:/Users/allan/AppData/Local/Temp/codex-clipboard-dfd82889-cbc1-43ce-a5d2-9dffcd665982.png')
if ref.exists():shutil.copy2(ref,O/'Reference/user_reference.png')
bpy.ops.wm.open_mainfile(filepath=str(S/'SkeletonSniperStock_M24_Editable.blend'),load_ui=False,use_scripts=False)
stock=bpy.data.objects['SniperSkeleton_M24']
for im in bpy.data.images:
 if im.source=='FILE' and im.filepath:im.filepath=bpy.path.abspath(im.filepath)
for ob in list(bpy.data.objects):
 if ob!=stock:bpy.data.objects.remove(ob,do_unlink=True)
stock.name='M24_DirectStock_Meshy'
old_front=Vector((0,-.125,.039));old_back=Vector((0,-.3603858947753906,.029875358566641808))
new_front=Vector((0,-.075,.088));new_back=Vector((0,-.3603858947753906,.048))
scale=(new_back-new_front).length/(old_back-old_front).length
rotation=(old_back-old_front).rotation_difference(new_back-new_front)
fit=Matrix.Translation(new_front)@rotation.to_matrix().to_4x4()@Matrix.Scale(scale,4)@Matrix.Translation(-old_front)
stock.data.transform(fit)
parts=[stock]
def mat(name,c,metal,r):
 m=bpy.data.materials.get(name) or bpy.data.materials.new(name);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 p.inputs['Base Color'].default_value=(*c,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=r;return m
metal=mat('SniperStock_Interface',(.026,.029,.031),1,.36)
polymer=mat('M24_IndependentGrip',(.017,.018,.018),0,.56)
def finish(ob,ma,bevel=.0005):
 ob.data.materials.clear();ob.data.materials.append(ma)
 for p in ob.data.polygons:p.use_smooth=True
 if bevel:
  mod=ob.modifiers.new('Machined edge radii','BEVEL');mod.width=bevel;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=.45
 mod=ob.modifiers.new('Planar normal weighting','WEIGHTED_NORMAL');mod.keep_sharp=True
 bpy.context.view_layer.objects.active=ob
 for mod in list(ob.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
 uv=ob.data.uv_layers.new(name='PhysicalUV')
 for p in ob.data.polygons:
  axes=sorted(range(3),key=lambda a:abs(p.normal[a]))[:2]
  for li in p.loop_indices:
   co=ob.data.vertices[ob.data.loops[li].vertex_index].co;uv.data[li].uv=(co[axes[0]]*20,co[axes[1]]*20)
 return ob
def mesh(name,v,f,ma,bevel=.0005):
 me=bpy.data.meshes.new(name);me.from_pydata(v,[],f);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 ob=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(ob);return finish(ob,ma,bevel)
# Short machined receiver tail. No original stock wrist or triangular adapter.
# End section embraces the Meshy hinge nose; the forward section overlaps the
# existing receiver bedding at its real native/advanced-chassis boundary.
rings=[(.040,.024,.055,.104),(.020,.025,.064,.101),(-.015,.025,.067,.098),(-.045,.022,.069,.103),(-.069,.013,.065,.110),(-.079,.010,.065,.110)]
verts=[]
for y,w,lo,hi in rings:
 c=.002
 verts += [(-w+c,y,lo),(w-c,y,lo),(w,y,lo+c),(w,y,hi-c),(w-c,y,hi),(-w+c,y,hi),(-w,y,hi-c),(-w,y,lo+c)]
faces=[tuple(range(7,-1,-1)),tuple(range(8*(len(rings)-1),8*len(rings)))]
for i in range(len(rings)-1):
 for j in range(8):faces.append((i*8+j,i*8+(j+1)%8,(i+1)*8+(j+1)%8,(i+1)*8+j))
tail=mesh('M24_MachinedReceiverTail',verts,faces,metal,.00055);parts.append(tail)
def cylinder(name,pos,r,depth,axis,ma,vertices=48):
 rot={'X':(0,math.pi/2,0),'Y':(math.pi/2,0,0),'Z':(0,0,0)}[axis]
 bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r,depth=depth,location=pos,rotation=rot)
 ob=bpy.context.object;ob.name=name;bpy.ops.object.transform_apply(location=False,rotation=True,scale=True);return finish(ob,ma,.00016)
# Recessed fastener details, separated from the hand-contact area and bolt path.
for sign in (-1,1):
 for y,z,x in ((.027,.080,.0252),(-.056,.086,.0186)):
  screw=cylinder('Receiver tail retaining screw',(sign*x,y,z),.0025,.0007,'X',metal);parts.append(screw)
  tool=cylinder('Hex recess tool',(sign*(x+.00025),y,z),.00125,.0013,'X',metal,6)
  bpy.context.view_layer.objects.active=screw;mod=screw.modifiers.new('Socket recess','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=tool;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(tool,do_unlink=True)
# Take the saved native contact surface, remove the broad stock-tail flare,
# close its cuts, and retain its trigger-facing and lateral hand surfaces.
host=json.load(gzip.open(S/'Review20261031/saved_geometry.json.gz','rt'))['M24']['host']
hv=np.array(host['positions'])*[.01,-.01,.01];hf=np.array(host['triangles']);hi=np.array(host['material_ids'])
slot=next(i for i,m in enumerate(host['materials']) if m['slot']=='M24_FactoryChassis')
me=bpy.data.meshes.new('Native M24 grip contact shell');me.from_pydata(hv.tolist(),[],hf[hi==slot].tolist());me.update()
bm=bmesh.new();bm.from_mesh(me);bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000002)
for p,n in [((0,-.066,0),(0,-1,.075)),((0,0,.0865),(0,0,1))]:
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=p,plane_no=n,dist=.000001,clear_outer=True)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bmesh.ops.holes_fill(bm,edges=[e for e in bm.edges if e.is_boundary],sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
grip=bpy.data.objects.new('M24_IndependentGrip',me);bpy.context.collection.objects.link(grip);finish(grip,polymer,.00065)
# Same physical UV convention as existing M24 rear-grip material variants.
for p in grip.data.polygons:
 coords=[grip.data.vertices[grip.data.loops[li].vertex_index].co for li in p.loop_indices]
 around=[math.atan2(v.x,v.z-.035)/(2*math.pi) for v in coords]
 if max(around)-min(around)>.5:around=[a+1 if a<0 else a for a in around]
 for li,v,a in zip(p.loop_indices,coords,around):
  grip.data.uv_layers.active.data[li].uv=((v.y-.23*v.z)/.08,a*1.7)
def export(name,objects):
 bpy.ops.object.select_all(action='DESELECT')
 for ob in objects:
  ob.hide_set(False);ob.select_set(True)
  if ob!=stock:
   bpy.context.view_layer.objects.active=ob
   mod=ob.modifiers.new('Export cap triangulation','TRIANGULATE')
   if hasattr(mod,'keep_custom_normals'):mod.keep_custom_normals=True
   bpy.ops.object.modifier_apply(modifier=mod.name)
 bpy.context.view_layer.objects.active=objects[0]
 f=O/'Exports'/(name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(f),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 return str(f)
exports={'stock':export('SM_M24_DirectSkeletonStock',parts),'grip':export('SM_M24_IndependentGrip',[grip])}
# Retained gun geometry in the authoring scene, excluded from both exports.
keep=hf[~np.isin(hi,[0,1,4,6])]
native=mesh('Retained_M24_reference_only',hv.tolist(),keep.tolist(),metal,0)
for ob in [native]:ob.hide_set(True);ob.hide_render=True
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(O/'M24_DirectStock_Editable.blend'))
(O/'authoring.json').write_text(json.dumps({'exports':exports,'stock_uniform_scale_from_previous':scale,'stock_front_old':list(old_front),'stock_front_new':list(new_front),'shoulder_contact_target':list(new_back),'native_hidden_slots':['M24_FactoryStock','M24_FactoryChassis'],'new_grip_separate':True,'grip_contact_basis':'native front and lateral surface retained; rear flare and top bedding recut','arms_or_animation_changed':False,'source_frame':'M24 author metres, FBX -Y/Z'},indent=2))
print('M24_DIRECT_STOCK_AUTHORED',flush=True)
