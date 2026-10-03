"""Baked staff-living refinement; reuse installed surfaces and drainage author."""
from pathlib import Path
SCRIPT=Path(__file__).resolve().parent
entry=SCRIPT/'author_living.py'
_STAFF_REFINEMENT_HELPERS=True
exec(compile(entry.read_text('utf8').split('for key,fn in PROTOTYPES.items():')[0],str(entry),'exec'))
import random

OUT=ROOT/'RefinementV3/Authored';OUT.mkdir(parents=True,exist_ok=True)
BASE=CFG['ue_base']+'/RefinementV3'
MAPPING.update({key:BASE+'/Materials/'+name for key,name in {
    'Carpet':'MI_Staff_NavyCarpet_V3','Linen':'M_Staff_Linen_V3','Terry':'M_Staff_Terry_V3',
    'Hem':'M_Staff_Hem_V3','Notices':'M_Staff_Notices_V3'}.items()})
for key in ('Carpet','Linen','Terry','Hem','Notices'):MATS[key]=bpy.data.materials.new('RS_'+key)
NOTICE=json.loads((OUT/'notice-atlas.json').read_text('utf8'))
OLDMAN=json.loads((ROOT/'Authored/manifest.json').read_text('utf8'))
RECORDS_OLD={r['name']:r for r in OLDMAN['objects']}
changed={};records=[]

def surface_solid(points,nx,ny,uvs,mat='Linen',thickness=.022,kind='Body'):
    """Closed, smoothly shaded cloth with material coordinates following its grid."""
    vs=list(points)+[(x,y,z-thickness) for x,y,z in points];n=len(points)
    fs=[];coords=[]
    for i in range(nx):
        for j in range(ny):
            a=i*(ny+1)+j;f=(a,a+ny+1,a+ny+2,a+1)
            fs.append(f);coords.append([uvs[k] for k in f])
            fs.append(tuple(k+n for k in reversed(f)));coords.append([uvs[k] for k in reversed(f)])
    boundary=[i*(ny+1) for i in range(nx+1)]+[nx*(ny+1)+j for j in range(1,ny+1)]
    boundary += [i*(ny+1)+ny for i in reversed(range(nx))]+[j for j in reversed(range(1,ny))]
    for a,b in zip(boundary,boundary[1:]+boundary[:1]):
        fs.append((a,a+n,b+n,b));coords.append([uvs[a],uvs[a],uvs[b],uvs[b]])
    poly(kind,vs,fs,mat,coords,smooth=True)
    return boundary

def sewn_hem(points,indices,mat='Hem',radius=.002):
    path=[points[i] for i in indices]+[points[indices[0]]]
    detail.tube('Body',path,radius,mat,10)

def remove_fabric():
    for key,g in list(G.items()):
        keep=[i for i,m in enumerate(g['m']) if m!='Fabric']
        if not keep:del G[key];continue
        for field in ('f','m','uv','smooth'):g[field]=[g[field][i] for i in keep]

