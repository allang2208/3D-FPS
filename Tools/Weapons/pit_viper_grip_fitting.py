"""Source-fitted Pit Viper palm panels with explicit outside winding.

Blender authoring helper; coordinates remain in the native component reference.
The protected lower latch/cutout, front strap, backstrap and gun rig are retained.
"""
import math
import numpy as np
from mathutils import Vector


class PalmPanel:
    def __init__(self, bvh, alignment, root, side, nx=64, ny=112):
        self.bvh, self.root, self.side = bvh, root, side
        self.nx, self.ny = nx, ny
        z0, z1 = -.025+alignment.translation.z, -.067+alignment.translation.z
        rows=[]
        for j in range(ny+1):
            z=z0+(z1-z0)*j/ny
            center=.058-.30*(z-alignment.translation.z)+alignment.translation.y
            hits=[]
            for i in range(241):
                y=center-.036+i*.0003
                hit,_,_,_=bvh.ray_cast(Vector((side*.055,y,z)),Vector((-side,0,0)))
                hits.append(hit is not None and hit.x*side>.010)
            a=b=120
            if not hits[120]: raise RuntimeError('Native palm surface missing at '+str((side,z)))
            while a>0 and hits[a-1]: a-=1
            while b<240 and hits[b+1]: b+=1
            corner=.0018*max(0,1-min(j,ny-j)/7)**2
            rows.append((center-.036+a*.0003+.0011+corner,
                         center-.036+b*.0003-.0011-corner,z))
        edge=np.asarray([(a,b) for a,b,z in rows])
        kernel=np.array([1,2,3,4,5,4,3,2,1],dtype=float);kernel/=kernel.sum()
        smooth=np.column_stack([np.convolve(np.pad(edge[:,k],(4,4),mode='edge'),kernel,mode='valid') for k in (0,1)])
        edge=np.column_stack([np.maximum(edge[:,0],smooth[:,0]),np.minimum(edge[:,1],smooth[:,1])])
        self.rows=[(float(edge[j,0]),float(edge[j,1]),row[2]) for j,row in enumerate(rows)]
        # The original molded knurl has sharply varying normals. Sample an
        # outside envelope along the side axis so seams cannot sink into it.
        native=np.empty((ny+1,nx+1),dtype=float)
        for j,(low,high,z) in enumerate(self.rows):
            for i in range(nx+1):
                y=low+(high-low)*i/nx
                native[j,i]=self.hit(y,z).x*side
        pad=np.pad(native,((1,1),(1,1)),mode='edge')
        self.outside=np.maximum.reduce([pad[dy:dy+ny+1,dx:dx+nx+1] for dy in range(3) for dx in range(3)])

    def hit(self,y,z):
        hit,_,_,_=self.bvh.ray_cast(Vector((self.side*.055,y,z)),Vector((-self.side,0,0)))
        if hit is None: raise RuntimeError('Native side fit missed '+str((self.side,y,z)))
        return hit

    def location(self,u,v,offset=0):
        u,v=max(0,min(1,u)),max(0,min(1,v))
        r=v*self.ny;j=min(self.ny-1,int(r));t=r-j
        low,high,z=(self.rows[j][k]*(1-t)+self.rows[j+1][k]*t for k in range(3))
        y=low+(high-low)*u
        col=u*self.nx;i=min(self.nx-1,int(col));s=col-i
        x=(self.outside[j,i]*(1-s)+self.outside[j,i+1]*s)*(1-t)+(self.outside[j+1,i]*(1-s)+self.outside[j+1,i+1]*s)*t
        return self.root@Vector((self.side*(x+offset),y,z))

    def geometry(self, atlas=False, relief=None):
        verts,faces,uv=[],[],[]
        count=(self.nx+1)*(self.ny+1)
        for back in (False,True):
            for j,(low,high,z) in enumerate(self.rows):
                for i in range(self.nx+1):
                    u,v=i/self.nx,j/self.ny
                    fade=min(1,min(u,1-u,v,1-v)/.045)
                    offset=.000040 if back else .000090+.00019*fade
                    if not back and relief:offset+=float(relief(u,1-v))*fade
                    verts.append(self.location(u,v,offset))
                    uv.append((u,1-v) if atlas else ((low+(high-low)*u+.30*z)/.1,z/.1))
        idx=lambda i,j:j*(self.nx+1)+i
        for j in range(self.ny):
            for i in range(self.nx):
                f=(idx(i,j),idx(i+1,j),idx(i+1,j+1),idx(i,j+1))
                # In the canonical yz plane this winding points toward -X.
                if self.side>0:f=f[::-1]
                faces.append(f);faces.append(tuple(k+count for k in f[::-1]))
        boundary=[idx(i,0) for i in range(self.nx+1)]
        boundary+=[idx(self.nx,j) for j in range(1,self.ny+1)]
        boundary+=[idx(i,self.ny) for i in range(self.nx-1,-1,-1)]
        boundary+=[idx(0,j) for j in range(self.ny-1,0,-1)]
        for a,b in zip(boundary,boundary[1:]+boundary[:1]):
            f=(a,a+count,b+count,b)
            faces.append(f[::-1] if self.side>0 else f)
        return verts,faces,uv

    def record(self):
        return {'side':self.side,'length_m':abs(self.rows[-1][2]-self.rows[0][2]),
                'width_m':[min(b-a for a,b,z in self.rows),max(b-a for a,b,z in self.rows)],
                'edge_offset_m':.000090,'base_offset_m':.00028,'closed_shell':True,
                'normal_policy':'explicit exterior winding, canonical side axis'}
