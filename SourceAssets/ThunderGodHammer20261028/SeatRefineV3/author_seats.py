"""Five Thor seats: keep every factory vertex, UV and normal; add open relief hardware."""
import bpy,bmesh,math,json,hashlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
P=Path(__file__).resolve().parent;OUT=P/'Export';OUT.mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.preferences.filepaths.save_version=0
with bpy.data.libraries.load(str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),link=False) as(a,b):b.objects=['SM_ThunderGodHammer_head_mount_factory']
factory=b.objects[0];bpy.context.collection.objects.link(factory);source=factory.data;source.calc_loop_triangles()
source_name=factory.name;native_triangles=len(source.loop_triangles)
bvh=BVHTree.FromPolygons([v.co for v in source.vertices],[list(t.vertices) for t in source.loop_triangles],all_triangles=True)
with bpy.data.libraries.load(str(P.parent/'ModulesV1/ThunderGodHammer_SharedParts_Editable.blend'),link=False) as(a,b):
 b.materials=[next(n for n in a.materials if n.split('.')[0]==key) for key in ['M_CommonHammerHeadSteel','M_CommonHammerSeatDarkSteel','M_CommonHammerSeatDamping']]
steel,dark,pad=b.materials
for mat,key in zip([steel,dark,pad],['M_CommonHammerHeadSteel','M_CommonHammerSeatDarkSteel','M_CommonHammerSeatDamping']):mat.name=key
# The donor Blender graph also mixed its old weapon atlas by vertex color.
# New hardware must use only shared steel PBR, matching the dedicated UE materials.
steel_images={key:next(n.image for n in steel.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and n.image.name.startswith('T_CommonHammerSteel_'+key)) for key in ['BaseColor','MetallicRoughness','Normal']}
for mat,factor,is_pad in [(steel,1,False),(dark,.38,False),(pad,1,True)]:
 ns=mat.node_tree.nodes;ls=mat.node_tree.links;ns.clear();bs=ns.new('ShaderNodeBsdfPrincipled');out=ns.new('ShaderNodeOutputMaterial');ls.new(bs.outputs['BSDF'],out.inputs['Surface'])
 uv=ns.new('ShaderNodeUVMap');uv.uv_map='SteelUV';nodes={}
 for key,im in steel_images.items():
  n=ns.new('ShaderNodeTexImage');n.image=im;ls.new(uv.outputs[0],n.inputs['Vector']);nodes[key]=n
 mult=ns.new('ShaderNodeMixRGB');mult.blend_type='MULTIPLY';mult.inputs[0].default_value=1;mult.inputs[2].default_value=(factor,factor,factor,1);ls.new(nodes['BaseColor'].outputs['Color'],mult.inputs[1])
 sep=ns.new('ShaderNodeSeparateColor');ls.new(nodes['MetallicRoughness'].outputs['Color'],sep.inputs[0])
 if is_pad:bs.inputs['Base Color'].default_value=(.025,.025,.025,1);bs.inputs['Roughness'].default_value=.74;bs.inputs['Metallic'].default_value=0
 else:ls.new(mult.outputs[0],bs.inputs['Base Color']);ls.new(sep.outputs['Green'],bs.inputs['Roughness']);ls.new(sep.outputs['Blue'],bs.inputs['Metallic'])
 nm=ns.new('ShaderNodeNormalMap');nm.uv_map='SteelUV';nm.inputs['Strength'].default_value=.18;ls.new(nodes['Normal'].outputs['Color'],nm.inputs['Color']);ls.new(nm.outputs['Normal'],bs.inputs['Normal'])