original_bunk=bunk_bed
def bed_v3(variant):
    original_bunk();remove_fabric()
    rng=random.Random(610020+variant*53)
    for level,z in enumerate((.43,1.58)):
        phase=rng.uniform(0,math.tau);shift=rng.uniform(-.009,.009)
        # Mattress: compressed top, soft corners, edge welt and actual thickness.
        rounded_box('Body',(shift,0,z+.12),(1.965,.84,.19),'Linen',.057,8)
        for side in (-1,1):
            path=[]
            for i in range(57):
                x=-.94+i*1.88/56
                path.append((x+shift,side*.412,z+.156+.003*math.sin(x*5+phase)))
            detail.tube('Body',path,.0032,'Hem',12)
        # The duvet uses a different fixed seed per level and bed. Its folds are
        # baked geometry; no runtime cloth, tick, or per-frame randomisation.
        nx,ny=60,34;pts=[];uvs=[]
        yaw=math.radians(([-4,7,-7,3][variant])*(-1 if level else 1))
        co,si=math.cos(yaw),math.sin(yaw)
        length=[1.77,1.48,1.82,1.62][variant];width=[.97,1.02,.93,1.04][variant]
        centerx=[-.15,-.25,-.10,-.27][variant];centery=rng.uniform(-.045,.045)
        for i in range(nx+1):
            u=i/nx;x=(u-.5)*length
            for j in range(ny+1):
                v=j/ny;y=(v-.5)*width
                px=centerx+x*co-y*si;py=centery+x*si+y*co
                # Supported sheet becomes a weighted fall past the bed edge.
                fall=max(0,abs(py)-.405)*1.8+max(0,-.963-px)*1.5
                envelope=math.sin(math.pi*u)**.5*math.sin(math.pi*v)**.45
                ridge=(.016+.016*variant)*(.5+.5*math.sin(21*u+9*v+phase))**3
                diagonal=.023*math.exp(-((v-.28-.32*u)/.085)**2)
                rumple=.045*math.exp(-((u-.22)/.23)**2)*(.5+.5*math.sin(v*28+u*8+phase))**2
                turn=.095*math.exp(-((u-.88)/.105)**2)*(v**3 if (variant+level)%2 else (1-v)**3)
                pz=z+.235-fall+envelope*(ridge+diagonal+rumple)+turn
                pts.append((px,py,pz));uvs.append((x/.42,y/.42))
        boundary=surface_solid(pts,nx,ny,uvs,thickness=.025)
        sewn_hem(pts,boundary,radius=.0026)
        # Pillow is inflated with a pinched seam and gently twisted placement.
        px=.69+rng.uniform(-.035,.025);py=rng.uniform(-.075,.075)
        angle=math.radians(rng.uniform(-13,13));co,si=math.cos(angle),math.sin(angle)
        pts=[];uvs=[];nx,ny=28,32
        for i in range(nx+1):
            u=i/nx;a=(u-.5)*.43
            for j in range(ny+1):
                v=j/ny;b=(v-.5)*.62
                puff=.10*(math.sin(math.pi*u)*math.sin(math.pi*v))**.43
                crease=.009*math.sin(v*28+phase)*math.exp(-((u-.12)/.15)**2)
                pts.append((px+a*co-b*si,py+a*si+b*co,z+.229+puff+crease))
                uvs.append((a/.42,b/.42))
        boundary=surface_solid(pts,nx,ny,uvs,thickness=.025)
        sewn_hem(pts,boundary,radius=.0022)

def basin_v3():
    # Rear plane is +0.23 m. The ceramic backsplash and steel cleats touch it.
    rings=[(.74,.54,.845),(.73,.52,.886),(.60,.40,.902),(.46,.29,.810),(.16,.11,.735),(.076,.055,.733)]
    vs=[];fs=[];n=72
    for w,d,z in rings:
        for i in range(n):
            a=math.tau*i/n;vs.append((w/2*math.cos(a),d/2*math.sin(a)-.025,z))
    for row in range(len(rings)-1):
        for i in range(n):fs.append((row*n+i,row*n+(i+1)%n,(row+1)*n+(i+1)%n,(row+1)*n+i))
    poly('Body',vs,fs,'Ceramic',smooth=True)
    rounded_box('Body',(0,.204,.905),(.76,.068,.30),'Ceramic',.021,6)
    for x in (-.27,.27):
        box('Body',(x,.223,.68),(.067,.028,.26),'BareSteel')
        beam('Body',(x,.215,.80),(x,-.18,.80),.045,.03,'BareSteel')
        beam('Body',(x,.22,.555),(x,-.17,.79),.03,.03,'BareSteel')
        for z in (.58,.775):detail.fastener((x,.202,z),(0,-1,0),.008,'Body')
    detail.ring((0,-.025,.735),(0,0,1),.039,.025,.015,'BareSteel',48,'Body')
    # Bottle trap connects bowl drain to the wall penetration, with screw unions.
    detail.tube('Body',[(0,-.025,.729),(0,-.025,.56)],.029,'BareSteel',32)
    cylinder((0,-.025,.485),(0,0,1),.047,.16,'BareSteel',sides=48)
    detail.tube('Body',[(0,-.025,.52),(0,.247,.52)],.029,'BareSteel',32)
    for z in (.58,.425):cylinder((0,-.025,z),(0,0,1),.049,.020,'BareSteel',sides=36)
    detail.ring((0,.228,.52),(0,1,0),.058,.025,.019,'BareSteel',40,'Body')
    # Hot/cold isolation valves and supply tails continue into the mounted faucet.
    for x in (-.105,.105):
        detail.tube('Body',[(x,.247,.625),(x,.148,.625),(x,.148,.82),(x*.7,.177,.878)],.009,'BareSteel',20)
        detail.ring((x,.230,.625),(0,1,0),.025,.010,.014,'BareSteel',28,'Body')
        cylinder((x,.122,.625),(0,1,0),.019,.022,'BareSteel',sides=24)
        box('Body',(x,.100,.625),(.055,.013,.010),'Yellow' if x<0 else 'OlivePaint')
    cylinder((0,.16,.944),(0,0,1),.028,.07,'BareSteel',sides=40)
    detail.tube('Body',[(0,.16,.958),(0,.16,1.092),(0,.135,1.118),(0,-.06,1.118)],.016,'BareSteel',32)
    cylinder((0,-.06,1.102),(0,0,1),.019,.022,'BareSteel',sides=32)
    box('Body',(0,.17,1.136),(.10,.025,.015),'BareSteel')
    for x in (-.26,.26):collider((x,0,.815),(.16,.54,.12))
    collider((0,.206,.907),(.76,.07,.30))

