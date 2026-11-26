"""Village gate kit in UE centimetres. +Y faces the courtyard, X follows the walls."""
import math
import os
import sys
from pathlib import Path

import source_mesh
from author_kit import box, hoist
from wall_geometry import Mesh

STONE, CAP, PAVING, OAK, IRON = 'ChapelWall', 'Coping', 'Paving', 'Oak', 'Iron'


BRONZE, EMBERS = 'Bronze', 'Embers'
FOOTING, FLOORBOARD = 'Footing', 'Floorboard'


class Kit(Mesh):
    def __init__(self, seed):
        super().__init__(seed)
        self.phase = self.rng.random(), self.rng.random()
        self.groups = {key: {k: [] for k in ('vertices', 'normals', 'uv0', 'uv1', 'triangles')}
                       for key in (STONE, CAP, PAVING, OAK, IRON, BRONZE, EMBERS, FOOTING, FLOORBOARD)}

    def triangle(self, a, b, c, material, offset=(0., 0.)):
        super().triangle(a, b, c, material, offset)
        group = self.groups[material]
        nx, ny, nz = group['normals'][-1]
        axis = max(range(3), key=lambda i: abs((nx, ny, nz)[i]))
        tile = {STONE: 200., CAP: 94., PAVING: 200., OAK: 150., IRON: 80., BRONZE: 60.,
                EMBERS: 18., FOOTING: 90., FLOORBOARD: 200.}[material]
        # Project a continuous elevation through all pieces of the arch.
        # Keep up pointing towards the top of the DirectX scan in UE UV space.
        for i, (x, y, z) in zip((-3, -2, -1), (a, b, c)):
            u, v = ((y, z), (x, z), (x, y))[axis]
            group['uv0'][i] = [u/tile + self.phase[0], -v/tile + self.phase[1]]

    def block(self, x0, x1, y0, y1, z0, z1, mat=STONE, collide=True):
        box(self, x0, x1, y0, y1, z0, z1, mat, collide)

    def span(self, a, b, y0, y1, bottom_a, bottom_b, top_a, top_b, mat):
        self.solid([[(a,y0,z0),(b,y0,z1),(b,y1,z1),(a,y1,z0)]
                    for z0,z1 in ((bottom_a,bottom_b),(top_a,top_b))], mat)

    def incline(self, a, b, y0, y1, za, zb, thick, mat, collide=True):
        self.span(a,b,y0,y1,za-thick,zb-thick,za,zb,mat)
        if collide:
            pitch = math.atan2(zb-za,b-a)
            depth = thick*math.cos(pitch)
            self.boxes.append(dict(center=[(a+b)/2+depth/2*math.sin(pitch),(y0+y1)/2,
                                           (za+zb)/2-depth/2*math.cos(pitch)],
                                   size=[math.hypot(b-a,zb-za),y1-y0,depth],pitch=math.degrees(pitch)))

    def coping(self,a,b,y0,y1,z0,z1,material=CAP,*,support_top=False):
        # A dressed block with clipped corners and a slightly weathered bevel.
        cut=min(3.,(b-a)*.08,(y1-y0)*.12)
        outline=[(a+cut,y0),(b-cut,y0),(b,y0+cut),(b,y1-cut),
                 (b-cut,y1),(a+cut,y1),(a,y1-cut),(a,y0+cut)]
        cx,cy=(a+b)/2,(y0+y1)/2
        def ring(z,bevel):
            return [(x+math.copysign(min(bevel,abs(x-cx)),cx-x),
                     y+math.copysign(min(bevel,abs(y-cy)),cy-y),z) for x,y in outline]
        self.solid([ring(z0,1.),ring(z0+1.5,0.),ring(z1-2.,0.),ring(z1,1.5)],material)
        if support_top:
            # Inscribe the support box in the bevelled top, including its clipped corners.
            inset=1.5+cut*.5
            self.collision(a+inset,b-inset,y0+inset,y1-inset,z0,z1)

    def save(self, name):
        source_mesh.save_role(name, {}, self)

    def rim(self, rings, material):
        """Join nested contours into a closed rim, keeping the opening hollow."""
        for first,second in zip(rings,rings[1:]+rings[:1]):
            for i in range(len(first)):
                j=(i+1)%len(first)
                self.triangle(first[i],first[j],second[j],material)
                self.triangle(first[i],second[j],second[i],material)


