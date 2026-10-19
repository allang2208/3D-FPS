"""Geometry primitives copied from the owned ArmoredBoots authoring source.
New brown leather set owns this snapshot; importing it performs no asset save.
"""
import json,math
import bpy,bmesh
import numpy as np
objects=[]
bone_ids={}
def unit(a):
    a=np.array(a,float);return a/max(np.linalg.norm(a),1e-10)

def profile(z):
    levels=[4,8,12,18,24,30,36,40]
    return np.array([np.interp(z,levels,v) for v in [
        [14.8,14.8,14.65,14.1,13.7,13.1,12.7,12.1],
        [-2.45,-2.45,-2.65,-2.75,-2.95,-2.8,-2.35,-1.5],
        [4.45,4.45,4.05,4.75,5.95,6.7,6.45,6.35],
        [5.85,5.85,5.25,5.3,5.85,6.65,6.85,6.85]]])

def shaft_point(side,theta,z,offset=0,ridge=0):
    cx,cy,rx,ry=profile(z);s=1 if side=='l' else -1
    return np.array([s*(cx+(rx+offset)*math.sin(theta)),cy+(ry+offset)*math.cos(theta)+ridge*math.exp(-(theta/.19)**2),z])

def foot_point(side,u,v,z):
    s=1 if side=='l' else -1;angle=math.atan2(2.00392146,12.92064786)
    return np.array([s*(14.798+math.cos(angle)*u+math.sin(angle)*v),-2.45465-math.sin(angle)*u+math.cos(angle)*v,z])

def foot_shape(v):
    levels=[-7.0,-6.6,-5.5,-3,0,3,6,10,14,18,21,22.8,24]
    width=np.interp(v,levels,[.16,2.4,3.9,4.35,4.6,4.95,5.5,6.0,6.15,5.65,4.7,3.35,.18])
    top=np.interp(v,levels,[5.1,7.2,9.2,10.9,12.0,10.4,8.2,6.6,5.7,5.15,4.75,3.7,1.25])
    return width,top

def dorsal(side,v,theta,raise_cm=0):
    w,h=foot_shape(v);return foot_point(side,(w+raise_cm)*math.sin(theta),v,-.65+(h+.65)*(.5+.5*math.cos(theta))+raise_cm)

def smooth(a,b,x):
    t=np.clip((x-a)/(b-a),0,1);return float(t*t*(3-2*t))

def skin(side,p,mode):
    if mode=='calf':return {bone_ids['calf_'+side]:1.}
    # Native articulation locations: ankle 8.42 cm; ball forward 13.08 cm.
    s=1 if side=='l' else -1;v=(s*p[0]-14.798)*.1533+(p[1]+2.45465)*.9882
    calf=smooth(8.4,16.5,p[2]) if mode=='flex' else 0.
    toe=smooth(10.6,16.3,v)*(1-calf)
    return {bone_ids['calf_'+side]:calf,bone_ids['ball_'+side]:toe,bone_ids['foot_'+side]:max(0,1-calf-toe)}

def mesh_object(name,vertices,faces,side,mode,slot,thickness=0,bevel=0):
    mesh=bpy.data.meshes.new(name)
    mesh.from_pydata([(x*.01,-y*.01,z*.01) for x,y,z in vertices],[],[list(reversed(f)) for f in faces]);mesh.update()
    ob=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(ob);bpy.context.view_layer.objects.active=ob
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    if thickness:
        mod=ob.modifiers.new('Closed forged thickness','SOLIDIFY');mod.thickness=thickness*.01;mod.offset=-1
        mod.use_even_offset=True;bpy.ops.object.modifier_apply(modifier=mod.name)
    if bevel:
        mod=ob.modifiers.new('Rounded production bevel','BEVEL');mod.width=bevel*.01;mod.segments=3;mod.limit_method='ANGLE';mod.angle_limit=.5
        bpy.ops.object.modifier_apply(modifier=mod.name)
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-8)
    bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=1e-8);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    for poly in mesh.polygons:poly.use_smooth=True
    mesh.set_sharp_from_angle(angle=math.radians(52))
    uv=mesh.uv_layers.new(name='Physical25cm')
    for poly in mesh.polygons:
        axis=max(range(3),key=lambda i:abs(poly.normal[i]));plane=[i for i in range(3) if i!=axis]
        for li in poly.loop_indices:
            co=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(co[plane[0]]/.25,co[plane[1]]/.25)
    mesh.update();ob['material_slot']=slot;ob['side']=side;ob['weight_zone']=mode
    objects.append(ob);return ob

