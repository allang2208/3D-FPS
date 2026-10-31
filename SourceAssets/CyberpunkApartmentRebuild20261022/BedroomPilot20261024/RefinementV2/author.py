"""Precision bedroom dressing. Metres, supported assemblies, no preview render."""
import ast,sys,math,json
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from design import *
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonReceptionHall20261006/Scripts'))
import geometry as g
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC'
g.ROOM='BedroomPilot'
source=ast.parse((R.parents[1]/'RefinementV4/author.py').read_text('utf8'))
exec(compile(ast.Module(body=[n for n in source.body if isinstance(n,ast.FunctionDef) and n.name in {'B','roundbox','pipe','ring','text'}],type_ignores=[]),'precision_helpers','exec'),globals())
out=R/'Meshes';out.mkdir(parents=True,exist_ok=True)

def pipe(k,points,r=.008,m='EdgeSteel',sides=16):
    points=[Vector(p) for p in points]
    if len(points)>3 and (points[0]-points[-1]).length<1e-7:
        points=points[:-1];vs=[];fs=[];n=len(points)
        for i,p in enumerate(points):
            tangent=(points[(i+1)%n]-points[(i-1)%n]).normalized()
            _,a,b=g.basis(tangent)
            vs.extend(tuple(p+r*(a*math.cos(j*math.tau/sides)+b*math.sin(j*math.tau/sides))) for j in range(sides))
        for i in range(n):
            for j in range(sides):fs.append((i*sides+j,i*sides+(j+1)%sides,((i+1)%n)*sides+(j+1)%sides,((i+1)%n)*sides+j))
        g.poly(k,vs,fs,m,smooth=True)
    else:g.tube(k,points,r,m,sides)

def loop(cx,cy,z,w,d,r=.04):
    points=[]
    for x,y,a in [(cx+w/2-r,cy+d/2-r,0),(cx-w/2+r,cy+d/2-r,90),(cx-w/2+r,cy-d/2+r,180),(cx+w/2-r,cy-d/2+r,270)]:
        for i in range(9):
            t=math.radians(a+i*90/8);points.append((x+r*math.cos(t),y+r*math.sin(t),z))
    return points+[points[0]]

def cup(k,c,r=.039,h=.095):
    x,y,z=c
    g.lathe(k,c,(0,0,1),[(0,r*.73),(.007,r*.90),(h-.006,r),(h,r-.002),(h,r-.006),(.012,r*.73),(.012,.003)],'Ceramic',40)
    points=[]
    for i in range(33):
        t=i/32;xx=x+r*.94+.037*math.sin(t*math.pi)**.72
        points.append((xx,y,z+.022+t*(h-.042)))
    pipe(k,points,.005,'Ceramic',10)

def book(k,c,w=.17,d=.23,h=.026,title='FIELD NOTES',mat='CharcoalWeave',yaw=0):
    x,y,z=c
    # Casebound cover, page block, spine and a printed horizontal title.
    roundbox(k,(x,y,z+h/2),(w-.007,d-.008,h-.006),'Paper',.0015,2)
    for zz in (z+.002,z+h-.002):roundbox(k,(x,y,zz),(w,d,.004),mat,.002,2)
    roundbox(k,(x-w/2+.002,y,z+h/2),(.006,d,h),mat,.002,2)
    for j in range(3):B(k,(x+w/2-.002,y,z+.007+j*.004),(.0015,d-.015,.0005),'FogLinen')
    text(k,title,(x-w*.39,y-.008,z+h+.00005),min(.013,w/max(14,len(title)*.8)),'Paper',(0,0,0))
    text(k,'BAY / EDITION 07',(x-w*.39,y-d*.31,z+h+.00005),.006,'Paper',(0,0,0))