bronze=steel.copy();bronze.name='M_ThorSeatV3_Bronze'
ns=bronze.node_tree.nodes;ls=bronze.node_tree.links;bs=next(n for n in ns if n.type=='BSDF_PRINCIPLED')
mix=ns.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(.95,.51,.22,1)
if bs.inputs['Base Color'].is_linked:ls.new(bs.inputs['Base Color'].links[0].from_socket,mix.inputs[1])
else:mix.inputs[1].default_value=bs.inputs['Base Color'].default_value
ls.new(mix.outputs[0],bs.inputs['Base Color']);bs.inputs['Metallic'].default_value=.9
# Keep the actual source PBR, resolving its packed images through the factory file.
CX=-.0004452141001820564;CZ=.9095
parts=[];all_parts=[];rows=[]
def surface(x,z,sgn,offset=0):
 hit=bvh.ray_cast(Vector((CX+x,sgn*.20,z)),Vector((0,-sgn,0)),.4)[0]
 return (hit.y if hit else sgn*.039)+sgn*offset
def finish(o,mat,bevel=.0007):
 bpy.context.view_layer.objects.active=o;o.data.materials.clear();o.data.materials.append(mat)
 if bevel:
  m=o.modifiers.new('Rounded forged edges','BEVEL');m.width=bevel;m.segments=3;m.use_clamp_overlap=True;bpy.ops.object.modifier_apply(modifier=m.name)
 for f in o.data.polygons:f.use_smooth=True
 m=o.modifiers.new('Weighted hard-surface normals','WEIGHTED_NORMAL');m.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=m.name)
 # Generated pieces get their own metric UVs; original UVMap is never unwrapped.
 uv=o.data.uv_layers.get('UVMap') or o.data.uv_layers.new(name='UVMap')
 for f in o.data.polygons:
  ax=max(range(3),key=lambda i:abs(f.normal[i]));axes=[i for i in range(3) if i!=ax]
  for li in f.loop_indices:
   co=o.matrix_world@o.data.vertices[o.data.loops[li].vertex_index].co
   uv.data[li].uv=(co[axes[0]]*7+.5,co[axes[1]]*7+.5)
 second=o.data.uv_layers.new(name='SteelUV')
 for i,item in enumerate(uv.data):second.data[i].uv=item.uv
 tri=o.modifiers.new('Explicit triangles for exported tangents','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
 parts.append(o);return o
def ribbon(name,points,width,depth,sgn,mat,offset=.001):
 # Closed, rectangular-section forged strip. Points follow the relief at stations.
 pts=[Vector((CX+x,surface(x,z,sgn,offset),z)) for x,z in points];vs=[]
 # Ring keepers are turned on a single plane; projecting each station onto relief
 # made them corrugated. Their perimeter feet sit on the existing rim instead.
 if name in ['Quartered medallion reinforcement','Antique bronze medallion keeper','Segmented conductive keeper']:
  for p in pts:p.y=sgn*(.0570+offset)
 for i,p in enumerate(pts):
  tang=pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)];tang.y=0;tang.normalize();side=Vector((-tang.z,0,tang.x))*width*.5
  for s,d in [(-1,-1),(1,-1),(1,1),(-1,1)]:vs.append(p+side*s+Vector((0,d*depth*.5,0)))
 fs=[(3,2,1,0),tuple(range((len(pts)-1)*4,len(pts)*4))]
 for i in range(len(pts)-1):
  for j in range(4):fs.append((4*i+j,4*i+(j+1)%4,4*(i+1)+(j+1)%4,4*(i+1)+j))
 me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update()
 bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
 o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);return finish(o,mat,min(.00065,width*.16,depth*.22))
def bolt(x,z,sgn,r=.0026,mat=steel,offset=.003):
 y=surface(x,z,sgn,offset)
 bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=r,depth=.0026,location=(CX+x,y,z),rotation=(math.pi/2,0,0));o=bpy.context.object;o.name='Recessed octagonal fastener';finish(o,mat,.00035)
 # Small dark inset gives fastener a clear seat, with no painted fake rivet.
 bpy.ops.mesh.primitive_cylinder_add(vertices=8,radius=r*.41,depth=.0003,location=(CX+x,y+sgn*.0014,z),rotation=(math.pi/2,0,0));finish(bpy.context.object,dark,.00008)