def tube(name,path,radius,side,mode,slot=0,closed=False,sides=8):
    path=np.array(path);vertices=[];faces=[];count=len(path)
    for i,p in enumerate(path):
        tangent=unit(path[(i+1)%count]-path[(i-1)%count]) if closed else unit(path[min(i+1,count-1)]-path[max(0,i-1)])
        a=unit(np.cross(tangent,[0,0,1] if abs(tangent[2])<.9 else [0,1,0]));b=np.cross(tangent,a)
        vertices.extend(p+radius*(math.cos(t)*a+math.sin(t)*b) for t in np.linspace(0,2*math.pi,sides,endpoint=False))
    for i in range(count if closed else count-1):
        for j in range(sides):faces.append([i*sides+j,i*sides+(j+1)%sides,((i+1)%count)*sides+(j+1)%sides,((i+1)%count)*sides+j])
    if not closed:faces.extend([list(reversed(range(sides))),list(range((count-1)*sides,count*sides))])
    return mesh_object(name,vertices,faces,side,mode,slot)

def rivet(name,p,n,side,mode,r=.22):
    n=unit(n);a=unit(np.cross(n,[0,0,1] if abs(n[2])<.9 else [1,0,0]));b=np.cross(n,a)
    curve=[(0,.12),(.5,.11),(.88,.065),(1,.0),(1.07,-.045),(.65,-.07),(0,-.07)]
    verts=[np.array(p)+n*curve[0][1]];faces=[];sides=12
    for radius,h in curve[1:-1]:verts.extend(np.array(p)+n*h+r*radius*(math.cos(t)*a+math.sin(t)*b) for t in np.linspace(0,math.tau,sides,endpoint=False))
    for i in range(sides):faces.append([0,1+i,1+(i+1)%sides])
    for j in range(len(curve)-3):
        for i in range(sides):
            a0=1+j*sides+i;b0=1+j*sides+(i+1)%sides;faces.append([a0,b0,b0+sides,a0+sides])
    end=len(verts);verts.append(np.array(p)+n*curve[-1][1]);start=1+(len(curve)-3)*sides
    for i in range(sides):faces.append([start+i,end,start+(i+1)%sides])
    mesh_object(name,verts,faces,side,mode,0)