def cloth(k,c,w,d,h,mat,fold=.0,nx=66,ny=40,drop=0):
    """Closed cloth surface with a supported centre and a shaped hanging perimeter."""
    x0,y0,z0=c;vs=[];fs=[];uv=[]
    for side in (1,-1):
        for j in range(ny+1):
            v=j/ny;y=(v-.5)*d
            for i in range(nx+1):
                u=i/nx;x=(u-.5)*w
                edge=max(0,(abs(x)-w*.40)/(w*.10))
                z=h*.55*math.sin(u*math.pi)**.65*math.sin(v*math.pi)**.8
                z+=.008*math.sin(23*u+6*v)*math.sin(v*math.pi)+.004*math.sin(48*v+13*u)*(.3+edge)
                z+=fold*math.exp(-((v-.79)/.085)**2)-drop*edge**1.4
                vs.append((x0+x,y0+y,z0+z+side*.004))
    count=(nx+1)*(ny+1)
    for layer in range(2):
        for j in range(ny):
            for i in range(nx):
                a=layer*count+j*(nx+1)+i;f=(a,a+1,a+nx+2,a+nx+1)
                fs.append(f if layer==0 else tuple(reversed(f)))
                uv.append([(i*w/nx,j*d/ny),((i+1)*w/nx,j*d/ny),((i+1)*w/nx,(j+1)*d/ny),(i*w/nx,(j+1)*d/ny)] if layer==0 else [(i*w/nx,(j+1)*d/ny),((i+1)*w/nx,(j+1)*d/ny),((i+1)*w/nx,j*d/ny),(i*w/nx,j*d/ny)])
    edge=list(range(nx+1))+[j*(nx+1)+nx for j in range(1,ny+1)]+[ny*(nx+1)+i for i in range(nx-1,-1,-1)]+[j*(nx+1) for j in range(ny-1,0,-1)]
    for a,b in zip(edge,edge[1:]+edge[:1]):fs.append((a,a+count,b+count,b));uv.append(None)
    g.poly(k,vs,fs,mat,uv=uv,smooth=True)
    pipe(k,[vs[i] for i in edge]+[vs[edge[0]]],.0022,'FogLinen',8)

# Headwall is attached to the existing partition, above the retained bed headboard.
k='Headwall'
roundbox(k,(0,0,2.43),(5.55,.032,1.47),'Graphite',.012)
for i in range(9):
    x=-2.40+i*.60
    roundbox(k,(x,-.035,2.43),(.575,.058,1.41),'CharcoalWeave',.018,5)
    # A low-profile stitched seam, no floating cover card.
    pipe(k,[(x-.265,-.067,1.76),(x-.265,-.067,3.10)],.0018,'FogLinen',7)
for x in (-2.84,2.84):
    roundbox(k,(x,-.01,1.85),(.11,.085,2.70),'Walnut',.012)
    B(k,(x,-.056,1.85),(.014,.006,2.55),'Copper')
for z in (1.68,3.18):roundbox(k,(0,-.020,z),(5.80,.10,.035),'EdgeSteel',.006)
for x in (-2.55,2.55):
    for z in (1.85,2.95):g.cylinder(k,(x,.016,z),(x,.0578,z),.024,'Graphite',24)
# Narrow ventilation crown has real depth and spaced vanes.
for i in range(56):B(k,(-2.70+i*.098,-.025,3.29),(.045,.065,.12),'Graphite')
for x in (-2.88,2.88):
    for z in (1.69,3.17):g.cylinder(k,(x,-.065,z),(x,-.071,z),.006,'EdgeSteel',20)

k='ServiceSpine'
roundbox(k,(0,0,.78),(.16,.055,1.46),'Graphite',.010)
for z in (.33,.40,.47):
    roundbox(k,(0,-.033,z),(.105,.02,.035),'Rubber',.004)
    for x in (-.025,.025):B(k,(x,-.045,z),(.009,.003,.008),'Copper')
roundbox(k,(0,-.035,1.24),(.10,.018,.19),'EdgeSteel',.008)
for z in (1.18,1.24,1.30):ring(k,(0,-.049,z),(0,1,0),.016,.011,.006,'Graphite')
B(k,(0,-.052,1.39),(.034,.005,.006),'CoolIndicator')
for z in (.24,1.40):g.cylinder(k,(0,.0275,z),(0,.060,z),.025,'Graphite',24)
text(k,'48V',(-.035,-.048,.61),.015,'Paper',(90,0,0))
text(k,'LOCAL',(-.043,-.048,.58),.011,'Paper',(90,0,0))

