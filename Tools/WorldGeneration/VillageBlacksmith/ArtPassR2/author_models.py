"""Dimensioned rural furniture art pass. Blender background, centimetre authoring, metre FBX."""
import bpy,bmesh,math,json,random
from pathlib import Path
from mathutils import Matrix,Vector
ROOT=Path(__file__).resolve().parents[4]
OUT=ROOT/'SourceAssets/HillsVillageBlacksmith20261117/ArtPassR2'
AUTH=OUT/'Authored';AUTH.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
rng=random.Random(1711172)
M={n:bpy.data.materials.new(n) for n in ['Oak','Endgrain','Iron','Linen','Blanket','Stone','Sign','Closed']}
parts=[];colliders=[];manifest=[];assets={}
def v(p):return Vector((p[0]/100,-p[1]/100,p[2]/100))
def mesh(name,verts,faces,mat='Oak'):
    d=bpy.data.meshes.new(name);d.from_pydata([v(p) for p in verts],[],faces);d.update()
    o=bpy.data.objects.new(name,d);bpy.context.collection.objects.link(o);d.materials.append(M[mat]);parts.append(o)
    bm=bmesh.new();bm.from_mesh(d);bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(d);bm.free()
    return o
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,mod):active(o);bpy.ops.object.modifier_apply(modifier=mod.name)
def uv_project(o,longaxis=2,offset=(0,0),scale=1.):
    for layer in list(o.data.uv_layers):
        if layer.name not in ('UV0','UV1'):o.data.uv_layers.remove(layer)
    uv=o.data.uv_layers.get('UV0') or o.data.uv_layers.new(name='UV0')
    uv.active_render=True;o.data.uv_layers.active=uv
    for f in o.data.polygons:
        ax=max(range(3),key=lambda i:abs(f.normal[i]));other=[i for i in range(3) if i!=longaxis]
        transverse=next((i for i in other if i!=ax),other[0])
        for k in f.loop_indices:
            p=o.data.vertices[o.data.loops[k].vertex_index].co
            if ax==longaxis:coords=(p[other[0]]/.24+.5,p[other[1]]/.24+.5)
            else:coords=(p[transverse]/scale+offset[0],p[longaxis]/(scale*2)+offset[1])
            uv.data[k].uv=coords
def soften(o,width,segments=3):
    m=o.modifiers.new('Tool worn arris','BEVEL');m.width=width/100;m.segments=segments;m.limit_method='ANGLE';m.angle_limit=.6
    apply(o,m)
    for p in o.data.polygons:p.use_smooth=True
    # Split the broad plane from its bevel while retaining curved corner shading.
    bm=bmesh.new();bm.from_mesh(o.data)
    for e in bm.edges:
        if e.is_manifold:e.smooth=e.calc_face_angle()<math.radians(50)
    bm.to_mesh(o.data);bm.free()
    n=o.modifiers.new('Face weighted corner normals','WEIGHTED_NORMAL');n.keep_sharp=True;n.weight=40;apply(o,n)
def cube(name,c,s,mat='Oak',bevel=.2,collision=False):
    bpy.ops.mesh.primitive_cube_add(size=1,location=v(c));o=bpy.context.object;o.name=name;o.dimensions=Vector(s)/100
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(M[mat]);parts.append(o)
    if bevel:soften(o,bevel)
    uv_project(o,max(range(3),key=lambda i:s[i]),(rng.random(),rng.random()),1.)
    if collision:colliders.append((c,s,0))
    return o
