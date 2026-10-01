"""Original industrial treatment hall. Source dimensions in metres; no render/test."""
from pathlib import Path
SCRIPT=Path(__file__).resolve().parent
PROJECT=SCRIPT.parents[2]
exec(compile((PROJECT/'SourceAssets/DungeonAnatomyTheatre20261001/Scripts/geometry.py').read_text('utf-8'),'shared_geometry','exec'))
OUT=Path(globals().get('EXPORT_OUT',OUT));OUT.mkdir(parents=True,exist_ok=True);detail.setup(globals());ROOM['height_m']=8.
CFG['revision']=globals().get('EXPORT_REVISION',CFG['revision'])
ATLAS=json.loads((OUT/'atlas.json').read_text('utf-8'))
MAPPING['Labels']=CFG['ue_base']+'/RefineV2/Materials/M_FlueGas_Labels_V2'
MATS['Labels']=bpy.data.materials.new('RS_Labels')
for key in ('Green','Red'):
    MAPPING[key]='/Game/Dungeons/SeamMetal20260923/Materials/MI_Room_'+key+'Paint'
    MATS[key]=bpy.data.materials.new('RS_'+key)
RAIL_RUNS=[]

def basis(axis):
    n=Vector(axis).normalized();u=Vector((0,0,1)).cross(n) if abs(n.z)<.9 else Vector((1,0,0))
    u.normalize();return n,u,n.cross(u)

def lathe(kind,c,axis,profile,mat='PipeEnamel',segments=64):
    n,u,v=basis(axis);c=Vector(c);vs=[];fs=[];uv=[];smooth=[]
    for z,r in profile:
        vs.extend(c+n*z+(u*math.cos(i*math.tau/segments)+v*math.sin(i*math.tau/segments))*r for i in range(segments))
    for k in range(len(profile)-1):
        for i in range(segments):
            j=(i+1)%segments;fs.append((k*segments+i,k*segments+j,(k+1)*segments+j,(k+1)*segments+i))
            r=(profile[k][1]+profile[k+1][1])/2
            uv.append([(i/segments*math.tau*r/.8,profile[k][0]/.8),((i+1)/segments*math.tau*r/.8,profile[k][0]/.8),
                ((i+1)/segments*math.tau*r/.8,profile[k+1][0]/.8),(i/segments*math.tau*r/.8,profile[k+1][0]/.8)])
            smooth.append(True)
    fs.extend([tuple(reversed(range(segments))),tuple((len(profile)-1)*segments+i for i in range(segments))]);uv.extend([None,None]);smooth.extend([False,False])
    poly(kind,vs,fs,mat,uv,smooth)

def plate(kind,c,width,height,key,normal=(0,-1,0)):
    n,u,v=basis(normal);c=Vector(c)
    beam(kind,c-n*.026,c-n*.009,width,height,'BareSteel')
    x0,y0,x1,y1=ATLAS['rects'][key];w,h=ATLAS['size']
    coords=[(x0/w,1-y1/h),(x1/w,1-y1/h),(x1/w,1-y0/h),(x0/w,1-y0/h)]
    poly(kind,[c-u*width/2-v*height/2,c+u*width/2-v*height/2,c+u*width/2+v*height/2,c-u*width/2+v*height/2],[(0,1,2,3)],'Labels',[coords])
    for a in (-1,1):
        for b in (-1,1):detail.fastener(c+u*a*(width/2-.024)+v*b*(height/2-.024),n,.006,kind)

