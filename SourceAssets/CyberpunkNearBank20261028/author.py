"""Author curved embankment and bounded near-side neighborhood assemblies only."""
import bpy,bmesh,ast,json,math,random,sys,collections
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R));from design import *
sys.path.insert(0,str(R/'BlenderDeps'))
from shapely.geometry import Polygon,Point,LineString,box
from shapely.ops import unary_union,triangulate
# Reuse the proven geometry helper class without executing the previous authoring module.
old=PROJECT/'SourceAssets/CyberpunkUrbanLandscape20261025/author_geometry.py'
node=next(n for n in ast.parse(old.read_text(encoding='utf8')).body if isinstance(n,ast.ClassDef) and n.name=='Build')
exec(compile(ast.Module(body=[node],type_ignores=[]),str(old),'exec'),globals())
bpy.ops.wm.read_factory_settings(use_empty=True)
OUT=R/'Meshes';OUT.mkdir(exist_ok=True)
report=dict(stage='authored',meshes=[],seed=SEED,scope='near_bank_only',tests_run=False)
layout=dict(seed=SEED,scope='near_bank_only',shore=[],assemblies=[],plants=[],buildings=[],rejected=[])
urban=json.loads((PROJECT/'SourceAssets/CyberpunkUrbanLandscape20261025/layout.json').read_text())
ext=json.loads((PROJECT/'SourceAssets/CyberpunkExteriorUpgrade20261025/layout.json').read_text())
host=box(*HOST);occupied=[host];road_shapes=[LineString([r['a'],r['b']]).buffer(r['width']/2+2,cap_style=2) for r in ROADS]
for row in BUILDINGS:
    b=ext['prototypes']['BPP_'+row['style']]['bounds'];px,py,pz=row['p']
    rect=box(px+b['min'][0]/100,py+b['min'][1]/100,px+b['max'][0]/100,py+b['max'][1]/100)
    if any(rect.buffer(8).intersects(q) for q in occupied+road_shapes):
        layout['rejected'].append(dict(id=row['id'],reason='footprint_clearance'));continue
    row=dict(row,blueprint='/Game/Props/CyberpunkExteriorUpgrade20261025/Blueprints/BP_Exterior_'+row['style'],footprint=list(rect.bounds),height_m=(b['max'][2]-b['min'][2])/100)
    row['p'][2]-=b['min'][2]/100
    occupied.append(rect);layout['buildings'].append(row)
obstacles=unary_union(occupied+road_shapes)

def export(b,key,origin,bevel=.015,collision=False):
    obj=b.object('SM_NB_'+key,bevel)
    # Continue physical UV coordinates across chunk seams.
    world_offset=(origin[0],-origin[1],origin[2]);uv=obj.data.uv_layers.active
    for face in obj.data.polygons:
        axis=max(range(3),key=lambda i:abs(face.normal[i]));dims=[i for i in range(3) if i!=axis]
        for li in face.loop_indices:
            uv.data[li].uv.x+=world_offset[dims[0]]/4
            uv.data[li].uv.y+=world_offset[dims[1]]/4
    # Smooth longitudinal curvature while retaining sharp manufactured section edges.
    bm=bmesh.new();bm.from_mesh(obj.data)
    for face in bm.faces:face.smooth=True
    for edge in bm.edges:
        if edge.is_manifold:edge.smooth=edge.calc_face_angle(0)<math.radians(35)
    bm.to_mesh(obj.data);bm.free();obj.data.update()
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    path=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
    report['meshes'].append(dict(key=key,name=obj.name,fbx=str(path),p=origin,roles=[m.name for m in obj.data.materials],triangles=sum(len(p.vertices)-2 for p in obj.data.polygons),collision=collision))
    obj.location=(origin[0],-origin[1],origin[2]);obj.select_set(False)

def add_profile(b,xs,profile,role,origin):
    vertices=[]
    for x in xs:
        for offset,height in profile(x):
            p=frame(x,offset,GROUND+height);vertices.append(tuple(p[j]-origin[j] for j in range(3)))
    n=len(profile(xs[0]));faces=[tuple(reversed(range(n))),tuple((len(xs)-1)*n+j for j in range(n))]
    for i in range(len(xs)-1):
        for j in range(n):faces.append((i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j))
    b.mesh(vertices,faces,role)

