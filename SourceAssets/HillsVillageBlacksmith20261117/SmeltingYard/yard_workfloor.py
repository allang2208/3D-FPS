"""Loose work material is concentrated where it falls, with the walking aisle between deposits."""
import math
import random
import re
from pathlib import Path
from yard_sites import BAY_Y, bay

def dress_floor(poly,beam):
    root=Path(__file__).resolve().parents[3]
    grid_src=(root/'Source/FPSGAME/WorldGeneration/TemperateVillageGroundData.inl').read_text(encoding='utf8')
    source=grid_src.split('Relief[Rows][Columns]={',1)[1].split('};',1)[0]
    grid=[list(map(int,row.split(','))) for row in re.findall(r'\{([-0-9,]+)\}',source)]
    def elevation(x,y):
        x+=.5*(len(grid[0])-1)-43.9
        y+=.5*(len(grid)-1)-9.
        i,j=math.floor(x),math.floor(y)
        u,v=x-i,y-j
        return .01*((1-v)*((1-u)*grid[j][i]+u*grid[j][i+1])+v*((1-u)*grid[j+1][i]+u*grid[j+1][i+1]))
    origin=elevation(0,0)
    def ground(x,y):
        return elevation(x,y)-origin
    rng=random.Random(423791)

    def chip(name,x,y,r,ry,h,material,base=None):
        n=rng.randrange(5,9)
        angle=rng.random()*math.tau
        outline=[(math.cos(angle+k*math.tau/n)*r*rng.uniform(.72,1.15),
                  math.sin(angle+k*math.tau/n)*ry*rng.uniform(.76,1.16)) for k in range(n)]
        z=ground(x,y)-.009 if base is None else base
        vertices=[(x+a,y+b,z) for a,b in outline]
        vertices += [(x+a*.93,y+b*.93,z+h*rng.uniform(.38,.68)) for a,b in outline]
        vertices += [(x+a*.55+.13*r,y+b*.51,z+h*rng.uniform(.75,1.0)) for a,b in outline]
        faces=[tuple(reversed(range(n))),tuple(range(2*n,3*n))]
        for layer in (0,n):
            for k in range(n):
                j=(k+1)%n
                faces.append((layer+k,layer+j,layer+n+j,layer+n+k))
        poly(name,vertices,faces,[material],[0]*len(faces))

    for y in BAY_Y:
        x,_=bay(y)
        # A few worn flat fragments mark the tap side; charcoal and spalled brick collect at the flanks.
        for dx,dy,r in [(-1.02,.09,.25),(-1.34,-.13,.22),(-1.05,-.34,.16)]:
            chip('Embedded hearth flag',x+dx,y+dy,r,r*.72,.030,'Stone')
        for k in range(31):
            side=1 if k%4 else -1
            xx=x+rng.uniform(-1.22,.29)
            yy=y+side*rng.uniform(.53,.78)+.08*math.sin(4*xx)
            r=rng.uniform(.014,.074)
            chip('Quenched clinker',xx,yy,r,r*rng.uniform(.53,.85),r*.70,
                 ('Clinker','Coal','Brick')[k%3])
    for px,py,rx,ry,n,slot in [(-1.82,.25,.16,2.75,32,'Stone'),(.78,-2.19,1.24,.23,21,'Bark'),
                               (4.45,-2.01,.64,.13,15,'Clinker'),(3.18,2.78,.38,.47,13,'Stone')]:
        for _ in range(n):
            xx,yy=px+rx*rng.uniform(-1,1),py+ry*rng.uniform(-1,1)
            r=rng.uniform(.016,.067)
            chip('Eave grit and floor sweepings',xx,yy,r,r*.50,r*.60,slot)

    # Rolled rim, tapered sheet, recessed inner floor and a wire bail on a half-full ash pail.
    x,y=5.84,2.58
    z=ground(x,y)
    n=28
    rings=[(.180,.012),(.201,.049),(.258,.408),(.267,.415),(.266,.429),
           (.251,.433),(.246,.411),(.179,.056)]
    verts=[]
    for radius,hh in rings:
        for j in range(n):
            a=j*math.tau/n
            dent=1.-.12*math.exp(-((j-8)/2.1)**2)
            verts.append((x+radius*math.cos(a)*dent,y+radius*math.sin(a),z+hh))
    faces=[tuple(reversed(range(n))),tuple(range(7*n,8*n))]
    for k in range(len(rings)-1):
        for j in range(n):
            i=k*n+j
            faces.append((i,k*n+(j+1)%n,(k+1)*n+(j+1)%n,i+n))
    poly('Battered ash pail',verts,faces,['Iron'],[0]*len(faces))
    prev=None
    for j in range(13):
        a=math.pi*j/12.
        end=(x+.255*math.cos(a),y+.17*math.sin(a),z+.36+.19*math.sin(a))
        if prev: beam('Pail wire bail',prev,end,.012,.012,'Iron')
        prev=end
    chip('Fine ash inside pail',x,y,.215,.212,.033,'Clinker',z+.24)
    for j in range(14):
        a=rng.random()*math.tau
        rr=.15*math.sqrt(rng.random())
        chip('Collected cinder',x+rr*math.cos(a),y+rr*math.sin(a),.042,.034,.032,'Coal',z+.264)

    # Crooked clinker rake laid on the fuel-bin runners; narrow teeth taper into the sweepings.
    beam('Oak rake shaft',(.99,-2.04,.07),(-.39,-2.43,.59),.038,.043,'Oak')
    beam('Iron rake crosspiece',(.89,-1.90,.065),(1.10,-2.21,.065),.024,.032,'Iron')
    for k in range(6):
        u=.89+.042*k
        v=-1.90-.062*k
        beam('Rake tooth',(u,v,.068),(u+.091,v+.056,.012),.014,.013,'Iron')
