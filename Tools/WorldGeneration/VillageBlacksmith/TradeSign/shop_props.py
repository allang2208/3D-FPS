"""Packing bay for a wheel awaiting repair, and a small floor-standing tong rack."""
import math
import random
from mathutils import Vector
from forms import bar,sweep,ring

def wheel(m):
    tilt=math.radians(14);co,si=math.cos(tilt),math.sin(tilt)
    origin=Vector((17,40.6,42*co+3.1*si))
    axis=Vector((0,co,si))
    def pt(r,t,depth=0):
        return origin+Vector((math.cos(t)*r,-math.sin(t)*r*si,math.sin(t)*r*co))+axis*depth
    # Six replaceable wooden felloes, enclosed by one continuous iron tyre.
    for part in range(6):
        count=(10,7,4)[m.level]
        angles=[(part+(j/count)*.986+.007)*math.tau/6 for j in range(count+1)]
        sweep(m,[pt(37.95,t) for t in angles],(3.28,3.04),'Oak',axis,box=True)
    count=(72,48,30)[m.level]
    angles=[i/count*math.tau for i in range(count)]
    sweep(m,[pt(41.40,t) for t in angles],(3.10,.60),'Iron',axis,True,True)
    # A narrow worn lane on the tread sits inside the tyre's bevelled shoulders.
    sweep(m,[pt(41.93,t,.32) for t in angles],(1.08,.085),'Rubbed',axis,True,True)
    for j in range(10):
        t=(j+.17)*math.tau/10
        sweep(m,[pt(r,t,z) for r,z in ((6.,.5),(11.,.3),(23.,.05),(31.,-.08),(35.7,0))],
              [(2.35,2.15),(2.11,2.40),(1.43,1.72),(1.65,1.56),(1.78,1.39)],'Sawn',axis,box=True)
    # Turned nave with a visible through-bore and dark compression collars.
    count=(32,22,14)[m.level]
    sections=[(-9.,3.0),(-9.,6.5),(-7.8,7.6),(-4.,8.1),(0,8.6),(5,7.9),
              (8.8,7.0),(10.,6.3),(10.,3.),(-9.,3.)]
    rows=[]
    for depth,r in sections:
        rows.append(m.vertices([pt(r,math.tau*i/count,depth) for i in range(count)]))
    for j in range(len(rows)-1):
        mat='Endgrain' if j in (0,7) else 'Oak'
        for i in range(count):
            k=(i+1)%count
            ids=[rows[j]+i,rows[j]+k,rows[j+1]+k,rows[j+1]+i]
            if j in (0,7):
                uv=[(.5+sections[h][1]*math.cos(math.tau*t/count)/22,
                     .5+sections[h][1]*math.sin(math.tau*t/count)/22) for h,t in ((j,i),(j,k),(j+1,k),(j+1,i))]
            else:
                uv=[(i/count,sections[j][0]/46),((i+1)/count,sections[j][0]/46),
                    ((i+1)/count,sections[j+1][0]/46),(i/count,sections[j+1][0]/46)]
            m.face(ids[::-1],uv[::-1],mat,j not in (0,7))
    for depth,r in ((-6.5,7.8),(6.5,7.66)):
        sweep(m,[pt(r,t,depth) for t in angles],(1.16,.42),'Iron',axis,True,True)

def packing(m):
    rng=random.Random(331)
    def crate(cx,cy,bottom,w,d,h,yaw,open_top):
        a=math.radians(yaw)
        def p(x,y,z):return (cx+math.cos(a)*x-math.sin(a)*y,cy+math.sin(a)*x+math.cos(a)*y,bottom+z)
        rows=4
        for i in range(rows):
            height=(h-3)/rows
            z=2.0+(i+.5)*height
            for side in (-1,1):
                m.board(rng,p(0,side*(d/2-1.5),z),w-1,2.65,height-.36,yaw,'Sawn',wane=.25)
                m.board(rng,p(side*(w/2-1.5),0,z),d-5.8,2.65,height-.36,yaw+90,'Oak')
        for side in (-1,1):
            for end in (-1,1):
                x=end*(w/2-8)
                bar(m,p(x,side*(d/2+.15),1),p(x,side*(d/2+.15),h),(3.0,1.45),'Oak',(math.cos(a),math.sin(a),0),True)
                if m.level<2:
                    for z in (5.5,h-5):
                        bar(m,p(x,side*(d/2+1.35),z),p(x,side*(d/2+1.95),z),
                            (.59,.59),'Iron',(math.cos(a),math.sin(a),0))
        for j in range(5):
            y=(j-2)*(d-5)/5
            m.board(rng,p(0,y,2.15 if open_top else h-1.3),w-4.9,(d-5)/5-.27,2.55,yaw,'Sawn',wane=.22,check=j==0)
        for x in (-w*.32,w*.32):
            m.board(rng,p(x,0,1.1),d,6.2,2.2,yaw+90,'Oak')
    crate(0,0,0,91,54,44,0,False)
    crate(11,3.5,44,62,43,37,-3,True)
    # Old packing battens within the open top crate leave the side slats and bottom visible.
    for j,(x,y,z,a) in enumerate([(-2,-3,48,5),(1,2,51,13),(6,-4,54,-8)]):
        m.board(rng,(x+11,y+3.5,z),44-j*2,8.2,2.7,a,'Oak' if j==0 else 'Sawn',wane=.58,check=True)
    wheel(m)

def tong_rack(m):
    rng=random.Random(824)
    for x in (-30.5,30.5):
        m.board(rng,(x,0,2.7),33,7.0,5.4,90,'Oak')
        bar(m,(x,0,4.9),(x,0,85),(3.1,3.0),'Oak',flat=True)
    m.board(rng,(0,0,18),63,4.0,5.0,0,'Oak')
    m.board(rng,(0,0,78),68,4.5,8.4,0,'Oak')
    for x,reach,jaw,hang in ((-19,43,7.4,-2.),(-1.5,51,9.2,1.6),(18,39,5.6,-1.)):
        # Each hook carries the jaws; both reins clear the lower tie and floor.
        hook=[(x,-1.7,78),(x,-6.,77),(x,-7.3,78),(x,-7.2,80.6)]
        sweep(m,hook,(.65,.65),'Iron',(1,0,0))
        pivot_z=78.8-jaw
        for side in (-1,1):
            y=-5.8+side*.63
            cheek=[(x+side*3.1,y,78.6),(x+side*1.05,y,77.2),(x+side*3.2,y,pivot_z+3.8),
                   (x,y,pivot_z),(x-side*1.9,y,pivot_z-5),(x-side*3.2+hang*.4,y,pivot_z-reach*.6)]
            sweep(m,cheek,[(1.13,.52),(.97,.56),(1.12,.58),(1.47,.63),(1.04,.58),(.73,.62)],'Iron',(0,1,0))
            grip=[cheek[-1],(x-side*3.65+hang*.76,y-.5,pivot_z-reach*.8),
                  (x-side*4.5+hang,y-.25,pivot_z-reach)]
            sweep(m,grip,[(.73,.62),(.72,.69),(.81,.72)],'Rubbed',(0,1,0))
        bar(m,(x,-7.45,pivot_z),(x,-4.1,pivot_z),(1.22,1.22),'Rubbed',(1,0,0))