def gauge(c,axis,key='Pressure',angle=152):
    n,u,v=basis(axis);c=Vector(c);r=.17
    lathe('Instruments',c,n,[(0,r*.94),(.012,r),(.073,r),(.090,r*.96),(.095,r*.92)],'BareSteel',64)
    centre=c+n*.098;vs=[centre];uvs=[(.5,.5)]
    for i in range(49):
        a=i*math.tau/48;vs.append(centre+(u*math.cos(a)+v*math.sin(a))*r*.90);uvs.append((.5+.49*math.cos(a),.5-.49*math.sin(a)))
    x0,y0,x1,y1=ATLAS['rects'][key];w,h=ATLAS['size']
    coords=[((x0+a*(x1-x0))/w,1-(y0+b*(y1-y0))/h) for a,b in uvs]
    poly('Instruments',vs,[(0,i+1,i+2) for i in range(48)],'Labels',[[coords[0],coords[i+1],coords[i+2]] for i in range(48)])
    t=math.radians(angle);tip=centre+(u*math.cos(t)+v*math.sin(t))*.123+n*.009
    detail.tube('Instruments',[centre+n*.009,tip],.004,'Rubber',12)
    detail.tube('Instruments',[centre,centre+n*.018],.011,'BareSteel',16)
    detail.ring(centre,n,.174,.156,.015,'BareSteel',48,'Instruments')
    detail.ring(centre-n*.003,n,.159,.153,.006,'Rubber',48,'Instruments')

def wheel(c,axis,r=.19,kind='Valves'):
    n,u,v=basis(axis);c=Vector(c)
    detail.tube(kind,[c-n*.18,c+n*.024],.026,'BareSteel',20)
    detail.torus(c,n,r,.016,kind,'Yellow',40)
    for i in range(4):
        t=i*math.pi/2;detail.tube(kind,[c,c+(u*math.cos(t)+v*math.sin(t))*r],.011,'BareSteel',12)
    detail.fastener(c+n*.03,n,.017,kind)

def flange(c,n,r,kind='DuctFlanges'):
    c=Vector(c);n,u,v=basis(n)
    for offset in (-.03,.03):detail.ring(c+n*offset,n,r+.10,r-.008,.045,'BareSteel',64,kind)
    detail.ring(c,n,r+.073,r-.007,.014,'Rubber',64,kind)
    for i in range(12):
        t=i*math.tau/12;detail.fastener(c+n*.058+(u*math.cos(t)+v*math.sin(t))*(r+.06),n,.016,kind)

def pipe(kind,points,r,mat='PipeEnamel',sides=48):
    # Continuous quarter-circle elbows retain a believable bend radius.
    ps=[Vector(p) for p in points];path=[ps[0]]
    for i in range(1,len(ps)-1):
        p=ps[i];a=(p-ps[i-1]).normalized();b=(ps[i+1]-p).normalized()
        reach=min(max(r*1.7,.14),(p-ps[i-1]).length*.4,(ps[i+1]-p).length*.4)
        centre=p-a*reach+b*reach
        path.extend(centre-b*reach*math.cos(j/16*math.pi/2)+a*reach*math.sin(j/16*math.pi/2) for j in range(17))
    path.append(ps[-1])
    # One connected annular solid. Splitting materials into three duplicated vertex
    # arrays made the inner shell independently flip outwards during normal repair.
    rings=detail.frames(path);thickness=max(.008,r*.025);vs=[];fs=[];uv=[];sm=[];mats=[]
    distance=[0]
    for i in range(1,len(rings)):distance.append(distance[-1]+(rings[i][0]-rings[i-1][0]).length)
    count=len(rings)*sides
    for radius in (r,r-thickness):
        for p,t,a,b in rings:
            vs.extend(p+radius*(a*math.cos(j*math.tau/sides)+b*math.sin(j*math.tau/sides)) for j in range(sides))
    for layer,radius in enumerate((r,r-thickness)):
        for i in range(len(rings)-1):
            for j in range(sides):
                ids=[layer*count+i*sides+j,layer*count+i*sides+(j+1)%sides,layer*count+(i+1)*sides+(j+1)%sides,layer*count+(i+1)*sides+j]
                coords=[(j/sides*math.tau*radius/.8,distance[i]/.8),((j+1)/sides*math.tau*radius/.8,distance[i]/.8),
                    ((j+1)/sides*math.tau*radius/.8,distance[i+1]/.8),(j/sides*math.tau*radius/.8,distance[i+1]/.8)]
                if layer:ids.reverse();coords.reverse()
                fs.append(ids);uv.append(coords);sm.append(True);mats.append(mat if layer==0 else 'PipeInner')
    for end in (0,len(rings)-1):
        p,t,a,b=rings[end]
        for j in range(sides):
            ids=[end*sides+j,count+end*sides+j,count+end*sides+(j+1)%sides,end*sides+(j+1)%sides]
            if end:ids.reverse()
            fs.append(ids);uv.append([(vs[k].dot(a)/.8,vs[k].dot(b)/.8) for k in ids]);sm.append(False);mats.append('PipeCutSteel')
    start=len(group(kind)['f']);poly(kind,vs,fs,mat,uv,sm);group(kind)['m'][start:]=mats