def mirror_v3():
    # All wall hardware lives on rear +Y, avoiding a hovering front-only frame.
    rounded_box('Body',(0,.013,.42),(.78,.100,.84),'PaintedSteel',.010,6)
    box('Body',(0,-.023,.42),(.718,.007,.775),'Mirror')
    for x in (-.33,.33):
        for z in (.09,.75):
            box('Body',(x,.065,z),(.065,.030,.090),'BareSteel')
            cylinder((x,-.03,z),(0,1,0),.008,.009,'BareSteel',sides=20)
    box('Body',(0,.065,.69),(.66,.030,.07),'BareSteel')

def shower_v3():
    # Local wall plane is +0.060. Branches are fed by the room's two headers.
    for x in (-.14,.14):
        detail.tube('Body',[(x,.067,.19),(x,-.005,.19),(x,-.005,1.055)],.014,'BareSteel',28)
        for z in (.20,.64,.95):
            detail.ring((x,-.005,z),(0,0,1),.023,.014,.036,'BareSteel',32,'Body')
        detail.ring((x,.053,.19),(0,1,0),.032,.014,.018,'BareSteel',32,'Body')
    detail.tube('Body',[(-.21,-.005,1.055),(.21,-.005,1.055)],.029,'BareSteel',32)
    for x in (-.16,.16):
        cylinder((x,-.050,1.055),(0,1,0),.035,.039,'BareSteel',sides=40)
        box('Body',(x,-.075,1.072),(.092,.018,.018),'BareSteel')
    # Riser begins at mixer outlet; elbows share endpoints and have couplings.
    detail.tube('Body',[(0,-.005,1.055),(0,-.005,1.92),(0,-.018,2.03),
                         (0,-.060,2.09),(0,-.30,2.09),(0,-.355,2.057)],.018,'BareSteel',32)
    for z in (1.35,1.80):
        detail.tube('Body',[(0,.065,z),(0,-.005,z)],.012,'BareSteel',20)
        detail.ring((0,.058,z),(0,1,0),.035,.009,.020,'BareSteel',32,'Body')
        detail.ring((0,-.005,z),(0,0,1),.026,.018,.032,'BareSteel',32,'Body')
    cylinder((0,-.355,2.035),(0,0,1),.105,.035,'BareSteel',sides=64)
    detail.ring((0,-.355,2.016),(0,0,1),.104,.091,.008,'BareSteel',64,'Body')
    for row in range(1,5):
        radius=row*.021;count=row*10
        for j in range(count):
            a=j*math.tau/count
            cylinder((radius*math.cos(a),-.355+radius*math.sin(a),2.015),(0,0,1),.0017,.005,'Rubber',sides=8)
    rounded_box('Body',(.40,-.12,1.15),(.22,.22,.034),'Ceramic',.01)
    for x in (.32,.48):beam('Body',(x,.06,1.10),(x,-.15,1.132),.012,.020,'BareSteel')
    rounded_box('Body',(.40,-.10,1.20),(.075,.12,.045),'Terry',.012)

