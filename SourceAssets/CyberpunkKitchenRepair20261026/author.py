"""Kitchen corrective source. Metres, +Y toward wall. No review scene/render."""
from pathlib import Path
import sys,json,math,bpy,bmesh,runpy
from mathutils import Vector
R=Path(__file__).resolve().parent
K=R.parent/'CyberpunkApartmentRebuild20261022/KitchenPilot20261024'
sys.path.insert(0,str(K))
import model as g
from materials import all_materials,simple
from spec import PBR
g.clear();col=bpy.data.collections.new('KIT_Source');bpy.context.scene.collection.children.link(col)
g.M=all_materials(K,PBR)
g.M['Smoke']=simple('Smoke',(.012,.016,.021),.18,.35)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1.

# Closed stainless shell, continuous rounded walls, sloped floor and real drain hole.
# Existing counter aperture 771 x 521 mm; new flange 790 x 540 mm.
k='Sink';cx=-.330
profile=[(.790,.540,.055,.003),(.750,.500,.045,.003),(.714,.464,.052,-.008),
         (.704,.454,.060,-.020),(.670,.410,.075,-.215),(.644,.384,.082,-.235)]
rings=[]
for w,h,r,z in profile:rings.append([(cx+x,y,z) for x,y,_ in g.rounded_rect(w,h,r,z,segments=20)])
n=len(rings[0]);angles=[math.atan2(y,x-cx) for x,y,z in rings[-1]]
rings.append([(cx+.035*math.cos(a),.035*math.sin(a),-.250) for a in angles])
rings.append([(cx+.035*math.cos(a),.035*math.sin(a),-.253) for a in angles])
for w,h,r,z in reversed(profile[1:]):
    rings.append([(cx+x,y,z-.003) for x,y,_ in g.rounded_rect(w+.006,h+.006,r+.003,z,segments=20)])
rings.append([(cx+x,y,0) for x,y,_ in g.rounded_rect(.790,.540,.055,segments=20)])
vs=[p for ring in rings for p in ring];fs=[]
for j in range(len(rings)):
    a=j*n;b=((j+1)%len(rings))*n
    for i in range(n):q=(i+1)%n;fs.append((a+i,a+q,b+q,b+i))
g.poly(k,vs,fs,'Steel',True)
g.ring(k,(cx,0,-.250),(0,0,1),.035,.026,.002,'Steel',96)
g.lathe(k,(cx,0,-.254),(0,0,-1),[(0,.027),(.018,.027),(.018,.024),(0,.024)],'Graphite',64)
# Perforated basket, radial bars over a recessed dark drain throat.
for i in range(12):
    a=i*math.tau/12;p=(cx+.007*math.cos(a),.007*math.sin(a),-.253)
    q=(cx+.024*math.cos(a),.024*math.sin(a),-.253);g.cyl(k,p,q,.0012,'Steel',12)
g.cyl(k,(cx,0,-.257),(cx,0,-.251),.007,'Steel',48)
# Mixer shares one continuous centreline. All mounting feet fit the solid rear deck.
g.lathe(k,(cx,.294,0),(0,0,1),[(0,.026),(.002,.026),(.004,.023),(.008,.022),(.137,.019),(.149,.014)],'Steel',64)
g.ring(k,(cx,.294,.0005),(0,0,1),.026,.023,.001,'Rubber',64)
path=[(cx,.294,.137),(cx,.294,.276)]
for i in range(33):
    a=i*math.pi/32;path.append((cx,.194+.10*math.cos(a),.276+.10*math.sin(a)))
path.extend([(cx,.094,.245),(cx,.094,.230)])
g.tube(k,path,.012,'Steel',32)
g.lathe(k,(cx,.094,.233),(0,0,-1),[(0,.0135),(.012,.0135),(.015,.011)],'Steel',64)
g.ring(k,(cx,.094,.218),(0,0,1),.0105,.008,.001,'Graphite',48)
g.cyl(k,(cx+.014,.294,.112),(cx+.040,.294,.112),.017,'Steel',48)
g.pipe(k,[(cx+.037,.294,.112),(cx+.067,.294,.163)],.006,'Steel',24)
# Closed ceramic dispenser with actual neck/collar, supported beside the basin.
sx,sy=.135,.194
g.lathe(k,(sx,sy,.0002),(0,0,1),[(0,.030),(.004,.037),(.012,.041),(.090,.041),(.110,.034),(.117,.014),(.129,.014)],'Porcelain',80)
g.lathe(k,(sx,sy,.122),(0,0,1),[(0,.016),(.016,.016),(.019,.013)],'Steel',64)
g.pipe(k,[(sx,sy,.135),(sx,sy,.163),(sx-.044,sy,.163),(sx-.048,sy,.153)],.0055,'Steel',24)
for j in range(3):g.box(k,(.640,-.275,.001+j*.0022),(.180,.090,.002),'Linen',.0008,4)

# Special sink carcasses: no top slab or high shelves inside the bowl envelope.
for k in ['SinkBody0','SinkBody1']:
    g.box(k,(0,0,.16),(.590,.645,.022),'Wood',.002,4)
    for x in [-.283,.283]:g.box(k,(x,0,.390),(.024,.645,.46),'Wood',.003,4)
    g.box(k,(0,.316,.516),(.542,.018,.71),'Wood',.002,4)
    g.box(k,(0,-.320,.647),(.542,.020,.032),'Steel',.002,4)
    g.box(k,(0,-.10,.075),(.54,.38,.15),'Graphite',.003,4)
    for x in [-.235,.235]:g.box(k,(x,.0,.028),(.035,.54,.05),'Graphite',.003,4)

