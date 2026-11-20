"""Wearable game-art mesh primitives and the padded retention assembly."""
import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree


def unit(v):
    v=np.asarray(v,float)
    return v/np.maximum(np.linalg.norm(v,axis=-1,keepdims=True),1e-12)


class Studio:
    def __init__(self,mats,high,rig):
        self.mats=mats
        self.high=high
        self.rig=rig
        self.objs=[]
        self.group=None

    def mesh(self,name,p,f,mat,uvs=None,smooth=True):
        p=np.asarray(p,float)
        me=bpy.data.meshes.new(name)
        me.from_pydata((p*[.01,-.01,.01]).tolist(),[],f)
        me.update()
        bo=bmesh.new();bo.from_mesh(me)
        bmesh.ops.recalc_face_normals(bo,faces=list(bo.faces))
        bo.to_mesh(me);bo.free()
        ob=bpy.data.objects.new(name,me)
        (self.group or bpy.context.collection).objects.link(ob)
        me.materials.append(self.mats[mat]);self.objs.append(ob)
        span=float(self.mats[mat].get('PhysicalTile_cm',{'Webbing':4,'Stitch':2,'PadMesh':4,'Composite':8}.get(mat,4)))
        uv=me.uv_layers.new(name="SurfaceUV")
        for poly in me.polygons:
            poly.use_smooth=smooth
            dim=max(range(3),key=lambda k:abs(poly.normal[k]))
            axes=[j for j in range(3) if j!=dim]
            for li in poly.loop_indices:
                idx=me.loops[li].vertex_index
                uv.data[li].uv=(uvs[idx] if uvs is not None else p[idx,axes]/span)
        return ob

    def group_to(self,name):
        group=bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(group);self.group=group

    def cord(self,name,path,r,mat,closed=False,sides=None):
        v=np.asarray(path)
        if len(v)<2:return
        n=len(v);nside=sides or (10 if self.high else 6)
        p=[];axis=None
        for i,point in enumerate(v):
            tangent=unit(v[(i+1)%n]-v[(i-1)%n]) if closed else unit(v[min(i+1,n-1)]-v[max(0,i-1)])
            if axis is None:
                ref=[0,0,1.] if abs(tangent[2])<.93 else [0,1,0.]
                axis=unit(np.cross(tangent,ref))
            else:axis=unit(axis-tangent*np.dot(axis,tangent))
            right=np.cross(tangent,axis)
            p.extend(point+r*(np.cos(a)*axis+np.sin(a)*right) for a in np.arange(nside)*2*np.pi/nside)
        f=[(i*nside+k,i*nside+(k+1)%nside,((i+1)%n)*nside+(k+1)%nside,((i+1)%n)*nside+k)
           for i in range(n if closed else n-1) for k in range(nside)]
        if not closed:f.extend([tuple(reversed(range(nside))),tuple(range((n-1)*nside,n*nside))])
        return self.mesh(name,p,f,mat)

    def cushion(self,name,fn,width,height,mat,loft,reverse=False,seam=True,power=.48):
        # A rolled rectangular cushion with a sewn border and a softly crowned face.
        n=80 if self.high else 40
        theta=np.arange(n)*2*np.pi/n
        coords=np.stack([np.sign(np.cos(theta))*abs(np.cos(theta))**power,
                         np.sign(np.sin(theta))*abs(np.sin(theta))**power],axis=1)
        coords[np.abs(coords)<.0001]=0.
        loops=[(.12,.93),(.40,.95),(.68,.92),(.84,.83),(.93,.68),(.985,.40),
               (1.,.20),(.993,.04),(.92,0.)]
        curves=[];p=[];uv=[]
        for size,h in loops:
            ring=[]
            for u,v in coords*size:
                pt,normal=fn(u,v)
                ring.append(pt+normal*(loft*h))
                uv.append((u*width/4,v*height/4))
            p.extend(ring);curves.append(np.array(ring))
        f=[(i*n+k,i*n+(k+1)%n,(i+1)*n+(k+1)%n,(i+1)*n+k)
           for i in range(len(loops)-1) for k in range(n)]
        p.extend([fn(0,0)[0]+fn(0,0)[1]*(.93*loft),fn(0,0)[0]]);uv.extend([(0,0),(0,0)])
        f.extend([(len(p)-2,k,(k+1)%n) for k in range(n)])
        offset=n*(len(loops)-1)
        f.extend([(len(p)-1,offset+(k+1)%n,offset+k) for k in range(n)])
        self.mesh(name,p,f,mat,uv)
        if seam:self.cord(name+"_Welt",curves[4],min(abs(loft)*.105,.048),mat,True)