def drain_v3():
    # Directly reuse the approved lift-out grate author, dimensions and hardware.
    detail.grate(-.42,.42,0)
    g=G.pop('Frames');G['Body']=g
    # Preserve open slots; a real sump floor lies 17 cm below, not under the bars.
    box('Body',(0,0,-.174),(.89,.56,.028),'PipeInner')
    for y in (-.275,.275):box('Body',(0,y,-.084),(.94,.025,.19),'Mortar')
    for x in (-.462,.462):box('Body',(x,0,-.084),(.025,.55,.19),'Mortar')
    detail.ring((.22,0,-.153),(0,0,1),.072,.053,.025,'BareSteel',40,'Body')
    cylinder((.22,0,-.185),(0,0,1),.052,.04,'PipeInner',sides=40)
    collider((0,0,-.003),(.93,.57,.026))

def towel_v3():
    # Wall anchors + continuous bar; towels wrap around it with unequal falls.
    for x in (-.48,.48):
        cylinder((x,.058,.35),(0,1,0),.032,.030,'BareSteel')
        detail.tube('Body',[(x,.066,.35),(x,-.16,.35)],.013,'BareSteel',24)
        for z in (.328,.372):detail.fastener((x,.038,z),(0,-1,0),.006,'Body')
    detail.tube('Body',[(-.48,-.16,.35),(.48,-.16,.35)],.016,'BareSteel',32)
    for k,cx in enumerate((-.247,.227)):
        nx,ny=30,72;pts=[];uvs=[]
        width=.35 if k==0 else .32;front=.57 if k==0 else .48;back=.30 if k==0 else .36
        arc=math.pi*.021;length=front+arc+back
        for i in range(nx+1):
            u=i/nx;xx=(u-.5)*width
            for j in range(ny+1):
                s=j/ny*length
                if s<front:
                    fall=front-s;yy=-.183;zz=.35-fall
                elif s<front+arc:
                    a=(s-front)/arc*math.pi;yy=-.16-.023*math.cos(a);zz=.35+.023*math.sin(a);fall=0
                else:
                    fall=s-front-arc;yy=-.137;zz=.35-fall
                amp=.003+.016*min(1,fall/.18)
                fold=amp*math.sin(u*math.tau*(3.5+k)+fall*2.8+k)
                yy+=fold;zz+=.009*math.sin(u*math.tau*2+k)*min(1,fall/.18)
                pts.append((cx+xx+.009*math.sin(fall*3+u*4),yy,zz))
                uvs.append((xx/.35,s/.35))
        # Towels need thickness along Y, not a vertical slab along Z.
        n=len(pts);vs=pts+[(x,y+.003,z) for x,y,z in pts];fs=[];coords=[]
        for i in range(nx):
            for j in range(ny):
                a=i*(ny+1)+j;f=(a,a+ny+1,a+ny+2,a+1)
                fs.extend([f,tuple(v+n for v in reversed(f))]);coords.extend([[uvs[v] for v in f],[uvs[v] for v in reversed(f)]])
        boundary=[i*(ny+1) for i in range(nx+1)]+[nx*(ny+1)+j for j in range(1,ny+1)]
        boundary += [i*(ny+1)+ny for i in reversed(range(nx))]+[j for j in reversed(range(1,ny))]
        for a,b in zip(boundary,boundary[1:]+boundary[:1]):
            fs.append((a,a+n,b+n,b));coords.append([uvs[a],uvs[a],uvs[b],uvs[b]])
        poly('Body',vs,fs,'Terry',coords,smooth=True);sewn_hem(pts,boundary,radius=.0018)
        for band in (0,3,ny-3,ny):
            path=[pts[i*(ny+1)+band] for i in range(nx+1)]
            detail.tube('Body',path,.0013,'Hem',10)

