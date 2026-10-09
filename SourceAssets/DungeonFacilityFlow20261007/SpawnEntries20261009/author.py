"""Detailed closed/open outlet parts, with independent hinges and shared PBR."""
from pathlib import Path
import bpy,bmesh,sys,json,hashlib,math,copy
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[2];OUT=ROOT/'Authored';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonReceptionHall20261006/Scripts'));import geometry as g
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC';g.ROOM='Entry'
BASE='/Game/Dungeons/SpawnEntries20261009'
materials={'Paint':'/Game/Dungeons/ReceptionHall20261006/Materials/M_Reception_Teal',
 'Steel':'/Game/Dungeons/SeamMetal20260923/Materials/MI_BareSteel',
 'Black':'/Game/Dungeons/StaffLiving20261002/WallInsetV6/Materials/M_Staff_KettleRubber_V6',
 'Concrete':'/Game/Dungeons/WallUpgrade20260924/Materials/MI_WallConcrete'}

# UE +X points into the room; Blender Y is the opposite handedness on export.
g.box('DoorBody',(.045,0,1.50),(.05,2.18,3.),'Black')
for s in (-1,1):
 g.box('DoorBody',(.80,s*1.02,1.50),(1.52,.13,3.),'Paint')
 g.box('DoorBody',(1.56,s*1.035,1.50),(.07,.19,3.),'Steel')
 g.box('DoorBody',(.84,s*.949,.15),(1.4,.008,.25),'Steel')
 for z in (.18,.8,1.65,2.73):g.bolt('DoorBody',(1.603,s*1.05,z),(1,0,0),.013)
g.box('DoorBody',(.80,0,2.94),(1.52,2.18,.12),'Paint')
g.box('DoorBody',(1.56,0,2.90),(.08,2.18,.11),'Steel')
g.box('DoorBody',(.83,0,.016),(1.43,1.91,.026),'Steel')
for z in (.5,1.55,2.52):
 g.cylinder('DoorBody',(1.50,.93,z-.09),(1.50,.93,z+.09),.043,'Steel',24)
# Leaf relative to UE (150,-90,0) hinge: Y ranges [0,180] cm.
g.box('DoorLeaf',(0,-.90,1.42),(.062,1.78,2.80),'Paint')
g.box('DoorLeaf',(.036,-.90,.30),(.012,1.62,.36),'Steel')
g.box('DoorLeaf',(.038,-.90,1.61),(.008,1.50,1.58),'Paint')
for z in (.57,2.63):g.box('DoorLeaf',(.047,-.90,z),(.017,1.65,.043),'Steel')
for y in (-.11,-1.69):g.box('DoorLeaf',(.048,y,1.59),(.015,.035,1.99),'Steel')
g.box('DoorLeaf',(.055,-1.60,1.20),(.025,.12,.32),'Steel')
g.rounded_pipe('DoorLeaf',[(.085,-1.60,1.15),(.14,-1.60,1.15),(.14,-1.38,1.15)],.021,'Steel',16)
g.box('DoorLeaf',(.055,-.50,2.31),(.014,.62,.27),'Black')
for i in range(5):g.box('DoorLeaf',(.071,-.75+i*.12,2.31),(.017,.065,.045),'Steel')
for i in range(8):g.box('DoorLeaf',(.051,-.90,.94+i*.038),(.016,.67,.013),'Steel')
# Two half-width hinged leaves fit the 1.5m recess; a single 1.8m leaf would
# penetrate the rear wall at 90 degrees. Each leaf keeps its own jamb hinge.
data=g.G[(g.ROOM,'DoorLeaf')];data['v']=[(x,y*.5,z) for x,y,z in data['v']]
right=copy.deepcopy(data);right['v']=[(x,-y,z) for x,y,z in right['v']];g.G[(g.ROOM,'DoorLeafRight')]=right

# Flush cast-iron cover: ribs, fastening recesses, two lifting handles and hinge.
g.ring('HatchBody',(0,0,.009),(0,0,1),.82,.72,.03,'Steel',64)
g.ring('HatchBody',(0,0,-.10),(0,0,1),.755,.72,.20,'Black',64)
g.cylinder('HatchBody',(0,0,-.235),(0,0,-.225),.72,'Black',64)
for i in range(12):
 a=math.tau*i/12;g.bolt('HatchBody',(.786*math.cos(a),.786*math.sin(a),.025),(0,0,1),.015)
