"""Centimetre-scale profile sweeps for forged sections, bent links and joinery."""
import math
from mathutils import Vector

def section(width,depth,n,box=False):
    if box:
        a,b=width,depth
        k=min(a,b)*.25
        return [(-a+k,-b),(a-k,-b),(a,-b+k),(a,b-k),(a-k,b),(-a+k,b),(-a,b-k),(-a,-b+k)]
    return [(width*math.cos(i*math.tau/n),depth*math.sin(i*math.tau/n)) for i in range(n)]

def sweep(m,points,sizes,mat,reference=(1,0,0),closed=False,box=False,sides=None):
    path=[Vector(p) for p in points]
    n=sides or (10,8,6)[m.level]
    reference=Vector(reference).normalized()
    rings=[]
    for i,p in enumerate(path):
        v=((path[(i+1)%len(path)]-p).normalized() if closed or i<len(path)-1 else Vector())
        w=((p-path[(i-1)%len(path)]).normalized() if closed or i else Vector())
        tangent=(v+w).normalized()
        u=(reference-tangent*reference.dot(tangent)).normalized()
        if u.length<.1:raise ValueError('Section axis parallel to path')
        v=tangent.cross(u).normalized()
        a,b=sizes[i] if isinstance(sizes,list) else sizes
        ring=[p+u*x+v*y for x,y in section(a,b,n,box)]
        rings.append((m.vertices(ring),ring))
    n=len(rings[0][1]); distance=0
    for i in range(len(path) if closed else len(path)-1):
        j=(i+1)%len(path);base,r=rings[i];other,s=rings[j]
        extent=distance+(path[i]-path[j]).length;perim=0.
        for a in range(n):
            b=(a+1)%n
            length=(r[a]-r[b]).length
            m.face([base+a,base+b,other+b,other+a],
                   [(perim/48,distance/48),((perim+length)/48,distance/48),
                    ((perim+length)/48,extent/48),(perim/48,extent/48)],mat,not box)
            perim+=length
        distance=extent
    if not closed:
        for k,order in ((0,list(reversed(range(n)))),(-1,list(range(n)))):
            start,ring=rings[k]
            m.face([start+i for i in order],[(.5+.47*math.cos(math.tau*i/n),.5+.47*math.sin(math.tau*i/n)) for i in order],mat)

def bar(m,a,b,r,mat='Iron',ref=(1,0,0),flat=False):
    sweep(m,[a,b],r,mat,ref,box=flat)

def ring(m,centre,u,v,tube,mat='Iron'):
    c=Vector(centre);u=Vector(u);v=Vector(v)
    n=(28,18,12)[m.level]
    pts=[c+u*math.cos(i*math.tau/n)+v*math.sin(i*math.tau/n) for i in range(n)]
    sweep(m,pts,(tube,tube),mat,u.cross(v).normalized(),True)

def curve(start,spans,count):
    pts=[Vector(start)]
    for p1,p2,p3 in spans:
        p0=pts[-1];p1,p2,p3=map(Vector,(p1,p2,p3))
        for j in range(1,count+1):
            t=j/count
            pts.append(p0*(1-t)**3+3*p1*t*(1-t)**2+3*p2*t*t*(1-t)+p3*t**3)
    return pts