class Anatomy:
    def __init__(self,xyz,triangles,c):
        self.tree=BVHTree.FromPolygons(xyz.tolist(),triangles,all_triangles=True)
        self.org=c.origin[:2]

    def hit(self,a,z):
        direction=np.array([np.sin(a),np.cos(a),0.])
        center=np.array([*self.org,z])
        hit=self.tree.ray_cast(Vector(center+direction*42),Vector(-direction),68)[0]
        if hit is None:raise RuntimeError(f"Surfaceless strap section {a:.2f}, {z:.2f}")
        return np.array(hit),direction


def crown_board(c,x,y):
    angle=np.arctan2(x,y)
    r=np.hypot(x,y);lo,hi=0.,.74
    for _ in range(14):
        t=(lo+hi)*.5
        q=c.sample(angle,t)
        if np.linalg.norm(q[:2]-c.origin[:2])>r:hi=t
        else:lo=t
    t=(lo+hi)*.5
    return c.sample(angle,t),c.normal(angle,t)


def inside(s,c):
    s.group_to("02 · Comfort liner")
    # Segmented dark comfort pads and coyote backing, as visible in the official underside.
    def summit(u,v):
        p,n=crown_board(c,u*3.45,v*3.95-.60)
        return p-n*.79,-n
    s.cushion("Liner_Crown_Central_Island",summit,6.9,7.9,"Webbing",.65,power=.36)
    specs=[("Frontal",0,.68,.70,.24,1.06),
           ("Fore_Crown",0,.37,.78,.18,.85),
           ("Occipital",np.pi,.69,.67,.235,1.12),
           ("Rear_Crown",np.pi,.38,.79,.20,.89)]
    for sign in [-1,1]:
        specs+= [(label+("_L" if sign>0 else "_R"),sign*a,t,w,h,thick)
                 for label,a,t,w,h,thick in (("Temple",1.10,.77,.29,.22,1.12),("Parietal",1.95,.61,.34,.27,1.30))]
    for name,a,t,halfangle,halft,thickness in specs:
        def pad(u,v):
            aa=a+halfangle*u;tt=t+halft*v;n=c.normal(aa,tt)
            return c.sample(aa,tt)-n*.76,-n
        s.cushion("Liner_"+name+"_Backing",pad,halfangle*20,halft*34,"Webbing",.35)
        def pad_face(u,v):
            q,n=pad(u*.90,v*.86)
            return q+n*.28,n
        s.cushion("Liner_"+name+"_SpacerMesh",pad_face,halfangle*18,halft*31,"PadMesh",thickness)


def strip(s,name,path,axes,width,thick=.15,mat="Webbing",edge=True):
    path=np.asarray(path);axes=unit(axes)
    tangent=unit(np.gradient(path,axis=0));cross=unit(np.cross(tangent,axes))
    surface=unit(np.cross(cross,tangent))
    rows=[];uv=[];perim=[(-.50,0),(-.48,.42),(-.38,.52),(.38,.52),(.48,.42),(.50,0),(.48,-.42),(-.48,-.42)]
    length=np.concatenate([[0.],np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))])
    for i,(pt,d,n) in enumerate(zip(path,cross,surface)):
        w=width[i] if np.ndim(width) else width
        rows.append([pt+d*u*w+n*h*thick for u,h in perim])
        uv.extend([(u*w/4,length[i]/4) for u,h in perim])
    rows=np.asarray(rows);nr,nc=rows.shape[:2]
    faces=[(i*nc+j,i*nc+(j+1)%nc,(i+1)*nc+(j+1)%nc,(i+1)*nc+j) for i in range(nr-1) for j in range(nc)]
    faces.extend([tuple(reversed(range(nc))),tuple(range((nr-1)*nc,nr*nc))])
    s.mesh(name,rows.reshape(-1,3),faces,mat,uv)
    if edge:
        for j in (1,4):s.cord(name+("_FoldA" if j==1 else "_FoldB"),rows[:,j],.027,mat)
    return surface,cross


def dial(s,center,axis):
    # Recessed, lobed adjustment wheel; its stitched fabric saddle follows the nape.
    axis=unit(axis);right=np.array([1.,0.,0.]);up=unit(np.cross(axis,right))
    steps=120 if s.high else 60
    profile=[(1.23,0),(1.27,.11),(1.16,.22),(1.18,.32),(1.04,.43),(.93,.50),(.77,.51)]
    p=[]
    for j,(r,d) in enumerate(profile):
        for a in np.arange(steps)*2*np.pi/steps:
            rr=r-(.07*(.5+.5*np.cos(12*a))**2 if j in (2,3,4) else 0.)
            p.append(center+axis*d+rr*(right*np.cos(a)+up*np.sin(a)))
    f=[(i*steps+j,i*steps+(j+1)%steps,(i+1)*steps+(j+1)%steps,(i+1)*steps+j) for i in range(len(profile)-1) for j in range(steps)]
    f.extend([tuple(reversed(range(steps))),tuple(range((len(profile)-1)*steps,len(profile)*steps))])
    s.mesh("Nape_Tension_Dial",p,f,"Polymer")
    for sign in [-1,1]:
        pts=[center+axis*.526+right*sign*(.26+.18*t)+up*(.46-.27*t) for t in np.linspace(0,1,4)]
        s.cord("Dial_Moulded_Chevron_"+str(sign),pts,.031,"DarkPolymer",sides=5)


