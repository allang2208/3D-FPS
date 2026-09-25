"""Author a continuous CC0 arm surface against the unchanged M4 reference rig.

Blender background production only; no action playback or preview rendering.
The UE importer retains the original native reference skeleton/inverse binds.
"""
import json, math
from pathlib import Path
import bpy, bmesh
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/ModularOutfit20260924')
OUT=ROOT/'RealisticM4Candidate';OUT.mkdir(exist_ok=True)
DONOR=ROOT/'Donor/BareHands'
native=json.loads((ROOT/'NativeSkin/M4_source.json').read_text(encoding='utf-8'))
skel=json.loads((DONOR/'default.mhskel').read_text(encoding='utf-8'))
coords=[];tex=[];faces=[];uvs=[];group=''
for line in (DONOR/'base.obj').read_text(encoding='utf-8').splitlines():
    t=line.split()
    if not t:continue
    if t[0]=='v':coords.append(Vector((float(t[1]),-float(t[3]),float(t[2])))*.1)
    elif t[0]=='vt':tex.append(tuple(map(float,t[1:3])))
    elif t[0]=='g':group=t[1]
    elif t[0]=='f' and group=='body':
        parts=[s.split('/') for s in t[1:]]
        faces.append([int(s[0])-1 for s in parts]);uvs.append([tex[int(s[1])-1] for s in parts])
sw=[{} for _ in coords]
for n,values in json.loads((DONOR/'default_weights.mhw').read_text(encoding='utf-8'))['weights'].items():
    for i,w in values:sw[i][n]=w

def joint(n):return sum((coords[i] for i in skel['joints'][n]),Vector())/len(skel['joints'][n])
def head(n):return joint(skel['bones'][n]['head'])
def tail(n):return joint(skel['bones'][n]['tail'])
def point(v):return Vector((v[0],-v[1],v[2]))*.01
def ue(v):return [v.x*100,-v.y*100,v.z*100]
def norm(w):
    w=dict(sorted(((n,v) for n,v in w.items() if v>1e-6),key=lambda v:-v[1])[:8])
    total=sum(w.values());return {n:v/total for n,v in w.items()} if total else {}
def frame(a,b,across):
    x=(b-a).normalized();z=x.cross(across).normalized();y=z.cross(x).normalized()
    m=Matrix((x,y,z)).transposed().to_4x4();m.translation=a;return m
def activate(obj):
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj

target={n:point(b['position']) for n,b in native['bones'].items()}
np=[point(v) for v in native['positions']];nw=native['weights']
transforms={};mapping={};fit={}
for s in ('l','r'):
    S=s.upper();wrist='wrist.'+S
    across=head('finger2-1.'+S)-head('finger5-1.'+S)
    ta=target['index_01_'+s]-target['pinky_01_'+s]
    hand_length=(target['middle_01_'+s]-target['hand_'+s]).length/(head('finger3-1.'+S)-head(wrist)).length
    hand_width=ta.length/across.length
    # Longitudinal joint fitting is independent from skin thickness. Scaling
    # every finger radially by its segment length was producing swollen joints.
    hand_depth=math.sqrt(hand_length*hand_width)
    fit[s]={'palm_length_scale':hand_length,'palm_width_scale':hand_width,'palm_depth_scale':hand_depth}
    def add(src,dst,a,b,c,e,width=hand_width,depth=hand_depth):
        axial=(e-c).length/(b-a).length
        transforms[src]=frame(c,e,ta)@Matrix.Diagonal((axial,width,depth,1))@frame(a,b,across).inverted()
        mapping[src]=dst
    add(wrist,'hand_'+s,head(wrist),head('finger3-1.'+S),target['hand_'+s],target['middle_01_'+s])
    for section in ('upperarm','lowerarm'):
        a=head(section+'01.'+S)
        b=head('lowerarm01.'+S) if section=='upperarm' else head(wrist)
        c=target[section+'_'+s];e=target['lowerarm_'+s] if section=='upperarm' else target['hand_'+s]
        # Real anatomical muscle volume, slightly athletic, with one scale per
        # complete segment and a shared transform for its two donor twist bones.
        radius_scale=hand_width*(1.03 if section=='upperarm' else 1.0)
        for j in (1,2):add(section+f'0{j}.'+S,section+'_'+s,a,b,c,e,radius_scale,radius_scale)
    for number,stem in enumerate(('index','middle','ring','pinky'),1):
        src=f'metacarpal{number}.{S}';dst=stem+'_metacarpal_'+s
        add(src,dst,head(src),tail(src),target[dst],target[stem+'_01_'+s])
    for number,stem in enumerate(('thumb','index','middle','ring','pinky'),1):
        for j in (1,2,3):
            src=f'finger{number}-{j}.{S}';dst=f'{stem}_{j:02}_{s}';a=target[dst]
            if j<3:b=target[f'{stem}_{j+1:02}_{s}']
            else:
                raw=Vector(native['bones'][dst]['axes'][0]);direction=Vector((raw.x,-raw.y,raw.z)).normalized()
                if direction.dot(a-target[f'{stem}_02_{s}'])<0:direction=-direction
                extent=sorted((p-a).dot(direction) for p,w in zip(np,nw) if w.get(dst,0)>.5)
                reach=extent[int((len(extent)-1)*.985)] if extent else .023
                b=a+direction*max(.012,min(.038,reach-.0015))
            add(src,dst,head(src),tail(src),a,b)

