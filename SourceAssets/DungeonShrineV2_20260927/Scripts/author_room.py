"""Author the empty shrine from the concept; metres, +Y goes into the room.

The concrete entrance uses the production ShoredBreach fracture/rebar author.
No render, preview scene or test is run here. Existing statues are not rebuilt.
"""
import json, math, random, sys
from pathlib import Path
import bpy, bmesh
from mathutils import Vector, noise

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parents[1]
OUT=ROOT/'Authored';OUT.mkdir(parents=True,exist_ok=True)
CFG=json.loads((ROOT/'Config/room.json').read_text())
R=random.Random(CFG['seed']);G={}
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
sys.path.insert(0,str(PROJECT/'SourceAssets/DungeonRoomShells20260922/Scripts'))
import room_detail_geometry as detail

def poly(kind,vs,fs,mat,uv=None,smooth=False):
    g=G.setdefault(kind,dict(v=[],f=[],m=[],smooth=[]));off=len(g['v'])
    g['v'].extend(tuple(v) for v in vs);g['f'].extend(tuple(off+i for i in f) for f in fs)
    g['m'].extend([mat]*len(fs));g['smooth'].extend(smooth if isinstance(smooth,list) else [smooth]*len(fs))

def box(kind,c,size,mat='Mortar',yaw=0):
    x,y,z=c;a,b,h=[v*.5 for v in size];co,si=math.cos(yaw),math.sin(yaw)
    vs=[(x+dx*co-dy*si,y+dx*si+dy*co,z+dz) for dx,dy,dz in [(-a,-b,-h),(a,-b,-h),(a,b,-h),(-a,b,-h),(-a,-b,h),(a,-b,h),(a,b,h),(-a,b,h)]]
    poly(kind,vs,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)

def prism(kind,points,start,direction,normal,depth,mat):
    from mathutils.geometry import tessellate_polygon
    if sum(points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points)))<0:points=list(reversed(points))
    s=Vector((start[0],start[1],0));d=Vector((direction[0],direction[1],0));n=Vector((normal[0],normal[1],0));num=len(points)
    vs=[tuple(s+d*t+n*dep+Vector((0,0,z))) for dep in (-depth/2,depth/2) for t,z in points]
    tris=tessellate_polygon([[Vector((t,z,0)) for t,z in points]])
    fs=[tuple(tri) for tri in tris]+[tuple(num+i for i in reversed(tri)) for tri in tris]
    fs.extend((i,i+num,(i+1)%num+num,(i+1)%num) for i in range(num));poly(kind,vs,fs,mat)

detail.setup({'poly':poly,'box':box,'prism':prism,'CFG':{'style':{'wall_thickness':CFG['wall_thickness_m']}}})
detail.breach_wall(Vector((0,0)),Vector((1,0)),Vector((0,1)),6.5,3.9,CFG['breach'],'Concrete')
G['EntranceConcrete']=G.pop('Shell');G['EntranceRebar']=G.pop('Services')

def stone(kind,c,size,mat='Stone',yaw=0,wear=.008,density=3):
    """Fitted block with small real rounded edges and low-amplitude surface erosion."""
    bm=bmesh.new();bmesh.ops.create_cube(bm,size=1)
    for v in bm.verts:
        for k in range(3):v.co[k]*=size[k]
    bmesh.ops.bevel(bm,geom=list(bm.edges),offset=min(wear,min(size)*.13),segments=3,affect='EDGES',clamp_overlap=True)
    bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=density,use_grid_fill=True)
    bm.normal_update();co,si=math.cos(yaw),math.sin(yaw)
    seed=Vector((R.uniform(0,80),R.uniform(0,80),R.uniform(0,80)))
    for v in bm.verts:
        p=v.co.copy();n=v.normal.copy()
        # Millimetre relief, not centimetres of random bulging on every block.
        amp=min(.0028,min(size)*.018)
        v.co+=n*(noise.noise_vector(p*19+seed)[0]*amp+noise.noise_vector(p*47+seed)[1]*amp*.32)
    bm.verts.index_update();vs=[]
    for v in bm.verts:
        x,y,z=v.co;vs.append((c[0]+x*co-y*si,c[1]+x*si+y*co,c[2]+z))
    faces=[tuple(v.index for v in f.verts) for f in bm.faces]
    poly(kind,vs,faces,mat,smooth=True);bm.free()

