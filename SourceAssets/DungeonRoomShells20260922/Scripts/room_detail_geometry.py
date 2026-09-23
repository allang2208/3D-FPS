"""Local architectural detailing. Metres; preserve approved footprints and service routes."""
import math,random,zlib
import bmesh
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

H=None
def setup(host):
    global H
    H=host

def poly(kind,vs,fs,mat,uv=None,smooth=False):H['poly'](kind,vs,fs,mat,uv,smooth)
def box(*args,**kwargs):H['box'](*args,**kwargs)

def frames(points):
    ps=[Vector(p) for p in points];result=[];last=None
    for i,p in enumerate(ps):
        t=(ps[min(i+1,len(ps)-1)]-ps[max(0,i-1)]).normalized()
        if last is None:
            helper=Vector((0,0,1)) if abs(t.z)<.9 else Vector((0,1,0))
            a=t.cross(helper).normalized()
        else:a=(last-t*last.dot(t)).normalized()
        b=t.cross(a).normalized();result.append((p,t,a,b));last=a
    return result

def sweep(kind,points,radius,mat='ServicePaint',sides=32,thickness=None,inner_mat=None):
    rings=frames(points);vs=[];fs=[];uv=[];sm=[];distance=[0]
    for i in range(1,len(rings)):distance.append(distance[-1]+(rings[i][0]-rings[i-1][0]).length)
    radii=[radius]+([radius-thickness] if thickness else [])
    for r in radii:
        for p,t,a,b in rings:
            vs.extend(tuple(p+r*(a*math.cos(j*math.tau/sides)+b*math.sin(j*math.tau/sides))) for j in range(sides))
    total=len(rings)*sides
    for layer,r in enumerate(radii):
        for i in range(len(rings)-1):
            for j in range(sides):
                ids=[layer*total+i*sides+j,layer*total+i*sides+(j+1)%sides,layer*total+(i+1)*sides+(j+1)%sides,layer*total+(i+1)*sides+j]
                # Cross(circumference tangent, longitudinal tangent) points outward.
                uvs=[(j/sides*math.tau*r/.8,distance[i]/.8),((j+1)/sides*math.tau*r/.8,distance[i]/.8),((j+1)/sides*math.tau*r/.8,distance[i+1]/.8),(j/sides*math.tau*r/.8,distance[i+1]/.8)]
                if layer:ids.reverse();uvs.reverse()
                fs.append(ids);uv.append(uvs);sm.append(True)
    for end in (0,len(rings)-1):
        p,t,a,b=rings[end]
        if thickness:
            for j in range(sides):
                ids=[end*sides+j,total+end*sides+j,total+end*sides+(j+1)%sides,end*sides+(j+1)%sides]
                if end!=0:ids.reverse()
                fs.append(ids);uv.append([(Vector(vs[k]).dot(a)/.8,Vector(vs[k]).dot(b)/.8) for k in ids]);sm.append(False)
        else:
            ids=[end*sides+j for j in range(sides)]
            if end==0:ids.reverse()
            fs.append(ids);uv.append([(Vector(vs[k]).dot(a)/.8,Vector(vs[k]).dot(b)/.8) for k in ids]);sm.append(False)
    if inner_mat and thickness:
        side_count=(len(rings)-1)*sides
        poly(kind,vs,fs[:side_count],mat,uv[:side_count],sm[:side_count])
        poly(kind,vs,fs[side_count:2*side_count],inner_mat,uv[side_count:2*side_count],sm[side_count:2*side_count])
        poly(kind,vs,fs[2*side_count:],'PipeCutSteel',uv[2*side_count:],sm[2*side_count:])
    else:poly(kind,vs,fs,mat,uv,sm)

def tube(kind,points,radius,mat='ServicePaint',sides=24):
    sweep(kind,points,radius,mat,max(12,sides))

def ring(center,axis,outer,inner,length,mat='ServiceHardware',sides=40,kind='Services'):
    c,n=Vector(center),Vector(axis).normalized()
    sweep(kind,[c-n*length/2,c+n*length/2],outer,mat,sides,outer-inner)

