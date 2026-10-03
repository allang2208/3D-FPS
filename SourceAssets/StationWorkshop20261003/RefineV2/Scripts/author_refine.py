"""Precision office equipment, readable print faces, bounded spares and live door skins."""
import json,math,random,sys,bmesh
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];PARENT=ROOT.parent;PROJECT=PARENT.parents[1]
sys.path.insert(0,str(ROOT/'Scripts'))
import geometry as g
g.BASE='/Game/Dungeons/StationWorkshop20261003/RefineV2'
g.MAP['Keycaps']='/Game/Dungeons/StationWorkshop20261003/RefineV2/Materials/M_Office_Keycaps'
g.MAP['Legends']='/Game/Dungeons/StationWorkshop20261003/RefineV2/Materials/M_Office_Legends'
g.MAP['Display']='/Game/Dungeons/StationWorkshop20261003/RefineV2/Materials/M_Office_Display'
g.MAP['Glass']='/Game/Dungeons/IsolationWard20260929/Materials/M_WardGlassV2'
for key in ('Keycaps','Legends','Display'):g.MATS[key]=bpy.data.materials.new('RS_'+key)
source=(PARENT/'Scripts/author_workshop.py').read_text('utf8')
helpers=source[source.index('REGIONS='):source.index('# Workshop fits')]
exec(compile(helpers,'workshop_refine_helpers','exec'))
BASE=g.BASE;OUT=g.OUT

def segment(start,end):
    exec(compile(source[source.index(start):source.index(end)],'accepted_workshop_segment','exec'))

# The accepted atlas already has native aspect typography; only its physical reading axes change.
segment('# Detailed notice board','# Parts rack:')
segment('# Loose documents are separate','# Standoffs span')
segment('# Searchable dispatch pedestal','# Loose documents are separate')
segment('cyl((1113,244,61)','# Searchable dispatch pedestal')
segment('cyl((449,546,94)','# Two ceiling fixtures')

# Preserve conduits and wall outlet, but replace the cable crossing the desktop.
electrical=source[source.index('# Power is physically'):source.index('# Dispatch furniture:')]
electrical=electrical.replace('tube([(647,13,90),(647,18,86),(643,25,77),(627,40,77),(615,58.1,87),(615,58.1,102)],.24)',
    '''tube([(647,13,90),(647,19,89),(647,27,85),(642,37,78.5),(621,39,78.5),(607,43,82),(607,56.7,106)],.24)
box((665,8.6,90),(10,3.2,8),'Plastic',.35)
box((665,11,90),(3.8,4,4.6),'Rubber',.35)
for xx in (661.5,668.5):bolt((xx,7.6,90),axis=(0,1,0),r=.35)
tube([(665,13,90),(665,21,87),(665,30,82),(669,38,78.4),(698,46,78.4),(703,66,78.4),(698,75,80.3)],.24)''')
exec(compile(electrical,'electrical_reroute','exec'))

# Stand and monitor: thin bezel, rear enclosure seam, ventilation and actual connector sockets.
box((595,60,111),(51,4.2,30.6),'Plastic',.6)
box((595,62.17,111),(49.8,.5,29.4),'Rubber',.25)
printed((595,62.47,111),46.4,26.1,'Monitor',normal=(0,1,0),mat='Screen')
box((595,60,89),(4,3.8,21),'Steel',.25)
box((595,61.5,78.35),(25,16,1.7),'Steel',.45)
box((595,60,91),(6.5,4.4,4.5),'Plastic',.4)
for x in (573,575.5,578):bolt((x,62.55,97.3),axis=(0,1,0),r=.28)
for x in range(576,615,3):box((x,57.84,117.5),(1.0,.2,6),'Rubber',.08)
for x,y,z in ((607,57.7,106),(604,57.7,106),(583,57.7,104)):
    box((x,y,z),(2.5,.8,1.9),'Rubber',.2)
box((607,56.6,106),(1.9,1.8,1.6),'Rubber',.18)
box((583,56.6,104),(2.7,1.7,1.2),'Steel',.08)

