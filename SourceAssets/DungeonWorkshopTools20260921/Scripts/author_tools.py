"""Author recognizable tools, local working surfaces and mechanical luminaires; no preview."""
import bpy,bmesh,json,math,random
from pathlib import Path
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/DungeonWorkshopTools20260921');OUT=ROOT/'Authored'
OLD=ROOT.parent/'DungeonWorkshopDetail20260921';ROOM=ROOT.parent/'DungeonRoomInteriors20260921'
R=random.Random(92154)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
exec(compile((ROOT/'Scripts/geometry_helpers.py').read_text(),str(ROOT/'Scripts/geometry_helpers.py'),'exec'),globals())
recipes=json.loads((OUT/'material-manifest.json').read_text());materials={};aliases={}
oldassets=json.loads((OLD/'Receipts/asset-import.json').read_text())
with bpy.data.libraries.load(str(OLD/'Authored/DungeonWorkshopDetail.blend'),link=False) as (src,dst):
    dst.materials=['WSDetail_'+s for s in ('Steel','RackPaint','PaintRed','DarkRubber','BluePlastic','BareEdge')]
for mat in dst.materials:
    key=mat.name.removeprefix('WSDetail_');materials[key]=mat;aliases[mat.name]=oldassets['materials'][key]
for key,recipe in recipes.items():
    mat=bpy.data.materials.new('WSTools_'+key);mat.use_nodes=True
    p=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
    if p is None:
        p=mat.node_tree.nodes.new('ShaderNodeBsdfPrincipled');o=mat.node_tree.nodes.new('ShaderNodeOutputMaterial');mat.node_tree.links.new(p.outputs['BSDF'],o.inputs['Surface'])
    p.inputs['Metallic'].default_value=recipe['metallic'];p.inputs['Roughness'].default_value=recipe.get('roughness',.6)
    if 'color' in recipe:p.inputs['Base Color'].default_value=(*recipe['color'],1)
    if 'emission' in recipe:p.inputs['Emission Color'].default_value=(*recipe['emission'],1);p.inputs['Emission Strength'].default_value=1
    for ch,path in recipe.get('maps',{}).items():
        n=mat.node_tree.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(path,check_existing=True)
        if ch!='BaseColor':n.image.colorspace_settings.name='Non-Color'
        if ch=='Normal':
            nm=mat.node_tree.nodes.new('ShaderNodeNormalMap');mat.node_tree.links.new(n.outputs['Color'],nm.inputs['Color']);mat.node_tree.links.new(nm.outputs['Normal'],p.inputs['Normal'])
        else:mat.node_tree.links.new(n.outputs['Color'],p.inputs['Base Color' if ch=='BaseColor' else 'Roughness'])
        if recipe.get('masked') and ch=='BaseColor':mat.node_tree.links.new(n.outputs['Alpha'],p.inputs['Alpha'])
    materials[key]=mat

class Frame:
    def __init__(self,c,right,up):self.c=Vector(c);self.u=Vector(right);self.v=Vector(up);self.n=self.u.cross(self.v).normalized()
    def p(self,x,y,z=0):return tuple(self.c+self.u*x+self.v*y+self.n*z)
def outline(g,points,frame,thickness,mat):
    # Concave profiles retain real jaw openings and forged handle silhouettes.
    points=list(points)
    if sum(points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points)))<0:points.reverse()
    n=len(points);p2=[Vector((x,y,0)) for x,y in points];lookup={tuple(p):i for i,p in enumerate(p2)}
    tris=[[p if isinstance(p,int) else lookup[tuple(p)] for p in tri] for tri in tessellate_polygon([p2])]
    vs=[frame.p(x,y,z) for z in (-thickness/2,thickness/2) for x,y in points]
    fs=[tuple(reversed(t)) for t in tris]+[tuple(i+n for i in t) for t in tris]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    add(g,vs,fs,mat)
def annulus(g,frame,outer,inner,height,mat='Steel',segments=36,teeth=False):
    vs=[]
    for z in (-height/2,height/2):
        for inside in (False,True):
            for i in range(segments):
                t=math.tau*i/segments;r=inner*(1+.08*math.cos(t*6)) if inside and teeth else inner if inside else outer
                vs.append(frame.p(r*math.cos(t),r*math.sin(t),z))
    n=segments;fs=[];sm=[]
    for i in range(n):
        j=(i+1)%n
        fs.extend([(i,j,2*n+j,2*n+i),(n+j,n+i,3*n+i,3*n+j),(2*n+i,2*n+j,3*n+j,3*n+i),(j,i,n+i,n+j)])
        sm.extend([True,True,False,False])
    add(g,vs,fs,mat,sm)
