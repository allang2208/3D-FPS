"""Dimensioned concourse and six independently replaceable portal assemblies."""
import bpy,bmesh,math,json,sys,hashlib,random
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1];OUT=ROOT/'Authored'
refined=ROOT/'RefineV2'
if __name__=='__main__' and (refined/'Receipts/install.json').exists() and json.loads((refined/'Receipts/install.json').read_text('utf8')).get('stage')=='maps_saved':
 import runpy
 runpy.run_path(str(refined/'author.py'),run_name='__main__')
 raise SystemExit(0)
sys.path.insert(0,str(ROOT/'Scripts'));import geometry as g
CFG=json.loads((ROOT/'Config/layout.json').read_text('utf8'));ROLES=json.loads((ROOT/'Config/materials.json').read_text('utf8'));ATLAS=json.loads((ROOT/'Config/atlas.json').read_text('utf8'));BASE=CFG['base']
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
materials={}
for k,r in ROLES.items():
 m=bpy.data.materials.new('FT_'+k);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*r['basecolor_linear'],1);p.inputs['Roughness'].default_value=r['roughness'];p.inputs['Metallic'].default_value=r['metallic'];materials[k]=m
 if k=='Labels':
  t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(OUT/'Textures/T_FT_Wayfinding.png'));m.node_tree.links.new(t.outputs['Color'],p.inputs['Base Color'])
def B(k,c,s,m='Concrete',col=False):g.box(k,c,s,m,collision=col)
def sign(key,c,w,n=(0,-1,0),kind='Signs'):
 rect=ATLAS['rects'][key];h=w*(rect[3]-rect[1])/(rect[2]-rect[0]);g.printed_plate(kind,c,w,h,key,n,ATLAS,depth=.025)
def rail(a,b):g.rail(a,b,'Rails',1.08)
def frame(c,width,height,m='Teal'):
 x,y,z=c
 for s in (-1,1):B('Frames',(x+s*(width/2+.055),y,z+height/2),(.11,.28,height),m,True)
 B('Frames',(x,y,z+height+.065),(width+.22,.28,.13),m,True)
def tile(x0,y0,x1,y1,z,kind='Floor'):
 nx=math.ceil((x1-x0)/1.5);ny=math.ceil((y1-y0)/1.5);dx=(x1-x0)/nx;dy=(y1-y0)/ny
 for i in range(nx):
  for j in range(ny):B(kind,(x0+(i+.5)*dx,y0+(j+.5)*dy,z-.021),(dx-.01,dy-.01,.042),'Floor')
def fixture(c,kind='Fixtures',length=1.6):
 x,y,z=c;B(kind,(x,y,z+.09),(length,.32,.16),'Teal');B('Diffusers',(x,y,z-.003),(length-.09,.255,.025),'Glow')
 for dx in (-length*.35,length*.35):
  g.cylinder('Hangers',(x+dx,y,z+.17),(x+dx,y,8.38),.009,'Steel',8)
  B('HangerAnchors',(x+dx,y,8.38),(.12,.12,.06),'Steel')

g.ROOM='Hall'
B('Slab',(0,0,-.22),(48.6,36.6,.36),'Concrete',True);g.box(None,(0,0,-.02),(48,36,.04),collision='Slab');tile(-24,-18,24,18,0)
# West arrival and three 7.6m facade recesses; portals themselves carry the 3x2.8m throat.
for lo,hi in [(-18,-1.5),(1.5,18)]:B('Walls',(-24.16,(lo+hi)/2,4.2),(.32,hi-lo,8.4),'Concrete',True)
B('Walls',(-24.16,0,5.7),(.32,3,5.4),'Concrete',True)
for lo,hi in [(-18,-3.8),(3.8,18)]:B('Walls',(24.16,(lo+hi)/2,4.2),(.32,hi-lo,8.4),'Concrete',True)
B('Walls',(24.16,0,6.9),(.32,7.6,3.0),'Concrete',True)
for side in (-1,1):
 for lo,hi in [(-24,4.2),(11.8,24)]:B('Walls',((lo+hi)/2,side*18.16,4.2),(hi-lo,.32,8.4),'Concrete',True)
 B('Walls',(8,side*18.16,6.9),(7.6,.32,3.0),'Concrete',True)
 for lo,hi in [(-23.8,4.12),(11.88,23.8)]:
  for z in (.12,1.2):B('Skirting',((lo+hi)/2,side*17.975,z),(hi-lo,.04,.09 if z<.5 else .035),'Teal')
