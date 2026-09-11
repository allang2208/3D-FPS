import bpy,bmesh,math,sys,json
from pathlib import Path
from mathutils import Vector
P=Path(__file__).parent;asset=sys.argv[sys.argv.index('--')+1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(next(P.glob(asset+'_candidate_v01*.glb'))))
o=next(o for o in bpy.context.scene.objects if o.type=='MESH')
bpy.context.view_layer.objects.active=o;o.select_set(True)
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
def mat(name,color,rough=.4,metal=0,trans=0):
 m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes.get('Principled BSDF')
 n.inputs['Base Color'].default_value=(*color,1);n.inputs['Roughness'].default_value=rough;n.inputs['Metallic'].default_value=metal;n.inputs['Transmission Weight'].default_value=trans;n.inputs['IOR'].default_value=1.46
 return m
def cap(bm):
 edges=[e for e in bm.edges if e.is_boundary]
 if edges:bmesh.ops.holes_fill(bm,edges=edges,sides=0)
 bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
if 'potion' in asset:
 # Trim the thin background support reconstructed under the original bottle.
 zmin=min(v.co.z for v in o.data.vertices);zmax=max(v.co.z for v in o.data.vertices);h=zmax-zmin
 bm=bmesh.new();bm.from_mesh(o.data)
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,zmin+.035*h),plane_no=(0,0,1),clear_inner=True,dist=1e-5)
 cap(bm);bm.to_mesh(o.data);bm.free()
 glass=mat('Physical clear glass',(.98,.995,1),.09,0,1)
 silver=mat('Polished silver',(.67,.7,.73),.22,1,0)
 o.data.materials.append(glass);gi=len(o.data.materials)-1
 o.data.materials.append(silver);si=len(o.data.materials)-1
 for f in o.data.polygons:
  c=f.center;z=(c.z-zmin)/h;r=math.hypot(c.x,c.y)
  if asset=='hp_potion': f.material_index=0 if z>.89 else gi
  else: f.material_index=si if (z>.83 or (.61<z<.84 and r>.092*h)) else gi
  f.use_smooth=True
 # Derive a separate sealed liquid volume from the generated bottle's lower body.
 liquid=o.copy();liquid.data=o.data.copy();bpy.context.collection.objects.link(liquid);liquid.name='Liquid volume'
 bm=bmesh.new();bm.from_mesh(liquid.data)
 level=zmin+h*(.51 if asset=='hp_potion' else .46)
 bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),plane_co=(0,0,level),plane_no=(0,0,1),clear_outer=True,dist=1e-5)
 cap(bm)
 for v in bm.verts:
  v.co.x*=.93;v.co.y*=.93;v.co.z=zmin+.045*h+(v.co.z-zmin-.035*h)*.98
 bm.to_mesh(liquid.data);bm.free()
 liquid.data.materials.clear()
 lm=mat('Red health liquid' if asset=='hp_potion' else 'Blue mana liquid',(.55,.009,.015) if asset=='hp_potion' else (.015,.46,.67),.12,0,.78)
 liquid.data.materials.append(lm)
 for f in liquid.data.polygons:f.material_index=0;f.use_smooth=True
 # Solid glass wall, preserving the generated outside shape.
 mod=o.modifiers.new('Glass wall thickness','SOLIDIFY');mod.thickness=.007*h;mod.offset=-1
 bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
else:
 # Replace the damaged lettering region by a planar cardboard surface using the
 # original reference directly as UV input; no image repaint or regeneration.
 coords=[v.co for v in o.data.vertices];lo=Vector(tuple(min(v[i] for v in coords) for i in range(3)));hi=Vector(tuple(max(v[i] for v in coords) for i in range(3)))
 width=hi.x-lo.x;height=hi.z-lo.z
 # Generated front wall is the negative Y face. Cover its central label only.
 x0=lo.x+.008*width;x1=hi.x-.008*width
 z0=lo.z+.008*height;z1=lo.z+(.54 if asset=='ammo_762' else .59)*height
 front=[v.y for v in coords if x0<v.x<x1 and z0<v.z<z1]
 y=min(front)-.004
 vertices=[(x0,y,z0),(x1,y,z0),(x1,y,z1)]
 if asset=='ammo_762':
  cx=(x0+x1)/2
  vertices.extend([(cx+.13*width,y,z1),(cx+.095*width,y,z1-.048*height),(cx-.095*width,y,z1-.048*height),(cx-.13*width,y,z1)])
 vertices.append((x0,y,z1))
 mesh=bpy.data.meshes.new('Retopologized printed front wall');mesh.from_pydata(vertices,[],[tuple(range(len(vertices)))])
 patch=bpy.data.objects.new('Correct caliber printing',mesh);bpy.context.collection.objects.link(patch)
 uv=mesh.uv_layers.new(name='Reference front label')
 # Pixel coordinates in the generated FRONT input (716 square crop).
 rect=(.138,.12,.988,.485) if asset=='ammo_762' else (.103,.084,.967,.592)
 u0,v0,u1,v1=rect
 for poly in mesh.polygons:
  for li in poly.loop_indices:
   v=mesh.vertices[mesh.loops[li].vertex_index].co
   uv.data[li].uv=(u0+(v.x-x0)/(x1-x0)*(u1-u0),v0+(v.z-z0)/(z1-z0)*(v1-v0))
 m=mat('Reference cardboard print',(.3,.1,.07),.9)
 tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(P/(asset+'_view0_00001_.png')));tex.image.pack()
 m.node_tree.links.new(tex.outputs['Color'],m.node_tree.nodes['Principled BSDF'].inputs['Base Color']);mesh.materials.append(m)
bpy.ops.object.select_all(action='DESELECT')
for obj in bpy.context.scene.objects:
 if obj.type=='MESH':obj.select_set(True)
bpy.ops.export_scene.gltf(filepath=str(P/(asset+'_candidate_v02.glb')),export_format='GLB',use_selection=True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/(asset+'_editable.blend')))