def ftube(g,f,pts,r,mat='Steel',sides=28):tube(g,[f.p(*p) for p in pts],r,mat,sides)
def wrench(g,f,length=.24):
    s=length/.24
    jaw=[(-.024,.058),(-.033,.030),(-.025,-.002),(-.014,-.006),(-.012,.023),(.010,.028),(.016,.002),(.027,.007),(.034,.035),(.023,.061),(.008,.074),(-.01,.074)]
    outline(g,[(x*s,y*s) for x,y in jaw],f,.006*s,'Steel')
    outline(g,[(-.009*s,.055*s),(.009*s,.055*s),(.008*s,length-.027*s),(-.008*s,length-.027*s)],f,.005*s,'Steel')
    ringframe=Frame(f.p(0,length-.012*s),f.u,f.v);annulus(g,ringframe,.019*s,.011*s,.008*s,teeth=True)
    outline(g,[(-.003*s,.082*s),(.003*s,.082*s),(.003*s,length-.044*s),(-.003*s,length-.044*s)],Frame(f.p(0,0,.003*s),f.u,f.v),.0007,'BareEdge')
def driver(g,f,length=.235,cross=True):
    ftube(g,f,[(0,.009,0),(0,.070,0)],.012,'PaintRed')
    ftube(g,f,[(0,.004,0),(0,.014,0)],.013,'DarkRubber')
    for t in range(6):
        a=t*math.tau/6
        ftube(g,f,[(math.cos(a)*.010,.021,math.sin(a)*.010),(math.cos(a)*.010,.06,math.sin(a)*.010)],.0022,'DarkRubber',12)
    ftube(g,f,[(0,.068,0),(0,.083,0)],.009,'Steel')
    ftube(g,f,[(0,.08,0),(0,length-.012,0)],.0035,'Steel')
    if cross:
        outline(g,[(-.0035,length-.016),(.0035,length-.016),(.001,length),(-.001,length)],f,.002,'Steel')
        outline(g,[(-.0035,length-.016),(.0035,length-.016),(.001,length),(-.001,length)],Frame(f.c,f.n,f.v),.002,'Steel')
    else:outline(g,[(-.0036,length-.018),(.0036,length-.018),(.005,length),(-.005,length)],f,.0015,'Steel')
def pliers(g,f):
    for side in (-1,1):
        ftube(g,f,[(side*.037,.01,0),(side*.031,.057,0),(side*.012,.103,0),(-side*.008,.14,0)],.006,'Steel')
        ftube(g,f,[(side*.037,.009,0),(side*.032,.048,0),(side*.022,.077,0)],.009,'BluePlastic')
        outline(g,[(side*.008,.124),(side*.021,.153),(side*.010,.205),(side*.002,.205),(side*.006,.158),(-side*.005,.140)],f,.008,'Steel')
    ftube(g,f,[(0,.133,-.005),(0,.133,.007)],.010,'Steel')
    ftube(g,f,[(0,.133,.007),(0,.133,.010)],.005,'BareEdge',6)
def hammer(g,f):
    outline(g,[(-.013,0),(.013,0),(.010,.207),(.014,.243),(-.014,.243),(-.010,.207)],f,.019,'Timber')
    ftube(g,f,[(-.065,.247,0),(.046,.247,0)],.024,'Steel',32)
    ftube(g,f,[(-.073,.247,0),(-.060,.247,0)],.028,'Steel',36)
    ftube(g,f,[(.043,.247,0),(.064,.247,0)],.017,'Steel',32)
    ftube(g,f,[(.063,.247,0),(.078,.247,0)],.012,'Steel',28)
def flat(c,angle=0):return Frame(c,(math.cos(angle),math.sin(angle),0),(-math.sin(angle),math.cos(angle),0))

