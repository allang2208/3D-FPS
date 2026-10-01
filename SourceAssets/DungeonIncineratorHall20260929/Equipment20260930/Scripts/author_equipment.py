"""Dimensioned hard-surface assemblies. Editable source and UE game exports; no renders."""
import json,math,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector,Euler
sys.path.insert(0,str(Path(__file__).resolve().parent))
import mesh_helpers as g
from mesh_helpers import box,face,rod,lathe,tube,bolt,plaque,basis
ROOT=Path(__file__).resolve().parents[1]
PARTS=[];CURRENT=None

def part(name):
    global CURRENT
    if CURRENT:CURRENT['last_vertex']=len(g.V)
    CURRENT={'name':name,'first_vertex':len(g.V)};PARTS.append(CURRENT)

def torus(c,axis,radius,wire,surface='steel',major=64,minor=10):
    n,u,v=basis(axis);c=Vector(c)
    rings=[]
    for i in range(major):
        a=i*math.tau/major;direction=u*math.cos(a)+v*math.sin(a)
        rings.append([c+direction*(radius+wire*math.cos(j*math.tau/minor))+n*wire*math.sin(j*math.tau/minor) for j in range(minor)])
    for i in range(major):
        for j in range(minor):
            face([rings[i][j],rings[(i+1)%major][j],rings[(i+1)%major][(j+1)%minor],rings[i][(j+1)%minor]],surface,
                 [(i/major,j/minor),((i+1)/major,j/minor),((i+1)/major,(j+1)/minor),(i/major,(j+1)/minor)],True)

def curved(points,r,surface='rubber',segments=12,resolution=7):
    p=[Vector(a) for a in points];out=[]
    for i in range(len(p)-1):
        a=p[max(0,i-1)];b=p[i];c=p[i+1];d=p[min(len(p)-1,i+2)]
        for j in range(resolution):
            t=j/resolution;out.append((b*2+(c-a)*t+(a*2-b*5+c*4-d)*t*t+(-a+b*3-c*3+d)*t*t*t)*.5)
    out.append(p[-1]);tube(out,r,surface,segments)

def beam(a,b,width,height,surface='teal',wall=.004):
    # Hollow rectangular section, with four real walls and open end bores.
    a=Vector(a);b=Vector(b);n,u,v=basis(b-a)
    for sign in (-1,1):
        for verts in ([a+u*sign*width/2-v*height/2,b+u*sign*width/2-v*height/2,b+u*sign*width/2+v*height/2,a+u*sign*width/2+v*height/2],):
            plate(verts,wall,surface)
        plate([a-u*width/2+v*sign*height/2,b-u*width/2+v*sign*height/2,b+u*width/2+v*sign*height/2,a+u*width/2+v*sign*height/2],wall,surface)

def plate(points,thickness=.004,surface='steel',bevel=.001):
    points=[Vector(p) for p in points];normal=(points[1]-points[0]).cross(points[2]-points[0]).normalized()
    count=len(points);verts=[p+normal*thickness*.5 for p in points]+[p-normal*thickness*.5 for p in points]
    faces=[tuple(range(count)),tuple(reversed(range(count,count*2)))]+[(i,(i+1)%count,(i+1)%count+count,i+count) for i in range(count)]
    mesh=bpy.data.meshes.new('_sheet');mesh.from_pydata(verts,[],faces)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    if bevel:bmesh.ops.bevel(bm,geom=list(bm.edges),offset=min(bevel,thickness*.22),segments=2,affect='EDGES')
    bm.normal_update()
    for p in bm.faces:
        axis=max(range(3),key=lambda i:abs(p.normal[i]));dims=[i for i in range(3) if i!=axis]
        lo=[min(v.co[i] for v in bm.verts) for i in dims];hi=[max(v.co[i] for v in bm.verts) for i in dims]
        uv=[(.02+.96*(v.co[dims[0]]-lo[0])/max(hi[0]-lo[0],.0001),.98-.96*(v.co[dims[1]]-lo[1])/max(hi[1]-lo[1],.0001)) for v in p.verts]
        face([v.co.copy() for v in p.verts],surface,uv,p.calc_area()<thickness*.04)
    bm.free();bpy.data.meshes.remove(mesh)

