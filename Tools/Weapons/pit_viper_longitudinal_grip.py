"""Native-shaped long side skins, ending at the original magwell shoulder."""
import numpy as np
from mathutils import Vector
from pit_viper_grip_fitting import PalmPanel

def palm_limits(parts):
    host=next(p for p in parts if p['identity']=='2011pv frame_12' and p['material']=='polymer')
    vertices=[Vector(v) for v in host['verts']];palm=[]
    for face in host['faces']:
        points=[vertices[i] for i in face]
        n=(points[1]-points[0]).cross(points[2]-points[0])
        if n.length<1e-10:continue
        if (abs(n.normalized().x)>.9 and min(abs(p.x) for p in points)>.010
            and min(p.z for p in points)<-.060 and max(p.z for p in points)>-.022
            and sum(p.y for p in points)/len(points)>.050):palm.extend(points)
    if not palm:raise RuntimeError('Native longitudinal palm surfaces are missing')
    # Grip body and magazine interface are distinct parts. The wider native
    # lower flare is not a surface to extend the skin onto, even where it is
    # present in the donor frame mesh. End above its earliest shoulder.
    flare=[v for v in vertices if abs(v.x)>.01585 and v.z<-.050 and v.y>.050]
    bottom=min(p.z for p in palm)+.0012
    if flare:bottom=max(bottom,max(v.z for v in flare)+.0012)
    return max(p.z for p in palm)-.0012,bottom

def palm_lower_boundary(parts):
    """Lower edge of the long OUTER palm faces, not the frame's bottom cap."""
    host=next(p for p in parts if p['identity']=='2011pv frame_12' and p['material']=='polymer')
    vertices=[Vector(v) for v in host['verts']];edge=set()
    for face in host['faces']:
        points=[vertices[i] for i in face]
        n=(points[1]-points[0]).cross(points[2]-points[0])
        if n.length<1e-10:continue
        if (abs(n.normalized().x)>.9 and min(abs(p.x) for p in points)>.014
            and min(p.z for p in points)<-.060 and max(p.z for p in points)>-.022):
            edge.update((float(p.y),float(p.z)) for p in points if p.z<-.060)
    points=np.asarray(sorted(edge));slope,intercept=np.polyfit(points[:,0],points[:,1],1)
    return float(slope),float(intercept)

class LongitudinalPalmPanel(PalmPanel):
    def __init__(self,bvh,alignment,root,side,limits,lower_line,nx=64,ny=160):
        self.bvh,self.root,self.side=bvh,root,side;self.nx,self.ny=nx,ny
        self.lower_line=lower_line
        z0,z1=(z+alignment.translation.z for z in limits)
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
            if not hits[120]:raise RuntimeError('Native grip body absent at '+str((side,z)))
            while a>0 and hits[a-1]:a-=1
            while b<240 and hits[b+1]:b+=1
            corner=.0014*max(0,1-min(j,ny-j)/6)**2
            rows.append((center-.036+a*.0003+.0011+corner,center-.036+b*.0003-.0011-corner,z))
        edge=np.asarray([(a,b) for a,b,z in rows]);kernel=np.array([1,2,3,4,5,4,3,2,1],dtype=float);kernel/=kernel.sum()
        smoothed=np.column_stack([np.convolve(np.pad(edge[:,k],(4,4),mode='edge'),kernel,mode='valid') for k in (0,1)])
        edge=np.column_stack([np.maximum(edge[:,0],smoothed[:,0]),np.minimum(edge[:,1],smoothed[:,1])])
        self.rows=[(float(edge[j,0]),float(edge[j,1]),r[2]) for j,r in enumerate(rows)]
        native=np.empty((ny+1,nx+1),dtype=float)
        for j,(low,high,z) in enumerate(self.rows):
            for i in range(nx+1):native[j,i]=self.hit(low+(high-low)*i/nx,z).x*side
        pad=np.pad(native,((1,1),(1,1)),mode='edge')
        self.outside=np.maximum.reduce([pad[dy:dy+ny+1,dx:dx+nx+1] for dy in range(3) for dx in range(3)])
        # The original magwell/latch projects beyond the palm body. End each
        # longitudinal column at its actual upper contour, rather than painting
        # across it or stopping every column on an arbitrary horizontal line.
        stops=[]
        for i in range(nx+1):
            stop=ny
            for j in range(int(ny*.65),ny+1):
                low,high,z=self.rows[j];y=low+(high-low)*i/nx
                # Native bottom seam slopes across the grip. A horizontal
                # Z cutoff would wrap onto its raised lower cap at the rear.
                boundary=lower_line[0]*(y-alignment.translation.y)+lower_line[1]+.0012
                if z-alignment.translation.z<boundary or self.outside[j,i]>.01585:
                    stop=max(1,j-2);break
            stops.append(stop/ny)
        stop=np.asarray(stops);padded=np.pad(stop,(2,2),mode='edge')
        self.ends=np.minimum.reduce([padded[k:k+nx+1] for k in range(5)])
        self.nominal_length=abs(z1-z0)
        self.atlas_height=self.nominal_length*float(np.mean(self.ends))
        self.atlas_width=float(np.mean([b-a for a,b,z in self.rows[:int(ny*.65)]]))

    def location(self,u,v,offset=0):
        u,v=max(0,min(1,u)),max(0,min(1,v));column=u*self.nx
        i=min(self.nx-1,int(column));s=column-i
        end=self.ends[i]*(1-s)+self.ends[i+1]*s
        return super().location(u,v*float(end),offset)

    def record(self):
        record=super().record()
        record.update(design='full longitudinal native palm outline on each side',
            fitted_height_m=[self.nominal_length*float(np.min(self.ends)),self.nominal_length*float(np.max(self.ends))],
            nominal_native_palm_length_m=self.nominal_length,atlas_height_m=self.atlas_height,
            atlas_width_m=self.atlas_width,lower_boundary='above native lower flare and magazine interface, 1.2 mm clearance; per-column raised latch exclusion',
            native_lower_seam_z_from_y=list(self.lower_line),
            upper_boundary='native palm shoulder, inset 1.2 mm')
        return record