def rail_bar(kind,a,b,zlo,zhi,width,mat):
    a,b=Vector(a),Vector(b);along=b-a;along.z=0;along.normalize();side=Vector((-along.y,along.x,0))
    vs=[p+side*s*width/2+Vector((0,0,z)) for p in (a,b) for s,z in ((-1,zlo),(1,zlo),(1,zhi),(-1,zhi))]
    poly(kind,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)

def railings(a,b,kind='Railings',height=1.10):
    a,b=Vector(a),Vector(b);count=max(1,math.ceil((b-a).length/1.25))
    rail_bar(kind,a,b,height-.04,height+.04,.08,'PaintedSteel')
    rail_bar(kind,a,b,.48,.54,.06,'PaintedSteel')
    for i in range(count+1):
        p=a+(b-a)*i/count
        box(kind,p+Vector((0,0,height/2)),(.08,.08,height),'PaintedSteel')
        box(kind,p+Vector((0,0,.012)),(.15,.15,.024),'BareSteel')
    RAIL_RUNS.append(dict(kind=kind,a=list(a),b=list(b),height=height,width=.08))

def metal_box(kind,c,size,mat='PaintedSteel'):
    box(kind,c,size,mat)

# Concrete shell, real construction joints, chamfered structural beams.
paving(-14,-12,14,12)
outline=[(-14,-12),(14,-12),(14,12),(-14,12)]
for a,b in zip(outline,outline[1:]+outline[:1]):
    openings=[]
    if a[0]==b[0]:openings=[dict(center=abs(-8-a[1]),width=3.,height=2.8)]
    wall_segment(a,b,8,openings,tiles=False)
box('Roof',(0,0,8.17),(28.28,24.28,.34),'Concrete')
for x in (-13.65,13.65):
    for y in (-11.65,-3,4,11.65):
        box('Columns',(x,y,3.8),(.43,.6,7.6),'Concrete')
        box('Columns',(x,y,.15),(.64,.80,.30),'Concrete')
for y in (-10,-3,4,11):
    box('RoofRibs',(0,y,7.67),(27.3,.32,.65),'Concrete')
for sign in (-1,1):
    a,b=sorted((14*sign,16*sign));paving(a,-10,b,-6)
    wall_segment((a,-10),(b,-10),3.4,tiles=False);wall_segment((b,-6),(a,-6),3.4,tiles=False)
    wall_segment((16*sign,-10),(16*sign,-6),3.4,[dict(center=2,width=3,height=2.8)],tiles=False)
    box('Roof',((a+b)/2,-8,3.54),(2.28,4.28,.28),'Concrete')
    if CFG.get('phase')=='subject':box('SamplePortCaps',(16*sign,-8,1.4),(.15,3.0,2.8),'PaintedSteel')

