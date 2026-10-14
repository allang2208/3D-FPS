"""Editable, physically grounded janitorial and administrative incident props."""
from pathlib import Path
import bpy,bmesh,math,sys,json,hashlib,random
from mathutils import Vector,Matrix,Euler
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parents[1];OUT=ROOT/'Authored'
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonFacilityTransit20261007/Scripts'))
import geometry as g
sys.path.insert(0,str(PROJECT/'SourceAssets/ReceptionFinish20261010'))
from concrete_mesh import project_uv
BASE='/Game/Dungeons/TransitIncidentDressing20261010'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
g.ROOM='Incident';rng=random.Random(101010)
materials=dict(Yellow=BASE+'/Materials/M_Incident_YellowPlastic',
    Paper='/Game/Dungeons/ReceptionHall20261006/Refine20261007/Materials/M_RH2_Paper',
    Forms=BASE+'/Materials/M_Incident_Forms',Caution=BASE+'/Materials/M_Incident_Caution',
    Board=BASE+'/Materials/M_Incident_Fiberboard',
    Fabric=BASE+'/Materials/M_Incident_Cotton',
    Steel='/Game/Dungeons/FacilityTransit20261007/RefineV2/Materials/M_FT2_Brushed',
    Rubber='/Game/Dungeons/FacilityTransit20261007/RefineV2/Materials/M_FT2_Gasket',
    Teal='/Game/Dungeons/ReceptionHall20261006/Materials/M_Reception_Teal')

def rounded_ring(w,d,r,z):
    pts=[]
    for cx,cy,a in ((w/2-r,d/2-r,0),(-w/2+r,d/2-r,90),(-w/2+r,-d/2+r,180),(w/2-r,-d/2+r,270)):
        for i in range(13):
            t=math.radians(a+i*90/12);pts.append((cx+r*math.cos(t),cy+r*math.sin(t),z))
    return pts

def shell(kind,rings,mat,cap_first=False,cap_last=False):
    n=len(rings[0]);vs=[p for ring in rings for p in ring];fs=[]
    for k in range(len(rings)-1):
        fs.extend((k*n+i,k*n+(i+1)%n,(k+1)*n+(i+1)%n,(k+1)*n+i) for i in range(n))
    if cap_first:fs.append(tuple(reversed(range(n))))
    if cap_last:fs.append(tuple((len(rings)-1)*n+i for i in range(n)))
    g.poly(kind,vs,fs,mat,smooth=True)

def label(kind,c,w,h,role='Caution'):
    x,y,z=c
    g.poly(kind,[(x-w/2,y,z-h/2),(x+w/2,y,z-h/2),(x+w/2,y,z+h/2),(x-w/2,y,z+h/2)],[(0,1,2,3)],role,[[(0,0),(1,0),(1,1),(0,1)]])

# 20 litre wheeled mop bucket: open double shell, rolled rim, wringer and folded bail.
k='Bucket'
shell(k,[rounded_ring(.40,.275,.043,.058),rounded_ring(.47,.335,.055,.385),
    rounded_ring(.475,.34,.058,.398),rounded_ring(.458,.323,.050,.400),
    rounded_ring(.450,.315,.047,.382),rounded_ring(.389,.264,.038,.070)],'Yellow',True,True)
for z,w,d in ((.090,.406,.280),(.345,.461,.326)):
    ring=rounded_ring(w,d,.05,z);g.tube(k,ring+[ring[0]],.004,'Yellow',8)
for x in (-.17,.17):
    for y in (-.097,.097):
        g.box(k,(x,y,.052),(.065,.042,.027),'Rubber')
        g.cylinder(k,(x,y-.023,.029),(x,y+.023,.029),.028,'Rubber',24)
        g.cylinder(k,(x,y-.026,.029),(x,y+.026,.029),.007,'Steel',12)