chunks=math.ceil((X[-1]-X[0])/240)
for ci in range(chunks):
    x0=X[0]+(X[-1]-X[0])*ci/chunks;x1=X[0]+(X[-1]-X[0])*(ci+1)/chunks
    step=1.5 if abs((x0+x1)/2)<800 else 3.0
    n=math.ceil((x1-x0)/step);xs=[x0+(x1-x0)*j/n for j in range(n+1)]
    origin=[(x0+x1)/2,shore_y((x0+x1)/2)-20,GROUND]
    b=Build()
    # The base is below finished surfaces, so no coplanar old/new ground is retained.
    vs=[]
    for x in xs:
        y=shore_y(x);back=legacy_y(x)-687.5
        vs.extend([(x-origin[0],y-.25-origin[1],-.22),(x-origin[0],back-origin[1],-.22),(x-origin[0],back-origin[1],-16.25),(x-origin[0],y-.25-origin[1],-16.25)])
    fs=[(3,2,1,0),tuple((len(xs)-1)*4+j for j in range(4))]
    for i in range(len(xs)-1):
        for j in range(4):fs.append((i*4+j,(i+1)*4+j,(i+1)*4+(j+1)%4,i*4+(j+1)%4))
    b.mesh(vs,fs,'Ground')
    add_profile(b,xs,lambda x:[(-3.0,-6.0),(-2.0,-4.7),(-.15,-.1),(.70,-.1),(.70,-6.0)],'Stone',origin)
    add_profile(b,xs,lambda x:[(-.28,-.10),(-.28,.20),(-.22,.28),(.70,.28),(.78,.20),(.78,-.10)],'Cap',origin)
    add_profile(b,xs,lambda x:[(.80,-.12),(.80,.12),(walk_width(x)+.80,.12),(walk_width(x)+.80,-.12)],'Paving',origin)
    add_profile(b,xs,lambda x:[(walk_width(x)+.82,-.12),(walk_width(x)+.82,.19),(walk_width(x)+1.02,.19),(walk_width(x)+1.02,-.12)],'Cap',origin)
    add_profile(b,xs,lambda x:[(walk_width(x)+1.05,-.20),(walk_width(x)+1.05,-.03),(walk_width(x)+12,-.03),(walk_width(x)+12,-.20)],'Lawn',origin)
    export(b,f'Bank_{ci:02d}',origin,0,abs(origin[0])<800)
    layout['shore'].extend(frame(x) for x in xs[:-1])
layout['shore'].append(frame(X[-1]))

# Continuous rail follows the same curve. No independent straight fence segments.
for start,end in [(-650,-325),(-325,0),(0,325),(325,650)]:
    origin=frame((start+end)/2,0,GROUND);b=Build()
    for z,r in [(1.28,.045),(.78,.025)]:
        pts=[frame(start+(end-start)*i/math.ceil((end-start)/1.4),.38,GROUND+z) for i in range(math.ceil((end-start)/1.4)+1)]
        b.tube([[p[j]-origin[j] for j in range(3)] for p in pts],r,'Metal',12)
    count=round((end-start)/2.5)
    for i in range(count+1):
        x=start+(end-start)*i/count;p=frame(x,.38,GROUND+.27);q=[p[j]-origin[j] for j in range(3)]
        b.cylinder(q,.055,1.01,'Metal',16)
    export(b,f'Rail_{start+650:04d}',origin,0,True)

# Build one unioned street surface, avoiding overlapping full road pieces at junctions.
lane=unary_union([LineString([r['a'],r['b']]).buffer(3.5,cap_style=2) for r in ROADS])
full=unary_union([LineString([r['a'],r['b']]).buffer(r['width']/2,cap_style=2) for r in ROADS])
sidewalk=full.difference(lane.buffer(.18))
origin=[15,-120,GROUND];b=Build()
def surface(poly,z,role):
    for t in triangulate(poly):
        if not poly.covers(t.representative_point()) or t.intersection(poly).area<t.area*.99999:continue
        b.mesh([(x-origin[0],y-origin[1],z) for x,y in list(t.exterior.coords)[:3]],[(0,1,2)],role)
        b.mesh([(x-origin[0],y-origin[1],-.22) for x,y in list(t.exterior.coords)[:3]],[(2,1,0)],role)
    for p in getattr(poly,'geoms',[poly]):
        if p.geom_type!='Polygon':continue
        for ring in [p.exterior,*p.interiors]:
            coords=list(ring.coords)
            for a,c in zip(coords,coords[1:]):
                b.mesh([(a[0]-origin[0],a[1]-origin[1],-.22),(c[0]-origin[0],c[1]-origin[1],-.22),(c[0]-origin[0],c[1]-origin[1],z),(a[0]-origin[0],a[1]-origin[1],z)],[(0,1,2,3)],role)
surface(lane,.06,'Asphalt');surface(sidewalk,.16,'Paving')
for poly in getattr(lane,'geoms',[lane]):
    coords=list(poly.exterior.coords)
    for a,c in zip(coords,coords[1:]):
        b.mesh([(a[0]-origin[0],a[1]-origin[1],.06),(c[0]-origin[0],c[1]-origin[1],.06),(c[0]-origin[0],c[1]-origin[1],.16),(a[0]-origin[0],a[1]-origin[1],.16)],[(0,1,2,3)],'Cap')
for x in range(-195,220,10):
    if any(abs(x-v)<12 for v in (-215,235)):continue
    b.box((x-origin[0],-160-origin[1],.066),(4,.12,.008),'Marking')