def steps(m, start, end, bottom, rise, y0, y1, count):
    """Horizontal oak treads, two stringers and a continuous walkable collision plane."""
    dx, dz = (end-start)/count, rise/count
    for j in range(count):
        a,b = sorted((start+j*dx, start+(j+1)*dx))
        top = bottom+(j+1)*dz
        # Plane the leading arris and taper the underside of each solid oak tread.
        m.solid([[(a,y0,z),(b,y0,z),(b,y1,z),(a,y1,z)] for z in (top-5.,top-.8)] +
                [[(a+.35,y0+.5,top),(b-.35,y0+.5,top),(b-.35,y1-.5,top),(a+.35,y1-.5,top)]],OAK)
        if j%2==0:
            for y in (y0+7.,y1-7.):
                pin(m,(a+5.,y,top),(0,0,.75),1.6)
    a,b = sorted((start,end))
    za,zb = (bottom,bottom+rise) if end>start else (bottom+rise,bottom)
    for y in (y0+4,y1-9):
        m.incline(a,b,y,y+6,za+2,zb+2,16,OAK,False)
    # Only the continuous sloping face carries characters, from the first tread to the landing.
    pitch = math.atan2(zb-za,b-a)
    d = 7.
    m.boxes.append(dict(center=[(a+b)/2+d*math.sin(pitch),(y0+y1)/2,(za+zb)/2+dz/2-d*math.cos(pitch)],
                        size=[math.hypot(b-a,zb-za),y1-y0,2*d],pitch=math.degrees(pitch)))


def spindle(m,start,end,profile,material,sides=10):
    """Turn a sequence of radii around the line between the two pin centres."""
    import numpy as np
    a,b=np.array(start,dtype=float),np.array(end,dtype=float)
    unit=(b-a)/np.linalg.norm(b-a)
    ref=(0.,0.,1.) if abs(unit[2])<.9 else (1.,0.,0.)
    u=np.cross(ref,unit);u/=np.linalg.norm(u)
    v=np.cross(unit,u)
    circles=[math.cos(math.tau*i/sides)*u+math.sin(math.tau*i/sides)*v for i in range(sides)]
    m.solid([[tuple(a+(b-a)*t+r*p) for p in circles] for t,r in profile],material)


def pin(m,base,axis,r,material=IRON):
    end=tuple(a+b for a,b in zip(base,axis))
    spindle(m,base,end,((0.,r),(.42,r),(.85,r*.78),(1.,r*.44)),material,8)


def release_handle():
    m=Kit(4051)
    spindle(m,(-9,0,0),(17,0,0),((0.,7.),(.12,8.),(.76,8.),(.88,6.),(1.,6.)),IRON)
    spindle(m,(-5,0,1),(-9,0,39),((0.,4.2),(.13,5.),(.22,3.5),(.88,2.8),(1.,4.)),IRON)
    spindle(m,(-10,0,33),(-14,0,54),((0.,3.5),(.09,4.7),(.2,4.1),(.72,4.8),(.9,5.1),(1.,3.2)),OAK,12)
    for z in (35.,50.):
        spindle(m,(-10-(z-33)*.19,0,z-1.2),(-10-(z-33)*.19-.45,0,z+1.2),
                ((0.,4.9),(.25,5.2),(.75,5.2),(1.,4.9)),BRONZE,12)
    pin(m,(-9,0,0),(-3,0,0),5.,BRONZE)
    m.collision(-14,17,-8,8,-7,9)
    m.collision(-19,-2,-5,5,8,55)
    m.save('SM_GateReleaseHandle')


