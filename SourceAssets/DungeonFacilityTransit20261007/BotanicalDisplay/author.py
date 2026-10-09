"""Fabricate a twelve-pane botanical case, physically supported soil bed and guidance detour."""
import bpy,bmesh,math,json,sys,hashlib,random,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parent;PARENT=ROOT.parent;PROJECT=PARENT.parents[1];OUT=ROOT/'Authored'
CFG=json.loads((ROOT/'assembly.json').read_text('utf8'));ROLES=json.loads((ROOT/'materials.json').read_text('utf8'));ATLAS=json.loads((ROOT/'atlas.json').read_text('utf8'));BASE=CFG['base']
sys.path.insert(0,str(PARENT/'Scripts'));import geometry as g
g.ROOM='Botanical';bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
materials={}
for role,r in ROLES.items():
    m=bpy.data.materials.new('FT_'+role);m.use_nodes=True;p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*r['basecolor_linear'],1);p.inputs['Roughness'].default_value=r['roughness'];p.inputs['Metallic'].default_value=r['metallic'];materials[role]=m
    if role=='Labels':
        t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(OUT/'Textures/T_BotanicalDisplay_Label.png'));m.node_tree.links.new(t.outputs['Color'],p.inputs['Base Color'])
Z=(0,0,1)
def radial(r,a,z):return (r*math.cos(a),r*math.sin(a),z)
def soil_z(x,y):return .605+.058*math.exp(-((x-.55)**2+(y+.5)**2)/2.4)+.022*math.sin(2.3*x+1.4*y)*max(0,1-math.hypot(x,y)/3.08)

# Grounded stepped plinth with a separate stone rim, recessed toe and layered metal band.
g.lathe('Plinth',(0,0,0),Z,[(.0,3.37),(.06,3.37),(.10,3.49),(.17,3.49),(.20,3.43),(.52,3.43),(.55,3.38)],'Graphite',144)
g.cylinder('PlinthCollision',(0,0,.02),(0,0,.58),3.42,'Graphite',48,True)
# Collision-only hull shares the visible plinth actor without an overlapping second surface.
g.G.pop(('Botanical','PlinthCollision'));g.C[('Botanical','Plinth')].extend(g.C.pop(('Botanical','PlinthCollision')))
g.ring('StoneRim',(0,0,.59),Z,3.43,3.025,.12,'Stone',144)
g.ring('FootTrim',(0,0,.116),Z,3.501,3.486,.035,'Steel',144)
g.ring('BaseTrim',(0,0,.512),Z,3.445,3.423,.032,'Brass',144)
g.ring('GlazingShoe',(0,0,.677),Z,3.355,3.245,.055,'EC',144)

# One continuous triangulated soil surface with low mounds; no stacked coplanar soil discs.
vs=[(0,0,soil_z(0,0))];fs=[];n=128;nr=12
for j in range(1,nr+1):
    for i in range(n):
        x,y,_=radial(3.085*j/nr,math.tau*i/n,0);vs.append((x,y,soil_z(x,y)))
for i in range(n):fs.append((0,1+i,1+(i+1)%n))
for j in range(nr-1):
    for i in range(n):
        a=1+j*n+i;b=1+j*n+(i+1)%n;c=a+n;d=b+n;fs.extend([(a,c,d),(a,d,b)])
g.poly('Soil',vs,fs,'Soil',smooth=True)

# Each pane sits in its own gasket, captured by corner posts and top/bottom shoes.
for i in range(12):
    a=math.tau*(i+.5)/12;p=radial(3.3,a,3.52)
    g.box('Mullions',p,(.075,.058,5.75),'EC',yaw=a,collision=True)
    for z in (.713,6.312):
        g.box('FrameCaps',radial(3.3,a,z),(.108,.102,.070),'Steel',yaw=a)
        g.bolt('Fasteners',radial(3.348,a,z),radial(1,a,0),.007)
    a=math.tau*i/12;ap=3.3*math.cos(math.pi/12);w=CFG['glass'][0]['width_m']
    for z in (.685,6.355):g.box('PaneSeats',radial(ap,a,z),(.035,w,.027),'Gasket',yaw=a)
    for side in (-1,1):
        p=radial(ap,a,3.52);t=side*(w/2+.002)
        g.box('PaneSeats',(p[0]-math.sin(a)*t,p[1]+math.cos(a)*t,p[2]),(.020,.017,5.66),'Gasket',yaw=a)
