"""Original leather belt and empty detachable quiver; native body fit in cm."""
import sys,math,json,gc
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from native_fit import *

class LeatherBelt(NativeBelt):
    def __init__(self,row):
        super().__init__(row)
        self.mount_arc=self.perimeter*.265
        self.lean=5.7
        self.mount_origin,self.mount_basis=self.frame_at(self.mount_arc,.72)
        self.mount_weights=self.native_weights(self.mount_origin)
        self.pelvis_index=next(i for i,b in enumerate(self.bones) if b['name']=='pelvis')
        # The whole quiver stays the same size. Only the mounting standoff is
        # fitted to this body's real hip and upper-thigh envelope.
        local=(self.pants_points-self.mount_origin)@self.mount_basis
        t=np.clip((local[:,2]+49)/44,0,1);cx=self.lean*(1-t)
        relevant=(local[:,2]>-49)&(local[:,2]<-5)&(np.abs(local[:,0]-cx)<6.3)&(local[:,1]>-5)
        self.qy=max(5.3,float(np.max(local[relevant,1]+2.75+.45*t[relevant]))+1.0)
        self.fit_report.update(quiver_center_standoff_cm=self.qy,quiver_length_cm=44,
            mount_arc_cm=self.mount_arc,quiver_side='wearer right, slightly rearward',
            attachment_dimensions_shared=True,animation_tested=False)
        write(R/'Authored'/f'{self.body}_waist_fit.json',self.fit_report)
        for m in self.mats:
            bs=m.node_tree.nodes.get('Principled BSDF')
            if 'Suede' in m.name:bs.inputs['Sheen Weight'].default_value=.32
            elif 'Leather' in m.name:bs.inputs['Coat Weight'].default_value=.015
            if 'Metal' in m.name:
                for node in m.node_tree.nodes:
                    if node.bl_idname=='ShaderNodeNormalMap':node.inputs['Strength'].default_value=.22
        self.module_parts={}

    def mesh(self,name,points,faces,mat=0,uv=None,slots=None,col=None):
        ob=super().mesh(name,points,faces,mat,uv,slots,col)
        mask=ob.data.attributes.new('QuiverMotionMask','FLOAT','POINT')
        for vi,v in enumerate(ob.data.vertices):
            value=1. if self.active_kind=='quiver' else 0.
            if self.active_kind=='hangers':
                ue=np.array([v.co.x*100,-v.co.y*100,v.co.z*100])
                z=((ue-self.mount_origin)@self.mount_basis)[2]
                t=float(np.clip((-z-5.5)/4.5,0,1));value=t*t*(3-2*t)
            mask.data[vi].value=value
            if col is None and value>0:
                ws={i:w*(1-value) for i,w in self.weights[ob.name][vi].items()}
                ws[self.pelvis_index]=ws.get(self.pelvis_index,0)+value
                self.weights[ob.name][vi]={i:w for i,w in ws.items() if w>1e-7}
        return ob

    def in_mount(self,kind):
        self.active_frame=(self.mount_origin,self.mount_basis)
        self.active_weights=self.mount_weights;self.active_kind=kind

    def polish(self,ob,width=.045):
        b=ob.modifiers.new('Soft cut leather edge','BEVEL');b.width=width*.01
        b.segments=3 if self.level==0 else 2;b.limit_method='ANGLE';b.angle_limit=.6
        return ob

    def rivet(self,name,p,normal,radius=.26,mat=3):
        normal=unit(np.array(normal));u=unit(np.cross(normal,[0,0,1]) if abs(normal[2])<.9 else np.cross(normal,[0,1,0]));v=np.cross(normal,u)
        ps=[];faces=[];n=(20,12,8)[self.level]
        for rr,h in [(radius*.84,-.03),(radius,0),(radius,.045),(radius*.87,.095),(radius*.48,.13)]:
            for a in np.arange(n)*TAU/n:ps.append(np.array(p)+rr*(u*math.cos(a)+v*math.sin(a))+normal*h)
        for j in range(4):
            for i in range(n):k=j*n+i;faces.append([k,j*n+(i+1)%n,(j+1)*n+(i+1)%n,k+n])
        faces.extend([list(reversed(range(n))),list(range(4*n,5*n))])
        return self.mesh(name,ps,faces,mat)

    def ring(self,name,center,w,h,r=.22,mat=3):
        rough=[np.array(center)+[x,0,z] for x,z in self.rounded_rect(w,h,min(w,h)*.29,12 if self.level==0 else 7)]
        rough=np.array(rough+[rough[0]])
        arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(rough,axis=0),axis=1))]
        steps=max(24,int(arc[-1]/(.15,.25,.40)[self.level]))
        samples=np.linspace(0,arc[-1],steps,endpoint=False)
        path=np.stack([np.interp(samples,arc,rough[:,k]) for k in range(3)],axis=-1)
        return self.tube(name,[path],r,mat,(16,10,8)[self.level],True)

    def belt(self):
        self.world();density=(224,144,80)[self.level]
        body=self.band('Belt_FullGrain_Carry_Leather',3.3,self.perimeter-3.3,0,1,.04,.40,0,n=density)
        self.polish(body,.045)
        self.band('Belt_Continuous_Suede_Lining',3.34,self.perimeter-3.34,.035,.965,-.045,.035,2,n=density)
        for v in (.045,.955):
            aa=[self.angle(s) for s in np.linspace(3.38,self.perimeter-3.38,224)]
            self.tube('Belt_Burnished_Edge',[ [self.point(a,v,.40) for a in aa] ],.06,1,6)
        if self.level<2:
            aa=[self.angle(s) for s in np.linspace(3.65,self.perimeter-3.65,400)]
            for v in (.115,.885):self.stitch('Belt_Saddle_Stitch',[self.point(a,v,.425) for a in aa],[self.outward(a) for a in aa],pitch=.34)
        self.local(0,.74,kind='buckle')
        self.ring('Buckle_Solid_Brass_Frame',[0,.25,0],7.0,5.45,.26)
        self.tube('Buckle_Prong_Hinge',[[[-3.40,.24,-.80],[-3.40,.24,.80]]],.17,4,10)
        self.tube('Buckle_Single_Curved_Prong',[[[-3.40,.24,0],[-2.5,.40,0],[-.5,.58,0],[1.38,.58,0],[1.65,.16,0]]],.13,3,10)
        # Adjustable free end is actual leather with bored through-holes.
        outline=[[-6.0,-2.02],[6.8,-2.02],[7.9,-1.5],[9.0,0],[7.9,1.5],[6.8,2.02],[-6.0,2.02]]
        ps=[[x,y,z] for y in (-.22,.08) for x,z in outline];n=len(outline)
        fs=[list(reversed(range(n))),list(range(n,2*n))]+[[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
        tail=self.mesh('Belt_Adjustment_Tongue_With_Real_Holes',ps,fs,0)
        holes=[-1.05,1.65,4.25,6.75]
        for i,x in enumerate(holes):self.punch(tail,[x,-.05,0],.23,i)
        self.polish(tail,.055)
        for z in (-1.68,1.68):self.stitch('Tongue_Stitch',[[x,.12,z] for x in np.linspace(-5.8,6.8,80)],[[0,1,0]]*80,pitch=.34)
        # Keeper surrounds the tongue and is separate from the buckle frame.
        path=[[5.4,y,z] for y,z in self.rounded_rect(1.20,4.65,.32,10)]
        normals=[unit([0,y,z*.1]) for _,y,z in path]
        path.append(path[0]);normals.append(normals[0])
        self.ribbon('Belt_Independent_Leather_Keeper',np.array(path),np.array(normals),1.15,5,.23)
        self.world()

    def punch(self,target,center,r,index):
        # A boolean is used only for the few functional adjustment holes.
        wp=np.array(center)@self.active_frame[1].T+self.active_frame[0]
        direction=self.active_frame[1][:,1];db=Vector((direction[0],-direction[1],direction[2]))
        bpy.ops.mesh.primitive_cylinder_add(vertices=(28,20,12)[self.level],radius=r*.01,depth=.022,location=bv(wp))
        cut=bpy.context.object;cut.rotation_mode='QUATERNION';cut.rotation_quaternion=Vector((0,0,1)).rotation_difference(db)
        for m in self.mats:cut.data.materials.append(m)
        for f in cut.data.polygons:f.material_index=1
        bpy.context.view_layer.objects.active=target
        mod=target.modifiers.new('Punched adjustment hole '+str(index),'BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cut
        bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cut,do_unlink=True)
        self.weights[target.name]=[self.active_weights.copy() for _ in target.data.vertices]

    def saddle(self):
        self.world();self.active_kind='saddle'
        self.polish(self.band('Saddle_Shaped_Hip_Reinforcement',self.mount_arc-6.5,self.mount_arc+6.5,.015,.985,.45,.70,5,n=200),.045)
        aa=[self.angle(s) for s in np.linspace(self.mount_arc-6.1,self.mount_arc+6.1,80)]
        for v in (.10,.90):self.stitch('Saddle_Edge_Stitch',[self.point(a,v,.72) for a in aa],[self.outward(a) for a in aa],pitch=.31)
        self.hanger_seats=[];self.hanger_frames=[]
        for side in (-1,1):
            self.local(self.mount_arc+3.45*side,.72,kind='saddle');x=0.
            loop_origin,loop_basis=self.active_frame
            # Closed folded leather loop genuinely encircles the carry belt.
            points=np.array([[x,y-.20,z] for y,z in self.rounded_rect(1.10,5.55,.40,12 if self.level==0 else 8)])
            normals=np.array([unit([0,p[1]+.20,p[2]*.18]) for p in points])
            points=np.vstack([points,points[0]]);normals=np.vstack([normals,normals[0]])
            self.ribbon('Saddle_Threaded_Leather_Loop',points,normals,2.05,0,.24)
            for dx in (-.71,.71):self.stitch('Loop_Edge_Stitch',points+np.array([dx,0,0]),normals,pitch=.31)
            self.ring('Saddle_Brass_D_Ring',[x,.66,-3.22],2.65,2.35,.22)
            self.rivet('Loop_Closure_Rivet',[x,.55,-1.70],[0,1,0],.25)
            self.hanger_seats.append(((loop_origin+loop_basis@np.array([0,.66,-4.40])-self.mount_origin)@self.mount_basis).tolist())
            self.hanger_frames.append((loop_origin.copy(),loop_basis.copy()))

    def qpoint(self,a,t,inside=False,extra=0):
        t=float(t);rx=4.1+1.55*t;ry=2.75+.45*t
        if inside:rx-=.33;ry-=.33
        rx+=extra;ry+=extra
        co=math.cos(a);si=math.sin(a)
        soft=lambda v:math.copysign(abs(v)**.84,v)
        wrinkle=.045*math.sin(4*a+12*t)*math.sin(math.pi*t)**2
        return np.array([self.lean*(1-t)+(rx+wrinkle)*soft(co),self.qy+(ry+wrinkle*.4)*soft(si),-49+44*t+.10*math.sin(2*a)*t])

    def shell(self):
        self.in_mount('quiver');n=(96,64,40)[self.level];nz=(32,22,12)[self.level]
        ps=[];uv=[];fs=[];slots=[]
        for inner in (False,True):
            for j in range(nz+1):
                t=j/nz if not inner else .011+(1-.011)*j/nz
                for i in range(n):ps.append(self.qpoint(TAU*i/n,t,inner));uv.append((32*i/n/4,44*t/4))
        m=n*(nz+1)
        for side in (0,1):
            for j in range(nz):
                for i in range(n):k=side*m+j*n+i;fs.append([k,side*m+j*n+(i+1)%n,side*m+(j+1)*n+(i+1)%n,k+n]);slots.append(0 if side==0 else 2)
        for i in range(n):fs.append([nz*n+i,nz*n+(i+1)%n,m+nz*n+(i+1)%n,m+nz*n+i]);slots.append(1)
        for start,z,mat in [(0,-49,1),(m,-48.51,2)]:
            c=len(ps);ps.append(np.array([self.lean,self.qy,z]));uv.append((0,0))
            for i in range(n):fs.append([c,start+i,start+(i+1)%n]);slots.append(mat)
        shell=self.mesh('Quiver_Continuous_Hollow_Leather_Shell',ps,fs,0,uv,slots)
        self.band_quiver('Quiver_Rolled_Mouth_Binding',.956,1.005,.12,1)
        self.band_quiver('Quiver_Reinforced_Stitched_Base',0,.105,.10,5)
        for t in (.941,.975,.115,.045):
            aa=np.linspace(0,TAU,200)
            path=[self.qpoint(a,t,extra=.145 if t>.95 or t<.105 else .035) for a in aa]
            normals=[unit([math.cos(a),math.sin(a),.08]) for a in aa]
            self.stitch('Quiver_Circumferential_Saddle_Stitch',path,normals,pitch=.30)
        for a in (-math.pi/2-.27,-math.pi/2+.27,math.pi/2-.13,math.pi/2+.13):
            path=[self.qpoint(a,t,extra=.035) for t in np.linspace(.12,.94,140)]
            self.stitch('Quiver_Longitudinal_Construction_Seam',path,[[math.cos(a),math.sin(a),0]]*len(path),pitch=.31)
        # Front longitudinal seam has a narrow recessed/burnished welt.
        path=[self.qpoint(math.pi/2,t,extra=.025) for t in np.linspace(.11,.95,80)]
        self.tube('Quiver_Long_Seam_Welt',[path],.045,1,6)
        # Separate structural rear strip follows the tapered shell, not a box.
        aa=np.linspace(-math.pi/2-.32,-math.pi/2+.32,12);ts=np.linspace(.08,.98,34)
        points=[self.qpoint(a,t,extra=.08) for t in ts for a in aa]
        faces=[]
        for j in range(len(ts)-1):
            for i in range(len(aa)-1):k=j*len(aa)+i;faces.append([k,k+1,k+1+len(aa),k+len(aa)])
        self.solid(self.mesh('Quiver_Rear_Load_Spreading_Strip',points,faces,5),.18)
        for side in (-1,1):
            xfrac=.32*side;points=[];faces=[];nz2=(22,14,8)[self.level]
            for j,t in enumerate(np.linspace(.015,.99,nz2+1)):
                rx=4.1+1.55*t-.36;ry=2.75+.45*t-.36
                x=self.lean*(1-t)+rx*xfrac;yspan=ry*(1-abs(xfrac)**(2/.84))**(.84/2)
                for s in (-1,1):points.append([x,self.qy+s*yspan,-49+44*t-.10])
            for j in range(nz2):faces.append([j*2,j*2+1,j*2+3,j*2+2])
            self.solid(self.mesh('Quiver_Suede_Internal_Divider',points,faces,2),.17)
            self.tube('Quiver_Divider_Soft_Top_Edge',[[points[-2],points[-1]]],.11,2,8)
        for t in (.14,.88):
            for a in (-math.pi/2-.22,-math.pi/2+.22):self.rivet('Quiver_Rear_Reinforcing_Rivet',self.qpoint(a,t,extra=.16),[math.cos(a),math.sin(a),0],.21)
        return shell

    def band_quiver(self,name,t0,t1,extra,mat):
        n=(96,64,40)[self.level];ps=[];fs=[];uv=[]
        for t in np.linspace(t0,t1,5):
            for i in range(n):ps.append(self.qpoint(i*TAU/n,t,extra=extra));uv.append((32*i/n/4,(t-t0)*44/4))
        for j in range(4):
            for i in range(n):k=j*n+i;fs.append([k,j*n+(i+1)%n,(j+1)*n+(i+1)%n,k+n])
        return self.solid(self.mesh(name,ps,fs,mat,uv),.13)

    def hangers(self):
        self.in_mount('hangers')
        for i,p in enumerate(self.hanger_seats):
            x=p[0];bottom_y=self.qy-2.78
            # Return leg and the curved fold go over the lower D-ring bar;
            # the two ends meet at the press stud on the quiver's rear strip.
            origin,basis=self.hanger_frames[i]
            to_mount=lambda v:(origin+basis@np.array(v)-self.mount_origin)@self.mount_basis
            fold=[to_mount([0,.66+.40*math.cos(a),-4.395+.40*math.sin(a)]) for a in np.linspace(math.pi,0,22)]
            path=np.array([[x-.42,bottom_y-.24,-10.0],to_mount([0,.26,-5.45])]+fold+[to_mount([0,1.06,-5.05]),[x,bottom_y,-7.6],[x-.65,bottom_y+.05,-12.8],[x-.83,bottom_y+.13,-14.4]])
            # Dense path samples keep both edges and seam pitch smooth.
            dense=[]
            for a,b in zip(path[:-1],path[1:]):dense.extend(a*(1-t)+b*t for t in np.linspace(0,1,12,endpoint=False))
            dense=np.array(dense+[path[-1]])
            length=np.r_[0,np.cumsum(np.linalg.norm(np.diff(dense,axis=0),axis=1))]
            samples=np.linspace(0,length[-1],max(48,int(length[-1]/(.075,.12,.22)[self.level])))
            dense=np.stack([np.interp(samples,length,dense[:,k]) for k in range(3)],axis=-1)
            normals=[];sides=[]
            for j in range(len(dense)):
                tangent=unit(dense[min(j+1,len(dense)-1)]-dense[max(j-1,0)])
                side=unit(np.array([1.,0,0])-tangent*tangent[0]);sides.append(side);normals.append(unit(np.cross(side,tangent)))
            normals=np.array(normals);sides=np.array(sides)
            points=[];faces=[];uv=[];arc=np.r_[0,np.cumsum(np.linalg.norm(np.diff(dense,axis=0),axis=1))]
            section=self.rounded_rect(1.82,.24,.045,3 if self.level==0 else 2);ns=len(section)
            for j,q in enumerate(dense):
                for sw,sn in section:
                    points.append(q+sides[j]*sw+normals[j]*sn);uv.append((sw/4,arc[j]/4))
            for j in range(len(dense)-1):
                for k in range(ns):faces.append([j*ns+k,j*ns+(k+1)%ns,(j+1)*ns+(k+1)%ns,(j+1)*ns+k])
            faces.extend([list(reversed(range(ns))),list(range((len(dense)-1)*ns,len(dense)*ns))])
            self.mesh('Hanger_Detachable_Folded_Leather_Strap',points,faces,0,uv)
            for dx in (-.62,.62):self.stitch('Hanger_Strap_Edge_Stitch',dense+sides*dx+normals*.145,normals,pitch=.29)
            for z in (-10.0,-12.7):self.rivet('Hanger_Brass_Press_Stud',[x-.42,bottom_y-.16,z],[0,-1,0],.31)
            self.rivet('Hanger_Upper_Rivet',to_mount([0,1.08,-5.45]),basis[:,1]@self.mount_basis,.22)

    def build(self,level):
        self.level=level;start=len(self.objects)
        self.belt();self.saddle();shell=self.shell();self.hangers();self.world()
        parts=self.objects[start:]
        print('LEATHER_GEOMETRY_AUTHORED',self.body,level,len(parts),flush=True)
        return parts,shell

    def reference_sources(self,shell):
        self.world();ref=self.cols['06_NATIVE_REFERENCES'];high=self.cols['07_HIGH_SURFACE_SOURCES']
        for name,points,faces in [('ST6_Pants',self.pants_points,self.pants_faces),('Native_Body',self.body_points,self.body_faces)]:
            ob=self.mesh(self.body+'_'+name+'_REFERENCE',points,faces,0,col=ref);ob.hide_render=True;ob.display_type='WIRE'
        ob=shell.copy();ob.data=shell.data.copy();ob.parent=None;ob.modifiers.clear();ob.name='HIGH_Quiver_Leather_Surface';high.objects.link(ob)
        sub=ob.modifiers.new('Editable dense physical surface','SUBSURF');sub.subdivision_type='SIMPLE';sub.levels=3;sub.render_levels=3
        self.displace(ob,'Leather_Chestnut')
        high.hide_render=high.hide_viewport=True;ref.hide_render=ref.hide_viewport=True
        for i,p in enumerate(self.hanger_seats):
            ob=bpy.data.objects.new('ATTACH_Quiver_'+('Front' if i else 'Rear'),None);self.cols['08_ATTACHMENT_ANCHORS'].objects.link(ob)
            ob.location=bv(self.mount_origin+self.mount_basis@np.array(p));ob.empty_display_type='ARROWS';ob.empty_display_size=.025
            ob['authoring_anchor_only']=True

    def author(self):
        levels=[];shell=None
        for level in range(3):
            parts,q=self.build(level);levels.append(parts)
            if level==0:shell=q
        self.world();rig=self.native_rig()
        for parts in levels:self.bind(parts,rig)
        rows=[]
        for level,parts in enumerate(levels):
            merged,stats=self.merge_for_export(parts,f'SK_LeatherQuiverBelt_{self.body}_LOD{level}',rig)
            self.fbx([merged],E/(merged.name+'.fbx'),rig)
            self.neutral(merged,R/'Authored'/(merged.name+'.json'))
            if level==0:self.glb([merged],E/f'LeatherQuiverBelt_{self.body}.glb',rig)
            stats.update(lod=level,fbx=str(E/(merged.name+'.fbx')));rows.append(stats)
            bpy.data.objects.remove(merged,do_unlink=True)
            print('LEATHER_LOD_EXPORTED',self.body,level,stats['triangles'],flush=True)
        if self.body=='Jason':
            parts=[o for o in levels[0] if o.get('assembly_kind')=='quiver']
            merged,stats=self.merge_for_export(parts,'SM_LeatherQuiver_Standalone')
            # Rigid module export has its bottom centre at the origin, +Z up.
            for v in merged.data.vertices:
                ue=np.array([v.co.x*100,-v.co.y*100,v.co.z*100]);local=(ue-self.mount_origin)@self.mount_basis-np.array([self.lean,self.qy,-49]);v.co=bv(local)
            merged.vertex_groups.clear();self.fbx([merged],E/'SM_LeatherQuiver_Standalone.fbx');self.glb([merged],E/'LeatherQuiver_Standalone.glb')
            bpy.data.objects.remove(merged,do_unlink=True)
        self.level=0;self.reference_sources(shell)
        for key in ('02_EXPORT_LOD1','03_EXPORT_LOD2','05_STANDALONE_MASTERS','08_ATTACHMENT_ANCHORS'):self.cols[key].hide_render=self.cols[key].hide_viewport=True
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type=='VIEW_3D':area.spaces.active.region_3d.view_distance=1.1;area.spaces.active.region_3d.view_location=bv(self.mount_origin+self.up*-20)
        self.selection(levels[0]);bpy.ops.file.pack_all();path=E/f'LeatherQuiverBelt_{self.body}_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(path))
        pivot=self.mount_origin+self.mount_basis@np.mean(self.hanger_seats,axis=0)
        axis=self.mount_basis@unit([-self.lean,0,44])
        tips=[(self.mount_origin+self.mount_basis@np.array([self.lean+x,self.qy+y,-47.6+dz])).tolist() for x,y,dz in [(-2.6,.7,0),(-2.6,-.8,1.0),(0,.55,.3),(2.6,-.7,.8),(2.6,1.,0)]]
        write(R/'Authored'/f'{self.body}_attachments.json',dict(body=self.body,frame_origin_cm=self.mount_origin.tolist(),frame_basis=self.mount_basis.tolist(),quiver_center_offset_cm=self.qy,attachment_points_cm=self.hanger_seats,weights=self.mount_weights,rigid_module=True,side='right',pivot=pivot.tolist(),outward=self.mount_basis[:,1].tolist(),arrow_up=axis.tolist(),arrow_tips=tips))
        report=dict(body=self.body,blend=str(path),lods=rows,fit=self.fit_report,quiver_empty=True,detachable_geometry=True,game_integrated=False,runtime_tested=False)
        write(R/'Authored'/f'{self.body}_production.json',report)

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    for row in read(R/'inputs.json')['records']:
        if args and row['body'] not in args:continue
        LeatherBelt(row).author();gc.collect()
    rows=[read(R/'Authored'/f'{b}_production.json') for b in ('Jason','Kaitlin') if (R/'Authored'/f'{b}_production.json').exists()]
    write(R/'authored.json',dict(completed=len(rows)==2,name='皮革箭袋腰带',records=rows,texture_maps=24,unreal_imported=False,runtime_tested=False))
