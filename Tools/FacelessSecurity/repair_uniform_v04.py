"""Rebuild the faulty waist/neck details and unify garment attachment weights."""
import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
from mathutils.kdtree import KDTree
from mathutils.geometry import barycentric_transform
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008')
ROOT=BASE/'V04'
for d in ['Authoring','Delivery','Logs']:(ROOT/d).mkdir(parents=True,exist_ok=True)
prefix=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/author_character.py').read_text(encoding='utf-8').split('# Appended to the native skeleton')[0]
ns={};exec(compile(prefix,'security_fit','exec'),ns)
fit=ns['matrix'];normalize=ns['norm'];body_sample=ns['body_sample'];body_tree=ns['body_bvh']
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V03/Authoring/FacelessSecurity_V03.blend'))
rig=bpy.data.objects['root'];rig.animation_data_clear()
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
body=bpy.data.objects['Security_CompleteBody'];display=bpy.data.objects['Security_OutfitBody']
report={'source':'V03','removed':[],'rebuilt':[],'rebound':[],'animation_assets_preserved':True,'game_tested':False,'rendered':False}
old_weights={}
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):active(o);bpy.ops.object.modifier_apply(modifier=m.name)
def smoothstep(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def uv(o):
    layer=o.data.uv_layers.active or o.data.uv_layers.new(name='UVMap')
    for f in o.data.polygons:
        for li in f.loop_indices:
            p=o.data.vertices[o.data.loops[li].vertex_index].co
            layer.data[li].uv=(p.y/.20,p.z/.20) if abs(f.normal.x)>.5 else (p.x/.20,p.z/.20)
        f.use_smooth=True
def make(name,verts,faces,mat,thickness=0):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(mat)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free();uv(o)
    if thickness:
        m=o.modifiers.new('GarmentThickness','SOLIDIFY');m.thickness=thickness;m.offset=-1;apply(o,m)
    report['rebuilt'].append(name);return o

# Work in the original male source pose. Rebinding below preserves that
# surface while changing attachment weights, rather than moving rest vertices
# with weights that belonged to another pose.
for o in list(bpy.context.scene.objects):
    if o.type!='MESH' or o in [body,display] or o.name.startswith('Security_Boot'):continue
    names={g.index:g.name for g in o.vertex_groups}
    ws=[{names[g.group]:g.weight for g in v.groups} for v in o.data.vertices]
    matrices=[fit(w) for w in ws];normals=[n.vector.copy() for n in o.data.corner_normals]
    transformed=[(matrices[lp.vertex_index].to_3x3().inverted().transposed()@n).normalized() for lp,n in zip(o.data.loops,normals)]
    for v,m in zip(o.data.vertices,matrices):v.co=m@v.co
    o.parent=None;o.matrix_world=Matrix.Identity(4);o.modifiers.clear();o.data.update();o.data.normals_split_custom_set(transformed)
    old_weights[o.name]=ws

def smooth_weights(o,kind):
    ws=old_weights[o.name];names=sorted({n for row in ws for n in row}|{'pelvis'});index={n:i for i,n in enumerate(names)}
    w=np.zeros((len(ws),len(names)),dtype=np.float64)
    for i,row in enumerate(ws):
        for n,value in row.items():w[i,index[n]]=value
    for v in o.data.vertices:
        p=v.co
        amount=smoothstep(1.00,1.105,p.z) if kind=='pants' else (1-smoothstep(1.135,1.25,p.z))*(1-smoothstep(.22,.285,abs(p.x)))
        w[v.index]*=1-amount;w[v.index,index['pelvis']]+=amount
    edges=np.array([e.vertices[:] for e in o.data.edges]);a,b=edges[:,0],edges[:,1]
    count=np.bincount(np.r_[a,b],minlength=len(w))[:,None]
    for _ in range(5):
        total=np.zeros_like(w);np.add.at(total,a,w[b]);np.add.at(total,b,w[a]);w=.6*w+.4*total/np.maximum(count,1)
    # Inner/outer shell and coincident seams receive the same nearby weights.
    tree=KDTree(len(w))
    for v in o.data.vertices:tree.insert(v.co,v.index)
    tree.balance();old=w.copy()
    for v in o.data.vertices:
        ids=[i for _,i,_ in tree.find_range(v.co,.0035)]
        if len(ids)>1:w[v.index]=old[ids].mean(0)
    return [normalize({n:float(value) for n,value in zip(names,row)}) for row in w]
shirt=bpy.data.objects['Security_Shirt_Continuous'];pants=bpy.data.objects['Security_Trousers_Continuous']
weights={shirt.name:smooth_weights(shirt,'shirt'),pants.name:smooth_weights(pants,'pants')}

def surface(o):
    o.data.calc_loop_triangles();points=[v.co.copy() for v in o.data.vertices];triangles=[tuple(t.vertices) for t in o.data.loop_triangles]
    return BVHTree.FromPolygons(points,triangles,all_triangles=True),points,triangles
shirt_surface=surface(shirt);pants_surface=surface(pants)
def attached(p,surf,rows):
    tree,points,triangles=surf;hit=tree.find_nearest(p);ids=triangles[hit[2]]
    coeff=barycentric_transform(hit[0],*(points[i] for i in ids),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
    result={};values=[max(0.,float(c)) for c in coeff];total=sum(values)
    for i,c in zip(ids,values):
        for n,w in rows[i].items():result[n]=result.get(n,0)+w*c/total
    return normalize(result)

remove_prefixes=('Security_Belt','Security_DutyBelt','Security_Buckle','Security_Collar','Security_Epaulette','Security_RankBar','Security_PocketFlap')
for o in list(bpy.context.scene.objects):
    if o.name.startswith(remove_prefixes):report['removed'].append(o.name);bpy.data.objects.remove(o,do_unlink=True)
uniform=bpy.data.materials['Security_Uniform'];trim=bpy.data.materials['Security_Trim'];leather=bpy.data.materials['Security_Leather'];metal=bpy.data.materials['Security_Hardware'];thread=bpy.data.materials['Security_Insignia']
forced={}

# Only the trouser waist can define the belt. The old maximum of shirt and
# trousers also hit the hanging sleeves and generated 15 cm radial spikes.
def beltpoint(theta,z,offset=.007):
    center=Vector((0,.020,z));direction=Vector((math.sin(theta),-math.cos(theta),0))
    hit=pants_surface[0].ray_cast(center,direction,.31)
    if hit[0] is None:raise RuntimeError('Missing trouser waist surface')
    return hit[0]+direction*offset
N=96;verts=[tuple(beltpoint(2*math.pi*i/N,float(z))) for z in np.linspace(1.109,1.151,5) for i in range(N)]
faces=[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(4) for i in range(N)]
belt=make('Security_DutyBelt',verts,faces,leather,.003);forced[belt.name]={'pelvis':1.}
for i,t in enumerate([.55,1.08,1.85,2.7,3.58,4.43,5.2,5.73]):
    v=[tuple(beltpoint(t+dx,float(z),.011)) for z in np.linspace(1.105,1.155,6) for dx in [-.025,.025]]
    o=make('Security_BeltKeeper_%02d'%i,v,[(j*2,j*2+1,j*2+3,j*2+2) for j in range(5)],trim,.002);forced[o.name]={'pelvis':1.}
def rounded_box(name,center,size,mat):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=o.modifiers.new('RoundedHardware','BEVEL');mod.width=.0012;mod.segments=3;apply(o,mod)
    transform=o.matrix_world.copy()
    for v in o.data.vertices:v.co=transform@v.co
    o.matrix_world=Matrix.Identity(4);o.data.materials.append(mat);uv(o);report['rebuilt'].append(name);return o
p=beltpoint(0,1.13,.014)
for name,offset,size in [('Top',(0,0,.018),(.052,.004,.005)),('Bottom',(0,0,-.018),(.052,.004,.005)),('Left',(.0235,0,0),(.005,.004,.036)),('Right',(-.0235,0,0),(.005,.004,.036)),('Prong',(0,-.0005,0),(.035,.003,.003))]:
    o=rounded_box('Security_Buckle_'+name,p+Vector(offset),size,metal);forced[o.name]={'pelvis':1.}

# Front panels use the closed body's first front-facing hit, so a missing
# shirt triangle can never send one corner to the back of the character.
def frontpoint(x,z,offset=.022):
    hit=body_tree.ray_cast(Vector((x,-.5,z)),Vector((0,1,0)),.8)
    if hit[0] is None or hit[1].y>.2:raise RuntimeError('No front body surface for garment panel')
    return hit[0]+Vector((0,-offset,0))
for side,sign in [('l',1),('r',-1)]:
    corners=[Vector((sign*.017,1.647)),Vector((sign*.072,1.650)),Vector((sign*.094,1.592)),Vector((sign*.036,1.611))]
    v=[];cols=9;rows=9
    for t in np.linspace(0,1,rows):
        left=corners[0].lerp(corners[3],float(t));right=corners[1].lerp(corners[2],float(t))
        for s in np.linspace(0,1,cols):
            xz=left.lerp(right,float(s));v.append(tuple(frontpoint(xz.x,xz.y,.025)))
    make('Security_CollarLeaf_'+side,v,[(j*cols+i,j*cols+i+1,(j+1)*cols+i+1,(j+1)*cols+i) for j in range(rows-1) for i in range(cols-1)],uniform,.0022)
    # Subdivided flap follows the same shirt weights as the pocket below it.
    x0,x1=sorted([sign*.048,sign*.149]);v=[];cols=13;rows=6
    for t in np.linspace(0,1,rows):
        for s in np.linspace(0,1,cols):
            z=(1-t)*1.476+t*(1.448-.009*(1-abs(2*s-1)))
            v.append(tuple(frontpoint(float(x0+(x1-x0)*s),float(z),.030)))
    make('Security_PocketFlap_'+side,v,[(j*cols+i,j*cols+i+1,(j+1)*cols+i+1,(j+1)*cols+i) for j in range(rows-1) for i in range(cols-1)],uniform,.0018)

N=96;v=[]
for z in np.linspace(1.644,1.667,5):
    c=Vector((0,.005,float(z)))
    for i in range(N):
        t=2*math.pi*i/N;d=Vector((math.sin(t),-math.cos(t),0));hit=body_tree.ray_cast(c,d,.18)
        if hit[0] is None:raise RuntimeError('Missing source neck circumference')
        v.append(tuple(hit[0]+d*.010))
collar=make('Security_CollarStand',v,[(j*N+i,j*N+(i+1)%N,(j+1)*N+(i+1)%N,(j+1)*N+i) for j in range(4) for i in range(N)],uniform,.0022)

def shoulderpoint(x,y,offset=.022):
    hit=body_tree.ray_cast(Vector((x,y,1.90)),Vector((0,0,-1)),.50)
    if hit[0] is None:raise RuntimeError('Missing source shoulder surface')
    return hit[0]+Vector((0,0,offset))
for side,sign in [('l',1),('r',-1)]:
    v=[tuple(shoulderpoint(sign*float(x),float(y))) for x in np.linspace(.135,.255,21) for y in np.linspace(.014,.052,5)]
    make('Security_Epaulette_'+side,v,[(j*5+i,j*5+i+1,(j+1)*5+i+1,(j+1)*5+i) for j in range(20) for i in range(4)],trim,.002)
    for k,x in enumerate([.214,.230]):
        v=[tuple(shoulderpoint(sign*float(xx),float(y),.024)) for xx in [x-.002,x+.002] for y in np.linspace(.016,.050,9)]
        make('Security_RankBar_'+side+'_'+str(k),v,[(i,i+1,i+10,i+9) for i in range(8)],thread,.001)
    rounded_box('Security_EpauletteStud_'+side,shoulderpoint(sign*.146,.033,.025),(.008,.008,.0025),metal)

def bind(o,rows):
    matrices=[fit(ws) for ws in rows];normals=[n.vector.copy() for n in o.data.corner_normals]
    mapped=[(matrices[lp.vertex_index].to_3x3().transposed()@n).normalized() for lp,n in zip(o.data.loops,normals)]
    o.vertex_groups.clear()
    for n in sorted({n for ws in rows for n in ws}):o.vertex_groups.new(name=n)
    for v,m,ws in zip(o.data.vertices,matrices,rows):
        v.co=m.inverted()@v.co
        for n,w in ws.items():o.vertex_groups[n].add([v.index],w,'REPLACE')
    o.data.update();o.data.normals_split_custom_set(mapped);o.parent=rig;o.matrix_parent_inverse=rig.matrix_world.inverted()
    mod=o.modifiers.new('NativeHumanoidSkin','ARMATURE');mod.object=rig;report['rebound'].append(o.name)

# Detail pieces inherit the finished parent garment's continuous weights.
# Sampling bare skin independently allowed trims to pull away during bending.
source_metrics={}
for o in list(bpy.context.scene.objects):
    if o.type!='MESH' or o in [body,display] or o.name.startswith('Security_Boot'):continue
    if o.name in weights:rows=weights[o.name]
    elif o.name in forced:rows=[forced[o.name]]*len(o.data.vertices)
    elif o.name=='Security_CollarStand':rows=[body_sample(v.co) for v in o.data.vertices]
    else:
        is_pants=o.name.startswith(('Security_Trouser','Security_RearPocket'))
        surf=pants_surface if is_pants else shirt_surface;parent=pants if is_pants else shirt
        rows=[attached(v.co,surf,weights[parent.name]) for v in o.data.vertices]
        if any(token in o.name for token in ['Button','Stud','IDPlate','IDLetters','TieClip']):
            center=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices)
            rows=[attached(center,surf,weights[parent.name])]*len(o.data.vertices)
    if o.name in report['rebuilt']:
        p=np.array([v.co for v in o.data.vertices]);edges=np.array([e.vertices[:] for e in o.data.edges])
        source_metrics[o.name]={'vertices':len(p),'bounds':[p.min(0).tolist(),p.max(0).tolist()],'longest_edge_m':float(np.linalg.norm(p[edges[:,0]]-p[edges[:,1]],axis=1).max())}
    bind(o,rows)

# Preserve the existing zombie actions in editable authoring data. UE keeps
# its existing V03 clips; no new retarget or gameplay timing changes occur.
with bpy.data.libraries.load(str(BASE/'V03/Motion/FacelessSecurity_MaleMotion_V03.blend'),link=False) as (data_from,data_to):
    data_to.actions=[name for name in data_from.actions if name.startswith('Security_MaleV03_')]
rig.animation_data_create()
for action in data_to.actions:
    if not action:continue
    track=rig.animation_data.nla_tracks.new();track.name=action.name
    strip=track.strips.new(action.name,1,action);strip.action_slot=action.slots[0];strip.extrapolation='NOTHING';track.mute=True
rig.animation_data.action=None
body.hide_set(True);body.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessSecurity_V04.blend'))
report['source_geometry']=source_metrics;report['clothing_parts']=sum(o.type=='MESH' and o not in [body,display] for o in bpy.context.scene.objects)
(ROOT/'uniform_repair.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/export_delivery.py').read_text(encoding='utf-8').replace('V01','V04')
exec(compile(src,'export_uniform_v04','exec'))