# Retain the exact existing workbench steel frame; replace only timber boards.
with bpy.data.libraries.load(str(ROOM/'Authored/DungeonRooms_Authored.blend'),link=False) as (src,dst):dst.objects=['SM_Room_WS_Workbench','SM_Room_WS_Toolboard','SM_Room_WS_Cables']
source_objects=[]
for ob in dst.objects:
    scene.collection.objects.link(ob)
    if 'Workbench' in ob.name:
        wood={i for i,m in enumerate(ob.data.materials) if 'Timber' in m.name}
        bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.material_index in wood],context='FACES')
        bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(ob.data);bm.free()
        ob.name='SM_WSTools_BenchFrame'
    elif 'Cables' in ob.name:
        bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.delete(bm,geom=[f for f in bm.faces if all(v.co.z<1.5 for v in f.verts)],context='FACES')
        bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS');bm.to_mesh(ob.data);bm.free()
        ob.name='SM_WSTools_CeilingCables'
    else:ob.name='SM_WSTools_Toolboard'
    for i,slot in enumerate(ob.material_slots):
        name=slot.material.name
        ob.data.materials[i]=materials['DarkRubber' if 'Rubber' in name else 'Steel' if 'Iron' in name else 'RackPaint']
    source_objects.append(ob)

# Continuous long-grain boards with cut end grain and subtly worn front edges.
def board(c,size,length_axis):
    start=len(groups.get('BenchTop',{}).get('f',[]));box('BenchTop',c,size,'Timber')
    g=groups['BenchTop']
    for fi in range(start,len(g['f'])):
        face=g['f'][fi];vs=[Vector(g['v'][i]) for i in face];normal=(vs[1]-vs[0]).cross(vs[2]-vs[0]).normalized()
        if abs(normal[length_axis])>.8:g['mat'][fi]='EndGrain'
        uvs=[]
        for vert in vs:
            local=(10-vert.x,-vert.y,vert.z)
            long=local[length_axis];across=local[1-length_axis]
            if abs(normal.z)>.8:uvs.append(((across-c[1-length_axis])/size[1-length_axis]+.5,(long-c[length_axis])/2+.45))
            elif abs(normal[length_axis])>.8:uvs.append(((across-c[1-length_axis])/size[1-length_axis]+.5,(local[2]-c[2])/size[2]+.5))
            else:uvs.append(((local[2]-c[2])/.24,(long-c[length_axis])/2+.45))
        g['uv'][fi]=uvs
for i in range(3):board((.17+(i+.5)*.76/3,2.61,.908),(.76/3-.003,2.26,.062),1)
for i in range(3):board((1.77,3.39+(i+.5)*.68/3,.908),(1.64,.68/3-.003,.062),0)
for x,y in [(.235,1.56),(.865,1.56),(.235,3.67),(.865,3.67),(1.015,3.445),(2.525,3.445),(1.015,4.015),(2.525,4.015)]:
    bolt('BenchDetail',(x,y,.940),(0,0,1),.005)

# Properly bolted swivel vise with anvil, slide, replaceable jaw pads and a threaded screw.
cx,cy=2.25,3.70
box('BenchDetail',(cx,cy,.954),(.31,.285,.027),'RackPaint')
tube('BenchDetail',[(cx,cy,.968),(cx,cy,1.001)],.124,'Steel',48)
for xx in (-.12,.12):
    for yy in (-.108,.108):bolt('BenchDetail',(cx+xx,cy+yy,.969),(0,0,1),.008)
profile=[(-.135,0),(.092,0),(.092,.048),(-.011,.065),(-.050,.142),(-.105,.142),(-.112,.055),(-.135,.041)]
outline('BenchDetail',profile,Frame((cx,cy,1.0),(1,0,0),(0,0,1)),.137,'RackPaint')
box('BenchDetail',(cx+.061,cy,1.047),(.263,.083,.063),'Steel')
box('BenchDetail',(cx+.10,cy,1.110),(.058,.146,.092),'RackPaint')
for xx in (cx-.05,cx+.071):
    box('BenchDetail',(xx,cy,1.150),(.018,.18,.044),'Steel')
    for j in range(16):
        yy=cy-.078+j*.0104
        tube('BenchDetail',[(xx+(.010 if xx<cx else -.010),yy,1.132),(xx+(.010 if xx<cx else -.010),yy+.006,1.168)],.0009,'BareEdge',6)
    for yy in (cy-.066,cy+.066):bolt('BenchDetail',(xx,yy,1.166),(0,0,1),.0035)