# Two scrubber vessels: concrete curbs, shoes, dished heads, circumferential seams.
for index,tower in enumerate(CFG['towers']):
    x,y,z=tower['position'];r=tower['radius'];kind='Scrubber'+str(index+1)
    box('EquipmentPlinths',(x,y,.15),(3.85,3.85,.3),'Concrete')
    for dx in (-1,1):
        for dy in (-1,1):
            xx=x+dx*1.03;yy=y+dy*1.03
            box(kind,(xx,yy,.33),(.39,.39,.06),'BareSteel')
            beam(kind,(xx,yy,.36),(xx,yy,1.10),.16,.16,'PaintedSteel')
            for a in (-.12,.12):detail.fastener((xx+a,yy,.374),(0,0,1),.022,kind)
    profile=[(.60,.22),(.66,.6),(.77,1.02),(.96,1.38),(1.15,r),(5.63,r)]
    profile += [(5.63+.71*math.sin(i*math.pi/2/12),r*math.cos(i*math.pi/2/12)) for i in range(1,12)]
    profile.append((6.34,.07));lathe(kind,(x,y,0),(0,0,1),profile,'PipeEnamel',96)
    for zz in (1.38,3.35,5.4):
        detail.torus((x,y,zz),(0,0,1),r+.003,.008,kind,'BareSteel',96)
    for zz in (1.75,4.28):
        c=Vector((x+r+.065,y,zz));axis=(1,0,0)
        detail.ring(c,axis,.42,.28,.13,'BareSteel',64,kind)
        lathe(kind,c,axis,[(.045,.36),(.074,.36)],'PaintedSteel',64)
        for j in range(10):
            a=j*math.tau/10;detail.fastener(c+Vector((.085,.325*math.cos(a),.325*math.sin(a))),axis,.016,kind)
        for yy in (-.11,.11):detail.tube(kind,[c+Vector((.092,yy,-.10)),c+Vector((.15,yy,-.10)),c+Vector((.15,yy,.10)),c+Vector((.092,yy,.10))],.014,'BareSteel',12)
    shell_x=x+math.sqrt(r*r-.65*.65)
    pipe('WetPipework',[(shell_x-.065,y-.65,1.15),(x+2.05,y-.65,1.15),(x+2.05,y-.65,.40),(x+3.10,y-.65,.40),(x+3.10,y-.65,.10)],.10)
    lathe('PipeCouplings',(shell_x-.045,y-.65,1.15),(1,0,0),[(0,.15),(.16,.15)],'BareSteel',48)
    flange((shell_x+.19,y-.65,1.15),(1,0,0),.10,'PipeCouplings')
    lathe('PipeCouplings',(x+2.05,y-.65,.65),(0,0,1),[(0,.10),(.03,.145),(.20,.145),(.24,.10)],'PaintedSteel',48)
    wheel((x+2.29,y-.65,.77),(1,0,0),.17)
    gauge((x+r+.24,y+.67,1.72),(1,0,0),angle=152+index*34)
    shell_x=x+math.sqrt(r*r-.67*.67)
    pipe('WetPipework',[(shell_x-.055,y+.67,1.30),(x+r+.24,y+.67,1.30),(x+r+.24,y+.67,1.62)],.023,sides=24)
    lathe('PipeCouplings',(shell_x-.04,y+.67,1.30),(1,0,0),[(0,.065),(.10,.065)],'BareSteel',32)
    detail.ring((shell_x+.08,y+.67,1.30),(1,0,0),.080,.025,.024,'BareSteel',32,'PipeCouplings')
    lathe('PipeCouplings',(x+r+.24,y+.67,1.52),(0,0,1),[(0,.037),(.10,.037)],'BareSteel',6)
    plate('Signs',(x,y-r-.025,2.45),1.05,.315,'Tower'+str(index+1))
    # Spray manifold and its separate injection nozzles terminate in the vessel shell.
    pipe('WetPipework',[(x-1.8,y,0.25),(x-1.8,y,4.8),(x-1.42,y,4.8)],.08)
    for zz in (1.4,3.0,4.6):detail.ring((x-1.8,y,zz),(0,0,1),.095,.081,.05,'BareSteel',24,'WetPipework')