# Keyboard: separate tray, inset deck, six staggered rows, navigation cluster and numpad.
box((590,95.1,78.18),(45.5,16.5,1.36),'Plastic',.32)
box((590,95.1,78.9),(43.8,15.1,.22),'Rubber',.08)
keylabels=[]
def key(x,y,w,label,row=0):
    h=1.82;z=79.28
    box((x,y,z),(w,h,.65),'Keycaps',.13)
    index=len(keylabels);keylabels.append(dict(text=label,index=index))
    c=Vector((x,y,z+.33));u=Vector((1,0,0));v=Vector((0,-1,0))
    legend_width=min(w-.28,1.7)
    verts=[b(c+u*xx*legend_width/2+v*yy*legend_width/2) for xx,yy in ((-1,-1),(1,-1),(1,1),(-1,1))]
    mesh=bpy.data.meshes.new('Key legend '+label);mesh.from_pydata(verts,[],[(0,1,2,3)]);mesh.update()
    o=bpy.data.objects.new('Key '+label,mesh);bpy.context.scene.collection.objects.link(o);mesh.materials.append(g.MATS['Legends'])
    uv=mesh.uv_layers.new(name='UVMap');col=index%16;rr=index//16
    coords=[((col+.08)/16,1-(rr+.92)/8),((col+.92)/16,1-(rr+.92)/8),((col+.92)/16,1-(rr+.08)/8),((col+.08)/16,1-(rr+.08)/8)]
    for li in mesh.polygons[0].loop_indices:uv.data[li].uv=coords[mesh.loops[li].vertex_index]
    g.parts.append(o)
key(570,88.7,1.82,'Esc')
for i in range(12):key(574+i*2.05,88.7,1.82,'F'+str(i+1))
rows=[('` 1 2 3 4 5 6 7 8 9 0 - = Back',90.85,569.9,0),
      ('Tab Q W E R T Y U I O P [ ]',92.98,570.6,1),
      ('Caps A S D F G H J K L ; Enter',95.11,571.1,2),
      ('Shift Z X C V B N M , . / Shift',97.24,571.5,3)]
for text,y,x0,row in rows:
    x=x0
    for label in text.split():
        width={'Tab':2.6,'Caps':3.1,'Shift':3.5,'Enter':3.1,'Back':3.0}.get(label,1.82)
        key(x+width/2,y,width,label,row);x+=width+.24
for x,label in [(572,'Ctrl'),(575,'Win'),(578,'Alt'),(593,'Alt'),(596,'Fn'),(599,'Ctrl')]:key(x,99.37,2.6,label)
key(585.6,99.37,11.2,'Space')
for r,text in enumerate(('Ins Home PgUp','Del End PgDn','Num / *','7 8 9','4 5 6','1 2 3')):
    for col,label in enumerate(text.split()):key(603.3+col*2.2,88.7+r*2.13,1.82,label)
for x,label in [(603.3,'0'),(605.5,'.'),(607.7,'+')]:key(x,101.48,1.82,label)
for x in (571,609):
    box((x,91,77.75),(3.2,3,.5),'Rubber',.1)
for x in (604,606,608):cyl((x,86.7,79.05),.13,.18,'Lamp',sides=16)
box((590,86.68,78.4),(1.9,1.2,.8),'Rubber',.1)

# Mouse: rounded ellipsoid shell, independent buttons, centre seam and a ribbed scroll wheel.
box((626,95.2,77.8),(20,21,.5),'Rubber',.3)
bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=24,location=b((626,94.5,79.1)))
o=bpy.context.object;o.scale=(.031,.05,.016);g.finish(o,'Plastic',0)
for f in o.data.polygons:f.use_smooth=True
for x in (624.5,627.5):box((x,91.8,79.97),(2.4,4.6,.6),'Keycaps',.25)
box((626,91.5,80.3),(.25,4.5,.15),'Rubber',.02)
cyl((626,91.0,80.35),.52,1.02,'Rubber',axis=(1,0,0),sides=40)
for x in (625.7,625.9,626.1,626.3):ring((x,91,80.35),.52,.045,'Steel',axis=(1,0,0))
box((626,89.6,79.15),(1.1,1.8,.75),'Rubber',.16)

