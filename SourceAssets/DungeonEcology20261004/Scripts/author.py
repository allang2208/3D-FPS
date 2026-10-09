"""Full-scale ecology architecture and horticulture kit. Blender background production.
Metres, individual room origins, explicit interfaces; no preview/test rendering.
"""
from pathlib import Path
import random,os
SCRIPT=Path(__file__).resolve().parent;PROJECT=SCRIPT.parents[2]
geometry=(PROJECT/'SourceAssets/DungeonAnatomyTheatre20261001/Scripts/geometry.py').read_text('utf8')
# A full-height opening through a low parapet has no lintel above its top.
geometry=geometry.replace('if b-a<.001:return','if b-a<.001 or z1-z0<.001:return')
exec(compile(geometry,'shared_geometry','exec'))
detail.setup(globals());OUT.mkdir(parents=True,exist_ok=True)
ATLAS=json.loads((OUT/'atlas.json').read_text('utf8'));BASE=CFG['ue_base'];records=[]
OLD=json.loads((ROOT/'Revisions/v6/Authored/manifest.json').read_text('utf8'))['objects']
REUSED={i['name']:i for i in OLD}
MESHBASE=CFG.get('mesh_base',BASE)
OUT=ROOT/'Authored/RefineV7';OUT.mkdir(parents=True,exist_ok=True)
ONLY=set(filter(None,os.environ.get('ECOLOGY_EXPORT_ONLY','').split(',')))
for k in ('Labels','Soil','Bark','Algae','Water','Glass','Diffuser','Ceramic','Paper','DarkPlastic'):
    MAPPING[k]=BASE+'/Materials/M_Eco_'+k;MATS[k]=bpy.data.materials.new('RS_'+k)
for k in ('JarGlass','JarGel','Leaf'):
    MAPPING[k]=BASE+'/RefineV3/Materials/M_Eco_'+k;MATS[k]=bpy.data.materials.new('RS_'+k)
RNG=random.Random(1042026)
RAIL_HULLS=[]
for room in CFG['rooms']:
    room['plants']=[p for p in room['plants'] if not p.get('authored_crown')]
    if room['id']=='EcoNursery':
        for p in room['plants']:p['position'][2]=1.025
    if room['id']=='EcoBiosphere':
        for p in room['containers']:
            if p['container_id'] in ('EcoBiosphere.Sample0','EcoBiosphere.Tote0'):p['position_m'][2]=.07
        for p in room['container_groups']:
            if p['id'] in ('Sample0','Tote0'):p['position_m'][2]=.07

def sign(c,w,key,n=(0,-1,0),kind='Signs'):
    c=Vector(c);n=Vector(n).normalized();u=Vector((0,0,1)).cross(n).normalized();v=Vector((0,0,1));h=w/4
    beam(kind,c-n*.018,c-n*.003,w+.025,h+.025,'PaintedSteel')
    x0,y0,x1,y1=ATLAS['rects'][key];aw,ah=ATLAS['size']
    uv=[(x0/aw,1-y1/ah),(x1/aw,1-y1/ah),(x1/aw,1-y0/ah),(x0/aw,1-y0/ah)]
    poly(kind,[c-u*w/2-v*h/2,c+u*w/2-v*h/2,c+u*w/2+v*h/2,c-u*w/2+v*h/2],[(0,1,2,3)],'Labels',[uv])
    for s in (-1,1):detail.fastener(c+u*s*(w/2-.035),n,.007,kind)

def cylinder(kind,c,r,h,mat='BareSteel',sides=40):
    detail.tube(kind,[(c[0],c[1],c[2]-h/2),(c[0],c[1],c[2]+h/2)],r,mat,sides)

