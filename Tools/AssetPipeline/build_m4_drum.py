"""Refine the existing Godot drum and fit its own tower to the actual M4 magazine contour."""
import bpy,bmesh,json,math,numpy as np
from pathlib import Path
from mathutils import Vector,Matrix
OUT=Path('D:/FPS3D/FPSGAME/SourceAssets/M4Drum20260909');OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4Replacement/m4_source_imported.blend')
original=bpy.data.objects['Magazine Light.003'];src=np.array([list(original.matrix_world@v.co) for v in original.data.vertices])
bpy.ops.wm.open_mainfile(filepath='D:/FPS3D/FPSGAME/SourceAssets/M4FoldingSights20260909/M4_FoldingSights_Editable.blend')
rig=bpy.data.objects['SK_M4_Infima'];rig.animation_data_clear()
for b in rig.pose.bones:b.matrix_basis=Matrix.Identity(4)
bpy.context.view_layer.update()
mag=next(o for o in rig.children if o.type=='MESH' and 'Magazine' in o.name)
dst=np.array([list(v.co) for v in mag.data.vertices]);assert len(src)==len(dst)
fit=np.linalg.lstsq(np.column_stack([src,np.ones(len(src))]),dst,rcond=None)[0]
assert np.max(np.abs(np.column_stack([src,np.ones(len(src))])@fit-dst))<1e-6
G=Matrix(np.vstack([fit.T,[0,0,0,1]]));inv=G.inverted()
top=float(src[:,2].max());cut=top-.042
# Exact cross-section from triangle intersections, not an AABB replacement.
neck=bpy.data.objects.new('M4FittedFeedTower',mag.data.copy());bpy.context.scene.collection.objects.link(neck)
neck.data.transform(inv);neck.vertex_groups.clear();bm=bmesh.new();bm.from_mesh(neck.data)
bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
bmesh.ops.bisect_plane(bm,geom=list(bm.verts)+list(bm.edges)+list(bm.faces),dist=1e-7,plane_co=(0,0,cut),plane_no=(0,0,1),clear_inner=True,clear_outer=False)
boundary=[e for e in bm.edges if e.is_boundary and all(abs(v.co.z-cut)<1e-5 for v in e.verts)]
assert boundary
points=[v.co.copy() for e in boundary for v in e.verts]
center=Vector(((min(p.x for p in points)+max(p.x for p in points))/2,(min(p.y for p in points)+max(p.y for p in points))/2,cut-.010))
# Extrude the measured rim down into a smooth shoulder. The retained upper
# surface is part of this replacement; the complete original magazine is hidden.
ring=boundary
for step in range(1,9):
 result=bmesh.ops.extrude_edge_only(bm,edges=ring);verts=[v for v in result['geom'] if isinstance(v,bmesh.types.BMVert)]
 t=step/8;z=cut-.044*t;ease=t*t*(3-2*t)
 for v in verts:
  p=v.co.copy();rad=max(abs(p.x-center.x)/.0195,abs(p.y-center.y)/.0355,1e-6)
  v.co.x=center.x+(p.x-center.x)*(1+(1/rad-1)*ease*.24)
  v.co.y=center.y+(p.y-center.y)*(1+(1/rad-1)*ease*.24);v.co.z=z
 ring=[e for e in result['geom'] if isinstance(e,bmesh.types.BMEdge) and all(v in verts for v in e.verts)]