# Two identical restrained wall reading fixtures, each with its own scheduled light.
k='ReadingFixture'
roundbox(k,(0,0,0),(.15,.055,.23),'Graphite',.016)
for z in (-.07,.07):g.cylinder(k,(0,.0275,z),(0,.070,z),.021,'Graphite',24)
g.cylinder(k,(0,-.03,.02),(0,-.12,.02),.023,'Copper',32)
roundbox(k,(0,-.16,.027),(.25,.19,.016),'Graphite',.008,5)
for x in (-.120,.120):roundbox(k,(x,-.16,-.005),(.010,.19,.053),'Graphite',.004)
for y in (-.25,-.07):roundbox(k,(0,y,-.005),(.23,.010,.053),'Graphite',.004)
roundbox(k,(0,-.16,-.022),(.224,.162,.009),'WarmDiffuser',.006,5)
for x in (-.096,.096):B(k,(x,-.16,.037),(.012,.16,.006),'Copper')
for x in (-.045,.045):g.cylinder(k,(x,-.033,-.065),(x,-.04,-.065),.007,'EdgeSteel',20)

# Nightstand objects are a single supported cluster. The drawers remain independent.
k='BedsideTray'
roundbox(k,(0,0,.012),(.32,.27,.024),'Walnut',.025,6)
roundbox(k,(0,0,.027),(.285,.235,.008),'Rubber',.021,6)
for x in (-.153,.153):roundbox(k,(x,0,.031),(.014,.26,.022),'Walnut',.006)
for y in (-.128,.128):roundbox(k,(0,y,.031),(.292,.014,.022),'Walnut',.006)
roundbox(k,(-.055,.015,.038),(.075,.145,.013),'Graphite',.008)
roundbox(k,(-.055,.015,.045),(.062,.128,.002),'Ink',.005)
B(k,(-.055,-.030,.0465),(.035,.003,.0005),'CoolIndicator')
g.torus(k,(.078,.025,.035),(0,0,1),.030,.004,'Copper',36,10)
roundbox(k,(.078,.025,.043),(.038,.043,.013),'Graphite',.008)
for t in range(12):
    a=t*math.tau/12;g.cylinder(k,(.078+.012*math.cos(a),.025+.015*math.sin(a),.050),(.078+.012*math.cos(a),.025+.015*math.sin(a),.051),.001,'Paper',8)

k='BedsideBooks'
book(k,(0,0,0),.20,.24,.028,'SLEEP / CYCLE','CharcoalWeave')
book(k,(.018,-.012,.028),.17,.22,.022,'NIGHT SIGNAL','Graphite')
cup(k,(-.045,.035,.050),.034,.087)

# Bed accent ends at the foot, retaining the existing central rest surface.
exec(compile((R/'bedding.py').read_text('utf8'),str(R/'bedding.py'),'exec'),globals())

# Large low-profile bedside rug; its thin border is geometry, weave comes from PBR.
k='BedRug';roundbox(k,(0,0,.006),(3.55,1.25,.012),'Rug',.055,8)
for inset in (.035,.06):pipe(k,loop(0,0,.0125,3.55-inset*2,1.25-inset*2,.05),.001,'FogLinen',8)
for i in range(28):
    x=-1.64+i*.121;pipe(k,[(x,-.62,.009),(x+.006,-.65,.007),(x-.003,-.675,.006)],.0015,'Rug',6)

# Narrow upholstered bench against the far side wall, outside the wardrobe's travel.
k='WindowBench'
roundbox(k,(0,0,.44),(1.68,.55,.095),'Walnut',.025,6,col=True)
roundbox(k,(0,0,.525),(1.61,.51,.11),'CharcoalWeave',.047,8,col=True)
pipe(k,loop(0,0,.54,1.60,.50,.06),.003,'FogLinen',8)
for x in (-.67,.67):
    for y in (-.19,.19):roundbox(k,(x,y,.22),(.045,.045,.44),'Graphite',.006,col=True)
for y in (-.21,.21):B(k,(0,y,.12),(1.40,.024,.035),'EdgeSteel')
for j in range(3):
    roundbox('BenchFoldedLinen',(.40+j*.009,0,.5905+j*.0205),(.54,.405,.020),'FogLinen',.009,6)
    pipe('BenchFoldedLinen',loop(.40+j*.009,0,.5905+j*.0205,.533,.398,.015),.0016,'CharcoalWeave',8)