for row in layout['buildings']:
    a=box(*row['footprint']);apron=a.buffer(3,join_style=2).difference(a)
    bx0,by0,bx1,by1=a.bounds
    b.box(((bx0+bx1)/2-origin[0],(by0+by1)/2-origin[1],-.10),(bx1-bx0+.10,by1-by0+.10,.24),'Cap')
    surface(apron,.12,'Paving')
    # A clear 3 m approach on the front facade links to the neighborhood street.
    cx=row['p'][0];front=a.bounds[3];end=-168 if row['p'][1]<-160 else -152
    path=LineString([(cx,front if row['p'][1]<-160 else a.bounds[1]),(cx,end)]).buffer(1.5,cap_style=2)
    path=path.difference(unary_union(occupied)).difference(full)
    surface(path,.12,'Paving')
export(b,'Neighborhood_Streets',origin,0,True)

rng=random.Random(SEED);plant_occupied=[]
def addplant(key,p,height):
    src=urban['source_meshes'][key];scale=height/((src['max'][2]-src['min'][2])/100)
    radius=max(src['max'][0]-src['min'][0],src['max'][1]-src['min'][1])/200*scale
    area=Point(p[:2]).buffer(radius+1.0)
    if area.intersects(obstacles) or any(math.dist(p[:2],q)<radius+r+.5 for q,r in plant_occupied):return
    plant_occupied.append((p[:2],radius))
    layout['plants'].append(dict(mesh=key,p=[p[0],p[1],p[2]-src['min'][2]/100*scale],yaw=rng.uniform(0,360),scale=scale,height=height,radius=radius))
for x0 in range(-630,631,22):
    x=x0+rng.uniform(-4,4);off=walk_width(x)+rng.uniform(6,11)
    addplant('TreeA' if x0%3 else 'TreeB',frame(x,off,GROUND-.02),rng.uniform(9,13))
for i in range(210):
    x=rng.uniform(-650,650);off=walk_width(x)+rng.uniform(3,9)
    addplant('Shrub' if i%3 else 'GroundA',frame(x,off,GROUND-.02),rng.uniform(.65,1.35) if i%3 else .4)
# Roadside trees are arranged in clusters outside the continuous walking strip.
for x in range(-195,225,22):
    for yy in (-143,-178):addplant('TreeB',[x+rng.uniform(-2,2),yy,GROUND-.22],rng.uniform(7,10))

for i,x in enumerate(NODES):
    for dx in (-3.8,3.8):
        xx=x+dx;layout['assemblies'].append(dict(kind='Bench',p=frame(xx,10.3,GROUND+.32),yaw=tangent(xx)+180,scale=1))
    layout['assemblies'].append(dict(kind='Bin',p=frame(x-7,10.0,GROUND+.12),yaw=tangent(x),scale=1))
    layout['assemblies'].append(dict(kind='Wayfinding',p=frame(x+7,10.0,GROUND+.12),yaw=tangent(x),scale=1))

b=Build();b.cylinder((0,0,0),.16,.08,'Metal',40);b.cylinder((0,0,.08),.085,.62,'Metal',40)
b.cylinder((0,0,.70),.095,.10,'Warm',40);b.cylinder((0,0,.80),.115,.045,'Metal',40)
export(b,'Bollard',[0,0,0],.008,False)
b=Build();b.box((0,0,0),(1.15,.24,.035),'Metal')
for i in range(12):b.box((-.51+i*.093,0,.023),(.035,.20,.018),'Rubber')
export(b,'Drain',[0,0,0],.004,False)
for x in range(-625,626,32):
    if min(abs(x-n) for n in NODES)<10:continue
    layout['assemblies'].append(dict(kind='Bollard',p=frame(x,walk_width(x)-.15,GROUND+.12),yaw=tangent(x),scale=1))
    layout['assemblies'].append(dict(kind='Drain',p=frame(x,walk_width(x)+.30,GROUND+.135),yaw=tangent(x),scale=1))

layout['ground_z']=GROUND;layout['roads']=ROADS;layout['protected_host']=HOST
layout['counts']=dict(bank_chunks=chunks,plants=len(layout['plants']),furniture=len(layout['assemblies']),buildings=len(layout['buildings']))
layout['planning']=dict(shoreline='C1 monotone cubic Hermite with bounded low-frequency shoreline variation',station_step_m=[1.5,3.0],promenade_width_m=[8,12.2],focus_shore_x_m=[-650,650],building_scope='near side only',opposite_bank_generated=False,new_test_levels=0)
(R/'geometry.json').write_text(json.dumps(report,indent=2),encoding='utf8')
(R/'layout.json').write_text(json.dumps(layout,indent=2),encoding='utf8')
bpy.ops.wm.save_as_mainfile(filepath=str(R/'NearBank_Source.blend'))
print('NEAR_BANK_AUTHORED',layout['counts'],'triangles',sum(r['triangles'] for r in report['meshes']),flush=True)
