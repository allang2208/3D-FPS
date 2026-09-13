"""Rebuild QBZ iron sights and refine the supplied gun's hard surfaces.

Authoring only: no preview render or gameplay validation is performed.
Coordinates are metres in the established QBZ WPN_root frame.
"""
import bpy,bmesh,json,math
from pathlib import Path
from mathutils import Vector,Matrix
O=Path(__file__).parent;S=O.parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(S/'QBZ191Refine20260913/QBZ191_Editable.blend'))
s=bpy.context.scene;r=bpy.data.objects['SK_M4_Infima'];hands=bpy.data.objects['SK_Manny_Arms_Export'];old=bpy.data.objects['QBZ191_Export']
materials=list(old.data.materials)
with bpy.data.libraries.load(str(S/'QBZ19120260912/QBZ191_Editable.blend'),link=False) as (a,b):b.objects=['QBZ191_Export']
gun=b.objects[0];s.collection.objects.link(gun);gun.parent=r;gun.matrix_parent_inverse=Matrix.Identity(4);gun.matrix_basis=Matrix.Identity(4)
for mod in gun.modifiers:
 if mod.type=='ARMATURE':mod.object=r
bpy.data.objects.remove(old,do_unlink=True);gun.name='QBZ191_Export';gun.data.name='QBZ191_Machined_Geometry'
source_material_indices=[p.material_index for p in gun.data.polygons]
gun.data.materials.clear()
for m in materials:gun.data.materials.append(m)
for p,index in zip(gun.data.polygons,source_material_indices):p.material_index=index
def fresh_material(name,color,metal,rough):
 m=bpy.data.materials.new(name);m.use_nodes=True;bs=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Metallic'].default_value=metal;bs.inputs['Roughness'].default_value=rough;return m
iron=fresh_material('M_QBZ191_Irons_Machined',(.028,.032,.036),.78,.58)
inner=fresh_material('M_QBZ191_Irons_Inner',(.008,.01,.012),.15,.84)
poly=materials[0].copy();poly.name='M_QBZ191_Polymer'
steel=materials[0].copy();steel.name='M_QBZ191_Steel'
for m in [iron,inner,poly,steel]:gun.data.materials.append(m)
# Match the new UE per-part shading, preserving UV0 and the authored maps.
for m in [materials[0],materials[1],poly,steel]:
 nodes=m.node_tree.nodes;links=m.node_tree.links;bs=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
 ispoly=m==poly;issteel=m==steel;ismag=m==materials[1]
 for n in nodes:
  if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.24 if ispoly else .35 if ismag else .28
 rough=next(n for n in nodes if n.type=='TEX_IMAGE' and n.image and 'Roughness' in n.image.name)
 mul=nodes.new('ShaderNodeMath');mul.operation='MULTIPLY';mul.inputs[1].default_value=.45 if ispoly else .55;links.new(rough.outputs['Color'],mul.inputs[0])
 add=nodes.new('ShaderNodeMath');add.operation='ADD';add.inputs[1].default_value=.42 if ispoly else .25;links.new(mul.outputs[0],add.inputs[0])
 lo=nodes.new('ShaderNodeMath');lo.operation='MAXIMUM';lo.inputs[1].default_value=.58 if ispoly else .47 if not issteel else .44;links.new(add.outputs[0],lo.inputs[0]);links.new(lo.outputs[0],bs.inputs['Roughness'])
 if ispoly:
  for link in list(bs.inputs['Metallic'].links):links.remove(link)
  bs.inputs['Metallic'].default_value=.02
 else:
  metal=next(n for n in nodes if n.type=='TEX_IMAGE' and n.image and 'Metallic' in n.image.name)
  mm=nodes.new('ShaderNodeMath');mm.operation='MULTIPLY';mm.inputs[1].default_value=1 if issteel else .85;links.new(metal.outputs['Color'],mm.inputs[0]);links.new(mm.outputs[0],bs.inputs['Metallic'])
comps=json.loads((S/'QBZ19120260912/components.json').read_text())[0]['components']
polyids=set(comps[91]['ids']+comps[92]['ids']);steelids=set(comps[19]['ids']+comps[89]['ids'])
for face in gun.data.polygons:
 if all(i in polyids for i in face.vertices):face.material_index=5
 elif all(i in steelids for i in face.vertices):face.material_index=6
