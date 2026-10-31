"""Near-view structural details; physical UVs and closed smooth solids."""
_roundbox=roundbox
def text(k,string,c,size=.035,m='Paper',rotation=(90,0,0)):
    curve=bpy.data.curves.new('V3 printed relief','FONT');curve.body=string;curve.size=size
    curve.extrude=.00018;curve.bevel_depth=.00006;curve.resolution_u=6
    ob=bpy.data.objects.new('Printed type',curve);bpy.context.collection.objects.link(ob);ob.location=c;ob.rotation_euler=tuple(math.radians(v) for v in rotation)
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob;bpy.ops.object.convert(target='MESH')
    bm=bmesh.new();bm.from_mesh(ob.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-7);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(ob.data);bm.free()
    g.poly(k,[ob.matrix_world@v.co for v in ob.data.vertices],[tuple(p.vertices) for p in ob.data.polygons],m)
    bpy.data.objects.remove(ob,do_unlink=True)
def roundbox(k,c,s,m='Graphite',r=.008,seg=4,col=False):
    _roundbox(k,c,s,m,r,max(seg,8),col)
_lathe=g.lathe;_torus=g.torus;_tube=g.tube
def dense_lathe(kind,c,axis,profile,mat='EdgeSteel',segments=40,collision=False):
    segments=max(segments,96);start=len(g.group(kind)['f'])
    _lathe(kind,c,axis,profile,mat,segments,collision)
    distance=[0.]
    for a,b in zip(profile,profile[1:]):distance.append(distance[-1]+math.hypot(b[0]-a[0],b[1]-a[1]))
    data=g.group(kind)
    for j in range(len(profile)-1):
        rr=(profile[j][1]+profile[j+1][1])/2
        for i in range(segments):data['uv'][start+j*segments+i]=[(i/segments*math.tau*rr,distance[j]),((i+1)/segments*math.tau*rr,distance[j]),((i+1)/segments*math.tau*rr,distance[j+1]),(i/segments*math.tau*rr,distance[j+1])]
def dense_torus(kind,c,axis,major,minor,mat='EdgeSteel',segments=40,sides=8):
    segments=max(segments,96);sides=max(sides,16);start=len(g.group(kind)['f'])
    _torus(kind,c,axis,major,minor,mat,segments,sides)
    for i in range(segments):
        for j in range(sides):g.group(kind)['uv'][start+i*sides+j]=[(i*math.tau*major/segments,j*math.tau*minor/sides),((i+1)*math.tau*major/segments,j*math.tau*minor/sides),((i+1)*math.tau*major/segments,(j+1)*math.tau*minor/sides),(i*math.tau*major/segments,(j+1)*math.tau*minor/sides)]
def dense_tube(kind,points,r,mat='Rubber',sides=12):
    _tube(kind,points,r,mat,max(sides,24 if r>.003 else 12))
g.lathe=dense_lathe;g.torus=dense_torus;g.tube=dense_tube
def ring(k,c,axis,ro,ri,depth,m='EdgeSteel'):g.ring(k,c,axis,ro,ri,depth,m,96)
def screw(k,c,axis=(0,0,1),r=.003,mat='EdgeSteel'):
    p=Vector(c);n,a,b=g.basis(axis)
    g.lathe(k,p,n,[(0,r*.88),(.0006,r),(.0015,r),(.0018,r*.85)],mat,40)
    # Recess insert is a physical dark cross on the screw face.
    for direction in (a,b):g.beam(k,p+n*.00185-direction*r*.52,p+n*.00185+direction*r*.52,r*.22,.00012,'Ink')

