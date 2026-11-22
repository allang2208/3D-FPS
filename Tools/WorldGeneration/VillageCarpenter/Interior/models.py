"""Plot 04 interior pieces in centimetres. Positive Y is the back of the tool chest."""
from math import cos, sin, pi, radians
from random import Random
from mathutils import Vector
from geometry import SurfaceMesh, PALETTE

PALETTE.update(Iron=(.14,.115,.09),Steel=(.29,.28,.25),WetOak=(.21,.13,.07),
               Water=(.12,.21,.19),Brass=(.45,.32,.15),Linen=(.43,.38,.29))


class Model(SurfaceMesh):
    def poly(self, points, material, uv, outward):
        order = list(range(len(points)))
        a,b,c = (Vector(v) for v in points[:3])
        if (b-a).cross(c-a).dot(Vector(outward))<0:
            order.reverse()
        start = self.vertices(points)
        self.face([start+i for i in order],[uv[i] for i in order],material)

    def bar(self, rng, a, b, width, depth, mat, bevel=.12):
        # Section and UV axis follow the stock, including upright cleats and hinge pins.
        a,b = Vector(a),Vector(b)
        direction=(b-a).normalized()
        side=direction.cross(Vector((0,0,1)) if abs(direction.z)<.9 else Vector((0,1,0))).normalized()
        up=direction.cross(side)
        w,h=width*.5,depth*.5
        q=min(bevel,w*.3,h*.3)
        section=((-w+q,-h),(w-q,-h),(w,-h+q),(w,h-q),(w-q,h),(-w+q,h),(-w,h-q),(-w,-h+q))
        left=[a+side*x+up*y for x,y in section]
        right=[b+side*x+up*y for x,y in section]
        phase,shift=rng.random(),rng.random()
        for i in range(8):
            j=(i+1)%8
            span=(left[i]-left[j]).length/60.
            height=(a-b).length/65.
            uv=[(shift,phase),(shift+span,phase),(shift+span,phase+height),(shift,phase+height)]
            self.poly([left[i],left[j],right[j],right[i]],mat,uv,(left[i]+left[j])*.5-a)
            shift+=span
        uv=[(.5+shift+x/60,.5+phase+y/60) for x,y in section]
        end='Endgrain' if mat in ('Oak','Sawn') else mat
        self.poly(left,end,uv,-direction)
        self.poly(right,end,uv,direction)

    def tube(self, rng, a, b, r, mat, r2=None, sides=None):
        # Short tapered pins, domed nail shoulders and rolled hinge knuckles.
        a,b=Vector(a),Vector(b)
        direction=(b-a).normalized()
        x=direction.cross(Vector((0,0,1)) if abs(direction.z)<.9 else Vector((0,1,0))).normalized()
        y=direction.cross(x)
        count=sides or (12,8,6)[self.level]
        offsets=[x*cos(i*2*pi/count)+y*sin(i*2*pi/count) for i in range(count)]
        left=[a+o*r for o in offsets]
        right=[b+o*(r if r2 is None else r2) for o in offsets]
        shift=rng.random()
        for i in range(count):
            j=(i+1)%count
            self.poly([left[i],left[j],right[j],right[i]],mat,
                      [(shift+(i+d)/count,(b-a).length*z/56) for d,z in ((0,0),(1,0),(1,1),(0,1))],offsets[i]+offsets[j])
        uv=[(.5+o.dot(x)*r/30,.5+o.dot(y)*r/30) for o in offsets]
        self.poly(left,mat,uv,-direction)
        self.poly(right,mat,uv,direction)


def stave_point(radius,angle,z):
    return (radius*cos(angle),radius*sin(angle),z)


