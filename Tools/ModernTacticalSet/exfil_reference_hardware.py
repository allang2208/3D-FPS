"""Cosmetic EXFIL Rail 2.0 hardware for the photographed coyote shell.

The label uses a distinct H1_Label face with upright, unmirrored 0..1 UVs
when seen looking at either side of the helmet. All other parts have UVs
in the physical tiling convention used by the rest of the outfit.
"""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt


def _cm(v):
    return (np.asarray(v)*[.01,-.01,.01]).tolist()


def _unit(v):
    return v/np.maximum(1.e-12,np.linalg.norm(v,axis=-1,keepdims=True))


def _inside(p,ring):
    x,y=p
    inside=False
    x0,y0=ring[-1]
    for x1,y1 in ring:
        if (y0>y)!=(y1>y) and x<(x1-x0)*(y-y0)/(y1-y0)+x0:
            inside=not inside
        x0,y0=x1,y1
    return inside


def _ring(points,step):
    out=[]
    for first,second in zip(points,np.roll(points,-1,axis=0)):
        a,b=np.asarray(first),np.asarray(second)
        n=max(1,int(math.ceil(np.linalg.norm(b-a)/step)))
        out.extend(a+(b-a)*(i/n) for i in range(n))
    return np.asarray(out)


def _round(x0,y0,x1,y1,r,steps=4):
    r=min(r,(x1-x0)*.499,(y1-y0)*.499)
    p=[]
    for x,y,a in [(x1-r,y1-r,0),(x0+r,y1-r,90),(x0+r,y0+r,180),(x1-r,y0+r,270)]:
        for angle in np.radians(np.linspace(a,a+90,steps)):
            p.append((x+r*np.cos(angle),y+r*np.sin(angle)))
    return p


def _circle(x,y,r,n):
    a=np.arange(n)*math.tau/n
    return np.stack((x+r*np.cos(a),y+r*np.sin(a)),axis=1)


def _inset(ring,distance):
    edges=_unit(np.roll(ring,-1,axis=0)-ring)
    area=np.sum(ring[:,0]*np.roll(ring[:,1],-1)-ring[:,1]*np.roll(ring[:,0],-1))
    normal=np.stack((-edges[:,1],edges[:,0]),axis=1)*np.sign(area)
    previous=np.roll(normal,1,axis=0)
    vector=(previous+normal)/np.maximum(.05,1+(previous*normal).sum(1))[:,None]
    vector/=np.maximum(1.,np.linalg.norm(vector,axis=1)/2.1)[:,None]
    return ring+distance*vector