def book(k,c,w=.17,d=.23,h=.026,title='FIELD NOTES',mat='BookNavy',yaw=0):
    x,y,z=c;cover={'CharcoalWeave':'BookNavy','Graphite':'BookNavy','OchreCloth':'BookOchre'}.get(mat,mat)
    start=len(g.group(k)['v'])
    # Five signatures give the page block separate paper edges and a rounded fore-edge.
    hh=(h-.006)/5
    for j in range(5):
        zz=z+.003+hh*(j+.5)
        roundbox(k,(x+.001,y,zz),(w-.009,d-.010,hh-.00022),'PageEdges',.0012,5)
    for zz in (z+.0015,z+h-.0015):roundbox(k,(x,y,zz),(w,d,.003),cover,.0013,5)
    # Continuous rounded spine, shoulders and headbands.
    roundbox(k,(x-w/2+.002,y,z+h/2),(.006,d,h),cover,.0025,6)
    for yy in (y-d/2+.006,y+d/2-.006):
        pipe(k,[(x-w/2+.004,yy,z+.005),(x-w/2+.004,yy,z+h-.005)],.0014,'FogLinen',12)
    for zz in (z+.004,z+h-.004):pipe(k,[(x-w/2+.007,y-d/2+.004,zz),(x-w/2+.007,y+d/2-.004,zz)],.00055,cover,10)
    text(k,title,(x-w*.37,y-.008,z+h+.00015),min(.012,w/max(14,len(title)*.8)),'Paper',(0,0,0))
    text(k,'STUDIO / 2077',(x-w*.37,y-d*.31,z+h+.00015),.0055,'Paper',(0,0,0))
    # Inset cover frame follows the board, with useful relief at close view.
    pipe(k,loop(x,y,z+h+.00025,w-.022,d-.026,.006),.00035,'Copper',10)
    if yaw:
        co,si=math.cos(yaw),math.sin(yaw);vs=g.group(k)['v']
        for i in range(start,len(vs)):
            xx,yy,zz=vs[i];vs[i]=(x+(xx-x)*co-(yy-y)*si,y+(xx-x)*si+(yy-y)*co,zz)

def leaf(k,base,end,width,roll,seed):
    a=Vector(base);b=Vector(end);axis=(b-a).normalized();side=axis.cross(Vector((0,0,1))).normalized()
    if side.length<.1:side=Vector((1,0,0))
    normal=side.cross(axis).normalized();side=(side*math.cos(roll)+normal*math.sin(roll)).normalized();normal=side.cross(axis).normalized()
    nx=16;ny=32;vs=[];fs=[];uv=[]
    for layer in (1,-1):
        for j in range(ny+1):
            t=j/ny;radius=width*.5*max(.008,math.sin(math.pi*t)**.78)*(1-.18*t)
            centre=a+(b-a)*t+normal*(.013*math.sin(math.pi*t)-.016*t*t)
            for i in range(nx+1):
                q=-1+2*i/nx
                ridge=.006*(1-abs(q)**.7)*math.sin(math.pi*t)
                wave=.0015*math.sin(t*20+seed)*q*q*math.sin(math.pi*t)
                vs.append(centre+side*q*radius+normal*(ridge+wave+layer*.00028))
    n=(nx+1)*(ny+1)
    for layer in (0,1):
        for j in range(ny):
            for i in range(nx):
                a0=layer*n+j*(nx+1)+i;f=(a0,a0+1,a0+nx+2,a0+nx+1)
                coords=[(i/nx,j/ny),((i+1)/nx,j/ny),((i+1)/nx,(j+1)/ny),(i/nx,(j+1)/ny)]
                fs.append(f if layer==0 else tuple(reversed(f)));uv.append(coords if layer==0 else list(reversed(coords)))
    edge=list(range(nx+1))+[j*(nx+1)+nx for j in range(1,ny+1)]+[ny*(nx+1)+i for i in range(nx-1,-1,-1)]+[j*(nx+1) for j in range(ny-1,0,-1)]
    for a0,b0 in zip(edge,edge[1:]+edge[:1]):fs.append((a0,a0+n,b0+n,b0));uv.append([(0,0),(0,.001),(.01,.001),(.01,0)])
    g.poly(k,vs,fs,'Leaf',uv=uv,smooth=True)