# Gas route: low inlet into first vessel, upper transfer into second; then bag filter.
pipe('GasDucts',[(-13.9,-5,4.6),(-10.4,-5,4.6),(-10.4,-5,3.1),(-9.53,-5,3.1)],.48)
pipe('GasDucts',[(-8,-5,6.22),(-8,-5,7.05),(-8,2,7.05),(-8,2,6.20)],.49)
pipe('GasDucts',[(-6.46,2,5.2),(-4.8,2,5.2),(-4.8,6.5,5.2),(5.4,6.5,5.2),(5.4,3.2,5.2),(6.21,3.2,5.2)],.54)
for p,n,r in [((-12,-5,4.6),(1,0,0),.48),((-8,-2,7.05),(0,1,0),.49),((-3,6.5,5.2),(1,0,0),.54),((2.0,6.5,5.2),(1,0,0),.54)]:flange(p,n,r)
for x in (-3,2):
    for y in (5.86,7.14):
        detail.tube('DuctSupports',[(x,y,4.59),(x,y,7.96)],.016,'BareSteel',12)
        box('DuctSupports',(x,y,7.95),(.19,.19,.045),'BareSteel')
    box('DuctSupports',(x,6.5,4.61),(.12,1.48,.12),'BareSteel')

# Baghouse panels, removable doors and two tapered hoppers with sealed collection bins.
x,y,z=CFG['filter']['position'];w=CFG['filter']['width'];length=CFG['filter']['length']
box('EquipmentPlinths',(x,y,.12),(w+.55,length+.5,.24),'Concrete')
for xx in (x-w/2+.17,x+w/2-.17):
    for yy in (y-length/2+.2,y,y+length/2-.2):
        box('BaghouseFrame',(xx,yy,2.06),(.16,.16,3.70),'BareSteel')
        box('BaghouseFrame',(xx,yy,.275),(.4,.4,.07),'BareSteel')
        for dx in (-.125,.125):detail.fastener((xx+dx,yy,.321),(0,0,1),.018,'BaghouseFrame')
for zz in (2.7,6.5):
    for xx in (x-w/2,x+w/2):box('BaghouseFrame',(xx,y,zz),(.15,length,.18),'BareSteel')
    for yy in (y-length/2,y+length/2):box('BaghouseFrame',(x,yy,zz),(w,.15,.18),'BareSteel')
box('Baghouse',(x,y,4.6),(w-.12,length-.12,3.67),'PipeEnamel')
box('Baghouse',(x,y,6.55),(w+.08,length+.08,.16),'PaintedSteel')
for xx in (x-w/2-.012,x+w/2+.012):
    for yy in (y-2.35,y,y+2.35):
        box('BaghouseDoors',(xx,yy,4.40),(.095,2.14,2.7),'PaintedSteel')
        side=-1 if xx<x else 1
        for dy in (-.86,.86):
            for zz in (3.32,5.48):detail.fastener((xx+side*.06,yy+dy,zz),(side,0,0),.014,'BaghouseDoors')
        for zz in (3.60,5.15):box('BaghouseDoors',(xx+side*.083,yy-.91,zz),(.09,.19,.12),'BareSteel')
        detail.tube('BaghouseDoors',[(xx+side*.08,yy+.79,4.17),(xx+side*.19,yy+.79,4.17),(xx+side*.19,yy+.79,4.56),(xx+side*.08,yy+.79,4.56)],.022,'BareSteel',16)
        for j in range(6):box('BaghouseDoors',(xx+side*.065,yy,5.30+j*.056),(.026,.67,.022),'BareSteel')
for cy in (-.95,2.55):
    top=[(x-2.2,cy-1.58,2.70),(x+2.2,cy-1.58,2.70),(x+2.2,cy+1.58,2.70),(x-2.2,cy+1.58,2.70)]
    low=[(x-.28,cy-.28,1.34),(x+.28,cy-.28,1.34),(x+.28,cy+.28,1.34),(x-.28,cy+.28,1.34)]
    poly('Hoppers',low+top,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'PaintedSteel')
    box('Hoppers',(x,cy,1.31),(.69,.69,.13),'BareSteel')
    wheel((x-.49,cy,1.3),(-1,0,0),.18)
    lathe('DustBins',(x,cy,.26),(0,0,1),[(0,.55),(.04,.61),(.77,.61),(.81,.64),(.86,.64)],'ServicePaint',64)
    for zz in (.33,.93):detail.torus((x,cy,zz),(0,0,1),.619,.020,'DustBins','BareSteel',64)
    detail.tube('Hoppers',[(x,cy,1.08),(x,cy,1.30)],.255,'Rubber',32)