class Builder:
    def __init__(self,crown,rig,high):
        self.crown=crown
        self.rig=rig
        self.high=high
        self.parts=[]
        self.prefix='EXFIL_'
        rings=46
        cols=160
        a=np.arange(cols)*math.tau/cols
        p=[crown.sample(0.,.0001)]
        for t in np.linspace(1/rings,1,rings):
            p.extend(crown.sample(a,t))
        f=[(0,1+(i+1)%cols,1+i) for i in range(cols)]
        for k in range(rings-1):
            for i in range(cols):
                l=1+k*cols+i;r=1+k*cols+(i+1)%cols
                f.extend([(l,r,r+cols),(l,r+cols,l+cols)])
        self.tree=BVHTree.FromPolygons(p,f,all_triangles=True)
        self.front_base=crown.sample(0.,1)[2]+.90

    def front(self,uv,offset):
        # Sample the shell in a front orthographic projection. The central
        # insert has smaller curvature than its two cast lateral wings.
        uv=np.asarray(uv);offset=np.broadcast_to(offset,len(uv))
        p=[]
        for (x,v),d in zip(uv,offset):
            z=self.front_base+v
            loc=self.tree.ray_cast(Vector((x,32,z)),Vector((0,-1,0)),60)[0]
            if loc is None:
                raise ValueError(f'Front cosmetic shroud misses {self.rig} shell at {x:.2f},{z:.2f}')
            p.append((x,loc.y+d,z))
        return np.asarray(p)

    def side(self,side):
        crown=self.crown
        def project(uv,offset):
            uv=np.asarray(uv)
            angle=np.radians(150-6.6*uv[:,0])*side
            z=crown.top+uv[:,1]
            lo=np.zeros(len(uv));hi=np.full(len(uv),1.073)
            for _ in range(14):
                mid=(lo+hi)*.5
                above=crown.sample(angle,mid)[:,2]>z
                lo=np.where(above,mid,lo);hi=np.where(above,hi,mid)
            t=(hi+lo)*.5
            return crown.sample(angle,t)+crown.normal(angle,t)*np.broadcast_to(offset,len(uv))[:,None]
        return project

    def mesh(self,name,points,faces,mat,smooth=True,uvs=None):
        me=bpy.data.meshes.new(self.prefix+name)
        me.from_pydata(_cm(points),[],faces);me.update()
        ob=bpy.data.objects.new(self.prefix+name,me)
        bpy.context.scene.collection.objects.link(ob)
        me.materials.append(bpy.data.materials['H1_'+mat])
        bm=bmesh.new();bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
        bm.to_mesh(me);bm.free();me.update()
        uv=me.uv_layers.new(name='EXFIL_UV')
        coords=np.asarray(points)
        for face in me.polygons:
            face.use_smooth=smooth
            if uvs is None:
                dominant=np.argmax(np.abs(face.normal))
                axes=[i for i in range(3) if i!=dominant]
            for li in face.loop_indices:
                vid=me.loops[li].vertex_index
                uv.data[li].uv=uvs[vid] if uvs is not None else tuple(coords[vid,axes]/4.)
        if smooth and hasattr(me,'set_sharp_from_angle'):
            me.set_sharp_from_angle(angle=.65)
        self.parts.append(ob)
        return ob

    def plate(self,name,outer,holes,project,back,face,mat='Polymer',bevel=.045,step=.57):
        r=min(bevel,.43*(face-back))
        original=[_ring(boundary,step) for boundary in [outer,*holes]]
        rings=[_inset(ring,r if index==0 else -r) for index,ring in enumerate(original)]
        xy=[];edges=[]
        for ring in rings:
            start=len(xy)
            xy.extend(ring)
            edges.extend((start+i,start+(i+1)%len(ring)) for i in range(len(ring)))
        bounds=np.asarray(outer)
        # Additional interior vertices follow the changing shell curvature.
        for i,u in enumerate(np.arange(bounds[:,0].min()+step*.47,bounds[:,0].max(),step)):
            for v in np.arange(bounds[:,1].min()+step*(.30+.33*(i%2)),bounds[:,1].max(),step):
                if _inside((u,v),rings[0]) and not any(_inside((u,v),h) for h in rings[1:]):
                    xy.append((u,v))
        points,_,tris,_,_,_=delaunay_2d_cdt([Vector(p) for p in xy],edges,[],0,1.e-6)
        points=np.array(points);surfaces=[]
        for tri in tris:
            center=points[list(tri)].mean(0)
            if _inside(center,rings[0]) and not any(_inside(center,h) for h in rings[1:]):
                surfaces.append(tuple(tri))
        count=len(points);f=list(surfaces)+[tuple(i+count for i in reversed(t)) for t in surfaces]
        # Boundary edges from the actual tessellation include vertices split
        # by the triangulator on long rails and at tangencies.
        boundary={}
        for tri in surfaces:
            for i,j in zip(tri,tri[1:]+tri[:1]):
                edge=min(i,j),max(i,j)
                boundary[edge]=boundary.get(edge,0)+1
        outline=[e for e,uses in boundary.items() if uses==1]
        ids=np.array(sorted({i for edge in outline for i in edge}),dtype=int)
        remap={v:k for k,v in enumerate(ids)}
        p=[project(points,back),project(points,face)]
        # Maintain the rounded wall throughout corners and holes. A global
        # bevel modifier on tessellated curved caps can create slivers wherever
        # a triangulation vertex lands very close to a lip.
        wall0=np.vstack(rings)
        wall1=np.vstack([np.roll(ring,-1,axis=0) for ring in rings])
        raw0=np.vstack(original)
        raw1=np.vstack([np.roll(ring,-1,axis=0) for ring in original])
        lines=wall1-wall0
        rr=np.maximum((lines*lines).sum(1),1.e-15)
        inner=points[ids]
        raw=[]
        for v in inner:
            along=np.clip(((v-wall0)*lines).sum(1)/rr,0,1)
            j=int(np.argmin(((v-(wall0+along[:,None]*lines))**2).sum(1)))
            raw.append(raw0[j]+(raw1[j]-raw0[j])*along[j])
        raw=np.array(raw)
        angle=np.linspace(0,np.pi/2,5 if self.high else 3)[1:]
        levels=[(np.sin(a),back+r*(1-np.cos(a))) for a in angle]
        levels.extend((np.sin(a),face-r*(1-np.cos(a))) for a in reversed(angle))
        current=ids
        for q,height in levels:
            next_ids=2*count+(len(p)-2)*len(ids)+np.arange(len(ids))
            p.append(project(inner+(raw-inner)*q,height))
            for a,b in outline:
                i,j=remap[a],remap[b]
                f.append((current[i],current[j],next_ids[j],next_ids[i]))
            current=next_ids
        for a,b in outline:
            i,j=remap[a],remap[b]
            f.append((current[i],current[j],b+count,a+count))
        return self.mesh(name,np.concatenate(p),f,mat)

    def tube(self,name,path,radius,mat,n=None,closed=False):
        path=np.asarray(path)
        n=n or (9 if self.high else 6);s=len(path)
        tangent=_unit(np.roll(path,-1,axis=0)-np.roll(path,1,axis=0))
        if not closed:
            tangent[0]=_unit(path[1]-path[0]);tangent[-1]=_unit(path[-1]-path[-2])
        basis=np.array([0.,0.,1.])
        if abs(basis@tangent[0])>.82:basis=np.array([1.,0.,0.])
        lateral=_unit(np.cross(tangent[0],basis));p=[]
        for point,axis in zip(path,tangent):
            lateral=_unit(lateral-axis*(axis@lateral))
            vertical=np.cross(axis,lateral)
            for a in np.arange(n)*math.tau/n:
                p.append(point+radius*(lateral*np.cos(a)+vertical*np.sin(a)))
        faces=[(j*n+i,j*n+(i+1)%n,((j+1)%s)*n+(i+1)%n,((j+1)%s)*n+i) for j in range(s if closed else s-1) for i in range(n)]
        if not closed:faces.extend([tuple(range(n-1,-1,-1)),tuple((s-1)*n+i for i in range(n))])
        return self.mesh(name,p,faces,mat)

    def screw(self,name,project,x,y,depth,radius):
        # A countersunk black surround, a domed screw head, and a real six-
        # sided recess share one surface of revolution and a recessed floor.
        n=36 if self.high else 18
        a=np.arange(n)*math.tau/n
        p=[]
        for r,h,hexagonal in [(1.04,-.025,False),(1.,.018,False),(.81,.04,False),(.77,.14,False),(.62,.18,False),(.37,.17,True),(.29,.038,True)]:
            rad=radius*r
            if hexagonal:rad=rad*np.cos(np.pi/6)/np.cos((a+np.pi/6)%(np.pi/3)-np.pi/6)
            p.extend(project(np.stack([x+rad*np.cos(a),y+rad*np.sin(a)],axis=1),depth+h))
        f=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for j in range(6) for i in range(n)]
        base=len(p);p.append(np.mean(p[:n],axis=0))
        recess=len(p);p.append(np.mean(p[6*n:7*n],axis=0))
        f.extend((base,(i+1)%n,i) for i in range(n))
        f.extend((recess,6*n+i,6*n+(i+1)%n) for i in range(n))
        self.mesh(name,p,f,'Metal')

    def front_casting(self):
        # Front-view contour traced from the manufacturer's coyote Rail 2
        # gallery. UV-plane coordinates are artwork coordinates.
        def trace(p):
            # Fit the lateral wings against both visible side screws in the
            # supplied oblique view. The screws retain circular heads.
            return [((x-302)*.0673,(279-y)*.052) for x,y in p]
        outline=trace([(285,122),(292,118),(313,118),(321,123),(328,142),(339,150),
            (344,158),(346,164),(393,199),(401,209),(402,226),(398,232),(385,239),
            (339,273),(331,279),(272,279),(265,275),(216,240),(204,233),(200,227),
            (201,210),(207,202),(258,163),(262,151),(277,144)])
        openings=[]
        left=[[(259,176),(259,207),(236,196)],[(259,217),(259,251),(232,233)],
              [(277,140),(281,149),(269,149)]]
        for hole in left:
            openings.append(trace(hole))
            openings.append(trace([(604-x,y) for x,y in hole]))
        openings.append(trace([(276,168),(331,168),(331,249),(276,249)]))
        self.plate('Shroud_cast_perimeter_vented',outline,openings,self.front,-.012,.36,bevel=.085)
        # The front window is recessed all the way back to the coated
        # shell. A flat retaining frame and the central rounded spring tab
        # cast separate shadows across it.
        outer=trace([(268,153),(336,153),(342,158),(342,254),(338,259),(266,259),(262,254),(262,160)])
        window=trace([(279,168),(326,168),(331,174),(331,243),(326,248),(279,248),(275,244),(275,174)])
        self.plate('Shroud_recessed_insert',outer,[window],self.front,.32,.96,bevel=.072)
        self.plate('Shroud_upper_ledge',trace([(266,154),(338,154),(342,157),(340,164),(264,164),(262,160)]),[],self.front,.88,1.23,bevel=.066)
        self.plate('Shroud_lower_ledge',trace([(267,247),(337,247),(341,253),(337,259),(268,259),(263,254)]),[],self.front,.85,1.17,bevel=.064)
        self.plate('Shroud_lower_latch_recess',trace([(270,262),(334,262),(332,274),(327,275),(323,269),(281,269),(276,276),(272,273)]),[],self.front,.345,.69,bevel=.047)
        self.plate('Shroud_insert_rounded_tab',trace([(291,167),(313,167),(315,178),(314,187),(311,192),(307,196),(300,197),(295,195),(291,191),(289,185),(290,175)]),[],self.front,.31,.61,bevel=.06)
        for i,(x,y,r) in enumerate([(302,133,.54),(219,218,.51),(388,218,.51)]):
            u,v=trace([(x,y)])[0]
            self.screw('Shroud_black_captive_'+str(i),self.front,u,v,.37,r)
        for i,(x,y) in enumerate([(268,254),(337,254)]):
            u,v=trace([(x,y)])[0]
            self.screw('Shroud_insert_pin_'+str(i),self.front,u,v,1.16,.096)

    def badge(self,side,project):
        tag='L' if side>0 else 'R'
        shell_projection=project
        def project(uv,offset):
            return shell_projection(np.asarray(uv)+[.15,.65],offset)
        # The wider tan loop field is visible behind the dark molded ID badge.
        backing=_round(4.05,-5.18,10.18,.18,.33,5)
        self.plate('Rail2_loop_field_'+tag,backing,[],project,-.009,.14,'LoopPile',.043)
        # Each needle pass lies in the tan attachment field. Build the dashes
        # into one mesh so the inventory renderer handles them as one object.
        curve=_ring(_round(4.14,-5.07,10.08,.085,.26,7),.13)
        curve=np.vstack((curve,curve[0]))
        length=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(curve,axis=0),axis=1))]
        stations=np.linspace(0,length[-1],int(length[-1]/.23)+1)
        starts=stations[:-1]+.03
        ends=stations[1:]-.025
        ticks=np.stack((starts,(starts+ends)*.5,ends),axis=1).ravel()
        points=np.stack([np.interp(ticks,length,curve[:,j]) for j in (0,1)],axis=1)
        centers=project(points,np.tile([.138,.164,.139],len(starts))).reshape(-1,3,3)
        rings=6 if self.high else 4
        angle=np.arange(rings)*math.tau/rings
        verts=[];faces=[]
        for path in centers:
            first=len(verts)
            axis=_unit(path[-1]-path[0])
            normal=_unit(np.cross(axis,[side,0,0]))
            binormal=np.cross(axis,normal)
            for v in path:
                verts.extend(v+.013*(np.cos(angle)[:,None]*normal+np.sin(angle)[:,None]*binormal))
            faces.extend((first+j*rings+k,first+j*rings+(k+1)%rings,first+(j+1)*rings+(k+1)%rings,first+(j+1)*rings+k) for j in (0,1) for k in range(rings))
            faces.extend([tuple(first+j for j in range(rings-1,-1,-1)),tuple(first+2*rings+j for j in range(rings))])
        self.mesh('Rail2_loop_attachment_stitches_'+tag,verts,faces,'Stitch')
        outer=_round(4.29,-3.64,9.92,-.13,.22,5)
        self.plate('Rail2_badge_bound_edge_'+tag,outer,[],project,.135,.245,'Webbing',.038)
        border=_ring(_round(4.34,-3.58,9.87,-.18,.19,5),.21)
        self.tube('Rail2_badge_piping_'+tag,project(border,.251),.035,'Stitch',closed=True)
        nx,ny=16,10
        uv=[(i/nx,j/ny) for j in range(ny+1) for i in range(nx+1)]
        xy=np.array([[4.43+5.35*u,-3.48+3.20*v] for u,v in uv])
        f=[(j*(nx+1)+i,j*(nx+1)+i+1,(j+1)*(nx+1)+i+1,(j+1)*(nx+1)+i) for j in range(ny) for i in range(nx)]
        # The native-to-Blender Y reflection reverses the polygon order.
        if side>0:f=[tuple(reversed(q)) for q in f]
        proper=[(1-u if side>0 else u,v) for u,v in uv]
        self.mesh('EXFIL_BALLISTIC_badge_face_'+tag,project(xy,.256),f,'Label',uvs=proper)

    def rail(self,side):
        tag='L' if side>0 else 'R'
        project=self.side(side)
        # The load-bearing rail follows the upper ear cut and turns into a
        # long swept tab aft. The four rear voids and rectangular strap slot
        # are genuine silhouette holes, visible from the back of the rail.
        outline=[(.13,-13.50),(.10,-12.91),(.42,-11.60),(.80,-9.08),(1.36,-6.40),
            (1.80,-5.08),(2.20,-4.65),(2.71,-4.55),(3.04,-4.78),(4.67,-4.70),
            (4.95,-3.93),(5.22,-3.79),(7.28,-3.84),(7.54,-4.43),(10.75,-4.59),
            (11.63,-4.84),(13.70,-5.01),(13.24,-7.30),(12.79,-7.68),(12.31,-8.37),
            (11.29,-8.42),(10.39,-7.18),(9.25,-6.60),(7.71,-6.43),(6.14,-6.40),
            (5.08,-6.52),(4.06,-7.13),(3.24,-8.65),(2.53,-10.17),(1.84,-12.17),
            (1.39,-13.45),(.76,-13.70)]
        holes=[[(5.16,-4.53),(7.16,-4.55),(7.12,-4.18),(5.32,-4.12)],
               [(1.03,-12.87),(1.49,-11.18),(.85,-11.81),(.69,-12.89)],
               [(1.27,-10.42),(2.16,-10.02),(1.74,-10.95)],
               [(1.71,-8.48),(2.81,-8.09),(2.30,-9.43)],
               [(2.19,-7.04),(3.52,-6.79),(2.96,-7.61)],
               [(3.01,-5.35),(4.19,-5.28),(4.25,-5.94),(3.20,-6.54)],
               _circle(10.88,-5.52,.36,18 if self.high else 14)]
        self.plate('Rail2_swept_ear_bridge_'+tag,outline,holes,project,-.016,.38,bevel=.059,step=.48)
        self.plate('Rail2_front_recess_floor_'+tag,[(11.34,-4.95),(13.39,-5.12),(13.02,-6.35),(11.81,-6.31),(11.43,-6.09)],[],project,.371,.405,'DarkPolymer',.025)
        self.plate('Rail2_front_bezel_'+tag,[(11.26,-4.86),(13.57,-5.04),(13.19,-6.55),(11.65,-6.48),(11.28,-6.04)],
                   [[(11.61,-5.14),(13.13,-5.27),(12.91,-6.22),(11.89,-6.17),(11.58,-5.95)]],project,.383,.50,bevel=.035)
        foundation=[(3.52,-6.44),(3.45,-5.10),(3.81,-4.85),(10.59,-4.85),
                    (10.68,-6.08),(10.10,-6.51),(8.22,-6.57),(7.97,-6.32),(4.32,-6.29)]
        self.plate('Rail2_crossbar_base_'+tag,foundation,[],project,.35,.64,bevel=.05)
        self.plate('Rail2_center_badge_rebate_'+tag,_round(3.95,-6.17,7.99,-5.02,.12),[],project,.61,.73,'DarkPolymer',.029)
        self.plate('Rail2_center_cassette_'+tag,_round(4.03,-6.10,7.94,-5.09,.09),[],project,.713,.79,bevel=.032)
        logo=_circle(6.00,-5.59,.30,28 if self.high else 18)
        logo[:,0]=6.+(logo[:,0]-6.)*1.70
        self.tube('Rail2_cassette_stamp_border_'+tag,project(logo,.803),.017,'Polymer',closed=True)
        stamp=[(5.68,-5.40),(5.80,-5.78),(5.93,-5.48),(6.03,-5.78),(6.18,-5.40)]
        self.tube('Rail2_cassette_stamp_'+tag,project(np.asarray(stamp),.813),.024,'Polymer')
        for i,u in enumerate((8.28,8.97,9.67)):
            self.plate('Rail2_stepped_rib_'+tag+str(i),[(u-.18,-6.43),(u-.18,-4.95),(u-.09,-4.74),(u+.17,-4.77),
                       (u+.22,-4.95),(u+.22,-6.40),(u+.12,-6.56),(u-.08,-6.56)],[],project,.612,.94,bevel=.059)
        # The rear foot has a raised outer edge and an inset channel.
        path=np.asarray([(.39,-13.18),(.66,-11.82),(1.13,-9.8),(1.53,-8.04),(1.91,-6.39),(2.40,-5.23)])
        self.tube('Rail2_aft_molded_bead_'+tag,project(path,.40),.093,'Polymer')
        for i,(x,y,r,h) in enumerate([(4.51,-5.59,.23,.795),(7.44,-5.62,.23,.795),(1.49,-10.99,.27,.38),(2.57,-5.02,.19,.39)]):
            self.screw('Rail2_fastener_'+tag+str(i),project,x,y,h,r)
        self.badge(side,project)


def build(crown,rig,high):
    """Create helmet-mounted game art. Return every newly linked mesh."""
    b=Builder(crown,rig,high)
    b.front_casting()
    for side in (-1,1):
        b.rail(side)
    return b.parts
