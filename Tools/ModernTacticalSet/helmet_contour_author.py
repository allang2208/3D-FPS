"""Reshape the existing fitted helmet and its hardware in the original body frame."""
import copy
import json
import math
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

P=Path(__file__).resolve().parents[2]
T=P/'Tools/ModernTacticalSet'
sys.path.insert(0,str(T))
import helmet1_author as detail
from helmet_hair_mesh_clean import clean

ROOT=P/'SourceAssets/ModernTacticalSet20261113'
OLD=ROOT/'HelmetHairFitR1'
OUT=ROOT/'HelmetContourR2'
A=detail.A

class Crown:
    def __init__(self,rig):
        fit=json.loads((OLD/'fit.json').read_bytes())['profiles'][rig]
        self.old=fit
        profile=np.load(OUT/(rig+'-profile.npz'))
        self.origin=profile['origin'];self.rad=profile['rad'];self.step=float(profile['step'])
        self.ends=profile['ends'];self.top=float(profile['top'])

    def sample(self,theta,t):
        theta,t=np.broadcast_arrays(np.asarray(theta),np.asarray(t))
        col=theta%(2*np.pi)*len(self.ends)/(2*np.pi)
        u=col%1;i=np.floor(col).astype(int)%len(self.ends);j=(i+1)%len(self.ends)
        phi=t*((1-u)*self.ends[i]+u*self.ends[j])
        row=(phi/self.step).clip(0,len(self.rad)-1.001)
        k=row.astype(int);v=row%1
        r=(1-v)*((1-u)*self.rad[k,i]+u*self.rad[k,j])+v*((1-u)*self.rad[k+1,i]+u*self.rad[k+1,j])
        return self.origin+np.stack([np.sin(theta)*np.sin(phi),np.cos(theta)*np.sin(phi),np.cos(phi)],axis=-1)*r[...,None]

    def normal(self,theta,t):
        angle=self.sample(theta+.003,t)-self.sample(theta-.003,t)
        arc=self.sample(theta,np.maximum(t,.005)+.003)-self.sample(theta,np.maximum(t,.005)-.003)
        cross=np.cross(angle,arc);length=np.linalg.norm(cross,axis=-1,keepdims=True)
        return np.where(length>1e-7,cross/np.maximum(length,1e-7),[0,0,1])

    def surface(self,theta,t,offset):
        return self.sample(theta,t)+self.normal(theta,t)*offset

    def shell_tree(self):
        M,N=58,144
        points=[self.sample(0,0)]
        for t in np.linspace(1/M,1,M):
            points.extend(self.sample(np.arange(N)*2*np.pi/N,t))
        faces=[[0,1+i,1+(i+1)%N] for i in range(N)]
        for j in range(M-1):
            for i in range(N):
                a=1+j*N+i;b=1+j*N+(i+1)%N
                faces.extend([(a,b,b+N),(a,b+N,a+N)])
        return BVHTree.FromPolygons(points,faces,all_triangles=True)

    def front_hardware(self,p,tree):
        f=self.old;c=f['center'];rx=f['rx'];ry=f['front_radius'];rz=f['rz'];power=f['vertical_power']
        x=p[:,0]-c[0];z=p[:,2]-c[2]
        old_y=c[1]+ry*np.sqrt(np.maximum(.05,np.maximum(0,1-abs(z/rz)**power)**(2/power)-(x/rx)**2))
        result=p.copy();result[:,2]+=3.25;result[:,0]=x
        for i,v in enumerate(result):
            hit=tree.ray_cast(Vector((v[0],40,v[2])),Vector((0,-1,0)),70)[0]
            if hit is None:raise RuntimeError('Front shroud misses its mounting face')
            result[i,1]=hit.y+p[i,1]-old_y[i]
        return result

    def transfer(self,p):
        f=self.old;c=np.array(f['center']);q=p-c
        ry=np.where(q[:,1]>=0,f['front_radius'],f['rear_radius'])
        x=q[:,0]/f['rx'];y=q[:,1]/ry;z=q[:,2]/f['rz']
        angle=np.arctan2(x,y)
        # R1 used a slight exponent on the lateral meridians. Recover that
        # parameter before moving the actual split-normal mesh and attachments.
        target=np.abs(x)/np.maximum(np.abs(y),1e-8)
        a=abs(np.arctan2(abs(x),abs(y)))
        for _ in range(3):
            sin=np.maximum(np.sin(a),1e-8);cos=np.maximum(np.cos(a),1e-8)
            residual=sin**.96-target*cos
            a=np.clip(a-residual/(.96*sin**(-.04)*cos+target*sin),0,np.pi/2)
        angle=np.copysign(np.where(y>=0,a,np.pi-a),x)
        h=np.sqrt(x*x+y*y)
        along=np.where(abs(np.cos(angle))>.55,y/np.where(abs(np.cos(angle))>.55,np.cos(angle),1.),abs(x)/np.maximum(abs(np.sin(angle))**.96,1e-8))
        power=f['vertical_power'];rho=(along**power+abs(z)**power)**(1/power)
        zn=z/np.maximum(rho,1e-8)
        phi=np.arccos(np.clip(np.sign(zn)*abs(zn)**(power/2),-1,1))
        edge=self.top-11.6+2.15*abs(np.sin(angle))**6-3.6*np.maximum(0,-np.cos(angle))**2
        ez=(edge-c[2])/f['rz']
        end=np.arccos(np.clip(np.sign(ez)*abs(ez)**(power/2),-1,1))
        t=phi/end
        oldsurf=c+q/np.maximum(rho[:,None],1e-8)
        oldnormal=np.stack([x*h**(power-2)/f['rx'],y*h**(power-2)/ry,np.sign(z)*abs(z)**(power-1)/f['rz']],axis=1)
        oldnormal/=np.maximum(np.linalg.norm(oldnormal,axis=1,keepdims=True),1e-8)
        distance=((p-oldsurf)*oldnormal).sum(1)
        return self.sample(angle,t)+self.normal(angle,t)*distance[:,None]

