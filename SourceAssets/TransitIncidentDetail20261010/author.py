"""Detailed local-pivot replacements for the nine incident props. No scene render."""
from pathlib import Path
import bpy,bmesh,sys,math,json,hashlib,random
from mathutils import Vector,Euler
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1];OUT=ROOT/'Authored'
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonFacilityTransit20261007/Scripts'))
import geometry as g
sys.path.insert(0,str(PROJECT/'SourceAssets/ReceptionFinish20261010'))
from concrete_mesh import project_uv
BASE='/Game/Dungeons/TransitIncidentDetail20261010'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.unit_settings.system='METRIC'
bpy.context.scene.unit_settings.scale_length=1;g.ROOM='IncidentDetail';rng=random.Random(101017)
roles=('Yellow','Steel','Rubber','Cotton','Teal','Forms','Caution','Board','Paper')
materials={r:BASE+'/Materials/M_IncidentDetail_'+r for r in roles}

def rounded_box(k,c,s,mat='Yellow',bevel=.002):
    bm=bmesh.new();bmesh.ops.create_cube(bm,size=1)
    for v in bm.verts:v.co=Vector((v.co.x*s[0],v.co.y*s[1],v.co.z*s[2]))
    bmesh.ops.bevel(bm,geom=list(bm.edges),offset=min(bevel,min(s)*.24),segments=3,affect='EDGES')
    bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table();bm.normal_update()
    vs=[v.co+Vector(c) for v in bm.verts];fs=[tuple(v.index for v in f.verts) for f in bm.faces]
    smooth=[len(f.verts)==4 and f.calc_area()<min(s)*max(s)*.18 for f in bm.faces]
    g.poly(k,vs,fs,mat,smooth=smooth);bm.free()

def ringpts(w,d,r,z):
    pts=[]
    for x,y,a in ((w/2-r,d/2-r,0),(-w/2+r,d/2-r,90),(-w/2+r,-d/2+r,180),(w/2-r,-d/2+r,270)):
        for i in range(17):
            t=math.radians(a+i*90/16);pts.append((x+r*math.cos(t),y+r*math.sin(t),z))
    return pts

def shell(k,rings,mat='Yellow',capfirst=False,caplast=False):
    n=len(rings[0]);vs=[v for ring in rings for v in ring];fs=[];smooth=[]
    for j in range(len(rings)-1):
        fs.extend((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i) for i in range(n));smooth.extend([True]*n)
    if capfirst:fs.append(tuple(reversed(range(n))));smooth.append(False)
    if caplast:fs.append(tuple((len(rings)-1)*n+i for i in range(n)));smooth.append(False)
    g.poly(k,vs,fs,mat,smooth=smooth)

def face_label(k,vs,mat='Caution',uv=None):
    g.poly(k,vs,[(0,1,2,3)],mat,[uv or [(0,0),(1,0),(1,1),(0,1)]])

def screw(k,c,axis,r=.004):
    c=Vector(c);n,a,b=g.basis(axis)
    g.ring(k,c,n,r*1.4,r*.65,.0012,'Steel',24)
    g.lathe(k,c+n*.0006,n,[(0,r),(.001,r),(.002,r*.83)],'Steel',24)
    # Dark recessed cross remains geometry and does not depend on texture resolution.
    for direction in (a,b):g.beam(k,c+n*.0027-direction*r*.64,c+n*.0027+direction*r*.64,r*.26,.00025,'Rubber')

# Rounded injection-moulded shell with rolled lip, drainage fillets and strengthening ribs.
k='Bucket'
profiles=[(.392,.268,.040,.063),(.404,.278,.046,.075),(.414,.286,.047,.115),(.457,.322,.055,.330),
          (.471,.336,.059,.377),(.480,.345,.061,.390),(.480,.345,.061,.399),(.467,.331,.055,.404),
          (.452,.316,.050,.395),(.449,.313,.048,.379),(.435,.299,.043,.330),(.397,.270,.035,.115),
          (.386,.258,.035,.077),(.371,.242,.035,.073)]
shell(k,[ringpts(*p) for p in profiles],capfirst=True,caplast=True)
for z,w,d in ((.085,.408,.283),(.355,.469,.334)):
    pts=ringpts(w,d,.052,z);g.tube(k,pts+[pts[0]],.0038,'Yellow',10)