def weld(a,b,r=.0035):
    # Narrow irregular weld toe with shallow ripples, only at actual seams.
    a=Vector(a);b=Vector(b);n,u,v=basis(b-a);count=max(3,int((b-a).length/.009))
    tube([a+(b-a)*i/count+u*(math.sin(i*2.1)*r*.24) for i in range(count+1)],r,'steel',6)

def clevis(c,axis=(1,0,0),radius=.028,width=.13):
    c=Vector(c);n=Vector(axis).normalized()
    lathe(c-n*width*.5,n,[(0,radius),(.012,radius*1.16),(.019,radius), (width-.012,radius),(width-.012,radius*1.2),(width,radius*1.2)],'steel',32)
    for sign in (-1,1):
        center=c+n*sign*(width*.5+.002)
        torus(center,n,radius*.87,.002,'steel',32,8)
    u=basis(n)[1]
    curved([c+n*(width*.5+.002)+u*.020,c+n*(width*.5+.01)+u*.022,c+n*(width*.5+.017)+u*.010,c+n*(width*.5+.009)-u*.016],.0017,'steel',8,4)

def fitting(c,axis):
    lathe(c,axis,[(0,.012),(.010,.012),(.010,.008),(.021,.008)],'steel',6,False)
    lathe(Vector(c)+Vector(axis).normalized()*.021,axis,[(0,.009),(.019,.009),(.022,.007)],'steel',24)

def gauge(c,axis=(0,1,0),radius=.057):
    c=Vector(c);n,u,v=basis(axis)
    lathe(c,n,[(0,radius),(.008,radius),(.014,radius*.94),(.028,radius*.94),(.032,radius*.87),(.032,radius*.80),(.027,radius*.80)],'steel',64)
    center=c+n*.029
    for i in range(64):
        a=i*math.tau/64;b=(i+1)*math.tau/64
        face([center,center+(u*math.cos(a)+v*math.sin(a))*radius*.80,center+(u*math.cos(b)+v*math.sin(b))*radius*.80],'gauge',[(.5,.5),(.5+.5*math.cos(a),.5-.5*math.sin(a)),(.5+.5*math.cos(b),.5-.5*math.sin(b))])
    q=math.radians(225);d=u*math.cos(q)+v*math.sin(q);s=n.cross(d);p=center+n*.001
    face([p-d*.009-s*.0015,p+d*radius*.65,p-d*.009+s*.0015],'rubber',[(.3,.3),(.7,.3),(.5,.8)])
    lathe(p,n,[(0,.0035),(.002,.0035)],'steel',20)