def slab(points,top,depth,kind='Floor',mat='FloorStone'):
    """Thin polygonal paver, with a physically bevelled rim and separate stone cut."""
    if sum(points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points)))<0:points=list(reversed(points))
    n=len(points);verts=[(x,y,z) for z in (top-depth,top) for x,y in points]
    faces=[tuple(reversed(range(n))),tuple(range(n,2*n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    mesh=bpy.data.meshes.new('slab_temp');mesh.from_pydata(verts,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.bevel(bm,geom=list(bm.edges),offset=.006,segments=3,affect='EDGES',clamp_overlap=True)
    bmesh.ops.subdivide_edges(bm,edges=list(bm.edges),cuts=2,use_grid_fill=True);bm.normal_update();bm.verts.index_update()
    for v in bm.verts:
        if v.co.z>top-.003:v.co.z+=noise.noise_vector(v.co*16)[0]*.0015
    vs=[tuple(v.co) for v in bm.verts]
    for top_face in (True,False):
        fs=[tuple(v.index for v in f.verts) for f in bm.faces if (f.normal.z>.65)==top_face]
        poly(kind,vs,fs,mat if top_face else 'StoneCut',smooth=True)
    bm.free();bpy.data.meshes.remove(mesh)

# Solid backing owns mortar gaps; floor stays level with the existing passage.
box('Backing',(3.25,3.6,-.095),(6.5,7.75,.15),'Mortar')
for x in (.075,6.425):box('Backing',(x,3.71,1.60),(.15,7.47,3.2),'Mortar')
box('Backing',(3.25,7.39,2.13),(6.5,.20,4.26),'Mortar')
box('EntranceConcrete',(3.25,.14,4.23),(6.5,.83,.66),'Concrete')

# Broad fitted paving, a few chipped edges, 8-12 mm filled joints.
y=-.20;row=0
while y<7.26:
    h=min(R.uniform(.61,.81),7.28-y);x=.15
    while x<6.34:
        w=min(R.uniform(.76,1.18),6.35-x)
        if w<.06:break
        inset=.009;x0=x+inset;x1=x+w-inset;y0=y+inset;y1=y+h-inset
        cut=R.uniform(.018,.055) if x<1.5 or x>5.1 else R.uniform(.010,.025)
        points=[(x0+cut,y0),(x1-cut*.6,y0),(x1,y0+cut),(x1,y1-cut),(x1-cut,y1),(x0+cut,y1),(x0,y1-cut),(x0,y0+cut)]
        slab(points,R.uniform(.0,.005),.08,mat='FloorStone'+str((row+int(x*3))%3))
        x+=w
    y+=h;row+=1

# Fitted limestone courses. Only local corner damage, no uniformly protruding cubes.
z=.015;course=0
while z<3.02:
    h=min(R.uniform(.245,.35),3.025-z)
    if h<.04:break
    for side in (0,1):
        y=.30
        first=True
        while y<7.23:
            span=min((.32 if first and course%2 else R.uniform(.58,.92)),7.25-y)
            if span<.06:break
            depth=R.uniform(.205,.24);x=depth/2+.035 if side==0 else 6.465-depth/2
            stone('SideMasonry',(x,y+span/2,z+h/2),(depth,span-.012,h-.012),'Stone'+str(R.randrange(3)),wear=R.uniform(.006,.012))
            y+=span;first=False
    # Backing wall behind the niche remains recessed relative to its arch.
    x=.16
    while x<6.31:
        span=min(R.uniform(.53,.87),6.34-x)
        if span<.06:break
        stone('BackMasonry',(x+span/2,7.23,z+h/2),(span-.012,.22,h-.012),'Stone'+str(R.randrange(3)),wear=.009)
        x+=span
    z+=h;course+=1

# Complete the upper back wall behind the vault and the niche's crown.
while z<4.40:
    h=min(.29,4.40-z);x=.16
    while x<6.31:
        span=min(R.uniform(.57,.86),6.34-x)
        if span<.06:break
        stone('BackMasonry',(x+span/2,7.23,z+h/2),(span-.012,.22,h-.012),'Stone'+str(R.randrange(3)),wear=.007)
        x+=span
    z+=h

def vault_piece(kind,cx,y0,y1,z0,rx,rz,a0,a1,thick,mat,steps=5):
    vs=[]
    for y in (y0,y1):
        for add in (0,thick):
            for i in range(steps+1):
                a=a0+(a1-a0)*i/steps
                vs.append((cx+(rx+add)*math.cos(a),y,z0+(rz+add)*math.sin(a)))
    n=steps+1;fs=[]
    for i in range(steps):
        fs.extend([(i,i+1,2*n+i+1,2*n+i),(n+i,3*n+i,3*n+i+1,n+i+1),
                   (i,n+i,n+i+1,i+1),(2*n+i,2*n+i+1,3*n+i+1,3*n+i)])
    fs.extend([(0,2*n,3*n,n),(n-1,2*n-1,4*n-1,3*n-1)])
    poly(kind,vs,fs,mat)

# Continuous dark mortar vault with close stone courses in front of it.
vault_piece('Backing',3.25,.32,7.46,2.98,3.16,1.48,0,math.pi,.08,'Mortar',80)
for row in range(10):
    y0=.32+row*.694;y1=min(7.25,y0+.682)
    for i in range(23):
        a0=i*math.pi/23+.0025;a1=(i+1)*math.pi/23-.0025
        vault_piece('Vault',3.25,y0,y1,2.98,3.015,1.38,a0,a1,.145,'Stone'+str(R.randrange(3)),6)

# Two slim structural ribs express the ceiling; no false oversized columns.
for y in (1.40,4.28):
    for x in (.30,6.20):
        for level in range(10):stone('Ribs',(x,y,.15+level*.299),(.22,.31,.287),'Stone1',wear=.007,density=2)
        stone('Ribs',(x,y,3.00),(.32,.41,.12),'Stone1',density=2)
    for i in range(25):
        vault_piece('Ribs',3.25,y-.17,y+.17,2.98,2.93,1.31,i*math.pi/25+.002,(i+1)*math.pi/25-.002,.105,'Stone1',5)

# Recessed shrine niche, sized for every existing 1.8-2.05 m statue.
for x in (1.77,4.73):
    for i in range(7):stone('Niche',(x,6.85,.145+i*.278),(.30,.39,.266),'Stone1',wear=.008)
    stone('Niche',(x,6.83,1.98),(.40,.45,.13),'Stone1',density=2)
    stone('Niche',(x,6.83,.10),(.44,.48,.20),'Stone1',density=2)
for i in range(21):
    vault_piece('Niche',3.25,6.61,7.06,2.03,1.33,1.25,i*math.pi/21+.003,(i+1)*math.pi/21-.003,.30,'Stone1',6)
for c,size in [((3.25,6.24,.09),(2.08,1.66,.18)),((3.25,6.31,.27),(1.78,1.39,.18)),((3.25,6.35,.45),(1.48,1.15,.18))]:
    stone('Pedestal',c,size,'Stone1',wear=.014,density=6)

# Low earth deposits keep the 1.8 m central approach clear. No generic big pile.
def bank_height(x,y,side):
    edge=x if side==0 else 6.5-x
    length_bump=.13+.20*math.exp(-((y-1.85)/1.3)**2)+.08*math.sin(y*1.4)**2
    if side==0:length_bump+=.60*math.exp(-((y-5.2)/.85)**2)
    return max(.003,(1-min(1,max(0,edge-.16)/1.04))**1.7*length_bump)
for side in (0,1):
    vs=[];fs=[]
    for j in range(60):
        y=.26+j*7.0/59
        for i in range(12):
            edge=.14+i*1.06/11;x=edge if side==0 else 6.5-edge
            vs.append((x,y,bank_height(x,y,side)+noise.noise_vector(Vector((x,y,0))*13)[0]*.006))
    for j in range(59):
        for i in range(11):
            a=j*12+i;fs.extend([(a,a+1,a+13),(a,a+13,a+12)])
    poly('Earth',vs,fs,'Earth',smooth=True)
    for i in range(130):
        edge=R.uniform(.22,1.07);x=edge if side==0 else 6.5-edge;y=R.uniform(.36,7.18)
        s=R.uniform(.035,.14);h=s*R.uniform(.4,.85)
        detail.chunk((x,y,bank_height(x,y,side)+h*.28),(s*R.uniform(1,1.8),s,h),R,'StoneCut','Rubble')
# Collapsed left rear wall stones, seated in the bank rather than across the route.
for i in range(20):
    x=R.uniform(.30,.87);y=R.uniform(4.50,5.95);z=bank_height(x,y,0)
    detail.chunk((x,y,z+.09),(R.uniform(.18,.40),R.uniform(.20,.36),R.uniform(.12,.25)),R,'StoneCut','Rubble')
for side in (0,1):
    base=CFG['breach']['left'] if side==0 else CFG['breach']['right']
    for i in range(24):
        x=base+R.uniform(-.18,.15);y=R.uniform(-.19,.56);s=R.uniform(.025,.14)
        detail.chunk((x,y,s*.20),(s,s*R.uniform(.6,1.3),s*.55),R,'FractureConcrete','Rubble')

# Two unanimated metal sconces; warm emitting ceramic core, no new particle system.
for x in (1.40,5.10):
    box('Sconces',(x,7.085,1.95),(.13,.08,.37),'ServiceHardware')
    detail.sweep('Sconces',[(x,7.035,1.90),(x,6.79,1.84),(x,6.65,2.025)],.018,'ServiceHardware',16)
    detail.sweep('Sconces',[(x,6.63,2.01),(x,6.63,2.08)],.14,'ServiceHardware',32,.012,'ServiceHardware')
    detail.sweep('Sconces',[(x,6.63,2.045),(x,6.63,2.12)],.074,'WarmGlass',24)

# Export each bounded assembly, preserving material slot identity and collision intent.
MATS={name:bpy.data.materials.new(name) for name in sorted({m for g in G.values() for m in g['m']})}
records=[]
noncollision={'EntranceRebar','Rubble','Sconces'}
for kind,g in G.items():
    mesh=bpy.data.meshes.new('SM_ShrineV2_'+kind);mesh.from_pydata(g['v'],[],g['f']);mesh.update()
    names=list(dict.fromkeys(g['m']))
    for name in names:mesh.materials.append(MATS[name])
    for i,p in enumerate(mesh.polygons):p.material_index=names.index(g['m'][i]);p.use_smooth=g['smooth'][i]
    # Assign slots first so BMesh preserves them through vertex compaction.
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=.00001)
    bmesh.ops.dissolve_degenerate(bm,dist=.000001,edges=list(bm.edges))
    bmesh.ops.triangulate(bm,faces=list(bm.faces))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    uv=mesh.uv_layers.new(name='UVMap')
    for p in mesh.polygons:
        axis=max(range(3),key=lambda k:abs(p.normal[k]));axes=[k for k in range(3) if k!=axis]
        for li in p.loop_indices:
            v=mesh.vertices[mesh.loops[li].vertex_index].co;uv.data[li].uv=(v[axes[0]],v[axes[1]])
    obj=bpy.data.objects.new(mesh.name,mesh);bpy.context.collection.objects.link(obj)
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    # UV projection is assigned after triangulation so thin fracture triangles
    # receive a valid tangent basis even when their source polygon is nonplanar.
    path=OUT/(obj.name+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    records.append(dict(kind=kind,name=obj.name,fbx=str(path),materials=names,collision=kind not in noncollision,
        triangles=len(obj.data.polygons),position_cm=CFG['origin_ue_cm']))
    print('SHRINE_V2_AUTHORED',kind,len(obj.data.polygons),flush=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'ShrineRoomV2_Editable.blend'))
(OUT/'manifest.json').write_text(json.dumps(dict(revision=CFG['revision'],objects=records,tests_run=False),indent=2),encoding='utf-8')
print('SHRINE_V2_ROOM_EXPORTED',len(records),flush=True)