hp=[];weights=[]
for p,w in zip(coords,sw):
    selected={n:v for n,v in w.items() if n in transforms};total=sum(selected.values())
    hp.append(sum((transforms[n]@p*v for n,v in selected.items()),Vector())/total if total else p)
    dst={}
    for n,v in selected.items():dst[mapping[n]]=dst.get(mapping[n],0)+v
    weights.append(norm(dst))

# Transfer only the arm contribution from the accepted native surface. Bone
# names, including both twist bones, remain native; fingers and metacarpals
# retain their anatomical weights and cannot leak into a neighbouring digit.
arm_trees={}
for s in ('l','r'):
    for section in ('upperarm','lowerarm'):
        triangles=[t for t in native['triangles'] if
            sum(sum(v for n,v in nw[i].items() if n.startswith(section) and n.endswith('_'+s)) for i in t)/3>.5]
        arm_trees[s,section]=(BVHTree.FromPolygons(np,triangles,all_triangles=True),triangles)
for i,(p,w) in enumerate(zip(hp,weights)):
    if not w:continue
    s=max(('l','r'),key=lambda s:sum(v for n,v in w.items() if n.endswith('_'+s)))
    fractions={section:sum(v for n,v in w.items() if n==section+'_'+s) for section in ('upperarm','lowerarm')}
    if sum(fractions.values())<.001:continue
    new={n:v for n,v in w.items() if n not in ('upperarm_'+s,'lowerarm_'+s)}
    for section,fraction in fractions.items():
        if fraction<1e-6:continue
        tree,triangles=arm_trees[s,section]
        location,normal,ti,distance=tree.find_nearest(p)
        if ti is None:raise RuntimeError('Missing native arm binding '+s+section)
        face=triangles[ti];a,b,c=(np[j] for j in face)
        bc=barycentric_transform(location,a,b,c,Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
        sample={}
        for vi,factor in zip(face,bc):
            for n,v in nw[vi].items():
                if n.endswith('_'+s) and any(n.startswith(t) for t in ('upperarm','lowerarm','clavicle')):
                    sample[n]=sample.get(n,0)+max(0,factor)*v
        for n,v in norm(sample).items():new[n]=new.get(n,0)+v*fraction
    weights[i]=norm(new)

bpy.ops.wm.read_factory_settings(use_empty=True)
chosen=[]
for i,f in enumerate(faces):
    if all(sum(v for n,v in sw[j].items() if n in transforms)>.5 for j in f):chosen.append(i)
ids=sorted({v for i in chosen for v in faces[i]});remap={v:i for i,v in enumerate(ids)}
data=bpy.data.meshes.new('M4_Continuous_Anatomical_Surface')
data.from_pydata([hp[i] for i in ids],[],[[remap[v] for v in faces[i]] for i in chosen]);data.update()
obj=bpy.data.objects.new('M4_RealisticBareArms_Candidate',data);bpy.context.collection.objects.link(obj)
for n in sorted({n for i in ids for n in weights[i]}):obj.vertex_groups.new(name=n)
for i,src in enumerate(ids):
    for n,w in weights[src].items():obj.vertex_groups[n].add([i],w,'REPLACE')
layer=data.uv_layers.new(name='DonorUV')
for p,src in zip(data.polygons,chosen):
    p.use_smooth=True
    for li,t in zip(p.loop_indices,uvs[src]):layer.data[li].uv=t

# Preserve the donor's welded wrist and elbow topology. Cut only the proximal
# upper arm; this candidate contains no native sleeve/cuff/glove triangles.
bm=bmesh.new();bm.from_mesh(data)
deform=bm.verts.layers.deform.active;names={g.index:g.name for g in obj.vertex_groups}
for s in ('l','r'):
    a=target['upperarm_'+s];axis=(target['lowerarm_'+s]-a).normalized()
    vs=[v for v in bm.verts if sum(w for g,w in v[deform].items() if names[g].endswith('_'+s))>.5]
    selected=set(vs)
    edges=[e for e in bm.edges if all(v in selected for v in e.verts)]
    fs=[f for f in bm.faces if all(v in selected for v in f.verts)]
    bmesh.ops.bisect_plane(bm,geom=vs+edges+fs,plane_co=a+axis*.025,plane_no=axis,
        clear_inner=True,clear_outer=False,dist=1e-7)
boundary=[e for e in bm.edges if e.is_boundary]
if boundary:bmesh.ops.holes_fill(bm,edges=boundary,sides=0)
bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(data);bm.free();data.update()

# One subdivision creates rounded knuckle/elbow loops and interpolates the
# existing skin weights/UVs without changing the skeleton or any animation.
activate(obj)
sub=obj.modifiers.new('AnatomicalSurfaceResolution','SUBSURF');sub.levels=1
bpy.ops.object.modifier_apply(modifier=sub.name)
data=obj.data

material=bpy.data.materials.new('CC0_RealisticSkin');material.use_nodes=True
nodes=material.node_tree.nodes;links=material.node_tree.links
shader=next(n for n in nodes if n.type=='BSDF_PRINCIPLED')
shader.inputs['Roughness'].default_value=.5
shader.inputs['Subsurface Weight'].default_value=.13
image=bpy.data.images.load(str(OUT/'Donor/young_lightskinned_male_diffuse.png'));image.pack()
texture=nodes.new('ShaderNodeTexImage');texture.image=image
links.new(texture.outputs['Color'],shader.inputs['Base Color'])
data.materials.append(material)

# Store an editable native reference rig in Blender too. UE uses its own
# original reference bones, never an FBX reconstruction of this helper rig.
arm=bpy.data.armatures.new('M4_NativeReference');rig=bpy.data.objects.new('M4_NativeReference',arm)
bpy.context.collection.objects.link(rig);activate(rig);bpy.ops.object.mode_set(mode='EDIT')
by_index={b['index']:n for n,b in native['bones'].items()}
for n,info in native['bones'].items():
    b=arm.edit_bones.new(n);b.head=target[n]
    axis=Vector(info['axes'][0]);axis=Vector((axis.x,-axis.y,axis.z)).normalized()
    b.tail=b.head+axis*.025
    z=Vector(info['axes'][2]);b.align_roll(Vector((z.x,-z.y,z.z)).normalized())
for n,info in native['bones'].items():
    parent=by_index.get(info['parent'])
    if parent and parent!=n:arm.edit_bones[n].parent=arm.edit_bones[parent]
bpy.ops.object.mode_set(mode='OBJECT');rig.show_in_front=True
armmod=obj.modifiers.new('NativeReferenceSkinning','ARMATURE');armmod.object=rig;obj.parent=rig
obj['purpose']='M4-only surface candidate; original UE skeleton and animation remain authoritative'
obj['license']='MakeHuman core mesh + system skin CC0; see Donor/provenance.json'
obj['ue_source_mesh']=native['source']

data.calc_loop_triangles();verts=[];normals=[];uv=[];ws=[];tris=[];mats=[];lookup={}
layer=data.uv_layers.active.data
for tri in data.loop_triangles:
    indices=[]
    for vi,li in zip(tri.vertices,tri.loops):
        v=data.vertices[vi];t=layer[li].uv;identity=(vi,round(t.x,7),round(t.y,7))
        if identity not in lookup:
            lookup[identity]=len(verts);n=v.normal
            verts.append(ue(v.co));normals.append([n.x,-n.y,n.z]);uv.append([t.x,1-t.y])
            ws.append(norm({obj.vertex_groups[g.group].name:g.weight for g in v.groups}))
        indices.append(lookup[identity])
    # Y reflection is sufficient for UE front faces; do not reverse again.
    tris.append(indices);mats.append(0)
out={'surface_export_version':2,'anatomy_revision':'continuous_m4_candidate_1','profile':'M4',
    'source':native['source'],'vertices':verts,'normals':normals,'uv':uv,'weights':ws,
    'triangles':tris,'materials':mats,'sides':['l','r'],'fit':fit}
(OUT/'M4_skin.json').write_text(json.dumps(out,separators=(',',':')),encoding='utf-8')
activate(obj);bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'M4_RealisticBareArms_Candidate.blend'))
print('M4_REALISTIC_CANDIDATE_AUTHORED',len(verts),'vertices',len(tris),'triangles',flush=True)