def torus(center,axis,major,minor,kind='Services',mat='ServiceHardware',segments=36):
    c,n=Vector(center),Vector(axis).normalized();a=n.cross(Vector((0,0,1)) if abs(n.z)<.9 else Vector((0,1,0))).normalized();b=n.cross(a)
    vs=[];fs=[]
    for i in range(segments):
        radial=a*math.cos(i*math.tau/segments)+b*math.sin(i*math.tau/segments)
        for j in range(8):vs.append(tuple(c+radial*(major+minor*math.cos(j*math.tau/8))+n*minor*math.sin(j*math.tau/8)))
    for i in range(segments):
        for j in range(8):fs.append((i*8+j,((i+1)%segments)*8+j,((i+1)%segments)*8+(j+1)%8,i*8+(j+1)%8))
    poly(kind,vs,fs,mat,smooth=True)

def fastener(p,axis,r=.012,kind='Services'):
    p,n=Vector(p),Vector(axis).normalized()
    ring(p,n,r*1.45,r*.43,.0035,sides=20,kind=kind)
    # Hexagonal nut, actual opening over the shank; crisp machined flats.
    ring(p+n*.008,n,r,r*.46,.013,sides=6,kind=kind)
    tube(kind,[p-n*.008,p+n*.02],r*.43,'ServiceHardware',12)

def flange(p,n,r):
    p,n=Vector(p),Vector(n).normalized();basis=frames([p,p+n])[0];a,b=basis[2:]
    outer=r*1.35+.012
    # Paired flanges and a recessed dark gasket, all annular rather than solid disks.
    for s in (-1,1):
        ring(p+n*s*.024,n,outer,r-.003,.028)
        torus(p+n*s*.038,n,outer-.003,.0026)
        torus(p+n*s*.050,n,r+.002,.003,'Services','BareSteel')
    ring(p,n,outer-.010,r-.005,.015,'PaintedSteel')
    for j in range(8):
        radial=a*math.cos((j+.5)*math.tau/8)+b*math.sin((j+.5)*math.tau/8)
        c=p+radial*(r+(outer-r)*.61)
        tube('Services',[c-n*.052,c+n*.052],.006,'ServiceHardware',12)
        fastener(c+n*.043,n,.010);fastener(c-n*.043,-n,.010)

def ceiling_at(p):
    height=H['ROOM']['height_m']
    for x0,y0,x1,y1,z in H['ROOM'].get('ceilings',[]):
        if x0<=p.x<=x1 and y0<=p.y<=y1:height=min(height,z)
    for a,b in H['ROOM'].get('beams',[]):
        a,b=Vector(a),Vector(b);d=b-a;k=max(0,min(1,(p-a).dot(d)/d.length_squared));q=a+d*k
        if (p.xy-q.xy).length<.24:height=min(height,q.z-.18)
    return height

