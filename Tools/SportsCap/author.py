"""Editable five-panel sports cap, real vents, physical PBR and native head fits.

Authoring coordinates are centimetres: X right, Y rear, Z up. Blender uses
metres with Y reversed. This producer does not render or modify game catalogs.
"""
import bpy
import bmesh
import numpy as np
import math
import json
import hashlib
import shutil
from pathlib import Path
from mathutils import Vector, Matrix

P=Path('D:/FPS3D/FPSGAME'); R=P/'SourceAssets/SportsCap20261024'; E=R/'Exports'
E.mkdir(parents=True,exist_ok=True); (R/'Authored').mkdir(exist_ok=True)
TAU=math.tau
SURFACES=json.loads((R/'textures.json').read_text())['maps']
SURFACE={x['name']:x for x in SURFACES}
APPROVED=P/'SourceAssets/SportsSetDesign20261024/charcoal-sports-cap-concept-v1.png'
(R/'Reference').mkdir(exist_ok=True)
shutil.copy2(APPROVED,R/'Reference/approved-concept.png')


def read(path): return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,data): Path(path).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def bv(p): return Vector((p[0]*.01,-p[1]*.01,p[2]*.01))
def unit(v): return np.asarray(v)/max(float(np.linalg.norm(v)),1.e-12)