B('Roof',(0,0,8.55),(48.6,36.6,.30),'Concrete',True)
for x in (-23,-15,-7,1,9,17,23):
 B('RoofBeams',(x,0,8.03),(.26,36,.64),'Teal');B('RoofBeams',(x,0,7.70),(.42,36,.04),'Steel')
 for y in (-17.75,17.75):
  # Columns stay out of the three portal bays.
  if 4<x<12:continue
  g.i_column(x,y,7.7)
for side in (-1,1):
 g.rounded_pipe('HighServices',[(-23,side*17.65,7.30),(23,side*17.65,7.30)],.075,'Enamel',24)
 for x in (-20,-12,-4,4,12,20):
  g.flange('HighServices',(x,side*17.65,7.30),(1,0,0),.075,6)
  g.cylinder('ServiceBrackets',(x,side*17.69,7.22),(x,side*17.97,7.22),.019,'Steel',12)
# Arrival corridor lines up with the reception's 3m wide, 3m high eastern sleeve.
B('Approach',(-28,0,-.17),(8,3.64,.3),'Concrete',True);tile(-32,-1.5,-24,1.5,0,'ApproachFloor')
for sy in (-1,1):
 B('Approach',(-28,sy*1.64,1.5),(8,.28,3),'Concrete',True)
 B('ApproachTrim',(-28,sy*1.485,.96),(8,.035,.085),'Steel')
B('Approach',(-28,0,3.14),(8,3.56,.28),'Concrete',True)
for x in (-30.4,-26.6):sign('brief' if x<-28 else 'rules',(x,1.477,1.85),2.5)
sign('welcome',(-23.96,0,3.40),1.6,(1,0,0));sign('return',(-23.96,3.0,1.90),1.8,(1,0,0))
for x in (-29,-25.6):B('CorridorFixture',(x,0,2.88),(1.3,.3,.17),'Teal');B('Diffusers',(x,0,2.78),(1.22,.24,.02),'Glow')
# West observation platform. Open floor below, outer stairs avoid all branch queues.
B('GallerySlab',(-20,0,4.0),(8,36,.36),'Concrete',True);tile(-24,-18,-16,18,4.2,'UpperFloor')
g.box(None,(-20,0,4.18),(8,36,.04),collision='GallerySlab')
for y in (-12,-6,6,12):
 B('GalleryColumns',(-16.3,y,1.91),(.34,.34,3.82),'Teal',True);B('GalleryColumns',(-16.3,y,.045),(.56,.56,.09),'Steel',True)
import importlib.util
stairs_spec=importlib.util.spec_from_file_location('facility_stair_recipe',ROOT/'RefineV3/stair_recipe.py');stairs=importlib.util.module_from_spec(stairs_spec);stairs_spec.loader.exec_module(stairs);stairs.build(g)
for side in (-1,1):
 sign('balcony',(-4.6,side*17.97,2.1),2.6,(0,-side,0))
# Upstairs duty room, walls support actual glass and a native interactive door.
for y in (-10,1):B('OfficeWalls',(-21.6,y,6.0),(5.0,.18,3.6),'Concrete',True)
B('OfficeRoof',(-21.6,-4.5,7.89),(5.0,11.18,.18),'White',True)
for lo,hi in [(-10,-1.415),(-.185,1)]:
 B('OfficeWalls',(-19.2,(lo+hi)/2,4.715),(.16,hi-lo,1.03),'Stone',True)
 B('OfficeWalls',(-19.2,(lo+hi)/2,7.45),(.16,hi-lo,.8),'Concrete',True)