original_laundry=laundry
def laundry_v3():
    original_laundry();remove_fabric()
    for layer in range(4):
        nx,ny=26,26;pts=[];uvs=[];angle=layer*.83;co,si=math.cos(angle),math.sin(angle)
        for i in range(nx+1):
            u=i/nx;x=(u-.5)*.56
            for j in range(ny+1):
                v=j/ny;y=(v-.5)*.47
                z=.22+layer*.12+.035*math.sin(u*13+v*8+layer)+.04*math.sin(v*12)**2
                pts.append((x*co-y*si,x*si+y*co,z));uvs.append((x/.35,y/.35))
        boundary=surface_solid(pts,nx,ny,uvs,'Terry',.034);sewn_hem(pts,boundary)

def paper_quad(c,w,h,rect):
    x,y,z=c;x0,y0,x1,y1=rect;aw,ah=NOTICE['size']
    # Same mapping convention as the accepted signage author.
    coords=[(x0/aw,1-y1/ah),(x1/aw,1-y1/ah),(x1/aw,1-y0/ah),(x0/aw,1-y0/ah)]
    poly('Body',[(x-w/2,y,z-h/2),(x+w/2,y,z-h/2),(x+w/2,y,z+h/2),(x-w/2,y,z+h/2)],[(0,1,2,3)],'Notices',[coords])

def notice_v3():
    rounded_box('Body',(0,0,.55),(1.8,.065,1.10),'Wood',.010,6)
    box('Body',(0,-.035,.55),(1.70,.009,1.0),'SofaFabric')
    paper_quad((0,-.045,1.005),1.60,.128,NOTICE['header'])
    for i,x in enumerate((-.615,-.205,.205,.615)):
        zz=.575+(.004 if i%2 else -.004)
        box('Body',(x,-.046,zz),(.390,.002,.675),'Ceramic')
        paper_quad((x,-.048,zz),.385,.667,NOTICE['pages'][str(i)])
        for xx in (x-.170,x+.170):
            cylinder((xx,-.052,zz+.310),(0,1,0),.004,.007,'BareSteel',sides=16)
    paper_quad((.40,-.056,.135),.68,.115,NOTICE['reminder'])
    for x in (-.72,.72):box('Body',(x,.044,.70),(.07,.022,.20),'BareSteel')

PROTOTYPES.update({f'BunkBedMessy{i}':lambda i=i:bed_v3(i) for i in range(4)})
PROTOTYPES.update(WashBasin=basin_v3,ShowerFittings=shower_v3,FloorDrain=drain_v3,
    Mirror=mirror_v3,TowelRack=towel_v3,LaundryBasket=laundry_v3,Noticeboard=notice_v3)
for key in [f'BunkBedMessy{i}' for i in range(4)]+['WashBasin','ShowerFittings','FloorDrain','Mirror','TowelRack','LaundryBasket','Noticeboard']:
    G={};HULLS=[];PROTOTYPES[key]();g=merge_groups();name='SM_Staff_'+key+'_V3'
    export_mesh(name,g,prototype=key,kind='Body',hulls=HULLS,collision=bool(HULLS),nanite=key not in ('Mirror','FloorDrain'))
    records[-1]['asset']=BASE+'/Meshes/'+name;changed[key]=name

def g_from(obj,replace=None):
    m=obj.data;uv=m.uv_layers[0];names=[str(s.name).removeprefix('RS_').split('.')[0] for s in m.materials]
    return dict(v=[tuple(v.co) for v in m.vertices],f=[tuple(f.vertices) for f in m.polygons],
        m=[replace if names[f.material_index]=='Linoleum' and replace else names[f.material_index] for f in m.polygons],
        uv=[[tuple(uv.data[li].uv) for li in f.loop_indices] for f in m.polygons],smooth=[f.use_smooth for f in m.polygons])

# Read only the reusable floor solids from the saved source.
floor_names=['SM_Staff_Dormitory_FloorFinish','SM_Staff_Recreation_FloorFinish']
with bpy.data.libraries.load(str(ROOT/'Authored/StaffLivingTheme_Source.blend'),link=False) as (src,dst):dst.objects=floor_names
for obj in dst.objects:
    rid=RECORDS_OLD[obj.name]['room_id'];oldname=obj.name;g=g_from(obj,'Carpet');G={}
    if rid=='StaffDormitory':
        for x in (-15,15):box('FloorFinish',(x,0,-.009),(2,4,.018),'Carpet')
        add=G['FloorFinish'];o=len(g['v']);g['v']+=add['v'];g['f'] += [tuple(i+o for i in f) for f in add['f']]
        for k in ('m','uv','smooth'):g[k]+=add[k]
    bpy.data.objects.remove(obj,do_unlink=True)
    export_mesh(oldname+'_V3',g,room_id=rid,kind='FloorFinish',collision=True)
    records[-1]['asset']=BASE+'/Meshes/'+oldname+'_V3';changed[oldname]=oldname+'_V3'
