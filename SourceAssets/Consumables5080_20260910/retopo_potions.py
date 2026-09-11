"""Clean authorable bottle reconstruction using the reviewed 5080 silhouette and sheet.
Raw TRELLIS meshes are retained separately; this is an explicit retopology pass.
"""
import bpy,math,sys
from pathlib import Path
P=Path(__file__).parent;asset=sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
def material(name,col,rough=.15,metal=0,trans=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes.get('Principled BSDF');n.inputs['Base Color'].default_value=(*col,1);n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal;n.inputs['Transmission Weight'].default_value=trans;n.inputs['IOR'].default_value=1.46;return m
glass=material('Clear thick glass',(.985,.995,1),.055,0,1)
liquid=material('Health liquid' if asset=='hp_potion' else 'Mana liquid',(.75,.018,.025) if asset=='hp_potion' else (.035,.62,.85),.09,0,.75)
silver=material('Brushed silver',(.68,.71,.75),.2,1)
cork=material('Natural cork',(.48,.27,.08),.86)
tex=cork.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(P/'hp_potion_view0_00001_.png'));tex.image.pack();cork.node_tree.links.new(tex.outputs['Color'],cork.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
def lathe(name,profile,n,mat,caps=False,bevel=0):
 verts=[];faces=[]
 for z,r in profile:
  for i in range(n):
   a=2*math.pi*i/n+math.pi/8;verts.append((r*math.cos(a),r*math.sin(a),z))
 for j in range(len(profile)-1):
  for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
 if caps:faces.extend([tuple(reversed(range(n))),tuple((len(profile)-1)*n+i for i in range(n))])
 mesh=bpy.data.meshes.new(name);mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(o);mesh.materials.append(mat)
 uv=mesh.uv_layers.new(name='UVMap')
 for poly in mesh.polygons:
  poly.use_smooth=n>8
  for li in poly.loop_indices:
   vi=mesh.loops[li].vertex_index;j=vi//n;i=vi%n
   uv.data[li].uv=(.40+.18*i/max(1,n-1),.86+.10*j/max(1,len(profile)-1)) if mat==cork else (i/n,j/max(1,len(profile)-1))
 if bevel:
  mod=o.modifiers.new('Manufactured edge bevel','BEVEL');mod.width=bevel;mod.segments=3
  bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.modifier_apply(modifier=mod.name);o.select_set(False)
 return o
if asset=='hp_potion':
 outer=[(0,.20),(.025,.235),(.59,.235),(.72,.13),(.83,.13),(.84,.15),(.885,.15),(.9,.13)]
 inner=[(.9,.112),(.84,.112),(.73,.112),(.58,.216),(.035,.216),(.025,0)]
 lathe('Retopologized health bottle',outer+inner,8,glass,True,.004)
 lathe('Red liquid',[(.033,.193),(.047,.211),(.48,.211),(.482,0)],8,liquid,True,.002)
 lathe('Cork stopper',[(.84,.11),(.98,.12),(.99,.115)],48,cork,True,.004)
else:
 outer=[(0,.17),(.018,.21),(.07,.25),(.16,.295),(.27,.32),(.38,.302),(.47,.265),(.55,.20),(.62,.12),(.67,.077),(.84,.077),(.85,.095),(.875,.095),(.885,.078)]
 inner=[(.885,.063),(.67,.063),(.62,.105),(.55,.185),(.47,.250),(.38,.287),(.27,.305),(.16,.280),(.07,.235),(.03,.19),(.025,0)]
 lathe('Retopologized mana bottle',outer+inner,96,glass,True)
 lathe('Blue liquid',[(.034,.18),(.07,.231),(.16,.276),(.27,.301),(.38,.283),(.45,.254),(.452,0)],96,liquid,True)
 lathe('Silver stopper collar',[(.865,.088),(.888,.088)],64,silver,True,.003)
 bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,radius=.073,location=(0,0,.956));o=bpy.context.object;o.name='Silver stopper';o.data.materials.append(silver)
 for f in o.data.polygons:f.use_smooth=True
 curve=bpy.data.curves.new('Double spiral silver band','CURVE');curve.dimensions='3D';curve.bevel_depth=.008;curve.bevel_resolution=4
 sp=curve.splines.new('POLY');sp.points.add(192)
 for i,p in enumerate(sp.points):
  t=i/192;a=t*math.pi*4;p.co=(.085*math.cos(a),.085*math.sin(a),.665+.183*t,1)
 o=bpy.data.objects.new('Silver neck spiral',curve);bpy.context.collection.objects.link(o);curve.materials.append(silver)
# Deliver in metres at a practical inventory-prop size.
for o in bpy.context.scene.objects:
 o.scale*=.18;o.location*=.18
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.convert(target='MESH')
bpy.ops.export_scene.gltf(filepath=str(P/(asset+'_candidate_v02.glb')),export_format='GLB',use_selection=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/(asset+'_editable.blend')))