def plank(name,c,s,mat='Oak',wear=.13,collision=True):
    axis=max(range(3),key=lambda i:s[i]);cross=[i for i in range(3) if i!=axis]
    a,b=s[cross[0]]/2,s[cross[1]]/2;r=min(.36,a*.12,b*.22)
    ring=[(-a+r,-b),(a-r,-b),(a,-b+r),(a,b-r),(a-r,b),(-a+r,b),(-a,b-r),(-a,-b+r)]
    verts=[];faces=[];rings=max(3,min(12,int(s[axis]/14)))
    for j in range(rings+1):
        t=j/rings;drift=math.sin(t*math.pi)*rng.uniform(-wear,wear)
        for k,(aa,bb) in enumerate(ring):
            p=[0.,0.,0.];p[axis]=(t-.5)*s[axis]
            p[cross[0]]=aa+drift+rng.uniform(-wear*.35,wear*.35)
            p[cross[1]]=bb+math.sin(t*math.pi)*rng.uniform(-wear*.35,wear*.35)
            # Standing surfaces retain exact contact at both terminal planes.
            verts.append(p)
    for j in range(rings):
        for k in range(8):faces.append((j*8+k,j*8+(k+1)%8,(j+1)*8+(k+1)%8,(j+1)*8+k))
    faces.extend([tuple(reversed(range(8))),tuple(rings*8+k for k in range(8))])
    o=mesh(name,verts,faces,mat);o.location=v(c)
    if mat=='Oak':
        o.data.materials.append(M['Endgrain'])
        for p in o.data.polygons[-2:]:p.material_index=1
    uv_project(o,axis,(rng.random()*.7,rng.random()*.7),1.)
    if collision:colliders.append((c,s,0))
    return o
def beam(name,a,b,width,depth,mat='Oak'):
    direction=v(b)-v(a);o=plank(name,(0,0,0),(width,depth,direction.length*100),mat,collision=False)
    o.rotation_mode='QUATERNION';o.rotation_quaternion=direction.to_track_quat('Z','Y');o.location=(v(a)+v(b))/2
    return o
def cylinder(name,c,r,depth,mat='Iron',axis='Y',vertices=12):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices,radius=r/100,depth=depth/100,location=v(c))
    o=bpy.context.object;o.name=name;parts.append(o);o.data.materials.append(M[mat])
    if axis=='Y':o.rotation_euler.x=math.pi/2
    if axis=='X':o.rotation_euler.y=math.pi/2
    soften(o,min(.13,r*.18),2);uv_project(o,2)
    return o
def peg(c,axis='Y'):return cylinder('End grain oak drawbore peg',c,.63,1.6,'Endgrain',axis,10)
def nail(c,axis='Z'):return cylinder('Hand forged square-ish nail',c,.43,.42,'Iron',axis,6)
def tube(name,coords,r=.16,mat='Iron',cyclic=False):
    cu=bpy.data.curves.new(name,'CURVE');cu.dimensions='3D';cu.resolution_u=1;cu.bevel_depth=r/100;cu.bevel_resolution=2
    cu.use_fill_caps=True;s=cu.splines.new('POLY');s.points.add(len(coords)-1)
    for p,co in zip(s.points,coords):p.co=(*v(co),1)
    s.use_cyclic_u=cyclic;o=bpy.data.objects.new(name,cu);bpy.context.collection.objects.link(o);o.data.materials.append(M[mat])
    active(o);bpy.ops.object.convert(target='MESH')
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=bm.verts,dist=.0000001);bm.to_mesh(o.data);bm.free()
    parts.append(o);uv_project(o,2);return o
def cloth_volume(name,c,s,mat,expo=.28):
    verts=[];faces=[];nx=72;ny=28
    def sp(a,e):return math.copysign(abs(a)**e,a)
    for j in range(1,ny):
        lat=-math.pi/2+j*math.pi/ny
        for i in range(nx):
            t=i*math.tau/nx
            xx=s[0]/2*sp(math.cos(t),expo)*sp(math.cos(lat),expo)
            yy=s[1]/2*sp(math.sin(t),expo)*sp(math.cos(lat),expo)
            zz=s[2]/2*sp(math.sin(lat),.66)
            fold=(math.sin(xx*.48+yy*.18)+.5*math.sin(yy*.84-xx*.2))*.17
            zz+=fold*abs(math.cos(lat))**3
            verts.append((c[0]+xx,c[1]+yy,c[2]+zz))
    for j in range(ny-2):
        for i in range(nx):faces.append((j*nx+i,j*nx+(i+1)%nx,(j+1)*nx+(i+1)%nx,(j+1)*nx+i))
    lo=len(verts);verts.append((c[0],c[1],c[2]-s[2]/2));hi=len(verts);verts.append((c[0],c[1],c[2]+s[2]/2))
    for i in range(nx):faces.extend([(lo,(i+1)%nx,i),(hi,(ny-2)*nx+i,(ny-2)*nx+(i+1)%nx)])
    o=mesh(name,verts,faces,mat);uv_project(o,1,scale=.42)
    for f in o.data.polygons:f.use_smooth=True
    return o