bmesh.ops.holes_fill(bm,edges=[e for e in ring if e.is_boundary],sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(neck.data);bm.free();neck.data.update()
neck.data.transform(Matrix.Translation(-center));neck.data.materials.clear()
with bpy.data.libraries.load('E:/3d/3-dfps/tools/ai-gen/drum-v2-20260907/large-drum-v2.blend',link=False) as (a,b):b.objects=[n for n in a.objects if not n.startswith(('CalibratedFeedTower','ContinuousTowerShoulder','TowerRelief'))]
parts=[neck]
for o in b.objects:
 if o.type!='MESH':continue
 bpy.context.scene.collection.objects.link(o);bpy.context.view_layer.update()
 o.data=o.data.copy();o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
 # Flatten excessive round rim bulge while preserving the housing contact.
 if o.name.startswith('PrecisionRim'):
  side=1 if sum(v.co.y for v in o.data.vertices)>0 else -1
  for v in o.data.vertices:
   radial=Vector((v.co.x,0,v.co.z+.085));length=radial.length
   if length>0:
    target=.060+(length-.060)*.72;v.co.x*=target/length;v.co.z=-.085+radial.z*target/length
   v.co.y=side*(.03555+(abs(v.co.y)-.03555)*.75)
 # Remove redundant coplanar tessellation; reduce subpixel fastener bevel rings.
 bpy.context.view_layer.objects.active=o
 mod=o.modifiers.new('Planar cleanup','DECIMATE');mod.decimate_type='DISSOLVE';mod.angle_limit=math.radians(1)
 bpy.ops.object.modifier_apply(modifier=mod.name)
 mod=o.modifiers.new('Controlled detail budget','DECIMATE');mod.ratio=.42 if 'Screw' in o.name else .62
 bpy.ops.object.modifier_apply(modifier=mod.name)
 parts.append(o)
def mat(name,color,rough,metal):
 m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Metallic'].default_value=metal;return m
poly=mat('DrumPolymer',(.036,.034,.029),.64,0);steel=mat('DrumFasteners',(.12,.12,.115),.48,.7);index=mat('DrumIndex',(.34,.21,.07),.7,0)
triangles=0
for o in parts:
 material=steel if 'Screw' in o.name else index if 'OrangeIndex' in o.name else poly
 o.data.materials.clear();o.data.materials.append(material)
 for f in o.data.polygons:f.material_index=0
 if not o.data.uv_layers:o.data.uv_layers.new(name='UVMap')
 uv=o.data.uv_layers.active.data
 # A small clean panel patch of the M4 magazine PBR atlas, avoiding its
 # geometry-specific grooves and baked normals. The neck keeps exact geometry.
 for f in o.data.polygons:
  axes=sorted(range(3),key=lambda k:abs(f.normal[k]))[:2]
  for li in f.loop_indices:
   p=o.data.vertices[o.data.loops[li].vertex_index].co
   uv[li].uv=(.765+((p[axes[0]]+.15)*.35)% .07,.30+((p[axes[1]]+.15)*.35)% .07)
 # Eliminate imported custom normals after topology edits, preserve sharp planes.
 if o.data.has_custom_normals:
  bpy.context.view_layer.objects.active=o
  try:bpy.ops.mesh.customdata_custom_splitnormals_clear()
  except Exception:pass
 o.data.transform(G@Matrix.Translation(center));triangles+=sum(len(f.vertices)-2 for f in o.data.polygons)
 o['drum_part']=True
mag.hide_render=True
# A single UE mesh with three material sections, exact current receiver frame.
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=neck;bpy.ops.object.join();drum=bpy.context.object;drum.name='SM_M4_LargeDrum'
bpy.ops.export_scene.fbx(filepath=str(OUT/'SM_M4_LargeDrum.fbx'),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
# One rigid skin group for editable preview and animation work, not a new bone.
drum.parent=rig;drum.matrix_parent_inverse=Matrix.Identity(4);drum.matrix_basis=Matrix.Identity(4)
drum.vertex_groups.clear();group=drum.vertex_groups.new(name='WPN_SOCKET_Magazine');group.add(list(range(len(drum.data.vertices))),1,'REPLACE');mod=drum.modifiers.new('Magazine motion','ARMATURE');mod.object=rig
(OUT/'build.json').write_text(json.dumps(dict(source_triangles=26380,triangles=triangles,source_top=top,cut=cut,center=list(center),source_to_component=[list(row) for row in G],bone='WPN_SOCKET_Magazine',original_magazine=mag.name),indent=2))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M4_Drum_Optimized.blend'))
s=bpy.context.scene;s.render.engine='BLENDER_EEVEE';s.render.resolution_x=1200;s.render.resolution_y=800;s.render.resolution_percentage=100
for o in s.objects:o.hide_render=o not in rig.children
mag.hide_render=True
for o in rig.children:
 if o.type=='MESH' and 'Arms' in o.name:o.hide_render=True
focus=G@(center+Vector((0,0,-.04)));bpy.ops.object.camera_add();cam=bpy.context.object;s.camera=cam;cam.data.type='ORTHO';cam.data.ortho_scale=.36
for offset in [(0.4,0,.4),(-.3,.1,.3)]:
 bpy.ops.object.light_add(type='AREA',location=focus+Vector(offset));bpy.context.object.data.energy=30;bpy.context.object.data.size=.4
for name,offset in [('fit-side',(.6,0,.08)),('fit-oblique',(.5,-.35,.15)),('fit-reverse',(-.6,.1,.05))]:
 cam.location=focus+Vector(offset);cam.rotation_euler=(focus-cam.location).to_track_quat('-Z','Y').to_euler();s.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
print('M4_DRUM_BUILD_PASS',triangles,'center',list(center))