plate('Signs',(x,y-length/2-.073,4.7),1.55,.465,'Filter')

# Centrifugal extraction fan on a structural skid, motor fins, flange and drive guard.
fx,fy=8.0,6.6
box('FanSkid',(fx,fy,.19),(3.8,2.45,.38),'Concrete')
for yy in (fy-.80,fy+.80):box('FanSkid',(fx,yy,.44),(3.5,.17,.17),'BareSteel')
profile=[]
for i in range(81):
    a=i/80*math.tau;r=.74+.40*i/80;profile.append((fy+r*math.sin(a),1.54+r*math.cos(a)))
extrude_x('FanHousing',profile,fx-.9,fx+.05,'PipeEnamel')
detail.ring((fx-.97,fy,1.54),(1,0,0),.79,.55,.15,'BareSteel',64,'FanHousing')
lathe('FanHousing',(fx-.99,fy,1.54),(1,0,0),[(0,.54),(.03,.54)],'Rubber',64)
for dy in [-.45,-.30,-.15,0,.15,.3,.45]:
    hh=math.sqrt(.51**2-dy**2)
    detail.tube('FanHousing',[(fx-1.02,fy+dy,1.54-hh),(fx-1.02,fy+dy,1.54+hh)],.009,'BareSteel',12)
lathe('FanMotor',(fx+.25,fy,1.06),(1,0,0),[(0,.24),(.15,.34),(1.25,.34),(1.38,.29)],'PaintedSteel',48)
for i in range(24):
    a=i*math.tau/24
    detail.tube('FanMotor',[(fx+.43,fy+.355*math.cos(a),1.06+.355*math.sin(a)),(fx+1.45,fy+.355*math.cos(a),1.06+.355*math.sin(a))],.019,'BareSteel',12)
for xx in (fx+.55,fx+1.3):box('FanMotor',(xx,fy,.59),(.19,.83,.26),'BareSteel')
box('FanMotor',(fx+.94,fy,1.48),(.4,.38,.21),'PaintedSteel')
pipe('Exhaust',[(8.6,4.27,5.0),(6.0,4.27,5.0),(6.0,6.6,5.0),(6.0,6.6,1.54),(7.1,6.6,1.54)],.45)
pipe('Exhaust',[(7.7,7.35,1.9),(7.7,7.35,7.03),(12.9,7.35,7.03),(12.9,11.88,7.03)],.48)
flange((12.9,9.5,7.03),(0,1,0),.48)
plate('Signs',(fx,fy-1.0,.80),.9,.27,'Fan')

# Elevated gallery and two broad access stairs. All rail feet follow real tread planes.
px0,py0,px1,py1=CFG['platform']['rect'];top=CFG['platform']['height']
box('PlatformDeck',((px0+px1)/2,(py0+py1)/2,top-.08),(px1-px0,py1-py0,.16),'BridgeDeck')
for yy in (py0+.15,py1-.15):
    box('PlatformFrame',(0,yy,top-.23),(27,.16,.3),'BareSteel')
    for xx in (-12,-6,0,6,12):
        box('PlatformFrame',(xx,yy,(top-.35)/2),(.16,.16,top-.35),'BareSteel')
        box('PlatformFrame',(xx,yy,.023),(.36,.36,.045),'BareSteel')
        beam('PlatformFrame',(xx,yy,1.25),(xx+.8 if xx<12 else xx-.8,yy,2.1),.07,.07,'BareSteel')