G={};box('FloorFinish',(2,0,-.009),(4,4,.018),'Carpet')
export_mesh('SM_Staff_Link_Carpet_V3',G['FloorFinish'],room_id='Link',kind='FloorFinish',collision=False)
records[-1]['asset']=BASE+'/Meshes/SM_Staff_Link_Carpet_V3'

# Split both wet-room slab and finish around six open, recessed drain wells.
xs=[-9.8,-5.9,-2,1.9,5.8,9.7];holes=[(x-.48,-8.29,x+.48,-7.71) for x in xs]
cutx=sorted(set([-12,12]+[a for hole in holes for a in (hole[0],hole[2])]))
cuty=[-11,-8.29,-7.71,11]
for kind,z0,z1,mat in [('Floors',-.30,-.018,'Concrete'),('FloorFinish',-.018,0,'Ceramic')]:
    G={}
    for a,b in zip(cutx,cutx[1:]):
        for c,d in zip(cuty,cuty[1:]):
            if any(x0<(a+b)/2<x1 and y0<(c+d)/2<y1 for x0,y0,x1,y1 in holes):continue
            box(kind,((a+b)/2,(c+d)/2,(z0+z1)/2),(b-a,d-c,z1-z0),mat)
    if kind=='Floors':
        # Existing port-necks remain in the slab and keep the same walk surface.
        for x in (-13,13):box(kind,(x,0,-.159),(2,4,.282),'Concrete')
    for x0,y0,x1,y1 in holes:
        for x in (x0,x1):box(kind,(x,(y0+y1)/2,-.10),(.021,y1-y0,.20),'Mortar')
    name='SM_Staff_ChangingShowers_'+kind+'_V3'
    export_mesh(name,G[kind],room_id='StaffChangingShowers',kind=kind,collision=True)
    records[-1]['asset']=BASE+'/Meshes/'+name;changed[name.removesuffix('_V3')]=name

# Grout lines stop at the drainage rims instead of crossing the open wells.
G={}
for x in range(-11,12):
    spans=[(-10.5,-2.3)]
    for x0,y0,x1,y1 in holes:
        if x0<x<x1:spans=[(-10.5,y0),(y1,-2.3)];break
    for a,b in spans:box('WetGrout',(x,(a+b)/2,.002),(.005,b-a,.004),'Mortar')
for y in range(-10,-2):
    intervals=[(-11.75,11.75)]
    for x0,y0,x1,y1 in holes:
        if not y0<y<y1:continue
        cut=[]
        for a,b in intervals:
            if x1<=a or x0>=b:cut.append((a,b));continue
            if a<x0:cut.append((a,x0))
            if x1<b:cut.append((x1,b))
        intervals=cut
    for a,b in intervals:box('WetGrout',((a+b)/2,y,.002),(b-a,.005,.004),'Mortar')
name='SM_Staff_ChangingShowers_WetGrout_V3'
export_mesh(name,G['WetGrout'],room_id='StaffChangingShowers',kind='WetGrout',collision=False,nanite=False)
records[-1]['asset']=BASE+'/Meshes/'+name;changed[name.removesuffix('_V3')]=name

# Connected warm/cold headers behind the riser branches; bends enter the wall.
G={}
for dx,z in ((-.14,.19),(.14,.11)):
    y=-10.799
    endx=10.96 if dx<0 else 11.11
    detail.tube('WaterServices',[(-10.97,y,z),(endx,y,z),(endx,y,2.75+(z-.19)),(endx,-10.97,2.75+(z-.19))],.018,'BareSteel',28)
    for x in xs:
        if dx>0:detail.tube('WaterServices',[(x-dx,y,z),(x-dx,y,.19)],.014,'BareSteel',24)
        detail.ring((x-dx,y,z),(1,0,0),.026,.018,.055,'BareSteel',32,'WaterServices')