def door():
    front=(0,1,0)
    part('01_Fixed_frame_and_seal')
    for x in (-1.16,1.16):
        box((x,-.025,1.65),(.12,.21,2.84),'graphite',.007)
        for z in (.39,.96,1.53,2.10,2.91):bolt((x,.083,z),front,1.65)
        box((x*.933,.044,1.65),(.018,.018,2.61),'rubber',.003)
    for z in (.26,3.04):
        box((0,-.025,z),(2.44,.21,.12),'graphite',.007)
        box((0,.045,.35 if z<1 else 2.95),(2.18,.018,.018),'rubber',.003)
        for x in (-.86,-.43,0,.43,.86):bolt((x,.083,z),front,1.65)
    part('02_Insulated_door_and_stiffeners')
    box((0,-.08,1.65),(2.18,.20,2.58),'soot',.018)
    box((0,.033,1.65),(2.23,.032,2.64),'graphite',.012)
    # Returned skin rims and channel stiffeners have space between their flanges.
    for x in (-1.10,1.10):box((x,-.045,1.65),(.022,.17,2.62),'graphite',.004)
    for z in (.345,2.955):box((0,-.045,z),(2.19,.17,.022),'graphite',.004)
    for x in (-.68,.68):
        for dx in (-.050,.050):box((x+dx,.084,1.65),(.013,.07,2.44),'graphite',.002)
        box((x,.121,1.65),(.11,.012,2.44),'graphite',.002)
    for z in (.53,1.21,2.07,2.78):
        for dz in (-.049,.049):box((0,.084,z+dz),(2.08,.07,.012),'graphite',.002)
        box((0,.122,z),(2.08,.012,.11),'graphite',.002)
        for x in (-.99,-.72,.72,.99):bolt((x,.131,z),front,.95)
    for x in (-.84,.84):
        for z in (.46,2.86):weld((x-.045,.051,z),(x+.045,.051,z))
    plaque((0,.057,2.49),.66,.13,'door_plate',front)
    for x in (-.31,.31):bolt((x,.060,2.49),front,.38)
    # Peep-hole stays cold and capped, with a real retaining hinge and round bezel.
    lathe((.08,.055,1.24),front,[(0,.101),(.016,.101),(.026,.086),(.045,.086)],'steel',64)
    lathe((.08,.100,1.24),front,[(0,.072),(.003,.072)],'soot',48)
    box((.192,.103,1.24),(.025,.05,.086),'graphite',.003)
    rod((.204,.129,1.19),(.204,.129,1.29),.007,'steel',16)
    part('03_Three_knuckle_hinges')
    for z in (.64,1.65,2.66):
        for x in (-1.25,-1.05):
            box((x,.13,z),(.18,.09,.235),'steel',.005)
            for zz in (z-.075,z+.075):bolt((x,.177,zz),front,1.4)
        for i in range(5):lathe((-1.15,.196,z-.12+i*.049),(0,0,1),[(0,.043),(.044,.043)],'steel',32)
        lathe((-1.15,.196,z-.137),(0,0,1),[(0,.026),(.280,.026),(.280,.048),(.293,.048)],'steel',32)
        fitting((-1.15,.241,z),front)
    part('04_Handwheel_gearcase_and_six_dogs')
    box((0,.199,1.86),(.32,.14,.28),'graphite',.018)
    box((0,.278,1.86),(.28,.022,.24),'steel',.010)
    for x in (-.102,.102):
        for z in (1.78,1.94):bolt((x,.291,z),front,.95)
    lathe((0,.291,1.86),front,[(0,.061),(.040,.061),(.045,.042),(.104,.042)],'steel',48)
    torus((0,.411,1.86),front,.268,.021,'graphite',96,14)
    lathe((0,.389,1.86),front,[(0,.056),(.05,.056),(.055,.048)],'steel',48)
    for i in range(5):
        a=i*math.tau/5;rod((math.cos(a)*.051,.400,1.86+math.sin(a)*.051),(math.cos(a)*.251,.411,1.86+math.sin(a)*.251),.012,'graphite',16)
    bolt((0,.448,1.86),front,2.5)
    lathe((.246,.428,1.754),front,[(0,.014),(.02,.014),(.025,.022),(.115,.022),(.125,.015)],'rubber',32)
    for x in (-.83,.83):
        rod((x,.184,.52),(x,.184,2.80),.012,'steel',24)
        rod((0,.176,1.86),(x,.176,1.86),.013,'steel',24)
        for z in (.65,1.66,2.70):
            # Cast bearing stand, rotating crank, short dog shaft, and fixed strike.
            box((x,.147,z),(.095,.07,.13),'graphite',.007)
            lathe((x,.186,z),front,[(0,.031),(.025,.031),(.032,.025)],'steel',32)
            sign=1 if x>0 else -1
            plate([(x-sign*.018,.226,z-.032),(x+sign*.27,.226,z-.019),(x+sign*.29,.226,z+.05),(x-sign*.013,.226,z+.053)],.027,'steel',.003)
            bolt((x,.244,z),front,1.75)
            box((sign*1.105,.139,z+.014),(.14,.082,.14),'graphite',.004)
            box((sign*1.105,.192,z+.070),(.15,.055,.034),'steel',.003)
            for dz in (-.042,.045):bolt((sign*1.153,.184,z+dz),front,.75)
        for z in (.91,2.40):
            box((x,.155,z),(.070,.064,.065),'graphite',.004)
            for dx in (-.029,.029):bolt((x+dx,.191,z),front,.55)
    part('05_Hydraulic_ram_mounts_and_hoses')
    # Ram is fixed to the masonry cheek and drives a lug on the hinged leaf.
    A=Vector((-1.78,.24,1.05));B=Vector((-.99,.43,2.26));n=(B-A).normalized();length=(B-A).length
    box((-1.78,.046,1.05),(.23,.15,.33),'graphite',.008)
    for z in (.94,1.16):bolt((-1.78,.127,z),front,1.6)
    for y in (.184,.296):box((-1.78,y,1.065),(.105,.018,.19),'steel',.004)
    clevis(A,(0,1,0),.027,.145)
    rod(A,A+n*.14,.032,'steel',24)
    barrel=A+n*.145
    lathe(barrel,n,[(0,.078),(.031,.078),(.038,.066),(.69,.066),(.70,.083),(.745,.083),(.745,.049),(.762,.049)],'graphite',48)
    lathe(barrel+n*.762,n,[(0,.041),(.024,.041)],'steel',40)
    rod(barrel+n*.76,B-n*.093,.027,'chrome',40)
    lathe(B-n*.125,n,[(0,.043),(.018,.043),(.025,.034),(.10,.034)],'steel',32)
    for s in (-1,1):
        for t in (-1,1):
            _,u,v=basis(n);off=u*s*.049+v*t*.049
            rod(barrel+off+n*.018,barrel+off+n*.74,.006,'steel',12)
            bolt(barrel+off+n*.746,n,.84)
    for yy in (.375,.487):
        plate([(-1.095,yy,2.09),(-.84,yy,2.09),(-.945,yy,2.32),(-1.047,yy,2.32)],.018,'steel',.002)
    box((-.975,.247,2.14),(.26,.24,.11),'graphite',.005);clevis(B,(0,1,0),.024,.147)
    box((-1.78,.18,2.61),(.24,.11,.29),'graphite',.010)
    for z in (2.51,2.71):bolt((-1.865,.242,z),front,.85)
    gauge((-1.78,.239,2.63))
    for index,t in enumerate((.12,.67)):
        p=barrel+n*t+Vector((0,.064,0));fitting(p,front)
        end=Vector((-1.81+index*.10,.250,2.44));fitting(end,(0,0,-1))
        curved([p+Vector((0,.042,0)),p+Vector((-.05,.16,.06)),(-1.97+index*.11,.48,1.94),(-1.91+index*.10,.38,2.31),end+Vector((0,0,-.043))],.010,'rubber',14,9)
    plaque((-1.78,.126,.75),.25,.12,'service',front)

