"""Measured, smoothly sampled native torso surfaces for all carrier layers."""
import math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

class CarrierSurface:
    def __init__(self,body,skin_slot=2):
        p=np.asarray(body['positions']);f=np.asarray(body['triangles']);c=p[f].mean(axis=1)
        mask=(c[:,2]>96)&(c[:,2]<157)&(abs(c[:,0])<24)
        if skin_slot is not None:mask&=(np.asarray(body['triangle_materials'])==skin_slot)
        self.tree=BVHTree.FromPolygons(p.tolist(),f[mask].tolist(),all_triangles=True)
        self.x=np.linspace(-21,21,169);self.z=np.linspace(100,144,177)
        self.fields={}
        for side in [-1,1]:
            field=np.empty((len(self.z),len(self.x)))
            for j,z in enumerate(self.z):
                for i,x in enumerate(self.x):
                    # Stop at the torso centre. Through an open native chest
                    # section a full-depth ray would wrongly return the back.
                    hit=self.tree.ray_cast(Vector((x,side*60,z)),Vector((0,-side,0)),60-side*1.5-.5)[0]
                    field[j,i]=hit.y if hit is not None else np.nan
            # Fill missing outer columns from their last measured torso point.
            for row in field:
                ok=np.isfinite(row)
                if ok.any():row[:]=np.interp(self.x,self.x[ok],row[ok])
            # Shorter native bodies end below this shared sampling domain.
            # Extend their measured edge instead of inventing a neck surface.
            for column in field.T:
                ok=np.isfinite(column)
                if not ok.any():raise ValueError('No torso samples for carrier envelope')
                column[:]=np.interp(self.z,self.z[ok],column[ok])
            self.fields[side]=self.blur(field)
        self.tx=np.linspace(-17,17,137);self.ty=np.linspace(-14,17,125)
        top=np.full((len(self.ty),len(self.tx)),135.)
        for j,y in enumerate(self.ty):
            for i,x in enumerate(self.tx):
                hit=self.tree.ray_cast(Vector((x,y,159)),Vector((0,0,-1)),25)[0]
                if hit is not None:top[j,i]=hit.z
        self.top=self.blur(top)
        self.carriers={}
        for side,bodyfield in self.fields.items():
            dz,dx=np.gradient(bodyfield,self.z,self.x)
            outer=bodyfield+side*2.35*np.minimum(1.65,np.sqrt(1+dx*dx+dz*dz))
            # The body is open at section boundaries. Keep the measured
            # front/back ray envelope; a nearest-face sign near the neckline
            # is not a closed-volume distance and must not drive extrusion.
            outer*=side
            pad=np.pad(outer,((3,3),(3,3)),mode='edge')
            envelope=np.maximum.reduce([pad[j:j+len(self.z),i:i+len(self.x)] for j in range(7) for i in range(7)])
            self.carriers[side]=side*(self.blur(self.blur(envelope))+.10)

    @staticmethod
    def blur(a):
        # 1 cm smoothing removes muscle tessellation without shrinking the fit.
        for _ in range(3):
            p=np.pad(a,((0,0),(1,1)),mode='edge');a=(p[:,:-2]+2*p[:,1:-1]+p[:,2:])*.25
            p=np.pad(a,((1,1),(0,0)),mode='edge');a=(p[:-2]+2*p[1:-1]+p[2:])*.25
        return a

    @staticmethod
    def sample(a,xs,ys,x,y):
        fx=float(np.clip((x-xs[0])/(xs[-1]-xs[0])*(len(xs)-1),0,len(xs)-1.00001))
        fy=float(np.clip((y-ys[0])/(ys[-1]-ys[0])*(len(ys)-1),0,len(ys)-1.00001))
        i=int(fx);j=int(fy);u=fx-i;v=fy-j
        return float((a[j,i]*(1-u)+a[j,i+1]*u)*(1-v)+(a[j+1,i]*(1-u)+a[j+1,i+1]*u)*v)

    def front(self,x,z,side):return self.sample(self.fields[side],self.x,self.z,x,z)

    def carrier(self,x,z,side,offset):
        return np.array([x,self.sample(self.carriers[side],self.x,self.z,x,z)+side*(offset-1.7),z])

    def front_clearance(self,x,z,side,offset):
        dx=(self.front(x+.25,z,side)-self.front(x-.25,z,side))/.5
        dz=(self.front(x,z+.25,side)-self.front(x,z-.25,side))/.5
        return (offset+.65)*min(1.65,math.sqrt(1+dx*dx+dz*dz))

    def normal(self,point):
        near,n,face,distance=self.tree.find_nearest(Vector(point))
        return -np.array(n)

    def project(self,point,clearance):
        p=np.array(point,dtype=float)
        for _ in range(4):
            near,n,face,distance=self.tree.find_nearest(Vector(p));normal=-np.array(n)
            signed=float(np.dot(p-np.array(near),normal))
            if signed>=clearance-.001:break
            p+=normal*(clearance-signed)
        return p

    def strap(self,sign):
        us=np.linspace(0,1,31);vs=np.linspace(0,1,81);radii=np.zeros((len(vs),len(us)))
        for j,v in enumerate(vs):
            theta=math.pi*v;direction=np.array([0,math.cos(theta),math.sin(theta)])
            for i,u in enumerate(us):
                x=sign*(10.8+1.4*math.sin(theta))+(u-.5)*4.7;center=np.array([x,1.5,138.5])
                hit=self.tree.ray_cast(Vector(center+direction*30),Vector(-direction),30)[0]
                radii[j,i]=np.linalg.norm(np.array(hit)-center) if hit is not None else 7
        # A soft strap bridges small anatomical hollows, rather than copying
        # the discontinuous vertical silhouette into the sewn shoulder edge.
        expanded=np.pad(radii,((2,2),(2,2)),mode='edge')
        radii=np.maximum.reduce([expanded[j:j+len(vs),i:i+len(us)] for j in range(5) for i in range(5)])
        radii=self.blur(radii)+.75
        envelope=radii.copy()
        # One smooth bend across the entire strap width. Individual closest-
        # point corrections create pinched folds where the trapezius turns.
        for _ in range(1):
            curve=np.stack([np.polyval(np.polyfit(vs,envelope[:,i],6),vs) for i in range(len(us))],axis=1)
            curve+=np.maximum(0,np.max(envelope-curve,axis=0))[None,:]+.025
            for j in range(len(vs)):
                fit=np.polyval(np.polyfit(us,curve[j],2),us);curve[j]=fit+max(0,float(np.max(curve[j]-fit)))
            required=curve.copy()
            for j,v in enumerate(vs):
                theta=math.pi*v;direction=np.array([0,math.cos(theta),math.sin(theta)])
                for i,u in enumerate(us):
                    x=sign*(10.8+1.4*math.sin(theta))+(u-.5)*4.7
                    p=np.array([x,1.5,138.5])+curve[j,i]*direction
                    required[j,i]=curve[j,i]
            envelope=required
        coefficients=np.array([np.polyfit(vs,envelope[:,i],6) for i in range(len(us))])
        corrections=np.array([max(0,float(np.max(envelope[:,i]-np.polyval(coefficients[i],vs))))+.03 for i in range(len(us))])
        def evaluate(u,v):
            theta=math.pi*v;x=sign*(10.8+1.4*math.sin(theta))+(u-.5)*4.7
            radius=float(np.interp(u,us,[np.polyval(c,v)+e for c,e in zip(coefficients,corrections)]))
            return np.array([x,1.5+radius*math.cos(theta),138.5+radius*math.sin(theta)])
        return evaluate

    def shoulder(self,x,y):return self.sample(self.top,self.tx,self.ty,x,y)

    def flank(self,point,offset):
        p=np.asarray(point,dtype=float);center=np.array([0,2.5,p[2]])
        direction=p-center;direction/=np.linalg.norm(direction)
        hit=self.tree.ray_cast(Vector(center+direction*45),Vector(-direction),45)[0]
        if hit is not None:
            radius=np.linalg.norm(np.array(hit)-center)+offset
            p=center+direction*max(np.linalg.norm(p-center),radius)
        return p