def barrel(m):
    rng=Random(8404)
    count=22
    for i in range(count):
        start,end=(i+.026)*2*pi/count,(i+.974)*2*pi/count
        a=(start+end)*.5
        radial=Vector((cos(a),sin(a),0))
        phase,u=rng.random(),rng.random()
        lip=72+rng.uniform(-.65,.65)
        rings=[(0,24.2),(6,25.4),(22,28.7),(42,30.0),(60.8,29.3),(64.4,29.1),(lip-.66,28.3),(lip,27.95)]
        for inside in (False,True):
            for j,((z0,r0),(z1,r1)) in enumerate(zip(rings,rings[1:])):
                wall=2.15 if inside else 0.
                points=[stave_point(r-wall,ang,z) for r,ang,z in ((r0,start,z0),(r0,end,z0),(r1,end,z1),(r1,start,z1))]
                mat='WetOak' if inside and j<4 else 'Oak'
                if inside and j==4: mat='Sawn'  # exposed tide mark above the water
                self_uv=[(u+d*.114,phase+z/74) for d,z in ((0,z0),(1,z0),(1,z1),(0,z1))]
                m.poly(points,mat,self_uv,-radial if inside else radial)
        rim=[stave_point(r,ang,lip) for r,ang in ((27.95,start),(27.95,end),(25.8,end),(25.8,start))]
        m.poly(rim,'Endgrain',[(u+x/48,phase+y/48) for x,y,z in rim],(0,0,1))
        for ang,sign in ((start,-1),(end,1)):
            points=[stave_point(r,ang,z) for z,r in rings]+[stave_point(r-2.15,ang,z) for z,r in reversed(rings)]
            # Strips prevent concave end-cap tessellation across the barrel belly.
            for j in range(len(rings)-1):
                face=[points[j],points[j+1],points[-2-j],points[-1-j]]
                m.poly(face,'Oak',[(u,phase+rings[j][0]/74),(u,phase+rings[j+1][0]/74),(u+.03,phase+rings[j+1][0]/74),(u+.03,phase+rings[j][0]/74)],
                       (-sin(ang)*sign,cos(ang)*sign,0))
    for z,radius,width in ((6.8,25.85,4),(26,29.48,4.7),(54,30.1,4.6),(68,28.91,3.5)):
        n=(44,30,22)[m.level]
        for i in range(n):
            a,b=2*pi*i/n,2*pi*(i+1)/n
            for lo,hi,dr,rr,mat in ((-width/2,-width/2+.39,-.12,.13,'Steel'),(-width/2+.39,width/2-.32,.13,.13,'Iron'),(width/2-.32,width/2,.13,-.12,'Iron')):
                v=[stave_point(radius+d,t,z+h) for d,t,h in ((dr,a,lo),(dr,b,lo),(rr,b,hi),(rr,a,hi))]
                m.poly(v,mat,[(i/n*3,z/55),((i+1)/n*3,z/55),((i+1)/n*3,(z+hi-lo)/55),(i/n*3,(z+hi-lo)/55)],(cos(a),sin(a),0))
        for angle in (-1.6+z*.018,-1.48+z*.018):
            m.tube(rng,stave_point(radius+.08,angle,z),stave_point(radius+.56,angle,z),.79,'Iron',.53)
    m.tube(rng,(0,0,2),(0,0,4.5),22.9,'WetOak',sides=32)
    # A damp wiping cloth folds over the near rim. Follow the stave profile down
    # both sides so there is a weighted hem and a thickness at the silhouette.
    ribs=(12,8,5)[m.level]
    levels=((25.3,62.),(25.6,69.4),(26.2,72.9),(27.6,73.4),(29.0,72.6),(29.5,67.),(30.2,57.),(31.1,46.))
    rows=[]
    for j,(r,z) in enumerate(levels):
        row=[]
        for i in range(ribs+1):
            t=i/ribs
            wave=sin(t*pi*4+.4)*.47+sin(t*pi*7)*.18
            sag=(sin(t*pi)*2.6+sin(t*pi*2)*1.1) if j==len(levels)-1 else 0.
            row.append(stave_point(r+wave,-2.92+t*.53,z+wave*.24-sag))
        rows.append(row)
    for j in range(len(rows)-1):
        for i in range(ribs):
            f=[rows[j][i],rows[j][i+1],rows[j+1][i+1],rows[j+1][i]]
            mid=Vector(f[0])+Vector(f[1]);mid.z=0
            m.poly(f,'Linen',[(i/ribs, j/7),((i+1)/ribs,j/7),((i+1)/ribs,(j+1)/7),(i/ribs,(j+1)/7)],
                   -mid if j<2 else (0,0,1) if j<4 else mid)
    # A short-handled dipper rests on two edges of the barrel, clear of the centre.
    m.bar(rng,(-20,-19,73.4),(10,-22,73.8),2.9,1.5,'Sawn',.3)
    bowl(m,(13,-21.8,73.3),4.4,2.55,'Oak')