def tank(kind,x,y):
    box(kind,(x,y,.15),(2.15,2.15,.3),'Concrete')
    for dx in (-.65,.65):
        for dy in (-.65,.65):
            box(kind,(x+dx,y+dy,.4),(.14,.14,.5),'PaintedSteel')
            box(kind,(x+dx,y+dy,.33),(.22,.22,.025),'BareSteel')
            detail.fastener((x+dx,y+dy,.35),(0,0,1),.017,kind)
    cylinder(kind,(x,y,1.85),.85,2.8,'PipeEnamel',72)
    for z in (.48,1.1,2.6,3.24):detail.torus((x,y,z),(0,0,1),.852,.018,kind,'BareSteel',64)
    cylinder(kind,(x,y,3.28),.86,.09,'BareSteel',64);cylinder(kind,(x,y,3.37),.24,.09,'PaintedSteel')
    for i in range(10):
        a=i*math.tau/10;detail.fastener((x+math.cos(a)*.73,y+math.sin(a)*.73,3.34),(0,0,1),.014,kind)
    detail.tube(kind,[(x-.36,y-.865,.7),(x-.36,y-.865,2.8)],.026,'Ceramic')
    for z in (.7,1.1,1.5,1.9,2.3,2.7):box(kind,(x-.3,y-.887,z),(.08,.006,.014),'Rubber')
    sign((x+.12,y-.863,1.9),.78,'Supply',kind=kind)

def valve(c,axis,kind='Services'):
    c=Vector(c);n=Vector(axis).normalized();a=Vector((0,0,1)).cross(n)
    if a.length<.01:a=Vector((1,0,0))
    a.normalize();b=n.cross(a)
    detail.torus(c,n,.16,.014,kind,'Yellow',36)
    for i in range(4):
        ang=i*math.pi/2;detail.tube(kind,[c,c+(a*math.cos(ang)+b*math.sin(ang))*.16],.010,'BareSteel',12)
    detail.tube(kind,[c-n*.16,c+n*.02],.023,'BareSteel',18)

def pump(kind,x,y):
    box(kind,(x,y,.16),(1.65,.95,.32),'Concrete')
    box(kind,(x,y,.35),(1.46,.7,.06),'BareSteel')
    for dx in (-.62,.62):
        for dy in (-.26,.26):detail.fastener((x+dx,y+dy,.39),(0,0,1),.023,kind)
    detail.tube(kind,[(x-.57,y,.64),(x+.12,y,.64)],.22,'PaintedSteel',48)
    for j in range(20):
        a=j*math.tau/20
        beam(kind,(x-.55,y+math.cos(a)*.24,.64+math.sin(a)*.24),(x+.1,y+math.cos(a)*.24,.64+math.sin(a)*.24),.016,.05,'BareSteel')
    detail.tube(kind,[(x+.19,y,.64),(x+.51,y,.64)],.32,'PipeEnamel',48)
    detail.ring((x+.49,y,.64),(1,0,0),.35,.08,.04,'BareSteel',48,kind)
    detail.tube(kind,[(x+.52,y,.64),(x+.85,y,.64)],.09,'PipeEnamel',24)
    sign((x-.2,y-.365,.50),.48,'Pump',kind=kind)

def rail(a,b,kind='Rails',height=1.1):
    a,b=Vector(a),Vector(b);count=max(1,math.ceil((b-a).length/1.35))
    along=b-a;side=Vector((-along.y,along.x,0)).normalized()*.045
    RAIL_HULLS.append([tuple(p+side*s+Vector((0,0,z))) for p in (a,b) for s,z in ((-1,0),(1,0),(1,height),(-1,height))])
    for z in (.51,height):detail.tube(kind,[a+Vector((0,0,z)),b+Vector((0,0,z))],.032,'PaintedSteel',18)
    beam(kind,a+Vector((0,0,.075)),b+Vector((0,0,.075)),.03,.15,'BareSteel')
    for i in range(count+1):
        p=a+(b-a)*i/count;detail.tube(kind,[p,p+Vector((0,0,height))],.032,'PaintedSteel',18)
        box(kind,p+Vector((0,0,.014)),(.16,.16,.028),'BareSteel')

def stairs(x,y,width,height,run,kind='Stairs'):
    count=math.ceil(height/.16);depth=run/count
    for i in range(count):
        z=height*(i+1)/count;yy=y+(i+.5)*depth
        box(kind,(x,yy,z/2),(width,depth,z),'Concrete')
        box('Nosing',(x,yy-depth/2+.035,z+.007),(width-.04,.07,.014),'BridgeDeck')
    for s in (-1,1):rail((x+s*width/2,y,0),(x+s*width/2,y+run,height))

