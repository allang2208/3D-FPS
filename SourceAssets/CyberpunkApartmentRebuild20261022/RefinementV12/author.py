"""Precision ceiling lamp housings. Existing acoustic panels and vents remain.
Final UE-world metres; no rendering or game launch.
"""
from pathlib import Path
import bpy,bmesh,math,json,runpy
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC'
roles=['Graphite','Steel','DiffuserWarm','DiffuserNeutral','DiffuserCool','GuideCyan'];materials={};groups={}
for role in roles:
 m=bpy.data.materials.new(role);m.diffuse_color=(.05,.07,.09,1);materials[role]=m

def box(g,p,s,role,bevel=0):
 # Author in UE axes, reflect Y once for Blender export.
 bpy.ops.mesh.primitive_cube_add(size=1,location=(p[0],-p[1],p[2]));ob=bpy.context.object;ob.scale=s
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if bevel:
  # Subdivision keeps metre-long faces from degenerating at tiny bevel corners.
  bm=bmesh.new();bm.from_mesh(ob.data)
  edges=[e for e in bm.edges if e.calc_length()>.65]
  if edges:bmesh.ops.subdivide_edges(bm,edges=edges,cuts=max(1,math.ceil(max(s)/.65)-1),use_grid_fill=True)
  bm.to_mesh(ob.data);bm.free()
  mod=ob.modifiers.new('Manufactured edge','BEVEL');mod.width=min(bevel,min(s)*.35);mod.segments=3
  bpy.ops.object.modifier_apply(modifier=mod.name)
 ob.data.materials.append(materials[role]);groups.setdefault(g,[]).append(ob)
 return ob

for r in C['LIGHTS']:
 if not r['cover']:continue
 g=r['key'].replace('.','p').replace('-','m');x,y,z=r['center'];w=r['old_width'];d=r['old_depth']
 # Opaque housing fully covers the old emitter. The new face is 6.4 cm below it.
 box(g,(x,y,z+.045),(w+.22,d+.22,.20),'Graphite',.015)
 box(g,(x,y,z-.048),(w+.09,d+.09,.025),'Steel',.008)
 role='DiffuserWarm' if r['temperature']<3900 else 'DiffuserCool' if r['temperature']>=4400 else 'DiffuserNeutral'
 box(g,(x,y,z-.058),(w,d,.012),role,.004)
 # Recessed rails, end caps and fixing heads are solid geometry, not decal cards.
 for sign in (-1,1):
  box(g,(x,y+sign*(d/2+.079),z+.022),(w-.12,.027,.065),'Steel',.006)
  box(g,(x,y+sign*(d/2+.095),z+.016),(w-.28,.010,.012),'GuideCyan',.002)
  box(g,(x+sign*(w/2+.075),y,z+.047),(.055,d+.235,.15),'Steel',.010)
  for sy in (-1,1):
   box(g,(x+sign*(w/2+.075),y+sy*(d/2+.066),z-.035),(.025,.025,.010),'Graphite',.003)
  # Heat sink slots are outside the luminous aperture.
  for j in range(5):box(g,(x+sign*(w/2-.13-j*.058),y,z+.149),(.021,d+.12,.018),'Steel',.003)
 # New corridor ends also receive a real ceiling mounting bracket.
 if r['new']:
  for dx in (-w*.31,w*.31):box(g,(x+dx,y,5.477),(.14,.16,.108),'Graphite',.008)

out=R/'Meshes';out.mkdir(exist_ok=True);records=[]
for key,objects in groups.items():
 bpy.ops.object.select_all(action='DESELECT')
 for ob in objects:ob.select_set(True)
 bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();ob=bpy.context.object
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);name='SM_AP12_Fixture_'+key;ob.name=name
 mesh=ob.data;mesh.update();uv=mesh.uv_layers.new(name='UVMap')
 for poly in mesh.polygons:
  axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(poly.normal[i]))]
  for li in poly.loop_indices:
   v=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]],v[axes[1]])
 mod=ob.modifiers.new('Production triangulation','TRIANGULATE');path=out/(name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 records.append(dict(key=key,name=name,fbx=str(path),asset=C['BASE']+'/Meshes/'+name,triangles=sum(len(p.vertices)-2 for p in mesh.polygons),materials=[m.name for m in mesh.materials],simple_collision_boxes=0))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'PrecisionLighting_Source.blend'))
(R/'assembly.json').write_text(json.dumps(dict(meshes=records,rendered=False,game_run=False,new_textures=0),indent=2),encoding='utf8')
print('AP12_FIXTURES_AUTHORED',len(records),sum(r['triangles'] for r in records),flush=True)