def bowl(m,c,r,h,mat):
    n=(24,16,10)[m.level]
    for i in range(n):
        a,b=2*pi*i/n,2*pi*(i+1)/n
        section=((.28,0.),(.67,.20),(1.,1.),(.90,.96),(.64,.32),(.22,.18))
        for j,((r0,z0),(r1,z1)) in enumerate(zip(section,section[1:])):
            pts=[(c[0]+r*rad*cos(t),c[1]+r*rad*sin(t),c[2]+z*h) for rad,t,z in ((r0,a,z0),(r0,b,z0),(r1,b,z1),(r1,a,z1))]
            out=(cos(a),sin(a),-.4) if j<2 else (0,0,1) if j==2 else (-cos(a),-sin(a),1)
            m.poly(pts,mat,[(p[0]/48,p[1]/48+p[2]/60) for p in pts],out)
    for rad,dz,up in ((.28,0.,-1),(.22,.18,1)):
        pts=[(c[0]+r*rad*cos(i*2*pi/n),c[1]+r*rad*sin(i*2*pi/n),c[2]+dz*h) for i in range(n)]
        m.poly(pts,mat,[(p[0]/48,p[1]/48) for p in pts],(0,0,up))


def water(m):
    pts=[stave_point(26.95,2*pi*i/48,0) for i in range(48)]
    m.poly(pts,'Water',[(.5+x/53.9,.5+y/53.9) for x,y,z in pts],(0,0,1))


def chest_body(m):
    rng=Random(1709)
    for j in range(6):m.board(rng,(0,-20+j*8,3),73,7.95,4,material='Oak',wane=.26)
    for sign in (-1,1):
        for i in range(4):
            z=6.8+i*8.15
            m.bar(rng,(-36.2,sign*22.4,z),(36.2,sign*22.4,z),2.9,8,'Oak' if i!=2 else 'Sawn',.32)
            m.bar(rng,(sign*35.3,-21,z),(sign*35.3,21,z),3.3,8,'Oak',.28)
        for y in (-22.5,22.5):
            m.bar(rng,(sign*31.1,y,3.6),(sign*31.1,y,36.1),5.9,4.6,'Sawn',.48)
        for x in (-23,23):
            m.bar(rng,(x,sign*24.2,5.5),(x,sign*24.2,31.6),3.6,1.08,'Iron')
            if m.level<2:
                for z in (7.8,28.9):
                    m.tube(rng,(x,sign*24.5,z),(x,sign*25.25,z),.65,'Steel',.48)
        # Rolled iron loops and a drop handle on each short end.
        x=sign*37.2
        m.bar(rng,(x,-6,24),(x,6,24),.9,3.8,'Iron')
        for y in (-5.3,5.3):m.tube(rng,(x,y,24),(x+sign*2.1,y,20),.64,'Iron')
        m.tube(rng,(x+sign*2.1,-5.3,20),(x+sign*2.1,5.3,20),.83,'Steel')
    m.bar(rng,(-4,-24.1,28),(4,-24.1,28),1.65,3,'Iron')
    for x in (-23,23):
        m.tube(rng,(x-3.6,24.4,37),(x+3.6,24.4,37),1.3,'Iron')


def chest_lid(m):
    # Origin is the actual rear hinge axle. Closed lid extends toward negative Y.
    rng=Random(891)
    for i in range(5):m.board(rng,(0,-43.6+i*9.6,1.4),75,9.54,3.8,material='Oak',wane=.24,check=i==0)
    for x in (-23,23):
        m.bar(rng,(x,-46.5,3.73),(x,-1.4,3.73),3.6,.85,'Iron')
        for y in (-43.,-23.,-3.):m.tube(rng,(x,y,4.14),(x,y,4.55),.67,'Steel',.46)
        for side in (-1,1):
            m.tube(rng,(x+side*3.85,0,0),(x+side*5.9,0,0),1.25,'Iron')
    m.bar(rng,(0,-48.4,-6),(0,-48.4,2.6),3.2,.9,'Iron')
    m.bar(rng,(-3.3,-49.1,-3.9),(3.3,-49.1,-3.9),1.6,1.4,'Brass')
    if m.level<2:
        for i in range(8):
            x,y=rng.uniform(-13,10),rng.uniform(-45.5,-35)
            p=[(x,y,3.34),(x+3.4,y+.33,3.34),(x+.82,y+.47,3.34)]
            m.poly(p,'Sawn',[(.4+a/40,.2+b/70) for a,b,z in p],(0,0,1))