# Oven centered on the vacant 600 mm module, opaque smoked glass and full trim.
k='Oven';x=-.020
g.box(k,(x,.006,-.460),(.572,.616,.758),'Graphite',.008,6)
for xx in [x-.278,x+.278]:g.box(k,(xx,-.307,-.461),(.016,.026,.746),'Steel',.003,4)
for z in [-.093,-.829]:g.box(k,(x,-.307,z),(.540,.026,.018),'Steel',.003,4)
g.box(k,(x,-.322,-.144),(.538,.020,.087),'Steel',.005,5)
g.box(k,(x,-.326,-.470),(.536,.024,.543),'Steel',.008,6)
g.box(k,(x,-.339,-.475),(.475,.003,.460),'Smoke',.008,6)
for xx in [x-.165,x+.165]:
    g.lathe(k,(xx,-.334,-.143),(0,-1,0),[(0,.022),(.018,.022),(.021,.019)],'Graphite',64)
    g.box(k,(xx,-.355,-.132),(.002,.001,.009),'Paper',.0004)
g.box(k,(x,-.333,-.144),(.106,.003,.043),'Smoke',.003,4)
g.text(k,'180',(x,-.335,-.152),.023,'Cyan')
g.pipe(k,[(x-.220,-.332,-.238),(x-.220,-.377,-.238),(x+.220,-.377,-.238),(x+.220,-.332,-.238)],.009,'Steel',32)
for j in range(11):g.box(k,(x-.225+j*.045,-.324,-.788),(.030,.003,.012),'Inside',.002,4)
# Hob and oven use the same module centreline and separate support planes.
g.box(k,(x,.010,.009),(.570,.510,.018),'Smoke',.012,6)
for xx in [x-.140,x+.140]:
    for y in [-.115,.135]:g.ring(k,(xx,y,.0187),(0,0,1),.089,.087,.0006,'Steel',96)
g.text(k,'INDUCTION',(x,-.225,.019),.011,'Paper',normal=(0,0,1))

# Connection hardware authored at the existing formal-map world coordinates.
# Blender coordinates here are UE centimetres /100 with Y inverted.
k='PowerHardware'
outlets={'Coffee':(15.78,20.389,1.725),'Kettle':(13.395,20.184,1.445)}
starts={};ends={'Coffee':(14.89,19.950,.977),'Kettle':(13.23,19.887,.962)}
for name,(x,y,z) in outlets.items():
    g.box(k,(x,y,z),(.150,.022,.150),'Graphite',.008,6)
    for dx in [-.053,.053]:g.bolt(k,(x+dx,y-.012,z),r=.003)
    g.box(k,(x,y-.026,z),(.049,.040,.056),'Rubber',.006,5)
    g.lathe(k,(x,y-.027,z-.022),(0,0,-1),[(0,.007),(.022,.006),(.030,.004)],'Rubber',32)
    starts[name]=(x,y-.027,z-.052)
for name,(x,y,z) in ends.items():
    g.box(k,(x,y-.006,z),(.020,.018,.021),'Rubber',.003,4)
    g.lathe(k,(x,y,z),(0,1,0),[(0,.006),(.012,.006),(.018,.0035)],'Rubber',32)
    ends[name]=(x,y+.018,z)
route=runpy.run_path(str(R/'cable_route.py'));route['add_edge_geometry'](g)
rows=g.finish(g.M,R)
bpy.data.objects['KIT_PowerHardware']['CoffeePortHeight']=.977
# Remove only the two obsolete kitchen power assemblies from the original source.
src=R.parent/'CyberpunkApartmentRebuild20261022/RefinementV2/CyberpunkApartment_Rebuild.blend'
with bpy.data.libraries.load(str(src),link=False) as (s,d):d.objects=['SM_AP_ResidentialDetails']
ob=d.objects[0]
if not ob:raise RuntimeError('Residential source object absent')
col.objects.link(ob);before=len(ob.data.polygons)
bm=bmesh.new();bm.from_mesh(ob.data)
faces=[]
for f in bm.faces:
    c=f.calc_center_median()
    if 13.15<c.y<13.50 and .91<c.z<1.23 and (8.70<c.x<9.02 or 10.29<c.x<10.61):faces.append(f)
bmesh.ops.delete(bm,geom=faces,context='FACES');bm.to_mesh(ob.data);bm.free()
if before-len(ob.data.polygons)<100:raise RuntimeError('Expected old cable geometry not removed')
bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
ob.location=(0,0,0);ob.rotation_euler=(0,0,0);ob.scale=(1,1,1)
fbx=R/'FBX/SM_KR_ResidentialDetails.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,use_tspace=True,mesh_smooth_type='FACE',add_leaf_bones=False)
rows.append(dict(key='ResidentialDetails',fbx=str(fbx),materials=[m.name for m in ob.data.materials],triangles=sum(len(p.vertices)-2 for p in ob.data.polygons)))
def ue(p):return [round(p[0]*100,5),round(-p[1]*100,5),round(p[2]*100,5)]
manifest=dict(meshes=rows,basin_depth_cm=25.0,basin_bottom_world_cm=69.7,carcass_intrusion_removed=True,
    old_power_faces_removed=before-len(ob.data.polygons),cables=[dict(name=n,start=ue(starts[n]),end=ue(ends[n]),length_cm=142 if n=='Coffee' else 82) for n in starts])
route['annotate'](manifest)
(R/'geometry.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'KitchenRepair.blend'))
print('KITCHEN_REPAIR_AUTHORED',len(rows),manifest['old_power_faces_removed'])
