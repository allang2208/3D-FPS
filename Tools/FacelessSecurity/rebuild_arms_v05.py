"""Rebuild arm garments with explicit limb topology and anatomical weights."""
import bpy,bmesh,json,math
import numpy as np
from pathlib import Path
from mathutils import Matrix,Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
BASE=Path('D:/FPS3D/FPSGAME/SourceAssets/FacelessSecurity20261008');ROOT=BASE/'V05'
for d in ['Authoring','Delivery','Motion','Logs']:(ROOT/d).mkdir(parents=True,exist_ok=True)
prefix=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/author_character.py').read_text(encoding='utf-8').split('# Appended to the native skeleton')[0]
ns={};exec(compile(prefix,'security_fit','exec'),ns)
fit=ns['matrix'];norm=ns['norm'];TARGET=ns['TARGET'];body_tree=ns['body_bvh'];body_sample=ns['body_sample'];torso_weights=ns['torso_weights']
bpy.ops.wm.open_mainfile(filepath=str(BASE/'V04/Authoring/FacelessSecurity_V04.blend'))
rig=bpy.data.objects['root'];rig.animation_data_clear()
for pb in rig.pose.bones:pb.matrix_basis=Matrix.Identity(4)
body=bpy.data.objects['Security_CompleteBody'];display=bpy.data.objects['Security_OutfitBody'];scene=bpy.context.scene
report={'source':'V04','removed':[],'new_parts':[],'body_arm_vertices_rebound':{},'game_tested':False,'rendered':False}
stored={}
def ease(a,b,x):
    t=max(0.,min(1.,(x-a)/(b-a)));return t*t*(3-2*t)
def mix(a,b,t):
    result={n:w*(1-t) for n,w in a.items()}
    for n,w in b.items():result[n]=result.get(n,0)+w*t
    return norm(result)
def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o
def apply(o,m):active(o);bpy.ops.object.modifier_apply(modifier=m.name)
def read_weights(o):
    names={g.index:g.name for g in o.vertex_groups}
    return [{names[g.group]:g.weight for g in v.groups} for v in o.data.vertices]
def put_weights(o,rows):
    o.vertex_groups.clear()
    for n in sorted({n for w in rows for n in w}):o.vertex_groups.new(name=n)
    for v,ws in zip(o.data.vertices,rows):
        for n,w in ws.items():o.vertex_groups[n].add([v.index],w,'REPLACE')
def unbind(o):
    ws=read_weights(o);matrices=[fit(w) for w in ws];normals=[n.vector.copy() for n in o.data.corner_normals]
    mapped=[(matrices[l.vertex_index].to_3x3().inverted().transposed()@n).normalized() for l,n in zip(o.data.loops,normals)]
    for v,m in zip(o.data.vertices,matrices):v.co=m@v.co
    o.parent=None;o.matrix_world=Matrix.Identity(4);o.modifiers.clear();o.data.update();o.data.normals_split_custom_set(mapped)
    stored[o.name]=ws
def bind(o,rows):
    matrices=[fit(w) for w in rows];normals=[n.vector.copy() for n in o.data.corner_normals]
    mapped=[(matrices[l.vertex_index].to_3x3().transposed()@n).normalized() for l,n in zip(o.data.loops,normals)]
    put_weights(o,rows)
    for v,m in zip(o.data.vertices,matrices):v.co=m.inverted()@v.co
    o.data.update();o.data.normals_split_custom_set(mapped);o.parent=rig;o.matrix_parent_inverse=rig.matrix_world.inverted()
    mod=o.modifiers.new('NativeHumanoidSkin','ARMATURE');mod.object=rig
def surface(o):
    o.data.calc_loop_triangles();p=[v.co.copy() for v in o.data.vertices];t=[tuple(f.vertices) for f in o.data.loop_triangles]
    return BVHTree.FromPolygons(p,t,all_triangles=True),p,t