def caster(x,y,swivel=False,brake=False):
    # 230 mm solid rubber tyre, steel hub, offset swivel bearing and stamped fork.
    wheel_y=y-.026 if swivel else y;z=.115
    lathe((x-.045,wheel_y,z),(1,0,0),[(0,.065),(.003,.100),(.012,.113),(.028,.115),(.062,.115),(.078,.111),(.089,.096),(.090,.065)],'rubber',56)
    for dx in (-.015,.015):torus((x+dx,wheel_y,z),(1,0,0),.1152,.0014,'soot',64,6)
    lathe((x-.051,wheel_y,z),(1,0,0),[(0,.057),(.009,.061),(.093,.061),(.102,.057)],'steel',40)
    for sign in (-1,1):
        sx=x+sign*.052
        lathe((sx,wheel_y,z),(sign,0,0),[(0,.033),(.009,.028),(.014,.021)],'steel',32)
        bolt((sx+sign*.014,wheel_y,z),(sign,0,0),1.5)
        plate([(x+sign*.069,wheel_y-.032,.098),(x+sign*.069,wheel_y+.034,.098),(x+sign*.069,y+.051,.270),(x+sign*.069,y-.049,.270)],.006,'steel',.001)
        for a in range(6):
            t=a*math.tau/6
            lathe((sx,wheel_y+math.cos(t)*.043,z+math.sin(t)*.043),(sign,0,0),[(0,.004),(.001,.004)],'rubber',12)
    box((x,y,.274),(.151,.104,.009),'steel',.003)
    if swivel:
        lathe((x,y,.278),(0,0,1),[(0,.052),(.012,.060),(.025,.060),(.028,.050),(.042,.05)],'steel',48)
        torus((x,y,.299),(0,0,1),.060,.003,'rubber',48,8)
    else:box((x,y,.299),(.103,.091,.042),'steel',.003)
    box((x,y,.332),(.17,.14,.024),'steel',.003)
    for dx in (-.062,.062):
        for dy in (-.047,.047):bolt((x+dx,y+dy,.346),(0,0,1),.68)
    if brake:
        plate([(x-.047,y+.046,.249),(x+.047,y+.046,.249),(x+.047,y+.13,.216),(x-.047,y+.13,.216)],.004,'steel',.001)
        box((x,y+.120,.220),(.081,.046,.009),'rubber',.003,(.24,0,0))
        rod((x-.079,y+.042,.25),(x+.079,y+.042,.25),.006,'steel',16)

