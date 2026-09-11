import bpy,json,math
from pathlib import Path
from mathutils import Matrix,Vector
O=Path(__file__).parent;bounds=json.loads((O/'bounds.json').read_text());report={}
mounts={'panoramic_red_dot':(.06,.06,.072),'prism_scope_2x':(.105,.105,.070),'lpvo_1_6x':(.16,.146,.084)}
for key,(mount_y,center,length) in mounts.items():
 bpy.ops.wm.open_mainfile(filepath=str(O.parent/'AKMArmSupport20260911/AKM_OpticMount_Editable.blend'))
 s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];a=bpy.data.actions['AKM_Native_idle'];r.animation_data.action=a;r.animation_data.action_slot=a.slots[0];s.frame_set(0);bpy.context.view_layer.update()
 root=r.matrix_world@r.pose.bones['WPN_root'].matrix;mat=next(m for m in bpy.data.materials if m.name=='AKM_Soviet_MountSteel');parts=[]
 def bevel(o,width=.0005):
  bpy.context.view_layer.objects.active=o
  b=o.modifiers.new('Machined edge radius','BEVEL');b.width=width;b.segments=3
  bpy.ops.object.modifier_apply(modifier=b.name)
 def box(name,loc,size,edge=.0005):
  bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.scale=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(mat);bevel(o,edge);parts.append(o);return o
 def prism(name,points,axis,lo,hi):
  axes=[i for i in range(3) if i!=axis];verts=[]
  for v in (lo,hi):
   for pt in points:
    co=[0,0,0];co[axis]=v;co[axes[0]]=pt[0];co[axes[1]]=pt[1];verts.append(co)
  n=len(points);faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
  me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new(name,me);s.collection.objects.link(o);o.data.materials.append(mat);parts.append(o)
  bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
  bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
  return o
 # A thin rail carried by an open side bracket, with tapered ends.
 y0=-center-length/2;y1=-center+length/2
 deck=prism('Tapered rail carrier',[(-.0152,y0+.005),(-.0112,y0),(.0128,y0),(.0168,y0+.005),(.0168,y1-.005),(.0128,y1),(-.0112,y1),(-.0152,y1-.005)],2,.104,.109)
 bevel(deck,.00065)
 # Independent rail ridges leave visible recoil grooves; top height stays 113 mm.
 count=int((length-.004)/.010)
 for i in range(count):
  y=-center+(i-(count-1)/2)*.010
  tooth=prism('Recoil rail ridge',[(-.0102,.109),(-.0112,.111),(-.0097,.113),(.0113,.113),(.0128,.111),(.0118,.109)],1,y-.0028,y+.0028);bevel(tooth,.00018)
 # Left receiver clamp: chamfered profile and a genuine through window.
 plate=prism('Windowed side bracket',[(y0+.004,.066),(y1-.004,.066),(y1,.071),(y1-.006,.098),(y1-.013,.105),(y0+.013,.105),(y0+.006,.098),(y0,.071)],0,-.024,-.019)
 cutter=box('Window cutter',(-.0215,-center,.0845),(.016,length-.031,.018),.003)
 bpy.context.view_layer.objects.active=plate
 mod=plate.modifiers.new('Through lightening window','BOOLEAN');mod.operation='DIFFERENCE';mod.object=cutter;bpy.ops.object.modifier_apply(modifier=mod.name)
 parts.remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True);bevel(plate,.0006)
 box('Receiver clamp shoe',(-.0198,-center,.069),(.007,length-.009,.007),.0007)
 for sign in (-1,1):
  y=-center+sign*(length/2-.012)
  arm=prism('Swept bridge shoulder',[(-.022,.094),(-.022,.105),(-.013,.109),(.012,.109),(.012,.104),(-.010,.104)],1,y-.004,y+.004);bevel(arm,.0007)
  # Socket-head hardware on the outward face, recessed hex sockets.
  bpy.ops.mesh.primitive_cylinder_add(vertices=24,radius=.0032,depth=.0022,location=(-.025,-center+sign*(length/2-.010),.072),rotation=(0,math.pi/2,0))
  screw=bpy.context.object;screw.name='Clamp socket screw';screw.data.materials.append(mat);parts.append(screw);bevel(screw,.00025)
  bpy.ops.mesh.primitive_cylinder_add(vertices=6,radius=.0014,depth=.002,location=(-.0263,-center+sign*(length/2-.010),.072),rotation=(0,math.pi/2,0))
  cut=bpy.context.object;bpy.context.view_layer.objects.active=screw;mod=screw.modifiers.new('Hex socket','BOOLEAN');mod.object=cut;mod.operation='DIFFERENCE';bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
 bpy.ops.object.select_all(action='DESELECT')
 for o in parts:o.hide_set(False);o.select_set(True)
 bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();bridge=parts[0];bridge.name='SM_AKM_Mount_'+key
 # The source's positive-X receiver face is opposite the selector/ejection side.
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 for v in bridge.data.vertices:v.co.x=.0016-v.co.x
 bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.mesh.normals_make_consistent(inside=False);bpy.ops.object.mode_set(mode='OBJECT')
 if bridge.data.uv_layers.active is None:bridge.data.uv_layers.new(name='UVMap')
 for p in bridge.data.polygons:
  axes=[1,2] if abs(p.normal.x)>.7 else [1,0] if abs(p.normal.z)>.7 else [0,2]
  for li in p.loop_indices:
   v=bridge.matrix_world@bridge.data.vertices[bridge.data.loops[li].vertex_index].co;bridge.data.uv_layers.active.data[li].uv=(v[axes[0]]/.12+.5,v[axes[1]]/.025+.5)
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
 bpy.ops.export_scene.fbx(filepath=str(O/(bridge.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False)
 # Assemble the actual retained optic against the AKM for source inspection.
 bridge.matrix_world=root
 for ob in s.objects:
  if ob.type=='MESH' and ob!=bridge:ob.hide_render=ob.name not in ['AKM_Soviet_Native','AKM_FactoryMagazine_Preview']
 before=set(s.objects);bpy.ops.import_scene.fbx(filepath=bounds[key]['source']);optic=[o for o in s.objects if o not in before and o.type=='MESH']
 for o in optic:o.matrix_world=root@Matrix.Translation((.0008,-mount_y,.113))@Matrix.Rotation(-math.pi/2,4,'Z')@o.matrix_world
 bpy.ops.wm.save_as_mainfile(filepath=str(O/(key+'_AKM_Editable.blend')))
 s.render.engine='BLENDER_WORKBENCH';s.display.shading.color_type='MATERIAL';s.display.shading.show_cavity=True;s.render.resolution_x=1100;s.render.resolution_y=700;s.render.resolution_percentage=100
 d=bpy.data.cameras.new('MountReview');c=bpy.data.objects.new('MountReview',d);s.collection.objects.link(c);s.camera=c;d.type='ORTHO';d.ortho_scale=.25;t=root@Vector((0,-center,.083));c.location=t+Vector((-.7,-.15,.24));c.rotation_euler=(t-c.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(O/(key+'_mount.png'));bpy.ops.render.render(write_still=True)
 foot=bounds[key];assert foot['foot_lo'][0]+mount_y>=center-length/2-.0001 and foot['foot_hi'][0]+mount_y<=center+length/2+.0001
 report[key]={'mount_in_root_m':[.0008,mount_y,.113],'optic_scale':1,'bridge_center_y_m':center,'bridge_length_m':length,'mount_footprint_supported':True,'triangles':sum(len(p.vertices)-2 for p in bridge.data.polygons)}
(O/'mounts.json').write_text(json.dumps(report,indent=2));print('AKM_OPTIC_MOUNTS_PASS')