def sample(p,surf,rows):
    tree,points,tri=surf;hit=tree.find_nearest(p);ids=tri[hit[2]]
    abc=barycentric_transform(hit[0],*(points[i] for i in ids),Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
    abc=[max(0.,float(c)) for c in abc];total=sum(abc);result={}
    for i,c in zip(ids,abc):
        for n,w in rows[i].items():result[n]=result.get(n,0)+w*c/total
    return norm(result)

for o in list(scene.objects):
    if o.type=='MESH' and not o.name.startswith('Security_Boot'):unbind(o)
old_shirt=surface(bpy.data.objects['Security_Shirt_Continuous'])
old_pants=surface(bpy.data.objects['Security_Trousers_Continuous'])
old_cuffs={s:surface(bpy.data.objects['Security_Cuff_'+s]) for s in ['l','r']}
for name in ['Security_Shirt_Continuous','Security_Cuff_l','Security_Cuff_r']:
    report['removed'].append(name);bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
uniform=bpy.data.materials['Security_Uniform']

def arm_weights(p,side,skin=False,original=None):
    s,e,w=[Vector(TARGET[side][n]) for n in ['shoulder','elbow','wrist']]
    upper=(e-s).normalized();lower=(w-e).normalized()
    # Only shoulder/clavicle and same-side upperarm/lowerarm/hand can drive
    # sleeves. Pelvis, opposite limbs and fingers cannot enter this field.
    elbow=ease(-.065,.065,(p-e).dot((w-s).normalized()))
    rows=mix({'upperarm_'+side:1.},{'lowerarm_'+side:1.},elbow)
    root=(1-ease(-.055,.040,(p-s).dot(upper)))*.45
    if root:rows=mix(rows,{'clavicle_'+side:1.},root)
    wrist=ease(-.035,.018,(p-w).dot(lower))
    hand={'hand_'+side:1.}
    if skin and original:
        keep={n:v for n,v in original.items() if n.endswith('_'+side) and n.startswith(('hand','thumb','index','middle','ring','pinky'))}
        if keep:hand=norm(keep)
    return mix(rows,hand,wrist)

def make(name,verts,faces,weight_function,uvs=None,thickness=.0025):
    me=bpy.data.meshes.new(name);me.from_pydata(verts,[],faces);me.update()
    o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);me.materials.append(uniform)
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
    layer=me.uv_layers.new(name='UVMap')
    for f in me.polygons:
        f.use_smooth=True
        for li in f.loop_indices:
            vi=me.loops[li].vertex_index;layer.data[li].uv=uvs[vi] if uvs else (me.vertices[vi].co.x/.2,me.vertices[vi].co.z/.2)
    put_weights(o,[weight_function(v.co) for v in me.vertices])
    if thickness:
        # Assign weights before thickness so paired inner/outer vertices
        # inherit identical attachment data at every sewn edge.
        m=o.modifiers.new('MatchedInnerOuterShell','SOLIDIFY');m.thickness=thickness;m.offset=-1;apply(o,m)
    report['new_parts'].append(name);return o

# A closed torso shell has no topology running down into either forearm.
# The overlapping sleeve caps cover the shoulder seam and underarm gusset.
N=96;zs=np.linspace(1.110,1.645,49);radii=[]
for z in zs:
    c=Vector((0,.020,float(z)));row=[]
    rx=float(np.interp(z,[1.11,1.22,1.36,1.45,1.53,1.58,1.645],[.214,.210,.228,.238,.244,.213,.120]))
    for i in range(N):
        t=2*math.pi*i/N;d=Vector((math.sin(t),-math.cos(t),0));h=body_tree.ray_cast(c,d,.37)
        limit=1/math.sqrt((d.x/rx)**2+(d.y/.180)**2)
        r=min((h[0]-c).length,limit) if h[0] is not None else limit
        row.append(r+.014)
    radii.append(row)
radii=np.array(radii)
for _ in range(4):radii=(2*radii+np.roll(radii,1,1)+np.roll(radii,-1,1))/4
v=[];uv=[]
for j,z in enumerate(zs):
    for i in range(N+1):
        t=2*math.pi*i/N;r=float(radii[j,i%N]);v.append((math.sin(t)*r,.020-math.cos(t)*r,float(z)))
        uv.append((t*.21/.2,float(z)/.2))