def glazing(a,b,z0,z1,kind='Glass',divisions=None):
    a,b=Vector(a),Vector(b);d=b-a;length=d.length;d.normalize();normal=Vector((-d.y,d.x,0))
    for z in (z0,z1):beam('WindowFrames',a+Vector((0,0,z)),b+Vector((0,0,z)),.055,.055,'PaintedSteel')
    count=divisions if divisions is not None else math.ceil(length/1.8)
    for i in range(count+1):
        p=a+(b-a)*i/count;beam('WindowFrames',p+Vector((0,0,z0)),p+Vector((0,0,z1)),.065,.065,'PaintedSteel')
    for i in range(count):
        p=a+(b-a)*(i+.5)/count
        box(kind,(p.x,p.y,(z0+z1)/2),(length/count-.07,.012,z1-z0-.07),'Glass',math.atan2(d.y,d.x))

def benches(x,y,broken=False):
    kind='CultivationBenches';w=2.9;d=1.4
    for dx in (-1.3,1.3):
        for dy in (-.57,.57):
            box(kind,(x+dx,y+dy,.44),(.055,.055,.88),'BareSteel')
            box(kind,(x+dx,y+dy,.018),(.13,.13,.036),'Rubber')
    for z in (.25,.83):
        for dy in (-.63,.63):box(kind,(x,y+dy,z),(w,.045,.045),'BareSteel')
        for dx in (-1.38,1.38):box(kind,(x+dx,y,z),(.045,d,.045),'BareSteel')
    box(kind,(x,y,.865),(w,d,.035),'BareSteel')
    for i in range(3):
        xx=x-.94+i*.94
        box(kind,(xx,y,.888),(.84,1.24,.026),'DarkPlastic')
        for dx in (-.42,.42):box(kind,(xx+dx,y,.93),(.025,1.24,.1),'DarkPlastic')
        for dy in (-.61,.61):box(kind,(xx,y+dy,.93),(.84,.025,.1),'DarkPlastic')
        for j in range(4):
            for k in range(3):
                px=xx-.27+k*.27;py=y-.43+j*.28
                cylinder(kind,(px,py,.96),.115,.12,'DarkPlastic',16)
                v4.medium(px,py,1.024,.103)
    for dx in (-1.33,1.33):
        beam(kind,(x+dx,y+.62,.9),(x+dx,y+.62,3.15),.045,.045,'BareSteel')
        beam(kind,(x+dx,y+.62,3.12),(x+dx,y-.4,3.12),.045,.045,'BareSteel')
    box(kind,(x,y,3.07),(2.7,.32,.07),'PaintedSteel')
    box('LampDiffusers',(x,y,3.031),(2.55,.23,.009),'Diffuser')
    detail.tube('Services',[(x+1.32,y+.66,.1),(x+1.32,y+.66,3.1),(x,y+.12,3.1)],.009,'Rubber',12)
    detail.tube('Services',[(x-1.4,y+.66,1.14),(x+1.4,y+.66,1.14)],.025,'PipeEnamel',20)
    sign((x,y-.729,.74),.48,'Tray',kind='Signs')