box('BenchDetail',(cx-.139,cy,1.106),(.071,.125,.022),'Steel')
tube('BenchDetail',[(cx-.09,cy,1.039),(cx+.279,cy,1.039)],.014,'Steel',28)
helix=[(cx+.10+i*.0006,cy+.0145*math.cos(i*.0006/.0065*math.tau),1.039+.0145*math.sin(i*.0006/.0065*math.tau)) for i in range(251)]
tube('BenchDetail',helix,.0016,'Steel',8)
tube('BenchDetail',[(cx+.275,cy,1.039),(cx+.296,cy,1.039)],.028,'Steel',32)
tube('BenchDetail',[(cx+.295,cy-.103,.995),(cx+.295,cy+.108,1.083)],.007,'Steel',24)
for yy,zz in ((cy-.104,.995),(cy+.109,1.083)):
    tube('BenchDetail',[(cx+.295,yy-.009,zz),(cx+.295,yy+.009,zz)],.011,'Steel',24)
label((cx,cy-.071,1.071),(1,0,0),.10,.040,7)

# Table tools arranged around the repair, leaving a clear middle working patch.
wrench('BenchDetail',flat((1.12,3.58,.947),-.30),.21)
driver('BenchDetail',flat((1.48,3.49,.955),.32),.245,False)
pliers('BenchDetail',flat((.60,3.27,.952),-.28))
# Ratchet with drive head, selector, quick release and a rubber handle.
f=flat((1.83,3.55,.957),.08)
outline('BenchDetail',[(-.012,0),(.012,0),(.009,.15),(.023,.199),(.018,.233),(-.018,.233),(-.023,.199),(-.009,.15)],f,.012,'Steel')
ftube('BenchDetail',f,[(0,.014,0),(0,.112,0)],.013,'DarkRubber')
ftube('BenchDetail',f,[(0,.207,.005),(0,.207,.018)],.012,'Steel')
outline('BenchDetail',[(-.017,.186),(-.005,.181),(.006,.184),(.004,.190),(-.014,.194)],Frame(f.p(0,0,.008),f.u,f.v),.004,'BareEdge')
# Socket rail and genuine hollow socket heads.
box('BenchDetail',(1.59,3.97,.951),(.40,.052,.019),'DarkRubber')
for i in range(7):
    xx=1.42+i*.057;radius=.010+i*.0015
    annulus('BenchDetail',flat((xx,3.97,.978)),radius+.005,radius-.003,.039,teeth=True)
    ring('BenchDetail',(xx,3.97,.963),(0,0,1),radius+.005,.0015,'BareEdge',32)
# Caliper: rail, fixed/moving jaws, slider, thumbscrew and scale ticks.
f=flat((.57,1.78,.949),-.24)
outline('BenchDetail',[(-.009,0),(.009,0),(.009,.213),(-.009,.213)],f,.004,'Steel')
for v in (.024,.103):
    outline('BenchDetail',[(-.033,v-.01),(.036,v-.01),(.044,v+.01),(.037,v+.014),(.008,v+.006),(-.008,v+.006),(-.036,v+.041),(-.042,v+.041)],f,.006,'Steel')
    if v>.03:ftube('BenchDetail',f,[(0,v,.006),(0,v,.013)],.012,'DarkRubber')
for i in range(22):
    vv=.016+i*.008
    outline('ToolWear',[(-.007,vv),(-.001 if i%5 else .004,vv),(-.001 if i%5 else .004,vv+.0005),(-.007,vv+.0005)],Frame(f.p(0,0,.0023),f.u,f.v),.0002,'DarkRubber')
# Sectioned magnetic parts tray.
cx,cy=1.72,3.74
box('BenchDetail',(cx,cy,.949),(.29,.25,.012),'Steel')
for xx in (cx-.145,cx,cx+.145):box('BenchDetail',(xx,cy,.966),(.006,.25,.040),'Steel')
for yy in (cy-.125,cy+.125):box('BenchDetail',(cx,yy,.966),(.29,.006,.040),'Steel')
for i in range(12):
    xx=cx+(.068 if i<6 else -.068)+R.uniform(-.041,.041);yy=cy+R.uniform(-.075,.075)
    if i<6:annulus('BenchDetail',flat((xx,yy,.964)),.008,.004,.005,segments=12)
    else:
        tube('BenchDetail',[(xx,yy,.959),(xx+.023,yy+.010,.963)],.003,'Steel',12)
        bolt('BenchDetail',(xx+.023,yy+.010,.963),(1,0,0),.005)