def wrought_grille(west):
    m=Kit(4047 if west else 4049)
    # Only the 17 cm tongues enter the jamb channels; the side galleries stay clear.
    outer=363. if west else 263.
    n=16 if west else 12
    eye,height=(265.,498.) if west else (165.,478.)
    def crest(x):return height-35.-67.*(x/outer)**2
    centers=[(2*i/(n-1)-1.)*(outer-6.) for i in range(n)]
    for x in centers:
        def bar_ring(z,r,d):
            bevel=min(r*.35,d*.35)
            return [(x+u,v,z) for u,v in ((-r+bevel,-d),(r-bevel,-d),(r,-d+bevel),(r,d-bevel),
                                          (r-bevel,d),(-r+bevel,d),(-r,d-bevel),(-r,-d+bevel))]
        m.solid([bar_ring(0.,.9,1.5),bar_ring(22.,5.7,4.5),bar_ring(30.,6.,5.),
                 bar_ring(crest(x)+6.,6.,5.)],IRON)
    # Each continuous strap sandwiches the uprights; rivet heads sit on its face.
    # The curved crown follows the head of the opening, retaining the old hoist eyes.
    for row in range(5):
        def seam(x):return crest(x) if row==4 else 49.+row*83.
        for side in (-1,1):
            y0,y1=sorted((side*5.,side*8.))
            nodes=[-outer,*centers[1:-1],outer]
            for a,b in zip(nodes,nodes[1:]):
                m.span(a,b,y0,y1,seam(a)-5.,seam(b)-5.,seam(a)+5.,seam(b)+5.,IRON)
            for x in centers:
                pin(m,(x,side*8.,seam(x)),(0,side*2.,0),3.2)
    for x in (-eye,eye):
        # Open forged lifting eye in the YZ plane, seated into a double-strapped lug.
        bottom=crest(x)
        m.block(x-8,x+8,-7,7,bottom-10.,height-7.,IRON,False)
        segments=16
        for i in range(segments):
            a,b=[math.tau*j/segments for j in (i,i+1)]
            def ring(t):
                return [(x+3.6*math.sin(phi),(8.+3.5*math.cos(phi))*math.cos(t),
                         height+(8.+3.5*math.cos(phi))*math.sin(t)) for phi in [math.tau*j/8 for j in range(8)]]
            # Connect only the outer tube surface, avoiding a disk across the eye.
            ra,rb=ring(a),ring(b)
            for j in range(8):
                k=(j+1)%8
                m.triangle(ra[j],rb[j],rb[k],IRON);m.triangle(ra[j],rb[k],ra[k],IRON)
    m.collision(-outer,outer,-9.,9.,0.,height)
    m.save('SM_GateWroughtGrille'+('West' if west else 'East'))


def door_surround(m,throat,spring,rise,face,direction):
    # Each wedge wraps into the tunnel and rolls from the deep reveal across a
    # chamfered nose into the wall. All rings share the same angular joint.
    count=21
    for i in range(count):
        a=-math.pi/2+math.pi*i/count+.0017
        b=-math.pi/2+math.pi*(i+1)/count-.0017
        key=i==count//2
        profile=[(-32.,-7.),(-32.,34.),(1.,34.),(11.,30.),(15.+(4. if key else 0.),23.),
                 (15.+(4. if key else 0.),0.),(9.,-6.),(-32.,-7.)]
        def facepoint(t,depth,r):
            return ((throat+r)*math.sin(t),face+direction*depth,spring+(rise+r+(9. if key and r>20. else 0.))*math.cos(t))
        # Wind each elevation outwards as the bevel turns into the opening.
        outline=list(reversed(profile[:-1])) if direction>0 else profile[:-1]
        ra=[facepoint(a,d,r) for d,r in outline]
        rb=[facepoint(b,d,r) for d,r in outline]
        m.solid([ra,rb],CAP)
    for s in (-1,1):
        x=throat*s
        for j in range(5):
            z=j*spring/5.
            a,b=sorted((x-6.*s,x+(40.+(6. if j%2 else 0.))*s))
            y0,y1=sorted((face-direction*32.,face+direction*14.))
            m.coping(a,b,y0,y1,z+.35,z+spring/5.-.55,FOOTING if z==0. else CAP)
        a,b=sorted((x-9.*s,x+49.*s))
        y0,y1=sorted((face-direction*35.,face+direction*19.))
        m.coping(a,b,y0,y1,spring-15.,spring+1.)
    # A shallow second archivolt has a continuous shadow joint above the key.
    for i in range(count):
        a,b=(-math.pi/2+math.pi*i/count,-math.pi/2+math.pi*(i+1)/count)
        y0,y1=sorted((face-direction*1.,face+direction*5.))
        rings=[]
        for r in (40.,48.):
            rings.append([((throat+r)*math.sin(t),y,spring+(rise+r)*math.cos(t))
                          for t,y in ((a,y0),(b,y0),(b,y1),(a,y1))])
        m.solid(rings,CAP)