shirt=make('Security_Shirt_Torso',v,[(j*(N+1)+i,j*(N+1)+i+1,(j+1)*(N+1)+i+1,(j+1)*(N+1)+i) for j in range(len(zs)-1) for i in range(N)],torso_weights,uv)

for side in ['l','r']:
    s,e,w=[Vector(TARGET[side][n]) for n in ['shoulder','elbow','wrist']]
    upper=(e-s).normalized();lower=(w-e).normalized();l1=(e-s).length;l2=(w-e).length
    rows=[]
    for q in np.linspace(-.060,l1+l2-.020,65):
        if q<=l1:
            c=s+upper*float(q);axis=upper.lerp(lower,ease(l1-.06,l1+.06,q)).normalized()
        else:c=e+lower*float(q-l1);axis=upper.lerp(lower,ease(l1-.06,l1+.06,q)).normalized()
        front=Vector((0,-1,0));front=(front-axis*front.dot(axis)).normalized();side_axis=axis.cross(front).normalized()
        expected=float(np.interp(q,[-.06,0,.13,l1,l1+l2],[.012,.090,.082,.073,.052]))
        rr=[]
        for i in range(48):
            t=2*math.pi*i/48;d=front*math.cos(t)+side_axis*math.sin(t)
            h=body_tree.ray_cast(c,d,.12)
            radius=(h[0]-c).length+.012 if h[0] is not None else expected
            if q<0:radius=expected
            else:radius=max(expected*.82,min(expected*1.12,radius))
            rr.append(radius)
        rows.append((c,axis,front,side_axis,rr,q))
    rr=np.array([x[4] for x in rows])
    for _ in range(4):
        rr=(2*rr+np.roll(rr,1,1)+np.roll(rr,-1,1))/4
        rr[1:-1]=(rr[:-2]+2*rr[1:-1]+rr[2:])/4
    v=[];uv=[];N=48
    for j,(c,axis,front,around,_,q) in enumerate(rows):
        for i in range(N+1):
            t=2*math.pi*i/N;radius=float(rr[j,i%N])
            wrinkle=.0018*math.sin((q-l1)*90+t*.6)*math.exp(-((q-l1)/.075)**2)
            v.append(tuple(c+(front*math.cos(t)+around*math.sin(t))*(radius+wrinkle)))
            uv.append((t*.075/.2,float(q)/.2))
    faces=[(j*(N+1)+i,j*(N+1)+i+1,(j+1)*(N+1)+i+1,(j+1)*(N+1)+i) for j in range(len(rows)-1) for i in range(N)]
    faces.append(tuple(reversed(range(N))))
    make('Security_Sleeve_'+side,v,faces,lambda p,side=side:arm_weights(p,side),uv)
    v=[];uv=[];front=Vector((0,-1,0));front=(front-lower*front.dot(lower)).normalized();around=lower.cross(front).normalized()
    for q in np.linspace(-.067,-.002,10):
        c=w+lower*float(q);r=float(np.interp(q,[-.067,-.002],[.058,.053]))
        for i in range(N+1):
            t=2*math.pi*i/N;v.append(tuple(c+(front*math.cos(t)+around*math.sin(t))*r));uv.append((t*.055/.2,float(q)/.2))
    make('Security_Cuff_'+side,v,[(j*(N+1)+i,j*(N+1)+i+1,(j+1)*(N+1)+i+1,(j+1)*(N+1)+i) for j in range(9) for i in range(N)],lambda p,side=side:arm_weights(p,side),uv,.002)

def leg_weights(p):
    side_mix=ease(-.055,.055,p.x) if p.z>.72 else (1. if p.x>=0 else 0.)
    thigh={'thigh_l':side_mix,'thigh_r':1-side_mix};calf={'calf_l':side_mix,'calf_r':1-side_mix}
    foot={'foot_l':side_mix,'foot_r':1-side_mix}
    row=mix({'pelvis':1.},thigh,1-ease(.89,1.08,p.z));row=mix(row,calf,1-ease(.515,.655,p.z))
    return mix(row,foot,1-ease(.085,.175,p.z))
