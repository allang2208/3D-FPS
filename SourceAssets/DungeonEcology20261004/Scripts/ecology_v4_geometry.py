"""Local reuse, horticultural surfaces and pipe-fit collision for ecology V4."""
import math,json,numpy as np
from mathutils import Vector
H=None;PIPE_HULLS=[]
def setup(host):
    global H,HEIGHT,original_pipe
    H=host;HEIGHT=np.load(H['ROOT']/'Sources/StockV4/soil-height.npy')
    original_pipe=H['detail'].smooth_pipe;H['detail'].smooth_pipe=solid_pipe
    for key in ('SoilPot','SoilBed'):
        H['MAPPING'][key]=H['CFG'].get('soil_material_base',H['MESHBASE'])+'/Materials/M_Eco_'+key
        H['MATS'][key]=H['bpy'].data.materials.new('RS_'+key)
def reset():PIPE_HULLS.clear()
def height_sample(u,v):
    x=(u%1)*255;y=((1-v)%1)*255;ix=int(x);iy=int(y);fx=x-ix;fy=y-iy
    return float(HEIGHT[iy,ix]*(1-fx)*(1-fy)+HEIGHT[iy,(ix+1)%256]*fx*(1-fy)+HEIGHT[(iy+1)%256,ix]*(1-fx)*fy+HEIGHT[(iy+1)%256,(ix+1)%256]*fx*fy)
def medium(x,y,top,radius):
    N=32;R=6;phase=((x*17.37+y*4.3)%1,(y*19.71-x*3.5)%1)
    vs=[];uv=[]
    for j in range(R+1):
        radius_i=max(.00005,radius*j/R)
        for k in range(N):
            a=k*math.tau/N;dx=math.cos(a)*radius_i;dy=math.sin(a)*radius_i;u=dx/.18+phase[0];v=dy/.18+phase[1]
            z=top-.005*(j/R)**4+(height_sample(u,v)-.5)*.004
            vs.append((x+dx,y+dy,z));uv.append((u,v))
    fs=[tuple(reversed(range(N)))];fuv=[[uv[i] for i in fs[0]]]
    for j in range(R):
        for k in range(N):
            q=(j*N+k,j*N+(k+1)%N,(j+1)*N+(k+1)%N,(j+1)*N+k);fs.append(q);fuv.append([uv[i] for i in q])
    # Faces above run clockwise in the radial direction; flip them to face the room.
    fs=[tuple(reversed(f)) for f in fs];fuv=[list(reversed(u)) for u in fuv]
    H['poly']('PotSoil',vs,fs,'SoilPot',fuv,True)
def bed_height(x,y):
    t=min(1,((x-3)/8.8)**2+(y/7.2)**2)
    return .022+(1-t)**1.3*.108+(math.sin(x*.73+y*.45)*.017+math.cos(y*1.1-x*.38)*.012)*(1-t)+(height_sample(x/.85,y/.85)-.5)*.018*(1-t)
def biosphere_bed(r):
    N=144;R=60;vs=[];uv=[]
    for j in range(R+1):
        t=max(.00001,j/R)
        for k in range(N):
            a=k*math.tau/N;x=3+8.8*t*math.cos(a);y=7.2*t*math.sin(a)
            vs.append((x,y,bed_height(x,y)));uv.append((x/.85,y/.85))
    fs=[];fuv=[]
    for j in range(R):
        for k in range(N):
            q=(j*N+k,(j+1)*N+k,(j+1)*N+(k+1)%N,j*N+(k+1)%N);fs.append(q);fuv.append([uv[i] for i in q])
    H['poly']('SoilBed',vs,fs,'SoilBed',fuv,True)
    for k in range(72):
        a=k*math.tau/72;bb=(k+1)*math.tau/72
        p=(3+8.83*math.cos(a),7.23*math.sin(a),.065);q=(3+8.83*math.cos(bb),7.23*math.sin(bb),.065)
        H['beam']('SoilEdging',p,q,.085,.13,'Concrete')
    # Subtle drip irrigation follows the inset edge; no roots or grass across the walkway.
    for rx,ry in ((7.7,6.2),(4.9,3.9)):
        ps=[]
        for k in range(97):
            a=k*math.tau/96;x=3+rx*math.cos(a);y=ry*math.sin(a);ps.append((x,y,bed_height(x,y)+.014))
        H['detail'].tube('Services',ps,.009,'Rubber',12)
    for p in r['plants']:
        if p.get('soil_surface'):p['position'][2]=bed_height(*p['position'][:2])
    r['hero_tree']['position'][2]=bed_height(3,0)
