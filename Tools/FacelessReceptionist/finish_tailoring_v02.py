"""Tailor continuous clothing directly around the corrected Nurse bind body."""
import bpy,bmesh,math,json
from pathlib import Path
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
ROOT=Path(r'D:\FPS3D\FPSGAME\SourceAssets\FacelessReceptionist20261007\V02')
bpy.ops.wm.open_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V02.blend'))
body=bpy.data.objects['Receptionist_CompleteBody'];rig=body.parent
with bpy.data.libraries.load(str(ROOT.parent/'Authoring/Inputs.blend'),link=False) as (fr,to):
 to.objects=['Receptionist_SourceBody']
source=to.objects[0];ap=[v.co.copy() for v in source.data.vertices]
rest=[v.co.copy() for v in body.data.vertices]
body.data.calc_loop_triangles();tris=[tuple(t.vertices) for t in body.data.loop_triangles]
weights=[{body.vertex_groups[g.group].name:g.weight for g in v.groups} for v in body.data.vertices]
tree=BVHTree.FromPolygons(rest,tris,all_triangles=True)
def surface(p):
 hit=tree.find_nearest(p);ids=tris[hit[2]]
 b=barycentric_transform(hit[0],*(rest[i] for i in ids),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
 b=[max(0.,float(x)) for x in b];total=sum(b);b=[x/total for x in b]
 a=sum((ap[i]*f for i,f in zip(ids,b)),Vector())
 ws={}
 for i,f in zip(ids,b):
  for n,w in weights[i].items():ws[n]=ws.get(n,0)+w*f
 ws={n:w for n,w in sorted(ws.items(),key=lambda v:-v[1])[:8] if w>1e-5};total=sum(ws.values());ws={n:w/total for n,w in ws.items()}
 return a,ws
def active(o):
 bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):active(o);bpy.ops.object.modifier_apply(modifier=m.name)
def smooth(a,b,x):
 t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def lerp_table(z,table):
 for (a,x),(b,y) in zip(table,table[1:]):
  if a<=z<=b:return x+(y-x)*(z-a)/(b-a)
 return table[0][1] if z<table[0][0] else table[-1][1]