def plant(k,c):
    x,y,z=c
    # Closed glazed pot, foot ring, thick rolled lip, inner wall and inset soil.
    profile=[(0,.075),(.003,.084),(.010,.088),(.017,.089),(.045,.095),(.12,.112),(.163,.119),(.175,.120),(.181,.117),(.182,.113),(.179,.107),(.171,.106),(.055,.082),(.021,.075),(.021,.004)]
    g.lathe(k,c,(0,0,1),profile,'Ceramic',128)
    g.torus(k,(x,y,z+.178),(0,0,1),.113,.0035,'Ceramic',128,20)
    g.cylinder(k,(x,y,z+.155),(x,y,z+.160),.102,'Soil',96)
    import random
    rnd=random.Random(24)
    for i in range(26):
        t=rnd.random()*math.tau;r=.094*math.sqrt(rnd.random());xx=x+math.cos(t)*r;yy=y+math.sin(t)*r
        g.lathe(k,(xx,yy,z+.158),(0,0,1),[(0,.002),(.002,.0038),(.004,.002)],'Soil',16)
    for stem in range(6):
        angle=stem*2.399;length=.23+(.045 if stem%2 else 0)
        points=[]
        for j in range(17):
            t=j/16;points.append((x+math.cos(angle)*.055*t*t,y+math.sin(angle)*.045*t*t,z+.16+length*t))
        pipe(k,points,.0021,'Stem',20)
        for j in range(3):
            t=.32+j*.23;p=Vector(points[round(t*16)])
            for sign in (-1,1):
                a=angle+sign*1.2;end=p+Vector((math.cos(a)*(.075-j*.009),math.sin(a)*(.063-j*.007),.028-j*.003))
                tip=p+(end-p)*.13
                pipe(k,[p,tip],.0009,'Stem',12)
                leaf(k,tip,end,.037-j*.003,sign*.14,stem*3+j)

def bed_lamps(k):
    for side in (-1,1):
        x=side*.88
        # Mount against the retained headboard face and use a smooth continuous bend.
        g.lathe(k,(x,1.123,1.328),(0,-1,0),[(0,.029),(.006,.029),(.009,.025)],'Graphite',96)
        pts=[]
        a=Vector((x,1.112,1.328));b=Vector((x,.95,1.36));c=Vector((x,.94,1.27))
        for j in range(33):
            t=j/32;pts.append((1-t)**2*a+2*(1-t)*t*b+t*t*c)
        pipe(k,pts,.0105,'Copper',40)
        profile=[(0,.019),(.002,.023),(.008,.028),(.048,.057),(.055,.058),(.057,.056),(.057,.050),(.052,.050),(.010,.021),(.004,.016)]
        g.lathe(k,(x,.94,1.27),(0,0,-1),profile,'Graphite',128)
        # Opaque lens is recessed inside a closed shell; it cannot reveal internals.
        g.cylinder(k,(x,.94,1.218),(x,.94,1.216),.0495,'WarmDiffuser',128)
        g.ring(k,(x,.94,1.216),(0,0,1),.051,.049,.003,'Rubber',128)
        for a in (0,math.pi):screw(k,(x+.053*math.cos(a),.94+.053*math.sin(a),1.214),(0,0,-1),.0022)

def closed_wall_housing(k):
    profiles=[(.035,.234,.174,.009),(.034,.246,.186,.013),(.030,.25,.19,.016),(-.025,.25,.19,.016),(-.0315,.242,.182,.012),(-.0315,.228,.166,.008),(-.028,.224,.162,.006),(.018,.224,.162,.006),(.019,.220,.158,.006)]
    vs=[];fs=[];uv=[];sm=[];distance=[0.]
    for j,(z,w,d,r) in enumerate(profiles):
        ringpoints=loop(0,-.16,z,w,d,r)[:-1];vs.extend(ringpoints)
        if j:
            p=profiles[j-1];distance.append(distance[-1]+math.sqrt((z-p[0])**2+((w-p[1])/2)**2+((d-p[2])/2)**2))
    n=len(vs)//len(profiles);lengths=[0.]
    for i in range(n):lengths.append(lengths[-1]+(Vector(vs[(i+1)%n])-Vector(vs[i])).length)
    for j in range(len(profiles)-1):
        for i in range(n):
            a=j*n+i;b=j*n+(i+1)%n;c=(j+1)*n+(i+1)%n;d=(j+1)*n+i
            fs.append((a,b,c,d));sm.append(True);uv.append([(lengths[i],distance[j]),(lengths[i+1],distance[j]),(lengths[i+1],distance[j+1]),(lengths[i],distance[j+1])])
    fs.extend([tuple(reversed(range(n))),tuple((len(profiles)-1)*n+i for i in range(n))]);uv.extend([None,None]);sm.extend([False,False])
    g.poly(k,vs,fs,'Graphite',uv=uv,smooth=sm)