g.G[(g.ROOM,'BenchFoldedLinen')]['v']=[(x,y,z+.0014*math.sin(21*x+7*y)*math.sin(13*y+3)*min(1,max(0,(z-.5805)/.008))) for x,y,z in g.G[(g.ROOM,'BenchFoldedLinen')]['v']]

# Hollow woven hamper, fitted base, continuous rim and cloth draped over one edge.
k='LaundryBasket'
g.lathe(k,(0,0,.025),(0,0,1),[(0,.205),(.03,.215),(.46,.255),(.47,.252),(.47,.232),(.035,.198),(.035,.003)],'CharcoalWeave',64)
for i in range(40):
    a=i*math.tau/40
    pipe(k,[(r*math.cos(a),r*math.sin(a),z) for r,z in [(.214,.04),(.222,.14),(.234,.29),(.255,.49)]],.003,'Walnut',7)
for i in range(16):g.torus(k,(0,0,.055+i*.027),(0,0,1),.215+i*.0025,.0025,'Walnut',64,6)
g.torus(k,(0,0,.495),(0,0,1),.245,.012,'Graphite',64,10)
g.box(None,(0,0,.25),(.43,.43,.50),collision=k)
for sign in (-1,1):pipe(k,[(sign*.225,-.06,.43),(sign*.27,-.05,.40),(sign*.27,.05,.40),(sign*.225,.06,.43)],.009,'Rubber',12)
exec(compile((R/'basket_cloth.py').read_text('utf8'),str(R/'basket_cloth.py'),'exec'),globals())
# The authored shell starts 25 mm above its local origin; place its bottom on the floor.
g.G[(g.ROOM,'LaundryBasket')]['v']=[(x,y,z-.025) for x,y,z in g.G[(g.ROOM,'LaundryBasket')]['v']]
g.C[(g.ROOM,'LaundryBasket')]=[]
g.box(None,(0,0,.235),(.43,.43,.47),collision='LaundryBasket')

# Reading corner shelving is bracketed; objects are seated on explicit shelf heights.
k='WallShelf'
for x in (-.66,.66):
    roundbox(k,(x,.105,.30),(.04,.05,.78),'Graphite',.006)
    for z in (-.02,.61):g.cylinder(k,(x,.13,z),(x,.1548,z),.025,'Graphite',24)
    for z in (0,.52):g.beam(k,(x,.10,z-.12),(x,-.18,z-.012),.025,.026,'EdgeSteel')
for z in (0,.52):roundbox(k,(0,-.065,z),(1.55,.36,.035),'Walnut',.010)
book(k,(-.46,-.08,.018),.19,.245,.027,'URBAN ATLAS','Graphite')
book(k,(-.435,-.08,.045),.17,.23,.026,'QUIET HOURS','OchreCloth')
for i in range(7):
    x=-.55+i*.065
    roundbox(k,(x,-.04,.67),(.052,.18,.26),'CharcoalWeave' if i%3 else 'OchreCloth',.004)
    B(k,(x,-.132,.72),(.038,.0015,.003),'Paper')
    B(k,(x,-.132,.69),(.025,.0015,.003),'Paper')
g.lathe(k,(.43,-.04,.018),(0,0,1),[(0,.09),(.02,.095),(.16,.12),(.18,.115),(.18,.10),(.025,.078),(.025,.003)],'Ceramic',40)
g.lathe(k,(.43,-.04,.16),(0,0,1),[(0,.097),(.008,.098)],'Walnut',40)
# Stylised dried reeds: real stems and tapered leaves, no glowing flat foliage cards.
for i in range(11):
    a=i*2.4;top=(.43+.14*math.cos(a),-.04+.10*math.sin(a),.40+.04*math.sin(i))
    pipe(k,[(.43,-.04,.17),(.43+.04*math.cos(a),-.04+.03*math.sin(a),.30),top],.0015,'Walnut',6)
    for j in range(3):
        z=.28+j*.035;px=.43+(z-.17)*.4*math.cos(a);py=-.04+(z-.17)*.25*math.sin(a)
        g.poly(k,[(px,py,z),(px+.012,py+.006,z+.04),(px+.07*math.cos(a+j),py+.07*math.sin(a+j),z+.035),(px-.008,py-.006,z+.015)],[(0,1,2,3),(3,2,1,0)],'OchreCloth')

