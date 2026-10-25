"""Detailed game belt, detachable carriers and non-functional magazine visual props.

Uses actual saved ST6 trousers for each fitted waist and native body weights.
No game integration, garment replacement, animation test or preview rendering.
"""
import ast
import bpy
import bmesh
import gc
import hashlib
import json
import math
import shutil
from pathlib import Path
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

P=Path('D:/FPS3D/FPSGAME');R=P/'SourceAssets/TacticalMagazineBelt20261024';E=R/'Exports';TAU=math.tau
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def bv(p):return Vector((p[0]*.01,-p[1]*.01,p[2]*.01))
def unit(v):return np.asarray(v)/max(float(np.linalg.norm(v)),1.e-12)
def smooth_circular(v,sigma=2):
    k=np.arange(-int(sigma*3),int(sigma*3)+1);w=np.exp(-.5*(k/sigma)**2);w/=w.sum()
    return sum(np.roll(v,int(i),axis=0)*q for i,q in zip(k,w))
def bary(p,tri):
    a,b,c=tri;v0=b-a;v1=c-a;v2=p-a;d00=v0@v0;d01=v0@v1;d11=v1@v1;den=max(d00*d11-d01*d01,1.e-15)
    v=(d11*(v2@v0)-d01*(v2@v1))/den;w=(d00*(v2@v1)-d01*(v2@v0))/den
    q=np.maximum([1-v-w,v,w],0);return q/max(q.sum(),1.e-12)

# Frozen project primitives keep this source reproducible independently of caps.
tree=ast.parse((P/'Tools/TacticalMagazineBelt/primitives.py').read_text(encoding='utf-8'))
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Cap'],type_ignores=[]),'belt_geometry_primitives','exec'))
SURFACES=read(R/'textures.json')['maps'];SURFACE={x['name']:x for x in SURFACES}
MAG={'rifle':dict(width=6.3,depth=2.5,height=15.6,curve=.62,material=7,slot_width=7.7,slot_depth=3.65,slot_height=10.8),
     'pistol':dict(width=2.85,depth=2.35,height=12.1,curve=.10,material=8,slot_width=3.85,slot_depth=3.40,slot_height=8.9)}