g.cylinder('HatchBody',(-.73,-.23,.03),(-.73,.23,.03),.045,'Steel',24)
# Hinge-local circle centre at +73 cm X.
g.lathe('HatchLeaf',(.73,0,0),(0,0,1),[(-.017,.712),(.0,.715),(.012,.703)],'Steel',64)
g.ring('HatchLeaf',(.73,0,.016),(0,0,1),.68,.652,.015,'Black',64)
for i in range(-7,8):
 y=i*.078;span=math.sqrt(max(0,.625**2-y*y))
 if span:g.box('HatchLeaf',(.73,y,.027),(span*2,.017,.016),'Steel')
for y in (-.41,.41):
 g.box('HatchLeaf',(.73,y,.035),(.27,.11,.012),'Black')
 g.rounded_pipe('HatchLeaf',[(.62,y,.04),(.62,y,.071),(.84,y,.071),(.84,y,.04)],.016,'Steel',12)

# Ceiling-mounted closed duct, 180 cm deep, rather than a flat surface sticker.
for s in (-1,1):
 g.box('VentBody',(0,s*.86,-.89),(1.80,.07,1.78),'Paint')
 g.box('VentBody',(s*.86,0,-.89),(.07,1.66,1.78),'Paint')
 for z in (-.08,-.9,-1.73):
  g.box('VentBody',(s*.90,0,z),(.04,1.84,.055),'Steel')
  g.box('VentBody',(0,s*.90,z),(1.84,.04,.055),'Steel')
 for t in (-.62,0,.62):g.bolt('VentBody',(s*.9,t,-1.77),(0,0,-1),.013)
g.box('VentBody',(0,0,-.023),(1.75,1.75,.035),'Black')
# Vent leaf hinge-local centre +78cm X; slats retain a dark opaque back plate.
g.box('VentLeaf',(.78,0,0),(1.56,1.56,.035),'Black')
for s in (-1,1):
 g.box('VentLeaf',(.78,s*.76,-.035),(1.57,.052,.08),'Steel')
 g.box('VentLeaf',(.78+s*.76,0,-.035),(.052,1.48,.08),'Steel')
for i in range(15):g.box('VentLeaf',(.12+i*.094,0,-.055),(.053,1.45,.048),'Paint')
for old,new in [('VentBody','VentLargeBody'),('VentLeaf','VentLargeLeaf')]:
 data=copy.deepcopy(g.G[(g.ROOM,old)]);data['v']=[tuple(v*1.5 for v in p) for p in data['v']];g.G[(g.ROOM,new)]=data
for old,new in [('VentBody','VentCompactBody'),('VentLeaf','VentCompactLeaf')]:
 data=copy.deepcopy(g.G[(g.ROOM,old)]);data['v']=[tuple(v*.75 for v in p) for p in data['v']];g.G[(g.ROOM,new)]=data

records=[]
for (_,kind),data in g.G.items():
 mesh=bpy.data.meshes.new(kind);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
 obj=bpy.data.objects.new('SM_Entry_'+kind,mesh);bpy.context.collection.objects.link(obj)
 slots=list(dict.fromkeys(data['m']));mapping={}
 for name in slots:
  mat=bpy.data.materials.get('Entry_'+name) or bpy.data.materials.new('Entry_'+name);mesh.materials.append(mat);mapping[mat.name]=materials[name]
 uv=mesh.uv_layers.new(name='UVMap')
 for face,mat,smooth in zip(mesh.polygons,data['m'],data['smooth']):
  face.material_index=slots.index(mat);face.use_smooth=smooth
  axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(face.normal[a]))]
  for li in face.loop_indices:
   p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(p[axes[0]],p[axes[1]])
 bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(mesh);bm.free()
 bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
 bevel=obj.modifiers.new('Manufactured edge radii','BEVEL');bevel.width=.004;bevel.segments=3;bevel.limit_method='ANGLE';bpy.ops.object.modifier_apply(modifier=bevel.name)
 tri=obj.modifiers.new('Triangle export','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
 file=OUT/(obj.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
 records.append(dict(name=obj.name,kind=kind,mesh=BASE+'/Meshes/'+obj.name,fbx=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),materials=mapping,collision=False,nanite=False,cast_shadow=True,triangles=len(obj.data.polygons)))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'SpawnEntries.blend'))
(ROOT/'geometry.json').write_text(json.dumps(dict(meshes=records),indent=2),encoding='utf8')
print('SPAWN_ENTRY_KIT_AUTHORED',[(r['kind'],r['triangles']) for r in records])
