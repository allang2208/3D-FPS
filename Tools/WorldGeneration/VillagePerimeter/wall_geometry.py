"""Author two perimeter styles from the accepted chapel fieldstone construction.

UE centimetres: +X along a 300 cm module, +Z up; ground is z=0.
Triangle order follows the same static-mesh buffer convention as the shrine plinth.
No rendering, gameplay or inspection is performed by this authoring module.
"""
import json
import math
import random
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'SourceAssets/HillsVillagePerimeter20261117'
MATERIALS=('Mortar','YardField','YardSlate','YardCap')

class Mesh:
    def __init__(self, seed):
        self.rng=random.Random(seed)
        self.groups={name:{key:[] for key in ('vertices','normals','uv0','uv1','triangles')} for name in MATERIALS}
        self.boxes=[]
        self.stones=0

    def triangle(self,a,b,c,material,offset=(0.,0.)):
        ab=[b[i]-a[i] for i in range(3)];ac=[c[i]-a[i] for i in range(3)]
        n=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
        length=math.sqrt(sum(v*v for v in n))
        if length<1e-8:raise ValueError('Cannot author a zero-area stone face')
        n=[v/length for v in n]
        axis=max(range(3),key=lambda i:abs(n[i]))
        axes=((1,2),(0,2),(0,1))[axis]
        data=self.groups[material];start=len(data['vertices'])
        for p in (a,b,c):
            data['vertices'].append(p);data['normals'].append(n)
            data['uv0'].append([p[axes[0]]/100.+offset[0],p[axes[1]]/100.+offset[1]])
            data['uv1'].append([max(0.,p[2])/170.,0.])
        data['triangles'].append([start,start+2,start+1])

    def solid(self,rings,material,offset=(0.,0.)):
        count=len(rings[0])
        for low,high in zip(rings,rings[1:]):
            for i in range(count):
                j=(i+1)%count
                self.triangle(low[i],low[j],high[j],material,offset)
                self.triangle(low[i],high[j],high[i],material,offset)
        for points,reverse in ((rings[0],True),(rings[-1],False)):
            center=[sum(p[k] for p in points)/count for k in range(3)]
            for i in range(count):
                a,b=points[i],points[(i+1)%count]
                self.triangle(center,b,a,material,offset) if reverse else self.triangle(center,a,b,material,offset)

    def block(self,x0,x1,y0,y1,z0,z1):
        self.solid([[(x0,y0,z),(x1,y0,z),(x1,y1,z),(x0,y1,z)] for z in (z0,z1)],'Mortar')

    def stone(self,x0,x1,y0,y1,low,high,slot,angle=0.):
        # Same battered, split 11-sided stones used by SM_ChapelYardWallA/B.
        r=self.rng;cx,cy=(x0+x1)*.5,(y0+y1)*.5;rx,ry=(x1-x0)*.5,(y1-y0)*.5
        outline=[(-.64,-1),(.10,-1),(.74,-.96),(1,-.57),(1,.26),(.76,.93),
                 (.16,1),(-.68,.96),(-.98,.6),(-1,-.10),(-.95,-.68)]
        profile=[(x*r.uniform(.91,1.),y*r.uniform(.90,1.)) for x,y in outline]
        tilt=r.uniform(-.09,.09)*min(x1-x0,45);ca,sa=math.cos(angle),math.sin(angle)
        rings=[]
        for factor,t in ((.87,0.),(.99,.15),(1.,.74),(.87,1.)):
            ring=[]
            for x,y in profile:
                f=factor*r.uniform(.94,1.);px,py=rx*x*f,ry*y*f
                ring.append([cx+px*ca-py*sa,cy+px*sa+py*ca,
                    low+(high-low)*(t+r.uniform(-.035,.035))+tilt*x])
            rings.append(ring)
        self.solid(rings,slot,(r.random(),r.random()));self.stones+=1

    def collision(self,x0,x1,y0,y1,z0,z1):
        self.boxes.append({'center':[(x0+x1)*.5,(y0+y1)*.5,(z0+z1)*.5],
                           'size':[x1-x0,y1-y0,z1-z0]})

    def chip(self,x,y,width,depth,height):
        # Low, partly buried shards soften the footprint without creating a raised skirt.
        r=self.rng;angle=r.uniform(-math.pi,math.pi);ca,sa=math.cos(angle),math.sin(angle)
        outline=[(math.cos(i*math.tau/6)*r.uniform(.7,1.),math.sin(i*math.tau/6)*r.uniform(.7,1.)) for i in range(6)]
        rings=[]
        for factor,z in ((.8,-4.),(1.,height*.3),(.45,height)):
            rings.append([[x+(px*width*ca-py*depth*sa)*factor*.5,
                           y+(px*width*sa+py*depth*ca)*factor*.5,z+r.uniform(-.6,.6)] for px,py in outline])
        self.solid(rings,'YardSlate' if r.random()<.4 else 'YardField',(r.random(),r.random()))
        self.stones+=1

    def foot_chips(self,repaired):
        for side in (-1,1):
            for _ in range(8 if repaired else 12):
                self.chip(self.rng.uniform(-145,145),side*self.rng.uniform(30,65),
                          self.rng.uniform(6,19),self.rng.uniform(4,12),self.rng.uniform(2,6))

    def data(self):
        return {'groups':self.groups,'collision_boxes':self.boxes,'stones':self.stones,
                'triangles':sum(len(v['triangles']) for v in self.groups.values())}