def base_frame(color='teal'):
    for x in (-.62,.62):
        beam((x,-.78,.387),(x,.78,.387),.080,.080,color)
        for y in (-.64,.64):caster(x,y,y>.1,y>.1)
    for y in (-.72,.72):beam((-.65,y,.387),(.65,y,.387),.08,.08,color)
    for x in (-.37,.37):
        # True open fork pockets, not a black face painted on a solid box.
        beam((x,-.805,.452),(x,.785,.452),.185,.096,color,.006)
    for y in (-.51,.51):
        for x in (-.60,.60):weld((x-.031,y,.428),(x+.031,y,.428))

def trolley():
    front=(0,1,0)
    part('01_Chassis_and_braked_casters');base_frame()
    part('02_Roller_table_and_bearings')
    for x in (-.62,.62):
        for y in (-.61,.54):beam((x,y,.43),(x,y,.655),.052,.052)
        beam((x,-.81,.661),(x,.65,.661),.069,.093)
    # 720 mm top matches the fixed furnace loading table. Slots remain visible.
    for j in range(17):
        y=-.748+j*.079
        lathe((-.58,y,.692),(1,0,0),[(0,.016),(.013,.027),(.020,.028), (1.140,.028),(1.147,.027),(1.160,.016)],'steel',40)
        for x in (-.626,.626):
            box((x,y,.685),(.014,.041,.042),'graphite',.004)
            bolt((x+(-.010 if x<0 else .010),y,.692),(-1 if x<0 else 1,0,0),.7)
    for x in (-.699,.699):
        box((x,-.07,.759),(.013,1.50,.148),'teal',.004)
        box((x,-.07,.837),(.036,1.51,.012),'steel',.002)
    box((0,.612,.738),(1.39,.021,.048),'ochre',.003)
    # Retractable stop bar with exposed pivot/lock rings; stored down at front.
    rod((-.65,-.835,.690),(.65,-.835,.690),.018,'steel',24)
    for x in (-.64,.64):
        box((x,-.815,.662),(.056,.083,.08),'teal',.004)
        torus((x,-.850,.632),(1,0,0),.017,.002,'steel',24,8)
    part('03_Folded_lower_tray_and_push_handle')
    box((0,0,.507),(1.10,1.25,.004),'steel',.0008)
    for x in (-.549,.549):box((x,0,.527),(.004,1.25,.04),'steel',.001)
    for y in (-.624,.624):box((0,y,.527),(1.10,.004,.04),'steel',.001)
    for x in (-.54,.54):
        curved([(x,.65,.54),(x,.799,.60),(x,.855,.76),(x,.855,1.015),(x*.95,.855,1.065)],.017,'steel',20,6)
        box((x,.645,.56),(.065,.06,.07),'teal',.004)
        for dx in (-.024,.024):bolt((x+dx,.680,.56),front,.7)
    rod((-.514,.855,1.065),(.514,.855,1.065),.017,'steel',24)
    for x in (-.35,.35):lathe((x-.12,.855,1.065),(1,0,0),[(0,.024),(.015,.026),(.225,.026),(.240,.024)],'rubber',32)
    box((0,.752,.553),(.76,.015,.15),'teal',.004)
    plaque((0,.762,.553),.58,.091,'trolley_plate',front)
    for x in (-.27,.27):bolt((x,.765,.553),front,.35)
    for x in (-.70,.70):plaque((x,-.10,.758),.78,.060,'hazard',(-1 if x<0 else 1,0,0))

