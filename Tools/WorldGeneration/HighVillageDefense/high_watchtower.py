"""Player-built square tower. UE centimetres; the twin wall-walk portals face +/-X."""
import math
import random
import sys
from pathlib import Path

import source_mesh
from chapel_gatehouse import CAP, FLOORBOARD, FOOTING, IRON, OAK, PAVING, STONE, Kit, level_guard, steps

HALF, INNER = 460., 402.
LEVELS = (0., 360., 820., 1320., 1820.)
ROOF = LEVELS[-1]
GROUND_FLOOR = 32.


class Tower(Kit):
    # The facade is authored looking along +Y. Quarter turns preserve normals
    # and world-space stone density on all elevations.
    side = 0

    def point(self, point):
        x,y,z = point
        return ((x,y,z),(-y,x,z),(-x,-y,z),(y,-x,z))[self.side]

    def triangle(self,a,b,c,material,offset=(0.,0.)):
        super().triangle(self.point(a),self.point(b),self.point(c),material,offset)

    def collision(self,x0,x1,y0,y1,z0,z1):
        a,b=self.point((x0,y0,z0)),self.point((x1,y1,z1))
        super().collision(min(a[0],b[0]),max(a[0],b[0]),min(a[1],b[1]),max(a[1],b[1]),z0,z1)


def dressed_opening(m,cx,sill,door):
    """Full-depth arched reveal with an inward splay and an unobstructed sill."""
    outer_r,inner_r,cut=(94.,101.,115.) if door else (30.,57.,70.)
    spring=sill+(185. if door else 92.)
    rise=64. if door else 35.
    head=spring+rise+19.
    angles=[math.pi*i/12. for i in range(13)]
    def opening(y,r):
        return [(cx-r,y,sill),(cx+r,y,sill),
                *[(cx+r*math.cos(t),y,spring+rise*math.sin(t)) for t in angles]]
    def border(y):
        return [(cx-cut,y,sill-10.),(cx+cut,y,sill-10.),
                *[(cx+cut*math.cos(t),y,head) for t in angles]]
    # The edge of a docking portal lies on the same plane as the wall end.
    face=-HALF if door else -HALF-5.
    inside=-INNER
    m.rim([border(face),opening(face,outer_r+3.),opening(-HALF+6.,outer_r),
           opening(inside,inner_r),border(inside)],CAP)
    # Each voussoir has a separate bevel and mortar joint. The shallow trim
    # lies outside the structural reveal and leaves the walking sill flush.
    for i in range(11):
        a,b=math.pi*i/11.+.004,math.pi*(i+1)/11.-.004
        extra=15. if i==5 else 11.
        profile=[(face+.8,1.),(face-3.,1.),(face-5.,3.),(face-5.,extra-2.),
                 (face-3.,extra),(face+.8,extra)]
        m.solid([[(cx+(outer_r+3.+r)*math.cos(t),y,spring+(rise+r)*math.sin(t))
                  for y,r in profile] for t in (a,b)],CAP)
    if not door:
        m.coping(cx-outer_r-14.,cx+outer_r+14.,face-9.,face+1.,sill-15.,sill-5.)
    m.collision(cx-cut,cx+cut,face,inside,sill-10.,sill)
    # Simple movement collision follows two bands of the splay. Fine traces
    # use the rendered reveal. Keep the boxes outside the clear opening.
    for j in range(2):
        y0=face+(inside-face)*j/2.
        y1=face+(inside-face)*(j+1)/2.
        r=outer_r+(inner_r-outer_r)*(j+1)/2.
        m.collision(cx-cut,cx-r,y0,y1,sill,head)
        m.collision(cx+r,cx+cut,y0,y1,sill,head)
        arch=opening(y1,r)[2::2]
        for (b,_,zb),(a,_,za) in zip(arch,arch[1:]):
            m.collision(a,b,y0,y1,max(za,zb),head)
    return cx-cut,cx+cut,sill-10.,head


def courtyard_leaf(m):
    """A single arched oak leaf standing open behind the courtyard jamb."""
    # Hang the leaf on the level landing, immediately beyond the last rise.
    hinge_y=INNER-28.
    width=182.
    m.block(103.,123.,hinge_y-5.,INNER+1.,GROUND_FLOOR,187.,CAP)
    def head(distance):
        return 183.+61.*math.sqrt(max(0.,1.-(2.*distance/width-1.)**2))
    for board in range(9):
        near=width*board/9.+.2
        far=width*(board+1)/9.-.2
        outline=[(98.,far),(105.,far),(105.,near),(98.,near)]
        m.solid([[(x,hinge_y-d,z(d)) for x,d in outline]
                 for z in (lambda d:GROUND_FLOOR+3.,head)],OAK)
    m.collision(98.,105.,hinge_y-width,hinge_y,GROUND_FLOOR+3.,183.)
    for z in (53.,148.):
        m.block(95.,98.,hinge_y-width+14.,hinge_y,z,z+7.,IRON,False)
        m.block(94.,103.,hinge_y-2.,INNER+1.,z-3.,z+10.,IRON,False)
    m.block(93.,98.,hinge_y-width+16.,hinge_y-width+27.,95.,109.,IRON,False)