bpy.ops.object.select_all(action='DESELECT');gun.select_set(True);bpy.context.view_layer.objects.active=gun
# Start from the original bound surface; the previous 4-segment all-edge bevel
# is not stacked a second time. Keep material/UV seams through coplanar cleanup.
bm=bmesh.new();bm.from_mesh(gun.data)
dead=[f for f in bm.faces if f.material_index==2];bmesh.ops.delete(bm,geom=dead,context='FACES')
loose=[v for v in bm.verts if not v.link_faces]
if loose:bmesh.ops.delete(bm,geom=loose,context='VERTS')
bmesh.ops.dissolve_limit(bm,angle_limit=math.radians(.25),verts=list(bm.verts),edges=list(bm.edges),use_dissolve_boundaries=False,delimit={'MATERIAL','SEAM','UV'})
weights=bm.edges.layers.float.get('bevel_weight_edge') or bm.edges.layers.float.new('bevel_weight_edge')
for e in bm.edges:
 sharp=e.is_manifold and e.calc_face_angle(0)>math.radians(38)
 e.smooth=not sharp;e[weights]=1.0 if sharp else 0.0
bm.to_mesh(gun.data);bm.free()
bev=gun.modifiers.new('Controlled 0.18mm two-segment machined edge','BEVEL');bev.limit_method='WEIGHT';bev.width=.00018;bev.segments=2;bev.use_clamp_overlap=True;bev.harden_normals=True
bpy.ops.object.modifier_move_up(modifier=bev.name);bpy.ops.object.modifier_apply(modifier=bev.name)
wn=gun.modifiers.new('Broad plane weighted normals','WEIGHTED_NORMAL');wn.keep_sharp=True;wn.weight=50
bpy.ops.object.modifier_move_up(modifier=wn.name);bpy.ops.object.modifier_apply(modifier=wn.name)
gun.data.calc_loop_triangles();body_triangles=len(gun.data.loop_triangles)
restroot=r.data.bones['WPN_root'].matrix_local.copy()
new_parts=[];part_stats={}
def part(name,verts,faces,mats=None,bevel=0):
 me=bpy.data.meshes.new(name);me.from_pydata([restroot@Vector(v) for v in verts],[],faces);me.update()
 for m in [iron,inner]:me.materials.append(m)
 for i,p in enumerate(me.polygons):p.use_smooth=True;p.material_index=mats[i] if mats else 0
 uv=me.uv_layers.new(name='UVMap')
 for p in me.polygons:
  for li in p.loop_indices:
   v=Vector(verts[me.loops[li].vertex_index]);uv.data[li].uv=(v.x*100,v.z*100)
 ob=bpy.data.objects.new(name,me);s.collection.objects.link(ob);ob.vertex_groups.new(name='WPN_root').add(list(range(len(verts))),1,'REPLACE')
 ob.parent=r;ob.matrix_parent_inverse=Matrix.Identity(4);ob.matrix_basis=Matrix.Identity(4)
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 bm=bmesh.new();bm.from_mesh(me)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
 for e in bm.edges:e.smooth=not(e.is_manifold and e.calc_face_angle(0)>math.radians(36))
 bm.to_mesh(me);bm.free()
 if bevel:
  be=ob.modifiers.new('Small functional edge radius','BEVEL');be.limit_method='ANGLE';be.angle_limit=math.radians(36);be.width=bevel;be.segments=3;be.use_clamp_overlap=True;be.harden_normals=True;bpy.ops.object.modifier_apply(modifier=be.name)
 wn=ob.modifiers.new('Machined face normals','WEIGHTED_NORMAL');wn.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=wn.name)
 ob.modifiers.new('Weapon root binding','ARMATURE').object=r
 me.calc_loop_triangles();part_stats[name]={'vertices':len(me.vertices),'triangles':len(me.loop_triangles)};new_parts.append(ob);return ob
def ring(name,c,rin,rout,depth):
 # Counterbored rear entry, true inner wall and bevelled outer lips.
 sections=[(rin+.00035,depth/2),(rout-.00020,depth/2),(rout,depth/2-.00020),(rout,-depth/2+.00020),(rout-.00020,-depth/2),(rin+.00020,-depth/2),(rin,-depth/2+.00020),(rin,depth/2-.00035)]
 n=96;v=[];f=[];mi=[]
 for radius,y in sections:
  for i in range(n):
   a=i*math.tau/n;v.append((c[0]+radius*math.cos(a),c[1]+y,c[2]+radius*math.sin(a)))
 for j in range(len(sections)):
  for i in range(n):f.append((j*n+i,j*n+(i+1)%n,((j+1)%len(sections))*n+(i+1)%n,((j+1)%len(sections))*n+i));mi.append(1 if j>=5 else 0)
 return part(name,v,f,mi)