for sign in (-1,1):
    for x in (-.16,-.105,.105,.16):
        g.tube(k,[(x,sign*.141,.115),(x,sign*.15,.22),(x,sign*.16,.325)],.0025,'Yellow',8)
    # Parting line and reinforced bail pivots.
    g.tube(k,[(sign*.206,0,.09),(sign*.218,0,.22),(sign*.234,0,.374)],.0006,'Yellow',6)
    g.lathe(k,(sign*.23,0,.313),(sign,0,0),[(0,.021),(.006,.021),(.010,.015)],'Yellow',40)
    screw(k,(sign*.241,0,.313),(sign,0,0),.007)
# Swivel caster forks, profiled tyres, hub caps and axle bolts; all joints overlap structurally.
for x in (-.166,.166):
    for y in (-.096,.096):
        g.lathe(k,(x,y,.059),(0,0,1),[(0,.020),(.009,.020),(.013,.014)],'Steel',32)
        for sign in (-1,1):rounded_box(k,(x,y+sign*.022,.043),(.035,.006,.032),'Steel',.002)
        g.lathe(k,(x,y,.029),(0,1,0),[(-.021,.022),(-.018,.028),(-.012,.030),(.012,.030),(.018,.028),(.021,.022)],'Rubber',48)
        for dy in (-.020,.020):
            g.lathe(k,(x,y+dy,.029),(0,1 if dy>0 else -1,0),[(0,.018),(.003,.018),(.004,.008)],'Steel',32)
            screw(k,(x,y+dy*1.21,.029),(0,1 if dy>0 else -1,0),.004)
        for dy in (-.008,0,.008):g.torus(k,(x,y+dy,.029),(0,1,0),.0295,.0006,'Rubber',40,6)
# Wringer basket: vented side walls, reinforcing rails and actual slotted press plate.
for x in (-.204,.204):
    for z in (.390,.473):rounded_box(k,(x,.084,z),(.018,.17,.018),'Yellow',.003)
    for y in (.009,.038,.068,.10,.13,.158):rounded_box(k,(x,y,.432),(.015,.014,.085),'Yellow',.002)
for y in (.009,.157):
    for z in (.390,.477):rounded_box(k,(0,y,z),(.420,.016,.017),'Yellow',.003)
    for x in [i*.032 for i in range(-6,7)]:rounded_box(k,(x,y,.431),(.012,.014,.081),'Yellow',.002)
for x in [i*.026 for i in range(-7,8)]:rounded_box(k,(x,.08,.389),(.012,.143,.012),'Yellow',.0015)
for x in (-.181,.181):
    g.cylinder(k,(x,.05,.417),(x,.07,.538),.008,'Steel',24)
    g.cylinder(k,(x,.010,.474),(x,.065,.538),.005,'Steel',20)
    screw(k,(x,.051,.415),(1,0,0),.006)
g.cylinder(k,(-.181,.07,.538),(.181,.07,.538),.008,'Steel',32)
g.lathe(k,(-.087,.07,.538),(1,0,0),[(0,.012),(.005,.016),(.169,.016),(.174,.012)],'Rubber',32)
for xx in [i*.007 for i in range(-10,11)]:g.torus(k,(xx,.07,.538),(1,0,0),.016,.0006,'Rubber',32,6)
# Bail with rolled grip; rounded joints eliminate the previous hard polyline bends.
path=[(-.242,0,.313),(-.245,-.05,.31),(-.248,-.17,.298),(-.228,-.23,.281),(-.20,-.252,.27),(.20,-.252,.27),(.228,-.23,.281),(.248,-.17,.298),(.245,-.05,.31),(.242,0,.313)]
g.tube(k,path,.0048,'Steel',16)
g.lathe(k,(-.068,-.252,.27),(1,0,0),[(0,.007),(.007,.012),(.129,.012),(.136,.007)],'Rubber',32)
# Label follows the front shell taper rather than hovering over the bucket.
face_label(k,[(-.049,-.1496,.185),(.049,-.1496,.185),(.049,-.1620,.337),(-.049,-.1620,.337)])
# Localised plastic abrasions on foot/rim: small chips remain plastic, never rusty metal.
for i in range(15):
    x=rng.uniform(-.17,.17);z=rng.uniform(.093,.12)
    g.tube(k,[(x,-.144,z),(x+rng.uniform(.008,.023),-.145,z+.003)],.00045,'Yellow',6)