# Labeled oil and cleaning bottles, with proper shoulders, seam and nozzle.
for xx,yy,h,idx,mat in [(1.11,3.97,.17,8,'Enamel'),(1.24,3.97,.21,9,'BluePlastic')]:
    tube('BenchDetail',[(xx,yy,.945),(xx,yy,.945+h*.77)],.041,mat,40)
    tube('BenchDetail',[(xx,yy,.945+h*.77),(xx,yy,.945+h*.91)],.025,mat,36)
    tube('BenchDetail',[(xx,yy,.945+h*.91),(xx,yy,.945+h)],.020,'DarkRubber',32)
    ring('BenchDetail',(xx,yy,.949),(0,0,1),.041,.002,'Steel',32)
    label((xx,yy-.0413,.945+h*.44),(1,0,0),.065,.073,idx)
    if idx==8:tube('BenchDetail',[(xx,yy,.945+h),(xx+.012,yy,.99+h),(xx+.06,yy,1.022+h)],.005,'Steel',24)

# Wall tools on the existing industrial pegboard, with real hooks and empty positions.
for i,length in enumerate((.20,.225,.245,.27,.30)):
    yy=1.77+i*.175;bottom=1.91-length
    f=Frame((.235,yy,bottom),(0,1,0),(0,0,1));wrench('HandTools',f,length)
    ring_z=bottom+length-.012*(length/.24)
    tube('HandTools',[(.174,yy,ring_z),(.252,yy,ring_z),(.258,yy,ring_z+.016)],.003,'Steel',18)
    label((.179,yy,2.015),(0,1,0),.105,.048,i+1)
for yy,what in [(2.75,'pliers'),(3.01,'hammer')]:
    f=Frame((.24,yy,1.55),(0,1,0),(0,0,1))
    (pliers if what=='pliers' else hammer)('HandTools',f)
    top=1.74 if what=='pliers' else 1.796
    for dy in (-.022,.022):tube('HandTools',[(.178,yy+dy,top),(.26,yy+dy,top),(.264,yy+dy,top+.015)],.0035,'Steel',18)
for i,yy in enumerate((3.24,3.40,3.55)):
    driver('HandTools',Frame((.238,yy,1.52),(0,1,0),(0,0,1)),.22+i*.025,i%2==0)
    ring('HandTools',(.22,yy,1.585),(0,0,1),.017,.003,'Steel',28)
    tube('HandTools',[(.175,yy,1.585),(.213,yy,1.585)],.004,'Steel',16)
for yy in (2.50,3.66):
    tube('HandTools',[(.174,yy,1.99),(.254,yy,1.99),(.258,yy,2.008)],.0035,'Steel',18)
    label((.179,yy,2.062),(0,1,0),.11,.043,11)
label((.193,2.67,2.165),(0,1,0),.67,.071,0)
for yy in (1.64,3.74):
    for zz in (1.185,2.185):bolt('HandTools',(.198,yy,zz),(1,0,0),.006)

# Heavy woven rag, supported on the tabletop then bending over its inner edge.
verts=[];faces=[];uvs=[];nx,ny=35,29
for j in range(ny):
    for i in range(nx):
        t=i/(nx-1);v=j/(ny-1);xx=.62+t*.48;yy=2.10+v*.32+.012*math.sin(t*3)
        if xx<=.924:zz=.944+.006*math.sin(t*20+v*5)*math.sin(math.pi*v)
        else:
            q=(xx-.924)/.176;xx=.924+.037*math.sin(q*math.pi*.5);zz=.944-.24*q+.011*math.sin(v*21+q*4)*q
        verts.append((xx,yy,zz))
for j in range(ny-1):
    for i in range(nx-1):
        a=j*nx+i;faces.append((a,a+1,a+1+nx,a+nx));uvs.append([(i/(nx-1),j/(ny-1)),((i+1)/(nx-1),j/(ny-1)),((i+1)/(nx-1),(j+1)/(ny-1)),(i/(nx-1),(j+1)/(ny-1))])
add('Rag',verts,faces,'Canvas',True,uvs)
for j in (0,ny-1):tube('Rag',[verts[j*nx+i] for i in range(nx)],.0014,'Canvas',10)

