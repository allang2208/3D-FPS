"""Mill-lane bakehouse geometry, in UE-local centimetres. Reuses village surface materials."""
from collections import defaultdict
from math import ceil, cos, hypot, pi, sin, sqrt
from random import Random


def sub(a,b):
    return tuple(x-y for x,y in zip(a,b))


def cross(a,b):
    return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


def dot(a,b):
    return sum(x*y for x,y in zip(a,b))


def unit(a):
    length=sqrt(dot(a,a))
    return tuple(x/length for x in a)


def mean(pts):
    return tuple(sum(v[i] for v in pts)/len(pts) for i in range(3))


class Mesh:
    def __init__(self):
        self.slots=defaultdict(lambda: ([],[],[],[]))

    def face(self,mat,points,center,grain=None):
        normal=unit(cross(sub(points[1],points[0]), sub(points[2],points[0])))
        if dot(normal,sub(mean(points),center))<0:
            points=list(reversed(points))
            normal=tuple(-v for v in normal)
        use_grain=grain and abs(dot(grain,normal))<.94
        if use_grain:
            side=unit(cross(normal,grain))
            along=unit(cross(side,normal))
        else:
            side=unit(cross((0,0,1) if abs(normal[2])<.9 else (0,1,0),normal))
            along=unit(cross(normal,side))
        tile=95. if mat in ('Oak','Sawn','DarkWood') else 142.
        vertices,normals,uvs,triangles=self.slots[mat]
        first=len(vertices)
        for v in points:
            vertices.append(v)
            normals.append(normal)
            uvs.append((dot(v,side)/tile,dot(v,along)/(tile*1.55 if use_grain else tile)))
        # UE static mesh front faces use clockwise winding.
        triangles.extend((first,first+i+1,first+i) for i in range(1,len(points)-1))

    def prism(self,mat,face,offset,grain=None):
        second=[tuple(v+delta for v,delta in zip(p,offset)) for p in face]
        center=mean(list(face)+second)
        self.face(mat,face,center,grain)
        self.face(mat,second,center,grain)
        for i in range(len(face)):
            j=(i+1)%len(face)
            self.face(mat,[face[i],face[j],second[j],second[i]],center,grain)

    def box(self,mat,x0,x1,y0,y1,z0,z1,bevel=0):
        b=min(bevel,(x1-x0)*.24,(y1-y0)*.24)
        outline=[(x0,y0+b),(x0+b,y0),(x1-b,y0),(x1,y0+b),
                 (x1,y1-b),(x1-b,y1),(x0+b,y1),(x0,y1-b)] if b else [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
        spans=(x1-x0,y1-y0,z1-z0)
        axis=spans.index(max(spans))
        grain=tuple(float(i==axis) for i in range(3)) if mat in ('Oak','Sawn','DarkWood') else None
        self.prism(mat,[(x,y,z0) for x,y in outline],(0,0,z1-z0),grain)

    def timber(self,mat,a,b,width,depth,arris=.8):
        axis=unit(sub(b,a))
        side=unit(cross(axis,(0,0,1) if abs(axis[2])<.92 else (0,1,0)))
        up=unit(cross(side,axis))
        w,d=width*.5,depth*.5
        k=min(arris,w*.3,d*.3)
        section=[(-w+k,-d),(w-k,-d),(w,-d+k),(w,d-k),(w-k,d),(-w+k,d),(-w,d-k),(-w,-d+k)]
        face=[tuple(a[i]+u*side[i]+v*up[i] for i in range(3)) for u,v in section]
        self.prism(mat,face,sub(b,a),axis)


WALLS = (
    # front/back coordinate, wall trace and openings (along, along, bottom, head)
    ('X',0,-402,402,[(-83,83,0,237),(-299,-130,98,210),(132,292,98,210),
                      (-63,63,402,495)]),
    ('X',902,-402,402,[(-54,79,405,493),(116,232,109,203)]),
    ('Y',-392,0,902,[(145,267,108,202),(415,525,408,500)]),
    ('Y',392,0,902,[(92,208,110,202),(448,548,401,495)]),
)
EAVE=553.


def skin(mesh,axis,pos,a,b,low,high,mat,depth=24,relief=0,bevel=0):
    p,q=pos-depth*.5-relief,pos+depth*.5+relief
    if axis=='X':
        mesh.box(mat,a,b,p,q,low,high,bevel)
    else:
        mesh.box(mat,p,q,a,b,low,high,bevel)


def wall(shell,frame,joinery,begin_surface=None):
    rng=Random(60614)
    for axis,pos,start,end,openings in WALLS:
        if begin_surface:
            begin_surface(axis,pos)
        # The rough opening surrounds the OUTSIDE of the lining. Previously the
        # plaster soffit and the oak soffit occupied the exact same plane.
        rough=[(a-9,b+9,z-7 if z else z,h+11) for a,b,z,h in openings]
        levels=sorted({-12.,64.,EAVE,*[v for _,_,z,h in rough for v in (z,h)]})
        for bottom,top in zip(levels,levels[1:]):
            voids=sorted((a,b) for a,b,z,h in rough if z<top and h>bottom)
            cursor=start
            for a,b in voids+[(end,end)]:
                if a>cursor:
                    skin(shell,axis,pos,cursor,a,bottom,top,'Mortar' if top<=64 else 'Plaster')
                    if top<=64:
                        # Stepped fieldstones under both faces of the limewashed panels.
                        courses=max(1,round((top-bottom)/19))
                        for course in range(courses):
                            lo=bottom+(top-bottom)*course/courses
                            hi=bottom+(top-bottom)*(course+1)/courses
                            span=a-cursor
                            n=max(1,round(span/48.))
                            cuts=[cursor]+[cursor+span*(i+rng.uniform(-.30,.30))/n for i in range(1,n)]+[a]
                            for l,r in zip(cuts,cuts[1:]):
                                if r-l>3:
                                    skin(shell,axis,pos,l+.65,r-.65,lo+.65,hi-.55,'Fieldstone',24,
                                         rng.uniform(1.,3.5),min(2.2,(hi-lo)*.12))
                cursor=max(cursor,b)
        for z in (68,303,543):
            # Passage interrupts the sole plate, but not the first-floor bressummer.
            pieces=[(start,-92),(92,end)] if axis=='X' and pos==0 and z==68 else [(start,end)]
            for a,b in pieces:
                skin(frame,axis,pos,a,b,z-6,z+6,'Oak',32)
        for a,b,z,h in openings:
            for lo,hi in ((a-9,a),(b,b+9)):
                skin(joinery,axis,pos,lo,hi,z,h,'Oak',34)
            skin(joinery,axis,pos,a-9,b+9,h,h+11,'Oak',36)
            if z==0: continue
            skin(joinery,axis,pos,a-9,b+9,z-7,z,'Sawn',43)
        posts = [-388,-310,-102,106,307,388] if axis=='X' else [10,72,330,613,837,892]
        for p in posts:
            spans=[(70,EAVE)]
            for a,b,z,h in rough:
                if p+6>a and p-6<b:
                    spans=[(i,j) for low,high in spans for i,j in ((low,min(high,z)),(max(low,h),high)) if j>i]
            for low,high in spans:
                skin(frame,axis,pos,p-6,p+6,low,high,'Oak',30)
        if axis=='Y':
            outer=pos+(-1 if pos<0 else 1)*13.5
            for a,b,z,h in [(12,65,74,145),(341,400,303,387),(760,828,76,172),(615,709,468,544)]:
                frame.timber('Oak',(outer,a,z),(outer,b,h),8,10)
    for pos in (0.,902.):
        if begin_surface:
            begin_surface('X',pos)
        gable=[(-391,pos-9,EAVE),(391,pos-9,EAVE),(0,pos-9,roof_z(0)-13)]
        shell.prism('Plaster',gable,(0,18,0))
        for x in (-202,0,202):
            frame.box('Oak',x-5,x+5,pos-14,pos+14,EAVE,roof_z(x)-12)
        for s in (-1,1):
            frame.timber('Oak',(0,pos,EAVE+7),(s*190,pos,roof_z(190)-22),8,10)
    # Two real oak leaves resting against their inner jambs. Keep the 1.5 m span clear.
    for sign in (-1,1):
        p=sign*79.
        for j in range(6):
            y=20+j*13.5
            joinery.box('Oak',p-2.6,p+2.6,y,y+13.1,.7,229,.45)
        for z in (29,171):
            joinery.box('Iron',p-3.8,p+3.8,21,93,z,z+4.8,.55)
            joinery.timber('Iron',(p,22,z+2.4),(sign*87,14,z+2.4),3,3,.35)
        joinery.timber('DarkWood',(p+sign*3.5,24,35),(p+sign*3.5,94,170),5,6)


def roof_z(x):
    return 803.-abs(x)*.61


def roof_roof(mesh,frame,flashing):
    rng=Random(2086)
    # Roof overhang and trimmers follow the blacksmith stack's 94.9 cm shaft.
    hole=(-299.,-191.,757.,865.)
    def subdivide(x0,x1,y0,y1):
        xs=sorted({x0,x1,*[v for v in hole[:2] if x0<v<x1]})
        ys=sorted({y0,y1,*[v for v in hole[2:] if y0<v<y1]})
        for a,b in zip(xs,xs[1:]):
            for c,d in zip(ys,ys[1:]):
                if not (hole[0]<(a+b)*.5<hole[1] and hole[2]<(c+d)*.5<hole[3]):
                    yield a,b,c,d
    def surface(a,b,c,d,mat,lift,thick,shape=None):
        poly=shape or [(a,c),(b,c),(b,d),(a,d)]
        mesh.prism(mat,[(x,y,roof_z(x)+lift) for x,y in poly],(0,0,-thick))
    for sign in (-1,1):
        for a,b,c,d in subdivide(min(0,sign*437),max(0,sign*437),-45,946):
            surface(a,b,c,d,'DarkWood',0,5)
        for course in range(18):
            low=max(0.,course*24.5-2.)
            high=min(438.,(course+1)*24.5+2.)
            c=-45.
            while c<946:
                d=min(946.,c+rng.uniform(20.,31.))
                a,b=sorted((sign*low,sign*high))
                for l,r,u,v in subdivide(a,b,c+.22,d-.22):
                    if r-l<.9 or v-u<1: continue
                    # Slightly clipped weather edges catch the eave light. The
                    # downslope course is below the overlapping upper course.
                    clip=min(rng.uniform(.7,2.2),(r-l)*.22,(v-u)*.16)
                    shape=[(l,u),(r-clip,u),(r,u+clip),(r,v-clip),(r-clip,v),(l,v)] if sign>0 else [
                        (l+clip,u),(r,u),(r,v),(l+clip,v),(l,v-clip),(l,u+clip)]
                    surface(l,r,u,v,'Slate',1.5+(17-course)*.042+rng.uniform(0,.32),2.1,shape)
                c=d
        # Roof-frame purlins and rafters are interrupted throughout the flue envelope.
        for xx in (42,158,278,389):
            x=xx*sign
            spans=[(-39.,940.)] if not hole[0]-7<x<hole[1]+7 else [(-39.,749.),(871.,940.)]
            for c,d in spans:
                frame.timber('Oak',(x,c,roof_z(x)-15),(x,d,roof_z(x)-15),12,14)
        for y in (-30,50,151,251,351,451,551,651,749,873,939):
            frame.timber('Oak',(sign*427,y,roof_z(427)-9),(0,y,roof_z(0)-9),8,10)
        for y in (-34,935):
            frame.timber('Oak',(sign*438,y,roof_z(438)),(0,y,roof_z(0)),9,14)
    frame.timber('Oak',(0,-41,785),(0,941,785),15,18)
    for y in (140,449,722):
        frame.timber('Oak',(-392,y,551),(392,y,551),15,18)
        frame.timber('Oak',(0,y,551),(0,y,785),13,13)
        for sign in (-1,1):
            frame.timber('Oak',(0,y,565),(sign*209,y,roof_z(209)-18),11,12)
    # Folded aprons lap the slate. Their inside edge sits against the shaft,
    # while the rear saddle sheds runoff around both cheeks.
    x0,x1,y0,y1=-293.,-197.,763.,859.
    for a,b,c,d in [(x0-18,x0,y0-16,y1+16),(x1,x1+18,y0-16,y1+16),
                     (x0,x1,y0-21,y0),(x0,x1,y1,y1+20)]:
        flashing.prism('Lead',[(x,y,roof_z(x)+4) for x,y in [(a,c),(b,c),(b,d),(a,d)]],(0,0,-1.3))
    for points in [[(x0,y0),(x1,y0)],[(x0,y1),(x1,y1)],[(x0,y0),(x0,y1)],[(x1,y0),(x1,y1)]]:
        (a,c),(b,d)=points
        poly=[(a,c,roof_z(a)+3),(b,d,roof_z(b)+3),(b,d,roof_z(b)+13),(a,c,roof_z(a)+13)]
        flashing.prism('Lead',poly,(0,1.2,0) if c==d else (1.2,0,0))
    # Capped ridge in short, lapped lengths; no continuous flat metal strip.
    for i in range(29):
        lo=-45+i*34.2
        hi=min(946.,lo+34.7)
        for sign in (-1,1):
            mesh.prism('Slate',[(0,lo,802),(sign*12,lo,798),(sign*10,lo,805),(0,lo,812)],(0,hi-lo,0))


def floor_and_stair(floor,frame,stair):
    rng=Random(24028)
    # The sales floor is flagstone, laid in staggered courses on a solid bed.
    floor.box('Mortar',-385,385,-13,895,-12,-2)
    for row in range(20):
        y=-13+row*45.4
        x=-385.
        while x<384.9:
            end=min(385.,x+rng.uniform(45,90))
            if end-x>1.5:
                floor.box('Flags',x+.45,end-.45,y+.40,min(895.,y+45.4)-.40,-3.,0.,
                          min(rng.uniform(.65,1.6),(end-x)*.15))
            x=end
    # An accessible oak threshold is carried to the flag course, down to the
    # village datum on the outward side. The entry has no raised sill.
    floor.prism('Flags',[(-83,-47,-7),(-83,-47,-3.8),(-83,-10,.1),(-83,-10,-7)],(166,0,0))
    # The flue must pass through both the loft deck and its supporting timbers.
    # The stair steps up +Y and turns left across a full-width top landing.
    holes=[(178,366,305,774),(-301,-189,754,870)]
    rects=[(-385,385,7,895)]
    for x0,x1,y0,y1 in holes:
        cropped=[]
        for a,b,c,d in rects:
            l,r,u,v=max(a,x0),min(b,x1),max(c,y0),min(d,y1)
            if l>=r or u>=v:
                cropped.append((a,b,c,d))
            else:
                cropped.extend(p for p in [(a,l,c,d),(r,b,c,d),(l,r,c,u),(l,r,v,d)] if p[0]<p[1] and p[2]<p[3])
        rects=cropped
    for a,b,c,d in rects:
        floor.box('DarkWood',a,b,c,d,307.1,310.5)
        x=a
        while x<b-.01:
            end=min(b,x+rng.uniform(17,29))
            y=c
            while y<d-.01:
                stop=min(d,y+rng.uniform(188,322))
                if end-x>.65 and stop-y>.65:
                    floor.box('Sawn',x+.12,end-.12,y+.14,stop-.14,309.8,315.,.55)
                y=stop
            x=end
    # Joists bear on wall plates. Doubled trimmers support cut joists without
    # placing a beam over a player's head on the upper flight.
    for y in (20,83,147,210,274,331,395,457,520,582,647,707,772,838,884):
        spans=[(-388,389)]
        for x0,x1,y0,y1 in holes:
            if y0-7<y<y1+7:
                spans=[(l,r) for a,b in spans for l,r in ((a,min(b,x0-4)),(max(a,x1+4),b)) if r>l]
        for a,b in spans:
            frame.timber('Oak',(a,y,300),(b,y,300),10.5,16)
    for x0,x1,y0,y1 in holes:
        for x in (x0-5,x1+5):
            frame.timber('Oak',(x,y0-7,299),(x,y1+7,299),10,18)
        for y in (y0-7,y1+7):
            frame.timber('Oak',(x0-9,y,299),(x1+9,y,299),11,18)
    n=18
    run=(774.-309.)/n
    for i in range(n):
        y=309+i*run
        top=(i+1)*17.5
        stair.box('Sawn',191,357,y-2.4,y+run,top-4.8,top,.9)
        stair.box('Oak',194,354,y,y+2.7,top-18.,top-4.7,.3)
    for x in (197,351):
        stair.timber('Oak',(x,304,-1),(x,780,313),10,18)
    for x in (196,352):
        for i in (0,4,8,12,17):
            y=309+(i+.28)*run
            z=(i+1)*17.5
            stair.box('Oak',x-3.5,x+3.5,y-3.5,y+3.5,z-5,z+86,.8)
        stair.timber('Oak',(x,313,103),(x,761,401),7,7.5)
        stair.timber('Oak',(x,313,63),(x,761,361),3.8,4)
    # Guard the open loft edges, with an unobstructed left turn at the head.
    for x in (173,372):
        for y in (302,421,540,659,768):
            stair.box('Oak',x-3.4,x+3.4,y-3.4,y+3.4,309,405,.8)
        stair.timber('Oak',(x,302,401),(x,768,401),6,7)
        stair.timber('Oak',(x,302,361),(x,768,361),3.5,4)
    for z in (361,401):
        stair.timber('Oak',(173,301,z),(372,301,z),5.8,6)


def casement_windows(mount,left,right):
    # Dimensions match the existing blacksmith hinge family. The housing
    # already owns the full-depth reveals, so this plate has no second frame.
    def pin(mesh,x,y,z,r,length):
        loop=[(x+r*cos(i*pi/6),y+r*sin(i*pi/6),z) for i in range(12)]
        mesh.prism('Iron',loop,(0,0,length))

    for side,leaf in ((1,left),(-1,right)):
        for z in (-51.,51.):
            hinge_y=-74*side
            mount.box('Iron',-13,-6,hinge_y-3.5,hinge_y+3.5,z-6,z+6,.55)
            mount.box('Iron',-8,.65,hinge_y-1.5,hinge_y+1.5,z-6.7,z-4.5,.35)
            pin(mount,0,hinge_y,z-5,.72,11.5)
            pin(leaf,0,0,z-3.8,1.2,7.8)

        def strip(mat,x0,x1,y0,y1,z0,z1,bevel=0.):
            l,r=sorted((side*y0,side*y1))
            leaf.box(mat,x0,x1,l,r,z0,z1,bevel)

        # Glazing lies in the sash rebate. Six panes end at lead bars, so the
        # open window is a true aperture and no transparent planes stack up.
        for l,r in ((1.,6.6),(67.4,73.5)):
            strip('Oak',-5.4,-.6,l,r,-81,81,.48)
        for lo,hi in ((-81,-74),(74,81)):
            strip('Oak',-5.4,-.6,6.6,67.4,lo,hi,.40)
        strip('Lead',-4.1,-1.4,36.1,37.7,-74,74,.18)
        for l,r in ((6.6,36.1),(37.7,67.4)):
            for lo,hi in ((-26,-24),(24,26)):
                strip('Lead',-4.1,-1.4,l,r,lo,hi,.15)
            for lo,hi in ((-74,-26),(-24,24),(26,74)):
                # One outer plane. Chapel glazing uses a two-sided material.
                y0,y1=sorted((side*l,side*r))
                leaf.face('Glass',[(-2.8,y0,lo),(-2.8,y1,lo),(-2.8,y1,hi),(-2.8,y0,hi)],
                          (-3.,(y0+y1)*.5,(lo+hi)*.5))
        for z in (-51.,51.):
            strip('Iron',-.6,.35,.9,6.6,z-1.7,z+1.7,.25)
        strip('Iron',-6.8,-5.4,68.8,72.,-8.5,1.8,.35)
        strip('Iron',-9.3,-6.5,69.5,71.2,-6.5,-4.8,.3)
        strip('Iron',-10.2,-8.8,65.,71.6,-6.6,-4.7,.3)
    # An indoor sill latch is reachable from the room when both leaves are open.
    mount.box('Iron',-39,-29,-4,4,-85.2,-81.8,.5)
    mount.timber('Iron',(-34,0,-82.7),(-34,0,-75.4),1.9,2.2,.3)
    ring=[(-34,3.4*cos(i*pi/6),-72.7+3.4*sin(i*pi/6)) for i in range(12)]
    for a,b in zip(ring,ring[1:]+ring[:1]):
        mount.timber('Iron',a,b,.8,.9,.13)


def bakery_oven(oven):
    rng=Random(20261120)
    cx=-245.
    def masonry(mat,x0,x1,y0,y1,z0,z1,n):
        weights=[rng.uniform(.7,1.3) for _ in range(n)]
        x=x0
        for w in weights:
            end=x+(x1-x0)*w/sum(weights)
            oven.box(mat,x+.45,end-.45,y0,y1,z0+.4,z1-.4,1.2)
            x=end

    # A log grate spans the masonry cheeks. Light catches broken ash and
    # fissures in the charcoal; the baking floor above stays clean.
    oven.box('Mortar',cx-86,cx+86,620,765,-9,12,3)
    for i in range(4):
        z=12+16*i
        for a,b in ((cx-84,cx-47),(cx+47,cx+84)):
            masonry('Fieldstone',a,b,625,758,z,z+16,1)
        for l,r in ((cx-47,cx-15),(cx+15,cx+47)):
            masonry('Soot',l,r,717,758,z,z+16,1)
    oven.box('Soot',cx-15,cx+15,753,760,12,74)
    for x in (-39,39):
        oven.box('Iron',cx+x-2.1,cx+x+2.1,632,718,13,22,.6)
    for y in (636,650,665,681,698,712):
        oven.timber('Iron',(cx-44,y,22),(cx+44,y,22),3.4,3.2,.5)

    def clinker(x,y,z,rx,ry,rz):
        # Angular broken coal, with occasional dull exposed cores. No emissive slab.
        n=7
        phase=rng.uniform(0,pi)
        radii=[rng.uniform(.77,1.07) for _ in range(n)]
        loop=[(x+rx*v*cos(phase+i*2*pi/n),y+ry*v*sin(phase+i*2*pi/n),z) for i,v in enumerate(radii)]
        cap=[(x+(p[0]-x)*.61,y+(p[1]-y)*.61,z+rz*rng.uniform(.77,1.1)) for p in loop]
        middle=(x,y,z+rz*.43)
        for i in range(n):
            j=(i+1)%n
            mat='Ember' if rng.random()<.09 else 'Coal'
            oven.face(mat,[loop[i],loop[j],cap[j]],middle)
            oven.face(mat,[loop[i],cap[j],cap[i]],middle)
            oven.face('Ash' if rng.random()<.18 else 'Coal',[cap[i],cap[j],(x,y,z+rz*1.15)],middle)

    lower_bed=[(cx+x,y,12.25) for x,y in
               [(-47,637),(-32,621),(-7,616),(27,626),(45,644),(46,706),(17,713),(-36,709),(-46,690)]]
    oven.prism('Ash',lower_bed,(0,0,1.3))
    for i in range(43):
        r=rng.uniform(1.6,5.3)
        clinker(cx+rng.uniform(-36,36),rng.uniform(632,706),13.55,r,r*rng.uniform(.62,1.4),r*.68)

    def split_log(ax,ay,az,bx,by,bz,radius):
        axis=unit((bx-ax,by-ay,bz-az))
        u=unit(cross(axis,(0,0,1)))
        v=unit(cross(u,axis))
        # Split billet, broad fractured top and faceted bark round the underside.
        section=[(-.79,.47),(-.15,.62),(.74,.46),(.96,-.10),(.58,-.84),(-.20,-.96),(-.85,-.62)]
        points=[]
        for t,s in [(0.,1.),(.31,1.01),(.73,.92),(1.,.84)]:
            center=(cx+ax+(bx-ax)*t,ay+(by-ay)*t,az+(bz-az)*t)
            points.append([tuple(center[k]+radius*s*(p*u[k]+q*v[k]) for k in range(3)) for p,q in section])
        middle=(cx+(ax+bx)/2,(ay+by)/2,(az+bz)/2)
        oven.face('Coal',points[0],middle,axis)
        oven.face('Coal',points[-1],middle,axis)
        for i,(lo,hi) in enumerate(zip(points,points[1:])):
            for j in range(len(section)):
                k=(j+1)%len(section)
                mat='DarkWood' if j in (0,1) and i==0 else 'Coal'
                oven.face(mat,[lo[j],hi[j],hi[k],lo[k]],middle,axis)
        # Short intermittent glow follows individual splits in the charred surface.
        for j in (2,5):
            for i in (1,2):
                lo,hi=points[i][j],points[i+1][j]
                if rng.random()<.83:
                    a=tuple(lo[k]+(hi[k]-lo[k])*.12 for k in range(3))
                    b=tuple(lo[k]+(hi[k]-lo[k])*.81 for k in range(3))
                    oven.timber('Ember',a,b,.58,.72,.08)

    for ends,r in [((-26,632,30,-19,704,29),7.4),((-4,640,29,5,707,30),7.1),
                   ((22,637,30,32,694,31),8.0),((-31,679,40,27,651,42),6.2),
                   ((-23,695,40,33,679,41),5.4)]:
        split_log(*ends,r)
    # A rear draught slot carries products of combustion from below the baking
    # deck into the vault beside the chimney throat.
    oven.box('Hearth',cx-89,cx+89,605,732,74,90,3)
    for l,r in ((cx-89,cx-15),(cx+15,cx+89)):
        oven.box('Hearth',l,r,732,764,74,90,1)
    oven.box('Hearth',cx-15,cx+15,753,764,74,90,1)
    # Oven deck and landing form a continuous level surface for the baker's peel.
    for i in range(3):
        masonry('Hearth',cx-82+54.7*i,cx-82+54.7*(i+1),588,628,89,95.4,1)
    for row in range(5):
        count=4+row%2
        sections=[(cx-70,cx+70,count)] if row<4 else [(cx-70,cx-15,2),(cx+15,cx+70,2)]
        for l,r,n in sections:
            masonry('Firebrick',l,r,628.5+row*25,653.2+row*25,89,95.4,n)
    for sign in (-1,1):
        x=cx+sign*68
        oven.box('Hearth',x-10,x+10,619,758,95,114,1)

    def wedge(mat,r,R,a,b,y,depth,spring):
        points=[(cx+rr*cos(t),y,spring+rr*sin(t)) for rr,t in ((r,a),(R,a),(R,b),(r,b))]
        oven.prism(mat,points,(0,depth,0))
    # A hand-laid firebrick vault is open inside. The second, wider jacket is
    # lime render, with clay reveals at the door and a soot-darkened rear barrel.
    for row in range(6):
        y=626.+row*20.9
        count=15 if row%2==0 else 16
        for i in range(count):
            a=pi*i/count+.002
            b=pi*(i+1)/count-.002
            wedge('Soot' if row>3 else 'Firebrick',59.,70.,a,b,y,20.5,112.)
    for i in range(25):
        wedge('Plaster',69.5,78.+1.2*sin(i*.7),pi*i/25,pi*(i+1)/25,633,118,112.)
    for i in range(13):
        wedge('Hearth' if i==6 else 'Firebrick',46.,67.,pi*i/13+.005,pi*(i+1)/13-.005,611,20,109.)
    for side in (-1,1):
        x=cx+side*56
        oven.box('Firebrick',x-10,x+10,610,629,94,109,.8)
    # Back wall is broken at the rear crown. The blacksmith stack takes smoke
    # through its authentic front port, scaled Z149..196. Inner flue ±17.55.
    for sign in (-1,1):
        oven.box('Soot',min(cx+sign*17,cx+sign*58),max(cx+sign*17,cx+sign*58),748,758,94,150)
    oven.box('Soot',cx-17,cx+17,749,759,94,149)
    for i in range(18):
        x0=-59.+118.*i/18
        x1=-59.+118.*(i+1)/18
        z0=112.+sqrt(max(0.,59**2-x0**2))
        z1=112.+sqrt(max(0.,59**2-x1**2))
        lo=148. if abs((x0+x1)/2)>17 else 174.
        if min(z0,z1)>lo+.2:
            oven.prism('Soot',[(cx+x0,749,lo),(cx+x1,749,lo),(cx+x1,749,z1),(cx+x0,749,z0)],(0,10,0))
    # Refractory breeching through the stone throat; separate cheeks, sill and
    # lintel keep the full bore open all the way to the upright chimney.
    for side in (-1,1):
        x=cx+side*20.
        oven.box('Hearth',x-3,x+3,747,791,147,180,.45)
    oven.box('Hearth',cx-17,cx+17,750,791,145,150,.5)
    oven.box('Hearth',cx-21,cx+21,748,793,177,183,.5)
    # Iron keeper and a removable oven door propped against its own plinth.
    oven.box('Iron',cx+59,cx+78,605,611,104,109,.6)
    oven.prism('Iron',[(cx-47,658,1),(cx-47,701,1),(cx-47,701,29),
                       (cx-47,693,39),(cx-47,666,39),(cx-47,658,29)],(2.2,0,0))


def models():
    names=('HouseShell','TimberFrame','ShopJoinery','Roof','Floors','Stair','Oven','Flashing',
           'WindowPintles','CasementLeft','CasementRight')
    allparts={name:Mesh() for name in names}
    wall(allparts['HouseShell'],allparts['TimberFrame'],allparts['ShopJoinery'])
    roof_roof(allparts['Roof'],allparts['TimberFrame'],allparts['Flashing'])
    floor_and_stair(allparts['Floors'],allparts['TimberFrame'],allparts['Stair'])
    bakery_oven(allparts['Oven'])
    casement_windows(allparts['WindowPintles'],allparts['CasementLeft'],allparts['CasementRight'])
    return allparts
