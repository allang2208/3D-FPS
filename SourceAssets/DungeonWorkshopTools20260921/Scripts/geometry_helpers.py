"""Geometry primitives reused from the authored workshop revision."""
import math
from mathutils import Vector
groups={}
def add(group,verts,faces,mat,smooth=False,uvs=None):
    g=groups.setdefault(group,{'v':[],'f':[],'mat':[],'smooth':[],'uv':[]});offset=len(g['v'])
    g['v'].extend((10-x,-y,z) for x,y,z in verts)
    for i,face in enumerate(faces):
        g['f'].append(tuple(offset+j for j in face));g['mat'].append(mat)
        g['smooth'].append(smooth if isinstance(smooth,bool) else smooth[i]);g['uv'].append(uvs[i] if uvs else None)

def box(g,c,size,mat,angle=0):
    x,y,z=c;a,b,d=[v/2 for v in size];co,si=math.cos(angle),math.sin(angle)
    vs=[(x+i*co-j*si,y+i*si+j*co,z+k) for i,j,k in [(-a,-b,-d),(a,-b,-d),(a,b,-d),(-a,b,-d),(-a,-b,d),(a,-b,d),(a,b,d),(-a,b,d)]]
    add(g,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)

def tube(g,points,r,mat,sides=24,cap=True):
    ps=[Vector(p) for p in points];vs=[]
    for i,p in enumerate(ps):
        t=(ps[min(i+1,len(ps)-1)]-ps[max(i-1,0)]).normalized()
        axis=Vector((0,0,1)) if abs(t.z)<.9 else Vector((0,1,0))
        a=t.cross(axis).normalized();b=t.cross(a).normalized()
        vs.extend(tuple(p+r*(math.cos(j*math.tau/sides)*a+math.sin(j*math.tau/sides)*b)) for j in range(sides))
    fs=[];sm=[]
    for i in range(len(ps)-1):
        for j in range(sides):fs.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j));sm.append(True)
    if cap:fs.extend([tuple(reversed(range(sides))),tuple((len(ps)-1)*sides+j for j in range(sides))]);sm.extend([False,False])
    add(g,vs,fs,mat,sm)

def ring(g,c,axis,r,minor,mat,n=36):
    axis=Vector(axis).normalized();a=axis.cross(Vector((0,0,1)) if abs(axis.z)<.9 else Vector((0,1,0))).normalized();b=axis.cross(a)
    points=[tuple(Vector(c)+r*(math.cos(i*math.tau/n)*a+math.sin(i*math.tau/n)*b)) for i in range(n+1)]
    tube(g,points,minor,mat,12,False)

def bolt(g,p,axis=(0,-1,0),r=.006):
    p=Vector(p);axis=Vector(axis).normalized()
    tube(g,[tuple(p),tuple(p+axis*.003)],r*1.4,'Steel',20)
    tube(g,[tuple(p+axis*.003),tuple(p+axis*.008)],r,'Steel',6)

def panel(g,c,right,up,w,h,mat,uv=(0,0,1,1)):
    c=Vector(c);right=Vector(right)*w/2;up=Vector(up)*h/2
    a,b,d,e=uv
    add(g,[tuple(c-right-up),tuple(c+right-up),tuple(c+right+up),tuple(c-right+up)],[(0,1,2,3)],mat,
        uvs=[[(a,b),(d,b),(d,e),(a,e)]])

def label(c,right,w,h,index):
    col=index%4;row=index//4
    uv=(col/4,(3-row)/4,(col+1)/4,(4-row)/4)
    panel('ToolMarkings',c,right,(0,0,1),w,h,'ToolLabels',uv)