# Replace old uniform wear and cabinet-position artifacts with local working marks.
for i in range(23):
    x=R.uniform(1.12,2.41);y=R.uniform(3.43,3.88);length=R.uniform(.014,.055)
    panel('BenchWear',(x,y,.9405),(1,0,0),(0,1,0),length,.0008,'BareEdge')
for c,size in [((.61,2.76,.9407),(.38,.25)),((2.23,3.66,.9407),(.32,.24)),((1.13,3.95,.9406),(.10,.10))]:
    panel('BenchWear',c,(1,0,0),(0,1,0),*size,'OilFilm')

# Articulated task lamp with a double-link spring arm, pivot bolts and lined shade.
base=(.27,2.13,.958);p1=(.36,2.13,1.27);p2=(.58,2.17,1.56);head=(.76,2.27,1.49)
box('TaskLamp',base,(.13,.14,.029),'RackPaint')
tube('TaskLamp',[base,p1],.014,'RackPaint',32)
for dy in (-.019,.019):tube('TaskLamp',[(p1[0],p1[1]+dy,p1[2]),(p2[0],p2[1]+dy,p2[2])],.008,'RackPaint',24)
tube('TaskLamp',[p2,head],.012,'RackPaint',28)
for p in (p1,p2):
    tube('TaskLamp',[(p[0],p[1]-.037,p[2]),(p[0],p[1]+.037,p[2])],.027,'Steel',32)
    bolt('TaskLamp',(p[0],p[1]-.041,p[2]),(0,-1,0),.009)
for yy in (2.095,2.165):
    pts=[]
    a=Vector((.37,yy,1.28));b=Vector((.49,yy,1.40));axis=(b-a).normalized();side=axis.cross(Vector((0,1,0))).normalized()
    for i in range(161):
        t=i/160;pts.append(tuple(a+(b-a)*t+.008*(Vector((0,1,0))*math.cos(t*14*math.tau)+side*math.sin(t*14*math.tau))))
    tube('TaskLamp',pts,.0015,'Steel',8)
shade_start=len(groups['TaskLamp']['v'])
vs=[];count=48
for z,r in [(1.510,.038),(1.410,.109),(1.506,.033),(1.414,.104)]:vs.extend((head[0]+r*math.cos(i*math.tau/count),head[1]+r*math.sin(i*math.tau/count),z) for i in range(count))
fs=[];mats=[]
for i in range(count):
    j=(i+1)%count;fs.extend([(i,j,count+j,count+i),(2*count+j,2*count+i,3*count+i,3*count+j),(count+i,count+j,3*count+j,3*count+i)])
add('TaskLamp',vs,fs,'RackPaint',True)
tube('TaskLamp',[(head[0],head[1],1.416),(head[0],head[1],1.421)],.064,'TaskLens',48)
ring('TaskLamp',(head[0],head[1],1.412),(0,0,1),.105,.004,'Steel',48)
shade_pivot=Vector((head[0],head[1],1.510));shade_target=Vector((.57,2.72,1.13))
shade_rotation=Vector((0,0,-1)).rotation_difference((shade_target-shade_pivot).normalized())
for i in range(shade_start,len(groups['TaskLamp']['v'])):
    x,y,z=groups['TaskLamp']['v'][i];p=shade_pivot+shade_rotation@(Vector((10-x,-y,z))-shade_pivot)
    groups['TaskLamp']['v'][i]=(10-p.x,-p.y,p.z)
tube('TaskLamp',[head,tuple(shade_pivot)],.017,'Steel',24)
task_emitter=shade_pivot+shade_rotation@(Vector((head[0],head[1],1.408))-shade_pivot)
tube('TaskCable',[(.20,2.64,1.31),(.22,2.53,1.01),(.27,2.20,.86),base,p1,(.47,2.15,1.36),p2,head],.0045,'DarkRubber',16)