def prism(name,outline,y,depth,bevel=.00015,mat=0):
 n=len(outline);v=[(x,y+d,z) for d in [-depth/2,depth/2] for x,z in outline]
 f=[tuple(range(n-1,-1,-1)),tuple(range(n,n*2))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
 return part(name,v,f,[mat]*len(f),bevel)
rear=(.000688,.009231,.122149);front=(.000689,-.343514,.120490)
ring('Rear_Aperture_8mm',rear,.004,.0065,.0036)
cx,cy,cz=rear
prism('Rear_Sight_Stem',[(cx-.0038,.098),(cx+.0038,.098),(cx+.0035,.1118),(cx+.0026,.117),(cx-.0026,.117),(cx-.0035,.1118)],cy,.0042,.00022)
for side in [-1,1]:
 # Protective ears stay outside the enlarged view opening.
 out=[(cx+side*x,z) for x,z in [(.0038,.103),(.0104,.108),(.0104,.12),(.0083,.127),(.0071,.127),(.0071,.1155),(.0042,.111)]]
 if side<0:out.reverse()
 prism('Rear_Protective_Ear_'+str(side),out,cy,.0032,.00025)
 # A separate face insert breaks up the flat block without a coarse normal map.
 prism('Rear_Ear_Recess_'+str(side),[(cx+side*.0074,.111),(cx+side*.0091,.112),(cx+side*.0091,.119),(cx+side*.0074,.119)],cy+.00168,.00012,.00006,1)
ring('Front_Protective_Ring_15mm',(.000689,-.343514,.1220),.0075,.0090,.0040)
cx,cy,cz=front
prism('Front_Sight_Tower',[(cx-.0048,.0965),(cx+.0048,.0965),(cx+.004,.108),(cx+.0031,.1154),(cx-.0031,.1154),(cx-.004,.108)],cy,.0050,.00022)
# The flat tip is precisely on the existing sight ray. Increasing the field of
# view does not move the shot direction or require new marker/rest positions.
prism('Front_Sight_Post',[(cx-.00115,.108),(cx+.00115,.108),(cx+.00048,cz),(cx-.00048,cz)],cy+.00035,.0016,.00007,1)
# Fine elevation collar at the base of the front post: 64 sides, real grooves.
def collar():
 n=64;v=[];f=[]
 for z,radius in [(.1035,.0026),(.1038,.00285),(.1052,.00285),(.1055,.0026)]:
  for i in range(n):
   a=i*math.tau/n;rr=radius-(.00015 if i%2 else 0);v.append((cx+rr*math.cos(a),cy+rr*math.sin(a),z))
 for j in range(3):
  for i in range(n):f.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
 f.extend([tuple(range(n-1,-1,-1)),tuple(range(3*n,4*n))]);part('Front_Elevation_Collar',v,f)
collar()
# Join by material name and bone group, leaving the Manny arm mesh untouched.
bpy.ops.object.select_all(action='DESELECT');gun.select_set(True)
for ob in new_parts:ob.select_set(True)
bpy.context.view_layer.objects.active=gun;bpy.ops.object.join()
gun.data.calc_loop_triangles()
report={'source':'QBZ191Refine20260913/QBZ191_Editable.blend','body_source':'QBZ19120260912/QBZ191_Editable.blend','previous_gun_triangles':224486,'body_triangles_after_refinement':body_triangles,'gun_triangles':len(gun.data.loop_triangles),'gun_vertices':len(gun.data.vertices),'rear_aperture_diameter_mm':8,'front_guard_inner_diameter_mm':15,'front_post_tip_width_mm':.96,'sight_markers_unchanged':{'rear':rear,'front':front},'new_parts':part_stats,'materials':[m.name for m in gun.data.materials],'status':'authored and exported; no post-change render or gameplay test'}
(O/'authoring.json').write_text(json.dumps(report,indent=2))
# Packed editable source retains the current 35 authored animation clips.
r.animation_data.action=bpy.data.actions['QBZ191_base_idle'];r.animation_data.action_slot=r.animation_data.action.slots[0];s.frame_set(0);bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
for ob in [r,gun,hands]:ob.select_set(True)
bpy.context.view_layer.objects.active=r
r.data.pose_position='REST';bpy.context.view_layer.update()
bpy.ops.export_scene.fbx(filepath=str(O/'SK_QBZ191_Manny.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
r.data.pose_position='POSE';bpy.context.view_layer.update()
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'QBZ191_Machined_Editable.blend'))
print('QBZ_MACHINED_MODEL_EXPORTED',json.dumps(report),flush=True)
