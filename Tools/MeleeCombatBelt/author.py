"""Detailed editable melee belt, built in native waist coordinates, in centimetres.

Only writes this asset's ModelR1 sources/exports. No UE publication or preview run.
"""
import sys,math,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from native_geometry import *

NYLON,WEB,PAD,LEATHER,EDGE,GRAPHITE,TITANIUM,LINING,THREAD=range(9)

def rounded(w,h,r,n=8):
    out=[]
    for x,z,a in ((w/2-r,h/2-r,0),(-w/2+r,h/2-r,90),(-w/2+r,-h/2+r,180),(w/2-r,-h/2+r,270)):
        for q in np.linspace(a,a+90,n,endpoint=False):out.append([x+r*math.cos(math.radians(q)),z+r*math.sin(math.radians(q))])
    return np.array(out)

def catmull(points,steps=10):
    q=np.array(points,dtype=float);q=np.vstack((q[0],q,q[-1]));out=[]
    for i in range(1,len(q)-2):
        a,b,c,d=q[i-1:i+3]
        for t in np.linspace(0,1,steps,endpoint=False):out.append(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
    return np.array(out+[q[-2]])

class MeleeBelt(NativeBelt):
    def __init__(self,row):
        super().__init__(row)
        self.parts=[]
        self.scene['asset_name']='破阵近战腰带'
        self.scene['production_stage']='Detailed model; no gameplay integration'
        self.scene['front_definition']='Native body forward; inventory display normalized separately'
        # The exporter reads this named group for the AO channel of the same ORM.
        settings=bpy.data.node_groups.new('glTF Material Output','ShaderNodeTree')
        settings.interface.new_socket('Occlusion',in_out='INPUT',socket_type='NodeSocketFloat')
        settings.nodes.new('NodeGroupInput');settings.nodes.new('NodeGroupOutput')
        for material in self.mats:
            separate=next((n for n in material.node_tree.nodes if n.bl_idname=='ShaderNodeSeparateColor'),None)
            if separate:
                node=material.node_tree.nodes.new('ShaderNodeGroup');node.node_tree=settings
                material.node_tree.links.new(separate.outputs['Red'],node.inputs['Occlusion'])

    def finish(self,ob,bevel=.055):
        if bevel:
            b=ob.modifiers.new('Manufactured edge radius','BEVEL');b.width=bevel*.01;b.segments=4;b.limit_method='ANGLE';b.angle_limit=math.radians(38);b.use_clamp_overlap=True;b.harden_normals=True
        n=ob.modifiers.new('Preserved planar hard-surface normals','WEIGHTED_NORMAL');n.keep_sharp=True;n.weight=45
        return ob

    def stitch(self,name,path,normals,mat=THREAD,pitch=.26,radius=.015):
        return Cap.stitch(self,name,path,normals,mat,pitch,radius)

    def frame(self,*args,**kwargs):
        return self.finish(Cap.frame(self,*args,**kwargs),0)

    def prism(self,name,outline,y0,y1,mat,bevel=.055):
        a=np.array(outline);n=len(a)
        ps=[[x,y,z] for y in (y0,y1) for x,z in a]
        fs=[list(range(n-1,-1,-1)),list(range(n,n*2))]
        fs += [[i,(i+1)%n,(i+1)%n+n,i+n] for i in range(n)]
        return self.finish(self.mesh(name,ps,fs,mat),bevel)

    def ring(self,name,x,y,z,w,h,r=.17,mat=TITANIUM):
        line=[[x+a,y,z+b] for a,b in rounded(w,h,min(w,h)*.30,12)]
        return self.tube(name,[line],r,mat,sides=12,closed=True)

    def fastener(self,name,x,y,z,r=.22,mat=TITANIUM):
        # Recessed hex drive, bevelled rim, actual lower socket floor.
        n=24;ps=[];fs=[]
        for radius,depth,hexagon in [(r,0,False),(r,.065,False),(.84*r,.10,False),(.43*r,.10,True),(.43*r,.025,True)]:
            for k in range(n):
                a=TAU*k/n;rr=radius
                if hexagon:rr*=math.cos(math.pi/6)/math.cos((a%(math.pi/3))-math.pi/6)
                ps.append([x+rr*math.cos(a),y+depth,z+rr*math.sin(a)])
        for j in range(4):
            for k in range(n):fs.append([j*n+k,j*n+(k+1)%n,(j+1)*n+(k+1)%n,(j+1)*n+k])
        fs.extend([list(range(n-1,-1,-1)),list(range(4*n,5*n))])
        return self.mesh(name,ps,fs,mat)

    def shape_height(self,a):
        c=math.cos(a)
        return 6.3+2.7*(1-abs(c)**4)+1.3*max(0,-c)**4

    def profile_v(self,a,t):return .5+(t-.5)*self.shape_height(a)/self.height

    def shaped_band(self,name,inner,outer,mat):
        self.world();na=512;nv=12;ps=[];uv=[];fs=[]
        arcs=np.linspace(4.7,self.perimeter-4.7,na+1)
        for offset in (inner,outer):
            for j in range(nv+1):
                for s in arcs:
                    a=self.angle(s);v=self.profile_v(a,j/nv)
                    ps.append(self.point(a,v,offset));uv.append([s/4,v*self.height/4])
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
        self.shaped_band('Belt_OuterShapedNylon',.06,.52,NYLON)
        self.shaped_band('Belt_InnerBreathableLining',-.16,.07,PAD)
        self.band('ContinuousLoadBearingWebbing',4.65,self.perimeter-4.65,.28,.72,.51,.76,WEB,n=512)
        for t in (.025,.975):
            arcs=np.linspace(4.75,self.perimeter-4.75,620);angles=[self.angle(s) for s in arcs]
            path=[self.point(a,self.profile_v(a,t),.55) for a in angles]
            self.tube('PerimeterRolledBinding_'+str(t),[path],.075,WEB,10)
            for d in (.20,.42):
                p=[self.point(a,self.profile_v(a,t)+(d/self.height if t<.5 else -d/self.height),.555) for a in angles]
                self.stitch('PerimeterDoubleStitch_'+str((t,d)),p,[self.outward(a) for a in angles])
        for v in (.32,.68):
            aa=[self.angle(s) for s in np.linspace(4.85,self.perimeter-4.85,580)]
            self.stitch('LoadStrapLockStitch_'+str(v),[self.point(a,v,.775) for a in aa],[self.outward(a) for a in aa],pitch=.3)
        # Short cushion islands retain deformation gaps instead of one rigid ring.
        count=12;span=(self.perimeter-16)/count
        for i in range(count):
            s=8+i*span
            self.band('InnerPad_%02d'%i,s+.22,s+span-.22,.12,.88,-.19,-.045,PAD,n=320,puff=.08)
        # Curved center-back panel remains thin for the backpack contact zone.
        s=self.perimeter/2
        self.band('RearLowProfilePad',s-5.0,s+5.0,.14,.86,.53,.89,PAD,n=480)
        for v in (.16,.84):
            aa=[self.angle(q) for q in np.linspace(s-4.9,s+4.9,100)]
            self.tube('RearPadBoundEdge_'+str(v),[[self.point(a,v,.91) for a in aa]],.07,WEB,8)
            self.stitch('RearPadStitch_'+str(v),[self.point(a,v+(.025 if v<.5 else -.025),.925) for a in aa],[self.outward(a) for a in aa])

    def buckle(self):
        self.local(0,.82,'buckle')
        left=[[-2.8,-2.65],[-.7,-2.65],[1.03,0],[-.7,2.65],[-2.8,2.65]]
        right=[[-.39,-2.65],[2.8,-2.65],[2.8,2.65],[-.39,2.65],[1.35,0]]
        for name,p in [('Male',left),('Female',right)]:
            self.prism('Buckle_'+name+'_MetalShell',p,-.05,.50,TITANIUM,.10)
            a=np.array(p);center=a.mean(0);inset=center+(a-center)*.88
            self.prism('Buckle_'+name+'_GraphiteInset',inset,.495,.555,GRAPHITE,.045)
        for sign in (-1,1):
            self.frame('Buckle_WebbingWindow_'+str(sign),[sign*3.75,.16,0],2.7,5.1,1.52,3.82,.58,TITANIUM)
            q=catmull([[sign*5.9,-.16,0],[sign*4.5,-.16,0],[sign*3.4,-.12,0],[sign*3.22,.32,0],[sign*3.55,.74,0],[sign*4.6,.77,0],[sign*5.9,.68,0]],8)
            self.ribbon('Buckle_ThreadedReturnStrap_'+str(sign),q,[np.array([0,1,0])]*len(q),3.6,WEB,.18)
            for z in (-1.45,1.45):
                line=[[sign*x,.80,z] for x in np.linspace(4.25,5.8,20)]
                self.stitch('Buckle_ReturnStitch_'+str((sign,z)),line,[[0,1,0]]*len(line))
            for z in (-2.12,2.12):self.fastener('Buckle_FramePin_'+str((sign,z)),sign*3.15,.48,z,.12,GRAPHITE)

    def side_plates(self):
        for sign in (-1,1):
            for index,f in enumerate((.10,.19,.29,.39)):
                arc=sign*f*self.perimeter
                self.local(arc,.92,'segmented_plate')
                w,h=6.0,6.9
                p=np.array([[-w/2+.6,-h/2],[w/2-.6,-h/2],[w/2,-h/2+.6],[w/2,h/2-.5],[w/2-.5,h/2],[-w/2+.5,h/2],[-w/2,h/2-.5],[-w/2,-h/2+.6]])
                prefix='Plate_%s_%02d'%('Right' if sign>0 else 'Left',index)
                self.prism(prefix+'_LeatherSaddle',p*1.13,-.27,.02,LEATHER,.10)
                self.prism(prefix+'_TitaniumRim',p,0,.23,TITANIUM,.075)
                self.prism(prefix+'_GraphiteFace',p*.95,.225,.31,GRAPHITE,.045)
                seam=[[x,.04,z] for x,z in p*1.075];seam.append(seam[0])
                self.stitch(prefix+'_SaddleStitch',seam,[[0,1,0]]*len(seam),pitch=.25)
                self.tube(prefix+'_BurnishedSaddleEdge',[[[x,-.02,z] for x,z in p*1.125]],.035,EDGE,8,True)
                for x in (-2.27,2.27):
                    for z in (-2.70,2.70):
                        self.fastener(prefix+'_SocketRivet_'+str((x,z)),x,.31,z,.21,GRAPHITE)
                        self.ring(prefix+'_RivetWasher_'+str((x,z)),x,.34,z,.42,.42,.025,TITANIUM)
                # Compliant rear pads bridge the load strap to the rigid plate.
                for x in (-2.2,2.2):self.box(prefix+'_RearBearing', [x,-.34,0],[1.1,.35,4.8],LINING,.12)

    def scabbard_mount(self):
        self.local(-.23*self.perimeter,1.25,'scabbard_carrier')
        self.prism('LeftCarrier_LeatherAnchor',rounded(3.8,9.1,.45),-.30,.04,LEATHER,.08)
        self.prism('LeftCarrier_RecessedMetalSpine',rounded(3.05,8.3,.35),.02,.25,GRAPHITE,.07)
        for z in (-3.2,3.2):self.fastener('LeftCarrier_AnchorBolt_'+str(z),0,.27,z,.30,TITANIUM)
        for index,anchor in enumerate((2.35,-2.55)):
            self.ring('CarrierPivot_Dring_'+str(index),0,.60,anchor+.12,2.55,1.75,.19,TITANIUM)
            neck=catmull([[0,.10,anchor+.85],[0,.54,anchor+.92],[0,1.12,anchor+.72],[0,1.62,anchor]],8)
            self.ribbon('Carrier_ReinforcedNeck_'+str(index),neck,[[0,1,0]]*len(neck),2.30,LEATHER,.22)
            self.fastener('Carrier_NeckStud_'+str(index),0,1.12,anchor+.64,.22,GRAPHITE)
            q=[];nn=[]
            for a in np.linspace(0,TAU,97):
                q.append([0,1.62+1.22*math.sin(a),anchor-2.15+2.15*math.cos(a)])
                nn.append(unit([0,2.15*math.sin(a),1.22*math.cos(a)]))
            self.ribbon('Carrier_EmptyLeatherLoop_'+str(index),np.array(q),nn,2.30,LEATHER,.22)
            for x in (-.92,.92):
                self.stitch('Carrier_LoopLockStitch_'+str((index,x)),np.array(q)+[x,0,0],nn,pitch=.24)
                self.tube('Carrier_BurnishedLoopEdge_'+str((index,x)),[np.array(q[:-1])+[x*1.22,0,0]],.033,EDGE,8,True)
            self.frame('Carrier_LoopAdjuster_'+str(index),[0,2.95,anchor-2.15],2.88,1.6,2.42,1.03,.22,TITANIUM)
            self.box('Carrier_AdjusterBridge_'+str(index),[0,3.08,anchor-2.15],[2.53,.18,.16],TITANIUM,.045)

    def stone_case(self):
        self.local(.23*self.perimeter,1.03,'stone_case')
        # A real open top, continuous wall thickness, closed base and inner lining.
        contour=rounded(7.8,2.65,.48,10);ps=[];uv=[];fs=[];n=len(contour)
        zs=[-2.9,-2.68,-1.7,0,1.5,2.7]
        for j,z in enumerate(zs):
            scale=.95+.05*math.sin(math.pi*.5*j/(len(zs)-1))
            for i,(x,y) in enumerate(contour):ps.append([x*scale,y*scale+1.325,z]);uv.append([i/n*20.0/4,(z+2.9)/4])
        for j in range(len(zs)-1):
            for i in range(n):fs.append([j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i])
        fs.append(list(range(n-1,-1,-1)))
        shell=self.mesh('StoneCase_ContinuousLeatherShell',ps,fs,LEATHER,uv)
        self.solid(shell,.18,LINING-LEATHER)
        self.tube('StoneCase_RolledMouth',[[[x,y+1.325,2.70] for x,y in contour]],.075,EDGE,10,True)
        self.box('StoneCase_InnerBottomPad',[0,1.30,-2.66],[6.95,1.95,.18],LINING,.12)
        for x in (-2.55,2.55):
            q=catmull([[x,-.19,-2.6],[x,-.22,0],[x,-.20,2.7],[x,.12,2.86],[x,.32,2.45]],10)
            self.ribbon('StoneCase_RearMountStrap_'+str(x),q,[[0,1,0]]*len(q),1.38,WEB,.18)
            self.fastener('StoneCase_RearMountPin_'+str(x),x,.12,2.44,.18,GRAPHITE)
        q=catmull([[0,.08,1.9],[0,.08,2.75],[0,.62,3.02],[0,2.30,2.96],[0,2.93,2.50],[0,3.04,1.48],[0,3.06,-.95]],10)
        verts=[];faces=[];uv=[];nx=32
        for j,p in enumerate(q):
            for i,x in enumerate(np.linspace(-3.87,3.87,nx+1)):
                corner=max(abs(x)-3.22,0);lift=.65-math.sqrt(max(0,.65*.65-corner*corner))
                z=p[2]+lift*max(0,(j/(len(q)-1)-.75)/.25)
                y=p[1]+.045*(1-(x/3.87)**2)*math.sin(math.pi*j/(len(q)-1))
                verts.append([x,y,z]);uv.append([(x+3.87)/4,j/(len(q)-1)*7.9/4])
        for j in range(len(q)-1):
            for i in range(nx):k=j*(nx+1)+i;faces.append([k,k+1,k+nx+2,k+nx+1])
        flap=self.mesh('StoneCase_RoundedFullWidthFlap',verts,faces,LEATHER,uv);self.solid(flap,.18,LEATHER-LEATHER)
        for x in (-3.56,3.56):self.stitch('StoneCase_FlapSideStitch_'+str(x),q+[x,.025,0],[[0,1,0]]*len(q),pitch=.24)
        line=[[x,3.10,-.72] for x in np.linspace(-3.22,3.22,90)]
        self.stitch('StoneCase_FlapHemStitch',line,[[0,1,0]]*len(line),pitch=.24)
        self.tube('StoneCase_FlapBurnishedHem',[[[x,3.065,-.96] for x in np.linspace(-3.22,3.22,60)]],.048,EDGE,8)
        self.fastener('StoneCase_SingleSnap',0,3.125,.15,.35,GRAPHITE)
        self.ring('StoneCase_SnapEdge',0,3.17,.15,.68,.68,.025,TITANIUM)
        self.local(.23*self.perimeter+6.3,1.05,'utility_loop')
        self.prism('UtilityLoop_WebbingAnchor',rounded(2.05,5.2,.3),-.22,.13,WEB,.055)
        self.ring('UtilityLoop_FoldedMetalRing',0,.50,-1.15,2.3,3.3,.21,TITANIUM)
        self.fastener('UtilityLoop_AnchorStud',0,.2,1.7,.20,GRAPHITE)

    def sources(self,parts):
        self.world();ref=self.cols['06_NATIVE_REFERENCES'];ref.hide_render=True
        self.mesh(self.body+'_ST6TrouserReference',self.pants_points,self.pants_faces,LINING,col=ref)
        ref.hide_viewport=True
        self.sockets=[]
        for name,arc in [('FrontBuckle',0),('LeftScabbardCarrier',-.23*self.perimeter),('RightStoneCase',.23*self.perimeter),('RearBackpackClearance',self.perimeter/2)]:
            origin,basis=self.frame_at(arc,1.0);ob=bpy.data.objects.new('ATTACH_'+name,None);self.cols['08_ATTACHMENT_ANCHORS'].objects.link(ob);ob.empty_display_type='ARROWS';ob.empty_display_size=.022;ob.location=bv(origin)
            self.sockets.append(dict(name=name,origin_cm=origin.tolist(),basis=basis.tolist(),native_weights=self.native_weights(origin)))
        self.cols['08_ATTACHMENT_ANCHORS'].hide_render=True

    def author(self):
        self.tailoring();self.buckle();self.side_plates();self.scabbard_mount();self.stone_case()
        parts=list(self.objects);rig=self.native_rig();self.bind(parts,rig)
        print('MELEE_DETAIL_ASSEMBLED',self.body,len(parts),flush=True)
        merged,stats=self.merge_for_export(parts,'SK_MeleeCombatBelt_'+self.body,rig)
        self.fbx([merged],E/(merged.name+'.fbx'),rig)
        self.glb([merged],E/(merged.name+'.glb'),rig)
        self.neutral(merged,E/(self.body+'_NativeWeightedMesh.json'))
        # Rigid display mesh preserves this full-detail geometry; no decimation.
        if self.body=='Jason':
            display=merged.copy();display.data=merged.data.copy();display.modifiers.clear();display.parent=None;self.scene.collection.objects.link(display);display.name='SM_MeleeCombatBelt_Display'
            center=self.point(0,.5,0);center=self.origin+self.up*center[2]
            for v in display.data.vertices:
                native=np.array([v.co.x*100,-v.co.y*100,v.co.z*100])-center
                v.co=Vector((float(native@self.right)*.01,-float(native@self.forward)*.01,float(native@self.up)*.01))
            display.vertex_groups.clear();self.fbx([display],E/(display.name+'.fbx'));self.glb([display],E/(display.name+'.glb'));bpy.data.objects.remove(display,do_unlink=True)
        bpy.data.objects.remove(merged,do_unlink=True)
        self.sources(parts)
        rig.hide_set(True)
        for key in ('02_EXPORT_LOD1','03_EXPORT_LOD2','04_RIGID_ATTACHMENT_MASTERS','05_EXPORT_ASSEMBLY','07_HIGH_SURFACE_SOURCES'):
            self.cols[key].hide_render=True;self.cols[key].hide_viewport=True
        self.selection(parts)
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type=='VIEW_3D':
                    area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_distance=.72;area.spaces.active.region_3d.view_location=bv(self.origin+self.up*self.point(0,.5,0)[2])
        self.scene.render.engine='CYCLES';self.scene.cycles.samples=64
        bpy.ops.file.pack_all();blend=E/f'MeleeCombatBelt_{self.body}_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        report=dict(body=self.body,completed=True,blend=str(blend),fbx=str(E/('SK_MeleeCombatBelt_'+self.body+'.fbx')),glb=str(E/('SK_MeleeCombatBelt_'+self.body+'.glb')),geometry=stats,fit=self.fit_report,attachments=self.sockets,material_slots=[m.name for m in self.mats],rigid_parts_not_globally_scaled=True,decimated=False,game_integrated=False,runtime_tested=False,preview_rendered=False)
        write(R/'Authored'/f'{self.body}_production.json',report)
        print('MELEE_DETAIL_SAVED',self.body,stats['triangles'],str(blend),flush=True)

if __name__=='__main__':
    chosen=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['Jason','Kaitlin']
    for row in read(R/'inputs.json')['records']:
        if row['body'] in chosen:MeleeBelt(row).author()
