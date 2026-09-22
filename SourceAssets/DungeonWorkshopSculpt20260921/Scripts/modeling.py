"""Component modeling in workshop-local metres, before the final engine-axis transform."""
import bpy,bmesh,math
from mathutils import Vector,Matrix
from mathutils.geometry import tessellate_polygon
from collections import defaultdict
PARTS=defaultdict(list)
class Frame:
    def __init__(self,c=(0,0,0),u=(1,0,0),v=(0,1,0)):
        self.c=Vector(c);self.u=Vector(u);self.v=Vector(v);self.n=self.u.cross(self.v).normalized()
    def p(self,x,y,z=0):return self.c+self.u*x+self.v*y+self.n*z
    def offset(self,x=0,y=0,z=0):return Frame(self.p(x,y,z),self.u,self.v)
def flat(c,angle=0):return Frame(c,(math.cos(angle),math.sin(angle),0),(-math.sin(angle),math.cos(angle),0))
def active(ob):
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
def material(ob,key):ob.data.materials.append(MATS[key])
def part(g,name,verts,faces,mat,smooth=False,uvs=None):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    ob=bpy.data.objects.new(name,me);bpy.context.scene.collection.objects.link(ob);material(ob,mat)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(me);bm.free()
    uv=me.uv_layers.new(name='UVMap')
    for face in me.polygons:
        face.use_smooth=smooth;axis=max(range(3),key=lambda a:abs(face.normal[a]));dims=[a for a in range(3) if a!=axis]
        for li in face.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv=(p[dims[0]]/.18,p[dims[1]]/.18)
    PARTS[g].append(ob);ob['component_group']=g
    return ob
def bevel(ob,width=.002,segments=5):
    m=ob.modifiers.new('Manufactured edge radius','BEVEL');m.width=width;m.segments=segments;m.limit_method='ANGLE';m.angle_limit=.45;m.harden_normals=True
    m=ob.modifiers.new('Planar faces and curved edge normals','WEIGHTED_NORMAL');m.keep_sharp=True;m.weight=50
    return ob
def box(g,name,c,size,mat,r=.001,frame=None):
    f=frame or Frame(c);sx,sy,sz=[s/2 for s in size]
    vs=[f.p(x,y,z) for z in (-sz,sz) for y in (-sy,sy) for x in (-sx,sx)]
    fs=[(0,2,3,1),(4,5,7,6),(0,1,5,4),(1,3,7,5),(3,2,6,7),(2,0,4,6)]
    ob=part(g,name,vs,fs,mat,True)
    if r:bevel(ob,r)
    return ob
def rounded(poly,r=.003,steps=5):
    out=[]
    for i,p in enumerate(poly):
        p=Vector(p);prev=Vector(poly[i-1]);nxt=Vector(poly[(i+1)%len(poly)])
        radius=min(r,(prev-p).length*.26,(nxt-p).length*.26)
        a=p+(prev-p).normalized()*radius;b=p+(nxt-p).normalized()*radius
        for j in range(steps+1):
            t=j/steps;q=(1-t)**2*a+2*t*(1-t)*p+t*t*b;out.append(tuple(q))
    return out
def profile(g,name,poly,f,thickness,mat,r=.001):
    poly=list(poly)
    n=len(poly);p2=[Vector((x,y,0)) for x,y in poly];lookup={tuple(p):i for i,p in enumerate(p2)}
    tris=[[p if isinstance(p,int) else lookup[tuple(p)] for p in tri] for tri in tessellate_polygon([p2])]
    vs=[f.p(x,y,sign*(thickness(y) if callable(thickness) else thickness)/2) for sign in (-1,1) for x,y in poly]
    fs=[tuple(reversed(t)) for t in tris]+[tuple(i+n for i in t) for t in tris]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    ob=part(g,name,vs,fs,mat,True)
    if r:bevel(ob,r)
    return ob
def catmull(points,steps=6):
    pts=[Vector(p) for p in points];out=[]
    for i in range(len(pts)-1):
        a=pts[max(0,i-1)];b=pts[i];c=pts[i+1];d=pts[min(len(pts)-1,i+2)]
        for j in range(steps):
            t=j/steps;out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return out+[pts[-1]]