class Belt(Cap):
    def __init__(self,row):
        self.row=row;self.body=row['body'];self.native=read(row['native_reference'])
        self.bones=self.native['bones'];self.bone_by={x['name']:x for x in self.bones}
        self.body_points=np.array(self.native['positions']);self.body_faces=np.array(self.native['triangles'],dtype=np.int32)
        self.pants_points=np.fromfile(R/'Inputs'/f'{self.body}_positions.bin',dtype='<f4').reshape(-1,3)
        self.pants_faces=np.fromfile(R/'Inputs'/f'{self.body}_triangles.bin',dtype='<i4').reshape(-1,3)
        right=np.array(self.bone_by['thigh_r']['position'])-np.array(self.bone_by['thigh_l']['position']);right[2]=0;self.right=unit(right)
        forward=sum(np.array(self.bone_by['ball_'+s]['position'])-np.array(self.bone_by['foot_'+s]['position']) for s in ('l','r'));forward[2]=0
        self.forward=unit(forward-self.right*(forward@self.right));self.up=np.array([0.,0.,1.])
        self.origin=np.array(self.bone_by['pelvis']['position']);self.origin[2]=0
        self.fit_waist()
        z=self.top.mean();centers=self.body_points[self.body_faces].mean(1)
        self.weight_faces=self.body_faces[(centers[:,2]>z-17)&(centers[:,2]<z+8)&(np.abs(centers[:,0]-self.origin[0])<32)]
        self.weight_tree=BVHTree.FromPolygons([Vector(p) for p in self.body_points],self.weight_faces.tolist(),all_triangles=True)
        bpy.ops.wm.read_factory_settings(use_empty=True);self.scene=bpy.context.scene;self.scene.unit_settings.system='METRIC';self.scene.unit_settings.scale_length=1
        self.cols={}
        for name in ('01_EDITABLE_LOD0','02_EXPORT_LOD1','03_EXPORT_LOD2','04_MAGAZINES_SEATED','05_MAGAZINE_MASTERS','06_NATIVE_REFERENCES','07_HIGH_SURFACE_SOURCES','08_SLOT_ANCHORS'):
            col=bpy.data.collections.new(name);self.scene.collection.children.link(col);self.cols[name]=col
        self.objects=[];self.mats=[];self.level=0;self.active_frame=None;self.active_weights=None;self.active_kind='belt';self.weights={};self.sockets=[]
        for row in SURFACES:self.make_material(row)
        mat=bpy.data.materials.new('Belt_Tonal_Stitch');mat.use_nodes=True;bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(.07,.077,.082,1);bs.inputs['Roughness'].default_value=.87;self.mats.append(mat)

    def fit_waist(self):
        ps=self.pants_points;delta=ps-self.origin
        angles=np.mod(np.arctan2(delta@self.right,delta@self.forward),TAU)
        high=ps[:,2].max();region=ps[:,2]>high-10.;tops=[];count=256
        for a in np.arange(count)*TAU/count:
            da=np.abs((angles-a+math.pi)%TAU-math.pi);sel=region&(da<.055)
            if not np.any(sel):sel=region&(da<.11)
            tops.append(float(ps[sel,2].max()))
        self.top=smooth_circular(np.array(tops),2.0);self.na=count;self.height=6.8
        geometry=BVHTree.FromPolygons([Vector(p) for p in ps],self.pants_faces.tolist(),all_triangles=True)
        radii=np.zeros((9,count));fallback=0
        for j,v in enumerate(np.linspace(0,1,9)):
            for i,a in enumerate(np.arange(count)*TAU/count):
                direction=self.right*math.sin(a)+self.forward*math.cos(a)
                z=self.top[i]-.35-self.height*(1-v)
                start=self.origin+np.array([0,0,z]);travel=0.;last=None
                for _ in range(16):
                    hit,normal,face,dist=geometry.ray_cast(Vector(start+direction*travel),Vector(direction),40-travel)
                    if hit is None:break
                    travel=float((np.array(hit)-start)@direction)+.008;last=travel
                    if travel>=38:break
                if last is None:
                    da=np.abs((angles-a+math.pi)%TAU-math.pi);sel=(da<.09)&(np.abs(ps[:,2]-z)<1.2)
                    if not np.any(sel):raise RuntimeError('Waist source has no surface at '+str((self.body,a,z)))
                    last=float(np.max((ps[sel]-start)@direction));fallback+=1
                radii[j,i]=last
        # Smooth cloth-scale ripples while retaining an outward envelope over the
        # source waistband, belt loops and fasteners at every sampled height.
        self.radii=np.stack([np.maximum(smooth_circular(q,2),q)+.32 for q in radii])
        pts=np.array([self.point(a,.5,0) for a in np.linspace(0,TAU,1025)])
        self.arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(pts,axis=0),axis=1))];self.arc_angles=np.linspace(0,TAU,1025);self.perimeter=float(self.arc[-1])
        self.fit_report=dict(body=self.body,pants_asset=self.row['pants_asset'],package_sha256=self.row['package_sha256'],front_axis=self.forward.tolist(),right_axis=self.right.tolist(),circumference_cm=self.perimeter,waist_width_cm=float(np.ptp(pts@self.right)),waist_depth_cm=float(np.ptp(pts@self.forward)),waist_top_range_cm=[float(self.top.min()),float(self.top.max())],belt_width_cm=self.height,source_samples=count*9,nearby_surface_fallbacks=fallback,fit_tested=False)
        write(R/'Authored'/f'{self.body}_waist_fit.json',self.fit_report)
        print('BELT_WAIST_AUTHORED',self.body,round(self.perimeter,2),flush=True)

    def sample(self,array,a):
        f=(a%TAU)/TAU*self.na;i=int(f)%self.na;t=f-int(f);return array[i]*(1-t)+array[(i+1)%self.na]*t

    def point(self,a,v=.5,offset=0):
        v=float(np.clip(v,0,1));j=min(7,int(v*8));t=v*8-j
        radius=self.sample(self.radii[j],a)*(1-t)+self.sample(self.radii[j+1],a)*t
        direction=self.right*math.sin(a)+self.forward*math.cos(a)
        return self.origin+direction*(radius+offset)+self.up*(self.sample(self.top,a)-.35-self.height*(1-v))

    def angle(self,arc):return float(np.interp(arc%self.perimeter,self.arc,self.arc_angles))
    def outward(self,a):return unit(self.right*math.sin(a)+self.forward*math.cos(a))
    def frame_at(self,arc,offset=1.35):
        a=self.angle(arc);normal=self.outward(a);tangent=unit(self.point(a+.001)-self.point(a-.001));tangent=unit(tangent-self.up*(tangent@self.up))
        return self.point(a,.5,offset),np.stack((tangent,normal,self.up),axis=1)

    def native_weights(self,p):
        q,_,face,_=self.weight_tree.find_nearest(Vector(p));tri=self.weight_faces[face];bc=bary(np.array(q),self.body_points[tri]);out={}
        for vi,amount in zip(tri,bc):
            for bi,w in self.native['weights'][int(vi)]:out[int(bi)]=out.get(int(bi),0)+float(w*amount)
        out=dict(sorted(out.items(),key=lambda x:-x[1])[:8]);total=sum(out.values());return {k:v/total for k,v in out.items() if v/total>1.e-5}

    def make_material(self,row):
        name=row['name'];m=bpy.data.materials.new(name);m.use_nodes=True;n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
        bs.inputs['Sheen Weight'].default_value=.17 if row['kind'] in ('nylon','webbing','pad') else 0
        for channel in ('BaseColor','Normal','ORM'):
            tex=n.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(R/'Textures'/f'T_{name}_{channel}.png'),check_existing=True);tex.extension='REPEAT'
            if channel=='BaseColor':l.new(tex.outputs['Color'],bs.inputs['Base Color'])
            else:
                tex.image.colorspace_settings.name='Non-Color'
                if channel=='Normal':
                    normal=n.new('ShaderNodeNormalMap');l.new(tex.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs[0],bs.inputs['Normal'])
                else:
                    sep=n.new('ShaderNodeSeparateColor');l.new(tex.outputs['Color'],sep.inputs[0]);l.new(sep.outputs['Green'],bs.inputs['Roughness']);l.new(sep.outputs['Blue'],bs.inputs['Metallic'])
        m['physical_tile_cm']=row['tile_m']*100;self.mats.append(m)

    def mesh(self,name,points,faces,mat=0,uv=None,slots=None,col=None):
        local=np.asarray(points,dtype=float);world=local if self.active_frame is None else local@self.active_frame[1].T+self.active_frame[0]
        ob=super().mesh(name,world,faces,mat,uv,slots,col)
        if uv is None:
            layer=ob.data.uv_layers.active
            for poly,face in zip(ob.data.polygons,faces):
                q=local[list(face)];normal=np.cross(q[1]-q[0],q[2]-q[0]);axes=[k for k in range(3) if k!=int(np.argmax(np.abs(normal)))]
                for li,vi in zip(poly.loop_indices,poly.vertices):layer.data[li].uv=(local[vi,axes[0]]/4,local[vi,axes[1]]/4)
        ob['assembly_kind']=self.active_kind
        if col is None:
            self.weights[ob.name]=[self.active_weights.copy() if self.active_weights is not None else self.native_weights(p) for p in world]
        return ob

    def solid(self,ob,cm,inner_mat=None):return super().solid(ob,cm,inner_mat)

    def local(self,arc,offset=1.35,kind='carrier'):
        self.active_frame=self.frame_at(arc,offset);self.active_weights=self.native_weights(self.active_frame[0]);self.active_kind=kind

    def world(self):self.active_frame=None;self.active_weights=None;self.active_kind='belt'

    def tube(self,name,paths,radius,mat,sides=6,closed=False):
        return super().tube(name,paths,radius,mat,sides if self.level==0 else max(4,sides-2),closed)

    def stitch(self,name,path,normals,mat=9,pitch=.32,radius=.017):
        return super().stitch(name,path,normals,mat,pitch,radius)

    def band(self,name,arc0,arc1,v0,v1,inner,outer,mat,n=160,puff=0):
        na=max(8,round(n*(arc1-arc0)/self.perimeter));nv=6 if self.level==0 else 3
        aa=[self.angle(x) for x in np.linspace(arc0,arc1,na+1)];ps=[];uv=[];fs=[]
        for off in (inner,outer):
            for j,v in enumerate(np.linspace(v0,v1,nv+1)):
                for i,a in enumerate(aa):
                    bulge=puff*math.sin(math.pi*i/na)*math.sin(math.pi*j/nv) if off==inner else 0
                    ps.append(self.point(a,v,off-bulge));uv.append(((arc1-arc0)*i/na/4,v*self.height/4))
        m=(na+1)*(nv+1)
        for side in (0,1):
            for j in range(nv):
                for i in range(na):
                    k=side*m+j*(na+1)+i;fs.append([k,k+1,k+na+2,k+na+1])
        for j in (0,nv):
            for i in range(na):k=j*(na+1)+i;fs.append([k,k+1,k+1+m,k+m])
        for i in (0,na):
            for j in range(nv):k=j*(na+1)+i;fs.append([k,k+na+1,k+na+1+m,k+m])
        return self.mesh(name,ps,fs,mat,uv)

    def tailoring(self):
        self.world();density=(240,144,88)[self.level];end=self.perimeter-3.7
        self.band('Belt_01_Inner_Facing',3.7,end,.12,.88,.12,.34,1,n=density)
        # Individually padded cells keep their seam channels and the front clear.
        cells=max(8,round((self.perimeter-12)/7.3));edges=np.linspace(5.8,self.perimeter-5.8,cells+1)
        for i,(a,b) in enumerate(zip(edges[:-1],edges[1:])):
            self.band(f'Pad_{i:02d}_Mesh_Cushion',a+.10,b-.10,.05,.95,.37,.85,3,n=density,puff=.19)
            if self.level<2:
                path=[self.point(self.angle(a+.24),v,.36) for v in np.linspace(.12,.88,20)]
                self.stitch(f'Pad_{i:02d}_Quilt_Seam',path,[-self.outward(self.angle(a))]*len(path))
        self.band('Belt_02_Main_Carry_Shell',3.7,end,0,1,.87,1.12,0,n=density)
        self.band('Belt_03_Center_Webbing',3.7,end,.19,.81,1.13,1.22,1,n=density)
        for v in (.025,.975):
            path=[self.point(self.angle(s),v,1.10) for s in np.linspace(3.72,end,density+1)]
            self.tube('Belt_Rolled_Edge', [path],.105,1,sides=8)
        for v in (.075,.12,.88,.925):
            aa=[self.angle(s) for s in np.linspace(3.78,end,density+1)]
            self.stitch('Belt_Double_Edge_Stitch',[self.point(a,v,1.145) for a in aa],[self.outward(a) for a in aa])
        # Modular loops are curved to this body rather than flat plates sunk in it.
        for i,s in enumerate(np.arange(7.0,self.perimeter-6,4.2)):
            for lo,hi in ((.22,.40),(.60,.78)):
                n=10 if self.level==0 else 6;ps=[];uv=[];fs=[]
                for j,v in enumerate(np.linspace(lo,hi,3)):
                    for k,t in enumerate(np.linspace(0,1,n+1)):
                        a=self.angle(s+(t-.5)*3.8);ps.append(self.point(a,v,1.24+.16*math.sin(math.pi*t)));uv.append((t*.95,v*self.height/4))
                for j in range(2):
                    for k in range(n):q=j*(n+1)+k;fs.append([q,q+1,q+n+2,q+n+1])
                self.solid(self.mesh(f'Modular_Loop_{i:02d}',ps,fs,1,uv),.065)
            if self.level==0:
                a=self.angle(s-1.73)
                for v in (.31,.69):
                    path=[self.point(self.angle(s-1.73+x),v+z,1.27) for x,z in [(-.06,-.075),(.06,.075),(-.06,.06),(.06,-.06)]]
                    self.tube('Loop_Bar_Tack',[path],.022,9,4)
        # Belt keepers fold around the actual carry shell.
        for arc in (5.9,-5.9,self.perimeter*.37,self.perimeter*.63):
            a=self.angle(arc);path=[];norm=[]
            for v,off in [(0,.72),(0,1.40),(.1,1.47),(.5,1.47),(.9,1.47),(1,1.40),(1,.72)]:
                path.append(self.point(a,v,off));norm.append(self.outward(a))
            self.ribbon('Keeper_Folded_Webbing',path,norm,1.15,1,.11)

    def fastener(self,name,x,y,z,r=.15):
        ring=[[x+r*math.cos(a),y,z+r*math.sin(a)] for a in np.linspace(0,TAU,17)[:-1]]
        self.tube(name+'_Rim',[ring],.035,5,6,closed=True)
        self.box(name+'_Inset',(x,y-.015,z),(r*1.35,.04,.075),4,.024)

    def buckle(self):
        self.local(0,1.55,'buckle')
        for sign in (-1,1):
            self.frame('Buckle_Webbing_Window', (sign*2.5,0,0),2.05,4.9,1.03,3.93,.52,5)
            self.box('Buckle_Sculpted_Half',(sign*1.1,.005,0),(1.55,.57,4.48),5,.28)
            self.box('Buckle_Inner_Shadow_Seam',(sign*.22,-.06,0),(.13,.21,3.2),4,.035)
            self.box('Buckle_Webbing_Return',(sign*3.0,-.22,0),(.83,.17,3.8),1,.09)
            for z in (-1.78,1.78):self.fastener('Buckle_Rivet',sign*1.18,.315,z,.11)
        for z in (-1.95,1.95):
            self.box('Buckle_Recessed_Release',(0,.03,z),(1.05,.46,.56),4,.19)
            self.box('Buckle_Release_Ridge',(0,.29,z),(.54,.08,.13),5,.055)
        self.world()

    def fitted_mount(self,arc,kind):
        self.local(arc,1.70,'carrier');origin,basis=self.active_frame;m=MAG[kind]
        local=(self.pants_points-origin)@basis;bottom=-m['slot_height']*.57
        region=(np.abs(local[:,0])<m['slot_width']*.5+.45)&(local[:,2]>bottom-.25)&(local[:,2]<bottom+m['slot_height']+.2)
        # Carrier backs are rigid. Place their entire footprint beyond the actual
        # trouser hip envelope, then route their straps back around the fitted belt.
        peak=float(local[region,1].max())
        extra=max(0.,peak+.80);self.local(arc,1.70+extra,'carrier')
        return extra

    def carrier(self,name,kind,arc=None):
        m=MAG[kind];w=m['slot_width'];d=m['slot_depth'];h=m['slot_height'];z0=-h*.57;z1=z0+h;cy=.30+d/2
        n=(10,7,4)[self.level];ps=[];uv=[];fs=[];slots=[];rings=[]
        # Real closed-bottom vessel: exterior, folded rim, inner wall, inner floor.
        sections=[(w-.26,d-.20,z0,.45),(w,d,z0+.55,.49),(w,d,z1-.40,.49),(w+.12,d+.12,z1,.53),
                  (w-.55,d-.55,z1,.31),(w-.61,d-.61,z1-.45,.29),(w-.64,d-.64,z0+.36,.28)]
        for wi,di,z,rad in sections:
            ring=self.rounded_rect(wi,di,min(rad,di*.24),n);rings.append(ring)
            for x,y in ring:ps.append([x,cy+y,z]);uv.append((x/4,(z+abs(y))/4))
        nr=len(rings[0])
        for j in range(len(sections)-1):
            for i in range(nr):fs.append([j*nr+i,j*nr+(i+1)%nr,(j+1)*nr+(i+1)%nr,(j+1)*nr+i]);slots.append(1 if j==3 else 3 if j>=4 else 4)
        fs.extend([list(reversed(range(nr))),list(range((len(sections)-1)*nr,len(sections)*nr))]);slots.extend([4,3])
        shell=self.mesh(name+'_Hollow_Carrier',ps,fs,4,uv,slots);shell['opening']='true cavity with modeled inner wall and floor';shell['magazine_kind']=kind
        rim=[[x,cy+y,z1+.015] for x,y in rings[3]]
        self.tube(name+'_Rolled_Opening_Binding',[rim],.105,1,8,True)
        self.stitch(name+'_Rim_Seam',rim+[rim[0]],[[0,0,1]]*(len(rim)+1),pitch=.27)
        # Sewn textile jacket outside the semi-rigid insert, rounded corner wrap.
        outer=self.rounded_rect(w+.14,d+.14,.55,n);ps=[];uv=[];fs=[];nh=6 if self.level==0 else 3
        for j,t in enumerate(np.linspace(0,1,nh+1)):
            z=z0+.6+t*(h-1.15)
            for i,(x,y) in enumerate(outer):
                scale=1+.009*math.sin(t*math.pi)*math.sin(i*.9+t*4);ps.append([x*scale,cy+y*scale,z]);uv.append((i/len(outer)*(w+d)/2,z/4))
        for j in range(nh):
            for i in range(len(outer)):k=j*len(outer)+i;fs.append([k,j*len(outer)+(i+1)%len(outer),(j+1)*len(outer)+(i+1)%len(outer),k+len(outer)])
        self.solid(self.mesh(name+'_Nylon_Outer_Sleeve',ps,fs,0,uv),.07)
        # Wrap bands and olive tapes remain genuine thickness, not painted stripes.
        for z in (z0+h*.31,z0+h*.66):
            path=np.array([[x,cy+y,z] for x,y in self.rounded_rect(w+.25,d+.25,.60,n)])
            norms=[unit([p[0],p[1]-cy,0]) for p in path];path=np.vstack((path,path[0]));norms.append(norms[0])
            self.ribbon(name+'_Elastic_Retention',path,norms,.62 if kind=='rifle' else .49,6,.08)
            for x in (-w*.30,w*.30):self.box(name+'_Band_Keeper',(x,cy+d/2+.21,z),(.65,.16,.91),1,.10)
        for sign in (-1,1):
            x=sign*(w/2-.65);y=cy+d/2+.135
            path=[np.array([x,y,z]) for z in np.linspace(z0+.45,z1-.2,14)]
            self.ribbon(name+'_Olive_Reinforcing_Tape',path,[[0,1,0]]*len(path),.64 if kind=='rifle' else .44,2,.09)
            for dx in (-.19,.19):self.stitch(name+'_Tape_Double_Stitch',[p+[dx,.015,0] for p in path],[[0,1,0]]*len(path),pitch=.24)
            edge=[[sign*(w/2-.12),cy+d/2-.16,z] for z in np.linspace(z0+.42,z1-.25,12)]
            self.tube(name+'_Corner_Protector',[edge],.10,4,8)
        # Two strap-through rear bridges and folded attachment tapes.
        for x in (-w*.26,w*.26):
            self.frame(name+'_Rear_Mount_Bridge',(x,.12,-.15),1.24,5.6,.65,4.83,.30,4)
            if arc is None:
                path=[np.array([x,y,z]) for y,z in [(-.08,-2.9),(-.45,-2.7),(-.50,2.55),(.05,2.78),(.34,2.45),(.35,-2.1)]]
            else:
                origin,basis=self.active_frame;a=self.angle(arc+x)
                def belt_point(v,offset):return (self.point(a,v,offset)-origin)@basis
                path=[np.array([x,.35,-2.1]),np.array([x,.35,2.45]),belt_point(1,1.35),belt_point(1,.26),belt_point(.8,.26),belt_point(.2,.26),belt_point(0,.26),belt_point(0,1.35),np.array([x,.10,-2.65])]
            self.ribbon(name+'_Mounting_Webbing',path,[[0,-1,0]]*len(path),.60,1,.10)
            if self.level<2:self.fastener(name+'_Mount_Snap',x,.43,-2.0,.14)
        # Exposed bottom cap and a restrained front face stitching frame.
        self.box(name+'_Bottom_Impact_Cap',(0,cy,z0+.12),(w-.35,d-.14,.42),4,.18)
        path=[np.array([x,cy+d/2+.19,z]) for x,z in self.rounded_rect(w-.68,h*.43,.26,n)]
        path=[p+np.array([0,0,z0+h*.48]) for p in path];path.append(path[0])
        self.stitch(name+'_Sleeve_Perimeter_Stitch',path,[[0,1,0]]*len(path),pitch=.26)
        return dict(kind=kind,local_seat=[0,cy,z0+.52],slot_floor_z=z0+.36,slot_top_z=z1,opening_width=w-.55,opening_depth=d-.55)

    def magazine(self,name,kind,seat):
        m=MAG[kind];w,d,h=m['width'],m['depth'],m['height'];seat=np.array(seat);n=(10,7,4)[self.level];nz=(20,12,7)[self.level];ps=[];uv=[];fs=[]
        def point(x,y,z):return seat+np.array([x+m['curve']*(z/h)**2,y,z])
        # Exterior-only game prop with a sealed insertion end and no feed internals.
        for j,z in enumerate(np.linspace(0,h-.42,nz+1)):
            taper=.94+.06*min(z/.8,1);rr=self.rounded_rect(w*taper,d*taper,min(.31,d*.18),n)
            for i,(x,y) in enumerate(rr):ps.append(point(x,y,z));uv.append((i/len(rr)*(w+d)/2,z/4))
        nr=4*n
        for j in range(nz):
            for i in range(nr):k=j*nr+i;fs.append([k,j*nr+(i+1)%nr,(j+1)*nr+(i+1)%nr,k+nr])
        fs.extend([list(reversed(range(nr))),list(range(nz*nr,(nz+1)*nr))])
        ob=self.mesh(name+'_Exterior_Casing',ps,fs,m['material'],uv);ob['game_visual_prop_only']=True
        # Narrow recessed seams, shallow molded grip ribs and separate base plate.
        for sign in (-1,1):
            y=sign*(d/2+.035)
            for x in np.linspace(-w*.32,w*.32,4 if kind=='rifle' else 2):
                p=[point(x,y,z) for z in np.linspace(1.5,h-1.1,nz)]
                self.ribbon(name+'_Long_Grip_Rib',p,[[0,sign,0]]*len(p),.14 if kind=='rifle' else .10,m['material'],.045)
            seam=[point(sign*(w/2-.13),0,z) for z in np.linspace(.6,h-.55,nz)]
            self.tube(name+'_Parting_Seam',[seam],.025,4,5)
            for z in np.linspace(2.0,h-2,5 if kind=='rifle' else 4):
                p=[point(x,y+sign*.03,z+.08*math.cos(x*1.1)) for x in np.linspace(-w*.39,w*.39,12)]
                self.ribbon(name+'_Grip_Crossbar',p,[[0,sign,0]]*len(p),.13,4,.045)
        center=point(0,0,h-.20)
        self.box(name+'_Separate_Baseplate',center,(w+.26,d+.28,.45),4,.14)
        self.box(name+'_Baseplate_Inset',point(0,0,h+.03),(w*.72,d*.63,.055),m['material'],.08)
        self.box(name+'_Sealed_Visual_End',point(0,0,.14),(w*.92,d*.91,.28),4,.11)
        if self.level<2:
            for x in np.linspace(-w*.33,w*.33,7 if kind=='rifle' else 4):
                p=[point(x,y,h+.065) for y in np.linspace(-d*.27,d*.27,4)]
                self.tube(name+'_Base_Grip_Groove',[p],.025,1,5)

    def build(self,level):
        self.level=level;start=len(self.objects);self.tailoring();self.buckle();mounts=[]
        for name,kind,arc in [('Rifle_A','rifle',-12),('Rifle_B','rifle',-21),('Pistol_A','pistol',11),('Pistol_B','pistol',16)]:
            standoff=self.fitted_mount(arc,kind);carrier_start=len(self.objects);spec=self.carrier(name,kind,arc)
            origin,basis=self.active_frame;seat=origin+basis@np.array(spec['local_seat'])
            entry=dict(name=name,arc_cm=arc,additional_hip_standoff_cm=standoff,origin_cm=origin.tolist(),basis=basis.tolist(),seat_cm=seat.tolist(),weights=self.active_weights.copy(),**spec)
            mounts.append(entry)
            for ob in self.objects[carrier_start:]:ob['slot_name']=name
        self.world();result=self.objects[start:]
        print('BELT_GEOMETRY_BUILT',self.body,level,len(result),flush=True)
        return result,mounts

    def rehome(self,objects,key):
        for ob in objects:
            for col in list(ob.users_collection):col.objects.unlink(ob)
            self.cols[key].objects.link(ob)

    def native_rig(self):
        arm=bpy.data.armatures.new(self.body+'_NativeBeltRig');rig=bpy.data.objects.new(arm.name,arm);self.cols['01_EDITABLE_LOD0'].objects.link(rig)
        bpy.ops.object.select_all(action='DESELECT');bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT');reflect=Matrix.Diagonal((1,-1,1))
        for b in self.bones:
            eb=arm.edit_bones.new(b['name']);axes=Matrix(b['axes']).transposed()
            for i in range(3):axes.col[i]=axes.col[i].normalized()
            matrix=(reflect@axes@reflect).to_4x4();matrix.translation=reflect@Vector(b['position'])*.01;eb.matrix=matrix;eb.length=.025
        for b in self.bones:
            if b['parent']>=0:arm.edit_bones[b['name']].parent=arm.edit_bones[self.bones[b['parent']]['name']]
        bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False);rig.show_in_front=True;rig.hide_render=True
        rig['body_variant']=self.body;rig['pants_reference']=self.row['pants_asset'];rig['runtime_tested']=False
        return rig

    def bind(self,objects,rig):
        for ob in objects:
            weights=self.weights[ob.name];ids={k for ws in weights for k in ws};groups={i:ob.vertex_groups.new(name=self.bones[i]['name']) for i in ids}
            for vi,ws in enumerate(weights):
                for bi,w in ws.items():groups[bi].add([vi],w,'REPLACE')
            ob.parent=rig;ob.modifiers.new('Native waist skinning','ARMATURE').object=rig

    def merge_for_export(self,objects,name,rig=None):
        bpy.ops.object.select_all(action='DESELECT');bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();copies=[];parts=[]
        for ob in objects:
            ev=ob.evaluated_get(deps);me=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=deps)
            copy=ob.copy();copy.data=me;copy.modifiers.clear();copy.parent=None;self.scene.collection.objects.link(copy);copy.matrix_world=ob.matrix_world.copy();copy.hide_set(False);copies.append(copy)
            me.calc_loop_triangles();parts.append(dict(name=ob.name,vertices=len(me.vertices),triangles=len(me.loop_triangles),kind=ob.get('assembly_kind','')))
        for ob in copies:ob.select_set(True)
        bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();ob=bpy.context.object;ob.name=name
        if rig:ob.parent=rig;ob.modifiers.new('Native waist skinning','ARMATURE').object=rig
        return ob,dict(vertices=len(ob.data.vertices),triangles=sum(x['triangles'] for x in parts),parts=parts)

    def selection(self,objects):
        bpy.ops.object.select_all(action='DESELECT')
        for ob in objects:ob.hide_set(False);ob.select_set(True)
        bpy.context.view_layer.objects.active=objects[0]

    def fbx(self,objects,path,rig=None):
        self.selection(objects+([rig] if rig else []))
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',path_mode='AUTO')

    def glb(self,objects,path,rig=None):
        self.selection(objects+([rig] if rig else []))
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_apply=False,export_animations=False,export_yup=True)

    def neutral(self,ob,path):
        me=ob.data;me.calc_loop_triangles();uv=me.uv_layers.active;groups={x.index:next(i for i,b in enumerate(self.bones) if b['name']==x.name) for x in ob.vertex_groups}
        data=dict(body=self.body,coordinate_system='UE centimetres; UV V not flipped',positions=[[v.co.x*100,-v.co.y*100,v.co.z*100] for v in me.vertices],triangles=[],uv=[],normals=[],triangle_materials=[],material_slots=[m.name for m in me.materials],bones=self.bones,weights=[])
        for v in me.vertices:
            ws=[(groups[g.group],g.weight) for g in v.groups if g.weight>1.e-6];total=sum(w for i,w in ws);data['weights'].append([[i,w/total] for i,w in ws])
        for tri in me.loop_triangles:
            loops=list(reversed(tri.loops));data['triangles'].append(list(reversed(tri.vertices)));data['uv'].append([list(uv.data[i].uv) for i in loops]);data['normals'].append([[me.corner_normals[i].vector.x,-me.corner_normals[i].vector.y,me.corner_normals[i].vector.z] for i in loops]);data['triangle_materials'].append(tri.material_index)
        Path(path).write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')

    def sources(self,levels):
        self.world();high=self.cols['07_HIGH_SURFACE_SOURCES'];ref=self.cols['06_NATIVE_REFERENCES']
        for original in [o for o in levels[0] if o.name in ('Belt_02_Main_Carry_Shell','Belt_03_Center_Webbing')]:
            ob=original.copy();ob.data=original.data.copy();ob.parent=None;ob.modifiers.clear();ob.name='HIGH_'+original.name;high.objects.link(ob)
            sub=ob.modifiers.new('Dense cloth authoring surface','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=3;sub.render_levels=3;self.displace(ob,'Belt_CharcoalNylon' if 'Shell' in original.name else 'Belt_BlackWebbing')
        for i,row in enumerate(SURFACES):
            ps=[];uv=[];fs=[];span=row['tile_m']*100
            for y in range(33):
                for x in range(33):ps.append([45+i*5+x/32*span,y/32*span,97]);uv.append((x/32,y/32))
            for y in range(32):
                for x in range(32):k=y*33+x;fs.append([k,k+1,k+34,k+33])
            ob=self.mesh('HIGH_Field_'+row['name'],ps,fs,i,uv,col=high);sub=ob.modifiers.new('Physical field subdivision','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=3;sub.render_levels=3;self.displace(ob,row['name'])
        for name,points,faces in [('ST6_Waist_Reference',self.pants_points,self.pants_faces),('Native_Body_Binding_Reference',self.body_points,self.body_faces)]:
            ob=self.mesh(self.body+'_'+name,points,faces,0,col=ref);ob.display_type='WIRE';ob.hide_render=True
        board=bpy.data.objects.new('APPROVED_CONCEPT',None);ref.objects.link(board);board.empty_display_type='IMAGE';board.data=bpy.data.images.load(str(R/'Reference/approved-concept.png'));board.empty_display_size=.7;board.location=(.6,0,1.1)
        high.hide_render=high.hide_viewport=True;ref.hide_render=ref.hide_viewport=True

    def author(self):
        levels=[]
        for level in range(3):
            objects,mounts=self.build(level);levels.append(objects)
            if level==0:self.sockets=mounts
        self.level=0;seated=[]
        for entry in self.sockets:
            self.active_frame=(np.array(entry['origin_cm']),np.array(entry['basis']));self.active_weights=entry['weights'];self.active_kind='magazine';start=len(self.objects)
            self.magazine(entry['name']+'_Magazine',entry['kind'],entry['local_seat']);parts=self.objects[start:];self.rehome(parts,'04_MAGAZINES_SEATED');seated.extend(parts)
            for ob in parts:ob['slot_name']=entry['name']
            empty=bpy.data.objects.new('SOCKET_'+entry['name'],None);self.cols['08_SLOT_ANCHORS'].objects.link(empty);empty.empty_display_type='ARROWS';empty.empty_display_size=.018
            reflect=Matrix.Diagonal((1,-1,1));matrix=(reflect@Matrix(entry['basis'])@reflect).to_4x4();matrix.translation=bv(entry['seat_cm']);empty.matrix_world=matrix
            empty['reference_pose_only']=True;empty['magazine_kind']=entry['kind'];empty['extraction_direction_ue']='positive local Z'
        self.world();rig=self.native_rig()
        for group in levels+[seated]:self.bind(group,rig)
        reports=[]
        for level,objects in enumerate(levels):
            merged,stats=self.merge_for_export(objects,f'SK_TacticalBelt_{self.body}_LOD{level}',rig);path=E/f'{merged.name}.fbx';self.fbx([merged],path,rig)
            if level==0:
                self.neutral(merged,R/'Authored'/f'TacticalBelt_{self.body}.json');self.glb([merged],E/f'TacticalBelt_{self.body}_Empty.glb',rig)
                self.glb([merged]+seated,E/f'TacticalBelt_{self.body}_Loaded.glb',rig)
            stats['lod']=level;stats['fbx']=str(path);reports.append(stats);bpy.data.objects.remove(merged,do_unlink=True)
            print('BELT_LOD_EXPORTED',self.body,level,stats['triangles'],flush=True)
        # Standalone identical-dimension prop masters. Export once; both bodies use them.
        magazine_reports=[];masters=[]
        if self.body=='Jason':
            for kind in MAG:
                item=dict(kind=kind,lods=[])
                for level in range(3):
                    self.level=level;self.active_frame=(np.zeros(3),np.eye(3));self.active_weights={};self.active_kind='magazine';start=len(self.objects);self.magazine('MASTER_'+kind+'_LOD'+str(level),kind,[0,0,0]);parts=self.objects[start:]
                    self.rehome(parts,'05_MAGAZINE_MASTERS');masters.extend(parts);merged,stats=self.merge_for_export(parts,'SM_'+kind.title()+'Magazine_LOD'+str(level));path=E/(merged.name+'.fbx');self.fbx([merged],path)
                    if level==0:self.glb([merged],E/(kind.title()+'Magazine.glb'))
                    stats['lod']=level;stats['fbx']=str(path);item['lods'].append(stats);bpy.data.objects.remove(merged,do_unlink=True)
                magazine_reports.append(item)
        self.world();self.level=0;self.sources(levels)
        for key in ('02_EXPORT_LOD1','03_EXPORT_LOD2','05_MAGAZINE_MASTERS','08_SLOT_ANCHORS'):
            self.cols[key].hide_render=self.cols[key].hide_viewport=True
        self.selection(levels[0]+seated)
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type=='VIEW_3D':
                    area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_distance=.75;area.spaces.active.region_3d.view_location=bv(self.point(0,.5,0))
        bpy.ops.file.pack_all();blend=E/f'TacticalBelt_{self.body}_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        write(R/'Authored'/f'{self.body}_attachments.json',dict(body=self.body,slots=self.sockets,magazine_envelopes=MAG,reference_pose=True,animation_implemented=False))
        report=dict(body=self.body,blend=str(blend),lods=reports,magazine_masters=magazine_reports,slot_count=4,seated_magazine_parts=len(seated),fit=self.fit_report,game_integrated=False,runtime_tested=False)
        write(R/'Authored'/f'{self.body}_production.json',report);return report


if __name__=='__main__':
    import sys
    selected=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    for row in read(R/'inputs.json')['records']:
        if selected and row['body'] not in selected:continue
        Belt(row).author();gc.collect()
    rows=[read(R/'Authored'/f'{r["body"]}_production.json') for r in read(R/'inputs.json')['records'] if (R/'Authored'/f'{r["body"]}_production.json').exists()]
    write(R/'authored.json',dict(completed=len(rows)==2,name='战术弹匣腰带',stage='detailed_models_and_native_waist_exports',records=rows,texture_maps=36,unreal_imported=False,configuration_changed=False,preview_rendered=False,runtime_tested=False))
    print('TACTICAL_BELT_AUTHORING_SAVED',len(rows),flush=True)
