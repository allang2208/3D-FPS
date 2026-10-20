"""Photo-derived SVCh folding irons for a GAME asset, fitted to its existing rail.
Exterior approximation, not factory CAD. No functional manufacturing output.
"""
import bpy, bmesh, json, math
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix
O=Path(__file__).parent
BASE=O.parent/'SightsR2'
bpy.ops.wm.open_mainfile(filepath=str(BASE/'SVCH_SightsR2_ElbowFit_Editable.blend'),load_ui=False)
bpy.context.preferences.filepaths.save_version=0
rig=bpy.data.objects['SK_M4_Infima'];rig.data.pose_position='REST'
rig.animation_data_clear()
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
for name in ['SVCH_Detailed_rear','SVCH_Detailed_front']:
 bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
old=bpy.data.materials.get('SVCH_New_FactorySights')
if old:old.name='Retired_HK_SightMaterial'
mat=bpy.data.materials.new('SVCH_New_FactorySights');mat.use_nodes=True
n=mat.node_tree.nodes;lk=mat.node_tree.links;n.clear();bs=n.new('ShaderNodeBsdfPrincipled');out=n.new('ShaderNodeOutputMaterial');lk.new(bs.outputs[0],out.inputs['Surface'])
vc=n.new('ShaderNodeVertexColor');vc.layer_name='SightFinish'
lk.new(vc.outputs['Color'],bs.inputs['Base Color']);lk.new(vc.outputs['Alpha'],bs.inputs['Roughness'])
bs.inputs['Metallic'].default_value=.65
noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=4200;noise.inputs['Detail'].default_value=2
geo=n.new('ShaderNodeNewGeometry');lk.new(geo.outputs['Position'],noise.inputs['Vector'])
bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.08;bump.inputs['Distance'].default_value=.000006
lk.new(noise.outputs['Fac'],bump.inputs['Height']);lk.new(bump.outputs[0],bs.inputs['Normal'])
coat=(.028,.033,.037,.43);steel=(.055,.061,.065,.34);dark=(.012,.014,.016,.5);mark=(.31,.32,.30,.5)
allparts=[];parts=[]
def finish(ob,name,color=coat):
 ob.name=name;ob.data.materials.clear();ob.data.materials.append(mat)
 ca=ob.data.color_attributes.new(name='SightFinish',type='FLOAT_COLOR',domain='CORNER')
 for e in ca.data:e.color=color
 for p in ob.data.polygons:p.use_smooth=True
 parts.append(ob);allparts.append(ob);return ob
def bevel(ob,width=.03,segments=4):
 bpy.context.view_layer.objects.active=ob
 m=ob.modifiers.new('Machined edge radii','BEVEL');m.width=width;m.segments=segments;m.limit_method='ANGLE'
 bpy.ops.object.modifier_apply(modifier=m.name)
 for p in ob.data.polygons:p.use_smooth=True
 m=ob.modifiers.new('Face weighted normals','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=50
 bpy.ops.object.modifier_apply(modifier=m.name)
 return ob
def cube(name,loc,size,width=.03,color=coat):
 bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.dimensions=size
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 bevel(o,width);return finish(o,name,color)
def cylinder(name,loc,r,depth,axis='X',color=steel,segments=96,width=.015):
 bpy.ops.mesh.primitive_cylinder_add(vertices=segments,radius=r,depth=depth,location=loc)
 o=bpy.context.object
 if axis=='X':o.rotation_euler[1]=math.pi/2
 elif axis=='Y':o.rotation_euler[0]=math.pi/2
 bpy.ops.object.transform_apply(location=False,rotation=True,scale=True)
 bevel(o,width,3);return finish(o,name,color)
def prism(name,profile,axis,low,high,width=.03,color=coat):
 # Extrude a 2D exterior polygon along X, Y or Z; dimensions are game cm.
 def pos(a,b,h):return (h,a,b) if axis=='X' else (a,h,b) if axis=='Y' else (a,b,h)
 verts=[pos(a,b,h) for h in [low,high] for a,b in profile];N=len(profile)
 faces=[tuple(range(N-1,-1,-1)),tuple(range(N,2*N))]
 faces += [(i,(i+1)%N,(i+1)%N+N,i+N) for i in range(N)]
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o)
 bevel(o,width);return finish(o,name,color)
def tube(name,loc,outer,inner,depth,color=coat):
 # Closed, bevelled annulus along the sight axis Y, with true visible thickness.
 N=128;verts=[]
 for y,r in [(-depth/2,outer),(depth/2,outer),(-depth/2,inner),(depth/2,inner)]:
  verts += [(loc[0]+r*math.cos(i*2*math.pi/N),loc[1]+y,loc[2]+r*math.sin(i*2*math.pi/N)) for i in range(N)]
 faces=[]
 for i in range(N):
  j=(i+1)%N
  faces.extend([(i,j,j+N,i+N),(i+2*N,i+3*N,j+3*N,j+2*N),(i,i+2*N,j+2*N,j),(i+N,j+N,j+3*N,i+3*N)])
 me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);bevel(o,.018,4);return finish(o,name,color)