# Desk side accessories occupy the free left/right strips, retaining keyboard + power button.
k='DeskLife'
book(k,(-.59,-.12,.783),.17,.23,.025,'SYSTEM NOTES','CharcoalWeave')
book(k,(-.58,-.105,.808),.145,.21,.018,'AFTER HOURS','OchreCloth')
cup(k,(.52,-.025,.783),.038,.094)
g.lathe(k,(.62,-.10,.783),(0,0,1),[(0,.044),(.008,.046),(.095,.044),(.098,.041),(.098,.037),(.012,.035),(.012,.002)],'Graphite',32)
for i in range(5):
    a=i*1.8;g.cylinder(k,(.62+.021*math.cos(a),-.10+.021*math.sin(a),.798),(.62+.026*math.cos(a),-.10+.024*math.sin(a),.955+i*.006),.003,'Copper' if i==0 else 'Walnut',10)
roundbox(k,(-.52,.105,.790),(.12,.18,.013),'Paper',.004)
for j in range(7):B(k,(-.52,.045+j*.018,.7967),(.085,.0012,.0003),'Ink')
g.cylinder(k,(-.55,.045,.7996),(-.49,.175,.7996),.003,'Copper',12)
# All tabletop accessories share the measured 79.5 cm support plane, plus 0.5 mm.
g.G[(g.ROOM,k)]['v']=[(x,y,z+.0125) for x,y,z in g.G[(g.ROOM,k)]['v']]

k='Headphones'
roundbox(k,(0,0,.010),(.17,.14,.020),'Graphite',.025,6)
g.cylinder(k,(0,.018,.02),(0,.018,.278),.012,'EdgeSteel',24)
roundbox(k,(0,.012,.286),(.11,.05,.028),'Walnut',.013,5)
points=[(.098*math.cos(t),0,.206+.105*math.sin(t)) for t in [i*math.pi/40 for i in range(41)]]
pipe(k,points,.011,'Graphite',12)
pipe(k,[(x,0,z-.011) for x,y,z in points[4:-4]],.010,'CharcoalWeave',12)
for sign in (-1,1):
    roundbox(k,(sign*.092,0,.157),(.044,.070,.105),'Graphite',.018,6)
    roundbox(k,(sign*.065,0,.157),(.018,.064,.095),'CharcoalWeave',.012,6)
    ring(k,(sign*.116,0,.157),(1,0,0),.026,.023,.003,'Copper')
pipe(k,[(.10,0,.11),(.13,.02,.05),(.11,.06,.028),(.02,.06,.025),(-.035,.075,.026),(-.09,.06,.023)],.0022,'Rubber',8)

k='DeskCableTray'
roundbox(k,(-.25,.27,.65),(.78,.08,.025),'Graphite',.008)
for x in (-.60,.06):B(k,(x,.27,.6985),(.025,.070,.097),'EdgeSteel')
for i in range(3):
    points=[(.04-i*.06,.25,.675),(-.22,.27-i*.014,.675),(-.57,.27-i*.014,.675),(-.665,.30,.61),(-.670,.33,.50),(-.67,.37,.35+i*.035),(-.647,.37,.35+i*.035)]
    pipe(k,points,.003,'Rubber',10)
for i in range(3):roundbox(k,(-.55+i*.25,.27,.686),(.17,.056,.043),'Graphite',.006)

# A wall rail above the work desk: horizontal captions on solid inset plates.
k='DeskRail'
roundbox(k,(0,0,.0),(1.64,.07,.27),'Graphite',.018)
for i in range(16):B(k,(-.75+i*.10,-.043,0),(.025,.018,.21),'Walnut')
roundbox(k,(-.44,-.062,0),(.59,.018,.22),'Ink',.010)
text(k,'BAY / 07',(-.68,-.074,.018),.053,'Paper',(90,0,0))
text(k,'PRIVATE QUARTERS',(-.68,-.074,-.055),.017,'Paper',(90,0,0))
for i in range(5):B(k,(.20+i*.13,-.060,-.03),(.072,.012,.085),'EdgeSteel')
for x in (-.78,.78):g.cylinder(k,(x,-.038,0),(x,-.046,0),.006,'Copper',20)
for x in (-.79,.79):
    roundbox(k,(x,-.015,-.485),(.030,.035,.960),'Graphite',.004)
    roundbox(k,(x,-.015,-.9715),(.055,.08,.026),'EdgeSteel',.005)

