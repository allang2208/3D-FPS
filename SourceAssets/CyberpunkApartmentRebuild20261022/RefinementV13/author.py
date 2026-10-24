"""Precision ceiling lamp housings. Existing acoustic panels and vents remain.
Final UE-world metres; no rendering or game launch.
"""
from pathlib import Path
import bpy,bmesh,math,json,runpy
R=Path(__file__).resolve().parent;C=runpy.run_path(str(R/'design.py'))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC'
roles=['Graphite','Steel','Acoustic','Rubber','Pearl','EdgeLight','Display','Control'];materials={};groups={}
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

# Large display: independent manufactured parts, final dimensions rather than stretching.
t=C['TV'];x,y,z=t['center'];w=t['width'];h=t['height']
box('TVBody',(x,y,z),(.09,w,h),'Graphite',.016)
box('TVBody',(x-.049,y,z),(.010,w-.042,h-.042),'Steel',.006)
box('TVDisplay',(x-.057,y,z),(.006,w-.080,h-.080),'Display',.002)
for sign in (-1,1):
 box('TVBody',(x-.064,y+sign*(w/2-.018),z),(.014,.022,h-.03),'Graphite',.005)
 box('TVBody',(x-.064,y,z+sign*(h/2-.018)),(.014,w-.03,.022),'Graphite',.005)
 # Solid bracket connects rear enclosure to the existing wall surface at X=21.132.
 box('TVBody',(21.092,y+sign*1.15,z),(.080,.12,2.7),'Steel',.008)
 for j in range(4):box('TVBody',(21.128,y+sign*1.15,z-1.05+j*.70),(.008,.19,.13),'Graphite',.005)
 for j in range(21):box('TVBody',(x+.051,y-w/2+.21+j*.285,z+sign*(h/2-.09)),(.014,.17,.025),'Rubber',.003)
# The independent speaker is supported above the cabinet, with a real recessed grille.
sx,sy,sz=20.98,-4.08,.735
box('Soundbar',(sx,sy,sz),(.14,2.82,.17),'Graphite',.025)
box('Soundbar',(sx-.074,sy,sz),(.012,2.69,.126),'Acoustic',.006)
for j in range(108):box('Soundbar',(sx-.084,sy-1.32+j*.0247,sz),(.013,.006,.108),'Steel',.002)
for yy in (-5.05,-3.11):box('Soundbar',(21.065,yy,sz),(.13,.10,.10),'Steel',.005)
box('Soundbar',(sx-.09,sy+1.21,sz+.048),(.008,.075,.009),'EdgeLight',.002)

# Quiet layered backing, with genuine reveal gaps around each panel.
box('TVBackdrop',(21.105,-4.08,2.90),(.024,6.55,4.28),'Graphite',.007)
for yy in (-7.33,-.83):
 box('TVBackdrop',(21.071,yy,2.90),(.065,.090,4.28),'Steel',.010)
 box('TVBackdrop',(21.034,yy,2.90),(.010,.018,3.98),'EdgeLight',.003)
for zz in (.77,5.03):box('TVBackdrop',(21.075,-4.08,zz),(.058,6.51,.065),'Steel',.008)
for j in range(6):box('TVBackdrop',(21.087,-6.82+j*1.09,4.96),(.040,1.062,.075),'Pearl',.005)
# Small supported power panel to the left of the soundbar.
box('TVBackdrop',(21.05,-6.82,.76),(.17,.31,.17),'Graphite',.010)

# Floating ceiling wings leave the central high ceiling and the main lamp unobstructed.
for xx in (8.18,20.13):
 box('LivingCeiling',(xx,-5.17,5.075),(.72,8.72,.22),'Graphite',.025)
 for j in range(12):
  yy=-9.15+j*.725
  box('LivingCeiling',(xx,yy,4.959),(.62,.68,.014),'Acoustic',.004)
 for dx in (-.32,.32):box('LivingCeiling',(xx+dx,-5.17,5.01),(.026,8.50,.045),'Steel',.006)
 box('LivingCeiling',(xx+(.375 if xx<10 else -.375),-5.17,5.10),(.012,8.2,.018),'EdgeLight',.003)
 for yy in (-8.65,-5.17,-1.69):box('LivingCeiling',(xx,yy,5.355),(.16,.19,.3525),'Steel',.008)

# Window pelmet covers the curtain rail without lowering across glass or door openings.
box('WindowHead',(14.30,-.53,5.31),(13.35,.40,.24),'Graphite',.018)
box('WindowHead',(14.30,-.744,5.265),(13.18,.025,.12),'Pearl',.006)
box('WindowHead',(14.30,-.761,5.327),(12.9,.012,.014),'EdgeLight',.002)
for xx in (8.3,11.3,14.3,17.3,20.3):box('WindowHead',(xx,-.53,5.477),(.16,.19,.1085),'Steel',.006)