def export(name,g,rid='',collision=True,nanite=True,hulls=(),bevel=0,raw_hulls=()):
    original_name=name
    if name in ('SM_EcoNursery_Walls','SM_EcoBiosphere_Walls'):name+='_DoorClearV2'
    if original_name in ('SM_EcoNursery_Walls','SM_EcoNursery_WindowFrames','SM_EcoNursery_Glass'):name+='_FrontSealV3'
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(g['v'],[],g['f']);mesh.update();ob=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(ob)
    mats=list(dict.fromkeys(g['m']))
    for k in mats:mesh.materials.append(MATS[k])
    uv=mesh.uv_layers.new(name='UVMap');uv2=mesh.uv_layers.new(name='DetailLocal');age=mesh.color_attributes.new(name='ServiceAge',type='FLOAT_COLOR',domain='CORNER')
    for f,m,coords,sm in zip(mesh.polygons,g['m'],g['uv'],g['smooth']):
        f.material_index=mats.index(m);f.use_smooth=sm;dims=[i for i in range(3) if i!=max(range(3),key=lambda k:abs(f.normal[k]))]
        scale=.075 if m=='V2_CeramicFractureCore' else 1.28 if 'WallRelief' in m else 2
        for j,li in enumerate(f.loop_indices):
            p=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=coords[j] if coords is not None else (p[dims[0]]/scale,p[dims[1]]/scale)
            uv2.data[li].uv=uv.data[li].uv;age.data[li].color=(.11+.04*math.sin(p.x+p.y),0,0,1)
    mesh.uv_layers.active_index=0
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    if bevel:
        mod=ob.modifiers.new('Small manufactured arris','BEVEL');mod.width=bevel;mod.segments=2;mod.limit_method='ANGLE'
        bpy.ops.object.modifier_apply(modifier=mod.name)
    tri=ob.modifiers.new('Triangles','TRIANGULATE');bpy.ops.object.modifier_apply(modifier=tri.name)
    selected=[]
    for i,(c,sz) in enumerate(hulls):
        bpy.ops.mesh.primitive_cube_add(size=1,location=c);cu=bpy.context.object;cu.name=f'UCX_{name}_{i:03d}';cu.dimensions=sz
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);selected.append(cu)
    for i,vs in enumerate(raw_hulls):
        faces=vs['faces'] if isinstance(vs,dict) else [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
        vertices=vs['vertices'] if isinstance(vs,dict) else vs
        cm=bpy.data.meshes.new(f'UCX_{name}_{len(hulls)+i:03d}');cm.from_pydata(vertices,[],faces);cm.update()
        cu=bpy.data.objects.new(cm.name,cm);bpy.context.scene.collection.objects.link(cu);selected.append(cu)
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True)
    for cu in selected:cu.select_set(True)
    bpy.context.view_layer.objects.active=ob
    mesh_base=MESHBASE
    target_out=OUT
    target_out.mkdir(parents=True,exist_ok=True);path=target_out/(name+'.fbx')
    kind=original_name.rsplit('_',1)[-1]
    changed=(rid=='EcoNursery' and kind in ('WindowFrames','OfficeTrim') or
        rid=='EcoBiosphere' and kind=='Benches')
    reuse=name in REUSED and not changed
    if not reuse and (not ONLY or original_name in ONLY):
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    records.append(dict(REUSED[name],reused=True) if reuse else dict(name=name,kind=original_name.rsplit('_',1)[-1],room_id=rid,asset=mesh_base+'/Meshes/'+name,fbx=str(path),materials={'RS_'+k:MAPPING[k] for k in mats},triangles=len(ob.data.polygons),collision=collision,nanite=nanite,simple_collision_hulls=len(hulls)+len(raw_hulls)))
    for cu in selected:bpy.data.objects.remove(cu,do_unlink=True)
    if rid:ob.location=next((r['offset'] for r in CFG['rooms'] if r['id']==rid),[0,0,0])
    print('ECOLOGY_EXPORTED',name,len(ob.data.polygons),flush=True)
    return ob

def export_room(r):
    for kind,g in G.items():
        if not g['f']:continue
        # Glass is authored as separate interactive panes, never as a static
        # invisible blocker baked into the room shell.
        if kind=='Glass':continue
        decorative=kind in ('Signs','Services','PotSoil','Soil','Algae','Water','LampDiffusers','Nosing','RootFibres','Tiles','OfficeElectrical','OfficeSockets','OfficeSupplies','OfficeBoard','SpecimenGlass','SpecimenGel','SpecimenCaps','SpecimenContents','SpecimenLabels','DeckHardware','StairApproachMarkings','LampHousings','BedSupportHardware','GardenIrrigation')
        hulls=[]
        if r['id']=='EcoNursery' and kind=='OfficeWindowSill':hulls=[((-10,3,.44),(6,.28,.88))]
        if r['id']=='EcoNursery' and kind=='WindowFrames':
            hulls=[((x,3,2.0925),(.095,.30,2.425)) for x in (-12.8175,-7.1825)]
            hulls += [((-10,3,z),(5.54,.30,.07)) for z in (.915,3.27)]
        export('SM_'+r['id']+'_'+kind,g,r['id'],not decorative,kind not in ('Glass','Water','LampDiffusers','Algae','SpecimenGlass','SpecimenGel','SpecimenLabels','SpecimenContents'),hulls=hulls,bevel=.003 if kind in ('Walls','Columns','Roof','Benches','Platforms','CultivationBenches','FloatingBeds','WaterPumps','WaterTreatment','WaterControls','OfficeTrim','BedSupports') else 0,raw_hulls=RAIL_HULLS if kind=='Rails' else v4.PIPE_HULLS if kind=='CoarsePipes' else v5.VAULT_HULLS if kind=='VaultPipes' else ())