# New sealed ceiling luminaires, independently fastened to the concrete ceiling.
for idx,(cx,cy,length,z) in enumerate([(4.0,1.8,1.26,3.025),(1.60,3.10,.98,3.12)]):
    box('CeilingFixtures',(cx,cy,z),(length,.235,.072),'Enamel')
    box('CeilingFixtures',(cx,cy,z-.041),(length-.04,.212,.012),'DarkRubber')
    box('CeilingFixtures',(cx,cy,z-.053),(length-.078,.183,.023),'Lens')
    for side in (-1,1):
        box('CeilingFixtures',(cx+side*(length/2-.016),cy,z),(.045,.24,.087),'Enamel')
        for dy in (-.066,.066):bolt('CeilingFixtures',(cx+side*(length/2+.008),cy+dy,z),(side,0,0),.004)
    for dx in (-length*.31,length*.31):
        for dy in (-.121,.121):
            box('CeilingFixtures',(cx+dx,cy+dy,z-.014),(.022,.012,.074),'Steel')
            tube('CeilingFixtures',[(cx+dx-.012,cy+dy,z+.019),(cx+dx+.012,cy+dy,z+.019)],.004,'Steel',16)
        box('CeilingFixtures',(cx+dx,cy,z+.049),(.06,.27,.019),'Steel')
        tube('CeilingFixtures',[(cx+dx,cy,z+.057),(cx+dx,cy,3.282)],.008,'Steel',20)
        box('CeilingFixtures',(cx+dx,cy,3.288),(.105,.085,.018),'Enamel')
        for yy in (cy-.024,cy+.024):bolt('CeilingFixtures',(cx+dx,yy,3.277),(0,0,-1),.006)
    # Small prismatic ribs contribute silhouette and material breakup, not a solid glow block.
    for j in range(27):box('CeilingFixtures',(cx-length*.44+j*length*.88/26,cy,z-.066),(.002,.166,.002),'Lens')
    box('CeilingFixtures',(cx+length*.42,cy+.19,3.257),(.13,.12,.060),'Enamel')
    tube('CeilingFixtures',[(cx+length*.42,cy+.19,3.231),(cx+length*.46,cy+.14,z+.071),(cx+length*.48,cy,z+.036)],.009,'DarkRubber',20)
    label((cx,cy-.119,z),(1,0,0),.19,.04,12)

# Remove only the old workshop luminaire from the currently referenced combined mesh.
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(ROOT/'Sources/current_fixtures.fbx'),use_custom_normals=True)
fixtures=[o for o in bpy.data.objects if o not in before and o.type=='MESH']
if len(fixtures)!=1:raise RuntimeError('Expected one exported fixture mesh')
fixture=fixtures[0];bpy.ops.object.select_all(action='DESELECT');fixture.select_set(True);bpy.context.view_layer.objects.active=fixture
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
bm=bmesh.new();bm.from_mesh(fixture.data)
cut=[f for f in bm.faces if all(5.45<v.co.x<6.55 and -2.0<v.co.y<-1.6 and 2.70<v.co.z<2.96 for v in f.verts)]
if not cut:
    bounds=[(min(v.co[i] for v in bm.verts),max(v.co[i] for v in bm.verts)) for i in range(3)]
    raise RuntimeError('Workshop fixture location did not match exported geometry: '+str(bounds))