B('OfficeWalls',(-19.2,-9.85,6.14),(.16,.30,1.84),'Concrete',True)
for y,width in [(-9.74,.08),(-7,.20),(-4.2,.20),(-1.45,.10),(-.185,.07),(1,.08)]:B('OfficeFrames',(-19.2,y,6.14),(.24,width,1.84),'Teal',True)
for z in (5.23,7.08):B('OfficeFrames',(-19.2,-5.7,z),(.24,8.52,.06),'Teal',True)
B('OfficeWalls',(-19.2,-.8,7.2),(.16,1.23,1.2),'Concrete',True)
for y in (-1.40,-.20):B('OfficeFrames',(-19.2,y,5.4),(.24,.07,2.4),'Teal',True)
B('OfficeFrames',(-19.2,-.8,6.63),(.24,1.27,.06),'Teal',True)
sign('duty',(-19.055,-5.1,7.5),2.4,(1,0,0));sign('rules',(-23.965,-5.4,6.45),2.0,(1,0,0))
# Wall-backed service zone and grounded shelves, lockers kept clear of stairs.
sign('ppe',(-1.1,17.974,2.70),3.4)
sign('service',(-1,-17.974,2.7),3.3,(0,1,0))
B('ServiceBench',(-.5,-17.25,.81),(6.4,.90,.08),'Wood',True)
for x in (-3.55,-.5,2.55):
 for y in (-17.60,-16.90):B('ServiceBench',(x,y,.405),(.075,.075,.81),'Steel',True)
B('ServiceBench',(-.5,-17.25,.23),(6.3,.78,.04),'Steel',True)
for x in (-2.8,1.6):
 B('MaintenancePanel',(x,-17.94,1.85),(.72,.12,.62),'Teal');B('MaintenancePanel',(x,-17.86,1.85),(.61,.035,.50),'Dark')
 for dx in (-.17,0,.17):g.cylinder('PanelIndicators',(x+dx,-17.838,1.98),(x+dx,-17.816,1.98),.025,'Glow',16)
# Inlaid floor guidance lies on a separate 8mm physical strip, not coplanar decals.
for a,b in [((-21,0,.008),(17,0,.008)),((5,.06,.008),(5,15,.008)),((11,-.06,.008),(11,-15,.008))]:g.beam('FloorGuidance',a,b,.10,.016,'Brass')
for j,(c,n) in enumerate([((22.7,0,4.75),(-1,0,0)),((8,16.7,4.75),(0,-1,0)),((8,-16.7,4.75),(0,1,0))]):
 sign('route'+str(j+1),c,3.2,n)
 # Physical brackets connect suspended signs to beams, behind their print plane.
 for tangent in (-1,1):
  ax=c[0]+(tangent*1.1 if abs(n[1])>.5 else 0);ay=c[1]+(tangent*1.1 if abs(n[0])>.5 else 0)
  g.cylinder('SignHangers',(ax,ay,5.46),(ax,ay,8.38),.014,'Steel',12)
  B('HangerAnchors',(ax,ay,8.38),(.14,.14,.06),'Steel')
for p in CFG['lights']:
 if p['type']=='spot':fixture([p['position_m'][0],p['position_m'][1],7.04])
 elif not p['id'].startswith('Approach'):
  x,y,z=p['position_m'];B('LocalFixtures',(x,y,z+.17),(1.3,.30,.18),'Teal');B('Diffusers',(x,y,z+.07),(1.22,.24,.022),'Glow')
  if p['id'].startswith('Gallery'):
   ceiling=7.80 if -10<y<1 else 8.40
   for dx in (-.42,.42):
    g.cylinder('Hangers',(x+dx,y,z+.26),(x+dx,y,ceiling-.02),.01,'Steel',8);B('HangerAnchors',(x+dx,y,ceiling-.02),(.10,.10,.05),'Steel')
# Reception's retained outer cap; original combined cap mesh is omitted from connected copies.
B('ReceptionEntryCap',(-86.15,0,1.7),(.30,4.5,3.4),'Concrete',True)