def lathe(g,name,f,profile_pts,mat,sides=64,lobes=0,cap=True):
    # Axial distance is frame V; U/N span the radial cross section.
    vs=[];fs=[]
    for z,r in profile_pts:
        for i in range(sides):
            a=i*math.tau/sides;rr=r*(1+lobes*math.cos(a*6));vs.append(f.p(rr*math.cos(a),z,rr*math.sin(a)))
    for j in range(len(profile_pts)-1):
        for i in range(sides):a=j*sides+i;b=j*sides+(i+1)%sides;fs.append((a,b,b+sides,a+sides))
    if cap:fs.extend([tuple(reversed(range(sides))),tuple((len(profile_pts)-1)*sides+i for i in range(sides))])
    ob=part(g,name,vs,fs,mat,True)
    uv=ob.data.uv_layers.active
    for face in ob.data.polygons:
        for li in face.loop_indices:
            vi=ob.data.loops[li].vertex_index;uv.data[li].uv=((vi%sides)/sides,(profile_pts[vi//sides][0]-profile_pts[0][0])/.15)
    if cap:
        ob.data.polygons[-1].use_smooth=False;ob.data.polygons[-2].use_smooth=False
    return ob
def sweep(g,name,pts,r,mat,sides=20,smooth_path=True,ellipse=1):
    points=catmull(pts,5) if smooth_path and len(pts)>2 else [Vector(p) for p in pts]
    vs=[];fs=[]
    for j,p in enumerate(points):
        tangent=(points[min(j+1,len(points)-1)]-points[max(j-1,0)]).normalized()
        axis=Vector((0,0,1)) if abs(tangent.z)<.93 else Vector((0,1,0))
        u=tangent.cross(axis).normalized();v=tangent.cross(u).normalized();rad=r(j/(len(points)-1)) if callable(r) else r
        for i in range(sides):
            a=i*math.tau/sides;vs.append(p+u*math.cos(a)*rad+v*math.sin(a)*rad*ellipse)
    for j in range(len(points)-1):
        for i in range(sides):a=j*sides+i;b=j*sides+(i+1)%sides;fs.append((a,b,b+sides,a+sides))
    fs.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+i for i in range(sides))])
    ob=part(g,name,vs,fs,mat,True)
    for face in ob.data.polygons[-2:]:face.use_smooth=False
    return ob
def ring(g,name,f,r,t,mat,sides=72):
    pts=[f.p(r*math.cos(i*math.tau/sides),r*math.sin(i*math.tau/sides)) for i in range(sides+1)]
    return sweep(g,name,pts,t,mat,12,False)
def cylinder(g,name,a,b,r,mat,sides=48):return sweep(g,name,[a,b],r,mat,sides,False)
def bore(ob,f,poly,depth):
    cutter=profile('_cutters','Cutter',poly,f,depth,'Machined',0)
    active(ob);m=ob.modifiers.new('Functional machined opening','BOOLEAN');m.operation='DIFFERENCE';m.solver='EXACT';m.object=cutter
    # Boolean comes before the component bevel so its real opening gets an edge radius too.
    while list(ob.modifiers).index(m)>0:bpy.ops.object.modifier_move_up(modifier=m.name)
    bpy.ops.object.modifier_apply(modifier=m.name)
    PARTS['_cutters'].remove(cutter);bpy.data.objects.remove(cutter,do_unlink=True)
def bolt(g,c,normal=(0,0,1),r=.005,name='Hex fastener'):
    a=Vector(c);n=Vector(normal).normalized();ob=cylinder(g,name,a,a+n*r*.75,r,'Machined',6);bevel(ob,r*.12,3)
    axis=n.cross(Vector((1,0,0)) if abs(n.x)<.9 else Vector((0,1,0))).normalized()
    ring(g,'Fastener washer',Frame(a,axis,n.cross(axis)),r*1.24,r*.13,'Machined',24)
def label(g,c,u,v,w,h,index):
    f=Frame(c,u,v);ob=part(g,'Printed service label',[f.p(-w/2,-h/2),f.p(w/2,-h/2),f.p(w/2,h/2),f.p(-w/2,h/2)],[(0,1,2,3)],'ToolLabels')
    uv=ob.data.uv_layers.active;xx=index%4;yy=index//4
    for li,uvv in zip(ob.data.polygons[0].loop_indices,[(xx/4+.005,1-(yy+1)/4+.005),((xx+1)/4-.005,1-(yy+1)/4+.005),((xx+1)/4-.005,1-yy/4-.005),(xx/4+.005,1-yy/4-.005)]):uv.data[li].uv=uvv
    return ob
