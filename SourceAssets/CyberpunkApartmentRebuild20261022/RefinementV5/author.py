"""Precision pocket doors, outward bathroom extension, glazing and fitted details."""
import bpy,bmesh,sys,math,json,ast
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from design import *
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonReceptionHall20261006/Scripts'))
import geometry as g
g.ROOM='Apartment';bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'
world_meshes=set();no_collision=set();placements=[];lights=[];glass_groups=set()
# Reuse the existing precision geometry helpers, without executing the old layout.
source=ast.parse((ROOT.parent/'RefinementV4/author.py').read_text('utf8'))
names={'B','roundbox','pipe','ring','text','world','wall','place','light'}
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in names],type_ignores=[]),'existing_geometry_helpers','exec'),globals())
def pocket_wall(key,axis,const,start,end,thick,doors,other=()):
 world(key)
 intervals=[]
 for d in doors:
  centre=d['p'][0 if axis=='X' else 1];w=d['width'];h=d['height'];a=centre-w-.085;b=centre+w+.085
  intervals.append((a,b,d))
 for a,b,h in other:intervals.append((a,b,dict(portal=True,height=h)))
 def part(a,b,z0,z1,normal=const,depth=thick,role='Wall'):
  if b-a<.001 or z1-z0<.001:return
  c=[(a+b)/2,normal,(z0+z1)/2];s=[b-a,depth,z1-z0]
  if axis=='Y':c[0],c[1]=c[1],c[0];s[0],s[1]=s[1],s[0]
  B(key,c,s,role,True)
 last=start
 for a,b,d in sorted(intervals):
  if a<start-.001 or b>end+.001:raise RuntimeError('Pocket outside solid wall '+key)
  part(last,a,0,HEIGHT)
  if d.get('portal'):part(a,b,d['height'],HEIGHT)
  else:
   centre=d['p'][0 if axis=='X' else 1];h=d['height'];hole=d['width']/2+.07
   part(a,b,h+.09,HEIGHT)
   for lo,hi in [(a,centre-hole),(centre+hole,b)]:
    for side in [-1,1]:part(lo,hi,0,h+.09,const+side*(thick/2-.0125),.025)
    # End cap closes the cavity; the leaf stops 4 cm before it.
    cap=lo+.0125 if hi<centre else hi-.0125
    part(cap-.0125,cap+.0125,0,h+.09)
  last=b
 part(last,end,0,HEIGHT)
 # Plinth trims stay on solid/skin spans and never bridge a door opening.
 cuts=sorted([(d['p'][0 if axis=='X' else 1]-d['width']/2-.07,d['p'][0 if axis=='X' else 1]+d['width']/2+.07) for d in doors]+[(a,b) for a,b,_ in other])
 spans=[];last=start
 for a,b in cuts:spans.append((last,a));last=b
 spans.append((last,end))
 for a,b in spans:
  for side in [-1,1]:
   part(a,b,.008,.125,const+side*(thick/2+.006),.012,'Dark')
doors={d['name']:d for d in DOORS}
pocket_wall('Wall_CorridorSouth','X',6.825,0,14.175,.15,[doors['Master']],[(8.25,12,3.025)])
pocket_wall('Wall_EastPartition','Y',14.175,0,13.75,.15,[doors['Bed2'],doors['Bed3']])
pocket_wall('Wall_Back','X',13.75,5.925,20,.30,[doors['Entry']])
pocket_wall('Wall_Bath1','X',10.175,3.55,5.85,.15,[doors['Bath1']])
pocket_wall('Wall_Bath2','X',10.175,0,3.40,.15,[doors['Bath2']])
pocket_wall('BalconyPocketWall','X',0,8.075,10.80,.28,[doors['Balcony']])
world('Facade')
for a,b in [(0,.62),(3.36,4.02),(11.24,11.98),(15.56,16)]:
 B('Facade',((a+b)*.625,0,HEIGHT/2),((b-a)*1.25,.28,HEIGHT),'Teal',True)
# The former continuous window plinth crossed both new leaf pockets.
for a,b in [(0,8.075),(10.80,20)]:B('Facade',((a+b)/2,0,.10),(b-a,.28,.20),'Dark',True)
B('Facade',(10,0,3.55625),(20,.28,.2625),'Teal',True)