for theme in CFG['themes']:
 g.ROOM=theme['id'];m=theme['code'];key=theme['id']
 # 7.6m-wide facade, shoulder depth 0.7m, 4m long standard clear passage.
 for s in (-1,1):
  B('Body',(s*2.65,.18,2.7),(2.3,.36,5.4),'Concrete',True)
  B('Body',(s*1.64,2,1.4),(.28,4,2.8),'Concrete',True)
  B('Jambs',(s*1.54,-.17,1.4),(.08,.48,2.8),m,True)
 B('Body',(0,.18,4.10),(3,.36,2.6),'Concrete',True)
 B('Throat',(0,2,2.93),(3.56,4,.26),'Concrete',True)
 B('Throat',(0,2,-.17),(3.56,4,.3),'Concrete',True);tile(-1.5,0,1.5,4,0,'ThroatFloor')
 B('Jambs',(0,-.17,2.855),(3.16,.48,.11),m,True)
 for s in (-1,1):
  B('Cladding',(s*2.65,-.038,2.2),(2.24,.055,4.32),m)
  B('Kickplates',(s*2.65,-.075,.27),(2.20,.027,.5),'Steel')
  for z in (.16,1.5,3.6):
   for x in (s*1.66,s*3.64):g.bolt('Hardware',(x,-.085,z),(0,-1,0),.011)
 B('Canopy',(0,-.39,4.5),(7.6,.92,.20),m)
 B('Diffusers',(0,-.52,4.389),(3.4,.18,.025),'Glow')
 sign(key,(0,-.15,3.58),3.0)
 sign(key+'_notice',(2.65,-.25,2.2),1.76)
 for x in (1.89,3.41):B('NoticeMounts',(x,-.15,2.2),(.06,.16,.5),'Steel')
 for z in (.3,1.15):
  for s in (-1,1):B('PassageTrim',(s*1.474,2,z),(.045,3.95,.09),m)
 for y in (1.0,3.0):B('TunnelLight',(0,y,2.70),(1.20,.20,.12),m);B('Diffusers',(0,y,2.629),(1.13,.15,.02),'Glow')
 if key=='freight':
  for s in (-1,1):
   for x in (s*1.90,s*3.35):
    B('DockProtection',(x,-.20,.72),(.20,.26,1.38),'Rubber',True)
    for z in (.24,.58,.92,1.26):B('BumperBand',(x,-.338,z),(.19,.018,.065),'Yellow')
   for z in (1.8,2.9,3.8):B('Ribbing',(s*2.67,-.12,z),(2.12,.13,.10),'Steel')
  B('ShutterCassette',(0,.57,3.16),(3.35,.70,.52),'Dark')
  for i in range(7):B('ShutterCassette',(0,.209,2.96+i*.062),(3.20,.03,.04),'Steel')
 elif key=='medical':
  for s in (-1,1):
   for i in range(7):
    for j in range(8):B('CleanTiles',(s*(1.53+(i+.5)*.32),-.079,.52+(j+.5)*.32),(.311,.025,.311),'White')
   B('Kickplates',(s*2.65,-.108,.27),(2.20,.02,.5),'Steel')
  B('AirPlenum',(-2.65,-.22,3.55),(1.75,.34,.52),'White')
  for i in range(18):B('HEPALouvres',(-3.4+i*.087,-.403,3.55),(.035,.022,.37),'Steel')
  # Distinct inset cross symbol beside the entry.
  B('MedicalSymbol',(-2.65,-.105,2.25),(.18,.04,.75),m);B('MedicalSymbol',(-2.65,-.108,2.25),(.75,.04,.18),m)
 elif key=='treatment':
  for s in (-1,1):
   for i in range(5):B('HeatShields',(s*(1.77+i*.42),-.12,1.72),(.385,.08,2.32),'Dark')
   g.cylinder('Bollards',(s*1.95,-.67,.06),(s*1.95,-.67,1.12),.105,'Yellow',32,True)
   for z in (.36,.71):g.ring('Bollards',(s*1.95,-.67,z),(0,0,1),.108,.102,.16,'Dark',32)
  B('ExtractDuct',(-2.7,-.43,4.04),(1.10,.76,1.85),'Steel')
  for z in (3.28,3.80,4.35,4.80):B('DuctBands',(-2.7,-.43,z),(1.17,.83,.045),'Dark')
  B('ExtractDuct',(-2.7,-.827,3.7),(.86,.035,.60),'Dark')
  for i in range(11):B('VentBlades',(-2.7,-.85,3.43+i*.053),(.81,.036,.026),'Steel')
 elif key=='staff_living':
  for s in (-1,1):
   for i in range(17):B('WoodPanelling',(s*(1.59+i*.128),-.12,1.28),(.115,.11,1.95),'Wood')
   B('SoftSconce',(s*2.65,-.18,3.0),(.35,.24,.55),'Brass');B('SoftSconce',(s*2.65,-.316,3.0),(.27,.025,.43),'Glow')
  sign('rules',(-2.65,-.189,2.15),1.75)
 elif key=='ecology':
  for x,r in [(-3.4,.085),(-3.02,.055)]:
   g.rounded_pipe('WaterRisers',[(x,3.7,.55),(x,-.34,.55),(x,-.34,4.98),(x,3.7,4.98)],r,'Enamel',24)
   for z in (.90,3.5,4.62):g.flange('WaterRisers',(x,-.34,z),(0,0,1),r,6)
  g.ring('ValveWheel',(-3.4,-.62,1.38),(0,1,0),.23,.20,.035,'Red',40)
  g.cylinder('ValveStem',(-3.4,-.38,1.38),(-3.4,-.64,1.38),.03,'Steel',20)
  for a in (0,math.pi/2):g.beam('ValveWheel',(-3.4-math.cos(a)*.2,-.64,1.38-math.sin(a)*.2),(-3.4+math.cos(a)*.2,-.64,1.38+math.sin(a)*.2),.025,.025,'Red')
  g.cylinder('Gauge',(-2.37,-.10,2.48),(-2.37,-.29,2.48),.20,'Steel',48);g.cylinder('Gauge',(-2.37,-.295,2.48),(-2.37,-.303,2.48),.172,'White',48)
  g.beam('Gauge',(-2.37,-.313,2.48),(-2.45,-.313,2.59),.012,.014,'Dark')
  for i in range(10):
   a=math.radians(-135+i*30);g.beam('Gauge',(-2.37+math.sin(a)*.13,-.314,2.48+math.cos(a)*.13),(-2.37+math.sin(a)*.154,-.314,2.48+math.cos(a)*.154),.007,.008,'Dark')
 elif key=='power':
  B('ElectricalBacking',(-2.65,-.15,2.2),(1.76,.18,2.8),'Dark')
  B('Isolator',(-2.65,-.36,1.48),(1.02,.32,.83),m,True)
  B('Isolator',(-2.65,-.533,1.48),(.90,.026,.70),'Dark')
  g.cylinder('DisconnectHandle',(-2.65,-.57,1.48),(-2.65,-.66,1.48),.11,'Red',32)
  g.beam('DisconnectHandle',(-2.65,-.69,1.37),(-2.65,-.69,1.69),.055,.045,'Red')
  for x in (-3.13,-2.65,-2.17):
   g.insulator((x,-.30,2.65),.52,.095)
   g.rounded_pipe('Cables',[(x,-.30,3.23),(x,-.30,4.98),(x,3.8,4.98)],.030,'Rubber',14)
  g.tray((-3.45,-.28),(-1.83,-.28),4.88,.55)
 # Separate universal sample stop, excluded from module/gate kits.
 B('SampleCap',(0,4.14,1.4),(3.54,.28,2.8),'Dark',True);sign('closed',(0,3.988,1.65),2.2,kind='SampleSign')