g.ring('Crown',(0,0,6.415),Z,3.36,3.215,.19,'EC',144)
g.ring('CrownTrim',(0,0,6.518),Z,3.36,3.215,.016,'Steel',144)
g.ring('CrownLiner',(0,0,6.302),Z,3.245,3.15,.020,'Gasket',144)
# A narrow supported light diffuser ring leaves the roof centre transparent.
g.ring('LightDiffuser',(0,0,6.305),Z,3.145,3.110,.017,'Glow',144)
for a in (0,math.pi):
    g.beam('RoofRibs',radial(.18,a,6.395),radial(3.22,a,6.395),.035,.04,'Steel')
    g.box('LampHousings',radial(1.82,a,6.353),(.46,.20,.065),'Graphite',yaw=a)
    g.box('LampDiffusers',radial(1.82,a,6.315),(.40,.16,.010),'Glow',yaw=a)

# Small-bore irrigation loop and branches are supported on soil, not floating or traversable.
g.tube('Irrigation',[radial(2.81,math.tau*i/144,soil_z(*radial(2.81,math.tau*i/144,0)[:2])+.022) for i in range(145)],.013,'Gasket',12)
for i in range(12):
    a=math.tau*i/12;x,y,z=radial(2.8,a,0);z=soil_z(x,y)+.016
    g.box('PipeClips',(x,y,z-.008),(.055,.045,.02),'Steel',yaw=a)
    g.rounded_pipe('Drippers',[(x,y,z+.01),radial(2.46,a+.035,z+.028),radial(2.41,a+.04,soil_z(*radial(2.41,a+.04,0)[:2])+.022)],.0055,'Gasket',8)
    g.cylinder('Drippers',radial(2.42,a+.04,z),radial(2.42,a+.04,z+.048),.014,'EC',16)

# Curved plinth cladding seams and a removable flush service access cover.
for i in range(12):
    a=math.tau*i/12
    g.box('BaseSeams',radial(3.435,a,.355),(.005,.008,.266),'Gasket',yaw=a)
g.box('ServiceCover',(3.442,0,.345),(.024,.66,.25),'EC')
for y in (-.287,.287):
    for z in (.25,.44):g.bolt('Fasteners',(3.458,y,z),(1,0,0),.006)
for y in (-.17,-.11,-.05,.01,.07,.13,.19):g.box('CoverVents',(3.457,y,.345),(.006,.019,.11),'Graphite')

# A single proportional printed plate on physical stand-offs facing the reception entrance.
g.printed_plate('Signs',(-3.54,0,.355),1.44,.36,'exhibit',(-1,0,0),ATLAS,depth=.02)
for y in (-.56,.56):
    g.beam('LabelSupports',(-3.36,y,.355),(-3.51,y,.355),.045,.13,'Steel')
    for z in (.202,.508):g.bolt('Fasteners',(-3.549,y,z),(-1,0,0),.005)