def cut(ob,cutter):
 bpy.context.view_layer.objects.active=ob;m=ob.modifiers.new('Machined recess','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter
 bpy.ops.object.modifier_apply(modifier=m.name);bpy.data.objects.remove(cutter,do_unlink=True)
def screw(name,x,y,z,r=.2):
 o=cylinder(name,(x,y,z),r,.10,'X',steel,96,.012)
 # An actual recessed screwdriver slot, not a black line over a flat cylinder.
 bpy.ops.mesh.primitive_cube_add(size=1,location=(x+(.048 if x>0 else -.048),y,z));c=bpy.context.object;c.dimensions=(.065,r*1.55,.047)
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);cut(o,c)
 # Boolean creates loops: rebuild the finish attribute with the screw finish.
 ca=o.data.color_attributes['SightFinish']
 for e in ca.data:e.color=steel
 bevel(o,.006,3)
 return o
rail_z=-.198285;center_x=6.07
# Last normal receiver slot and front handguard slot, measured from this asset.
mounts={'rear':-15.982,'front':-61.945}
for label,slot_y in mounts.items():
 parts=[]
 # x = transverse; y = muzzle-forward. This cavity follows the existing rail.
 cube(label+'_saddle_bridge',(0,0,.13),(2.17,2.62,.26),.045)
 jaw=[(.79,.015),(1.035,-.235),(.955,-.405),(.835,-.555),(1.18,-.555),(1.30,-.35),(1.30,.20),(1.05,.27)]
 prism(label+'_fixed_rail_jaw',[(-x,z) for x,z in reversed(jaw)],'Y',-1.28,1.28,.025)
 prism(label+'_moving_rail_jaw',jaw,'Y',-1.26,1.26,.025)
 # Short visual recoil key sits in the existing groove, below the saddle.
 cube(label+'_slot_key',(0,0,-.12),(1.82,.29,.23),.018,steel)
 cylinder(label+'_clamp_crossbolt',(0,0,-.105),.125,2.52,'X',dark,64,.01)
 screw(label+'_clamp_head',1.36,0,-.105,.235)
 screw(label+'_clamp_end',-1.315,0,-.105,.185)
 # Flat base and pivot side-cheeks, derived from the real side silhouette.
 cube(label+'_base_plinth',(0,0,.32),(1.82,2.34,.21),.06)
 cheek=[(-.95,.39),(.93,.39),(.93,.62),(.43,1.22),(-.24,1.22),(-.64,.94)]
 prism(label+'_left_hinge_cheek',cheek,'X',-.82,-.60,.055)
 prism(label+'_right_hinge_cheek',cheek,'X',.60,.82,.055)
 cylinder(label+'_fold_axis',(0,.12,.89),.34,1.78,'X',steel,128,.028)
 screw(label+'_axis_cap_L',-.925,.12,.89,.295)
 screw(label+'_axis_cap_R',.925,.12,.89,.295)
 cylinder(label+'_detent_button',(-.925,-.51,.62),.15,.12,'X',dark,80,.018)
 # Foldable slim stalk. The joint is represented in the geometry; no new animation.
 stem=[(-.42,.91),(.44,.91),(.38,1.50),(.24,2.78),(-.24,2.78),(-.40,1.52)]
 prism(label+'_folding_stalk',stem,'Y',-.18,.28,.055)
 cube(label+'_stalk_back_rib',(0,-.208,1.95),(.30,.095,1.29),.035,steel)
 if label=='front':
  tube('front_circular_protective_hood',(0,.10,3.10),.64,.485,.76,coat)
  # Fine central post and visible adjustment collar under the hood.
  cylinder('front_elevation_socket',(0,.10,2.68),.235,.29,'Z',steel,96,.018)
  cylinder('front_post_thread_base',(0,.10,2.85),.115,.24,'Z',dark,64,.009)
  cube('front_sight_post',(0,.10,2.99),(.105,.145,.22),.008,coat)
  # Post top at 3.10 cm above the rail, matching the rear aperture center.
  for j in range(16):
   a=2*math.pi*j/16
   o=cube('front_adjustment_flute_%02d'%j,(.235*math.cos(a),.10+.235*math.sin(a),2.68),(.045,.028,.15),.007,dark)
   o.rotation_euler[2]=a
  eye_y=.10
 else:
  # A narrow leaf/diopter on a folding stalk, not a rotating HK drum.
  tube('rear_diopter_leaf',(0,-.10,3.10),.31,.135,.22,coat)
  prism('rear_leaf_neck',[(-.22,2.65),(.22,2.65),(.23,2.94),(-.23,2.94)],'Y',-.205,.005,.035)
  # Height carriage and small transverse adjustment wheel seen in side photos.
  cube('rear_height_carriage',(0,.03,2.40),(.83,.65,.46),.055)
  cylinder('rear_adjustment_hub',(.53,.03,2.40),.275,.23,'X',steel,128,.022)
  for j in range(32):
   a=j*2*math.pi/32
   o=cube('rear_dial_grip_%02d'%j,(.53,.03+.27*math.cos(a),2.40+.27*math.sin(a)),(.18,.032,.030),.008,steel)
   o.rotation_euler[0]=a
  screw('rear_windage_center',.675,.03,2.40,.155)
  # Subtle reference ticks only; do not invent legible range markings.
  for j in range(4):cube('rear_scale_tick_%d'%j,(-.20+j*.13,-.306,2.42),(.009,.012,.11 if j==0 else .055),.002,mark)
  eye_y=-.10
 # Objects are authored in cm, baked to the exact existing world/rig basis.
 for ob in parts:
  nm=ob.matrix_world.to_3x3().inverted().transposed()
  normals=[(nm@v.vector).normalized() for v in ob.data.corner_normals]
  for v in ob.data.vertices:
   q=ob.matrix_world@v.co
   v.co=Vector(((center_x+q.x)*.01,(-slot_y+q.y)*.01,(rail_z+q.z)*.01))
  ob.matrix_world=Matrix.Identity(4);ob.parent=rig
  ob.data.update();ob.data.normals_split_custom_set(normals)
  ob.vertex_groups.new(name='WPN_root').add(list(range(len(ob.data.vertices))),1.,'REPLACE')
  ob.modifiers.new('Rigid weapon root','ARMATURE').object=rig
 # UVs are local physical-scale planar projection for fine coating texture.
 for ob in parts:
  uv=ob.data.uv_layers.new(name=bpy.data.objects['SVCH_New_KVInhibitor'].data.uv_layers[0].name)
  for poly in ob.data.polygons:
   axis=max(range(3),key=lambda a:abs(poly.normal[a]));a,b=[i for i in range(3) if i!=axis]
   for li in poly.loop_indices:
    p=ob.data.vertices[ob.data.loops[li].vertex_index].co
    uv.data[li].uv=(p[a]*45,p[b]*45)
 bpy.ops.object.select_all(action='DESELECT')
 for ob in parts:ob.select_set(True)
 bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();joined=bpy.context.object;joined.name='SVCH_RealFolding_'+label
 # Join normalizes matrix space; the bind remains WPN_root.
 joined.data.calc_loop_triangles()
 print(label,'triangles',len(joined.data.loop_triangles),flush=True)
 mounts[label]={'slot_center_component_cm':[center_x,slot_y,rail_z],
  'aim_component_cm':[center_x,slot_y-eye_y,rail_z+3.10],
  'triangles':len(joined.data.loop_triangles)}