for d in DOORS:
 w=d['width'];h=d['height'];key='Door_'+d['name']+'_Leaf'
 if d['name']=='Balcony':
  # A single optical surface avoids superposed front/back refraction.
  g.poly(key,[(0,-w/2+.035,.075),(0,w/2-.035,.075),(0,w/2-.035,h-.075),(0,-w/2+.035,h-.075)],[(0,1,2,3)],'WindowGlass')
  for side in [-1,1]:roundbox(key,(0,side*(w/2-.0175),h/2),(.040,.035,h),'Dark',.004)
  for z in [.0375,h-.0375]:roundbox(key,(0,0,z),(.040,w-.07,.075),'Dark',.004)
  g.box(None,(0,0,h/2),(.040,w,h),collision=key);glass_groups.add(key)
 else:
  roundbox(key,(0,0,h/2),(.040,w,h),'Armor',.006,col=True)
  # Flush recessed pull; neither side projects beyond the 4.8 cm leaf envelope.
  for side in [-1,1]:
   B(key,(side*.0205,0,1.20),(.001,w*.11,.29),'CabinetInside')
   for yy in [-w*.06,w*.06]:B(key,(side*.022,yy,1.20),(.004,.012,.31),'EdgeSteel')
   for zz in [1.045,1.355]:B(key,(side*.022,0,zz),(.004,w*.12,.012),'EdgeSteel')
   for zz in [.18,h-.18]:B(key,(side*.0215,0,zz),(.002,w-.13,.009),'Steel')
 # Frame lies flush on both wall faces. Deep pockets have independent wall collision.
 key='Door_'+d['name']+'_Frame'
 for side in [-1,1]:roundbox(key,(0,side*(w/2+.035),h/2),(.16,.070,h),'Dark',.006,col=True)
 roundbox(key,(0,0,h+.045),(.18,w+.14,.09),'Dark',.006,col=True)
 for side in [-1,1]:B(key,(side*.094,0,h+.045),(.008,w-.10,.012),'Cyan')
 # Fine guide channels and seals are part of the frame, not a blocker across the floor.
 for side in [-1,1]:B(key,(side*.026,0,.010),(.008,w+.04,.012),'Rubber')

# New thin-pane system, shared seal geometry and glass edge/spacer detail.
for key in ['WindowFrames','WindowGlass','WindowPaneCollision','WindowHardware']:
 world(key,key=='WindowPaneCollision')
glass_groups.add('WindowGlass')
def glazed(a,b,z0=.20,z1=3.425):
 n=math.ceil((b-a)/1.45);dx=(b-a)/n
 for i in range(n+1):
  x=a+i*dx;roundbox('WindowFrames',(x,0,(z0+z1)/2),(.065,.16,z1-z0),'Dark',.004)
  for sign in [-1,1]:B('WindowFrames',(x,sign*.083,(z0+z1)/2),(.025,.006,z1-z0-.02),'Steel')
 for z in [z0,z1]:roundbox('WindowFrames',((a+b)/2,0,z),(b-a,.17,.055),'Dark',.004)
 for i in range(n):
  left=a+i*dx+.0365;right=a+(i+1)*dx-.0365;lo=z0+.0275;hi=z1-.0275;x=(left+right)/2
  g.poly('WindowGlass',[(left,0,lo),(left,0,hi),(right,0,hi),(right,0,lo)],[(0,1,2,3)],'WindowGlass')
  B('WindowPaneCollision',(x,0,(lo+hi)/2),(right-left,.026,hi-lo),'Grout',True)
  for yy in [-.013,.013]:
   for xx in [left,right]:B('WindowHardware',(xx,yy,(lo+hi)/2),(.009,.010,hi-lo),'Rubber')
   for zz in [lo,hi]:B('WindowHardware',(x,yy,zz),(right-left,.010,.009),'Rubber')
  if hi-lo>1:
   # Sealed drainage slot and concealed corner fixings on the sill.
   for xx in [left+.10,right-.10]:
    roundbox('WindowHardware',(xx,.089,z0),(.075,.006,.009),'CabinetInside',.002)
    g.cylinder('WindowHardware',(xx,.090,z0+.014),(xx,.092,z0+.014),.003,'Steel',16)
for a,b in [(.775,4.2),(5.025,8.075),(10.80,14.05),(14.975,19.45)]:glazed(a,b)
glazed(8.75,10.125,3.05,3.425)
for y in [8.5,9.67,10.83,12.]:roundbox('WindowFrames',(20,y,1.90),(.16,.06,2.75),'Dark',.004)
for z in [.54,3.27]:B('WindowFrames',(20,10.25,z),(.16,3.5,.06),'Dark')
for y in [9.085,10.25,11.415]:
 g.poly('WindowGlass',[(20,y-.55,.565),(20,y+.55,.565),(20,y+.55,3.235),(20,y-.55,3.235)],[(0,1,2,3)],'WindowGlass')
 B('WindowPaneCollision',(20,y,1.90),(.028,1.10,2.67),'Grout',True)
 for yy in [y-.55,y+.55]:B('WindowHardware',(19.985,yy,1.90),(.010,.009,2.67),'Rubber')
 for z in [.565,3.235]:B('WindowHardware',(19.985,y,z),(.01,1.10,.009),'Rubber')