def hopper():
    front=(0,1,0)
    part('01_Chassis_fork_pockets_and_casters');base_frame('ochre')
    part('02_Tipping_cradle_and_trunnions')
    for x in (-.63,.63):
        plate([(x,-.25,.43),(x,.25,.43),(x,.09,.93),(x,-.09,.93)],.014,'ochre',.002)
        lathe((x-.059,-.015,.868),(1,0,0),[(0,.07),(.025,.07),(.025,.047),(.13,.047),(.13,.07),(.15,.07)],'steel',40)
        fitting((x+(.10 if x>0 else -.075),-.015,.868),(1 if x>0 else -1,0,0))
    part('03_Welded_tapered_bin_and_folded_rim')
    bottom=[(-.49,-.48,.59),(.49,-.48,.59),(.49,.49,.59),(-.49,.49,.59)]
    top=[(-.725,-.77,1.47),(.725,-.77,1.47),(.725,.72,1.47),(-.725,.72,1.47)]
    plate(bottom,.006,'steel')
    for i in range(4):
        j=(i+1)%4;plate([bottom[i],bottom[j],top[j],top[i]],.006,'ochre',.0012)
        weld(bottom[i],bottom[j],.003)
        weld(bottom[i],top[i],.0027)
    # Folded top rail seals against the two real lid panels.
    for x in (-.73,.73):
        box((x,-.025,1.478),(.058,1.55,.014),'ochre',.003)
        box((x,-.025,1.448),(.009,1.55,.054),'ochre',.002)
    for y in (-.785,.735):
        box((0,y,1.478),(1.515,.053,.014),'ochre',.003)
        box((0,y,1.448),(1.515,.009,.055),'ochre',.002)
    for x in (-.728,.728):box((x,-.025,1.490),(.020,1.48,.012),'rubber',.002)
    for y in (-.777,.727):box((0,y,1.490),(1.46,.02,.012),'rubber',.002)
    # Side ribs are external pressed channels: two thin flanges and a crest.
    for side in (-1,1):
        for y in (-.41,.39):
            a=Vector((side*.517,y*.65,.67));b=Vector((side*.71,y,1.36))
            beam(a,b,.032,.051,'ochre',.003)
    part('04_Separate_sealed_lids_hinges_and_handles')
    for side in (-1,1):
        # Both lids closed in the abandoned-room state; the centre seam is real.
        x=side*.379
        box((x,-.025,1.512),(.737,1.535,.021),'ochre',.007)
        box((side*.008,-.025,1.501),(.012,1.49,.018),'rubber',.002)
        for yy in (-.515,.48):
            for dx in (-.045,.045):box((side*.747+dx,yy,1.519),(.074,.101,.006),'steel',.001)
            for i in range(5):lathe((side*.747,yy-.045+i*.019,1.533),(0,1,0),[(0,.009),(.017,.009)],'steel',20)
            for xx in (side*.697,side*.795):
                for dy in (-.033,.033):bolt((xx,yy+dy,1.524),(0,0,1),.38)
        for yy in (-.18,.02):box((side*.24,yy,1.530),(.039,.053,.012),'steel',.002)
        curved([(side*.24,-.18,1.536),(side*.24,-.169,1.572),(side*.24,-.14,1.583),(side*.24,-.02,1.583),(side*.24,.009,1.572),(side*.24,.02,1.536)],.009,'steel',16,5)
    part('05_Latch_safety_chain_drain_and_signage')
    # Rear spring catch restrains the pivoting bin. A small ring is the release.
    box((0,.663,.665),(.18,.07,.15),'steel',.004)
    plate([(-.028,.684,.63),(.028,.684,.63),(.028,.778,.73),(-.028,.778,.73)],.012,'steel',.002)
    rod((-.12,.722,.694),(.12,.722,.694),.009,'steel',20)
    torus((0,.797,.729),(1,0,0),.030,.004,'steel',32,8)
    for i in range(12):
        t=i/11;p=(.19+t*.20,.774+math.sin(t*math.pi)*.05,.706-math.sin(t*math.pi)*.085)
        torus(p,(0,1,0) if i%2 else (1,0,0),.008,.0021,'steel',20,8)
    for z in (.653,.678,.703,.728,.753):torus((.068,.746,z),(0,0,1),.011,.002,'steel',24,8)
    # Drain is attached to the lower rear wall; a square-headed plug remains shut.
    lathe((.34,.510,.670),front,[(0,.027),(.033,.027),(.040,.032),(.052,.032)],'steel',32)
    box((.34,.569,.670),(.031,.018,.031),'steel',.002)
    # Nameplate standoffs sit on the sloping face; the face normal follows the bin.
    n=Vector((0,.967,-.254));c=Vector((0,.651,1.174));u=Vector((-1,0,0));v=n.cross(u).normalized()
    corners=[c-u*.36-v*.105,c+u*.36-v*.105,c+u*.36+v*.105,c-u*.36+v*.105]
    plate(corners,.003,'steel',.0005);face([p+n*.002 for p in corners],'waste_plate')
    for sign in (-1,1):bolt(c+u*sign*.337+n*.004,n,.40)
    plaque((.755,-.005,1.43),.54,.06,'hazard',(1,0,0))
    # Rear push bar fits wholly inside the 2 m footprint.
    for x in (-.52,.52):
        curved([(x,.71,1.36),(x,.87,1.36),(x,.883,1.40)],.014,'steel',18,5)
    rod((-.52,.883,1.40),(.52,.883,1.40),.014,'steel',24)
    lathe((-.29,.883,1.40),(1,0,0),[(0,.020),(.58,.020)],'rubber',32)