def rectangular_floor(x0,y0,x1,y1,z=0):
    box('Floors',((x0+x1)/2,(y0+y1)/2,z-.14),(x1-x0,y1-y0,.28),'Concrete')
    # Sparse physical expansion joints with metal drains at the perimeter.
    for x in range(math.ceil(x0/3)*3,math.floor(x1/3)*3+1,3):
        box('FloorJoints',(x,(y0+y1)/2,z+.0007),(.004,y1-y0,.0014),'Mortar')

def shell(r):
    a,b,h=r['size'];hx=a/2;hy=b/2;ROOM.update(id=r['id'],height_m=h)
    for p,q in [((-hx,-hy),(hx,-hy)),((hx,hy),(-hx,hy)),((-hx,hy),(-hx,-hy)),((hx,-hy),(hx,hy))]:
        o=[dict(center=hy,width=3,height=2.8)] if p[0]==q[0] else []
        wall_segment(p,q,h,o,tiles=r['id']=='EcoNursery')
    box('Roof',(0,0,h+.18),(a+.28,b+.28,.36),'Concrete')
    for x in range(int(-hx)+2,int(hx),6):
        box('RoofTrusses',(x,0,h-.35),(.18,b-.25,.7),'PaintedSteel')
        for y in (-hy+.4,hy-.4):
            box('Columns',(x,y,h/2),(.35,.42,h),'PaintedSteel');box('Columns',(x,y,.045),(.65,.7,.09),'BareSteel')
            for dx in (-.23,.23):detail.fastener((x+dx,y,.1),(0,0,1),.026,'Columns')
    for s in (-1,1):
        x0,x1=sorted((s*hx,s*(hx+2)));rectangular_floor(x0,-2,x1,2)
        wall_segment((x0,-2),(x1,-2),3.4,tiles=False);wall_segment((x1,2),(x0,2),3.4,tiles=False)
        wall_segment((s*(hx+2),-2),(s*(hx+2),2),3.4,[dict(center=2,width=3,height=2.8)],tiles=False)
        box('Roof',((x0+x1)/2,0,3.55),(2.28,4.28,.3),'Concrete')
    for y in (-hy+.65,hy-.65):detail.smooth_pipe([(-hx+.6,y,h-.95),(hx-.6,y,h-.95)],.065)
    sign((-hx+1.2,-1.95,2.6),1.5,{'EcoNursery':'Nursery','EcoHydroponics':'Hydro','EcoBiosphere':'Biosphere'}[r['id']],n=(0,1,0))
    sign((hx+1,1.8,2.9),.65,'Exit')
    for l in r['lights']:
        x,y,z=l['position']
        if l.get('grow_fixture') or l.get('fill_only'):continue
        # Biosphere keeps its previous physical fixture; the source moves below it.
        if r['id']=='EcoBiosphere':
            z-=.043
            box('LampHousings',(x,y,z+.14),(1.1,.35,.16),'PaintedSteel')
            box('LampDiffusers',(x,y,z+.055),(1.01,.28,.01),'Diffuser')
            if abs(x)<hx and z<h-1:
                for dx in (-.4,.4):detail.tube('Services',[(x+dx,y,z+.22),(x+dx,y,h-.03)],.006,'BareSteel',12)
            continue
        ceiling=l.get('fixture_ceiling_z',h)
        box('LampHousings',(x,y,z+.077),(1.1,.35,.12),'PaintedSteel')
        box('LampDiffusers',(x,y,z+.012),(1.01,.28,.01),'Diffuser')
        if abs(x)<hx and z<ceiling-.25:
            for dx in (-.4,.4):detail.tube('Services',[(x+dx,y,z+.14),(x+dx,y,ceiling-.01)],.006,'BareSteel',12)