# Bathroom grows outwards to the gym's existing north building line, +50% floor area.
wall('Wall_BathDivider','Y',3.475,8.475,15.425,.15)
wall('Wall_Service','Y',5.925,8.475,15.425,.15)
wall('BathNorthWall','X',15.425,3.55,6.0,.30)
world('Gym_CornerReturns');B('Gym_CornerReturns',(-.075,10.175,HEIGHT/2),(.15,.15,HEIGHT),'Wall',True)
world('BathExtensionSlab');B('BathExtensionSlab',(4.775,14.6625,-.18),(2.45,1.825,.30),'Grout',True)
world('BathFloorCollision');B('BathFloorCollision',(4.70,14.5125,-.015),(2.30,1.525,.03),'Grout',True)
world('BathCeiling');B('BathCeiling',(4.70,12.7625,HEIGHT+.09),(2.42,5.145,.18),'Ceiling',True)
world('BathFinish',False)
for ix in range(4):
 for iy in range(9):B('BathFinish',(3.55+(ix+.5)*2.30/4,10.25+(iy+.5)*5.025/9,.008),(2.30/4-.003,5.025/9-.003,.016),'BathTile')
for x in [3.565,5.835]:
 for iy in range(9):
  for iz in range(6):B('BathFinish',(x,10.25+(iy+.5)*5.025/9,.30+iz*.60),(.026,5.025/9-.003,.597),'BathWall')
for ix in range(4):
 for iz in range(6):B('BathFinish',(3.55+(ix+.5)*2.30/4,15.260,.30+iz*.60),(2.30/4-.003,.026,.597),'BathWall')
for x in [3.60,5.80]:B('BathFinish',(x,12.7625,HEIGHT-.04),(.05,4.94,.08),'Dark')
for y in [10.30,15.22]:B('BathFinish',(4.70,y,HEIGHT-.04),(2.20,.05,.08),'Dark')

# Broad walk-in wet zone with a linear drain and fixed side screen, entry at west.
world('BathShowerBase');roundbox('BathShowerBase',(4.70,14.54,.035),(2.16,1.42,.054),'Ceramic',.014,col=True)
world('BathShowerDetails',False)
roundbox('BathShowerDetails',(4.70,15.08,.065),(1.50,.074,.012),'Steel',.007)
for i in range(45):B('BathShowerDetails',(3.985+i*.032,15.08,.072),(.018,.048,.002),'CabinetInside')
world('BathShowerGlass',False);glass_groups.add('BathShowerGlass')
g.poly('BathShowerGlass',[(4.40,13.81,.06),(4.40,13.81,2.25),(5.78,13.81,2.25),(5.78,13.81,.06)],[(0,1,2,3)],'ShowerGlass')
world('BathShowerFrame')
for x in [4.39,5.79]:roundbox('BathShowerFrame',(x,13.81,1.155),(.025,.032,2.19),'Steel',.004)
B('BathShowerFrame',(5.09,13.81,2.25),(1.425,.026,.026),'Steel')
g.box(None,(5.09,13.81,1.155),(1.425,.035,2.19),collision='BathShowerFrame')
for z in [.32,1.87]:roundbox('BathShowerDetails',(5.795,13.81,z),(.045,.060,.07),'Steel',.006)
# Supported toiletry shelf, pump bottles, towel hooks and extractor louvres.
roundbox('BathShowerDetails',(4.05,15.195,1.05),(.56,.13,.035),'Stone',.009)
for x,height in [(3.91,.20),(4.08,.16)]:
 roundbox('BathShowerDetails',(x,15.19,1.08+height/2),(.07,.07,height),'Plastic',.012)
 g.cylinder('BathShowerDetails',(x,15.19,1.08+height),(x,15.19,1.12+height),.015,'Steel',24)
 B('BathShowerDetails',(x-.018,15.19,1.12+height),(.065,.016,.012),'Steel')
roundbox('BathShowerDetails',(5.15,15.22,3.1),(.52,.06,.26),'Dark',.01)
for i in range(10):B('BathShowerDetails',(4.95+i*.045,15.182,3.1),(.018,.022,.20),'Steel')
for y in [11.05,11.24]:
 g.cylinder('BathShowerDetails',(3.59,y,1.30),(3.66,y,1.30),.012,'Steel',24)
 g.cylinder('BathShowerDetails',(3.66,y,1.30),(3.66,y,1.35),.012,'Steel',24)

