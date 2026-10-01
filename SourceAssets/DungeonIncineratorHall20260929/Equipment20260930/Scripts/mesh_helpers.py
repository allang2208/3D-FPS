"""Precisely authored replacement cargo stack and switchgear. No renders or simulation."""
import json,math
from pathlib import Path
import bpy,bmesh
from mathutils import Vector,Matrix,Euler

ROOT=Path(__file__).resolve().parents[1]
ATLAS=json.loads((ROOT/'Authored/atlas.json').read_text(encoding='utf-8'))
MATERIAL='/Game/Dungeons/IncineratorHall20260929/EquipmentV1/Materials/M_IncineratorEquipment_Atlas'
SLOT='IncineratorEquipment_Atlas'
V=[];F=[];UV=[];SMOOTH=[]

def tex(surface,u,v):
    x0,y0,x1,y1=ATLAS['rects'][surface]
    return ((x0+u*(x1-x0))/4096,1-(y0+v*(y1-y0))/2048)

def face(vertices,surface,uv=None,smooth=False):
    offset=len(V);V.extend(tuple(p) for p in vertices);F.append(tuple(range(offset,offset+len(vertices))))
    UV.append([tex(surface,*p) for p in (uv or [(0,1),(1,1),(1,0),(0,0)])]);SMOOTH.append(smooth)

def box(c,size,surface='teal',bevel=.003,rotation=(0,0,0)):
    bm=bmesh.new();bmesh.ops.create_cube(bm,size=1)
    for vert in bm.verts:vert.co=Vector(tuple(vert.co[i]*size[i] for i in range(3)))
    if bevel:
        bmesh.ops.bevel(bm,geom=list(bm.edges),offset=min(bevel,min(size)*.23),segments=3,affect='EDGES')
    bm.normal_update();rot=Euler(rotation).to_matrix();center=Vector(c)
    for p in bm.faces:
        axis=max(range(3),key=lambda i:abs(p.normal[i]));dims=[i for i in range(3) if i!=axis]
        if surface in ('wood','red'):dims.sort(key=lambda i:size[i])
        coords=[]
        for vert in p.verts:
            uv=[]
            for dim in dims:
                den=max(size[dims[0]],size[dims[1]]) if surface=='wood' else size[dim]
                uv.append(.5+vert.co[dim]/max(den,.001)*.97)
            coords.append((uv[0],1-uv[1]))
        face([center+rot@v.co for v in p.verts],surface,coords,max(abs(p.normal[i]) for i in range(3))<.999)
    bm.free()

def basis(axis):
    n=Vector(axis).normalized();u=Vector((0,0,1)).cross(n) if abs(n.z)<.9 else Vector((1,0,0))
    u=(u-n*u.dot(n)).normalized();return n,u,n.cross(u).normalized()

def lathe(c,axis,profile,surface='steel',segments=32,smooth=True):
    n,u,v=basis(axis);c=Vector(c)
    rings=[[c+n*z+(u*math.cos(i*math.tau/segments)+v*math.sin(i*math.tau/segments))*radius for i in range(segments)] for z,radius in profile]
    for k in range(len(rings)-1):
        for i in range(segments):
            j=(i+1)%segments
            face([rings[k][i],rings[k][j],rings[k+1][j],rings[k+1][i]],surface,
                 [(i/segments,k/(len(rings)-1)),((i+1)/segments,k/(len(rings)-1)),((i+1)/segments,(k+1)/(len(rings)-1)),(i/segments,(k+1)/(len(rings)-1))],smooth)
    for k,reverse in [(0,True),(-1,False)]:
        ids=list(range(segments));ids=ids[::-1] if reverse else ids
        face([rings[k][i] for i in ids],surface,[(.5+.48*math.cos(i*math.tau/segments),.5-.48*math.sin(i*math.tau/segments)) for i in ids])

def rod(a,b,r,surface='steel',segments=16):
    a=Vector(a);b=Vector(b);lathe(a,b-a,[(0,r),((b-a).length,r)],surface,segments)

def tube(points,r,surface='steel',segments=12):
    points=[Vector(p) for p in points];rings=[]
    for i,p in enumerate(points):
        direction=(points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        n,u,v=basis(direction)
        rings.append([p+r*(u*math.cos(j*math.tau/segments)+v*math.sin(j*math.tau/segments)) for j in range(segments)])
    for k in range(len(rings)-1):
        for i in range(segments):
            j=(i+1)%segments
            face([rings[k][i],rings[k][j],rings[k+1][j],rings[k+1][i]],surface,[(i/segments,0),((i+1)/segments,0),((i+1)/segments,1),(i/segments,1)],True)
    face(list(reversed(rings[0])),surface,[(.5+.4*math.cos(i*math.tau/segments),.5+.4*math.sin(i*math.tau/segments)) for i in reversed(range(segments))])
    face(rings[-1],surface,[(.5+.4*math.cos(i*math.tau/segments),.5+.4*math.sin(i*math.tau/segments)) for i in range(segments)])

def bolt(c,axis=(0,-1,0),scale=1):
    n=Vector(axis).normalized();lathe(c,n,[(0,.009*scale),(.0016*scale,.009*scale)],'steel',24)
    center=Vector(c)+n*.0016*scale
    lathe(center,n,[(0,.0065*scale),(.004*scale,.0065*scale),(.005*scale,.0056*scale),(.005*scale,.0028*scale),(.0025*scale,.0028*scale)],'steel',6,False)
    lathe(center+n*.00255*scale,n,[(0,.0026*scale),(.0001*scale,.0026*scale)],'rubber',6,False)

def plaque(c,width,height,surface,axis=(0,-1,0),thickness=.0015,backing='steel'):
    n,u,v=basis(axis);c=Vector(c)
    # Backing dimensions and rotation are derived from the printed face basis.
    if abs(n.y)>.9:box(c-n*thickness*.5,(width,thickness,height),backing,.0006)
    elif abs(n.x)>.9:box(c-n*thickness*.5,(thickness,width,height),backing,.0006)
    else:box(c-n*thickness*.5,(width,height,thickness),backing,.0006)
    c+=n*.0004
    face([c-u*width*.5-v*height*.5,c+u*width*.5-v*height*.5,c+u*width*.5+v*height*.5,c-u*width*.5+v*height*.5],surface)