def smooth_path(points,steps=9):
    ps=[Vector(p) for p in points];out=[]
    for i in range(len(ps)-1):
        p0,p1,p2,p3=ps[max(0,i-1)],ps[i],ps[i+1],ps[min(len(ps)-1,i+2)]
        for j in range(steps):
            t=j/steps;out.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
    return out+[ps[-1]]

def root_tube(points,r0,r1,kind='RootWood',sides=40):
    path=smooth_path(points);frames=detail.frames(path);vs=[];fs=[];uv=[];distance=0.;dist=[]
    for i,(p,t,a,b) in enumerate(frames):
        if i:distance+=(p-frames[i-1][0]).length
        dist.append(distance);q=i/(len(frames)-1);rad=r0*(1-q)**1.15+r1*q
        for j in range(sides):
            ang=j*math.tau/sides;rr=rad*(1+.065*math.sin(ang*7+q*3)+.03*math.sin(ang*13-q*8))
            vs.append(p+(a*math.cos(ang)+b*math.sin(ang))*rr)
    for i in range(len(frames)-1):
        for j in range(sides):
            fs.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
            uv.append([(j/sides*2,dist[i]/2),((j+1)/sides*2,dist[i]/2),((j+1)/sides*2,dist[i+1]/2),(j/sides*2,dist[i+1]/2)])
    fs.extend([tuple(reversed(range(sides))),tuple((len(frames)-1)*sides+j for j in range(sides))]);uv.extend([None,None])
    poly(kind,vs,fs,'Bark',uv,True)

sys.path.insert(0,str(SCRIPT))
import ecology_v3_geometry as v3
v3.setup(globals())
import ecology_v4_geometry as v4
v4.setup(globals())
import ecology_v5_geometry as v5
v5.setup(globals())

for r in CFG['rooms']:
    G={};RAIL_HULLS=[];v4.reset();v5.reset();shell(r);rid=r['id'];hx,hy,h=r['size'][0]/2,r['size'][1]/2,r['size'][2]
    if rid=='EcoNursery':
        v3.nursery(r)
        v4.office_sockets()
    elif rid=='EcoHydroponics':
        v3.hydro(r)
        v5.bed_supports()
    else:
        rectangular_floor(-24,-16.5,24,16.5)
        v5.garden(r)
        box('Platforms',(0,14.2,2.88),(22,3.8,.24),'BridgeDeck')
        for x in (-10,0,10):
            for y in (12.5,15.8):box('Columns',(x,y,1.4),(.24,.24,2.8),'PaintedSteel')
        rail((-11,12.3,3),(11,12.3,3));rail((-11,16.1,3),(11,16.1,3))
        for x in (-12.2,12.2):
            stairs(x,5.3,2.4,3,7);box('Platforms',(x,14.2,2.88),(2.4,3.8,.24),'BridgeDeck')
            rail((x+(-1.2 if x<0 else 1.2),12.3,3),(x+(-1.2 if x<0 else 1.2),16.1,3))
        # Observation suite is inset inside the authored footprint.
        v5.monitor_front()
        wall_segment((-16,7),(-16,16.5),3.6,tiles=False);box('ObservationRoof',(-20,11.75,3.72),(8,9.5,.24),'Concrete')
        desk=r['monitoring_desk'];dx,dy,_=desk['center']
        box('Benches',desk['center'],desk['size'],'PaintedSteel')
        for x in (dx-2,dx+2):
            for y in (dy-.4,dy+.4):box('Benches',(x,y,.375),(.06,.06,.75),'BareSteel')
        # Detailed station desktop equipment is reused through authored part anchors.
        sign((-20,6.80,3.45),1.4,'Control',n=(0,-1,0));sign((3,-5.15,1.25),1.15,'Specimen')
        for x in (-13,-8.7):box('EvacuationPallets',(x,-15.72,.035),(1.3,1,.07),'BridgeDeck')
        for x in (-10,10):
            detail.smooth_pipe([(x,-15.3,.3),(x,-15.3,5.8),(x,8,5.8),(x,8,.2)],.09)
        sign((18,15.8,2.5),1.25,'Shutdown');sign((13,-4.8,1.35),.85,'Quarantine')
        for x,y,z in ((3,-5.15,1.25),(13,-4.8,1.35)):
            box('SignPosts',(x,y+.04,z/2),(.05,.05,z),'PaintedSteel');box('SignPosts',(x,y+.04,.025),(.30,.25,.05),'BareSteel')
    export_room(r)