def material():
    mat=bpy.data.materials.new(g.SLOT);mat.use_nodes=True
    nodes=mat.node_tree.nodes;nodes.clear();links=mat.node_tree.links
    out=nodes.new('ShaderNodeOutputMaterial');out.location=(520,50)
    bsdf=nodes.new('ShaderNodeBsdfPrincipled');bsdf.location=(260,50);links.new(bsdf.outputs['BSDF'],out.inputs['Surface'])
    maps={}
    for i,suffix in enumerate(('BaseColor','NormalGL','ORM')):
        im=bpy.data.images.load(str(ROOT/'Authored/Textures'/('T_IncineratorEquipment_'+suffix+'.png')))
        if suffix!='BaseColor':im.colorspace_settings.name='Non-Color'
        im.pack();node=nodes.new('ShaderNodeTexImage');node.image=im;node.location=(-650,-i*260);maps[suffix]=node
    links.new(maps['BaseColor'].outputs['Color'],bsdf.inputs['Base Color'])
    sep=nodes.new('ShaderNodeSeparateColor');sep.location=(-250,-480);links.new(maps['ORM'].outputs['Color'],sep.inputs['Color'])
    links.new(sep.outputs['Green'],bsdf.inputs['Roughness']);links.new(sep.outputs['Blue'],bsdf.inputs['Metallic'])
    norm=nodes.new('ShaderNodeNormalMap');norm.location=(-250,-210);links.new(maps['NormalGL'].outputs['Color'],norm.inputs['Color']);links.new(norm.outputs['Normal'],bsdf.inputs['Normal'])
    return mat