# Compact PC with front ports, fan grille, power ring and connected rear USB/power plugs.
box((694,87,91.6),(12,20,28.2),'Plastic',.45)
box((694,97.16,91.7),(10.8,.45,26.6),'Steel',.2)
for z in (82.3,84,85.7,87.4):box((694,97.48,z),(8,.22,.55),'Rubber',.08)
cyl((696.8,97.55,101.4),.78,.3,'Steel',axis=(0,1,0),sides=32)
ring((696.8,97.74,101.4),.57,.08,'Lamp',axis=(0,1,0))
for x in (691,694):box((x,97.5,96.2),(1.5,.45,.55),'Rubber',.06)
for z in (82.6,85.2,88,91):box((689,76.8,z),(2.5,.9,1),'Steel',.1)
box((698,76.8,80.3),(2.1,.9,1.6),'Rubber',.12)
for x in (690,698):box((x,87,77.85),(1.2,12,.7),'Rubber',.12)
for x in (688,700):
    for z in (91,93.5,96,98.5):box((x,86,z),(.17,13,.65),'Rubber',.07)
for z in (85.2,88):box((689,75.7,z),(2,2,1.1),'Rubber',.12)
box((698,75.6,80.3),(1.6,2,1.5),'Rubber',.18)

# Telephone: cradle under the receiver, curved handset, display and twelve individual buttons.
box((538,68,79.6),(15.5,19,4.2),'Plastic',.65)
box((538,73.3,81.9),(12,10,.45),'Rubber',.22)
for row in range(4):
    for col in range(3):
        box((534.4+col*3.6,70+row*2.05,82.4),(2.8,1.65,.75),'Keycaps',.25)
box((538,65,82.1),(7.3,2.8,.45),'Display',.15)
for x in (532.3,543.7):box((x,61.7,82.4),(3.6,5.3,1.4),'Plastic',.4)
tube([(531,61.5,84.8),(532,60.6,86.4),(535,60.5,87.1),(541,60.5,87.1),(544,60.6,86.4),(545,61.5,84.8)],1.22)
for x in (531,545):
    box((x,61.5,84.8),(3.9,5.4,2.6),'Plastic',.65)
    for dx in (-.8,0,.8):box((x+dx,64.25,84.8),(.17,.16,1.35),'Rubber',.04)
coil=[]
for i in range(145):
    t=i/144;coil.append((547+.58*math.sin(t*math.tau*12),64+t*13,83.5+.58*math.cos(t*math.tau*12)))
tube([(545.8,63,84.7),(547,64,83.5)]+coil+[(547,78.5,82),(545.7,78.5,80.7)],.12)
box((545.9,78.5,80.7),(1.6,1.1,1.1),'Rubber',.12)

# Handheld radio with speaker grille, channel dial, antenna collar and belt clip.
box((691,53,86.9),(6.4,4.2,18.8),'Plastic',.6)
box((691,55.3,89),(4.7,.6,3.7),'Display',.15)
for z in (80.2,81.8,83.4,85):box((691,55.3,z),(4.3,.3,.57),'Rubber',.07)
for x in (689.6,691,692.4):cyl((x,55.3,92.1),.34,.4,'Keycaps',axis=(0,1,0),sides=20)
cyl((689.5,53,97.3),.75,2.0,'Rubber',sides=32)
cyl((692.2,53,97),.54,1.5,'Steel',sides=32)
cyl((692.2,53,103.4),.27,11.3,'Rubber',sides=24)
box((691,50.65,86),(3,.75,10),'Steel',.2)

# Every lead has two real endpoints. Over the tabletop its centre is >=78.2 cm (top=77.5).
tube([(590,86.6,78.4),(590,83,78.3),(606,80,78.3),(646,78,78.3),(671,73,78.3),(680,72,81),(689,75,85.2)],.16)
tube([(626,89.4,79.1),(628,86,78.4),(640,83,78.4),(665,81,78.4),(681,78,81),(689,75,88)],.14)
box((689,75.7,91),(2,2,1.1),'Rubber',.12)
tube([(583,56,104),(583,50,99),(575,45,82),(576,38,78.3),(665,37,78.3),(681,45,78.3),(689,68,84),(689,75,91)],.22)
tube([(545.5,60.2,80.3),(548,48,78.3),(548,37,78.3),(563,31,76.4),(563,26,67),(559,13.7,62)],.16)
box((559,8.6,62),(7,3.2,5),'Plastic',.2)
for x in (556.8,561.2):bolt((x,10.4,62),axis=(0,1,0),r=.25)
box((559,12,62),(1.7,3.6,1.3),'Rubber',.1)
emit('DispatchElectronics')