def finish(name):
    global parts,colliders
    full='SM_Village'+name
    bpy.ops.object.select_all(action='DESELECT')
    for p in parts:p.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join();o=parts[0];o.name=full
    o.data.transform(o.matrix_world);o.matrix_world=Matrix.Identity(4)
    # Every component exports the same channel zero; signed boards additionally carry a unique paint UV.
    if not o.data.uv_layers.get('UV1'):
        uv=o.data.uv_layers.new(name='UV1')
        for k,d in enumerate(o.data.uv_layers['UV0'].data):uv.data[k].uv=d.uv
    o.data.uv_layers.active_index=0
    bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.dissolve_degenerate(bm,dist=.0000005,edges=list(bm.edges));bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(o.data);bm.free()
    triangulate=o.modifiers.new('Explicit game triangles','TRIANGULATE');triangulate.keep_custom_normals=True;apply(o,triangulate)
    o.data.calc_loop_triangles()
    bad=[p.index for p in o.data.polygons if p.area<1e-12]
    bm=bmesh.new();bm.from_mesh(o.data);open_edges=sum(not e.is_manifold for e in bm.edges);bm.free()
    assert not bad,(name,'zero area',bad[:8])
    assert not open_edges,(name,'open edges',open_edges)
    lods=[]
    for lod,ratio in [(0,1),(1,.50),(2,.22)]:
        q=o if lod==0 else o.copy()
        if lod:q.data=o.data.copy();bpy.context.collection.objects.link(q);q.name=full+f'_LOD{lod}'
        if lod:
            m=q.modifiers.new('Silhouette LOD','DECIMATE');m.ratio=ratio;m.delimit={'MATERIAL','UV'};apply(q,m)
        # Solidify's narrow cloth rim inherits coincident UVs. Give only those
        # triangles a metric planar unwrap, leaving the simulated coverlet UV intact.
        uv=q.data.uv_layers['UV0']
        for face in q.data.polygons:
            loops=list(face.loop_indices)
            if len(loops)!=3:continue
            a,b,c=[uv.data[k].uv for k in loops]
            if abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))>=1e-11:continue
            axis=max(range(3),key=lambda i:abs(face.normal[i]));axes=[i for i in range(3) if i!=axis]
            for k in loops:
                co=q.data.vertices[q.data.loops[k].vertex_index].co;uv.data[k].uv=(co[axes[0]]/.42,co[axes[1]]/.42)
        active(q);q.data.calc_loop_triangles()
        path=AUTH/(full+(f'_LOD{lod}' if lod else '')+'.fbx')
        bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',mesh_smooth_type='FACE',use_tspace=True,bake_anim=False,add_leaf_bones=False)
        lods.append({'level':lod,'triangles':len(q.data.loop_triangles),'file':str(path)})
        if lod:bpy.data.objects.remove(q,do_unlink=True)
    points=[vv.co for vv in o.data.vertices]
    bounds=[[min(p[i] for p in points)*100 for i in range(3)],[max(p[i] for p in points)*100 for i in range(3)]]
    manifest.append(dict(name=full,lods=lods,materials=[m.name for m in o.data.materials],bounds_blender_cm=bounds,open_edges=open_edges,zero_area_faces=len(bad),colliders=colliders))
    assets[name]=o;parts=[];colliders=[]
    o.hide_render=True;o.hide_set(True)

# JOINERY: vertical feet bear on z=0, rails enter their posts and are drawbored.
for x in (-51,51):
    for y in (-26,26):
        plank('Table upright',(x,y,35.75),(7,7,71.5))
        peg((x,y-3.7,62));peg((x+3.7,y,24),'X')
for y in (-26,26):plank('Long pegged apron',(0,y,65.5),(109,4.5,12))
for x in (-51,51):
    plank('Short end apron',(x,0,65.5),(4.5,55,12))
    plank('Trestle foot rail',(x,0,24),(5,55,7))
plank('Central through-tenon stretcher',(0,0,24),(111,5,7))
for x in (-55,55):plank('Stretcher wedge',(x,0,24),(1.5,7.4,9),collision=False)
for j in range(4):
    yy=(j-1.5)*17.8;plank('Hand planed tabletop',(0,yy,74),(130,17.5,5),wear=.15)
    for xx in (-50,50):nail((xx,yy,76.5))