def office_sockets():
    src=json.loads((H['ROOT']/'Sources/StockV4/socket-source.json').read_text('utf8'))
    for i,path in enumerate(src['materials']):
        key='StockSocket'+str(i);H['MAPPING'][key]=path;H['MATS'][key]=H['bpy'].data.materials.new('RS_'+key)
    for cx in (-10.0,-8.6):
        vs=[(cx+(y-2.65),9.85-(x-.1755),1.45+z-1.31) for x,y,z in src['vertices']]
        for face,mi,uv in zip(src['faces'],src['face_materials'],src['uvs']):
            H['poly']('OfficeSockets',[vs[i] for i in face],[tuple(range(len(face)))],'StockSocket'+str(mi),[uv] if uv else None)
        # Gland centre is part of the reused mesh; conduit meets it exactly.
        H['detail'].tube('OfficeElectrical',[(cx-.03,9.8355,1.531),(cx-.03,9.8355,2.45)],.010,'PipeEnamel',20)
        for z in (1.70,2.22):
            H['box']('OfficeElectrical',(cx-.03,9.846,z),(.040,.021,.028),'BareSteel')
    H['detail'].tube('OfficeElectrical',[(-10.03,9.8355,2.45),(-8.63,9.8355,2.45)],.010,'PipeEnamel',20)
def convex_segment(a,b,r):
    a,b=Vector(a),Vector(b);n=(b-a).normalized();u=n.cross(Vector((0,0,1)) if abs(n.z)<.9 else Vector((0,1,0))).normalized();v=n.cross(u)
    # Circumscribed twelve-sided section follows the cylinder without a room-wide hull.
    radius=r/math.cos(math.pi/12);sides=12
    vs=[tuple(p+(u*math.cos(k*math.tau/sides)+v*math.sin(k*math.tau/sides))*radius) for p in (a-n*.002,b+n*.002) for k in range(sides)]
    fs=[tuple(reversed(range(sides))),tuple(range(sides,2*sides))]+[(k,(k+1)%sides,(k+1)%sides+sides,k+sides) for k in range(sides)]
    PIPE_HULLS.append(dict(vertices=vs,faces=fs))
def solid_pipe(points,radius):
    services=H['G'].get('Services');nv=len(services['v']) if services else 0;nf=len(services['f']) if services else 0
    original_pipe(points,radius)
    if radius<.04:return
    source=H['G']['Services'];target=H['group']('CoarsePipes');offset=len(target['v'])
    target['v'].extend(source['v'][nv:]);target['f'].extend(tuple(i-nv+offset for i in f) for f in source['f'][nf:])
    for key in ('m','uv','smooth'):target[key].extend(source[key][nf:]);del source[key][nf:]
    del source['v'][nv:];del source['f'][nf:]
    ps=[Vector(p) for p in points];path=[ps[0]]
    for i in range(1,len(ps)-1):
        p=ps[i];before=(p-ps[i-1]).normalized();after=(ps[i+1]-p).normalized();reach=min(max(radius*2.2,.26),(p-ps[i-1]).length*.34,(ps[i+1]-p).length*.34);center=p-before*reach+after*reach
        for j in range(7):
            theta=j/6*math.pi/2;path.append(center-after*reach*math.cos(theta)+before*reach*math.sin(theta))
    path.append(ps[-1])
    for a,b in zip(path,path[1:]):
        if (b-a).length>.0001:convex_segment(a,b,radius+.003)
    for a,b in zip(ps,ps[1:]):
        d=b-a;length=d.length;n=d.normalized()
        if length<.75:continue
        count=max(1,int(length/2.6))
        for i in range(count):
            p=a+d*((i+.5)/count);convex_segment(p-n*.052,p+n*.052,radius*1.35+.012)