records=[]
def export(obj,room,kind,hulls,mapping,nanite=True,**extra):
 bpy.ops.object.select_all(action='DESELECT');obj.hide_set(False);obj.select_set(True);bpy.context.view_layer.objects.active=obj
 bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
 if kind not in ('Signs','SampleSign','Floor','UpperFloor','ThroatFloor','ApproachFloor','Glass','Fracture'):
  mod=obj.modifiers.new('Fabricated edge radii','BEVEL');mod.width=.0025;mod.segments=2;mod.limit_method='ANGLE';mod.angle_limit=math.radians(38);bpy.ops.object.modifier_apply(modifier=mod.name)
  mod=obj.modifiers.new('Area weighted normals','WEIGHTED_NORMAL');mod.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 mod=obj.modifiers.new('Export triangles','TRIANGULATE');mod.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=mod.name)
 cols=[]
 for i,(vs,fs) in enumerate(hulls):
  me=bpy.data.meshes.new('UCX_'+obj.name+'_%03d'%i);me.from_pydata(vs,[],fs);me.update();bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
  co=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(co);co.select_set(True);cols.append(co)
 fbx=OUT/(obj.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
 for co in cols:co.hide_set(True);co.hide_render=True
 records.append(dict(name=obj.name,room=room,kind=kind,mesh=BASE+'/Meshes/'+obj.name,fbx=str(fbx),sha256=hashlib.sha256(fbx.read_bytes()).hexdigest(),materials=mapping,triangles=len(obj.data.polygons),collision=bool(hulls),collision_hulls=len(hulls),nanite=nanite,
  cast_shadow=kind not in ('Signs','SampleSign','Diffusers','Fixtures','LocalFixtures','CorridorFixture','TunnelLight','Hangers','Hardware','SignHangers','Glass','Fracture'),preview_only=kind in ('SampleCap','SampleSign','ReceptionEntryCap'),**extra))
 print('FACILITY_TRANSIT_EXPORTED',obj.name,flush=True)
for (room,kind),data in g.G.items():
 name='SM_FT_'+room+'_'+kind;me=bpy.data.meshes.new(name);me.from_pydata(data['v'],[],data['f']);me.update();obj=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(obj);order=list(dict.fromkeys(data['m']))
 for role in order:me.materials.append(materials[role])
 me.uv_layers.new(name='UVMap');vc=me.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER');uv=me.uv_layers['UVMap']
 for face,role,coords,smooth in zip(me.polygons,data['m'],data['uv'],data['smooth']):
  face.material_index=order.index(role);face.use_smooth=smooth;axes=[a for a in range(3) if a!=max(range(3),key=lambda k:abs(face.normal[k]))];s=ROLES[role].get('uv_meters_override',ROLES[role].get('uv_meters',1))
  for j,li in enumerate(face.loop_indices):
   p=me.vertices[me.loops[li].vertex_index].co;uv.data[li].uv=coords[j] if coords else (p[axes[0]]/s,p[axes[1]]/s);vc.data[li].color=(.012+.045*math.exp(-max(p.z,0)/.25),0,0,1)
 export(obj,room,kind,g.C.get((room,kind),[]),{'FT_'+r:ROLES[r]['existing_ue_path'] for r in order},kind not in ('Signs','SampleSign','Diffusers'))
# Accepted native breakable glass recipe, resized geometrically instead of scaling its actor.
stock=json.loads((PROJECT/'SourceAssets/StationWorkshop20261003/RefineV2/Authored/manifest.json').read_text('utf8'))
glasspath=next(iter(next(x for x in stock['objects'] if x['name']=='SM_SW_WindowPaneV5')['materials'].values()));glass=bpy.data.materials.new('FT_Glass')
def cube(name,center,size,material=None):
 bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
 if material:o.data.materials.append(material)
 return o
def export_glass(obj,kind,boxes=(),shards=0):
 obj.name='SM_FT_'+kind;hulls=[]
 for c,s in boxes:
  o=cube('CollisionTemporary',c,s);hulls.append(([tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons]));bpy.data.objects.remove(o,do_unlink=True)
 export(obj,'Hall','Fracture' if shards else 'Glass',hulls,{'FT_Glass':glasspath},False,shards=shards)
text=(PROJECT/'SourceAssets/DungeonIsolationWard20260929/Scripts/author_breakable_glass.py').read_text('utf8');text=text[text.index('def clipped('):text.index("panes('Door'")]
text=text.replace(' for face,attr in zip(mesh.polygons,attributes):'," uv0=mesh.uv_layers['UVMap'];uv1=mesh.uv_layers['ShardCenter'];uv2=mesh.uv_layers['ShardSeed']\n for face,attr in zip(mesh.polygons,attributes):")
ctx=dict(bpy=bpy,math=math,random=random,cube=cube,export=export_glass,glass=glass);exec(compile(text,'facility_glazing','exec'),ctx);ctx['panes']('Duty',2.60,1.80,.008,12,11,61007)
for im in bpy.data.images:
 if im.source=='FILE' and im.has_data:im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'FacilityTransit_and_SixPortals.blend'))
(ROOT/'manifest.json').write_text(json.dumps(dict(base=BASE,meshes=records,tests_run=False,rendered=False),indent=2),encoding='utf8')
print('FACILITY_TRANSIT_SOURCE_SAVED',len(records),flush=True)