def open_box(m,rng,c,w,d,h,yaw,closed):
    ca,sa=cos(radians(yaw)),sin(radians(yaw))
    def p(x,y,z):return (c[0]+ca*x-sa*y,c[1]+sa*x+ca*y,c[2]+z)
    def stock(a,b,width,depth,mat):m.bar(rng,p(*a),p(*b),width,depth,mat,.36)
    for side in (-1,1):
        for row in range(3):
            z=(row+.5)*h/3
            stock((-w/2,side*(d/2-1),z),(w/2,side*(d/2-1),z),2.15,h/3-.27,'Sawn')
            stock((side*(w/2-1),-d/2+2,z),(side*(w/2-1),d/2-2,z),2.15,h/3-.27,'Sawn')
        for y in (-d/2+2.9,d/2-2.9):
            stock((side*(w/2-3),y,.4),(side*(w/2-3),y,h-.3),5,4.3,'Oak')
            if m.level<2:
                for z in (3,h-3):
                    m.tube(rng,p(side*(w/2-.5),y,z),p(side*(w/2+.25),y,z),.55,'Iron',.42)
    for i in range(4):
        m.board(rng,p(0,(i-1.5)*(d-4)/4,1.4),w-3,(d-4)/4-.2,2.6,yaw,material='Oak')
        if closed:m.board(rng,p(0,(i-1.5)*d/4,h+1.1),w,d/4-.18,2.2,yaw,material='Sawn',wane=.32,check=i==1)


def crates(m):
    rng=Random(571)
    open_box(m,rng,(0,0,0),69,48,33,-3,True)
    open_box(m,rng,(4,1,35.2),48,34,22,7,False)
    for i in range(6):
        m.board(rng,(5,-8+3.4*i,40+i*.65),29+rng.random()*9,3.4,3,13+i*2,material='Sawn',wane=.3)


def hardware(m):
    rng=Random(9911)
    open_box(m,rng,(0,0,0),33,21,5.4,0,False)
    m.bar(rng,(-1,-8,4.1),(-1,8,4.1),1.3,3.2,'Oak')
    # Hinges sit in the wide compartment, square-cut nails in the narrow one.
    for i in range(3):
        x,y=5+i*2.1,-1+i*2
        m.bar(rng,(x,y-5.8,3.3+i*.66),(x+2,y+4.5,3.3+i*.66),4.8,.63,'Iron')
        m.tube(rng,(x-1.4,y-5.5,3.75+i*.66),(x+2.4,y-6.2,3.75+i*.66),.76,'Steel')
    for i in range((13,8,4)[m.level]):
        x,y=rng.uniform(-12,-5.5),rng.uniform(-6,3)
        e=(x+rng.uniform(-1.7,1.6),y+rng.uniform(3.4,5.6),3.25+i*.06)
        m.tube(rng,(x,y,e[2]),e,.28,'Iron',.05,4)
        m.bar(rng,(x-.56,y,e[2]),(x+.56,y,e[2]),.83,.44,'Steel')


def bin_and_pegs(m):
    rng=Random(2389)
    open_box(m,rng,(0,0,0),38,21,12,-2,False)
    for i in range(10):
        x,y=-13+i*2.7,rng.uniform(-4,2)
        bottom=(x,y,2.6)
        end=(x+rng.uniform(-4,5),y+rng.uniform(4,8),rng.uniform(14,22))
        m.tube(rng,bottom,end,1.05,'Sawn',.9,8 if m.level==0 else 6)


BUILDERS={'WashBarrel':barrel,'WashWater':water,'JoinersChest':chest_body,'JoinersChestLid':chest_lid,
          'StackedCases':crates,'HingeTray':hardware,'PegBin':bin_and_pegs}
