"""Original local detail additions and separated PC rotors. No acceptance render."""
import bpy,bmesh,ast,math,json,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from design import *
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonReceptionHall20261006/Scripts'))
import geometry as g
g.ROOM='Apartment';bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'
source=ast.parse((ROOT.parent/'RefinementV4/author.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in {'B','roundbox','pipe','ring','text'}],type_ignores=[]),'reused_precision_helpers','exec'),globals())
# Ink sits on the actual keycap top, with a 0.2 mm printed relief.
rows=['1234567890-+=','QWERTYUIOP[]','ASDFGHJKL;','ZXCVBNM,./']
for row,s in enumerate(rows):
 for col,char in enumerate(s):text('KeyboardLegends',char,(-.362+col*.033,-.237+row*.033,.8383),.010,'Paper',(0,0,0))
text('KeyboardLegends','NEXUS / MK.07',(-.355,-.10,.830),.006,'Paper',(0,0,0))
# Dedicated front fans rotate around their own hub; fixed chassis is replaced below.
g.cylinder('ComputerRotor',(0,-.004,0),(0,.004,0),.023,'Dark',32)
for i in range(11):
 a=i*math.tau/11
 points=[(r*math.cos(a+o),y,r*math.sin(a+o)) for r,o,y in [(.024,0,0),(.078,.29,.001),(.080,.50,.002),(.031,.35,.002)]]
 g.poly('ComputerRotor',points,[(0,1,2,3)],'FanBlade')
 g.poly('ComputerRotor',[(x,y+.002,z) for x,y,z in points],[(3,2,1,0)],'FanBlade')
 for j in range(4):
  p=points[j];q=points[(j+1)%4];g.poly('ComputerRotor',[p,q,(q[0],q[1]+.002,q[2]),(p[0],p[1]+.002,p[2])],[(0,1,2,3)],'FanBlade')
ring('ComputerRotor',(0,0,0),(0,1,0),.079,.077,.004,'Dark')
# Real board surface, connectors, sockets and a readable chassis specification.
for y in [-.10+i*.020 for i in range(13)]:
 for z in [.22,.25,.28,.43]:B('ComputerDetail',(-.106,y,z),(.003,.013,.006),'Copper')
for y in [-.13,-.06,.01,.08]:
 B('ComputerDetail',(-.102,y,.46),(.012,.052,.020),'Plastic')
 for j in range(6):B('ComputerDetail',(-.094,y-.02+j*.008,.462),(.004,.003,.010),'Steel')
for z in [.06,.49]:
 for y in [-.20,.20]:g.cylinder('ComputerDetail',(.139,y,z),(.146,y,z),.006,'Steel',24)
text('ComputerDetail','NEXUS | T-07',(-.097,-.122,.315),.012,'Paper',(90,0,-90))
text('ComputerDetail','48V / MODULAR CORE',(-.092,-.122,.29),.005,'Paper',(90,0,-90))
for i in range(15):
 text('GymWeightMarks',str((i+1)*5),(.16,.119,.152+i*.045),.011,'Paper')
# A thin supported belt top replaces visual strips without adding collision.
g.poly('TreadmillBelt',[(-.30,-.79,.286),(.30,-.79,.286),(.30,.65,.286),(-.30,.65,.286)],[(0,1,2,3)],'Belt',uv=[[(0,0),(1,0),(1,1),(0,1)]])
for key,w,d,z in [('DeskSeams',1.65,.68,.77),('OfficeSeams',2.30,.80,.77)]:
 for x in [-w/2+.08,w/2-.08]:
  for y in [-d/2+.07,d/2-.07]:
   ring(key,(x,y,z+.024),(0,0,1),.007,.004,.0018,'Steel')
   B(key,(x,y,z+.025),(.007,.0015,.001),'Dark')
 text(key,'PORT 01 / LOCAL POWER',(.12,d/2-.09,.795),.007,'Paper',(0,0,0))

materials={};records=[];out=ROOT/'Meshes';out.mkdir(parents=True,exist_ok=True)
def export(ob,key,nanite=False,collision=False):
 bpy.ops.object.select_all(action='DESELECT');ob.hide_set(False);ob.select_set(True);bpy.context.view_layer.objects.active=ob
 ob.name='SM_AP7_'+key
 mod=ob.modifiers.new('Production triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
 fbx=out/(ob.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',add_leaf_bones=False,use_tspace=True)
 records.append(dict(key=key,name=ob.name,fbx=str(fbx),asset=BASE+'/Meshes/'+ob.name,triangles=len(ob.data.polygons),nanite=nanite,collision=collision))
for (_,key),data in g.G.items():
 mesh=bpy.data.meshes.new(key);mesh.from_pydata(data['v'],[],data['f']);mesh.update();ob=bpy.data.objects.new(key,mesh);bpy.context.collection.objects.link(ob)
 order=list(dict.fromkeys(data['m']))
 for role in order:
  if role not in materials:materials[role]=bpy.data.materials.new('AP_'+role)
  mesh.materials.append(materials[role])
 uv=mesh.uv_layers.new(name='UVMap')
 for p,role,coords in zip(mesh.polygons,data['m'],data['uv']):
  p.material_index=order.index(role);axes=[a for a in range(3) if a!=max(range(3),key=lambda j:abs(p.normal[j]))]
  if key=='KeyboardLegends':
   points=[mesh.vertices[i].co for i in p.vertices]
   lo=[min(v[a] for v in points) for a in axes];span=[max(v[a] for v in points)-lo[i] for i,a in enumerate(axes)]
  for j,li in enumerate(p.loop_indices):
   point=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=coords[j] if coords else (point[axes[0]],point[axes[1]])
   if key=='KeyboardLegends':uv.data[li].uv=tuple((point[a]-lo[i])/max(span[i],1e-8) for i,a in enumerate(axes))
 export(ob,key)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'ApartmentDetails_Source.blend'))
# Read the retained V4 prototype, removing only the two front rotors' old blades.
source=ROOT.parent/'RefinementV4/CyberpunkApartment_Rebuild.blend'
with bpy.data.libraries.load(str(source),link=False) as (available,wanted):
 wanted.objects=[n for n in available.objects if n=='SM_AP_ComputerTower']
if not wanted.objects:raise RuntimeError('Computer prototype missing in retained source')
ob=wanted.objects[0];bpy.context.collection.objects.link(ob);ob.location=(0,0,0);ob.rotation_euler=(0,0,0);ob.scale=(1,1,1)
bm=bmesh.new();bm.from_mesh(ob.data);remove=[]
for f in bm.faces:
 c=f.calc_center_median()
 # Existing front blade beams and hub lie inside the fixed illuminated annulus.
 front=-.236<c.y<-.212 and any(c.x*c.x+(c.z-z)**2<.077**2 for z in [.19,.39])
 gpu=.238<c.z<.244 and any(c.x*c.x+(c.y-y)**2<.050**2 for y in [-.055,.105])
 if front or gpu:remove.append(f)
bmesh.ops.delete(bm,geom=remove,context='FACES');bm.to_mesh(ob.data);bm.free();export(ob,'ComputerChassis',True)
# Glass optical UV1 belongs to each pane, preserving physical-scale UV0.
with bpy.data.libraries.load(str(ROOT.parent/'RefinementV5/ApartmentV5_Source.blend'),link=False) as (available,wanted):
 wanted.objects=[n for n in available.objects if n=='SM_AP5_WindowGlass']
ob=wanted.objects[0];bpy.context.collection.objects.link(ob)
mesh=ob.data;uv=mesh.uv_layers.new(name='PaneUV');remaining=set(range(len(mesh.polygons)))
while remaining:
 ids={remaining.pop()};verts=set(mesh.polygons[next(iter(ids))].vertices)
 changed=True
 while changed:
  added={i for i in remaining if verts.intersection(mesh.polygons[i].vertices)};changed=bool(added)
  for i in added:verts.update(mesh.polygons[i].vertices)
  remaining-=added;ids|=added
 ps=[mesh.vertices[i].co for i in verts];axis=0 if max(p.x for p in ps)-min(p.x for p in ps)>max(p.y for p in ps)-min(p.y for p in ps) else 1
 a=min(p[axis] for p in ps);b=max(p[axis] for p in ps);z0=min(p.z for p in ps);z1=max(p.z for p in ps)
 for i in ids:
  for li in mesh.polygons[i].loop_indices:
   p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=((p[axis]-a)/max(b-a,.001),(p.z-z0)/max(z1-z0,.001))
export(ob,'WindowGlass')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'ApartmentDetails_Source.blend'))
manifest=ROOT/'detail-assembly.json'
if manifest.exists():records.extend(r for r in json.loads(manifest.read_text())['meshes'] if r['key']=='BalconyRail')
manifest.write_text(json.dumps(dict(meshes=records,rendered=False),indent=2),encoding='utf8')
print('AP7_DETAILS_AUTHORED',len(records),flush=True)