def panel(crown,name,angle_lo,angle_hi,t_top,t_bottom,side):
    # Textile islands have a clipped forward corner and a lower edge parallel to the cheek rail.
    grid=[];nu,nv=27,12
    for j in range(nv+1):
        v=j/nv
        for i in range(nu+1):
            u=i/nu
            clip=max(0,1-4*u)
            a=(angle_lo+(angle_hi-angle_lo)*u+.13*clip*(1-v)**2)*side
            t=t_top+(t_bottom-t_top)*v+.08*clip*(1-v)+.055*u
            grid.append(crown.surface(a,t,.064))
    faces=[]
    for j in range(nv):
        for i in range(nu):
            k=j*(nu+1)+i
            faces.append([k,k+1,k+nu+2,k+nu+1])
    ob=A.mesh(name,grid,faces,'Webbing',thickness=.08,do_bind=False,radial_center=crown.origin)
    detail.project_uv(ob);detail.finish_normals(ob)
    perimeter=[i for i in range(nu+1)]+[j*(nu+1)+nu for j in range(1,nv+1)]+[nv*(nu+1)+i for i in reversed(range(nu))]+[j*(nu+1) for j in reversed(range(1,nv))]
    detail.tube(name+'_Fold',[grid[i] for i in perimeter],.050,'Webbing',6,True)

def radial_hit(tree,center,theta,z):
    origin=np.array([center[0],center[1],z]);axis=np.array([np.sin(theta),np.cos(theta),0])
    hit=tree.ray_cast(Vector(origin+axis*38),Vector(-axis),70)[0]
    if hit is None:raise RuntimeError('No side of native jaw for retention system')
    return np.array(hit),axis