# Replace the centre-crossing stripe with two smooth branches around the exhibit.
for a,b in [((-21,0,.012),(-6.0,0,.012)),((6.0,0,.012),(17,0,.012)),((5,.07,.012),(5,15,.012)),((11,-.07,.012),(11,-15,.012))]:g.beam('FloorGuidance',a,b,.10,.016,'Brass')
for side in (-1,1):
    # Use a broad rounded rectangular detour: 4.5m to each side, no tight passage.
    pts=[]
    control=[(-6,0),(-5,0),(-5,side*4.55),(-2.7,side*4.55)]
    def cubic(c,t):return tuple((1-t)**3*c[0][j]+3*(1-t)**2*t*c[1][j]+3*(1-t)*t*t*c[2][j]+t**3*c[3][j] for j in range(2))
    pts.extend([(*cubic(control,k/32),.012) for k in range(33)])
    pts.extend([(x,side*4.55,.012) for x in (-1.5,0,1.5,2.7)])
    control=[(2.7,side*4.55),(5,side*4.55),(5,0),(6,0)]
    pts.extend([(*cubic(control,k/32),.012) for k in range(1,33)])
    # Continuous shared edges keep the bends free of overlapping coplanar beam tops.
    vv=[];ff=[]
    for i,p in enumerate(pts):
        a=pts[max(0,i-1)];b=pts[min(len(pts)-1,i+1)];dx=b[0]-a[0];dy=b[1]-a[1];ln=math.hypot(dx,dy);nx=-dy/ln*.0425;ny=dx/ln*.0425
        vv.extend([(p[0]-nx,p[1]-ny,.004),(p[0]+nx,p[1]+ny,.004),(p[0]-nx,p[1]-ny,.020),(p[0]+nx,p[1]+ny,.020)])
    for i in range(len(pts)-1):
        a=i*4;b=a+4;ff.extend([(a+2,b+2,b+3,a+3),(a,a+1,b+1,b),(a,b,b+2,a+2),(a+1,a+3,b+3,b+1)])
    ff.extend([(0,2,3,1),(len(vv)-4,len(vv)-3,len(vv)-1,len(vv)-2)])
    g.poly('FloorGuidance',vv,ff,'Brass')

# Reuse the established FBX/UCX/Nanite authoring recipe with this assembly namespace.
source=(PARENT/'author.py').read_text('utf8');source=source[source.index('records=[]'):source.index('# Accepted native breakable glass recipe')]
exec(compile(source,'botanical_export','exec'),globals())
stock=json.loads((PROJECT/'SourceAssets/StationWorkshop20261003/RefineV2/Authored/manifest.json').read_text('utf8'))
glasspath=next(iter(next(x for x in stock['objects'] if x['name']=='SM_SW_WindowPaneV5')['materials'].values()));glass=bpy.data.materials.new('FT_Glass')
def cube(name,center,size,material=None):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if material:o.data.materials.append(material)
    return o
def export_glass(obj,kind,boxes=(),shards=0):
    obj.name='SM_FT_Botanical_'+kind;hulls=[]
    for c,s in boxes:
        o=cube('CollisionTemporary',c,s);hulls.append(([tuple(v.co) for v in o.data.vertices],[tuple(p.vertices) for p in o.data.polygons]));bpy.data.objects.remove(o,do_unlink=True)
    export(obj,'Botanical','Fracture' if shards else 'Glass',hulls,{'FT_Glass':glasspath},False,shards=shards)
text=(PROJECT/'SourceAssets/DungeonIsolationWard20260929/Scripts/author_breakable_glass.py').read_text('utf8');text=text[text.index('def clipped('):text.index("panes('Door'")]
text=text.replace(' for face,attr in zip(mesh.polygons,attributes):'," uv0=mesh.uv_layers['UVMap'];uv1=mesh.uv_layers['ShardCenter'];uv2=mesh.uv_layers['ShardSeed']\n for face,attr in zip(mesh.polygons,attributes):")
ctx=dict(bpy=bpy,math=math,random=random,cube=cube,export=export_glass,glass=glass);exec(compile(text,'botanical_glazing','exec'),ctx);ctx['panes']('Display',CFG['glass'][0]['width_m'],CFG['glass'][0]['height_m'],.008,7,17,71007)
bpy.ops.mesh.primitive_cylinder_add(vertices=144,radius=3.218,depth=.016,location=(0,0,6.431));o=bpy.context.object;o.name='SM_FT_Botanical_RoofGlass';o.data.materials.append(glass)
bpy.context.scene.cursor.location=(0,0,0);bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
export(o,'Botanical','Glass',[],{'FT_Glass':glasspath},False,roof=True)
for r in records:
    if r['kind'] in ('Signs','Soil','PaneSeats','Irrigation','Drippers','LightDiffuser','LampDiffusers','RoofRibs','Crown','CrownLiner','CrownTrim','LampHousings','Glass','Fracture'):r['cast_shadow']=False
for im in bpy.data.images:
    if im.source=='FILE' and im.has_data:im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'BotanicalDisplay.blend'))
(ROOT/'manifest.json').write_text(json.dumps(dict(base=BASE,meshes=records,tests_run=False,rendered=False),indent=2),encoding='utf8')
print('BOTANICAL_DISPLAY_AUTHORED',len(records),flush=True)