def cheek_connector(s,center,normal,side):
    """A sewn return on one cheek and the asymmetrical release on the other."""
    nr=unit(normal)
    across=unit(np.cross([0,0,1.],nr))
    along=unit(np.cross(nr,across))
    # Slight forward rake where the chin cup changes direction.
    tilt=.24*side
    across,along=unit(across+along*tilt),unit(along-across*tilt)
    label="Chin_Junction_"+("L" if side>0 else "R")
    def ring(name,w,h,holew,holeh,depth,origin,mat):
        steps=28 if s.high else 16
        theta=np.arange(steps)*2*np.pi/steps
        a=np.sign(np.cos(theta))*abs(np.cos(theta))**.36
        b=np.sign(np.sin(theta))*abs(np.sin(theta))**.36
        rings=[(w-.025,h-.025,0),(w,h,.04),(w,h,depth-.04),(w-.04,h-.04,depth),
               (holew,holeh,depth),(holew-.035,holeh-.035,depth-.04),(holew-.035,holeh-.035,0)]
        p=[origin+across*(u*x)+along*(v*y)+nr*z for x,y,z in rings for u,v in zip(a,b)]
        f=[(i*steps+j,i*steps+(j+1)%steps,((i+1)%len(rings))*steps+(j+1)%steps,
            ((i+1)%len(rings))*steps+j) for i in range(len(rings)) for j in range(steps)]
        s.mesh(label+"_"+name,p,f,mat)
    if side<0:
        ring("Female_Socket",.85,.54,.54,.27,.31,center,"Polymer")
        ring("Male_Strap_Slot",.77,.32,.54,.14,.21,center-along*.69,"Polymer")
        for sign in [-1,1]:
            s.cord(label+"_Squeeze_Lever_"+str(sign),[
                center+across*sign*.62-along*.67+nr*.13,
                center+across*sign*.75-along*.32+nr*.18,
                center+across*sign*.72+along*.12+nr*.18],.105,"DarkPolymer",sides=7)
        for y in (-.11,.08,.26):
            s.cord(label+"_Release_Grip_"+str(y),[center-across*.42+along*y+nr*.26,
                    center+across*.42+along*y+nr*.26],.065,"Polymer")
    else:
        ring("Return_Loop",.78,.42,.58,.23,.19,center,"Polymer")
        for y in (-.57,-.68):
            s.cord(label+"_Bar_Tack_"+str(y),[center-across*.53+along*y+nr*.05,
                    center+across*.53+along*y+nr*.05],.032,"Stitch")