# Actual silver mirror, mounted on the west wall above the rotated vanity.
key='BathMirror';world(key,False)
roundbox(key,(3.601,12.70,1.68),(.045,1.08,1.04),'Dark',.016)
roundbox(key,(3.628,12.70,1.68),(.012,1.025,.985),'Mirror',.008)
for y in [12.145,13.255]:B(key,(3.613,y,1.68),(.025,.012,.94),'Warm')
world('BathLighting',False)
for y in [11.65,14.35]:
 roundbox('BathLighting',(4.70,y,HEIGHT-.07),(1.25,.18,.10),'Dark',.01)
 B('BathLighting',(4.70,y,HEIGHT-.125),(1.16,.12,.01),'Warm')
 light('BathV5_'+str(y),[4.70,y,HEIGHT-.14],116,12,1100,radius=340,shadow=False)

world('Thresholds',False)
for d in DOORS:
 size=(d['width']+.10,.26,.006) if d['yaw']==90 else (.26,d['width']+.10,.006)
 B('Thresholds',(d['p'][0],d['p'][1],.015),size,'Steel')
for y,a,b in [(6.825,8.25,12.),(8.475,6.625,9.875),(8.475,11.75,13.05),(8.475,1.375,2.75),(8.475,4.35,5.725)]:B('Thresholds',((a+b)/2,y,.015),(b-a,.25,.006),'Steel')

OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True);materials={};records=[]
for (_,key),data in g.G.items():
 mesh=bpy.data.meshes.new('SM_AP5_'+key);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
 ob=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(ob)
 order=list(dict.fromkeys(data['m']))
 for role in order:
  if role not in materials:
   m=bpy.data.materials.new('AP_'+role);m.diffuse_color=(.12,.15,.18,1);materials[role]=m
  mesh.materials.append(materials[role])
 uv=mesh.uv_layers.new(name='UVMap')
 for p,role,coords,smooth in zip(mesh.polygons,data['m'],data['uv'],data['smooth']):
  p.material_index=order.index(role);p.use_smooth=smooth
  axes=[a for a in range(3) if a!=max(range(3),key=lambda j:abs(p.normal[j]))]
  for j,li in enumerate(p.loop_indices):
   point=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=coords[j] if coords else (point[axes[0]],point[axes[1]])
 bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
 mod=ob.modifiers.new('Triangulated export','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
 # Project final small bevel triangles so imported tangents remain well-defined.
 for p in ob.data.polygons:
  axes=[a for a in range(3) if a!=max(range(3),key=lambda j:abs(p.normal[j]))]
  for li in p.loop_indices:
   point=ob.data.vertices[ob.data.loops[li].vertex_index].co;ob.data.uv_layers.active.data[li].uv=(point[axes[0]],point[axes[1]])
 hulls=[]
 for i,(vs,fs) in enumerate(g.C.get(('Apartment',key),[])):
  hm=bpy.data.meshes.new('UCX_'+ob.name+'_'+str(i));hm.from_pydata(vs,[],fs);hm.update()
  ho=bpy.data.objects.new(hm.name,hm);bpy.context.collection.objects.link(ho);ho.select_set(True);hulls.append(ho)
 fbx=OUT/(ob.name+'.fbx')
 bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',add_leaf_bones=False,use_tspace=True)
 records.append(dict(key=key,name=ob.name,fbx=str(fbx),asset=BASE+'/Meshes/'+ob.name,triangles=len(ob.data.polygons),materials=order,
  collision=bool(hulls),hulls=len(hulls),nanite=key not in glass_groups and not key.startswith('Door_') and len(ob.data.polygons)>15000,
  world=key in world_meshes,hidden=key in ['WindowPaneCollision','BathFloorCollision']))
 for ho in hulls:bpy.data.objects.remove(ho,do_unlink=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'ApartmentV5_Source.blend'))
(ROOT/'assembly.json').write_text(json.dumps(dict(meshes=records,doors=DOORS,lights=lights,retire=RETIRE,
 bath_old=[3.55,10.25,5.85,13.60],bath_new=BATH,bath_area_old_m2=2.3*3.35*SCALE*SCALE,bath_area_new_m2=2.3*5.025*SCALE*SCALE,
 changed_adjacent_room_area_m2=0,pocket_wall_skin_m=.025,pocket_clear_m=.10,max_leaf_thickness_m=.048,
 production_rendered=False),indent=2),encoding='utf8')
print('APARTMENT_V5_AUTHORED',len(records),flush=True)