# Soft closed slippers beside the bed; toe area has a real arched upper and sole.
k='Slippers'
for side in (-1,1):
    x=side*.095;y=.015*side
    roundbox(k,(x,y,.014),(.105,.265,.028),'Rubber',.040,8)
    roundbox(k,(x,y,.032),(.096,.248,.018),'FogLinen',.038,8)
    vs=[];fs=[];ns=20;nl=14
    for layer in (0,1):
        for j in range(nl+1):
            yy=-.115+j*.135/nl
            for i in range(ns+1):
                t=i*math.pi/ns
                vs.append((x+(.052-layer*.004)*math.cos(t),y+yy,.037+(.065-layer*.004)*math.sin(t)*(1-.22*(j/nl))))
    count=(ns+1)*(nl+1)
    for layer in (0,1):
        for j in range(nl):
            for i in range(ns):
                a=layer*count+j*(ns+1)+i;f=(a,a+1,a+ns+2,a+ns+1);fs.append(f if layer==0 else tuple(reversed(f)))
    boundary=list(range(ns+1))+[j*(ns+1)+ns for j in range(1,nl+1)]+[nl*(ns+1)+i for i in range(ns-1,-1,-1)]+[j*(ns+1) for j in range(nl-1,0,-1)]
    for a,b in zip(boundary,boundary[1:]+boundary[:1]):fs.append((a,b,b+count,a+count))
    g.poly(k,vs,fs,'CharcoalWeave',smooth=True)
    pipe(k,[(x+.052*math.cos(t),y+.020,.037+.051*math.sin(t)) for t in [i*math.pi/25 for i in range(26)]],.002,'OchreCloth',8)

materials={};records=[]
for (_,key),data in g.G.items():
    mesh=bpy.data.meshes.new(key);mesh.from_pydata(data['v'],[],data['f']);mesh.update()
    ob=bpy.data.objects.new('SM_BP_'+key,mesh);bpy.context.collection.objects.link(ob)
    order=list(dict.fromkeys(data['m']))
    for role in order:
        if role not in materials:
            m=bpy.data.materials.new(role);m.use_nodes=True
            bsdf=m.node_tree.nodes.get('Principled BSDF');s=SURFACES[role]
            bsdf.inputs['Base Color'].default_value=(*s['color'],1)
            bsdf.inputs['Roughness'].default_value=sum(s['limits'])/2
            bsdf.inputs['Metallic'].default_value=s['metal'];materials[role]=m
        mesh.materials.append(materials[role])
    uv=mesh.uv_layers.new(name='PhysicalUV')
    for face,role,coords,smooth in zip(mesh.polygons,data['m'],data['uv'],data['smooth']):
        face.material_index=order.index(role);face.use_smooth=smooth
        axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(face.normal[a]))]
        for j,li in enumerate(face.loop_indices):
            p=mesh.vertices[mesh.loops[li].vertex_index].co
            uv.data[li].uv=coords[j] if coords else (p[axes[0]],p[axes[1]])
    # Per-group export and functional collision, no per-detail actors.
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    mod=ob.modifiers.new('Export triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=mod.name)
    hulls=[]
    for j,(verts,faces) in enumerate(g.C.get((g.ROOM,key),[])):
        cm=bpy.data.meshes.new('UCX_'+ob.name+f'_{j:02}');cm.from_pydata(verts,[],faces);cm.update()
        co=bpy.data.objects.new(cm.name,cm);bpy.context.collection.objects.link(co);co.select_set(True);hulls.append(co)
    fbx=out/(ob.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',add_leaf_bones=False,use_tspace=True)
    records.append(dict(key=key,name=ob.name,fbx=str(fbx),asset=BASE+'/Meshes/'+ob.name,triangles=len(mesh.polygons),materials=order,simple_hulls=len(hulls),nanite=key not in {'Slippers','DeskLife','BedsideBooks','BedsideTray','Headphones'}))
    for co in hulls:co.hide_set(True)
    print('BEDROOM_AUTHORED',key,len(mesh.polygons),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'BedroomPilot_Source.blend'))
(R/'assembly.json').write_text(json.dumps(dict(brief=BRIEF,meshes=records,rendered=False),indent=2),encoding='utf8')