railings((-11.40,py0+.07,top),(11.40,py0+.07,top),height=1.10)
box('KickPlates',(0,py0+.075,top+.10),(22.8,.018,.20),'PaintedSteel')
for x in CFG['stairs']['centres_x']:
    for step in range(15):
        z=(step+1)*.16;yy=3.1+(step+.5)*.36
        box('StairTreads',(x,yy,z-.035),(1.8,.36,.07),'BridgeDeck')
        box('Nosing',(x,yy-.162,z+.004),(1.77,.027,.008),'Yellow')
    for side in (-1,1):
        xx=x+side*.83
        beam('StairStringers',(xx,3.13,.025),(xx,8.48,2.3),.12,.22,'BareSteel')
        ps=[]
        for step in (0,3,6,9,12,14):
            p=(xx,3.1+(step+.5)*.36,(step+1)*.16)
            box('StairRails',(p[0],p[1],p[2]+.012),(.14,.14,.024),'BareSteel')
            box('StairRails',(p[0],p[1],p[2]+.55),(.08,.08,1.10),'PaintedSteel')
            ps.append(Vector((p[0],p[1],p[2]+1.10)))
        a,b=ps[0]-Vector((0,0,1.10)),ps[-1]-Vector((0,0,1.10))
        rail_bar('StairRails',a,b,1.06,1.14,.08,'PaintedSteel')
        rail_bar('StairRails',a,b,.48,.54,.06,'PaintedSteel')
        rail_bar('StairRails',b,(xx,8.66,2.4),1.06,1.14,.08,'PaintedSteel')
        RAIL_RUNS.append(dict(kind='StairRails',a=list(a),b=list(b),height=1.10,width=.08))
        RAIL_RUNS.append(dict(kind='StairRails',a=list(b),b=[xx,8.66,2.4],height=1.10,width=.08))
for sign in (-1,1):railings((sign*13.43,py0,top),(sign*13.43,py1,top))

# Rear control panel and readable maintenance signs clear of steelwork.
plate('Signs',(0,11.82,4.55),3.25,.98,'Main')
plate('Signs',(0,8.435,3.05),1.40,.42,'Platform')
for xx in (-.50,.50):beam('Signs',(xx,8.57,2.48),(xx,8.57,3.26),.036,.036,'BareSteel')
plate('Signs',(-13.825,-8,3.36),1.12,.34,'Entry',(1,0,0))
plate('Signs',(13.825,-8,3.36),1.12,.34,'Exit',(-1,0,0))
box('ControlPanel',(0,11.70,3.29),(2.40,.26,1.35),'PaintedSteel')
box('ControlPanel',(0,11.55,3.29),(2.28,.045,1.23),'Rubber')
for xx,ww in [(-.79,.72),(0,.78),(.79,.72)]:
    box('ControlPanel',(xx,11.512,3.29),(ww,.035,1.18),'PipeEnamel')
    for dx in (-ww/2+.037,ww/2-.037):
        for zz in (2.75,3.83):detail.fastener((xx+dx,11.488,zz),(0,-1,0),.008,'ControlHardware')
for xx,key,angle in [(-.79,'Pressure',142),(0,'Temperature',118)]:
    gauge((xx,11.47,3.52),(0,-1,0),key,angle=angle)
    plate('ControlHardware',(xx,11.478,3.21),.44,.095,'Inlet' if xx<0 else 'Flow')
    lathe('ControlHardware',(xx,11.474,2.94),(0,-1,0),[(0,.082),(.025,.082)],'BareSteel',48)
    lathe('ControlHardware',(xx,11.443,2.94),(0,-1,0),[(0,.064),(.055,.064),(.063,.055)],'Rubber',32)
    box('ControlHardware',(xx,11.372,2.94),(.027,.025,.10),'BareSteel')
    for j in range(7):
        a=math.radians(30+j*20);p=(xx+.095*math.cos(a),11.481,2.94+.095*math.sin(a))
        detail.tube('ControlHardware',[p,(p[0],p[1]-.007,p[2])],.005,'BareSteel',12)
    plate('ControlHardware',(xx,11.478,2.77),.31,.075,'Auto')
plate('ControlHardware',(.79,11.478,3.71),.57,.19,'Serial')
for xx,mat in ((.58,'Green'),(.80,'Yellow'),(1.02,'Red')):
    detail.ring((xx,11.472,3.47),(0,-1,0),.051,.033,.035,'BareSteel',32,'ControlHardware')
    lathe('ControlHardware',(xx,11.456,3.47),(0,-1,0),[(0,.033),(.031,.033),(.041,.025)],mat,32)
