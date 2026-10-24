"""Re-author the city on retained footprints; preserve ad-host shells and attachments."""
import bpy,ast,json,math,random,sys
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent));from design import *
bpy.ops.wm.open_mainfile(filepath=str(R.parent/'RefinementV15/CloserBay_Source.blend'));scene=bpy.context.scene
for ob in list(scene.objects):
 if ob.type=='MESH' and (ob.name.startswith(('City_','Landmark_')) or ob.name in ['FarCity','FarHeadland']):bpy.data.objects.remove(ob,do_unlink=True)
groups={};buildings=[];mats={m.name:m for m in bpy.data.materials};ATLAS_METRES=(76.8,121.6);FLOOR=3.8
for family in FAMILIES:
 m=bpy.data.materials.new(family);m.use_nodes=True;mats[family]=m;n=m.node_tree.nodes;l=m.node_tree.links;p=next(x for x in n if x.type=='BSDF_PRINCIPLED')
 for suffix,pin in [('BC','Base Color'),('ORM',None),('E','Emission Color')]:
  path=R/'Textures'/f'T_AP17_{family}_E.png' if suffix=='E' else R.parent/'RefinementV7/Textures'/f'T_AP7_{SOURCE_FAMILY[family]}_{suffix}.png'
  t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(path));t.image.pack()
  if pin:l.new(t.outputs['Color'],p.inputs[pin])
  else:
   t.image.colorspace_settings.name='Non-Color';s=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],s.inputs[0]);l.new(s.outputs['Green'],p.inputs['Roughness']);l.new(s.outputs['Blue'],p.inputs['Metallic'])
 p.inputs['Emission Strength'].default_value=.7
for name,color in LIGHTS.items():
 m=bpy.data.materials.new('Light'+name);m.use_nodes=True;p=next(n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED');p.inputs['Base Color'].default_value=(*[x*.25 for x in color],1);p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=1.25 if name=='Gold' else .95;mats['Light'+name]=m
# Retained scene elements must not carry the former full-power neon line.
for role in ['Neon0','Neon1','Neon2','Neon3','WarmLight','Navigation']:
 if role in mats:
  p=next((n for n in mats[role].node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
  if p:p.inputs['Emission Strength'].default_value=.4
tree=ast.parse((PROJECT/'SourceAssets/CyberpunkBayBuildings20261022/author_scene.py').read_text(encoding='utf8'))
helpers={'face','box','outline','shell','ring','beam','equipment','signage','tower'}
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in helpers],type_ignores=[]),'retained_building_grammar','exec'),globals())
baseface=face
def face(g,vs,mat='Frame',uv=None):
 if uv is None:
  a=Vector(vs[0]);n=(Vector(vs[1])-a).cross(Vector(vs[2])-a);dominant=max(range(3),key=lambda i:abs(n[i]));axes=[i for i in range(3) if i!=dominant];uv=[(v[axes[0]]/76.8,v[axes[1]]/121.6) for v in vs]
 if mat in ['Office','Residential','Tech']:mat=current_family
 baseface(g,vs,mat,uv)
current_family='QuietGlass';current_light='LightPearl'
def tier(g,x,y,z,w,d,h,family,neon,seed,roundness=0,taper=1):
 far=g.startswith('Far');family=current_family;light=current_light
 shell(g,x,y,z,w,d,h,family,roundness,taper)
 # Solid mullions plus deliberate architectural illumination, no every-window sparkle.
 count=max(1,int(h/(15.2 if far else 7.6)))
 for i in range(1,count+1):
  zz=min(h,i*h/count);s=1+(taper-1)*zz/h
  ring(g,x,y,z+zz-.5,w*s+.7,d*s+.7,.5,.7,'Frame',roundness)
  if not far and family in ['WarmBands','AmberTerrace'] and i%2==0:
   ring(g,x,y,z+zz-.85,w*s+.95,d*s+.95,.42,.24,light,roundness)
 low=outline(x,y,w+.7,d+.7,roundness);high=outline(x,y,w*taper+.7,d*taper+.7,roundness)
 for i,(a,b) in enumerate(zip(low,high)):
  beam(g,(*a,z),(*b,z+h),.85,.9,'Frame')
  if not far and family in ['PearlVertical','BlueFrame'] and i%2==0:
   na=(Vector(a)-Vector((x,y))).normalized();nb=(Vector(b)-Vector((x,y))).normalized()
   aa=Vector(a)+na*.78;bb=Vector(b)+nb*.78
   beam(g,(*aa,z+2),(*bb,z+h-2),.48,.5,light)
 ring(g,x,y,z+h,w*taper+1,d*taper+1,2,1,'Stone',roundness)
 if not far or seed%4==0:ring(g,x,y,z+h+1.65,w*taper+1.15,d*taper+1.15,.55,.4,light,roundness)
 return(x,y,z+h,w*taper,d*taper,roundness)