# Rear half wringer: open slats rather than an opaque block.
for x in (-.205,.205):g.box(k,(x,.085,.433),(.013,.156,.100),'Yellow')
for y in (.011,.156):g.box(k,(0,y,.433),(.410,.014,.100),'Yellow')
for x in [i*.027 for i in range(-7,8)]:g.box(k,(x,.081,.388),(.012,.13,.014),'Yellow')
for x in (-.19,.19):g.cylinder(k,(x,.07,.403),(x,.07,.55),.009,'Steel',16)
g.cylinder(k,(-.19,.07,.55),(.19,.07,.55),.009,'Steel',20)
g.cylinder(k,(-.09,.07,.55),(.09,.07,.55),.017,'Rubber',24)
for x in (-.233,.233):g.cylinder(k,(x,0,.31),(x+(.009 if x>0 else -.009),0,.31),.018,'Rubber',24)
g.tube(k,[(-.241,0,.31),(-.253,-.19,.30),(-.20,-.255,.27),(.20,-.255,.27),(.253,-.19,.30),(.241,0,.31)],.005,'Steel',16)
g.cylinder(k,(-.065,-.255,.27),(.065,-.255,.27),.011,'Rubber',20)
label(k,(0,-.163,.250),.107,.170)

# Mop is already a settled pose; shaft slopes onto the floor away from cotton head.
k='Mop';head=Vector((-.62,0,.036));end=Vector((.82,.17,.017));axis=(end-head).normalized()
g.cylinder(k,head,end,.0105,'Steel',24)
g.cylinder(k,end-axis*.19,end,.016,'Teal',28)
g.cylinder(k,end-axis*.025,end+axis*.008,.018,'Rubber',28)
g.cylinder(k,head-axis*.032,head+axis*.09,.026,'Teal',32)
for j in range(46):
    a=rng.uniform(-math.pi,math.pi);reach=rng.uniform(.10,.265)
    start=head+Vector((rng.uniform(-.016,.016),rng.uniform(-.035,.035),rng.uniform(-.011,.012)))
    tail=Vector((head.x-math.cos(a)*reach-.060,head.y+math.sin(a)*reach*.62,.007+rng.random()*.004))
    mid=(start+tail)*.5;mid.z=.010+rng.random()*.023
    g.tube(k,[start,start.lerp(mid,.55),mid,mid.lerp(tail,.6),tail],rng.uniform(.0027,.0045),'Fabric',8)

# Folded floor warning sign, with real grip opening and inset print.
k='WarningSign'
for y in (-.014,.014):
    g.box(k,(0,y,.27),(.29,.009,.43),'Yellow')
    for x in (-.142,.142):g.box(k,(x,y,.535),(.035,.012,.12),'Yellow')
    g.box(k,(0,y,.589),(.30,.012,.021),'Yellow')
    for x in (-.135,.135):g.box(k,(x,y,.029),(.034,.030,.058),'Rubber')
g.cylinder(k,(-.152,0,.58),(.152,0,.58),.009,'Steel',24)
label(k,(0,-.019,.285),.239,.387)