def facade(m,side):
    m.side=side
    # The long elevations own the corners, so interior faces never overlap.
    half=HALF if side%2==0 else INNER
    holes=[]
    if side==2:
        holes.append(dressed_opening(m,0.,0.,True))
    if side%2:
        holes.append(dressed_opening(m,0.,LEVELS[1],True))
    for level in LEVELS[1:-1]:
        centres=(-183.,183.) if side%2==0 else (0.,)
        if side%2 and level==LEVELS[1]:
            continue
        for centre in centres:
            holes.append(dressed_opening(m,centre,level+93.,False))
    xs=sorted({-half,half,*(x for a,b,_,_ in holes for x in (a,b))})
    for a,b in zip(xs,xs[1:]):
        low=-24.
        for bottom,top in sorted((z,t) for l,r,z,t in holes if l<=a and b<=r):
            if bottom>low:
                m.block(a,b,-HALF,-INNER,low,bottom)
            low=top
        m.block(a,b,-HALF,-INNER,low,ROOF-28.)

    # Dress each corner once, with alternating long and short returns.
    for row in range(34):
        base=row*51.
        length=66. if row%2==0 else 45.
        facing=FOOTING if row==0 else CAP
        m.coping(-HALF-3.,-HALF+length,-HALF-4.,-HALF+21.,base+1.,base+50.,facing)
        m.coping(-HALF-4.,-HALF+20.,-HALF+21.,-HALF+95.-length*.45,base+1.,base+50.,facing)
    # Splayed footings frame the courtyard door. The side sockets stay flush.
    for a,b in ((-HALF+8.,-122.),(122.,HALF-8.)) if side==2 else ((-HALF+8.,HALF-8.),):
        projection=0. if side%2 else 13.
        m.solid([[(a,-HALF-p,z),(b,-HALF-p,z),(b,-HALF+5.,z),(a,-HALF+5.,z)]
                 for z,p in ((-24.,projection+1.),(24.,projection+1.),(104.,1.))],FOOTING)
    for x in range(-375,376,125):
        m.solid([[(x-w,-HALF-p,z),(x+w,-HALF-p,z),(x+w,-HALF+1.,z),(x-w,-HALF+1.,z)]
                 for w,p,z in ((12.,3.,ROOF-105.),(17.,15.,ROOF-85.),(21.,28.,ROOF-49.))],CAP)
    m.side=0


def deck(m,outside,hole,z,depth,material):
    x0,x1,y0,y1=hole
    def ring(a,b,c,d,h):
        return [(a,c,h),(b,c,h),(b,d,h),(a,d,h)]
    m.rim([ring(-outside,outside,-outside,outside,z),ring(x0,x1,y0,y1,z),
           ring(x0,x1,y0,y1,z-depth),ring(-outside,outside,-outside,outside,z-depth)],material)
    for a,b,c,d in ((-outside,outside,-outside,y0),(-outside,outside,y1,outside),
                    (-outside,x0,y0,y1),(x1,outside,y0,y1)):
        m.collision(a,b,c,d,z-depth,z)