def arc(a,b,r):return [(r*math.cos(math.radians(t)),CZ+r*math.sin(math.radians(t))) for t in [a+(b-a)*i/24 for i in range(25)]]
def trace(name,points,sgn,mat=steel,width=.005,depth=.003,offset=.001):return ribbon(name,points,width,depth,sgn,mat,offset)
def mirror(points,sx):return [(sx*x,z) for x,z in points]
styles=[
 ('reinforced_block','厚壁重铸座','原生雷纹圆徽 · 阶梯锻钢护肩 · 八角沉头钉'),
 ('ribbed_light','镂肋轻型座','原生雷纹圆徽 · 分叉镂空支肋 · 露底编纹'),
 ('laminated_damper','叠片缓冲座','原生雷纹圆徽 · 四角错层钢片 · 深色缓冲夹层'),
 ('ancient_breaking_seal_seat','破势古印座','原生雷纹圆徽 · 古铜环箍 · 四方古印'),
 ('storm_drive_seat','鸣雷疾驱座','原生雷纹圆徽 · 青铜导雷拱肋 · 分段雷纹压条')]
factory.hide_render=True;factory.hide_set(True)
for oid,label,appearance in styles:
 parts=[]
 base=bpy.data.objects.new('SM_ThunderGodHammer_head_mount_'+oid,source.copy());bpy.context.collection.objects.link(base)
 original=base.vertex_groups.new(name='FACTORY_UNCHANGED');original.add(list(range(len(base.data.vertices))),1,'REPLACE')
 for sign in [-1,1]:
  if oid=='reinforced_block':
   # Wide stepped shoulders at the four corners leave the medallion and crest exposed.
   for sx in [-1,1]:
    for pts in [[(.035,.982),(.049,.978),(.056,.964),(.055,.946)],[(.055,.876),(.051,.862),(.033,.856)]]:
     trace('Forged stepped shoulder',mirror(pts,sx),sign,dark,.012,.006,.0016)
     trace('Raised silver arris',mirror(pts,sx),sign,steel,.006,.004,.0050)
    for z,x in [(.976,.047),(.950,.055),(.864,.049)]:bolt(sx*x,z,sign,.0031,steel,.008)
   for a,b in [(19,66),(114,161),(199,246),(294,341)]:trace('Quartered medallion reinforcement',arc(a,b,.0535),sign,steel,.0045,.0035,.002)
  elif oid=='ribbed_light':
   for sx in [-1,1]:
    # Open fork: two load paths, a visible window, no face plate across the relief.
    trace('Slender outer load path',mirror([(.035,.858),(.056,.878),(.059,.9095),(.056,.942),(.037,.977)],sx),sign,dark,.0055,.004,.0018)
    for pts in [[(.036,.977),(.035,.955),(.048,.942),(.056,.942)],[(.035,.858),(.035,.867),(.048,.877),(.056,.878)]]:
     trace('Forked diagonal support',mirror(pts,sx),sign,steel,.0038,.003,.003)
    for z,x in [(.977,.036),(.858,.035),(.9095,.059)]:bolt(sx*x,z,sign,.0022,steel,.0045)
  elif oid=='laminated_damper':
   for sx in [-1,1]:
    for top in [True,False]:
     pts=[(.030,.978),(.046,.973),(.054,.958)] if top else [(.030,.857),(.046,.864),(.055,.879)]
     for layer in range(3):
      # Real stacked lamellae separated by thin elastomer, visible from oblique views.
      q=[(x-(2-layer)*.0015,z+(2-layer)*(-.001 if top else .001)) for x,z in pts]
      trace('Dark damping separator',mirror(q,sx),sign,pad,.0105,.0016,.002+layer*.0035)
      trace('Stepped steel lamella',mirror(q,sx),sign,steel,.010,.0017,.0035+layer*.0035)
     bolt(sx*.043,.973 if top else .864,sign,.0028,steel,.012)
  elif oid=='ancient_breaking_seal_seat':
   for a,b in [(7,81),(99,173),(187,261),(279,353)]:
    trace('Antique bronze medallion keeper',arc(a,b,.0535),sign,bronze,.0043,.0038,.002)
   for sx in [-1,1]:
    for top in [True,False]:
     z=.969 if top else .861
     points=[(sx*.026,z),(sx*.035,z+.006),(sx*.043,z),(sx*.035,z-.006),(sx*.026,z)]
     trace('Open ancient seal lozenge',points,sign,bronze,.0028,.0027,.0025)
     trace('Raised silver seal stroke',[(sx*.032,z-.002),(sx*.035,z+.0028),(sx*.038,z-.002)],sign,steel,.0014,.0013,.0043)
    bolt(sx*.057,CZ,sign,.0028,bronze,.0035)
  elif oid=='storm_drive_seat':
   for sx in [-1,1]:
    path=mirror([(.027,.852),(.046,.864),(.058,.886),(.059,.917),(.050,.948),(.036,.969),(.012,.987)],sx)
    trace('Dark forged lightning arch',path,sign,dark,.0078,.005,.0025)
    trace('Bronze conductive arch',path,sign,bronze,.0043,.003,.0060)
    zig=mirror([(.041,.965),(.031,.953),(.043,.955),(.037,.945)],sx)
    trace('Crown lightning inlay',zig,sign,steel,.0021,.0018,.0040)
    for x,z in [(.029,.854),(.057,.887),(.051,.948),(.014,.986)]:bolt(sx*x,z,sign,.0024,bronze,.008)
   for a,b in [(30,65),(115,150),(210,245),(295,330)]:trace('Segmented conductive keeper',arc(a,b,.0533),sign,bronze,.0034,.0025,.003)
 # Join additions into the active native mesh: source vertices stay first and untouched.
 bpy.ops.object.select_all(action='DESELECT');base.select_set(True)
 for o in parts:o.select_set(True)
 bpy.context.view_layer.objects.active=base;bpy.ops.object.join()
 me=base.data;me.calc_loop_triangles()
 assert all((me.vertices[i].co-v.co).length<1e-9 for i,v in enumerate(source.vertices))
 assert all((me.uv_layers[0].data[i].uv-u.uv).length<1e-8 for i,u in enumerate(source.uv_layers[0].data))
 normal_error=max((me.corner_normals[i].vector-n.vector).length for i,n in enumerate(source.corner_normals))
 assert normal_error<2e-5,normal_error
 # No new geometry intrudes into the exact x/neck mating stations.
 extra=[v.co for v in me.vertices[len(source.vertices):]]
 assert all(CX-.065<v.x<CX+.065 and v.z>.844 for v in extra)
 bpy.ops.export_scene.fbx(filepath=str(OUT/(base.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,path_mode='STRIP')
 row=dict(id=oid,name=label,appearance=appearance,mesh=base.name,location_cm=[0,0,0],triangles=len(me.loop_triangles),factory_triangles_retained=native_triangles,added_triangles=len(me.loop_triangles)-native_triangles,materials=[m.name for m in me.materials],native_normal_error=normal_error,bounds_m=[[min(v.co[i] for v in me.vertices) for i in range(3)],[max(v.co[i] for v in me.vertices) for i in range(3)]])
 rows.append(row);all_parts.append(base);base.hide_render=True;base.hide_set(True)
 print('FACTORY_DERIVED_SEAT',oid,row['triangles'],flush=True)
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'ThorFactoryDerivedSeatsV3.blend'))
(P/'model_manifest.json').write_text(json.dumps(dict(parts=rows,factory_source=str(P.parent/'ModulesV1/ThunderGodHammer_Modular_Editable.blend'),method='Unmodified factory mesh plus rounded, open structural relief additions on both faces. No replacement face plate.',source_object=source_name,runtime_tested=False),ensure_ascii=False,indent=2),encoding='utf-8')
print('ALL_FIVE_SEATS_EXPORTED',flush=True)