def opening(z):return lerp_table(z,[(1.005,.001),(1.16,.002),(1.30,.038),(1.42,.072),(1.49,.080),(1.55,.058)])
sk=bpy.data.objects['Receptionist_Skirt']
sk.data.calc_loop_triangles()
sk_tree=BVHTree.FromPolygons([v.co.copy() for v in sk.data.vertices],[tuple(t.vertices) for t in sk.data.loop_triangles],all_triangles=True)
for name,kind,offset,thickness in [('Receptionist_Blazer_Continuous','jacket',.015,.0028),('Receptionist_Shirt_Continuous','shirt',.006,.0015)]:
 old=bpy.data.objects[name];mat=old.data.materials[0]
 o=body.copy();o.data=body.data.copy();bpy.context.scene.collection.objects.link(o)
 o.parent=None;o.matrix_world=Matrix.Identity(4);o.vertex_groups.clear()
 for m in list(o.modifiers):o.modifiers.remove(m)
 o.data.materials.clear();o.data.materials.append(mat)
 rem=o.modifiers.new('RestFabricUnion','REMESH');rem.mode='VOXEL';rem.voxel_size=.0045;rem.use_smooth_shade=True;apply(o,rem)
 sm=o.modifiers.new('RestTailorSmooth','SMOOTH');sm.factor=.55;sm.iterations=4;apply(o,sm)
 bm=bmesh.new();bm.from_mesh(o.data)
 def keep(p):
  a,_=surface(p)
  if kind=='jacket':
   bottom=1.005-.023*smooth(.26,.36,abs(a.x))
   if a.z<bottom or a.z>1.62:return False
   if a.z>1.54 and math.hypot(a.x,a.y-.005)<.058+(a.z-1.54)*2:return False
   if a.y<-.008 and abs(a.x)<opening(a.z):return False
   return True
  return 1.024<a.z<1.567 and abs(a.x)<.205
 mask={v:keep(v.co) for v in bm.verts}
 bmesh.ops.delete(bm,geom=[f for f in bm.faces if not all(mask[v] for v in f.verts)],context='FACES')
 bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
 bm.to_mesh(o.data);bm.free()
 dec=o.modifiers.new('TailoredTopology','DECIMATE');dec.ratio=.34 if kind=='jacket' else .25;apply(o,dec)
 # Use outward normals from the source solid before the openings were cut.
 bm=bmesh.new();bm.from_mesh(o.data);bm.normal_update()
 for v in bm.verts:
  v.co+=v.normal*offset
  a,_=surface(v.co)
  if kind=='jacket' and a.z<1.285 and abs(a.x)<.24:
   center=Vector((0,.027,v.co.z));direction=Vector((v.co.x,v.co.y-.027,0)).normalized()
   query_center=Vector((center.x,center.y,min(center.z,1.10)))
   h=sk_tree.ray_cast(query_center,direction,.5)
   if h[0] is not None:
    radius=(h[0]-query_center).length+.012
    current=(Vector((v.co.x,v.co.y,v.co.z))-center).length
    if current<radius:
     # Bring the blazer hem outside the skirt, fading above the waistband.
     v.co+=direction*(radius-current)*(1-smooth(1.105,1.285,a.z))
  if v.is_boundary and kind=='jacket' and a.z<1.025 and abs(a.x)<.24:
   v.co.z+=1.005-a.z
 bm.to_mesh(o.data);bm.free();o.data.update()
 bind=[surface(v.co)[1] for v in o.data.vertices]
 for n in sorted({n for ws in bind for n in ws}):o.vertex_groups.new(name=n)
 for v,ws in zip(o.data.vertices,bind):
  for n,w in ws.items():o.vertex_groups[n].add([v.index],w,'REPLACE')
 for f in o.data.polygons:f.material_index=0;f.use_smooth=True
 active(o);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
 solid=o.modifiers.new('TailoredThickness','SOLIDIFY');solid.thickness=thickness;solid.offset=0;apply(o,solid)
 o.parent=rig;o.matrix_parent_inverse=rig.matrix_world.inverted()
 ar=o.modifiers.new('NurseNativeSkin','ARMATURE');ar.object=rig
 bpy.data.objects.remove(old,do_unlink=True);o.name=name
# Put buttons, pocket welts and the badge onto the final blazer surface.
jacket=bpy.data.objects['Receptionist_Blazer_Continuous'];jacket.data.calc_loop_triangles()
jt=BVHTree.FromPolygons([v.co.copy() for v in jacket.data.vertices],[tuple(t.vertices) for t in jacket.data.loop_triangles],all_triangles=True)
for o in bpy.context.scene.objects:
 if not o.name.startswith(('Receptionist_Blazer_Button','Receptionist_PocketWelt')):continue
 p=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
 h=jt.ray_cast(Vector((p.x,-.8,p.z)),Vector((0,1,0)),1.5)
 if h[0] is not None:
  delta=Vector((0,h[0].y-.003-p.y,0))
  for v in o.data.vertices:v.co+=delta
bpy.data.objects.remove(source,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessReceptionist_V02.blend'))
receipt=json.loads((ROOT/'authoring_receipt.json').read_text())
parts=[o for o in bpy.context.scene.objects if o.type=='MESH' and o!=body]
receipt['parts']=[{'name':o.name,'vertices':len(o.data.vertices),'triangles':sum(len(f.vertices)-2 for f in o.data.polygons),'materials':[m.name for m in o.data.materials]} for o in parts]
receipt['notes'].append('Final jacket and shirt retopologized around repaired native bind body. Full body untouched by clothing shell creation.')
(ROOT/'authoring_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('TAILORING_SAVED',sum(x['triangles'] for x in receipt['parts']))