# Drape-shaped cotton yarn: two plies per tuft, wet flattened tails and a few frayed ends.
k='Mop';head=Vector((-.62,0,.035));end=Vector((.82,.17,.018));axis=(end-head).normalized()
g.cylinder(k,head+axis*.040,end-axis*.025,.0104,'Steel',32)
g.lathe(k,end-axis*.20,axis,[(0,.011),(.010,.016),(.170,.016),(.19,.011)],'Teal',40)
g.lathe(k,end-axis*.020,axis,[(0,.016),(.012,.017),(.028,.012)],'Rubber',36)
for t in [i*.010 for i in range(15)]:g.torus(k,end-axis*(.035+t),axis,.016,.0006,'Rubber',28,6)
g.lathe(k,head-axis*.020,axis,[(0,.020),(.015,.026),(.039,.027),(.055,.020),(.073,.014),(.090,.011)],'Teal',48)
for t in (0.012,.028,.044):g.torus(k,head+axis*t,axis,.0265,.0012,'Rubber',40,8)
screw(k,head+axis*.030+Vector((0,0,.026)),(0,0,1),.004)
for j in range(38):
    angle=rng.uniform(-math.pi,math.pi);reach=rng.uniform(.13,.264)
    a=head+Vector((rng.uniform(-.017,.017),rng.uniform(-.031,.031),rng.uniform(-.007,.008)))
    b=Vector((head.x-.055-math.cos(angle)*reach,head.y+math.sin(angle)*reach*.62,.007))
    c=a.lerp(b,.50)+Vector((-.024,rng.uniform(-.015,.015),-.009))
    for ply in range(2):
        pts=[]
        for i in range(25):
            t=i/24;p=(1-t)**2*a+2*t*(1-t)*c+t*t*b
            wave=t*math.tau*5+ply*math.pi+j;rad=.0018*(1-.5*t)
            p.y+=math.cos(wave)*rad;p.z=max(.0045,p.z+math.sin(wave)*rad)
            pts.append(p)
        g.tube(k,pts,.00175,'Cotton',8)
    if j%2==0:
        for f in range(3):
            a2=b+Vector((0,0,.001));e=b+Vector((rng.uniform(-.024,.016),rng.uniform(-.019,.02),-.001))
            g.tube(k,[a2,a2.lerp(e,.5)+Vector((0,0,.002)),e],.00038,'Cotton',5)

# Moulded warning stand with rounded perimeter returns, rear ribs and a pin hinge.
k='WarningSign'
for side in (-1,1):
    y=side*.014
    rounded_box(k,(0,y,.276),(.288,.010,.434),'Yellow',.002)
    for x in (-.140,.140):
        rounded_box(k,(x,y,.31),(.024,.018,.551),'Yellow',.0025)
        rounded_box(k,(x,y,.029),(.031,.030,.058),'Rubber',.003)
    rounded_box(k,(0,y,.590),(.297,.017,.027),'Yellow',.003)
    rounded_box(k,(0,y,.523),(.27,.017,.027),'Yellow',.003)
    for x in (-.099,.099):rounded_box(k,(x,-side*.003,.283),(.008,.011,.38),'Yellow',.0015)
    for z in (.09,.21,.36,.474):rounded_box(k,(0,-side*.003,z),(.246,.011,.008),'Yellow',.0015)
for x in (-.13,-.075,0,.075,.13):g.cylinder(k,(x-.019,0,.58),(x+.019,0,.58),.012,'Yellow',32)
g.cylinder(k,(-.155,0,.58),(.155,0,.58),.0048,'Steel',32)
for x in (-.156,.156):screw(k,(x,0,.58),(1 if x>0 else -1,0,0),.006)
face_label(k,[(-.115,-.0197,.091),(.115,-.0197,.091),(.115,-.0197,.47),(-.115,-.0197,.47)])