def ward_fittings(m,outer,front,floor,roof,well_y):
    throat=outer-188.
    # Cast mounting plate, its sunk bolts, axle cheeks and two stops.
    # The stepped, clipped outline catches a rim of light without a flat square sheen.
    shape=[(-22.,-19.),(-16.,-29.),(12.,-29.),(22.,-18.),(22.,20.),(12.,32.),(-12.,32.),(-22.,20.)]
    def escutcheon(depth,scale):
        return [(throat-depth,156.+dy*scale,113.+dz*scale) for dy,dz in reversed(shape)]
    m.solid([escutcheon(-.5,1.),escutcheon(3.8,1.),escutcheon(6.,.92)],IRON)
    m.collision(throat-6.,throat+1.,135.,177.,86.,143.)
    for j in range(9):
        angle=math.radians(-51.+j*12.75)
        y,z=156.+19.*math.sin(angle),113.+19.*math.cos(angle)
        pin(m,(throat-6.,y,z),(-1.4,0,0),1.5 if j%2 else 2.,BRONZE)
    # A few hot pieces of fuel sit at the lip of the actual bronze bowl.
    for i in range(7):
        t=math.tau*i/7
        x=throat-29.+4.8*math.cos(t); y=89.+4.*math.sin(t)
        spindle(m,(x,y,174.2),(x+.65,y-.4,177.5+(i%3)),((0.,2.1),(.45,3.7),(1.,1.1)),EMBERS,7)
    for y in (141.,171.):
        for z in (95.,132.):
            pin(m,(throat-6.,y,z),(-2.8,0,0),3.,BRONZE)
    spindle(m,(throat-15.,156.,113.),(throat,156.,113.),((0.,10.),(.16,12.),(.84,12.),(1.,10.)),IRON)
    for y in (137.,175.):m.block(throat-12.,throat-4.,y-3.,y+3.,135.,142.,IRON,False)
    # Stone ribs along the barrel vault continue into the tunnel as pilasters.
    for y in (front+133.,-72.,204.):
        for s in (-1,1):
            a,b=sorted((s*(throat-9.),s*(throat+1.)))
            m.block(a,b,y-15.,y+15.,-8.,229.,STONE)
            m.coping(a-2,b+2,y-19.,y+19.,219.,236.)
        for i in range(17):
            a,b=[-math.pi/2+math.pi*j/17+e for j,e in ((i,.001),(i+1,-.001))]
            rings=[]
            for r in (-9.,2.):
                rings.append([((throat+r)*math.sin(t),v,236.+(floor-311.+r)*math.cos(t))
                              for t,v in ((a,y-16.),(b,y-16.),(b,y+16.),(a,y+16.))])
            m.solid(rings,CAP)
    for face,inside in ((front,1),(264.,-1)):
        # The upper band projects over a course of individually bedded corbels.
        for j in range(7):
            x=(j-3)*(outer-74.)/3.
            def corbel_ring(z,length,width):
                ya,yb=sorted((face-inside*length,face+inside*2.))
                return [(x-width,ya,z),(x+width,ya,z),(x+width,yb,z),(x-width,yb,z)]
            m.solid([corbel_ring(roof-138.,4.,10.),corbel_ring(roof-127.,11.,13.),
                     corbel_ring(roof-99.,22.,17.),corbel_ring(roof-88.,24.,17.)],CAP)
        ya,yb=sorted((face-inside*25.,face+inside*1.))
        m.coping(-outer+22.,outer-22.,ya,yb,roof-89.,roof-77.)
    # Exposed transverse oak beams land on corbels and bring the ceiling down to scale.
    for y in (well_y+106.,106.):
        m.block(-outer+34.,outer-34.,y-8.,y+8.,roof-53.,roof-25.,OAK)
        for s in (-1,1):
            a,b=sorted((s*(outer-78.),s*(outer-32.)))
            m.coping(a,b,y-14.,y+14.,roof-65.,roof-52.)


def window_frame(m,cut,near,far):
    """A dressed stone surround with one continuous chamfered reveal."""
    left,right,base,head=cut
    cx=(left+right)/2
    sill=base+9.
    spring=head-30.
    angles=[math.pi*i/10 for i in range(11)]
    def outline(y):
        return [(left,y,base),(right,y,base),
                *[(cx+(right-cx)*math.cos(t),y,head) for t in angles]]
    def bore(y,bevel):
        radius=21.+bevel
        return [(cx-radius,y,sill-bevel),(cx+radius,y,sill-bevel),
                *[(cx+radius*math.cos(t),y,spring+radius*math.sin(t)) for t in angles]]
    # The wall stops at the rectangular cut. Front, back and soffit all
    # belong to this one mesh surface, including the paired central windows.
    m.rim([outline(near-4.),bore(near-4.,3.),bore(near+2.,0.),
           bore(far-2.,0.),bore(far+4.,3.),outline(far+4.)],CAP)
    m.collision(left,right,near,far,base,sill)
    m.collision(left,cx-21.,near,far,sill,head)
    m.collision(cx+21.,right,near,far,sill,head)
    arch=bore(near,0.)[2:]
    for (x0,_,z0),(x1,_,z1) in zip(arch,arch[1:]):
        m.collision(x1,x0,near,far,max(z0,z1),head)