removed=len(cut);bmesh.ops.delete(bm,geom=cut,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(fixture.data);bm.free();fixture.name='SM_WSTools_OtherFixtures';fixture.select_set(False)
input_state=json.loads((ROOT/'Receipts/inputs.json').read_text())
paths=next(r['materials'] for r in input_state['actors'] if r['label']=='DGN_AV2_LightFixtures')
for path in paths:aliases[path.split('.')[-1]]=path
source_objects.append(fixture)
# Full V2 rebuilds use the room-stage mesh with the ruin fixture already removed.
# Preserve that source revision as a second import, so this workshop pass cannot undo it.
variant=fixture.copy();variant.data=fixture.data.copy();variant.name='SM_WSTools_OtherFixturesWithoutRuin';scene.collection.objects.link(variant)
bm=bmesh.new();bm.from_mesh(variant.data)
cut=[f for f in bm.faces if 17.7<f.calc_center_median().x<19.3 and 8.7<f.calc_center_median().y<9.7 and f.calc_center_median().z>3.7]
bmesh.ops.delete(bm,geom=cut,context='FACES');bmesh.ops.delete(bm,geom=[v for v in bm.verts if not v.link_faces],context='VERTS')
bm.to_mesh(variant.data);bm.free();source_objects.append(variant)

bindings={'BenchFrame':'DGN_Room_WS_Workbench','Toolboard':'DGN_Room_WS_Toolboard','CeilingCables':'DGN_Room_WS_Cables','BenchDetail':'DGN_Room_WS_BenchDetail',
          'HandTools':'DGN_Room_WS_HandTools','Rag':'DGN_Room_WS_Cloth','BenchWear':'DGN_Room_WS_LocalWear',
          'TaskLamp':'DGN_Room_WS_TaskLight','OtherFixtures':'DGN_AV2_LightFixtures'}
objects=list(source_objects)
for name,g in groups.items():
    mesh=bpy.data.meshes.new('SM_WSTools_'+name);mesh.from_pydata(g['v'],[],g['f']);mesh.update()
    ob=bpy.data.objects.new(mesh.name,mesh);scene.collection.objects.link(ob)
    keys=list(dict.fromkeys(g['mat']))
    for key in keys:mesh.materials.append(materials[key])
    uv=mesh.uv_layers.new(name='UVMap')
    for face,key,smooth,faceuv in zip(mesh.polygons,g['mat'],g['smooth'],g['uv']):
        face.material_index=keys.index(key);face.use_smooth=smooth
        axis=max(range(3),key=lambda i:abs(face.normal[i]));dims=[i for i in range(3) if i!=axis]
        for j,li in enumerate(face.loop_indices):
            p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=faceuv[j] if faceuv else (p[dims[0]]/.5,p[dims[1]]/.5)
    bpy.context.view_layer.objects.active=ob;bpy.ops.object.select_all(action='DESELECT');ob.select_set(True)
    if name=='Rag':
        solid=ob.modifiers.new('Woven cloth thickness','SOLIDIFY');solid.thickness=.0015;bpy.ops.object.modifier_apply(modifier=solid.name)
    elif name not in ('ToolMarkings','BenchWear','ToolWear','TaskCable'):
        b=ob.modifiers.new('Tool edge radius','BEVEL');b.width=.00065 if name in ('BenchDetail','HandTools') else .0018
        b.segments=3;b.limit_method='ANGLE';b.angle_limit=.64;b.harden_normals=True;bpy.ops.object.modifier_apply(modifier=b.name)
        w=ob.modifiers.new('Face weighted normals','WEIGHTED_NORMAL');w.keep_sharp=True;bpy.ops.object.modifier_apply(modifier=w.name)
    tri=ob.modifiers.new('Tangent triangulation','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    ob.select_set(False);objects.append(ob)
manifest={'objects':[],'material_aliases':aliases,'removed_fixture_faces':removed,
          'hide_lights':['DGN_AV2_Light_Workshop','DGN_Room_WS_TaskLightSource'],
          'source_blend':str(OUT/'DungeonWorkshopTools.blend'),'tests_run':False,'screenshots_taken':False}
manifest['lights']=[
    {'label':'DGN_WSTools_CeilingArea','kind':'rect','position':[600,180,295.7],'lumens':850,'temperature':4300,'width':118.2,'height':18.3,'radius':475},
    {'label':'DGN_WSTools_BenchArea','kind':'rect','position':[840,310,305.2],'lumens':420,'temperature':4300,'width':90.2,'height':18.3,'radius':345},
    {'label':'DGN_WSTools_TaskSpot','kind':'spot','position':[(10-task_emitter.x)*100,task_emitter.y*100,task_emitter.z*100],
     'target':[(10-shade_target.x)*100,shade_target.y*100,shade_target.z*100],'lumens':95,'temperature':3200,'radius':220}]
for ob in objects:
    short=ob.name.removeprefix('SM_WSTools_');bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    file=OUT/(ob.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(file),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,bake_anim=False)
    manifest['objects'].append({'name':ob.name,'actor':bindings.get(short,'DGN_WSTools_'+short),'replace':short in bindings,
      'variant_only':short=='OtherFixturesWithoutRuin',
      'fbx':str(file),'collision':short in ('BenchFrame','BenchTop'),
      'cast_shadow':short not in ('BenchWear','ToolWear','ToolMarkings'), 'materials':[m.name for m in ob.data.materials]})
variant.hide_render=True;variant.hide_set(True)
for im in bpy.data.images:
    if im.source=='FILE' and im.filepath and Path(bpy.path.abspath(im.filepath)).exists():im.pack()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'DungeonWorkshopTools.blend'))
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('WORKSHOP_TOOLS_AUTHORED',len(objects),'fixture faces replaced',removed,'NO_RENDER')