def entrance_floor(m):
    # Three low rises inside the courtyard opening. The surrounding stone margin
    # carries the ends of the boards; the board joints have no collision edges.
    mouth=90.
    margin=24.
    field=INNER-margin
    bed=GROUND_FLOOR-6.
    rng=random.Random(4697)
    original_phase=m.phase

    def stone_course(x0,x1,y0,y1,bottom,top,count):
        along_x=x1-x0>=y1-y0
        start,end=(x0,x1) if along_x else (y0,y1)
        joints=[start]+[start+(end-start)*(i+rng.uniform(-.19,.19))/count for i in range(1,count)]+[end]
        for a,b in zip(joints,joints[1:]):
            bounds=(a+.18,b-.18,y0,y1) if along_x else (x0,x1,a+.18,b-.18)
            m.phase=(rng.random(),rng.random())
            m.coping(*bounds,bottom,top,FOOTING if top<GROUND_FLOOR else PAVING)
        m.collision(x0,x1,y0,y1,bottom,top)

    stone_course(-mouth,mouth,424.,HALF,-24.,10.5,3)
    stone_course(-mouth,mouth,382.,424.,-24.,21.,3)
    stone_course(-mouth,mouth,335.,382.,bed,GROUND_FLOOR,4)
    stone_course(-INNER,INNER,-INNER,-field,bed,GROUND_FLOOR,10)
    for left,right in ((-INNER,-field),(field,INNER)):
        stone_course(left,right,-field,INNER,bed,GROUND_FLOOR,9)
    for left,right in ((-field,-mouth),(mouth,field)):
        stone_course(left,right,field,INNER,bed,GROUND_FLOOR,3)
    for left,right,front,end in ((-INNER,-mouth,INNER,field),(-mouth,mouth,382.,335.),(mouth,INNER,INNER,field)):
        m.block(left,right,-INNER,front,-24.,bed,PAVING)
        x0,x1=max(left,-field),min(right,field)
        m.collision(x0,x1,-field,end,bed,GROUND_FLOOR)
        count=round((x1-x0)/21.)
        for i in range(count):
            a=x0+(x1-x0)*i/count+.13
            b=x0+(x1-x0)*(i+1)/count-.13
            joints=[-field]
            pos=-field+rng.uniform(95.,234.)
            while pos<end-75.:
                joints.append(pos)
                pos+=rng.uniform(171.,273.)
            joints.append(end)
            for lo,hi in zip(joints,joints[1:]):
                m.phase=(rng.random(),rng.random())
                # Grain follows +Y. Only the narrow top arris is hand-planed.
                def ring(z,inset):
                    return [(a+inset,lo+.16+inset,z),(b-inset,lo+.16+inset,z),
                            (b-inset,hi-.16-inset,z),(a+inset,hi-.16-inset,z)]
                m.solid([ring(bed,0.),ring(GROUND_FLOOR-.24,0.),ring(GROUND_FLOOR,.22)],FLOORBOARD)
    m.phase=original_phase


def stairs_and_floors(m):
    start,turn,edge=-205.,121.,251.
    entrance_floor(m)
    x=edge-9.
    for y in (-280.,-39.):
        m.block(x-7.,x+7.,y-7.,y+7.,GROUND_FLOOR,(LEVELS[-2]+ROOF)*.5-19.,OAK)
    for lower,upper in zip((GROUND_FLOOR,*LEVELS[1:]),LEVELS[1:]):
        half_rise=(upper-lower)*.5
        mid=lower+half_rise
        count=math.ceil(half_rise/17.)
        steps(m,start,turn,lower,half_rise,-289.,-169.,count)
        m.block(turn,edge,-289.,-30.,mid-19.,mid,OAK)
        steps(m,turn,start,mid,half_rise,-154.,-30.,count)
        if upper==ROOF:
            # Only the upper run emerges through the terrace. The return
            # landing below the closed deck has 222 cm clear headroom.
            deck(m,490.,(start,turn+6.,-160.,-24.),upper,28.,PAVING)
            level_guard(m,[(start+6.,-169.),(turn+15.,-169.),(turn+15.,-15.),(start+6.,-15.)],upper)
        else:
            deck(m,INNER,(start,edge,-289.,-30.),upper,19.,PAVING if upper==360. else OAK)
            level_guard(m,[(start+6.,-298.),(edge+9.,-298.),(edge+9.,-21.),(start+6.,-21.)],upper)
            for y in (104.,325.):
                m.block(-INNER,INNER,y-9.,y+9.,upper-43.,upper-19.,OAK)
        # The insert below the landing stays clear of both flights.
        m.block(turn+10.,edge-2.,-277.,-264.,mid-34.,mid-19.,OAK)
        m.block(turn+10.,edge-2.,-56.,-43.,mid-34.,mid-19.,OAK)


def crown(m):
    # The corner merlons have individual footing and cap stones. Side bands
    # stop at the corners so the top surfaces do not fight one another.
    for side in range(4):
        m.side=side
        m.coping(-460.,460.,-489.,-453.,ROOF-48.,ROOF-28.)
        length=490. if side%2==0 else 452.
        m.block(-length,length,-490.,-452.,ROOF,ROOF+47.)
        m.coping(-length,length,-492.,-448.,ROOF+46.,ROOF+55.)
        for x in (-320.,-160.,0.,160.,320.):
            m.block(x-38.,x+38.,-488.,-454.,ROOF+55.,ROOF+112.)
            m.coping(x-41.,x+41.,-491.,-451.,ROOF+112.,ROOF+122.)
        m.block(-488.,-426.,-488.,-426.,ROOF+55.,ROOF+124.)
        m.coping(-492.,-422.,-492.,-422.,ROOF+124.,ROOF+136.)
    m.side=0


if __name__=='__main__':
    source_mesh.OUT=Path(sys.argv[1])
    source_mesh.OUT.mkdir(parents=True,exist_ok=True)
    mesh=Tower(47231)
    for elevation in range(4):
        facade(mesh,elevation)
    courtyard_leaf(mesh)
    stairs_and_floors(mesh)
    crown(mesh)
    mesh.save('SM_HighWatchtower')