finish('OakTable')

for x in (-70,70):
    for y in (-17,17):plank('Rack upright',(x,y,85),(6,6,170))
for z in (12,64,116,164):
    for x in (-70,70):plank('Shelf housed bearer',(x,0,z-3.5),(5,40,4))
    for y in (-10,10):plank('Shelf plank',(0,y,z),(150,19.5,3))
    for x in (-70,70):
        for y in (-17,17):peg((x,y-3.15,z-4))
beam('Rear anti-racking diagonal',(-70,20,9),(70,20,158),6,2.5)
beam('Left side brace',(-72,-17,20),(-72,17,62),3,3)
beam('Right side brace',(72,-17,118),(72,17,159),3,3)
finish('OakShelf')

# Bed legs now align to the 106 x 205 frame (previous draft transposed width/depth).
for x in (-49,49):
    for y in (-96,96):
        height=78 if y>0 else 46
        plank('Bed corner post',(x,y,height/2),(7,7,height))
        peg((x,y+(-3.65 if y<0 else 3.65),32));peg((x+3.65,y,32),'X')
for x in (-49,49):plank('Rebated side rail',(x,0,32),(7,199,13))
for y in (-96,96):plank('End rail',(0,y,32),(103,6,13))
for j in range(12):plank('Mattress support slat',(0,-85+j*15.5,37),(96,12,3),wear=.07,collision=False)
for z in (53,68):plank('Headboard plank',(0,96,z),(102,4,13))
plank('Footboard',(0,-96,41),(102,4,8))
cloth_volume('Straw tick mattress',(0,0,45),(94,190,13),'Linen',.24)
cloth_volume('Compressed linen pillow',(0,65,56),(63,37,10),'Linen',.42)
for cx,cy,cz,sx,sy,expo in [(0,0,45,47,95,.24),(0,65,56,31.5,18.5,.42)]:
    points=[]
    for i in range(128):
        t=i*math.tau/128
        points.append((cx+sx*math.copysign(abs(math.cos(t))**expo,math.cos(t)),cy+sy*math.copysign(abs(math.sin(t))**expo,math.sin(t)),cz))
    tube('Linen seam piping',points,.10,'Linen',cyclic=True)
for j in range(3):
    # Ticking's shallow tufts are deliberately sparse and do not become cartoon buttons.
    for xx in (-26,26):cylinder('Mattress tuft',(xx,40+j*20,51.45),.6,.18,'Linen','Z',8)
def drape(x,y):
    side=max(0,abs(x)-43);foot=max(0,-y-85)
    z=52.0-side*1.55-foot*1.18
    fold=(math.sin(x*.37+y*.065)+.46*math.sin(x*.78-y*.11))*(.5+.028*side)
    fold+=.9*math.exp(-((y-26)/5.8)**2)
    return z+fold
verts=[];faces=[];nx,ny=48,64
bed_collision_parts=list(parts)
for support in bed_collision_parts:
    support.modifiers.new('Offline cloth contact','COLLISION')
    support.collision.thickness_outer=.003;support.collision.thickness_inner=.001;support.collision.cloth_friction=12
for j in range(ny+1):
    yy=-112+j*148/ny
    for i in range(nx+1):
        xx=-57+i*114/nx;verts.append((xx,yy,64+math.sin(xx*.27+yy*.09)*.24))
for j in range(ny):
    for i in range(nx):
        a=j*(nx+1)+i;faces.append((a,a+1,a+nx+2,a+nx+1))
o=mesh('Continuous wool coverlet with gravity folds',verts,faces,'Blanket');uv_project(o,1,scale=.42)
sim=o.modifiers.new('Offline gravity cloth','CLOTH');sim.settings.quality=8;sim.settings.mass=.24
sim.settings.tension_stiffness=18;sim.settings.compression_stiffness=18;sim.settings.shear_stiffness=8;sim.settings.bending_stiffness=.35
sim.collision_settings.collision_quality=5;sim.collision_settings.distance_min=.003;sim.collision_settings.use_self_collision=True;sim.collision_settings.self_distance_min=.003
sim.point_cache.frame_end=100
for frame in range(1,91):bpy.context.scene.frame_set(frame)
deps=bpy.context.evaluated_depsgraph_get();frozen=bpy.data.meshes.new_from_object(o.evaluated_get(deps),depsgraph=deps)
o.modifiers.clear();o.data=frozen
for support in bed_collision_parts:
    for mod in list(support.modifiers):
        if mod.type=='COLLISION':support.modifiers.remove(mod)