for xx,key,mat in ((.61,'FanStart','Green'),(.98,'FanStop','Red')):
    lathe('ControlHardware',(xx,11.48,3.16),(0,-1,0),[(0,.058),(.026,.058)],'BareSteel',32)
    lathe('ControlHardware',(xx,11.451,3.16),(0,-1,0),[(0,.044),(.033,.044)],mat,32)
    plate('ControlHardware',(xx,11.478,3.035),.27,.075,key)
lathe('ControlHardware',(.80,11.48,2.84),(0,-1,0),[(0,.105),(.015,.105)],'Yellow',48)
lathe('ControlHardware',(.80,11.455,2.84),(0,-1,0),[(0,.036),(.047,.036),(.06,.066),(.085,.066)],'Red',48)
for xx in (-1.16,1.16):
    for zz in (2.91,3.69):lathe('ControlHardware',(xx,11.512,zz),(0,0,1),[(-.07,.022),(.07,.022)],'BareSteel',24)
# Folded drip hood, cable glands, external conduit and mounting shoes.
box('ControlPanel',(0,11.57,3.994),(2.48,.54,.038),'PaintedSteel')
box('ControlPanel',(0,11.319,3.965),(2.48,.034,.072),'BareSteel')
for xx in (-.98,.98):
    box('ControlHardware',(xx,11.79,2.57),(.14,.08,.17),'BareSteel')
    detail.fastener((xx,11.741,2.56),(0,-1,0),.015,'ControlHardware')
for xx in (-.85,-.6):
    lathe('ControlHardware',(xx,11.71,2.61),(0,0,1),[(-.07,.04),(0,.04)],'Rubber',24)
    detail.tube('ControlHardware',[(xx,11.71,2.56),(xx,11.71,2.46),(xx,11.85,2.46)],.018,'Rubber',16)

# Drains, restrained exclusion stripes and overhead cable trays leave the aisle clear.
for x in (-4.9,4.9):
    box('DrainChannels',(x,0,.006),(.25,12,.012),'Rubber')
    for y in [j*.14-5.93 for j in range(86)]:box('DrainGrates',(x,y,.021),(.24,.026,.026),'BareSteel')
    for dx in (-.118,.118):box('DrainGrates',(x+dx,0,.02),(.018,12,.04),'BareSteel')
def exclusion_outline(x0,y0,x1,y1,width=.06):
    # A single mitered ring with shared corner vertices, on the floor only.
    outer=[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
    inner=[(x0+width,y0+width),(x1-width,y0+width),(x1-width,y1-width),(x0+width,y1-width)]
    vs=[(x,y,.007) for x,y in outer+inner]
    poly('FloorMarkings',vs,[(i,(i+1)%4,(i+1)%4+4,i+4) for i in range(4)],'Yellow')
exclusion_outline(-10.18,-7.20,-5.20,4.2)
exclusion_outline(5.2,-3.3,11.42,8.12)
for x in (-3.8,3.8):
    for side in (-1,1):box('CableTrays',(x+side*.23,0,7.21),(.045,22,.14),'BareSteel')
    for yy in range(-11,12):box('CableTrays',(x,yy,7.16),(.48,.06,.04),'BareSteel')
    for yy in (-9,-4,1,6,10):
        for side in (-1,1):detail.tube('CableTrays',[(x+side*.25,yy,7.15),(x+side*.25,yy,7.96)],.009,'BareSteel',12)
    for dx in (-.11,0,.11):detail.tube('CableTrays',[(x+dx,-11.5,7.2),(x+dx,11.5,7.2)],.023,'Rubber',12)
for light in CFG['lights']:
    x,y,z=light['position'];ceiling=3.4 if abs(x)>14 else 8
    for dx in (-.28,.28):detail.tube('LampHangers',[(x+dx,y,z+.08),(x+dx,y,ceiling-.03)],.011,'BareSteel',12)
exec(compile((SCRIPT/'export_geometry.py').read_text('utf-8'),str(SCRIPT/'export_geometry.py'),'exec'))