def suspension(crown,tree,side,rear):
    center=crown.old['center'];top=crown.top
    a=(2.34 if rear else .78)*side
    anchor=crown.surface(a,.995,-.19)
    if rear:
        phases=[0,.28,.60,.77,1];angles=np.array([2.34,2.19,1.86,1.53,.88])*side
        heights=[anchor[2],top-14.7,top-17.55,top-18.7,top-20.5]
    else:
        phases=[0,.33,1];angles=np.array([.78,.84,.88])*side;heights=[anchor[2],top-13.5,top-20.5]
    path=[];directions=[];points=[]
    for u in np.linspace(0,1,45):
        theta=np.interp(u,phases,angles);z=np.interp(u,phases,heights)
        h,axis=radial_hit(tree,center,theta,z)
        f=min(u/.26,1.);f=f*f*(3-2*f)
        v=(h+axis*.54)*f+(anchor+np.array([0,0,z-anchor[2]]))*(1-f)
        path.append(v);directions.append(axis)
    edge0=[];edge1=[]
    for k,(v,axis) in enumerate(zip(path,directions)):
        tangent=detail.unit(path[min(k+1,len(path)-1)]-path[max(k-1,0)])
        across=detail.unit(np.cross(tangent,axis))
        row=[]
        for frac in np.linspace(-.5,.5,5):
            pt=v+across*(1.25*frac)
            ang=math.atan2(pt[0]-center[0],pt[1]-center[1])
            surf,out=radial_hit(tree,center,ang,pt[2])
            pt+=out*max(0,.35-np.dot(pt-surf,out))
            row.append(pt)
        points.extend(row);edge0.append(row[0]);edge1.append(row[-1])
    name=('Rear_Nape_Yoke' if rear else 'Temple_Webbing')+str(side)
    faces=[[k*5+j,k*5+j+1,k*5+6+j,k*5+5+j] for k in range(len(path)-1) for j in range(4)]
    ob=A.mesh(name,points,faces,'Webbing',thickness=.14,do_bind=False,radial_center=crown.origin)
    detail.project_uv(ob);detail.finish_normals(ob)
    for e,edge in enumerate([edge0,edge1]):detail.tube(name+'_Fold'+str(e),edge,.040,'Webbing',6)
    return anchor

def adjust_jaw(p,name,crown,tree):
    center=crown.old['center'];result=p.copy()
    for i,v in enumerate(p):
        theta=math.atan2(v[0]-center[0],v[1]-center[1])
        rear=name.startswith(('Occipital','Knurled','Dial_'))
        shift=3.75 if rear else 1.65*max(0,1-(abs(theta)/.95)**2)
        old,axis=radial_hit(tree,center,theta,v[2]);new,_=radial_hit(tree,center,theta,v[2]+shift)
        result[i]=v+new-old
    return result

def chin_sling(crown,tree):
    center=crown.old['center']
    path=[];angles=np.linspace(-.9,.9,61)
    for theta in angles:
        z=crown.top-21.95+1.45*(abs(theta)/.9)**1.8
        skin,axis=radial_hit(tree,center,theta,z)
        path.append(skin+axis*.36)
    path=np.array(path)
    for _ in range(3):path[1:-1]=.25*path[:-2]+.50*path[1:-1]+.25*path[2:]
    def build_strip(label,a,b,material,extra):
        vertices=[];edges=[[],[]]
        for i in range(a,b+1):
            angle=angles[i];axis=np.array([np.sin(angle),np.cos(angle),-.72*np.exp(-(angle/.5)**2)])
            axis=detail.unit(axis)
            tangent=detail.unit(path[min(i+1,len(path)-1)]-path[max(i-1,0)])
            across=detail.unit(np.cross(tangent,axis))
            halfwidth=.62 if not extra else .74+.16*np.cos(np.pi*angle/.90)
            row=[path[i]+axis*(extra+.055*(1-u*u))+across*(halfwidth*u) for u in np.linspace(-1,1,7)]
            vertices.extend(row);edges[0].append(row[0]);edges[1].append(row[-1])
        faces=[[i*7+j,i*7+j+1,i*7+j+8,i*7+j+7] for i in range(b-a) for j in range(6)]
        ob=A.mesh(label,vertices,faces,material,thickness=.12 if not extra else .16,do_bind=False,radial_center=crown.origin)
        detail.project_uv(ob);detail.finish_normals(ob)
        for i,e in enumerate(edges):detail.tube(label+'_Binding_'+str(i),e,.040,material,6)
    build_strip('Lower_Retention_Sling',0,len(path)-1,'Webbing',0.)
    build_strip('Chin_Cushion',16,44,'PadMesh',.15)