def gate_shell(m, outer, front, rear, floor, roof, throat):
    '''A square envelope. Its only full-height breaks below the gallery are the two road mouths.'''
    spring, crown = 236., floor - 75.
    rise = crown - spring
    arch = [(throat*math.sin(t), spring+rise*math.cos(t))
            for t in [-math.pi/2 + math.pi*i/24 for i in range(25)]]

    def pierced(u0, u1, z0, z1, openings, draw):
        cuts = sorted({u0, u1, *(v for left,right,_,_ in openings for v in (left,right))})
        for a,b in zip(cuts, cuts[1:]):
            voids = sorted((max(z0,low),min(z1,high)) for left,right,low,high in openings
                           if left <= a and b <= right and low < z1 and high > z0)
            base = z0
            for low,high in voids:
                if base < low:
                    draw(a,b,base,low)
                base = max(base,high)
            if base < z1:
                draw(a,b,base,z1)

    # The transverse hall sits forward of the grille. A single section governs
    # the vault, walking surfaces and collision on both sides of each pier.
    hall_front,hall_back = -173.,-34.
    lane = outer-147.
    crest = lane-198.
    def hall_level(x):
        t=max(0.,min(1.,(lane-abs(x))/(lane-crest)))
        return 360.+(floor-360.)*t

    eye = throat-81.
    for (a,za),(b,zb) in zip(arch,arch[1:]):
        cuts=sorted({a,b,*(v for v in (-crest,crest,-eye-24.,-eye+24.,eye-24.,eye+24.) if a<v<b)})
        for l,r in zip(cuts,cuts[1:]):
            zl=za+(zb-za)*(l-a)/(b-a); zr=za+(zb-za)*(r-a)/(b-a)
            bands=[(front,hall_front),(hall_front,hall_back),(hall_back,-16.),(16.,rear)]
            if abs(abs((l+r)/2)-eye)<24.:
                bands[-1:]=[(16.,141.),(197.,rear)]
            for y0,y1 in bands:
                crossing=y0==hall_front
                tl,tr=(hall_level(l),hall_level(r)) if crossing else (floor,floor)
                m.span(l,r,y0,y1,zl,zr,tl-12.,tr-12.,STONE)
                m.collision(l,r,y0,y1,max(zl,zr),min(tl,tr)-12.)
                m.span(l,r,y0,y1,tl-12.,tr-12.,tl,tr,PAVING)
                if not crossing:
                    m.collision(l,r,y0,y1,floor-12.,floor)

    # Flat, recessed corner porches receive the original courtyard stairs and
    # wall walks. The central road is bounded by solid cheeks up to the gallery.
    for side in (-1,1):
        for y0,y1,height in ((front,hall_front,floor),(hall_back,-16.,360.),
                             (-16.,16.,360.),(16.,rear,360.)):
            inside=throat+25. if y0==-16. else throat
            a,b=sorted((side*inside,side*outer))
            m.block(a,b,y0,y1,-24.,47.,FOOTING,False)
            m.block(a,b,y0,y1,47.,height-12.,STONE,False)
            m.collision(a,b,y0,y1,-24.,height-12.)
            m.block(a,b,y0,y1,height-12.,height,PAVING)
        for inner,edge in ((throat,lane),(lane,outer)):
            a,b=sorted((side*inner,side*edge))
            za,zb=hall_level(a),hall_level(b)
            m.block(a,b,hall_front,hall_back,-24.,47.,FOOTING,False)
            m.span(a,b,hall_front,hall_back,47.,47.,za-12.,zb-12.,STONE)
            m.span(a,b,hall_front,hall_back,za-12.,zb-12.,za,zb,PAVING)
            m.collision(a,b,hall_front,hall_back,-24.,min(za,zb)-12.)
        # One unbroken collision plane per incline, including the join over the vault.
        a,b=sorted((side*crest,side*lane))
        za,zb=hall_level(a),hall_level(b)
        pitch=math.atan2(zb-za,b-a)
        thick=6.
        m.boxes.append(dict(center=[(a+b)/2+thick*math.sin(pitch),(hall_front+hall_back)/2,
                                    (za+zb)/2-thick*math.cos(pitch)],
                            size=[math.hypot(b-a,zb-za),hall_back-hall_front,2*thick],
                            pitch=math.degrees(pitch)))
        a,b=sorted((side*lane,side*outer))
        m.collision(a,b,hall_front,hall_back,348.,360.)
        # Enclose the moving guides, including their tips at full lift. This
        # bearing wall divides the road and machinery from the side approach.
        a,b=sorted((side*(throat+26.),side*(throat+42.)))
        m.block(a,b,hall_back,rear,360.,roof-25.)
        # Carry the wide rear opening over a recessed rectangular porch.
        a,b=sorted((side*(throat+42.),side*outer))
        m.block(a,b,rear-45.,rear,642.,roof-25.)
        m.block(a,b,rear-56.,rear+3.,628.,642.,CAP)
    m.collision(-crest,crest,hall_front,hall_back,floor-12.,floor)

    # Guards track the actual slope on the hoist side. A single central
    # opening on the other edge leads across a level forelanding to the stairs.
    def guard(a,b,y,za,zb):
        m.incline(a,b,y-4.5,y+4.5,za+92.,zb+92.,8.,OAK,False)
        m.incline(a,b,y-2.,y+2.,za+44.,zb+44.,4.,IRON,False)
        count=max(1,math.ceil((b-a)/93.))
        for i in range(count):
            x=a+(b-a)*i/count
            z=za+(zb-za)*i/count
            end_z=z+5.*(zb-za)/(b-a)
            m.span(x,x+5.,y-3.,y+3.,z,end_z,z+84.,end_z+84.,IRON)
        # The ramp stays continuous under the rail. Upright short boxes follow
        # the incline without extending below it into the road.
        for i in range(count):
            x0=a+(b-a)*i/count; x1=a+(b-a)*(i+1)/count
            z0=za+(zb-za)*i/count; z1=za+(zb-za)*(i+1)/count
            m.collision(x0,x1,y-3.,y+3.,min(z0,z1),max(z0,z1)+91.)
    guard(-crest,crest,hall_back,floor,floor)
    for side in (-1,1):
        a,b=sorted((side*crest,side*(throat+34.)))
        guard(a,b,hall_back,hall_level(a),hall_level(b))
        a,b=sorted((side*crest,side*(outer-32.)))
        guard(a,b,hall_front-2.,floor,floor)

    windows = [(x-33.,x+33.,floor+126.,floor+254.) for x in (-outer*.43,-44.,44.,outer*.43)]
    for near,far in ((front,front+45.),(rear-45.,rear)):
        def elevation(a,b,low,high):
            m.block(a,b,near,far,low,high)
        if far==rear:
            # Each side porch opens sideways under its own lintel. Only the
            # road has a monumental arch on the courtyard elevation.
            pierced(-throat-42.,throat+42.,floor,roof-25.,windows,elevation)
            for a,b in ((-throat-42.,-throat),(throat,throat+42.)):
                elevation(a,b,360.,floor)
        else:
            pierced(-outer,outer,floor,roof-25.,windows,elevation)
        face = front if near==front else rear
        direction = -1 if near==front else 1
        def relief(a,b,depth,low,high,mat=CAP):
            y0,y1 = sorted((face,face+direction*depth))
            m.block(a,b,y0,y1,low,high,mat,False)

        door_surround(m,throat,spring,rise,face,direction)
        for cut in windows:
            window_frame(m,cut,near,far)
        relief(-outer,outer,7.,roof-75.,roof-61.)

    for side in (-1,1):
        a,b=sorted((side*(outer-32.),side*outer))
        def flank(ya,yb,low,high):
            m.block(a,b,ya,yb,low,high)
        # The low landing stays level through the full walk and stair sockets.
        side_openings=[(hall_back-74.,180.,360.,628.),
                       (front+114.,front+148.,floor+150.,floor+252.)]
        pierced(front+45.,rear-45.,360.,roof-25.,side_openings,flank)

    # Alternating corner quoins articulate the deep returns and carry the crown
    # down to ground. Rear quoining stops beside the stair door at landing height.
    for s in (-1,1):
        for face,d in ((front,1),(rear,-1)):
            def footing(spread,z):
                l,r=sorted((s*(outer-84.-spread),s*(outer+spread)))
                near,far=sorted((face-d*spread,face+d*(67.+spread)))
                bevel=9.
                return [(l+bevel,near,z),(r-bevel,near,z),(r,near+bevel,z),(r,far-bevel,z),
                        (r-bevel,far,z),(l+bevel,far,z),(l,far-bevel,z),(l,near+bevel,z)]
            m.solid([footing(25.,-24.),footing(25.,47.),footing(12.,87.)],FOOTING)
            m.solid([footing(12.,87.),footing(12.,206.),footing(4.,239.)],STONE)
            # A collision box inset into the splayed foot leaves the approach to
            # each rear doorway clear at the height of the adjoining stair.
            l,r=sorted((s*(outer-84.),s*(outer+12.)))
            near,far=sorted((face-d*12.,face+d*67.))
            m.collision(l,r,near,far,-24.,211.)
            for j in range(math.ceil((roof+20.)/57.)):
                low=-20.+57.*j
                high=min(low+55.,roof-26.)
                if high<=low or high<=239.:
                    continue
                low=max(low,239.)
                length=70. if j%2==0 else 44.
                width=49. if j%2==0 else 66.
                if d<0 and low<632. and high>359.:
                    # Keep the jamb clear along the actual courtyard stair axis.
                    length=5.
                x0,x1=sorted((s*(outer-length),s*(outer+5.)))
                y0,y1=sorted((face-d*5.,face+d*width))
                m.coping(x0,x1,y0,y1,low,high)

    # The old player-built stair snaps just outside the east shoulder.
    m.block(outer,outer+145.,63.,167.,344.,360.,PAVING)
    m.block(outer,outer+132.,78.,151.,-24.,344.,STONE)
    # Separate rows of threshold flags and an inset drain follow the road through the vault.
    original_phase=m.phase
    for start,end in ((front-32.,-11.),(11.,rear+32.)):
        m.collision(-throat,throat,start,end,-6.,4.)
        rows=round((end-start)/57.)
        for row in range(rows):
            y0=start+(end-start)*row/rows; y1=start+(end-start)*(row+1)/rows
            count=max(4,round(2*throat/86.))+(row%2)
            joints=[-throat]+[-throat+(2*throat/count)*(j+m.rng.uniform(-.18,.18)) for j in range(1,count)]+[throat]
            for a,b in zip(joints,joints[1:]):
                m.phase=(original_phase[0]+m.rng.uniform(-.25,.25),original_phase[1]+m.rng.uniform(-.25,.25))
                m.coping(a+.35,b-.35,y0+.4,y1-.4,-7.,4.+m.rng.uniform(-.65,.65),PAVING)
        for s in (-1,1):
            a,b=sorted((s*(throat-14.),s*throat))
            m.coping(a,b,start,end,1.,11.)
    m.phase=original_phase
    hoist(m,throat+8.,1050. if outer>500. else 1010.)