rows=json.loads((PROJECT/'SourceAssets/CyberpunkBayBuildings20261022/assembly.json').read_text())['buildings']
roles=['WarmBands','PearlVertical','AmberTerrace','BlueFrame','CopperArcade','QuietGlass'];tints=['Gold','Pearl','Amber','Blue','Gold','Teal'];inventory=[]
for i,row in enumerate(rows):
 if row['group']=='Landmarks':continue
 row={k:row[k] for k in ['group','x','y','width','depth','height','style']}
 # Preserve all host shapes/coordinates; differing lighting now reveals their structure.
 family_index=(i*7+row['style']*3)%6;current_family=roles[family_index];current_light='Light'+tints[family_index]
 if row['group'].startswith('Far'):current_family='QuietGlass';current_light='LightPearl'
 tower(row,i);inventory.append(dict(group=row['group'],x=row['x'],y=row['y'],family=current_family))

def podium(g,x,y,w,d,family):
 shell(g,x,y,5,w*1.1,d*1.1,12,family);ring(g,x,y,16,w*1.14,d*1.14,1.8,1.6,'Stone')
 # Colonnade is lit as a contiguous stone facade with real supporting piers.
 for i in range(9):
  xx=x-w*.47+i*w*.94/8;box(g,(xx,y-d*.56,10.3),(1.5,2.2,10.6),'Stone');box(g,(xx,y-d*.573,10.8),(.65,.15,8.8),'LightGold')
 box(g,(x,y-d*.59,16.7),(w*.9,4.2,1),'Stone');box(g,(x,y-d*.612,16.25),(w*.88,.3,.55),'LightGold')
def crown(g,x,y,z,w,d,light):
 ring(g,x,y,z,w,d,6,1.7,'Frame');ring(g,x,y,z+5.6,w+.3,d+.3,.65,.45,light)

g='Landmark_0';x=-680;y=1430;current_family='PearlVertical';current_light='LightGold';podium(g,x,y,88,86,current_family)
for xx,w,h in [(x-25,33,342),(x+26,29,274)]:
 tier(g,xx,y,17.2,w,69,h,current_family,'Neon0',501,taper=.9);crown(g,xx,y,17.2+h,w*.9,62,'LightGold')
 for side in (-1,1):beam(g,(xx+side*w*.45,y-34.8,18),(xx+side*w*.40,y-31.2,17.2+h),1.1,1.,'LightPearl')
for z in (146,244):shell(g,x,y,z,46,28,11.4,'QuietGlass');box(g,(x,y-14.7,z+.4),(45,.6,.8),'LightGold')

g='Landmark_1';x=-360;y=1490;current_family='QuietGlass';current_light='LightBlue';podium(g,x,y,77,77,'CopperArcade')
tier(g,x,y,17.2,70,70,204,'QuietGlass','Neon0',510,0,.80)
# Tall open portal, rather than another fully glazed rectangular crown.
for side in (-1,1):
 a=(x+side*28,y,221.2);b=(x+side*20,y,291)
 beam(g,a,b,8,42,'Frame');beam(g,(a[0],y-21.4,a[2]),(b[0],y-21.4,b[2]),1.15,.7,'LightBlue')
box(g,(x,y,291),(48,42,6),'Frame');box(g,(x,y-21.4,294),(48,.7,1.1),'LightBlue')
for zz in (89,153,217):ring(g,x,y,zz,70-(zz-17.2)*.068+1,70-(zz-17.2)*.068+1,.6,.4,'LightPearl')

