"""Author the approved arcane belt as native, editable, fully detailed meshes.

Centimetres in construction space. Exports only this asset; no UE or renders.
"""
import sys,math,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from construction import *

class ArcaneBelt(BeltConstruction):
    def __init__(self,row):
        super().__init__(row)
        self.scene['reference']='ConceptR1/design-sheet.png'
        self.scene['fit_scope']='Saved ST6 trousers/native waist; robe adaptation not yet authored'
        for name,color,rough,metal,trans,emission in (
            ('Arcane_SmokyVioletQuartz',(.105,.035,.19),.14,0,.63,.035),
            ('Arcane_RecessedRuneEnamel',(.035,.007,.12),.27,.18,0,1.1),
            ('Arcane_DarkRecess',(.008,.009,.012),.69,.25,0,0)):
            m=bpy.data.materials.new(name);m.use_nodes=True;bs=m.node_tree.nodes.get('Principled BSDF')
            bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough
            bs.inputs['Metallic'].default_value=metal;bs.inputs['Transmission Weight'].default_value=trans
            bs.inputs['IOR'].default_value=1.46
            bs.inputs['Emission Color'].default_value=(.16,.025,.48,1);bs.inputs['Emission Strength'].default_value=emission
            self.mats.append(m)

    def annulus(self,name,inner,outer,y0,y1,mat,a0=0,a1=TAU):
        closed=abs(a1-a0-TAU)<1.e-6;n=max(8,round(96*(a1-a0)/TAU))
        aa=np.linspace(a0,a1,n,endpoint=False) if closed else np.linspace(a0,a1,n+1)
        count=len(aa);ps=[];uv=[];fs=[]
        for y,r in ((y0,inner),(y0,outer),(y1,inner),(y1,outer)):
            for a in aa:ps.append([r*math.cos(a),y,r*math.sin(a)]);uv.append([a*outer/4,r/4])
        for j in range(count if closed else count-1):
            k=(j+1)%count
            for u,v in ((0,1),(1,3),(3,2),(2,0)):fs.append([u*count+j,u*count+k,v*count+k,v*count+j])
        if not closed:
            fs.extend([[0,count,3*count,2*count],[count-1,3*count-1,4*count-1,2*count-1]])
        return self.finish(self.mesh(name,ps,fs,mat,uv),.025)

    def star(self,name,x,y,z,r=.55,mat=BRASS):
        p=[]
        for i in range(16):
            a=TAU*i/16;radius=r*(1 if i%4==0 else .65 if i%2==0 else .22)
            p.append([x+radius*math.cos(a),z+radius*math.sin(a)])
        return self.prism(name,p,y,y+.016,mat,.006)

    def constellation(self,name,x,y,z,scale=1,mat=BRASS):
        points=np.array([[-1.45,.95],[-.52,.42],[.35,1.40],[1.28,.65],[.75,-.65],[-.85,-1.15]])*scale
        paths=[]
        for a,b in ((0,1),(1,2),(2,3),(3,4),(4,5),(5,1)):
            paths.append([[x+points[k,0],y,z+points[k,1]] for k in (a,b)])
        self.tube(name+'_FineInlay',paths,.009,mat,5)
        for i,p in enumerate(points):self.star(name+'_Star_%02d'%i,x+p[0],y,z+p[1],(.14 if i%2 else .22)*scale,mat)

    def band_height(self,a):return 7.2-2.2*max(0,-math.cos(a))**4
    def band_v(self,a,t):return .5+(t-.5)*self.band_height(a)/self.height

    def shaped_band(self,name,inner,outer,mat):
        self.world();na=384;nv=8;ps=[];uv=[];fs=[]
        arcs=np.linspace(3.55,self.perimeter-3.55,na+1)
        for offset in (inner,outer):
            for j in range(nv+1):
                for s in arcs:
                    a=self.angle(s);v=self.band_v(a,j/nv)
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
        self.shaped_band('Belt_IndigoDoubleLeather',.05,.43,INDIGO)
        self.shaped_band('Belt_SoftNavyInnerLining',-.13,.055,LINING)
        for t in (.025,.975):
            aa=[self.angle(s) for s in np.linspace(3.6,self.perimeter-3.6,620)]
            path=[self.point(a,self.band_v(a,t),.445) for a in aa]
            self.tube('Belt_RolledEdge_'+str(t),[path],.06,EDGE,8)
            for inset in (.19,.38):
                vv=[self.band_v(a,t)+(inset/self.height if t<.5 else -inset/self.height) for a in aa]
                self.stitch('Belt_DoubleSaddleStitch_'+str((t,inset)),[self.point(a,v,.46) for a,v in zip(aa,vv)],[self.outward(a) for a in aa],pitch=.29)
        for i,f in enumerate((.34,.43,.57,.66)):
            # band() already emits native world-space waist points. The prior
            # keeper's pin frame must not transform the next leather loop again.
            self.world()
            s=self.perimeter*f;a=self.angle(s);h=self.band_height(a)-.2
            self.band('LeatherKeeper_%d'%i,s-.55,s+.55,.5-h/2/self.height,.5+h/2/self.height,.44,.70,INDIGO,n=220)
            self.local(s,.72,'rear_keeper')
            for z in (-h/2+.35,h/2-.35):self.fastener('Keeper_Pin_%s_%s'%(i,z),0,0,z,.115,BRASS)

    def buckle(self):
        self.local(0,.61,'astrolabe_buckle')
        for sign in (-1,1):
            self.frame('Buckle_RealStrapWindow_'+str(sign),[sign*3.65,.08,0],2.2,4.85,1.18,3.72,.36,DARKSILVER)
            path=catmull([[sign*5.05,-.12,0],[sign*4.1,-.13,0],[sign*3.48,-.12,0],[sign*3.42,.30,0],[sign*3.9,.40,0],[sign*5.05,.37,0]],8)
            self.ribbon('Buckle_ThreadedLeatherReturn_'+str(sign),path,[[0,1,0]]*len(path),3.65,INDIGO,.16)
            for z in (-1.48,1.48):
                p=[[sign*x,.45,z] for x in np.linspace(4.0,5.0,22)]
                self.stitch('Buckle_ReturnSeam_'+str((sign,z)),p,[[0,1,0]]*len(p))
        outline=[[3.10*math.cos(a),3.10*math.sin(a)] for a in np.linspace(0,TAU,96,endpoint=False)]
        self.prism('Astrolabe_ClosedClaspBackplate',outline,-.08,.18,DARKSILVER,.045)
        self.annulus('Astrolabe_RecessedOuterRuneTrack',2.48,2.71,.20,.25,RUNE)
        for i in range(4):
            a=i*math.pi/2+.08;b=(i+1)*math.pi/2-.08
            self.annulus('Astrolabe_OuterMachinedSegment_%d'%i,2.72,3.10,.18,.48,SILVER,a,b)
            self.annulus('Astrolabe_InnerIndexSegment_%d'%i,2.12,2.40,.28,.59,SILVER,a+.12,b-.12)
        self.annulus('Astrolabe_InnerDarkAnnularSeat',1.20,2.10,.19,.31,DARKSILVER)
        self.annulus('Astrolabe_CrystalRetainingBezel',1.13,1.37,.27,.72,BRASS)
        for i in range(4):
            a=i*math.pi/2
            self.fastener('Astrolabe_PivotStud_%d'%i,2.58*math.cos(a),.27,2.58*math.sin(a),.15,BRASS)
        # Every scale mark is seated into a lower channel between metal rings.
        paths=[]
        for i in range(48):
            a=TAU*i/48;r0=2.79;r1=3.01 if i%4==0 else 2.91
            paths.append([[r*math.cos(a),.489,r*math.sin(a)] for r in (r0,r1)])
        self.tube('Astrolabe_EngravedIndexInlays',paths,.009,ETCH,5)
        ps=[];uv=[];fs=[];n=24
        for r,y in ((.78,.30),(1.12,.51),(1.16,.72),(.91,1.04),(.31,1.14)):
            for i in range(n):
                a=TAU*i/n;ps.append([r*math.cos(a),y,r*math.sin(a)]);uv.append([.5+.5*math.cos(a)*r/1.16,.5+.5*math.sin(a)*r/1.16])
        for j in range(4):
            for i in range(n):k=(i+1)%n;fs.append([j*n+i,j*n+k,(j+1)*n+k,(j+1)*n+i])
        fs.extend([list(range(n-1,-1,-1)),list(range(4*n,5*n))])
        gem=self.mesh('Quartz_RecessedFacetedLens',ps,fs,CRYSTAL,uv)
        for face in gem.data.polygons:face.use_smooth=False
        self.constellation('Quartz_EmbeddedStarMap',0,.94,0,.46,SILVER)
        for i in range(3):
            a=TAU*i/3+math.pi/2
            path=[[r*math.cos(a),y,r*math.sin(a)] for r,y in ((1.56,.30),(1.45,.48),(1.32,.81),(1.02,1.08))]
            self.tube('Quartz_SolidRetainingClaw_%d'%i,[catmull(path,8)],.095,SILVER,10)

    def side_plates(self):
        for sign in (-1,1):
            for index,arc in enumerate((7.7,13.7)):
                self.local(sign*arc,.59,'articulated_rune_plate')
                prefix='Plate_%s_%d'%('Right' if sign>0 else 'Left',index)
                self.prism(prefix+'_LeatherMount',rounded(5.55,6.25,.38),-.15,.04,INDIGO,.055)
                self.prism(prefix+'_SilverBackplate',rounded(5.05,5.70,.27),.04,.18,SILVER,.035)
                self.frame(prefix+'_RaisedPerimeter',[0,.20,0],5.05,5.70,4.50,5.15,.16,SILVER)
                self.prism(prefix+'_InsetConstellationFace',rounded(4.42,5.06,.20),.10,.215,DARKSILVER,.025)
                self.constellation(prefix+'_StarChart',0,.232,0,1.15,BRASS)
                # Low enamel sits below the surrounding frame lip.
                p=[[-2.30,.20,2.35],[-2.30,.20,-2.2],[-2.12,.20,-2.39],[1.45,.20,-2.39]]
                self.tube(prefix+'_RecessedRuneInlay',[p],.026,RUNE,7)
                for x in (-2.30,2.30):
                    for z in (-2.58,2.58):self.fastener(prefix+'_Rivet_'+str((x,z)),x,.28,z,.105,BRASS)
                for x in (-2.62,2.62):
                    p=[[x,.06,z] for z in np.linspace(-2.5,2.5,32)]
                    self.stitch(prefix+'_LeatherSeam_'+str(x),p,[[0,1,0]]*len(p),pitch=.30)

    def rune_case(self):
        self.local(-.23*self.perimeter,.65,'left_rune_case')
        for x in (-2.05,2.05):
            self.prism('RuneCase_BackAttachment_'+str(x),rounded(1.12,5.9,.15)+[x,.10],-.34,.02,INDIGO,.05)
            for z in (-2.30,2.50):self.fastener('RuneCase_AnchorPin_'+str((x,z)),x,.05,z,.13,BRASS)
        # Actual open-top shell with inner lining, floor, and rolled rim.
        outer=rounded(6.5,1.95,.36,9);inner=rounded(6.10,1.55,.27,9)
        ps=[];fs=[];slots=[];count=len(outer)
        for ring,z in ((outer,-5.9),(outer,3.1),(inner,-5.66),(inner,3.1)):
            ps.extend([[x,y+.91,z] for x,y in ring])
        for i in range(count):
            j=(i+1)%count
            fs.extend([[i,j,count+j,count+i],[2*count+i,3*count+i,3*count+j,2*count+j],[count+i,count+j,3*count+j,3*count+i]])
            slots.extend([INDIGO,LINING,EDGE])
        fs.extend([list(range(count-1,-1,-1)),list(range(2*count,3*count))]);slots.extend([INDIGO,LINING])
        shell=self.mesh('RuneCase_HollowLeatherBody',ps,fs,INDIGO,slots=slots);self.finish(shell,.035)
        # A real separate folded lid, attached at the back and curved over the opening.
        q=catmull([[0,-.11,2.6],[0,-.10,3.34],[0,.55,3.46],[0,1.60,3.34],[0,2.00,2.88],[0,2.04,1.40],[0,2.02,-.48],[0,1.99,-1.12]],8)
        ps=[];uv=[];fs=[];nx=36
        for j,p in enumerate(q):
            for i,x in enumerate(np.linspace(-3.28,3.28,nx+1)):
                corner=max(abs(x)-2.85,0);lift=(.45-math.sqrt(max(0,.45*.45-corner*corner)))*max(0,(j/(len(q)-1)-.80)/.20)
                ps.append(p+[x,.035*(1-(x/3.28)**2),lift]);uv.append([(x+3.28)/4,j/(len(q)-1)*6.8/4])
        for j in range(len(q)-1):
            for i in range(nx):k=j*(nx+1)+i;fs.append([k,k+1,k+nx+2,k+nx+1])
        flap=self.mesh('RuneCase_ShapedClosureFlap',ps,fs,INDIGO,uv);self.solid(flap,.16)
        for x in (-3.02,3.02):
            self.stitch('RuneCase_FlapStitch_'+str(x),q+[x,.04,.04],[[0,1,0]]*len(q),pitch=.25)
        lower=[[x,2.035,-1.05] for x in np.linspace(-2.84,2.84,65)]
        self.tube('RuneCase_BurnishedFlapHem',[lower],.045,EDGE,8)
        self.stitch('RuneCase_HemSaddleStitch',np.array(lower)+[0,.02,.19],[[0,1,0]]*len(lower),pitch=.25)
        self.prism('RuneCase_SilverClosureTongue',[[-.44,1.3],[.44,1.3],[.44,-2.9],[0,-3.35],[-.44,-2.9]],2.02,2.15,SILVER,.04)
        self.prism('RuneCase_ClosureEnamelDiamond',[[0,-.45],[.20,-.82],[0,-1.19],[-.20,-.82]],2.155,2.18,RUNE,.01)
        self.star('RuneCase_ClosureCompass',0,2.16,.56,.32,DARKSILVER)
        self.constellation('RuneCase_FlapConstellation',0,2.09,1.9,.43,BRASS)

    def axial_part(self,name,sections,mat,sides=64,cy=1.75,cz=-.10):
        ps=[];uv=[];fs=[]
        for x,r in sections:
            for i in range(sides):
                a=TAU*i/sides;ps.append([x,cy+r*math.cos(a),cz+r*math.sin(a)]);uv.append([x/4,TAU*r*i/sides/4])
        for j in range(len(sections)-1):
            for i in range(sides):k=(i+1)%sides;fs.append([j*sides+i,j*sides+k,(j+1)*sides+k,(j+1)*sides+i])
        fs.extend([list(range(sides-1,-1,-1)),list(range((len(sections)-1)*sides,len(sections)*sides))])
        ob=self.mesh(name,ps,fs,mat,uv)
        return self.finish(ob,.045 if sides==6 else 0)

    def scroll_canister(self):
        self.local(.27*self.perimeter,.85,'right_scroll_canister')
        # Keep the rigid tube the same dimensions on both bodies, tilted along hip.
        a=math.radians(7);rot=np.array([[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]])
        self.active_frame=(self.active_frame[0],self.active_frame[1]@rot)
        self.axial_part('Scroll_ClosedLeatherWrappedBody',[(-4.95,1.34),(-4.75,1.40),(4.75,1.40),(4.95,1.34)],INDIGO)
        for sign in (-1,1):
            self.axial_part('Scroll_HexagonalEndCap_'+str(sign),[(sign*4.70,1.43),(sign*5.18,1.60),(sign*5.82,1.60),(sign*6.00,1.39)],SILVER,6)
            self.axial_part('Scroll_InnerCapCollar_'+str(sign),[(sign*4.64,1.43),(sign*4.84,1.48)],BRASS)
            for x in (sign*5.25,sign*5.59):
                self.axial_part('Scroll_CapSeam_'+str(x),[(x-.025,1.615),(x+.025,1.615)],DARKSILVER,6)
        # Two closed leather keeper rings and tangible bridges into the belt.
        for x in (-3.15,3.15):
            self.prism('Scroll_KeeperBridge_'+str(x),rounded(1.10,5.5,.20)+[x,0],-.35,.43,INDIGO,.06)
            ring=[]
            for angle in np.linspace(0,TAU,112,endpoint=False):ring.append([x,1.75+1.46*math.cos(angle),-.10+1.46*math.sin(angle)])
            normals=[unit(np.array(p)-[x,1.75,-.10]) for p in ring]
            self.ribbon('Scroll_DoublePointKeeper_'+str(x),np.array(ring+[ring[0]]),np.array(normals+[normals[0]]),.77,INDIGO,.15)
            for z in (-2.25,2.25):self.fastener('Scroll_BridgeRivet_'+str((x,z)),x,.48,z,.13,BRASS)
            p=[[x-.25,1.75+1.48*math.cos(a),-.10+1.48*math.sin(a)] for a in np.linspace(0,TAU,130)]
            self.stitch('Scroll_KeeperSeam_'+str(x),p,[unit(np.array(v)-[x-.25,1.75,-.10]) for v in p],pitch=.26)
        # Closed rolled leather seam and a sparse constellation inlay on the tube.
        self.tube('Scroll_LeatherLongSeam',[[[x,3.155,-.10] for x in np.linspace(-4.6,4.6,100)]],.027,EDGE,7)
        paths=[]
        for phase in (0,math.pi):
            p=[]
            for x in np.linspace(-4.55,4.55,180):
                a=phase+x*.43;p.append([x,1.75+1.412*math.cos(a),-.10+1.412*math.sin(a)])
            paths.append(p)
        self.tube('Scroll_SubtleCrossingRuneInlay',paths,.010,BRASS,5)

    def sources(self):
        self.world();ref=self.cols['06_NATIVE_REFERENCES'];ref.hide_render=True
        self.mesh(self.body+'_ST6TrouserReference',self.pants_points,self.pants_faces,LINING,col=ref);ref.hide_viewport=True
        self.sockets=[]
        for name,arc in [('AstrolabeBuckle',0),('LeftRuneCase',-.23*self.perimeter),('RightScrollCanister',.27*self.perimeter),('RearBackpackClearance',self.perimeter/2)]:
            origin,basis=self.frame_at(arc,.65);ob=bpy.data.objects.new('ATTACH_'+name,None)
            self.cols['08_ATTACHMENT_ANCHORS'].objects.link(ob);ob.empty_display_type='ARROWS';ob.empty_display_size=.022;ob.location=bv(origin)
            self.sockets.append(dict(name=name,origin_cm=origin.tolist(),basis=basis.tolist(),native_weights=self.native_weights(origin)))
        self.cols['08_ATTACHMENT_ANCHORS'].hide_render=True

    def author(self):
        self.tailoring();self.buckle();self.side_plates();self.rune_case();self.scroll_canister()
        parts=list(self.objects);rig=self.native_rig();self.bind(parts,rig)
        print('ARCANE_DETAIL_ASSEMBLED',self.body,len(parts),flush=True)
        merged,stats=self.merge_for_export(parts,'SK_ArcaneConduitBelt_'+self.body,rig)
        self.fbx([merged],E/(merged.name+'.fbx'),rig);self.glb([merged],E/(merged.name+'.glb'),rig)
        self.neutral(merged,E/(self.body+'_NativeWeightedMesh.json'))
        if self.body=='Jason':
            display=merged.copy();display.data=merged.data.copy();display.modifiers.clear();display.parent=None
            self.scene.collection.objects.link(display);display.name='SM_ArcaneConduitBelt_Display'
            center=self.origin+self.up*self.point(0,.5,0)[2]
            for v in display.data.vertices:
                native=np.array([v.co.x*100,-v.co.y*100,v.co.z*100])-center
                v.co=Vector((float(native@self.right)*.01,-float(native@self.forward)*.01,float(native@self.up)*.01))
            display.vertex_groups.clear();self.fbx([display],E/(display.name+'.fbx'));self.glb([display],E/(display.name+'.glb'))
            bpy.data.objects.remove(display,do_unlink=True)
        bpy.data.objects.remove(merged,do_unlink=True);self.sources();rig.hide_set(True)
        for key in ('02_EXPORT_LOD1','03_EXPORT_LOD2','04_RIGID_ATTACHMENT_MASTERS','05_EXPORT_ASSEMBLY','07_HIGH_SURFACE_SOURCES'):
            self.cols[key].hide_render=True;self.cols[key].hide_viewport=True
        self.selection(parts)
        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type=='VIEW_3D':
                    area.spaces.active.shading.type='MATERIAL';area.spaces.active.region_3d.view_distance=.70
                    area.spaces.active.region_3d.view_location=bv(self.origin+self.up*self.point(0,.5,0)[2])
        self.scene.render.engine='CYCLES';self.scene.cycles.samples=64
        bpy.ops.file.pack_all();blend=E/f'ArcaneConduitBelt_{self.body}_Editable.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        report=dict(body=self.body,completed=True,blend=str(blend),fbx=str(E/('SK_ArcaneConduitBelt_'+self.body+'.fbx')),glb=str(E/('SK_ArcaneConduitBelt_'+self.body+'.glb')),geometry=stats,fit=self.fit_report,attachments=self.sockets,material_slots=[m.name for m in self.mats],rigid_parts_not_globally_scaled=True,decimated=False,game_integrated=False,runtime_tested=False,preview_rendered=False)
        write(R/'Authored'/f'{self.body}_production.json',report)
        print('ARCANE_DETAIL_SAVED',self.body,stats['triangles'],str(blend),flush=True)

if __name__=='__main__':
    chosen=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['Jason','Kaitlin']
    for row in read(R/'inputs.json')['records']:
        if row['body'] in chosen:ArcaneBelt(row).author()