def smooth_pipe(points,radius):
    ps=[Vector(p) for p in points];path=[ps[0]]
    for i in range(1,len(ps)-1):
        p=ps[i];before=(p-ps[i-1]).normalized();after=(ps[i+1]-p).normalized()
        reach=min(max(radius*2.2,.26),(p-ps[i-1]).length*.34,(ps[i+1]-p).length*.34)
        first=p-before*reach;last=p+after*reach
        # Circular quarter bend maintains wall thickness, with 18 arc intervals.
        center=p-before*reach+after*reach
        for j in range(19):
            theta=j/18*math.pi/2;path.append(center-after*reach*math.cos(theta)+before*reach*math.sin(theta))
    path.append(ps[-1]);dense=[path[0]]
    for a,b in zip(path,path[1:]):
        n=max(1,math.ceil((b-a).length/.18))
        dense.extend(a+(b-a)*j/n for j in range(1,n+1))
    sweep('Services',dense,radius,'PipeEnamel',48,thickness=max(.009,radius*.058),inner_mat='PipeInner')
    # A rolled cut lip and internal wall are visible at every exposed end.
    for p,n in [(ps[0],(ps[1]-ps[0]).normalized()),(ps[-1],(ps[-1]-ps[-2]).normalized())]:
        torus(p,n,radius-.003,.004,mat='PipeCutSteel',segments=48)
    for a,b in zip(ps,ps[1:]):
        d=b-a;length=d.length;n=d.normalized()
        if length<.75:continue
        count=max(1,int(length/2.6))
        for i in range(count):
            p=a+d*((i+.5)/count)
            flange(p,n,radius)
            if abs(d.z)<.01 and p.z>2.5:
                # Saddle wraps the pipe. Two hanger rods terminate at actual soffit/beam.
                c=p+n*.28;ring(c,n,radius+.013,radius+.002,.035,'BareSteel',32,'Frames')
                side=Vector((-n.y,n.x,0));top=ceiling_at(c)
                for sign in (-1,1):
                    foot=c+side*sign*(radius+.04)
                    box('Frames',(foot.x,foot.y,foot.z),(.045,.045,.026),'ServiceHardware')
                    if top>foot.z+.07:
                        tube('Frames',[foot,Vector((foot.x,foot.y,top-.015))],.008,'ServiceHardware',12)
                        box('Frames',(foot.x,foot.y,top-.012),(.085,.085,.024),'BareSteel')

def grate(x0,x1,y):
    # Three lift-out cassettes seated on ledges; main slots remain open to the trench.
    width=x1-x0;count=max(1,round(width));span=width/count
    for yy in (y-.255,y+.255):
        box('Frames',((x0+x1)/2,yy,-.038),(width+.09,.065,.045),'ServiceHardware')
    for module in range(count):
        a=x0+module*span+.008;b=x0+(module+1)*span-.008
        for xx in (a+.016,b-.016):box('Frames',(xx,y,-.002),(.032,.5,.054),'ServiceHardware')
        for yy in (y-.234,y+.234):box('Frames',((a+b)/2,yy,-.002),(b-a,.032,.054),'ServiceHardware')
        usable=b-a-.075;n=max(4,int(usable/.04))
        for j in range(n+1):
            x=a+.0375+usable*j/n
            box('Frames',(x,y,-.007),(.008,.44,.040),'BareSteel')
        for yy in (y-.11,y+.11):box('Frames',((a+b)/2,yy,-.021),(b-a-.035,.007,.012),'ServiceHardware')
        for xx in (a+.025,b-.025):
            for yy in (y-.21,y+.21):fastener((xx,yy,.026),(0,0,1),.009,'Frames')

def chunk(center,size,r,mat='Concrete',kind='Debris'):
    # Convex, angular stones with unequal cuts, no rotated-box rubble.
    bm=bmesh.new()
    for j in range(12):
        a=j*2.399963;rxy=r.uniform(.65,1)
        bm.verts.new((math.cos(a)*size[0]*.5*rxy,math.sin(a)*size[1]*.5*rxy,r.uniform(-.5,.5)*size[2]))
    bm.verts.ensure_lookup_table();bmesh.ops.convex_hull(bm,input=list(bm.verts),use_existing_faces=False)
    bm.verts.index_update();verts=[tuple(Vector(center)+v.co) for v in bm.verts]
    fs=[tuple(v.index for v in f.verts) for f in bm.faces]
    bm.free();poly(kind,verts,fs,mat)