for xx in (1.38,6.04):
 box('OfficeCeiling',(xx,-5.0,5.13),(.34,8.05,.20),'Graphite',.018)
 box('OfficeCeiling',(xx,-5.0,5.022),(.26,7.91,.016),'Acoustic',.005)
 for yy in (-8.5,-5.0,-1.5):box('OfficeCeiling',(xx,yy,5.381),(.10,.15,.30),'Steel',.006)
for yy in (-2.3,-7.7):
 box('OfficeCeiling',(3.71,yy,5.16),(4.34,.15,.12),'Steel',.009)
 for j in range(14):box('OfficeCeiling',(1.77+j*.298,yy,5.24),(.035,.30,.22),'Graphite',.006)

for xx in (-4.5,4.45):
 box('GymCeiling',(xx,-19.20,5.21),(.32,6.45,.20),'Graphite',.017)
 box('GymCeiling',(xx,-19.20,5.104),(.20,6.24,.014),'Acoustic',.004)
 for yy in (-21.9,-19.2,-16.5):box('GymCeiling',(xx,yy,5.405625),(.12,.16,.25125),'Steel',.005)
for yy in (-16.02,-22.36):
 box('GymCeiling',(-.025,yy,5.23),(8.72,.19,.18),'Graphite',.015)
 box('GymCeiling',(-.025,yy+.102,5.24),(8.22,.012,.019),'EdgeLight',.002)
 for j in range(22):box('GymCeiling',(-4.06+j*.382,yy,5.35),(.028,.23,.13),'Steel',.005)

# Upper wall reveals are above doors and wardrobes; skip window-bearing walls.
for yy in (-10.095,-20.37):
 box('WallBands',(25.57,yy,4.56),(7.72,.075,.16),'Graphite',.012)
 box('WallBands',(25.57,yy+.045,4.50),(7.62,.015,.026),'Steel',.004)
 for xx in (22.4,24.5,26.6,28.7):box('WallBands',(xx,yy+.046,4.61),(.43,.018,.025),'Pearl',.004)
box('WallBands',(.25,-5.13,4.56),(.06,8.74,.16),'Graphite',.010)
for yy in (-8.2,-5.2,-2.2):box('WallBands',(.29,yy,4.56),(.015,.55,.11),'Steel',.005)

# Shared local-space physical power controller; front is local -Y.
box('PowerControl',(0,0,0),(.28,.055,.14),'Graphite',.012)
box('PowerControl',(0,.052,0),(.20,.065,.080),'Graphite',.008)
box('PowerControl',(0,-.030,0),(.251,.009,.112),'Steel',.004)
box('PowerControl',(0,-.037,0),(.237,.006,.098),'Control',.003)
box('PowerControl',(0,.012,-.073),(.22,.070,.010),'Rubber',.003)
for xx in (-.123,.123):box('PowerControl',(xx,-.039,-.046),(.011,.004,.011),'Graphite',.002)

out=R/'Meshes';out.mkdir(exist_ok=True);records=[]
for key,objects in groups.items():
 bpy.ops.object.select_all(action='DESELECT')
 for ob in objects:ob.select_set(True)
 bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();ob=bpy.context.object
 bpy.ops.object.transform_apply(location=True,rotation=True,scale=True);name='SM_AP13_'+key;ob.name=name
 mesh=ob.data;mesh.update();uv=mesh.uv_layers.new(name='UVMap');panel=mesh.uv_layers.new(name='PanelUV')
 for poly in mesh.polygons:
  axes=[i for i in range(3) if i!=max(range(3),key=lambda i:abs(poly.normal[i]))]
  points=[mesh.vertices[i].co for i in poly.vertices];lo=[min(p[a] for p in points) for a in axes];span=[max(p[a] for p in points)-lo[i] for i,a in enumerate(axes)]
  role=mesh.materials[poly.material_index].name
  for li in poly.loop_indices:
   v=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]],v[axes[1]])
   co=[(v[a]-lo[i])/max(span[i],.000001) for i,a in enumerate(axes)]
   if role=='Display' and abs(poly.normal.x)>.9:co[0]=1-co[0]
   panel.data[li].uv=co
 mod=ob.modifiers.new('Production triangulation','TRIANGULATE');path=out/(name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 records.append(dict(key=key,name=name,fbx=str(path),asset=C['BASE']+'/Meshes/'+name,triangles=sum(len(p.vertices)-2 for p in mesh.polygons),materials=[m.name for m in mesh.materials],simple_collision_boxes=0))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'ApartmentExperience_Source.blend'))
(R/'assembly.json').write_text(json.dumps(dict(meshes=records,rendered=False,game_run=False,television=C['TV']),indent=2),encoding='utf8')
print('AP13_GEOMETRY_AUTHORED',len(records),sum(r['triangles'] for r in records),flush=True)