# Four metre connection, preserved separately from the complete room bodies.
G={};ROOM.update(id='Link',height_m=3.4)
rectangular_floor(0,-2,4,2);wall_segment((0,-2),(4,-2),3.4,tiles=False);wall_segment((4,2),(0,2),3.4,tiles=False)
box('Roof',(2,0,3.55),(4,4.28,.30),'Concrete')
for k,g in G.items():export('SM_EcoLink_'+k,g,'Link',True,True)

# Adapt the accepted cabinet carcass and frame FBX; build meaningful new drawer inserts.
for target in ('RecordsCarcass','RecordsFrame'):
    records.append(dict(REUSED['SM_Eco_'+target],reused=True))
for seed in (True,False):
    G={};kind='Drawer';w=.627;d=.395
    box(kind,(0,0,.039),(w,d,.014),'BareSteel')
    for x in (-w/2,w/2):box(kind,(x,0,.13),(.012,d,.19),'BareSteel')
    for y in (-d/2,d/2):box(kind,(0,y,.13),(w,.012,.19),'BareSteel')
    box(kind,(0,.234,.145),(.68,.03,.298),'PaintedSteel')
    detail.tube(kind,[(-.12,.259,.12),(-.12,.298,.12),(.12,.298,.12),(.12,.259,.12)],.007,'BareSteel',16)
    sign((0,.251,.22),.2,'Seed' if seed else 'Records',n=(0,1,0),kind=kind)
    if seed:
        for x in (-.1,.1):box(kind,(x,0,.085),(.006,.37,.08),'BareSteel')
        box(kind,(0,0,.085),(.62,.006,.08),'BareSteel')
        for x in (-.21,0,.21):
            for y in (-.10,.10):
                for j in range(3):box(kind,(x,y+j*.018,.082+j*.012),(.14,.095,.016),'Paper',RNG.uniform(-.15,.15))
    else:
        for j in range(7):box(kind,(0,-.14+j*.044,.11),(.54,.012,.14),'Paper')
    name='SM_Eco_'+('SeedDrawer' if seed else 'RecordsDrawer');export(name,G[kind],collision=True,nanite=True,hulls=[((0,0,.135),(.67,.43,.27))],bevel=.002)

for item in OLD:
    if item['room_id']=='Interaction':records.append(dict(item,reused=True))
import ecology_v6_reuse as v6
v6.desktop(globals())

# A separate editable assembly source: local exported room meshes plus actual reused foliage coordinates.
for r in CFG['rooms']:
    for p in r['plants']:
        ob=bpy.data.objects.new(r['id']+'_PlantReference',None);bpy.context.scene.collection.objects.link(ob)
        ob.location=Vector(r['offset'])+Vector(p['position']);ob['ue_mesh']=p['mesh'];ob['height_m']=p['height_m'];ob['yaw']=p['yaw']
    for p in r['container_groups']:
        ob=bpy.data.objects.new(r['id']+'_'+p['id'],None);bpy.context.scene.collection.objects.link(ob)
        ob.location=Vector(r['offset'])+Vector(p['position_m']);ob['prototype']=p['prototype'];ob['caption']=p['caption']
for item in [i for i in records if i['room_id']=='Link']:
    src=bpy.data.objects[item['name']];src.location=(15,0,0);ob=src.copy();ob.data=src.data;bpy.context.scene.collection.objects.link(ob);ob.location=(63,0,0)
CFG['geometry_revision']=8
(ROOT/'Config/room.json').write_text(json.dumps(CFG,ensure_ascii=False,indent=2),encoding='utf8')
(ROOT/'Authored/manifest.json').write_text(json.dumps(dict(objects=records,revision=CFG['revision'],source_units='metres',coordinates='Blender x,y,z -> Unreal 100x,-100y,100z',tests_run=False,rendered=False),indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'EcologyTheme_Source.blend'))
print('ECOLOGY_SOURCE_SAVED',len(records),flush=True)
