"""Original village defence game props. Centimetres, +X forward. Paired carry grips run along X."""
from pathlib import Path
import sys
import numpy as np
from math import cos, sin, tau
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"GarrisonWorkshop"))
from author_workshop import Shop
from workshop_frontage import BRASS, IRON
import source_mesh
from chapel_gatehouse import spindle, pin

def ring(r,z,n,phase=0):
    return [(r*cos(i*tau/n+phase),r*sin(i*tau/n+phase),z) for i in range(n)]

def vessel(m,r,z,hand=False):
    shape=[(.25,0),(.42,.04),(.67,.19),(.88,.43),(.98,.70),(1,.86),(1.025,.89),
           (1.025,.94),(.995,.97),(.92,.94),(.92,.84),(.90,.71),(.80,.46),(.61,.25),(.35,.13),(.25,.12)]
    m.solid([ring(r*k,z+r*h,64) for k,h in shape],IRON)
    for h,rr in ((.69,.981),(.79,.999)):
        m.rim([ring(r*a,z+r*b,64) for a,b in ((rr-.025,h),(rr+.012,h),(rr+.012,h+.025),(rr-.025,h+.025))],IRON)
    for i in range(18 if not hand else 10):
        a=tau*(i+.5)/(18 if not hand else 10)
        pin(m,(r*.994*cos(a),r*.994*sin(a),z+r*.756),(r*.028*cos(a),r*.028*sin(a),0),r*.026,BRASS)
    for s in (-1,1):
        y=s*r
        for x in (-r*.45,r*.45):
            m.member((x,s*.80*r,z+.70*r),(x,y+s*.35*r,z+.90*r),r*.11,r*.10,IRON)
        grip=.079*r
        profile=([(0,2.35),(.08,2.70),(.16,3.0),(.22,3.065),(.78,3.065),(.84,3.0),(.92,2.70),(1,2.35)]
                 if hand else [(0,grip*.90),(.12,grip*1.08),(.18,grip),(.82,grip),(.88,grip*1.08),(1,grip*.90)])
        spindle(m,(-r*.48,s*r*1.35,z+.9*r),(r*.48,s*r*1.35,z+.9*r),
                profile,"SignOak",32 if hand else 16)

def station(m):
    # A staggered open-front stone brazier on a low plinth, topped by the riveted kettle.
    m.coping(-79,79,-77,77,0,10,"Footing")
    for row in range(3):
        for i in range(14):
            a=(i+(row%2)*.5)*tau/14
            if cos(a)>.74 and row<2:continue
            a0,a1=a-.209,a+.209
            def course(z,shrink):
                return [(r*cos(t),r*sin(t),z) for r,t in ((69-shrink,a0),(69-shrink,a1),(48+shrink,a1),(48+shrink,a0))]
            h=10+row*10
            m.solid([course(h,.7),course(h+1,0),course(h+9,0),course(h+10,.8)],"Footing")
    for y in range(-32,33,8):
        m.member((36,y,18),(63,y,35),3.3,3,IRON)
    for a in np.arange(4)*tau/4+tau/8:
        m.member((60*cos(a),60*sin(a),35),(43*cos(a),43*sin(a),62),9,10,IRON)
    vessel(m,63,35)
    m.collision(-61,61,-60,60,9,96)
    m.collision(-79,79,-77,77,0,10)

def fluid(m):
    n=64
    # Shared disc stores planar 0..1 UVs for the actual furnace pool shader.
    for i in range(n):
        a,b=i*tau/n,(i+1)*tau/n
        pts=((0,0,0),(cos(a)*50,sin(a)*50,0),(cos(b)*50,sin(b)*50,0))
        m.triangle(*pts,"Bronze")
        m.groups["Bronze"]["uv0"][-3:]=[(.5+x/100,.5+y/100) for x,y,_ in pts]

if __name__=="__main__":
    source_mesh.OUT=HERE
    for name,build in (("SM_OilHearth",station),("SM_OilHandPot",lambda m:vessel(m,14,-7,True)),("SM_OilSurface",fluid)):
        if "--hand-pot-only" in sys.argv and name!="SM_OilHandPot":continue
        mesh=Shop(9153);build(mesh);mesh.save(name)