for x in (-10.7,-6.4,-2.1,2.2,6.5,10.8):
    for z in (.19,.11):
        beam('WaterServices',(x,-10.80,z),(x,-10.97,z),.027,.025,'BareSteel')
for z in (.19,.11):
    detail.ring((10.96 if z==.19 else 11.11,-10.86,2.75+(z-.19)),(0,1,0),.038,.018,.026,'BareSteel',32,'WaterServices')
name='SM_Staff_ChangingShowers_WaterServices_V3'
export_mesh(name,G['WaterServices'],room_id='StaffChangingShowers',kind='WaterServices',collision=False,nanite=True)
records[-1]['asset']=BASE+'/Meshes/'+name

# Update authored placement data, preserving all independent rooms and furniture.
cfg=json.loads((ROOT/'Config/room.json').read_text('utf8'));cfg['layout_revision']=3;cfg['revision']='staff_living_refinement_v3_20261002'
for room in cfg['rooms']:
    bedindex=0
    for p in room['furniture']:
        key=p['prototype']
        if key=='BunkBed':p['prototype']='BunkBedMessy'+str((bedindex*3+bedindex//4)%4);bedindex+=1
        elif key=='WashBasin':p['position'][1]=-2.181
        elif key=='Mirror':p['position'][1]=-2.014;p['position'][2]=1.315
        elif key=='ShowerFittings':p['position'][1]=-10.804
        elif key=='TowelRack':p['position'][0]=-11.744
        elif key=='Noticeboard':
            if room['id']=='StaffDormitory':p['position'][1]=1.787
            elif room['id']=='StaffChangingShowers':p['position'][1]=1.587
    room['refinement_revision']=3
(OUT/'room-refined.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf8')

# Complete editable source: append untouched objects, then add updated assemblies.
excluded_prefixes=('UCX_SM_Staff_BunkBed','UCX_SM_Staff_WashBasin','UCX_SM_Staff_LaundryBasket')
excluded_names={'SM_Staff_'+k for k in ('BunkBed','WashBasin','ShowerFittings','FloorDrain','Mirror','TowelRack','LaundryBasket','Noticeboard')}
excluded_names.update(k for k in changed if k.startswith('SM_Staff_'))
affected_ids={room['id']+'_'+p['id'] for room in CFG['rooms'] for p in room['furniture'] if p['prototype'] in changed or p['prototype']=='BunkBed'}
with bpy.data.libraries.load(str(ROOT/'Authored/StaffLivingTheme_Source.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n not in excluded_names and n not in affected_ids and not n.startswith(excluded_prefixes)]
for ob in dst.objects:
    if ob: bpy.context.scene.collection.objects.link(ob)
for room,offset in zip(cfg['rooms'],cfg['preview_placements_m']):
    for p in room['furniture']:
        if p['prototype'] not in changed:continue
        source=bpy.data.objects[changed[p['prototype']]];inst=source.copy();inst.data=source.data
        inst.name=room['id']+'_'+p['id'];bpy.context.scene.collection.objects.link(inst)
        inst.location=Vector(offset)+Vector(p['position']);inst.rotation_euler.z=math.radians(p['yaw_blender_deg'])
source=bpy.data.objects['SM_Staff_Link_Carpet_V3'];source.location=(16,0,0)
inst=source.copy();inst.data=source.data;inst.name='SM_Staff_Link_Carpet_V3_Second'
bpy.context.scene.collection.objects.link(inst);inst.location=(48,0,0)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'StaffLivingTheme_RefinementV3.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(objects=records,changed=changed,revision=cfg['revision'],
    original_manifest=str(ROOT/'Authored/manifest.json'),source_units='metres; UE centimetres',
    cloth='Hospital Bed linen atlas + existing textile fiber normal; baked irregular geometry',
    drainage='room_detail_geometry.grate reused without changing accepted source',tests_run=False,rendered=False),indent=2),encoding='utf8')
print('STAFF_REFINEMENT_SOURCE_SAVED',len(records),flush=True)
