"""Side-blast hearth, from the stone plinth to the opening in the existing smoke duct."""
import math,random
from mathutils import Vector
from Workfloor.author import block,lump
from forms import bar,sweep

CX,CY=-23.,-5.
def deck_height(x,y):
    r=math.hypot((x-CX)/27,(y-CY)/21)
    if r<.58:return 76.8
    return min(82.5,76.8+(r-.58)*5.7/.42)

def face(m,pts,mat):
    base=m.vertices(pts)
    norm=(Vector(pts[1])-Vector(pts[0])).cross(Vector(pts[2])-Vector(pts[0]))
    axes=sorted(sorted(range(3),key=lambda i:abs(norm[i]))[:2])
    m.face([base+i for i in range(len(pts))],[(p[axes[0]]/72,p[axes[1]]/72) for p in pts],mat)

def shell(m,quad,thickness,mat):
    n=(Vector(quad[1])-Vector(quad[0])).cross(Vector(quad[2])-Vector(quad[0])).normalized()*thickness
    inner=[tuple(Vector(p)-n) for p in quad]
    face(m,quad,mat);face(m,inner[::-1],'Soot')
    for i in range(4):
        j=(i+1)%4;face(m,[quad[j],quad[i],inner[i],inner[j]],mat)

def body(m):
    rng=random.Random(582)
    # Mortar backing ends below the depressed hearth floor.
    block(m,(10,1,35.5),(119,97,71),'Stone',2.5)
    for course in range(5):
        z=7.2+14.4*course
        def course_facing(start,end):
            cuts=[start]
            s=start+(14 if course%2 else 27)
            while s<end-9:
                cuts.append(s+rng.uniform(-2,2));s+=rng.uniform(23,32)
            return list(zip(cuts,cuts[1:]+[end]))
        for y in (-49,51):
            for a,b in course_facing(-51,72):
                block(m,((a+b)/2,y,z),(b-a-.65,5.4,13.65),'Stone',1.1)
        for x in (-50,71):
            for a,b in course_facing(-47,49):
                block(m,(x,(a+b)/2,z),(4.8,b-a-.7,13.65),'Stone',1.1)
    # A continuous working surface. An elliptical fire hollow shares vertices around each course.
    n=(48,32,24)[m.level]
    rings=[[] for _ in range(4)]
    for i in range(n):
        a=i*math.tau/n;dx,dy=math.cos(a),math.sin(a)
        # Include a rectangular perimeter with four explicitly sampled corners.
        sx,sy=dx/max(abs(dx),abs(dy)),dy/max(abs(dx),abs(dy))
        outer=(8+69*sx,0+54*sy)
        for row,p in zip(rings,[(CX+dx*15.66,CY+dy*12.18,76.8),(CX+dx*27,CY+dy*21,82.5),
                                 (*outer,82.5),(*outer,71.0)]):row.append(p)
    face(m,rings[0],'Soot')
    for j,mat in enumerate(('Fireclay','Fireclay','Brick')):
        for i in range(n):
            k=(i+1)%n
            face(m,[rings[j][i],rings[j+1][i],rings[j+1][k],rings[j][k]],mat)
    # Side inlet meets the existing leather bellows nose. Open bore remains visible above the fire bed.
    path=[(-59,-6,65),(-55,-6,65.5),(-54,-6,70.8),(-54.0,-5.5,79.2),
          (-51.3,-5.2,84.1),(-47.,-5.,85.4),(-40.,-5.,85.4),(-34.,-5.,84.5)]
    radii=[5.3,5.45,5.,4.9,4.8,5.5,6.3,5.8]
    steps=(20,14,10)[m.level];outer=[];inner=[]
    for i,p in enumerate(path):
        axis=(Vector(path[min(i+1,len(path)-1)])-Vector(path[max(i-1,0)])).normalized()
        across=Vector((0,1,0));up=axis.cross(across).normalized();across=up.cross(axis).normalized()
        for dest,r in ((outer,radii[i]),(inner,radii[i]-1.4)):
            dest.append([tuple(Vector(p)+r*(math.cos(t*math.tau/steps)*across+math.sin(t*math.tau/steps)*up)) for t in range(steps)])
    for i in range(len(path)-1):
        for j in range(steps):
            k=(j+1)%steps
            face(m,[outer[i][j],outer[i][k],outer[i+1][k],outer[i+1][j]],'Fireclay' if i>=5 else 'Iron')
            face(m,[inner[i][k],inner[i][j],inner[i+1][j],inner[i+1][k]],'Soot')
    for i in (0,-1):
        for j in range(steps):
            k=(j+1)%steps
            poly=[outer[i][j],outer[i][k],inner[i][k],inner[i][j]]
            face(m,poly if i==-1 else poly[::-1],'Fireclay' if i==-1 else 'Iron')
    # Soot-dark fireback supports the hood. Its rear throat is open to the authored duct.
    for i in range(6):
        cuts=([-57,-19,24,66] if i%2==0 else [-57,-38,2,43,66])
        for a,b in zip(cuts,cuts[1:]):
            block(m,((a+b)/2,42.5,88+i*12),(b-a-.55,15,11.7),'Soot' if i<3 else 'Brick',.7)
    bottom=[(-61,-36,153),(63,-36,153),(63,51,153),(-61,51,153)]
    top=[(-27,18,246),(27,18,246),(27,58,246),(-27,58,246)]
    for a,b in ((0,1),(1,2),(3,0)):
        shell(m,[bottom[a],bottom[b],top[b],top[a]],1.4,'Iron')
        bar(m,bottom[a],bottom[b],(1.35,1.65),'Iron',(0,0,1),True)
    # Rear skirt ends at the existing service opening; seal the shoulders beside it.
    for quad in [[(-61,51,153),(63,51,153),(44.42,54.6,201),(-43.45,54.6,201)],
                 [(-43.45,54.6,201),(-25,54.6,201),(-25,58,246),(-27,58,246)],
                 [(25,54.6,201),(44.42,54.6,201),(27,58,246),(25,58,246)],top]:
        shell(m,quad,1.2,'Soot')
    for t in (.18,.54,.84):
        y=-36+54*t;z=153+93*t
        for x in (-59+32*t,59-32*t):
            lump(m,int(z+x),x,y-.8,z-.8,1.25,1.3,1.8,'Iron')