bpy.context.scene.frame_set(1)
def frozen_point(index):
    q=o.data.vertices[index].co;return (q.x*100,-q.y*100,q.z*100+.06)
for edge in ([j*(nx+1) for j in range(ny+1)],[j*(nx+1)+nx for j in range(ny+1)],list(range(nx+1))):
    tube('Coverlet stitched hem',[frozen_point(i) for i in edge],.075,'Blanket')
for p in o.data.polygons:p.use_smooth=True
m=o.modifiers.new('Woven thickness','SOLIDIFY');m.thickness=.0018;apply(o,m)
colliders.append(((0,0,45),(96,192,16),0))
finish('TimberBed')

for x in (-15,15):
    for y in (-13,13):plank('Stool leg',(x,y,21),(5,5,42))
for y in (-13,13):plank('Stool pegged side rail',(0,y,32),(35,4,7));plank('Low stretcher',(0,y,12),(35,3,4))
for x in (-15,15):plank('Cross brace',(x,0,12),(3,30,4))
for y in (-10,10):plank('Worn stool seat',(0,y,44),(46,19.6,4),wear=.19,collision=False)
# The narrow visual seam between the two boards is part of the sitting surface.
colliders.append(((0,0,44),(46,39.6,4),0))
for x in (-15,15):
    for y in (-13,13):peg((x,y-2.8,32));nail((x,y,46))
finish('OakStool')

# Stacked blooms: broad flat top/bottom maintain direct load-bearing contact.
for row in range(3):
    for col in range(4-row):
        xx=(col-(3-row)/2)*7.5
        o=plank('Hammered iron billet',(xx,rng.uniform(-2,2),2+row*4),(7.7,68-rng.uniform(0,7),4),'Iron',wear=.055,collision=False)
colliders.append(((0,0,6),(31,72,12),0));finish('IronStock')

# Deterministic gravity-settled broken timber. Convex-hull collision is baked offline.
for i in range(6):
    o=plank('Split discarded board',(rng.uniform(-18,18),rng.uniform(-9,9),24+i*12),(rng.uniform(58,84),rng.uniform(9,15),3),'Oak',wear=.32,collision=False)
    o.rotation_euler=(rng.uniform(-.08,.08),rng.uniform(-.09,.09),rng.uniform(-.5,.5))
    active(o);bpy.ops.rigidbody.object_add();o.rigid_body.collision_shape='CONVEX_HULL';o.rigid_body.use_margin=True;o.rigid_body.collision_margin=.001;o.rigid_body.friction=.85;o.rigid_body.restitution=0
ground=cube('Temporary settle plane',(0,0,-3),(600,600,6),collision=False);parts.remove(ground)
active(ground);bpy.ops.rigidbody.object_add();ground.rigid_body.type='PASSIVE';ground.rigid_body.friction=.85
bpy.context.scene.rigidbody_world.substeps_per_frame=8;bpy.context.scene.rigidbody_world.solver_iterations=30
bpy.context.scene.rigidbody_world.point_cache.frame_end=200
for frame in range(1,181):bpy.context.scene.frame_set(frame)
deps=bpy.context.evaluated_depsgraph_get();transforms={o:o.evaluated_get(deps).matrix_world.copy() for o in parts}
for o,t in transforms.items():active(o);bpy.ops.rigidbody.object_remove();o.matrix_world=t
bpy.data.objects.remove(ground,do_unlink=True);bpy.context.scene.frame_set(1)
floor=min((o.matrix_world@q.co).z for o in parts for q in o.data.vertices)
for o in parts:o.location.z-=floor
finish('AbandonedTimber')