# Each bounded state contains actual surface contacts, irregular spacing and varying pile counts.
for state,seed in enumerate((71031,71032,71033)):
    r=random.Random(seed)
    for x0 in (699,743,794):
        x=x0+r.uniform(-6,6);y=r.uniform(632,657);count=r.randint(1,4)
        for k in range(count):
            ring((x+r.uniform(-.35,.35),y+r.uniform(-.35,.35),132.7+k*2.4),5.2,1.2,'Steel',axis=(0,0,1))
    for x in (819+r.uniform(-3,3),839+r.uniform(-2,2)):
        y=r.uniform(633,657);h=r.uniform(11,17)
        cyl((x,y,131.5+h/2),3.2,h,'Steel');ring((x,y,131.5+h),3.0,.22,'Steel',axis=(0,0,1))
    for x,y,yaw in ((706+r.uniform(-4,4),649+r.uniform(-3,3),r.uniform(-8,8)),(751+r.uniform(-3,3),643+r.uniform(-5,5),r.uniform(-15,15))):
        start=len(g.parts);box((x,y,188.5),(34,37,14),'Plastic',.45)
        box((x,y,195.5),(35,38,.9),'Paint',.2);printed((x,y-18.8,188.5),28,5.6,'Tools')
        for o in g.parts[start:]:rotated(o,(x,y,181.5),yaw)
    for k in range(r.randint(5,8)):
        x=792+k*6.8;y=r.uniform(644,658);yaw=r.uniform(-12,12)
        o=cyl((x,y,183),1.5,r.uniform(13,20),'Copper',axis=(0,1,0),sides=28);rotated(o,(x,y,183),yaw)
    emit('RackSpares_'+str(state))

# Closed leaves use the production door's local X thickness / Y width hinge convention.
for kind,width,height in (('PersonnelLeaf',111,240),('ServiceLeaf',105,271)):
    box((0,0,height/2),(4,width,height),'Paint',.5)
    for x in (-2.12,2.12):
        box((x,0,height*.67),(.5,width-22,51),'Plastic',.18)
        box((x,0,height*.25),(.5,width-19,60),'Paint',.2)
        box((x,width/2-13,height*.45),(.8,5,18),'Steel',.2)
        direction=1 if x>0 else -1
        tube([(x,width/2-13,height*.45),(direction*7,width/2-13,height*.45),(direction*7,width/2-25,height*.45)],.75,'Steel')
        cyl((direction*2.9,width/2-13,height*.45-5),.9,.65,'Rubber',axis=(1,0,0),sides=24)
    for z in (24,height/2,height-24):
        cyl((0,-width/2+1.15,z),1.05,11,'Steel',sides=32)
    emit(kind,[((0,0,height/2),(4,width,height))])

# Reuse the hospital's Voronoi shard/UV contract and its material/FX, fitted to these openings.
ward=(PROJECT/'SourceAssets/DungeonIsolationWard20260929/Scripts/author_breakable_glass.py').read_text('utf8')
glass=g.MATS['Glass']
def cube(name,center,size,material=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.scale=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if material:o.data.materials.append(material)
    return o
def export(obj,kind,boxes=(),shards=0):
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    g.parts=[obj];g.emit('SM_SW_'+kind,hulls=boxes);g.records[-1].update(kind=kind,nanite=False,fracture_shards=shards)
exec(compile(ward[ward.index('def clipped('):ward.index("panes('Door'")],'hospital_glass_contract','exec'))
panes('Window',1.5167,1.43,.0065,12,10,71034)

for o in bpy.context.scene.objects:o.hide_set(False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StationWorkshop_RefineV2.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=g.records,regions=REGIONS,keylabels=keylabels,
    source='Original precision refinement; existing hospital glass shard contract',tests_run=False,rendered=False),ensure_ascii=False,indent=2),encoding='utf8')
print('STATION_WORKSHOP_V2_AUTHORED',len(g.records),flush=True)