def build():
    global CURRENT
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC'
    mat=material();dest=ROOT/'Authored';records=[]
    specs=[('FurnaceDoorKit',door,[((0,-.035,1.65),(2.44,.32,2.90)),((-1.57,.19,1.85),(.53,.55,2.12)),((0,.25,1.86),(.62,.45,.63))]),
           ('ChargingTrolley',trolley,[((0,0,.53),(1.48,1.65,.59)),((0,.854,.81),(1.15,.085,.56))]),
           ('MedicalWasteHopper',hopper,[((0,0,.45),(1.40,1.66,.60)),((0,-.025,1.10),(1.64,1.60,.86)),((0,.865,1.385),(1.12,.09,.085))])]
    source_col=bpy.data.collections.new('EDITABLE_COMPONENTS');bpy.context.scene.collection.children.link(source_col)
    export_col=bpy.data.collections.new('GAME_EXPORTS');bpy.context.scene.collection.children.link(export_col)
    for index,(key,author,colliders) in enumerate(specs):
        g.V.clear();g.F.clear();g.UV.clear();g.SMOOTH.clear();PARTS.clear();CURRENT=None;author();CURRENT['last_vertex']=len(g.V)
        name='SM_Incinerator_'+key+'_V1';mesh=bpy.data.meshes.new(name);mesh.from_pydata(g.V,[],g.F);mesh.materials.append(mat);mesh.update()
        obj=bpy.data.objects.new(name,mesh);export_col.objects.link(obj)
        uv=mesh.uv_layers.new(name='UVMap')
        for p,coords,smooth in zip(mesh.polygons,g.UV,g.SMOOTH):
            p.use_smooth=smooth
            for li,coord in zip(p.loop_indices,coords):uv.data[li].uv=coord
        # Semantic vertex groups persist in source for independent mechanical editing.
        for p in PARTS:
            vg=obj.vertex_groups.new(name=p['name']);vg.add(list(range(p['first_vertex'],p['last_vertex'])),1,'REPLACE')
        source=obj.copy();source.data=obj.data.copy();source.name='EDIT_'+key;source_col.objects.link(source)
        source.location=(index*4,4,0);source.hide_render=True
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
        bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.000003);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
        weighted=obj.modifiers.new('Manufactured weighted normals','WEIGHTED_NORMAL');weighted.keep_sharp=True;weighted.weight=40;bpy.ops.object.modifier_apply(modifier=weighted.name)
        tri=obj.modifiers.new('Export triangulation','TRIANGULATE');tri.keep_custom_normals=True;bpy.ops.object.modifier_apply(modifier=tri.name)
        mesh=obj.data;uv=mesh.uv_layers.active.data
        # Cap/ring edge triangles receive a defined tangent basis as part of export.
        for p in mesh.polygons:
            ids=list(p.loop_indices);a,b,c=(uv[i].uv.copy() for i in ids)
            if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>1e-12:continue
            coords=[mesh.vertices[mesh.loops[i].vertex_index].co for i in ids];axis=max(range(3),key=lambda k:abs(p.normal[k]));dims=[k for k in range(3) if k!=axis];center=sum(coords,Vector())/3
            for li,v in zip(ids,coords):uv[li].uv=g.tex('steel',.5+(v[dims[0]]-center[dims[0]])*.2,.5-(v[dims[1]]-center[dims[1]])*.2)
        collisions=[]
        for i,(center,size) in enumerate(colliders):
            bpy.ops.mesh.primitive_cube_add(size=1,location=center);co=bpy.context.object;co.name=f'UCX_{name}_{i:02d}';co.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);collisions.append(co)
        bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
        for co in collisions:co.select_set(True)
        bpy.context.view_layer.objects.active=obj;fbx=dest/(name+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
        lo=[min(v.co[i] for v in mesh.vertices) for i in range(3)];hi=[max(v.co[i] for v in mesh.vertices) for i in range(3)]
        records.append({'key':key,'name':name,'fbx':str(fbx),'materials':{g.SLOT:g.MATERIAL},'triangles':len(mesh.polygons),'bounds_m':[lo,hi],'size_m':[hi[i]-lo[i] for i in range(3)],'collision_boxes':len(colliders),'parts':[p['name'] for p in PARTS]})
        obj.location=(index*4,0,0)
        for co in collisions:co.location+=obj.location;co.hide_viewport=True;co.hide_render=True
        print('INCINERATOR_EQUIPMENT_AUTHORED',key,len(mesh.polygons),flush=True)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.save_as_mainfile(filepath=str(dest/'IncineratorEquipment_PrecisionV1.blend'))
    (dest/'manifest.json').write_text(json.dumps({'revision':'precision_equipment_v1_20260930','objects':records,'units':'metres; FBX axis -Y/Z','state':'Static cold equipment','tests_run':False,'rendered':False},indent=2),encoding='utf-8')

if __name__=='__main__':build()