class Cap:
    def __init__(self,body,head_path,body_path=None):
        self.body=body;self.head_path=head_path;self.head=read(head_path)
        self.points=np.array(self.head['positions'])
        bones=read(body_path)['bones'] if body_path else self.head['bones']
        self.bone=bones['head'] if isinstance(bones,dict) else next(x for x in bones if x['name']=='head')
        self.z0=float(self.points[:,2].max())-7.15
        section=self.points[np.abs(self.points[:,2]-self.z0)<.6]
        self.center=np.r_[(section[:,:2].max(0)+section[:,:2].min(0))*.5,self.z0]
        radii=(section[:,:2].max(0)-section[:,:2].min(0))*.5+.72
        radii*=max(1.,float(np.sqrt((((section[:,:2]-self.center[:2])/radii)**2).sum(1)).max())+.012)
        self.rx,self.ry=map(float,radii);self.height=9.55
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene=bpy.context.scene;self.scene.unit_settings.system='METRIC'
        self.scene.unit_settings.scale_length=1.
        self.cols={}
        for name in ('01_EDITABLE_LOD0','02_EXPORT_LOD1','03_EXPORT_LOD2','04_HIGH_SurfaceSources','05_NATIVE_References'):
            c=bpy.data.collections.new(name);self.scene.collection.children.link(c);self.cols[name]=c
        self.mats=[];self.objects=[];self.level=0
        for name,rough,sheen in [('Cap_CharcoalNylon',.77,.16),('Cap_SmokeVentNylon',.8,.12),('Cap_BlackSweatband',.89,.25),('Cap_BlackWebbing',.74,.12),('Cap_BlackPolymer',.48,0),('Cap_CyanBinding',.65,.12),('Cap_ReflectiveTape',.38,.5)]:
            self.material(name,rough,sheen)
        self.material('Cap_TonalStitch',.85,.08,texture=False)

    def material(self,name,rough,sheen,texture=True):
        m=bpy.data.materials.new(name);m.use_nodes=True
        n=m.node_tree.nodes;l=m.node_tree.links;bs=n.get('Principled BSDF')
        bs.inputs['Base Color'].default_value=(.035,.038,.042,1)
        bs.inputs['Roughness'].default_value=rough;bs.inputs['Sheen Weight'].default_value=sheen
        m.diffuse_color=(.12,.13,.14,1)
        if texture:
            for channel in ('BaseColor','Normal','ORM'):
                t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(R/'Textures'/f'T_{name}_{channel}.png'),check_existing=True)
                t.label=channel;t.extension='REPEAT'
                if channel=='BaseColor':l.new(t.outputs['Color'],bs.inputs['Base Color'])
                else:
                    t.image.colorspace_settings.name='Non-Color'
                    if channel=='Normal':
                        normal=n.new('ShaderNodeNormalMap');l.new(t.outputs['Color'],normal.inputs['Color']);l.new(normal.outputs['Normal'],bs.inputs['Normal'])
                    else:
                        sep=n.new('ShaderNodeSeparateColor');l.new(t.outputs['Color'],sep.inputs['Color']);l.new(sep.outputs['Green'],bs.inputs['Roughness']);l.new(sep.outputs['Blue'],bs.inputs['Metallic'])
            m['tile_cm']=SURFACE[name]['tile_m']*100
        self.mats.append(m)

    def mesh(self,name,points,faces,mat=0,uv=None,slots=None,col=None):
        me=bpy.data.meshes.new(name)
        me.from_pydata([bv(p) for p in points],[],[list(reversed(f)) for f in faces]);me.update()
        ob=bpy.data.objects.new(name,me)
        (col or self.cols[('01_EDITABLE_LOD0','02_EXPORT_LOD1','03_EXPORT_LOD2')[self.level]]).objects.link(ob)
        for m in self.mats: me.materials.append(m)
        if uv is None: uv=[(p[0]/4,p[1]/4) for p in points]
        layer=me.uv_layers.new(name='UV0_PhysicalScale')
        for i,poly in enumerate(me.polygons):
            poly.use_smooth=True;poly.material_index=slots[i] if slots else mat
            for li,vi in zip(poly.loop_indices,poly.vertices):layer.data[li].uv=uv[vi]
        bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
        if col is None:self.objects.append(ob)
        ob['source_units']='centimetres mapped to Blender metres'
        return ob

    def solid(self,ob,cm,inner_mat=None):
        mod=ob.modifiers.new('Physical sewn thickness','SOLIDIFY');mod.thickness=cm*.01;mod.offset=-1;mod.use_even_offset=True
        if inner_mat is not None:mod.material_offset=inner_mat
        return ob

    def cut(self,a): return .80-.12*math.cos(2*a)

    def crown(self,t,a):
        t=float(np.clip(t,0,1));rad=math.sqrt(max(0,1-t**2.2))
        s,c=math.sin(a),math.cos(a)
        x=self.rx*math.copysign(abs(s)**.94,s)*rad
        y=-self.ry*math.copysign(abs(c)**.94,c)*rad+.18*math.sin(math.pi*t)
        z=self.height*t-.16*c*math.sin(math.pi*t)
        # Restrained seam tension and two shallow cloth creases, not a smooth plastic dome.
        wrinkle=.045*math.sin(13*a+2*t)*math.exp(-((t-.13)/.12)**2)*math.sin(math.pi*t)
        wrinkle+=.035*math.sin(21*a-4*t)*math.exp(-((t-.45)/.30)**2)*math.sin(math.pi*t)
        return np.array([x+wrinkle*s,y-wrinkle*c,z+.025*math.sin(7*a)*math.sin(math.pi*t)**2])

    def normal(self,t,a):
        if t>.998:return np.array([0.,0.,1.])
        da=self.crown(t,a+.0002)-self.crown(t,a-.0002)
        dt=self.crown(min(.999,t+.0002),a)-self.crown(max(0,t-.0002),a)
        return unit(np.cross(da,dt))

    def lower(self,a,rear=False):
        da=(a-math.pi+math.pi)%TAU-math.pi
        return 3.25/self.height*math.sqrt(max(0,1-(da/.43)**2)) if rear and abs(da)<.43 else 0.

    def panel(self,name,a0,a1,na,nv,rear=False,side=False,inset=0,mat=0):
        ps=[];uv=[];fs=[];slots=[];cache={};holes=0
        def point(u,v):
            a=a0+(a1-a0)*u;lo=self.lower(a,rear);t=lo+(self.cut(a)-lo)*v
            return self.crown(t,a)-self.normal(t,a)*inset
        def vertex(u,v):
            key=(round(u,10),round(v,10))
            if key not in cache:
                a=a0+(a1-a0)*u;lo=self.lower(a,rear);t=lo+(self.cut(a)-lo)*v
                cache[key]=len(ps);ps.append(point(u,v));uv.append(((a-a0)*(self.rx+self.ry)*.47/4,t*self.height*1.35/4))
            return cache[key]
        for j in range(nv):
            for i in range(na):
                u,v=(i+.5)/na,(j+.5)/nv
                vent=side and .16<u<.84 and .54<v<.85
                if side:
                    outer=[(i/na,j/nv),((i+.5)/na,j/nv),((i+1)/na,j/nv),((i+1)/na,(j+.5)/nv),((i+1)/na,(j+1)/nv),((i+.5)/na,(j+1)/nv),(i/na,(j+1)/nv),(i/na,(j+.5)/nv)]
                else:outer=[(i/na,j/nv),((i+1)/na,j/nv),((i+1)/na,(j+1)/nv),(i/na,(j+1)/nv)]
                outside=[vertex(*p) for p in outer]
                if vent:
                    du=np.linalg.norm(point(u+.0001,v)-point(u-.0001,v))/.0002
                    dv=np.linalg.norm(point(u,v+.0001)-point(u,v-.0001))/.0002
                    radius=min(.075,du/na*.28,dv/nv*.28)
                    inside=[vertex(u+radius/du*math.cos(-3*math.pi/4+k*math.pi/4),v+radius/dv*math.sin(-3*math.pi/4+k*math.pi/4)) for k in range(8)]
                    for k in range(8):fs.append([outside[k],outside[(k+1)%8],inside[(k+1)%8],inside[k]]);slots.append(1)
                    holes+=1
                else:fs.append(outside);slots.append(mat)
        ob=self.solid(self.mesh(name,ps,fs,uv=uv,slots=slots),.085 if not inset else .035)
        ob['actual_through_vents']=holes;ob['panel']='Independent sewn pattern piece'
        return ob

    def top(self):
        na,nr=((112,24),(80,18),(56,13))[self.level]
        ps=[];uv=[];fs=[]
        for j in range(nr):
            v=.983*j/(nr-1)
            for i in range(na):
                a=TAU*i/na;t=self.cut(a)+(1-self.cut(a))*v;q=self.crown(t,a)
                ps.append(q);uv.append((q[0]/4,q[1]/4))
        for j in range(nr-1):
            for i in range(na):fs.append([j*na+i,j*na+(i+1)%na,(j+1)*na+(i+1)%na,(j+1)*na+i])
        center=len(ps);ps.append(np.array([0.,0.,self.height]));uv.append((0,0))
        for i in range(na):fs.append([(nr-1)*na+i,(nr-1)*na+(i+1)%na,center])
        return self.solid(self.mesh('05_Long_Center_Crown_Panel',ps,fs,uv=uv),.085)

    def tube(self,name,paths,radius,mat,sides=6,closed=False):
        ps=[];uv=[];fs=[]
        for path in paths:
            path=np.asarray(path);start=len(ps);n=len(path);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
            for j,p in enumerate(path):
                tangent=unit(path[(j+1)%n]-path[(j-1)%n]) if closed else unit(path[min(n-1,j+1)]-path[max(0,j-1)])
                ref=np.array([0.,0.,1.]) if abs(tangent[2])<.9 else np.array([0.,1.,0.]);u=unit(np.cross(tangent,ref));v=np.cross(tangent,u)
                for k in range(sides):
                    ps.append(p+radius*(u*math.cos(TAU*k/sides)+v*math.sin(TAU*k/sides)));uv.append((TAU*radius*k/sides/4,arc[j]/4))
            for j in range(n if closed else n-1):
                for k in range(sides):fs.append([start+j*sides+k,start+j*sides+(k+1)%sides,start+((j+1)%n)*sides+(k+1)%sides,start+((j+1)%n)*sides+k])
            if not closed:
                fs.append([start+k for k in reversed(range(sides))]);fs.append([start+(n-1)*sides+k for k in range(sides)])
        return self.mesh(name,ps,fs,mat,uv)

    def ribbon(self,name,path,normals,width,mat,thickness=.035):
        ps=[];uv=[];fs=[];arc=0.
        for i,p in enumerate(path):
            if i:arc+=float(np.linalg.norm(p-path[i-1]))
            tangent=unit(path[min(len(path)-1,i+1)]-path[max(0,i-1)])
            side=unit(np.cross(normals[i],tangent))
            for sign in (-1,1):ps.append(p+side*width*.5*sign);uv.append(((sign+1)*width/8,arc/4))
        for i in range(len(path)-1):fs.append([i*2,i*2+1,i*2+3,i*2+2])
        return self.solid(self.mesh(name,ps,fs,mat,uv),thickness)

    def stitch(self,name,path,normals,mat=7,pitch=.28,radius=.014):
        if self.level==2:return
        p=np.asarray(path);normals=np.asarray(normals);arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(p,axis=0),axis=1))]
        paths=[]
        for s in np.arange(.10,arc[-1]-.13,pitch):
            line=[]
            for phase in np.linspace(0,1,4 if self.level==0 else 3):
                at=min(s+phase*.17,arc[-1]);i=min(len(p)-2,max(0,np.searchsorted(arc,at)-1));t=(at-arc[i])/max(arc[i+1]-arc[i],1.e-9)
                point=p[i]*(1-t)+p[i+1]*t;n=unit(normals[i]*(1-t)+normals[i+1]*t)
                line.append(point+n*(-.006+.028*math.sin(math.pi*phase)))
            paths.append(line)
        if paths:self.tube(name,paths,radius,mat,4 if self.level==0 else 3)

    def brim(self,u,a):
        inner=self.crown(0,a);taper=max(0,math.cos(a/1.06*math.pi/2))**.68
        extension=-.42+u*(.42+5.5*taper)
        return inner+np.array([extension*math.sin(a),-extension*math.cos(a),-.12-.37*u-.65*u*u-.45*math.cos(a)**2*u])

    def bill(self):
        na,nv=((76,22),(54,16),(36,10))[self.level];ps=[];uv=[];fs=[]
        for j in range(nv+1):
            for i in range(na+1):
                q=self.brim(j/nv,-1.06+2.12*i/na);ps.append(q);uv.append((q[0]/4,q[1]/4))
        for j in range(nv):
            for i in range(na):
                a=j*(na+1)+i;fs.append([a,a+1,a+na+2,a+na+1])
        ob=self.solid(self.mesh('06_Curved_55mm_Brim_Shell',ps,fs,uv=uv),.23,2)
        ob['brim_extension_cm']=5.5;ob['brim_thickness_mm']=2.3
        outer=[self.brim(1,a)+[0,0,-.10] for a in np.linspace(-1.06,1.06,na+1)]
        self.tube('07_Black_Rolled_Brim_Binding',[outer],.12,4,8 if self.level==0 else 6)
        # Fine cyan welt is inset into the upper edge rather than a thick glowing pipe.
        cyan=[self.brim(.993,a)+[0,0,-.015] for a in np.linspace(-1.04,1.04,na+1)]
        self.tube('08_Cyan_Edge_Welt',[cyan],.028,5,6 if self.level==0 else 4)
        for k,u in enumerate((.18,.32,.46,.60,.74,.88)):
            path=[self.brim(u,a)+[0,0,.025] for a in np.linspace(-1.00,1.00,100)]
            self.stitch('09_Brim_Quilting_Row_%02d'%k,path,[[0,0,1]]*len(path),pitch=.30)

    def tailoring(self):
        aa=np.linspace(0,TAU,241);path=[self.crown(self.cut(a),a) for a in aa];nn=[self.normal(self.cut(a),a) for a in aa]
        self.ribbon('10_Top_Panel_Felled_Seam',[q+n*.045 for q,n in zip(path,nn)],nn,.22,0,.04)
        self.ribbon('11_Interior_Top_Seam_Tape',[q-n*.14 for q,n in zip(path,nn)],[-n for n in nn],.48,2,.035)
        for side in (-1,1):
            ss=[self.crown(self.cut(a)+side*.012,a)+self.normal(self.cut(a)+side*.012,a)*.055 for a in aa]
            self.stitch('12_Top_Seam_Double_'+str(side),ss,nn)
        for idx,a in enumerate((-.68,.68,math.pi-.68,math.pi+.68)):
            ts=np.linspace(.025,self.cut(a)-.015,90);path=[self.crown(t,a) for t in ts];nn=[self.normal(t,a) for t in ts]
            self.ribbon('13_Panel_Join_%d'%idx,[q+n*.035 for q,n in zip(path,nn)],nn,.16,0)
            self.ribbon('14_Interior_Seam_Tape_%d'%idx,[q-n*.14 for q,n in zip(path,nn)],[-n for n in nn],.48,2)
            for side in (-1,1):self.stitch('15_Panel_Stitches_%d_%d'%(idx,side),[self.crown(t,a+side*.014)+self.normal(t,a+side*.014)*.055 for t in ts],nn)
        rear_angles=np.linspace(math.pi-.43,math.pi+.43,90)
        rear=[self.crown(self.lower(a,True),a)+self.normal(self.lower(a,True),a)*.015 for a in rear_angles]
        rn=[self.normal(self.lower(a,True),a) for a in rear_angles]
        self.ribbon('16_Rear_Hair_Opening_Bias_Binding',rear,rn,.32,3,.075)
        self.stitch('17_Rear_Opening_Stitches',[q+n*.055 for q,n in zip(rear,rn)],rn,pitch=.26)
        angles=np.linspace(-math.pi+.43,math.pi-.43,150)
        ps=[];uv=[];fs=[]
        for j,z in enumerate((-.82,-.68,-.20,.35)):
            for i,a in enumerate(angles):
                q=self.crown(0,a)-self.normal(0,a)*(.14+.035*math.sin(j*math.pi/3));q[2]=z
                ps.append(q);uv.append((i/149*(self.rx+self.ry)*2.7/4,z/4))
        for j in range(3):
            for i in range(len(angles)-1):
                x=j*len(angles)+i;fs.append([x,x+1,x+1+len(angles),x+len(angles)])
        self.solid(self.mesh('18_Soft_Interior_Sweatband',ps,fs,2,uv),.10)
        for z in (-.72,.24):
            pp=[self.crown(0,a)-self.normal(0,a)*.22 for a in angles]
            for q in pp:q[2]=z
            self.tube('19_Sweatband_Fold_'+str(z),[pp],.035,2,6 if self.level==0 else 4)
        # Actual front lining reinforcement does not cover the side ventilation holes.
        self.panel('20_Front_Inner_Reinforcement',-.68,.68,20,12,inset=.13,mat=2)

    def rounded_rect(self,w,h,r,n=6):
        out=[]
        for cx,cz,start in ((w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)):
            for a in np.linspace(start,start+90,n,endpoint=False):out.append([cx+r*math.cos(math.radians(a)),cz+r*math.sin(math.radians(a))])
        return out

    def frame(self,name,center,w,h,innerw,innerh,depth,mat=4):
        outer=self.rounded_rect(w,h,min(.18,h*.2),8 if self.level==0 else 5)
        inner=self.rounded_rect(innerw,innerh,min(.12,innerh*.2),8 if self.level==0 else 5)
        ps=[];fs=[];n=len(outer)
        for y,ring in ((-depth/2,outer),(-depth/2,inner),(depth/2,outer),(depth/2,inner)):
            ps.extend([np.asarray(center)+[x,y,z] for x,z in ring])
        for i in range(n):
            k=(i+1)%n
            fs.extend([[i,k,n+k,n+i],[2*n+i,3*n+i,3*n+k,2*n+k],[i,2*n+i,2*n+k,k],[n+i,n+k,3*n+k,3*n+i]])
        ob=self.mesh(name,ps,fs,mat)
        bevel=ob.modifiers.new('Rounded moulded edges','BEVEL');bevel.width=.00018;bevel.segments=3 if self.level==0 else 2
        return ob

    def box(self,name,center,size,mat=4,bevel=.05):
        ps=[np.asarray(center)+np.array([sx,sy,sz])*np.asarray(size)/2 for sx,sy,sz in ((-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1))]
        fs=[[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]
        ob=self.mesh(name,ps,fs,mat);b=ob.modifiers.new('Soft manufactured corners','BEVEL');b.width=bevel*.01;b.segments=3 if self.level==0 else 2
        return ob

    def hardware(self):
        by=self.ry+.14;cz=-.28
        self.frame('21_Adjuster_Real_Twin_Slots',[.55,by,cz],2.25,1.25,1.70,.83,.28)
        self.box('22_Adjuster_Center_Bar',[.55,by,cz],[.22,.31,.87],bevel=.055)
        path=[np.array([x,by-.19+.07*math.sin((x+4)/8*math.pi),cz]) for x in np.linspace(-3.9,3.95,64)]
        self.ribbon('23_Adjustable_Webbing_Through_Buckle',path,[[0,1,0]]*len(path),.72,3,.11)
        # Returned tail passes around the right buckle edge and back through its slot.
        fold=[np.array([1.68+.16*math.cos(a),by+.02+.16*math.sin(a),cz]) for a in np.linspace(-math.pi/2,math.pi/2,18)]
        fold += [np.array([x,by+.18,cz]) for x in np.linspace(1.68,3.5,28)[1:]]
        self.ribbon('24_Doubled_Back_Adjustment_Tail',fold,[[0,1,0]]*len(fold),.70,3,.10)
        # Soft keeper is a complete wrapping loop in Y/Z, with the webbing passing inside.
        profile=self.rounded_rect(.64,.97,.13,8)
        keeper=[[2.75,by+y,cz+z] for y,z in profile]
        self.tube('25_Webbing_Tail_Keeper',[keeper],.085,3,6 if self.level==0 else 4,True)
        for x in (-3.75,3.75):
            line=[np.array([x,by+.04,cz+z]) for z in np.linspace(-.30,.30,14)]
            self.stitch('26_Anchor_Bartack_'+str(x),line,[[0,1,0]]*len(line),pitch=.065,radius=.018)
        for x in (3.48,3.59):
            line=[np.array([x,by+.29,cz+z]) for z in np.linspace(-.29,.29,10)]
            self.tube('27_Cyan_Rear_Bartack_'+str(x),[line],.022,5,5 if self.level==0 else 4)
        # Reflective strip is sewn onto the right lower side, clear of the vents.
        aa=np.linspace(1.98,2.12,18);t=.34
        pp=[self.crown(t,a)+self.normal(t,a)*.085 for a in aa];nn=[self.normal(t,a) for a in aa]
        self.ribbon('28_Reflective_Tab_Black_Backing',pp,nn,.29,3,.045)
        self.ribbon('29_Silver_Reflective_Slit',[q+n*.04 for q,n in zip(pp,nn)],nn,.18,6,.025)
        # A small blank woven size label and folded return inside the sweatband.
        aa=np.linspace(-2.52,-2.33,20);pp=[self.crown(0,a)-self.normal(0,a)*.28 for a in aa]
        for q in pp:q[2]=-.27
        nn=[-self.normal(0,a) for a in aa]
        self.ribbon('30_Interior_Woven_Care_Label',pp,nn,.48,2,.04)
        for p,n in ((pp[2],nn[2]),(pp[-3],nn[-3])):
            line=[p+np.array([0,0,z])+n*.03 for z in np.linspace(-.18,.18,12)]
            self.stitch('31_Label_End_Stitch',line,[n]*len(line),pitch=.08)

    def build(self,level):
        self.level=level;start=len(self.objects)
        na,nv=((32,22),(24,16),(18,12))[level]
        self.panel('01_Front_Crown_Panel',-.68,.68,na,nv)
        self.panel('02_Rear_Crown_With_Hair_Opening',math.pi-.68,math.pi+.68,na,nv,rear=True)
        for name,a0,a1 in [('03_Right_Perforated_Panel',.68,math.pi-.68),('04_Left_Perforated_Panel',math.pi+.68,TAU-.68)]:
            self.panel(name,a0,a1,36 if level<2 else 24,18 if level<2 else 14,side=True)
        self.top();self.bill();self.tailoring();self.hardware()
        return self.objects[start:]

    def fit(self):
        axes=np.array(self.bone['axes']).T;scale=np.linalg.norm(axes,axis=0);rot=axes/scale
        quat=Matrix(rot.T.tolist()).to_quaternion();w,x,y,z=quat
        return dict(location=np.linalg.solve(axes,self.center-np.array(self.bone['position'])).tolist(),
                    rotation=[math.degrees(math.asin(np.clip(2*(z*x-w*y),-1,1))),math.degrees(math.atan2(2*(w*z+x*y),1-2*(y*y+z*z))),math.degrees(math.atan2(-2*(w*x+y*z),1-2*(x*x+y*y)))],scale=(1/scale).tolist())

    def author(self):
        levels=[self.build(i) for i in range(3)]
        # Stable single-bone head follower; fine sewing detail does not need simulation bones.
        arm=bpy.data.armatures.new('SportsCap_HeadAttachment');rig=bpy.data.objects.new('SportsCap_HeadAttachment',arm)
        self.cols['01_EDITABLE_LOD0'].objects.link(rig);bpy.context.view_layer.objects.active=rig;rig.select_set(True)
        bpy.ops.object.mode_set(mode='EDIT');bone=arm.edit_bones.new('HatRoot');bone.head=(0,0,0);bone.tail=(0,0,.04);bpy.ops.object.mode_set(mode='OBJECT')
        for objects in levels:
            for ob in objects:
                ob.parent=rig;group=ob.vertex_groups.new(name='HatRoot');group.add(list(range(len(ob.data.vertices))),1.,'REPLACE')
                mod=ob.modifiers.new('Rigid head-bone follower','ARMATURE');mod.object=rig
        rig['proposed_item_name']='炭灰运动帽';rig['body_variant']=self.body;rig['covers_scalp_hair']=False
        high=self.cols['04_HIGH_SurfaceSources'];ref=self.cols['05_NATIVE_References']
        # The high crown uses the very same authored height field as the normal maps.
        for original in (levels[0][0],next(o for o in levels[0] if o.name=='05_Long_Center_Crown_Panel')):
            ob=original.copy();ob.data=original.data.copy();ob.parent=None;ob.modifiers.clear();ob.name='HIGH_'+original.name
            high.objects.link(ob)
            sub=ob.modifiers.new('Dense author surface','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=2;sub.render_levels=2
            self.displace(ob,'Cap_CharcoalNylon');self.solid(ob,.085)
        for i,row in enumerate(SURFACES):
            ps=[];fs=[];uv=[];span=row['tile_m']*100
            for y in range(33):
                for x in range(33):ps.append([32+i*5+x/32*span,y/32*span,0]);uv.append((x/32,y/32))
            for y in range(32):
                for x in range(32):k=y*33+x;fs.append([k,k+1,k+34,k+33])
            ob=self.mesh('HIGH_Field_'+row['name'],ps,fs,i,uv,col=high)
            sub=ob.modifiers.new('Height-field subdivision','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=3;sub.render_levels=3
            self.displace(ob,row['name'])
        native=self.mesh('REFERENCE_'+self.body+'_NativeHead',self.points-self.center,self.head['triangles'],col=ref)
        native.display_type='WIRE';native.hide_render=True
        board=bpy.data.objects.new('REFERENCE_Approved_Concept',None);ref.objects.link(board);board.empty_display_type='IMAGE';board.data=bpy.data.images.load(str(R/'Reference/approved-concept.png'));board.empty_display_size=.50;board.location=(.4,0,.10)
        high.hide_render=high.hide_viewport=True;ref.hide_render=ref.hide_viewport=True
        self.cols['02_EXPORT_LOD1'].hide_render=True;self.cols['02_EXPORT_LOD1'].hide_viewport=True
        self.cols['03_EXPORT_LOD2'].hide_render=True;self.cols['03_EXPORT_LOD2'].hide_viewport=True
        bpy.ops.object.select_all(action='DESELECT')
        for ob in levels[0]:ob.select_set(True)
        bpy.context.view_layer.objects.active=levels[0][0]
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type=='VIEW_3D':
                    area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_distance=.46;area.spaces.active.region_3d.view_location=(0,0,.03)
        bpy.ops.file.pack_all()
        blend=E/f'SportsCap_{self.body}_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        reports=[]
        for level,objects in enumerate(levels):
            col=self.cols[('01_EDITABLE_LOD0','02_EXPORT_LOD1','03_EXPORT_LOD2')[level]];col.hide_viewport=False
            bpy.context.view_layer.update();deps=bpy.context.evaluated_depsgraph_get();copies=[];parts=[]
            for ob in objects:
                evaluated=ob.evaluated_get(deps);me=bpy.data.meshes.new_from_object(evaluated,depsgraph=deps,preserve_all_data_layers=True)
                copy=bpy.data.objects.new(ob.name+'_Export',me);self.scene.collection.objects.link(copy);copy.matrix_world=ob.matrix_world.copy();copies.append(copy)
                me.calc_loop_triangles();parts.append(dict(name=ob.name,vertices=len(me.vertices),triangles=len(me.loop_triangles),through_vents=ob.get('actual_through_vents',0)))
            bpy.ops.object.select_all(action='DESELECT')
            for ob in copies:ob.select_set(True)
            bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();export=bpy.context.object;export.name=f'SK_SportsCap_{self.body}_LOD{level}'
            export.parent=rig;g=export.vertex_groups.get('HatRoot') or export.vertex_groups.new(name='HatRoot');g.add(list(range(len(export.data.vertices))),1.,'REPLACE')
            mod=export.modifiers.new('HeadAttachment','ARMATURE');mod.object=rig
            # Save the neutral centimetre author mesh for the existing static-head pipeline.
            if level==0:self.delivery(export,R/'Authored'/f'SportsCap_{self.body}.json')
            rig.select_set(True)
            fbx=E/f'SK_SportsCap_{self.body}_LOD{level}.fbx'
            bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH','ARMATURE'},add_leaf_bones=False,use_armature_deform_only=True,bake_anim=False,axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',path_mode='COPY',embed_textures=True)
            if level==0:
                bpy.ops.export_scene.gltf(filepath=str(E/f'SportsCap_{self.body}.glb'),export_format='GLB',use_selection=True,export_apply=False,export_animations=False,export_yup=True)
            reports.append(dict(lod=level,parts=parts,vertices=sum(p['vertices'] for p in parts),triangles=sum(p['triangles'] for p in parts),through_vents=sum(p['through_vents'] for p in parts),fbx=str(fbx)))
            bpy.data.objects.remove(export,do_unlink=True)
            col.hide_viewport=level>0
            print('SPORTS_CAP_EXPORTED',self.body,level,reports[-1]['triangles'],flush=True)
        return dict(body=self.body,blend=str(blend),glb=str(E/f'SportsCap_{self.body}.glb'),lods=reports,head_reference=str(self.head_path),head_reference_sha256=hashlib.sha256(self.head_path.read_bytes()).hexdigest(),opening_radii_cm=[self.rx,self.ry],world_origin_cm=self.center.tolist(),crown_height_cm=self.height,brim_extension_cm=5.5,fit=self.fit(),covers_scalp_hair=False,fit_tested=False)

    def displace(self,ob,family):
        row=SURFACE[family];tex=bpy.data.textures.new(ob.name+'_Height',type='IMAGE');tex.image=bpy.data.images.load(str(R/'Textures'/f'T_{family}_Height.png'),check_existing=True);tex.image.colorspace_settings.name='Non-Color'
        disp=ob.modifiers.new('Actual woven micro-relief','DISPLACE');disp.texture=tex;disp.texture_coords='UV';disp.strength=row['height_range_m'][1]-row['height_range_m'][0];disp.mid_level=.5

    def delivery(self,ob,path):
        me=ob.data;me.calc_loop_triangles();uv=me.uv_layers.active
        data=dict(profile=self.body,positions=[[v.co.x*100,-v.co.y*100,v.co.z*100] for v in me.vertices],triangles=[],uv=[],normals=[],triangle_materials=[],material_slots=[m.name for m in me.materials])
        for tri in me.loop_triangles:
            indices=list(reversed(tri.vertices));loops=list(reversed(tri.loops));data['triangles'].append(indices)
            data['uv'].append([list(uv.data[i].uv) for i in loops]);data['normals'].append([[me.corner_normals[i].vector.x,-me.corner_normals[i].vector.y,me.corner_normals[i].vector.z] for i in loops]);data['triangle_materials'].append(tri.material_index)
        path.write_text(json.dumps(data,separators=(',',':')),encoding='utf-8')


rows=[]
for body,head,bind in [('Jason',P/'SourceAssets/BlueMageHat20261019/native_head_jason.json',None),('Kaitlin',P/'SourceAssets/KaitlinPlayer20261023/NativeGeometry/SKM_MHC_Kaitlin_FaceMesh.json',P/'SourceAssets/KaitlinPlayer20261023/NativeGeometry/MHC_Kaitlin_Body.json')]:
    rows.append(Cap(body,head,bind).author())
    write(R/'authored.json',dict(completed=len(rows)==2,name='炭灰运动帽',approved_concept=str(APPROVED),records=rows,texture_maps=28,stage='detailed_model_and_exports',unreal_imported=False,configuration_changed=False,preview_rendered=False,runtime_tested=False))
print('SPORTS_CAP_AUTHORED',len(rows),'native-head model variants',flush=True)
