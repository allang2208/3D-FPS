"""Tool-specific chip fields, with each independent piece seated on the actual deck."""
import json
import math
import random
from collections import defaultdict
from layout import PLACEMENTS

class Deck:
    def __init__(self, path):
        self.bins=defaultdict(list)
        for a,b,c in json.loads(path.read_text()):
            ax,ay,az=a
            bx,by,bz=(b[i]-a[i] for i in range(3))
            cx,cy,cz=(c[i]-a[i] for i in range(3))
            det=bx*cy-by*cx
            if abs(det)<1.e-6: continue
            row=(ax,ay,az,bx,by,bz,cx,cy,cz,det)
            for x in range(math.floor(min(ax,b[0],c[0])/7),math.floor(max(ax,b[0],c[0])/7)+1):
                for y in range(math.floor(min(ay,b[1],c[1])/7),math.floor(max(ay,b[1],c[1])/7)+1):
                    self.bins[x,y].append(row)

    def height(self,x,y):
        height=None
        for ax,ay,az,bx,by,bz,cx,cy,cz,det in self.bins.get((math.floor(x/7),math.floor(y/7)),()):
            dx,dy=x-ax,y-ay
            s,t=(dx*cy-dy*cx)/det,(dy*bx-dx*by)/det
            if min(s,t)>=-1.e-6 and s+t<=1.000001:
                z=az+s*bz+t*cz
                if height is None or z>height: height=z
        return height

def scatter(mesh,key,deck):
    x0,y0,_=PLACEMENTS[key][0]
    rng=random.Random({'BenchCurls':51127,'SawSlivers':8819,'HewingChips':3021}[key])
    def seat(points):
        if key=='HewingChips':
            lift=-min(p[2] for p in points)
        else:
            # Rigid chips touch the highest supporting point of their own skin,
            # preserving opened spiral interiors across seams between floorboards.
            support=[]
            for x,y,z in points:
                top=deck.height(x0+x,y0+y)
                if top is not None: support.append(top-z)
            if not support: return [(x,y,z-3) for x,y,z in points]
            lift=max(support)
        return [(x,y,z+lift+.012) for x,y,z in points]

    # Dense drop zones below the tool, thinning toward a few isolated pieces.
    settings={
        'BenchCurls':[(1,16,20,27,24),(1,-25,15,21,12),(-7,-55,12,15,5)],
        'SawSlivers':[(3,-13,18,20,23),(-8,21,12,16,13)],
        'HewingChips':[(24,-11,22,17,22),(-28,9,18,14,15),(-7,-32,14,12,6)],
    }
    occupied=[]
    for cx,cy,rx,ry,count in settings[key]:
        for index in range(count):
            kind=rng.random()
            curled=key=='BenchCurls' and (kind<.72 or index<2)
            if curled:
                radius=rng.uniform(.9,2.7)*(1.14 if index<2 else 1.)
                width=rng.uniform(1.05,3.25)
                travel=rng.uniform(2.7,8.7)
                turns=rng.choice((rng.uniform(.48,.91),rng.uniform(1.02,1.75),rng.uniform(1.72,2.18)))
                spacing=max(radius*.92,width*.9)
            else:
                length=rng.uniform(2.2,9.4) if key!='HewingChips' else rng.uniform(4.7,15.2)
                width=length*rng.uniform(.17,.37) if key=='HewingChips' else rng.uniform(.28,1.5)
                thick=width*rng.uniform(.19,.52)
                spacing=max(.65,width*.66)
            # Keep centers apart to prevent several ribbons passing through one another.
            for attempt in range(50):
                angle=rng.uniform(0,math.tau)
                k=rng.random()**.56
                x=cx+rx*k*math.cos(angle)
                y=cy+ry*k*math.sin(angle)
                if all((x-u)**2+(y-v)**2>(spacing+s)**2 for u,v,s in occupied): break
            else: continue
            occupied.append((x,y,spacing))
            heading=rng.gauss(-1.12,.75) if key!='HewingChips' else math.atan2(y-32,x)+rng.uniform(-.8,.8)
            phase=rng.uniform(0,math.tau)
            hand=rng.choice((-1,1))
            grade=rng.random()
            if mesh.level and not curled and index%((2,4)[mesh.level-1])!=0: continue
            if mesh.level==2 and curled and index>1 and grade<.33: continue
            if curled:
                mesh.ribbon((x,y),heading,turns,radius,width,travel,phase,hand,seat)
            else:
                finish='Bark' if key=='HewingChips' and grade<.17 else ('Peel' if key=='BenchCurls' else 'Sawn')
                mesh.splinter((x,y),heading,length,width,thick,finish,phase,seat)