# Four different deformations: edge curl, folded corner, crossed crease, crushed wrinkles.
for idx in range(4):
    k='Paper'+str(idx);nx,ny=16,22;vs=[];fs=[];uv=[]
    for j in range(ny+1):
        v=j/ny
        for i in range(nx+1):
            u=i/nx;x=(u-.5)*.21;y=(v-.5)*.297
            if i in (0,nx):x+=(-1 if i==nx else 1)*(.0002+.0007*math.sin(j*2.79+idx)**8)
            if j in (0,ny):y+=(-1 if j==ny else 1)*.0005*math.sin(i*2.4+idx)**6
            if idx==0:z=.0012+.015*max(0,(u-.70)/.30)**2+.0015*math.sin(v*math.pi)
            elif idx==1:
                z=.0012+.002*math.sin(u*math.pi)
                d=max(0,(x+y-.118)/math.sqrt(2));a=math.radians(116)
                x+=(math.cos(a)-1)*d/math.sqrt(2);y+=(math.cos(a)-1)*d/math.sqrt(2);z+=math.sin(a)*d
            elif idx==2:z=.0012+.012*(1-abs(2*u-1))+.005*(1-abs(2*v-1))
            else:z=.0012+.024*math.sin(u*math.pi)*math.sin(v*math.pi)+.016*math.sin(u*4*math.pi+v*2)**2*math.sin(v*math.pi)
            vs.append((x,y,z))
    for j in range(ny):
        for i in range(nx):
            ids=(j*(nx+1)+i,j*(nx+1)+i+1,(j+1)*(nx+1)+i+1,(j+1)*(nx+1)+i);fs.append(ids)
            uv.append([((idx%2+q%(nx+1)/nx)*.5,(1-idx//2+q//(nx+1)/ny)*.5) for q in ids])
    g.poly(k,vs,fs,'Forms',uv,smooth=idx!=2)

# Folder has physical covers/spine, a worn tab, shuffled sheets and a folded metal fastener.
k='Folder'
rounded_box(k,(0,0,.002),(.251,.333,.0012),'Board',.0003)
rounded_box(k,(.09,.170,.002),(.07,.025,.0012),'Board',.0003)
vs=[];fs=[]
for j in range(11):
    y=-.166+j*.332/10
    for i in range(13):
        t=i/12;x=-.124-t*.23;z=.003+.012*t*t+.007*t*math.sin((y+.166)/.332*math.pi)
        vs.append((x,y,z))
for j in range(10):
    for i in range(12):a=j*13+i;fs.append((a,a+13,a+14,a+1))
g.poly(k,vs,fs,'Board',smooth=True)
for j in range(7):
    z=.0033+j*.00055;rounded_box(k,(j*.0012-.004,j*.0011,z),(.207,.293,.00045),'Paper',.00010)
face_label(k,[(-.103,-.145,.0071),(.105,-.145,.0071),(.105,.148,.0071),(-.103,.148,.0071)],'Forms',[(.5,.5),(1,.5),(1,1),(.5,1)])
for x in (-.078,.078):g.ring(k,(x,.126,.008),(0,0,1),.0042,.0026,.0010,'Steel',28)
rounded_box(k,(0,.126,.0088),(.164,.009,.0008),'Steel',.0002)
for x in (-.074,.074):rounded_box(k,(x,.110,.0097),(.005,.033,.001),'Steel',.0002)
g.tube(k,[(.072,.134,.009),(.092,.134,.009),(.092,.164,.009),(.082,.171,.009),(.074,.164,.009),(.074,.142,.009)],.0007,'Steel',10)

# Open expanded-metal wastebasket, dented locally; folded rims, rolled base and seam.
k='WasteBasket'
def basketpt(a,z):
    r=.118+(.155-.118)*z/.30
    dent=.011*math.exp(-((math.atan2(math.sin(a-.5),math.cos(a-.5)))/.32)**2)*(z/.30)**3
    return Vector(((r-dent)*math.cos(a),(r-dent)*math.sin(a),z))
g.lathe(k,(0,0,0),(0,0,1),[(.002,.11),(.005,.120),(.014,.123),(.020,.119)],'Steel',64)
for z,r in ((.018,.120),(.30,.155)):
    pts=[basketpt(math.tau*i/120,z) for i in range(121)];g.tube(k,pts,.004,'Steel',10)
for i in range(36):
    a=math.tau*i/36
    for sign in (-1,1):
        pts=[basketpt(a+sign*j*math.tau/72,.020+j*.028) for j in range(11)]
        g.tube(k,pts,.0011,'Steel',6)
g.tube(k,[basketpt(0,z) for z in (.020,.09,.18,.30)],.0020,'Steel',10)
for z in (.045,.12,.23,.285):
    p=basketpt(0,z);screw(k,p,(1,0,0),.002)

records=[]
for (_,kind),data in g.G.items():
    me=bpy.data.meshes.new(kind);me.from_pydata(data['v'],[],data['f']);me.update()
    used=list(dict.fromkeys(data['m']))
    for role in used:me.materials.append(bpy.data.materials.get('ID2_'+role) or bpy.data.materials.new('ID2_'+role))
    for face,role,smooth in zip(me.polygons,data['m'],data['smooth']):face.material_index=used.index(role);face.use_smooth=smooth
    project_uv(me)
    for f,coords in zip(me.polygons,data['uv']):
        if coords:
            for li,value in zip(f.loop_indices,coords):me.uv_layers.active.data[li].uv=value
    # Authored wear channels: dirt R, softened/contact edges G, damp cotton B.
    # Calculated in the upright maker coordinates, then kept when the prop is laid down.
    colors=me.color_attributes.new(name='Wear',type='BYTE_COLOR',domain='CORNER')
    for f in me.polygons:
        role=used[f.material_index]
        for li in f.loop_indices:
            p=me.vertices[me.loops[li].vertex_index].co
            mott=.5+.5*math.sin(p.x*71+math.sin(p.z*19))*math.sin(p.y*53+p.z*27)
            grime=.05+.14*mott;wear=.10+.13*mott;wet=0.
            if kind=='Bucket':
                grime+=.43*max(0,1-p.z/.16)+.14*math.exp(-((p.z-.37)/.025)**2)
                wear+=.38*math.exp(-((p.z-.394)/.018)**2)
            if kind=='Mop' and role=='Cotton':grime=.22+.30*mott;wet=.3+.45*max(0,1-p.z/.028)
            if kind=='WarningSign':grime+=.33*max(0,1-p.z/.13);wear+=.34*max(0,(abs(p.x)-.125)/.025)
            if kind=='WasteBasket':grime+=.30*max(0,1-p.z/.075)
            colors.data[li].color=(min(.85,grime),min(.75,wear),min(.8,wet),1)
    obj=bpy.data.objects.new('SM_IncidentDetail_'+kind,me);bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    if kind.startswith('Paper'):
        so=obj.modifiers.new('Paper edge thickness','SOLIDIFY');so.thickness=.00014;so.offset=-1;bpy.ops.object.modifier_apply(modifier=so.name)
    if kind in ('Bucket','WarningSign','WasteBasket'):
        matrix=Euler((math.radians(-92 if kind=='Bucket' else -90),0,0)).to_matrix()
        for p in me.vertices:p.co=matrix@p.co
    floor=min(v.co.z for v in me.vertices)
    for p in me.vertices:p.co.z+=.001-floor
    tri=obj.modifiers.new('Final triangles','TRIANGULATE');tri.quad_method='BEAUTY';bpy.ops.object.modifier_apply(modifier=tri.name)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
    me.set_sharp_from_angle(angle=math.radians(55))
    for f in me.polygons:
        uv=[me.uv_layers.active.data[li].uv.copy() for li in f.loop_indices]
        if abs((uv[1].x-uv[0].x)*(uv[2].y-uv[0].y)-(uv[1].y-uv[0].y)*(uv[2].x-uv[0].x))<1e-12:
            axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(f.normal[a]))]
            for li in f.loop_indices:
                p=me.vertices[me.loops[li].vertex_index].co;me.uv_layers.active.data[li].uv=(p[axes[0]],p[axes[1]])
    path=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,colors_type='LINEAR',add_leaf_bones=False,path_mode='STRIP')
    records.append(dict(name=obj.name,kind=kind,mesh=BASE+'/Meshes/'+obj.name,fbx=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        materials={'ID2_'+r:materials[r] for r in used},collision=False,cast_shadow=True,nanite=False,triangles=len(me.polygons),
        bounds_blender_m=[[min(v.co[a] for v in me.vertices) for a in range(3)],[max(v.co[a] for v in me.vertices) for a in range(3)]]))
sys.path.insert(0,str(ROOT))
from blender_materials import attach
attach(ROOT)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TransitIncidentDetail.blend'))
(ROOT/'geometry.json').write_text(json.dumps(dict(meshes=records,wear_channels=['dirt','edge wear','wet cotton']),indent=2),encoding='utf8')
print('INCIDENT_DETAIL_AUTHORED',len(records),sum(r['triangles'] for r in records),'triangles')