def level_guard(m,corners,base):
    """Timber rails terminate against a single square iron post at each joint."""
    post=4.5
    stations=[corners[0]]
    for (x0,y0),(x1,y1) in zip(corners,corners[1:]):
        spans=math.ceil(math.hypot(x1-x0,y1-y0)/104.)
        stations.extend((x0+(x1-x0)*i/spans,y0+(y1-y0)*i/spans) for i in range(1,spans+1))
        m.collision(min(x0,x1)-post,max(x0,x1)+post,min(y0,y1)-post,max(y0,y1)+post,base,base+88.)
    for x,y in stations:
        m.block(x-post,x+post,y-post,y+post,base,base+88.,IRON,False)
    for (x0,y0),(x1,y1) in zip(stations,stations[1:]):
        for half,low,high,mat in ((3.75,79.,86.,OAK),(2.,35.,40.,IRON)):
            if y0==y1:
                a,b=sorted((x0,x1))
                m.block(a+post,b-post,y0-half,y0+half,base+low,base+high,mat,False)
            else:
                a,b=sorted((y0,y1))
                m.block(x0-half,x0+half,a+post,b-post,base+low,base+high,mat,False)


def stair_and_lookout(m,outer,front,rear,floor,roof,well_y):
    exit_x,turn_x=-174.,174.
    edge=turn_x+136.
    upper_near,upper_far=well_y-64.,well_y+64.
    lower_near,lower_far=well_y-204.,well_y-78.
    mid=(floor+roof)/2.
    # Open directly above the returning flight. The turning landing fits
    # under the deck with 265 cm of headroom, so its roof remains usable.
    well_end=turn_x+12.
    near,far=upper_near-6.,upper_far+6.
    def rectangle(x0,x1,y0,y1,z):
        return [(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)]
    m.rim([rectangle(-outer,outer,front,rear,roof),
           rectangle(exit_x,well_end,near,far,roof),
           rectangle(exit_x,well_end,near,far,roof-25.),
           rectangle(-outer,outer,front,rear,roof-25.)],PAVING)
    for a,b,y0,y1 in ((-outer,outer,front,near),(-outer,outer,far,rear),
                       (-outer,exit_x,near,far),(well_end,outer,near,far)):
        m.collision(a,b,y0,y1,roof-25.,roof)
    # Posts stand wholly on the deck. The west end is clear for dismounting.
    level_guard(m,[(exit_x+6.,near-9.),(well_end+9.,near-9.),
                   (well_end+9.,far+9.),(exit_x+6.,far+9.)],roof)

    # Two full-width runs share a masonry half-landing. Its arched face
    # looks into the forecourt and the existing transverse gallery.
    niche=upper_far-106.
    cap_base=mid-20.
    m.block(turn_x,edge,lower_near,niche,floor,cap_base)
    m.block(turn_x,turn_x+18.,niche,upper_far,floor,cap_base)
    m.block(edge-18.,edge,niche,upper_far,floor,cap_base)
    centre=(turn_x+edge)/2.
    radius=(edge-turn_x)/2.-18.
    for j in range(12):
        t0,t1=[-math.pi/2+math.pi*i/12 for i in (j,j+1)]
        a,b=[centre+radius*math.sin(t) for t in (t0,t1)]
        za,zb=[floor+139.+38.*math.cos(t) for t in (t0,t1)]
        m.span(a,b,niche,upper_far,za,zb,cap_base,cap_base,STONE)
        m.collision(a,b,niche,upper_far,max(za,zb),cap_base)
    m.coping(turn_x-3.,edge+3.,lower_near-3.,upper_far+3.,cap_base,mid-12.)
    m.collision(turn_x,edge,lower_near,upper_far,cap_base,mid-12.)
    m.block(turn_x,edge,lower_near,upper_far,mid-12.,mid,PAVING)
    steps(m,exit_x,turn_x,floor,mid-floor,lower_near,lower_far,16)
    steps(m,turn_x,exit_x,mid,roof-mid,upper_near,upper_far,16)

    for side in (-1,1):
        for along_x in (True,False):
            start,end=(-outer,outer) if along_x else (front,rear)
            edge=(rear if side>0 else front) if along_x else side*outer
            def edge_box(a,b,inside,outside,low,high,cap=False):
                v0,v1=sorted((edge-side*inside,edge+side*outside))
                coords=(a,b,v0,v1) if along_x else (v0,v1,a,b)
                if cap:
                    m.coping(*coords,low,high,support_top=low>=roof)
                else:
                    m.block(*coords,low,high)
            # The sides stop at the corner stones of the front and rear walls.
            a,b=(start,end) if along_x else (start+34.,end-34.)
            edge_box(a,b,34.,0.,roof,roof+46.)
            edge_box(a,b,39.,4.,roof+44.,roof+52.,True)
            edge_box(a,b,38.,7.,roof-26.,roof-14.,True)
            count=round((end-start)/139.)
            pitch=(end-start)/count
            for i in range(1,count):
                center=start+i*pitch
                edge_box(center-31.,center+31.,32.,0.,roof+50.,roof+105.)
                edge_box(center-34.,center+34.,36.,4.,roof+103.,roof+113.,True)
    for s in (-1,1):
        x0,x1=sorted((s*outer,s*(outer-63.)))
        for y0,y1 in ((front,front+63.),(rear-63.,rear)):
            m.block(x0,x1,y0,y1,roof+48.,roof+129.)
            m.coping(x0-4.,x1+4.,y0-4.,y1+4.,roof+127.,roof+139.,support_top=True)


def gate(west):
    m=Kit(3853 if west else 3857)
    outer,floor=(534.,520.) if west else (434.,500.)
    rear=264.
    front=rear-2.*outer
    roof=floor+580.
    well_y=min((front+rear)/2.,-258.)
    throat=outer-188.
    gate_shell(m,outer,front,rear,floor,roof,throat)
    ward_fittings(m,outer,front,floor,roof,well_y)
    stair_and_lookout(m,outer,front,rear,floor,roof,well_y)
    m.save('SM_HighPortalGallery'+('West' if west else 'East'))


# curtain_wall.py uses this kit's stone, cap and paving projection for the high walls.


if __name__=='__main__':
    source_mesh.OUT=Path(sys.argv[1])
    source_mesh.OUT.mkdir(exist_ok=True,parents=True)
    frames_only=os.environ.get("GATEHOUSE_FRAMES_ONLY")=="1"
    for west in (True,False):
        gate(west)
        if not frames_only:
            wrought_grille(west)
    if not frames_only:
        release_handle()