report={'basis':'2023/2025 SVCh real photos; external visual reconstruction, unseen details approximated',
 'reference_pages':['https://www.kalashnikov.ru/naskolko-svch-prevoshodit-legendarnuyu-svd/','https://www.kalashnikov.ru/kontsern-kalashnikov-podtverdil-kachestvo-serijnyh-vintovok-svch/'],
 'mounts':mounts,'sight_height_above_rail_cm':3.10,'source_master':str(BASE/'SVCH_SightsR2_ElbowFit_Editable.blend'),
 'body_geometry_modified':False,'V9_modified':False,'source_animations_modified':False,'profile_reused':'/Game/Weapons/SVCH/Replacement20261018/SightsR2/ElbowFit/DA_SVCH_ElbowFitGrip',
 'runtime_tested':False}
landmarks=json.loads((BASE/'authoring_receipt.json').read_text())['landmarks_component_cm']
landmarks['RearSight']=mounts['rear']['aim_component_cm'];landmarks['FrontSight']=mounts['front']['aim_component_cm'];report['landmarks_component_cm']=landmarks
bpy.ops.wm.save_as_mainfile(filepath=str(O/'SVCH_RealFoldingSights_Editable.blend'))
# Keep the accepted correction isolated to FBX export copies exactly as before.
d=json.loads((BASE/'bolt_fit_recipe.json').read_text())['delta_component_cm'];shift=Vector((d[0]*.01,-d[1]*.01,d[2]*.01));copies=[];count=0
for ob in list(bpy.context.scene.objects):
 if ob.type!='MESH':continue
 c=ob.copy();c.data=ob.data.copy();bpy.context.scene.collection.objects.link(c);copies.append(c)
 group=c.vertex_groups.get('WPN_bolt')
 if group:
  local=c.matrix_world.inverted().to_3x3()@shift
  for v in c.data.vertices:
   if any(g.group==group.index and g.weight>.999 for g in v.groups):v.co+=local;count+=1
bpy.ops.object.select_all(action='DESELECT')
for ob in copies:ob.select_set(True)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();combined=bpy.context.object;combined.name='SVCH_RealFoldingSights';rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(O/'SK_SVCH_RealFoldingSights.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='OFF',use_tspace=False,colors_type='LINEAR')
report['bolt_export_compensated_vertices']=count
(O/'authoring_receipt.json').write_text(json.dumps(report,indent=2))
print('REAL_SVCH_SIGHTS_EXPORTED',flush=True)