g='Landmark_2';x=-1480;y=1450;current_family='CopperArcade';current_light='LightGold';podium(g,x,y,92,72,current_family)
for i,(z,w,d,h,dx) in enumerate([(17.2,68,62,68,0),(85.2,92,72,76,8),(161.2,76,60,91,-5)]):
 tier(g,x+dx,y,z,w,d,h,current_family,'Neon0',530+i)
 for side in (-1,1):
  yy=y+side*(d/2+1)
  for k in range(3):
   a=(x+dx-w*.45+k*w*.3,yy,z);b=(x+dx-w*.15+k*w*.3,yy,z+h);beam(g,a,b,2.4,2,'Frame');beam(g,(a[0],yy+side*1.05,a[2]),(b[0],yy+side*1.05,b[2]),.65,.5,'LightGold')
crown(g,x-5,y,252.2,62,48,'LightGold')

g='Landmark_3';x=390;y=1680;current_family='WarmBands';current_light='LightGold';podium(g,x,y,78,88,'CopperArcade')
for i,(dx,dy,h) in enumerate([(-23,0,201),(21,15,225),(4,-24,161)]):
 tier(g,x+dx,y+dy,17.2,31,39,h,current_family,'Neon1',551+i,16,.95)
 crown(g,x+dx,y+dy,17.2+h,30,38,'LightGold')

g='Landmark_4';x=1120;y=2420;current_family='QuietGlass';current_light='LightTeal';podium(g,x,y,110,90,'CopperArcade')
tier(g,x,y,17.2,36,40,132,current_family,'Neon2',570,8,.75)
for dx,dy in [(-36,-23),(36,-23),(0,34)]:beam(g,(x+dx,y+dy,17.2),(x+dx*.35,y+dy*.35,158),4.3,5.2,'Frame')
shell(g,x,y,149.2,96,80,22.8,'WarmBands',24,.90)
for zz in (149.5,160,171.5):ring(g,x,y,zz,98-(zz-149.5)*.4,82-(zz-149.5)*.3,1.15,.9,'LightTeal',24)
shell(g,x,y,175,30,30,27,'QuietGlass',8,.7);beam(g,(x,y,202),(x,y,242),1.8,1.8,'LightPearl')

# Source scene and exports use the same closer-bank translation exactly once.
out=R/'Meshes';out.mkdir(exist_ok=True);records=[]
for key,data in groups.items():
 me=bpy.data.meshes.new(key);me.from_pydata(data['v'],[],data['f']);me.update();ob=bpy.data.objects.new(key,me);scene.collection.objects.link(ob);ob.location.y=SHIFT
 order=list(dict.fromkeys(data['m']))
 for role in order:me.materials.append(mats[role])
 uv=me.uv_layers.new(name='ArchitecturalUV')
 for p,role,coords in zip(me.polygons,data['m'],data['uv']):
  p.material_index=order.index(role)
  for li,co in zip(p.loop_indices,coords):uv.data[li].uv=co
 clone=ob.copy();clone.data=me.copy();scene.collection.objects.link(clone);clone.location=(0,0,0);clone.name='SM_AP17_'+key
 for v in clone.data.vertices:v.co=((-v.co.x+10)*1.25,-(v.co.y+SHIFT)*1.25,(v.co.z-90)*1.25)
 bpy.ops.object.select_all(action='DESELECT');clone.select_set(True);bpy.context.view_layer.objects.active=clone;mod=clone.modifiers.new('Triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
 fbx=out/(clone.name+'.fbx');bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
 records.append(dict(key=key,name=clone.name,fbx=str(fbx),triangles=len(clone.data.polygons),materials=order));bpy.data.objects.remove(clone,do_unlink=True)
# Harbor and all retained background slots also use the new dimmer facade masks.
for ob in scene.objects:
 if ob.type!='MESH':continue
 for slot in ob.material_slots:
  if slot.material and slot.material.name in ['Office','Corporate','Financial','Residential','Housing','Terraces','Tech','Data','Harbor']:slot.material=mats['QuietGlass' if ob.name.startswith('Far') else 'CopperArcade']
bpy.ops.wm.save_as_mainfile(filepath=str(R/'ArchitecturalNight_Source.blend'))
(R/'assembly.json').write_text(json.dumps(dict(meshes=records,buildings=inventory,landmarks=5,reference='User-provided Shanghai skyline: horizontal bands, vertical ribs, crowns, dark glazing, silhouette hierarchy'),indent=2))
print('AP17_CITY_AUTHORED',len(inventory),len(records),flush=True)