def retention(s,c,head):
    s.group_to("03 · Retention system")
    base=c.top
    # Real rear cradle wraps under the back of the shell; dark spacer mesh
    # forms its skin side and a lower scallop reveals the tension dial.
    def occipital(u,v):
        # The sides taper under the back of the rail. Their upper corners
        # tuck below the shell instead of standing loose behind the ears.
        a=np.pi+.78*u
        edge=c.sample(a,1.)
        lower=2.06*(1.-u*u)+.50
        z=edge[2]-.28-.5*lower+v*(.88+.43*lower)
        pt,axis=head.hit(a,z)
        # The fabric sits against the nape while its exposed back supports the dial.
        projected=c.sample(a,.98)[:2]-c.origin[:2]
        rad=np.linalg.norm(pt[:2]-c.origin[:2])
        radius=max(rad+.77,np.linalg.norm(projected)-.98-.12*(1-v))
        return np.array([*(c.origin[:2]+axis[:2]*radius),z]),axis
    def nape_inside(u,v):
        pt,ax=occipital(u,v)
        return pt-ax*.48,-ax
    s.cushion("Nape_Hammock_Soft_Back",nape_inside,16,4.8,"PadMesh",.52,power=.67)
    s.cushion("Nape_Hammock_Coyote_Face",occipital,16,4.8,"Webbing",.35,power=.65)
    q,n=occipital(0,.10)
    dial(s,q+n*.32,n)

    for sign in [-1,1]:
        for back in (False,True):
            a0=(2.48 if back else .94)*sign
            start=c.surface(a0,.995,-.20)
            junction=.82*sign
            if back:
                k=[0,.20,.45,.72,1.]
                a=np.array([2.48,2.18,1.80,1.30,.82])*sign
                zs=[start[2]-.15,base-17.55,base-19.4,base-20.2,base-21.0]
            else:
                k=[0,.30,.60,1.]
                a=np.array([.94,1.0,.95,.82])*sign
                zs=[start[2],base-14.2,base-17.4,base-21.]
            path=[];dirs=[]
            endpoint,endpoint_ax=head.hit(junction,base-21.)
            endpoint+=endpoint_ax*.52
            for u in np.linspace(0,1,41 if s.high else 25):
                ang=np.interp(u,k,a);z=np.interp(u,k,zs)
                pt,axis=head.hit(ang,z)
                move=np.clip(u/.25,0,1);move=move*move*(3-2*move)
                point=(1-move)*(start+np.array([0,0,z-start[2]]))+move*(pt+axis*.48)
                if not back:
                    straight=start*(1-u)+endpoint*u
                    straight[2]=z
                    aa=np.arctan2(straight[0]-c.origin[0],straight[1]-c.origin[1])
                    skin,out=head.hit(aa,z)
                    clearance=np.dot(straight-skin,out)
                    point=straight+out*max(0.,.42-clearance)
                path.append(point);dirs.append(axis)
            label=("Rear_Yoke" if back else "Fore_Yoke")+("_L" if sign>0 else "_R")
            normal,across=strip(s,label,path,dirs,1.52 if back else 1.40)
            idx=int((.16 if not back else .21)*(len(path)-1))
            # Slider frame, central bar and doubled strap tail.
            o=path[idx]+normal[idx]*.17;r=across[idx];d=unit(np.cross(normal[idx],r))
            rect=[]
            for theta in np.arange(32)*2*np.pi/32:
                x=np.sign(np.cos(theta))*abs(np.cos(theta))**.36
                y=np.sign(np.sin(theta))*abs(np.sin(theta))**.36
                rect.append(o+r*x*.96+d*y*.61)
            s.cord(label+"_LadderLock",rect,.135,"Polymer",True,8)
            s.cord(label+"_ClampBar",[o-r*.83+normal[idx]*.04,o+r*.83+normal[idx]*.04],.12,"Polymer",sides=8)
            for tick in range(-2,3):
                at=o+r*tick*.22+normal[idx]*.145
                s.cord(label+"_ClampRib_"+str(tick),[at-d*.085,at+d*.085],.035,"Polymer")
            if not back:
                tail=np.array(path[idx:idx+max(3,len(path)//6)])+normal[idx:idx+max(3,len(path)//6)]*.19
                strip(s,label+"_FoldbackTail",tail,normal[idx:idx+len(tail)],1.22,.12,edge=False)
                for which in (1, len(tail)-2):
                    org=tail[which]+normal[idx+which]*.085
                    s.cord(label+"_BarTack_"+str(which),[org-across[idx+which]*.49,org+across[idx+which]*.49],.033,"Stitch")
        high=c.surface(sign*.94,.965,-.32);lower=c.surface(sign*.94,1.01,-.20)
        strip(s,"Front_Anchor_Loop_"+str(sign),[high,lower],[[sign,0,0],[sign,0,0]],1.51,.19,edge=False)
        pt,ax=head.hit(sign*.82,base-20.95)
        cheek_connector(s,pt+ax*.61,ax,sign)

    path=[];dirs=[];tang=np.linspace(-1,1,49 if s.high else 33)
    for t in tang:
        a=.82*t
        z=base-23.10+2.10*abs(t)**1.65
        pt,n=head.hit(a,z)
        # Stand off slightly at the centre under the jaw; the loop wraps
        # onto the tucked chin instead of floating across the mouth.
        path.append(pt+n*(.56-.08*abs(t)));dirs.append(unit(n+[0,0,-.42*(1-t*t)]))
    path=np.asarray(path)
    for _ in range(3):path[1:-1]=(path[:-2]+2*path[1:-1]+path[2:])*.25
    n,cross=strip(s,"Chin_Sling_Woven_Base",path,dirs,1.45)
    a,b=int(len(path)*.19),int(len(path)*.81)
    semi=np.sin(np.linspace(0,np.pi,b-a))
    strip(s,"Chin_Cup_Padded_Sleeve",path[a:b]+n[a:b]*.11,n[a:b],1.47+.34*semi,.32,"Webbing")
    for t in [a+2,a+4,b-5,b-3]:
        org=path[t]+n[t]*.30
        s.cord("Chin_Reinforcement_Tack_"+str(t),[org-cross[t]*.63,org+cross[t]*.63],.028,"Stitch")