def leather(side):
    # Continuous foot last with closed toe/heel, leather under the steel shells.
    verts=[];faces=[];ny=66;nr=40
    for v in np.linspace(-7,24,ny):
        w,h=foot_shape(v)
        for theta in np.linspace(0,math.tau,nr,endpoint=False):verts.append(foot_point(side,w*math.sin(theta),v,-.65+(h+.65)*(.5+.5*math.cos(theta))))
    for j in range(ny-1):
        for i in range(nr):faces.append([j*nr+i,j*nr+(i+1)%nr,(j+1)*nr+(i+1)%nr,(j+1)*nr+i])
    faces.extend([list(reversed(range(nr))),list(range((ny-1)*nr,ny*nr))])
    mesh_object('LeatherFoot_'+side,verts,faces,side,'foot',1)
    # Outer shaft, padded rim and inner wall share one watertight ring mesh.
    verts=[];faces=[];nr=64;rows=[]
    for z in np.linspace(8,38.1,28):rows.append((z,0.))
    rows.extend([(38.35,-.03),(38.52,-.18),(38.38,-.37)])
    rows.extend([(z,-.38) for z in np.linspace(38.1,8,27)])
    for z,offset in rows:
        for theta in np.linspace(0,math.tau,nr,endpoint=False):
            rim_lift=.48*max(0,math.cos(theta))*(smooth(34,38,z))
            wrinkle=.10*math.sin(z*1.8+math.sin(theta)*1.2)*math.exp(-((z-14)/5)**2)
            verts.append(shaft_point(side,theta,z+rim_lift,offset+wrinkle))
    for j in range(len(rows)):
        for i in range(nr):faces.append([j*nr+i,j*nr+(i+1)%nr,((j+1)%len(rows))*nr+(i+1)%nr,((j+1)%len(rows))*nr+i])
    mesh_object('LeatherShaftWithInnerWall_'+side,verts,faces,side,'flex',1)
    # Welt and sole retain a rounded anatomical foot outline and low heel.
    outline=[]
    for v in np.linspace(-6.9,23.9,78):outline.append((foot_shape(v)[0]+.48,v))
    for v in np.linspace(23.9,-6.9,78):outline.append((-foot_shape(v)[0]-.48,v))
    verts=[];faces=[]
    for z,offset in [(-2.55,-.05),(-2.48,.05),(-1.05,.10),(-.65,.03)]:
        verts.extend(foot_point(side,u+math.copysign(offset,u),v,z+max(0,v-18)*.025) for u,v in outline)
    n=len(outline)
    for j in range(3):
        for i in range(n):faces.append([j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i])
    faces.extend([list(reversed(range(n))),list(range(3*n,4*n))])
    mesh_object('LayeredLeatherSole_'+side,verts,faces,side,'foot',2,bevel=.10)
    welt=[foot_point(side,u,v,-.72) for u,v in outline]
    tube('RaisedWelt_'+side,welt,.12,side,'foot',2,True)
    # A coarse visible welt seam uses individual short arcs, grouped in one mesh.
    verts=[];faces=[];loop=np.array(welt);lengths=np.linalg.norm(np.roll(loop,-1,axis=0)-loop,axis=1);total=sum(lengths)
    cumulative=np.r_[0,np.cumsum(lengths)]
    def at(t):
        t=t%total;i=min(len(loop)-1,np.searchsorted(cumulative,t,side='right')-1);f=(t-cumulative[i])/lengths[i]
        return loop[i]*(1-f)+loop[(i+1)%len(loop)]*f
    for distance in np.arange(0,total,.72):
        path=[at(distance+d)+[0,0,.04+.07*math.sin(t*math.pi)] for t,d in zip(np.linspace(0,1,4),np.linspace(0,.40,4))]
        start=len(verts)
        for j,p in enumerate(path):
            axis=unit(path[min(j+1,3)]-path[max(0,j-1)]);a=unit(np.cross(axis,[0,0,1]));b=np.cross(axis,a)
            verts.extend(p+.035*(math.cos(t)*a+math.sin(t)*b) for t in np.linspace(0,math.tau,5,endpoint=False))
        for j in range(3):
            for i in range(5):faces.append([start+j*5+i,start+j*5+(i+1)%5,start+(j+1)*5+(i+1)%5,start+(j+1)*5+i])
    mesh_object('WeltStitch_'+side,verts,faces,side,'foot',3)

def valid_uv(uv,points):
    a,b=uv[1]-uv[0],uv[2]-uv[0]
    if abs(a[0]*b[1]-a[1]*b[0])>=1e-12:return uv
    tangent=unit(points[1]-points[0]);normal=unit(np.cross(points[1]-points[0],points[2]-points[0]));bitangent=np.cross(normal,tangent)
    local=points-points[0];return np.c_[local@tangent,local@bitangent]/25