def breach_wall(start,direction,normal,length,height,breach,mat):
    r=random.Random(923728);left,right,h=breach['left'],breach['right'],breach['height']
    d=H['CFG']['style']['wall_thickness'];origin=Vector((start.x,start.y,0));along=Vector((direction.x,direction.y,0));inward=Vector((normal.x,normal.y,0))
    def noise(t,phase):return .041*math.sin(t*13.7+phase)+.017*math.sin(t*38.9-phase)+.009*math.sin(t*83.1+phase*2)
    def side(z,rightside=False):
        phase=2.9 if rightside else .4;sign=-1 if rightside else 1
        return (right if rightside else left)+sign*(.065*math.sin(z*4.3+phase)+.10*math.sin(z*1.8+phase)+noise(z,phase))
    samples=48;zs=[h*i/samples for i in range(samples+1)]
    leftedge=[(side(z),z) for z in zs];rightedge=[(side(z,True),z) for z in zs]
    lx,rx=leftedge[-1][0],rightedge[-1][0]
    roof=[(lx+(rx-lx)*i/56,h+(math.sin(i/56*math.pi))*(.065*math.sin(i*.32)+.06)+noise(i/56*3.6,1.7)*math.sin(i/56*math.pi)) for i in range(57)]
    # Every region has identical boundary topology through depth. Interior rings chip back
    # unevenly, so the cut is a volume with changing front/back silhouettes.
    regions=[([(0,0)]+leftedge+[(lx,height),(0,height)],set(range(1,len(leftedge)+1))),
             (rightedge+[(length,h),(length,0)],set(range(len(rightedge)))),
             (roof+[(rx,height),(lx,height)],set(range(len(roof))))]
    for region_index,(region,edgeids) in enumerate(regions):
        area=sum(region[i][0]*region[(i+1)%len(region)][1]-region[(i+1)%len(region)][0]*region[i][1] for i in range(len(region)))
        if area<0:
            n=len(region);region.reverse();edgeids={n-1-i for i in edgeids}
        rings=[]
        for layer,depth in enumerate([-d/2,-d*.22,d*.26,d/2]):
            coords=[]
            for i,(t,z) in enumerate(region):
                # Endpoints stay welded between the two jambs and lintel.
                amount=math.sin(math.pi*max(0,min(1,(t-lx)/(rx-lx) if region_index==2 else z/h))) if i in edgeids else 0
                dt=(noise(z+t,layer*.87)*(.4 if layer in (0,3) else 1.2))*amount
                coords.append((t+dt,z,depth))
            rings.append(coords)
        vs=[tuple(origin+along*t+inward*depth+Vector((0,0,z))) for ring_ in rings for t,z,depth in ring_]
        n=len(region)
        for layer,reverse in [(0,False),(3,True)]:
            cap=[Vector((t,z,0)) for t,z,depth in rings[layer]]
            tris=tessellate_polygon([cap])
            faces=[tuple(layer*n+i for i in (list(reversed(tri)) if reverse else tri)) for tri in tris]
            poly('Shell',vs,faces,mat)
        for layer in range(3):
            for i in range(n):
                j=(i+1)%n;ids=(layer*n+i,(layer+1)*n+i,(layer+1)*n+j,layer*n+j)
                exposed=i in edgeids and j in edgeids
                uv=[((rings[k//n][k%n][0]+rings[k//n][k%n][1])/.64,rings[k//n][k%n][2]/.64) for k in ids]
                poly('Shell',[vs[k] for k in ids],[(0,1,2,3)],'FractureConcrete' if exposed else mat,[uv])
    # Separate the right upper wall from the fractured lintel, sharing its x boundary.
    H['prism']('Shell',[(rx,h),(length,h),(length,height),(rx,height)],start,direction,normal,d,mat)
    for rightside in (False,True):
        sign=-1 if rightside else 1
        for i,z in enumerate(([.38,.93,1.52,2.22] if rightside else [.64,1.28,2.04])):
            t=side(z,rightside);base=origin+along*(t-sign*.07)+inward*r.uniform(-.045,.055)+Vector((0,0,z))
            length_=r.uniform(.24,.58);bend=r.uniform(-.12,.17);depthbend=r.uniform(.055,.23)
            tip=base+along*sign*length_+inward*depthbend+Vector((0,0,bend))
            control=base+along*sign*length_*.62+inward*(depthbend*.15)+Vector((0,0,r.uniform(-.035,.05)))
            ps=[base*(1-t_)**2+control*2*(1-t_)*t_+tip*t_*t_ for t_ in [j/14 for j in range(15)]]
            rebar(ps,r.uniform(.007,.0105),r)
        # Embedded aggregate has contact with the cut instead of floating beside it.
        for i in range(22):
            z=r.uniform(.1,h-.12);t=side(z,rightside)-sign*.012
            center=origin+along*t+inward*r.uniform(-d*.36,d*.36)+Vector((0,0,z))
            chunk(center,(r.uniform(.025,.065),r.uniform(.025,.055),r.uniform(.03,.085)),r,'FractureConcrete','Shell')
    for fraction in (.28,.73):
        t=lx+(rx-lx)*fraction;p=origin+along*t+Vector((0,0,h+.10))+inward*.01
        ps=[p+Vector((0,0,-.46*j/18))+along*(.15*(j/18)**2)+inward*(.12*(j/18)**2) for j in range(19)]
        rebar(ps,.0085,r)

def rebar(points,radius,r):
    sweep('Services',points,radius,'ServicePaint',16)
    fr=frames(points);total=sum((fr[i][0]-fr[i-1][0]).length for i in range(1,len(fr)))
    turns=max(3,int(total/.022));helix=[]
    for i in range(turns*10+1):
        q=i/(turns*10)*(len(fr)-1);k=min(len(fr)-2,int(q));f=q-k
        p=fr[k][0].lerp(fr[k+1][0],f);a=fr[k][2].lerp(fr[k+1][2],f).normalized();b=fr[k][3].lerp(fr[k+1][3],f).normalized()
        ang=i/10*math.tau;helix.append(p+(a*math.cos(ang)+b*math.sin(ang))*radius)
    sweep('Services',helix,.00115,'ServiceHardware',8)

def rubble():
    r=random.Random(923583)
    x0,y0,x1,y1=H['ROOM']['breach']['pocket']
    for cx,cy in [(x0-.52,y0+.2),(x0+.6,y1-.37),(x1-.45,y0+.5)]:
        for i in range(22):
            x=cx+r.uniform(-.4,.4);y=cy+r.uniform(-.28,.28);h=r.uniform(.035,.14)
            chunk((x,y,h*.46),(r.uniform(.045,.27),r.uniform(.04,.21),h),r,'FractureConcrete')
        for i in range(11):
            x=cx+r.uniform(-.5,.5);y=cy+r.uniform(-.35,.35)
            ceramic_shard((x,y,.004),r)

def ceramic_shard(center,r):
    """Thick broken tile with a glazed face and exposed ceramic, matching the wall material."""
    n=r.randrange(5,8);sx=r.uniform(.055,.14);sy=r.uniform(.035,.08);yaw=r.uniform(0,math.tau)
    shape=[]
    for i in range(n):
        a=i*math.tau/n;rad=r.uniform(.73,1)
        dx=math.cos(a)*sx*rad;dy=math.sin(a)*sy*rad
        shape.append((dx*math.cos(yaw)-dy*math.sin(yaw),dx*math.sin(yaw)+dy*math.cos(yaw)))
    thickness=r.uniform(.0065,.010);tilt=r.uniform(-.018,.018)
    vs=[(center[0]+x,center[1]+y,center[2]+layer*thickness+x*tilt) for layer in (0,1) for x,y in shape]
    poly('Debris',vs,[tuple(reversed(range(n)))],'V2_CeramicFractureCore')
    for i in range(n):
        j=(i+1)%n;poly('Debris',[vs[k] for k in (i,j,j+n,i+n)],[(0,1,2,3)],'V2_CeramicFractureCore')
    cell=r.randrange(32,64)
    xs=[x for x,y in shape];ys=[y for x,y in shape]
    uv=[((cell%8+.045+.91*(x-min(xs))/(max(xs)-min(xs)))/8,(cell//8+.045+.91*(y-min(ys))/(max(ys)-min(ys)))/8) for x,y in shape]
    poly('Debris',vs,[tuple(n+i for i in range(n))],'V2_TileGlazeAtlas',[uv])