def wall(seed,profile=None):
    mesh=Mesh(seed);rng=mesh.rng
    repaired=profile is None
    if repaired:
        mesh.block(-150,150,-20,20,-35,151)
        mesh.collision(-150,150,-29,29,-32,166)
    else:
        for i,height in enumerate(profile):
            if height<=0:continue
            x0=-150+i*50;x1=x0+50
            # Exposed broken cores are rubble masonry, not a staircase of mortar boxes.
            for low in range(-35,max(-34,height-12),25):
                mesh.stone(x0-.5,x1+.5,-21,21,low,min(low+28,height-10),'YardField')
            mesh.collision(x0,x1,-28,28,-32,height)
    for side in (-1,1):
        for row,(low,high) in enumerate(((-36,14),(12,37),(35,61),(59,85),(83,109),(107,132),(130,153))):
            count=6 if row%2==0 else 7
            cuts=[-150]+[-150+300*i/count+rng.uniform(-9,9) for i in range(1,count)]+[150]
            for a,b in zip(cuts,cuts[1:]):
                top=high
                if profile is not None:
                    start=max(0,min(5,int((a+150)/50)));end=max(0,min(5,int((b+149.999)/50)))
                    top=min(top,min(profile[start:end+1]))
                    if top<=low+7:continue
                y0,y1=sorted((side*11.,side*rng.uniform(29,32)))
                slot='YardSlate' if rng.random()<.24 else 'YardField'
                mesh.stone(a-.4,b+.4,y0,y1,low,top,slot)
    if repaired:
        cuts=[-150,-101,-49,2,54,103,150]
        for a,b in zip(cuts,cuts[1:]):mesh.stone(a-.7,b+.7,-33,33,149,166+rng.uniform(-1.5,1.5),'YardCap')
    else:
        # Broken tops are exposed full-depth stones, rather than bare mortar boxes.
        for i,height in enumerate(profile):
            if height>0:mesh.stone(-150+i*50,-100+i*50,-29,29,max(-12,height-19),height,'YardField')
    mesh.foot_chips(repaired)
    return mesh.data()

def pier(seed,repaired):
    mesh=Mesh(seed);rng=mesh.rng;height=198 if repaired else 127
    mesh.block(-26,26,-26,26,-35,height-14)
    for low in range(-35,height-18,27):
        high=min(height-12,low+29);joint=rng.uniform(-6,6)
        for a,b in ((-35,joint+.5),(joint-.5,35)):
            box=(a,b,-35,35) if (low//27)%2 else (-35,35,a,b)
            mesh.stone(*box,low,high,'YardField' if rng.random()>.25 else 'YardSlate')
    if repaired:mesh.stone(-41,41,-41,41,height-19,height,'YardCap')
    else:
        mesh.stone(-37,4,-37,37,height-20,height+2,'YardField')
        mesh.stone(2,36,-35,36,height-20,height-7,'YardSlate')
    for _ in range(14):
        angle=rng.uniform(-math.pi,math.pi);radius=rng.uniform(36,56)
        mesh.chip(math.cos(angle)*radius,math.sin(angle)*radius,rng.uniform(7,17),rng.uniform(5,11),rng.uniform(2,5))
    mesh.collision(-36,36,-36,36,-32,height)
    return mesh.data()

def rubble(seed):
    mesh=Mesh(seed);rng=mesh.rng
    for i in range(13):
        x=rng.uniform(-108,108);y=rng.uniform(-45,45);w=rng.uniform(18,40);d=rng.uniform(16,30)
        mesh.stone(x-w*.5,x+w*.5,y-d*.5,y+d*.5,-9,rng.uniform(5,10 if i%3==0 else 19),
                   'YardSlate' if i%4==0 else 'YardField',rng.uniform(-math.pi,math.pi))
    for _ in range(20):
        mesh.chip(rng.uniform(-130,130),rng.uniform(-62,62),rng.uniform(5,17),rng.uniform(4,11),rng.uniform(2,6))
    return mesh.data()

def build():
    return {'RepairedA':wall(6431),'RepairedB':wall(2287),
            'RuinedA':wall(9063,[135,145,123,96,63,36]),
            'RuinedB':wall(7921,[34,58,84,71,108,137]),
            'RuinedC':wall(1643,[121,94,53,23,0,0]),
            'RuinedD':wall(5871,[0,0,32,66,99,131]),
            'PierRepaired':pier(815,True),'PierRuined':pier(816,False),
            'RubbleA':rubble(4117),'RubbleB':rubble(7139)}

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    data=build()
    (OUT/'wall-mesh-source.json').write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')
    summary={name:{'stones':m['stones'],'triangles':m['triangles'],'collision_boxes':len(m['collision_boxes'])} for name,m in data.items()}
    (OUT/'geometry-production.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary))