# Six dressed local grey-stone flags, seams reveal thickness; central feet land at z=6.
for x in (-80,0,80):
    for y in (-45,45):
        o=cube('Dressed hearth flag',(x,y,3),(79.4,89.4,6),'Stone',.65,collision=True)
        # Chips sit on the perimeter silhouette, leaving the bearing face flat.
        bm=bmesh.new();bm.from_mesh(o.data)
        for vv in bm.verts:
            if abs(vv.co.z)<.028:
                vv.co.x+=rng.uniform(-.0009,.0009);vv.co.y+=rng.uniform(-.0009,.0009)
        bmesh.ops.recalc_face_normals(bm,faces=bm.faces);bm.to_mesh(o.data);bm.free()
        uv=o.data.uv_layers['UV0']
        for f in o.data.polygons:
            axis=max(range(3),key=lambda i:abs(f.normal[i]));xy=[i for i in range(3) if i!=axis]
            for k in f.loop_indices:
                p=o.data.vertices[o.data.loops[k].vertex_index].co;uv.data[k].uv=(p[xy[0]],p[xy[1]])
finish('HearthPad')

for name,width,height,mat in [('BlacksmithSign',100,44,'Sign'),('ClosedPlaque',48,20,'Closed')]:
    count=3 if name=='BlacksmithSign' else 2
    for j in range(count):
        z=-height/2+(j+.5)*height/count
        o=plank('Painted split oak board',(0,0,z),(width,3.8,height/count-.22),mat,wear=.1,collision=False)
        o.data.materials.append(M['Oak'])
        for p in o.data.polygons:
            if p.normal.y<.8:p.material_index=1
        bpy.context.view_layer.update()
        unique=o.data.uv_layers.new(name='UV1')
        for p in o.data.polygons:
            for k in p.loop_indices:
                pos=o.matrix_world@o.data.vertices[o.data.loops[k].vertex_index].co
                unique.data[k].uv=(.5-pos.x*100/width,pos.z*100/height+.5)
    for xx in (-width*.38,width*.38):
        cube('Rear oak batten',(xx,2.8,0),(4,2.2,height-2),'Oak',.24)
        for z in (-height*.35,height*.35):nail((xx,-2.05,z),'Y')
    if name=='BlacksmithSign':
        # Forged straps, eyes and two wall brackets reach the actual masonry behind the sign.
        for xx in (-34,34):
            cube('Forged hanger strap',(xx,2.0,27),(2.2,.6,15),'Iron',.12)
            tube('Hanger eye',[(xx+2.1*math.cos(t),1.8,35+3*math.sin(t)) for t in [i*math.tau/24 for i in range(24)]],.46,cyclic=True)
            tube('Forged wall bracket',[(xx,2,38),(xx,22,38),(xx,24,38),(xx,24,28)],.72)
            cube('Wall mounting plate',(xx,24,31),(5,.7,18),'Iron',.18)
            for z in (24,38):nail((xx,23.5,z),'Y')
        # Real relief emblem, a compact village blacksmith anvil; no floating decal.
        poly=[(-45,4),(-29,4),(-23,1),(-31,-2),(-33,-2),(-33,-8),(-29,-10),(-44,-10),(-40,-8),(-40,-2),(-44,-1)]
        vv=[(-x,y,z+4) for y in (-2.5,-3.3) for x,z in poly];n=len(poly)
        ff=[tuple(reversed(range(n))),tuple(n+i for i in range(n))]+[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        emblem=mesh('Raised wrought anvil crest',vv,ff,'Iron');soften(emblem,.18,2);uv_project(emblem,0)
    else:
        for xx in (-16,16):tube('Plaque leather-dark iron wire',[(xx,2,7),(xx,3,13),(xx,10,13),(xx,10,8)],.2)
    finish(name)

for i,(name,o) in enumerate(assets.items()):
    o.hide_render=False;o.hide_set(False);o.location=((i%3)*3.1,(i//3)*2.8,0)
(OUT/'model-manifest.json').write_text(json.dumps({'assets':manifest,'seed':1711172,'units':'author cm / Blender m / FBX metre','lod_policy':'authored deterministic reduction; material and UV borders retained','style':'weathered rural chapel timber, forged iron, unbleached linen and local grey stone'},indent=2),encoding='utf-8')
bpy.ops.wm.save_as_mainfile(filepath=str(AUTH/'VillageFurniture_R2.blend'))
print('ART_PASS_AUTHORED',[(r['name'],r['lods'][0]['triangles']) for r in manifest])