def fuel(m):
    rng=random.Random(9334)
    m.fuel_colors={}
    def coal(x,y,z,a,b,h,seed):
        first=len(m.verts)
        lump(m,seed,x,y,z,a,b,h,'HotCoal')
        hotspot=math.exp(-((x+28)/14)**2-((y+5)/11)**2)
        for i in range(first,len(m.verts)):
            px,py,pz=m.verts[i];side=max(0.,min(1.,1.-(pz*100-z)/h))
            vein=.35+.65*abs(math.sin(1.3*px*100+py*60+seed))
            m.fuel_colors[i]=(hotspot*(.16+.84*side),hotspot**1.5*side*vein,0.,1.)
    count=0
    # Spare fuel surrounds the pocket; the denser glowing core rises out of it on the inlet side.
    for radius,number in ((.86,15),(.56,11),(.31,7),(0.,1)):
        for j in range(number):
            t=(j+.31*rng.random())*math.tau/number
            x=CX+radius*27*math.cos(t);y=CY+radius*20*math.sin(t)
            h=rng.uniform(4.2,6.1)
            coal(x,y,deck_height(x,y)-.5, rng.uniform(4.3,6.4),rng.uniform(3.7,5.2),h,9000+count);count+=1
    for j in range(13):
        t=j*2.39996;r=(j/13)**.5
        x=-25.5+14*r*math.cos(t);y=-5+10*r*math.sin(t)
        coal(x,y,80.8+2.2*(1-r),4.9,4.2,rng.uniform(4.4,6.5),2000+j)
    for j in range(12):
        x=rng.uniform(-32,4);y=rng.uniform(-39,-26)
        lump(m,77+j,x,y,82.45,rng.uniform(1.2,3.2),rng.uniform(.8,2.),rng.uniform(.35,1.1),'Ash')