def build(rig):
    crown=Crown(rig)
    bpy.ops.wm.open_mainfile(filepath=str(OLD/'Models'/f'TS01_Helmet_{rig}_GAME.blend'))
    bpy.context.preferences.filepaths.save_version=0
    detail.HIGH=False
    A.MATS={key:bpy.data.materials['H1_'+key] for key in detail.FAMILIES}
    A.OBJECTS=[]
    shell_tree=crown.shell_tree()
    h=json.loads((OLD/'Inputs'/f'{rig}_Head.json').read_bytes())
    body=json.loads((OLD/'Inputs'/f'{rig}_Body.json').read_bytes())['bones']['head'];head=h['bones']['head']
    hp=(np.asarray(h['positions'])-head['position'])@np.linalg.inv(head['axes'])@body['axes']+body['position']
    headtree=BVHTree.FromPolygons(hp.tolist(),h['triangles'],all_triangles=True)
    for ob in list(bpy.context.scene.objects):
        if ob.type!='MESH' or ob.name.startswith('REFERENCE_ONLY_'):continue
        if ob.name.startswith(('Temple_Loop','Front_Crown_Loop')):
            bpy.data.objects.remove(ob,do_unlink=True);continue
        me=ob.data
        p=np.array([A.nativept(v.co) for v in me.vertices])
        if ob.name.startswith(('Suspension_Front','Suspension_Rear','Suspension_Anchor','Contoured_Chin','Chin_Closure')):
            bpy.data.objects.remove(ob,do_unlink=True);continue
        if ob.name.startswith(('Occipital','Knurled','Dial_')):
            result=adjust_jaw(p,ob.name,crown,headtree)
        elif ob.name.startswith(('Chin_Adjuster','Side_Release')):
            result=p
        elif ob.name.startswith(('Three_Point','Receiver_','Shroud_Hex_')):
            result=crown.front_hardware(p,shell_tree)
        else:
            result=crown.transfer(p)
        if result is not p:
            for v,pt in zip(me.vertices,result):v.co=detail.xyz(pt)
            detail.finish_normals(ob)
        A.OBJECTS.append(ob)
    chin_sling(crown,headtree)
    for side in (-1,1):
        for rear in [False,True]:
            anchor=suspension(crown,headtree,side,rear)
            a=(2.34 if rear else .78)*side;axis=crown.normal(a,.995)
            detail.screw('Yoke_Attachment_'+str(side)+'_'+str(rear),anchor+axis*.51,axis,.23)
        panel(crown,'Crown_Fabric_Front_'+str(side),.36,1.49,.22,.69,side)
        panel(crown,'Crown_Fabric_Rear_'+str(side),1.52,2.81,.21,.70,side)
        for k,(t0,t1) in enumerate([(.60,.62)]):
            lead=[crown.surface(side*a,t0+(t1-t0)*u,.14) for u,a in zip(np.linspace(0,1,33),np.linspace(.34,1.42,33))]
            detail.tube('Cover_Bound_Seam_'+str(side)+'_'+str(k),lead,.042,'LoopPile',6)
        # A low-profile retention cord runs from the front shroud to each rail.
        cord=[crown.surface(side*(.35+.58*u),.74+.16*u-.04*np.sin(np.pi*u),.20) for u in np.linspace(0,1,34)]
        detail.tube('Shroud_Retention_'+str(side),cord,.095,'Rubber',8)
    for ob in A.OBJECTS:clean(ob)
    bpy.context.scene['Revision']='HelmetContourR2'
    bpy.ops.object.select_all(action='DESELECT')
    for o in A.OBJECTS:o.select_set(True)
    bpy.context.view_layer.objects.active=A.OBJECTS[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'Models'/f'TS01_Helmet_{rig}_GAME.blend'))
    d=detail.payload(A.OBJECTS);detail.write(OUT/'Authored'/f'helmet_{rig}_world.json',d)
    body=json.loads((OLD/'Inputs'/f'{rig}_Body.json').read_bytes());frame=body['bones']['head'];axes=np.array(frame['axes'])
    d['positions']=((np.array(d['positions'])-frame['position'])@np.linalg.inv(axes)).tolist()
    normals=np.array(d['normals'])@axes.T;normals/=np.maximum(np.linalg.norm(normals,axis=2,keepdims=True),1e-8)
    d['normals']=normals.tolist();d['attachment_frame']=frame
    detail.write(OUT/'Authored'/f'helmet_{rig}_wear.json',d)
    print('CONTOUR_HELMET_AUTHORED',rig,len(d['triangles']),flush=True)

if __name__=='__main__':build(sys.argv[-1])