# Bent A4 sheets retain continuous paper UVs across curls and folds.
for idx in range(4):
    k='Paper'+str(idx);vs=[];fs=[];uvs=[];nx,ny=8,12
    for j in range(ny+1):
        v=j/ny
        for i in range(nx+1):
            u=i/nx;x=(u-.5)*.21;y=(v-.5)*.297
            if idx==0:z=.0015+.010*max(0,(u-.67)/.33)**2+.003*math.sin(v*math.pi)
            elif idx==1:z=.0015+.025*max(0,(v-.74)/.26)**1.5+.004*math.sin(u*math.pi)
            elif idx==2:z=.0015+.013*(1-abs(2*u-1))+.003*math.sin(v*2*math.pi)**2
            else:z=.0015+.035*math.sin(u*math.pi)*math.sin(v*math.pi)+.012*math.sin(u*5*math.pi)**2*math.sin(v*math.pi)
            vs.append((x,y,z))
    for j in range(ny):
        for i in range(nx):
            ids=(j*(nx+1)+i,j*(nx+1)+i+1,(j+1)*(nx+1)+i+1,(j+1)*(nx+1)+i)
            fs.append(ids)
            uvs.append([((idx%2+(q%(nx+1))/nx)*.5,(1-idx//2+(q//(nx+1))/ny)*.5) for q in ids])
    g.poly(k,vs,fs,'Forms',uvs,smooth=idx!=2)

# Splayed manila folder left open; includes thickness, scored spine, paper stack and clip.
k='Folder'
g.box(k,(0,0,.002),(.25,.33,.003),'Board')
g.poly(k,[(-.125,-.165,.004),(-.125,.165,.004),(-.345,.165,.010),(-.351,-.165,.024)],[(0,1,2,3)],'Board')
g.box(k,(.090,.170,.004),(.068,.025,.003),'Board')
for j in range(4):g.box(k,(j*.002,0,.005+j*.0009),(.208,.294,.00065),'Paper')
g.poly(k,[(-.104,-.147,.009),(.104,-.147,.009),(.104,.147,.009),(-.104,.147,.009)],[(0,1,2,3)],'Forms',[[(0,0.5),(.5,.5),(.5,1),(0,1)]])
g.tube(k,[(.075,.129,.010),(.089,.129,.010),(.089,.157,.010),(.082,.165,.010),(.076,.158,.010),(.076,.136,.010)],.00065,'Steel',8)

# Tipped, open wire wastepaper basket; a visible source for part of the paper spill.
k='WasteBasket'
g.lathe(k,(0,0,0),(0,0,1),[(.005,.118),(.016,.123)],'Rubber',48)
for z,r in ((.035,.12),(.17,.137),(.30,.155)):
    g.torus(k,(0,0,z),(0,0,1),r,.0035,'Steel',48,8)
for i in range(40):
    a=math.tau*i/40
    g.tube(k,[(r*math.cos(a),r*math.sin(a),z) for z,r in ((.015,.118),(.17,.137),(.30,.155))],.0015,'Steel',6)

records=[]
for (_,kind),data in g.G.items():
    me=bpy.data.meshes.new(kind);me.from_pydata(data['v'],[],data['f']);me.update()
    roles=list(dict.fromkeys(data['m']))
    for role in roles:me.materials.append(bpy.data.materials.get('INC_'+role) or bpy.data.materials.new('INC_'+role))
    for face,role,smooth in zip(me.polygons,data['m'],data['smooth']):face.material_index=roles.index(role);face.use_smooth=smooth
    project_uv(me)
    for face,coords in zip(me.polygons,data['uv']):
        if coords:
            for li,uv in zip(face.loop_indices,coords):me.uv_layers.active.data[li].uv=uv
    obj=bpy.data.objects.new('SM_Incident_'+kind,me);bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    if kind.startswith('Paper'):
        # Shell thickness prevents back-face disappearances at raised paper corners.
        so=obj.modifiers.new('Paper thickness','SOLIDIFY');so.thickness=.00025;so.offset=-1
        bpy.ops.object.modifier_apply(modifier=so.name)
    if kind in ('Bucket','WarningSign','WasteBasket'):
        rotation=Euler((math.radians(-92 if kind=='Bucket' else -90),0,0)).to_matrix()
        for vert in me.vertices:vert.co=rotation@vert.co
    if not kind.startswith('Paper'):
        floor=min(v.co.z for v in me.vertices)
        for v in me.vertices:v.co.z-=floor-.001
    # Flat support contact is baked into each individual prop's local pivot.
    tri=obj.modifiers.new('Triangulation','TRIANGULATE');tri.quad_method='BEAUTY';tri.ngon_method='BEAUTY';bpy.ops.object.modifier_apply(modifier=tri.name)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();me.update()
    # Solidify inherits identical rim UVs from both sides. Give those narrow edge
    # triangles a real area in UV space while retaining the printed faces.
    for face in me.polygons:
        luv=[me.uv_layers.active.data[li].uv.copy() for li in face.loop_indices]
        if len(luv)==3 and abs((luv[1].x-luv[0].x)*(luv[2].y-luv[0].y)-(luv[1].y-luv[0].y)*(luv[2].x-luv[0].x))<1e-12:
            axes=[a for a in range(3) if a!=max(range(3),key=lambda a:abs(face.normal[a]))]
            for li in face.loop_indices:
                p=me.vertices[me.loops[li].vertex_index].co;me.uv_layers.active.data[li].uv=(p[axes[0]],p[axes[1]])
    path=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False,path_mode='STRIP')
    records.append(dict(name=obj.name,kind=kind,mesh=BASE+'/Meshes/'+obj.name,fbx=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        materials={'INC_'+r:materials[r] for r in roles},collision=False,cast_shadow=True,nanite=False,triangles=len(me.polygons),
        bounds_blender_m=[[min(v.co[i] for v in me.vertices) for i in range(3)],[max(v.co[i] for v in me.vertices) for i in range(3)]]))
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'TransitIncidentProps.blend'))
(ROOT/'geometry.json').write_text(json.dumps(dict(meshes=records),indent=2),encoding='utf8')
print('TRANSIT_INCIDENT_AUTHORED',len(records),'reusable prop meshes')