pants=bpy.data.objects['Security_Trousers_Continuous'];put_weights(pants,[leg_weights(v.co) for v in pants.data.vertices])
parents={n:(bpy.data.objects[n],surface(bpy.data.objects[n]),read_weights(bpy.data.objects[n])) for n in ['Security_Shirt_Torso','Security_Sleeve_l','Security_Sleeve_r','Security_Cuff_l','Security_Cuff_r','Security_Trousers_Continuous']}

# Preserve full skin/fingers, but remove any torso influence from the actual
# covered forearms. The source GLB and earlier full-body revisions remain.
for o in [body,display]:
    changed=0;rows=[]
    for v,original in zip(o.data.vertices,stored[o.name]):
        p=v.co;side='l' if p.x>=0 else 'r';s,e,w=[Vector(TARGET[side][n]) for n in ['shoulder','elbow','wrist']]
        a=e if p.z<e.z else s;b=w if p.z<e.z else e
        t=max(0.,min(1.,(p-a).dot(b-a)/(b-a).length_squared));distance=(p-a.lerp(b,t)).length
        if (.74<p.z<1.44 and abs(p.x)>.255 and distance<.145) or (.74<p.z<1.08 and abs(p.x)>.31 and distance<.22):
            rows.append(arm_weights(p,side,True,original));changed+=1
        else:rows.append(original)
    put_weights(o,rows);report['body_arm_vertices_rebound'][o.name]=changed

for o in list(scene.objects):
    if o.type!='MESH' or o.name.startswith('Security_Boot') or o in [body,display] or o.name in parents:continue
    if o.name.startswith(('Security_Belt','Security_Buckle','Security_DutyBelt')):
        put_weights(o,[{'pelvis':1.}]*len(o.data.vertices));continue
    if o.name=='Security_CollarStand':put_weights(o,[torso_weights(v.co) for v in o.data.vertices]);continue
    side='l' if sum(v.co.x for v in o.data.vertices)>=0 else 'r'
    if o.name.startswith('Security_CuffButton'):
        parent=parents['Security_Cuff_'+side];old_surface=old_cuffs[side]
    elif o.name.startswith(('Security_Trouser','Security_RearPocket')):
        parent=parents['Security_Trousers_Continuous'];old_surface=old_pants
    else:parent=parents['Security_Shirt_Torso'];old_surface=old_shirt
    shifts=[]
    for v in o.data.vertices:
        old=old_surface[0].find_nearest(v.co)[0];new=parent[1][0].find_nearest(old)[0];shifts.append(new-old)
    rigid=any(token in o.name for token in ['Button','Stud','IDPlate','IDLetters','TieClip'])
    if rigid:shifts=[sum(shifts,Vector())/len(shifts)]*len(shifts)
    for v,shift in zip(o.data.vertices,shifts):v.co+=shift
    if rigid:
        center=sum((v.co for v in o.data.vertices),Vector())/len(o.data.vertices);rows=[sample(center,parent[1],parent[2])]*len(o.data.vertices)
    else:rows=[sample(v.co,parent[1],parent[2]) for v in o.data.vertices]
    put_weights(o,rows)

for o in list(scene.objects):
    if o.type=='MESH' and not o.name.startswith('Security_Boot'):bind(o,read_weights(o))
body.hide_set(True);body.hide_render=True
rig.animation_data_create();bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/FacelessSecurity_V05.blend'))
report['sleeve_weight_contract']='Same-side clavicle/upperarm/lowerarm/hand only; no pelvis, spine, fingers or opposite arm. Separate overlapping torso and sleeves, no cross-region faces.'
(ROOT/'arm_rebuild.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
src=Path('D:/FPS3D/FPSGAME/Tools/FacelessSecurity/export_delivery.py').read_text(encoding='utf-8').replace('V01','V05')
exec(compile(src,'export_security_v05','exec'))
