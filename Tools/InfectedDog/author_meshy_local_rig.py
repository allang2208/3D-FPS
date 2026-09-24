"""Author a fitted quadruped bind on the actual Meshy quad mesh, in background.

No animation test, acceptance render, or UE operation is performed here.
Source topology, UVs, corner normals and PBR images are retained.
"""
import bpy
import json
import math
import hashlib
from pathlib import Path
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

PROJECT = Path(__file__).resolve().parents[2]
BASE = PROJECT / 'SourceAssets/InfectedDogMeshy20260924'
SOURCE = BASE / 'Meshy/candidate01_quad50k/downloads'
OUT = BASE / 'LocalRig'
OUT.mkdir(parents=True, exist_ok=True)
VERSION = 'InfectedDog_Meshy_LocalRigV1'

def log(s):
    print('LOCAL_RIG: ' + s, flush=True)

def smoothstep(a, b, x):
    t = np.clip((x-a)/(b-a), 0., 1.)
    return t*t*(3.-2.*t)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

# Import the glTF material graph/embedded images, then use the true quad FBX
# surface. Both are exports of the same Meshy remesh job and share the UV atlas.
bpy.ops.import_scene.gltf(filepath=str(SOURCE/'model.glb'))
glb_obj = next(o for o in scene.objects if o.type == 'MESH')
material = glb_obj.data.materials[0]
material.name = 'M_InfectedDog_Meshy_Skin'
for ob in list(scene.objects):
    bpy.data.objects.remove(ob, do_unlink=True)
bpy.ops.import_scene.fbx(filepath=str(SOURCE/'model.fbx'), use_custom_normals=True)
obj = next(o for o in scene.objects if o.type == 'MESH')
bpy.context.view_layer.update()
obj.name = 'SK_' + VERSION
obj.data.name = 'InfectedDog_Meshy_QuadSurface'
obj.data.materials.clear()
obj.data.materials.append(material)
for poly in obj.data.polygons:
    poly.material_index = 0

source_world = obj.matrix_world.copy()
world_vertices = np.array([list(source_world @ v.co) for v in obj.data.vertices])
source_min, source_max = world_vertices.min(axis=0), world_vertices.max(axis=0)
height_scale = 1.0 / (source_max[2]-source_min[2])
offset = Vector((-(source_min[0]+source_max[0])/2, 0, -source_min[2]))
transform = Matrix.Scale(height_scale, 4) @ Matrix.Translation(offset) @ source_world
# Explicitly carry corner normals across the rigid axis conversion. Do not
# recalculate/smooth the imported surface and thereby discard its baked basis.
corner_normals = [Vector(n.vector) for n in obj.data.corner_normals]
normal_matrix = transform.to_3x3().inverted().transposed()
transformed_normals = [(normal_matrix @ n).normalized() for n in corner_normals]
obj.data.transform(transform)
obj.matrix_world = Matrix.Identity(4)
obj.data.normals_split_custom_set(transformed_normals)
v = np.array([list(p.co) for p in obj.data.vertices], dtype=np.float64)
n = len(v)

# Pivots were placed from the actual source surface in grounded, one-meter
# authoring coordinates. They are NOT copies of the open-mouth Wolf bind pose.
spec = []
def bone(name, head, tail, parent=None, region='body', deform=True):
    spec.append(dict(name=name, head=list(head), tail=list(tail), parent=parent,
                     region=region, deform=deform))

bone('root', (0,0,0), (0,0,.12), deform=False)
bone('pelvis', (0,.26,.626), (0,.10,.618), 'root')
bone('spine_01', (0,.10,.618), (0,-.075,.609), 'pelvis')
bone('spine_02', (0,-.075,.609), (0,-.245,.608), 'spine_01')
bone('chest', (0,-.245,.608), (0,-.356,.66), 'spine_02')
bone('neck_01', (0,-.356,.66), (0,-.425,.716), 'chest', 'neck')
bone('neck_02', (0,-.425,.716), (0,-.491,.774), 'neck_01', 'neck')
bone('neck_03', (0,-.491,.774), (0,-.555,.819), 'neck_02', 'neck')
bone('head', (0,-.555,.819), (0,-.74,.735), 'neck_03', 'head')

for side, sign in [('L', 1), ('R', -1)]:
    def p(x,y,z): return (sign*x,y,z)
    bone('ear_base.'+side,p(.064,-.551,.868),p(.084,-.556,.928), 'head', 'ear_'+side)
    bone('ear_tip.'+side,p(.084,-.556,.928),p(.097,-.57,.99), 'ear_base.'+side, 'ear_'+side)
    shoulder, upper, elbow = p(.043,-.282,.647),p(.116,-.39,.566),p(.102,-.343,.374)
    wrist, pad, toes = p(.115,-.349,.105),p(.13,-.399,.034),p(.133,-.465,.022)
    bone('scapula.'+side, shoulder,upper,'chest','front_'+side)
    bone('upperarm.'+side,upper,elbow,'scapula.'+side,'front_'+side)
    bone('forearm.'+side,elbow,wrist,'upperarm.'+side,'front_'+side)
    bone('carpus.'+side,wrist,pad,'forearm.'+side,'front_'+side)
    bone('front_toes.'+side,pad,toes,'carpus.'+side,'front_'+side)
    hip, knee, hock = p(.106,.27,.627),p(.11,.278,.422),p(.113,.45,.224)
    ankle, pad, toes = p(.141,.452,.067),p(.148,.445,.031),p(.15,.395,.026)
    bone('thigh.'+side,hip,knee,'pelvis','rear_'+side)
    bone('calf.'+side,knee,hock,'thigh.'+side,'rear_'+side)
    bone('hock.'+side,hock,ankle,'calf.'+side,'rear_'+side)
    bone('hindfoot.'+side,ankle,pad,'hock.'+side,'rear_'+side)
    bone('rear_toes.'+side,pad,toes,'hindfoot.'+side,'rear_'+side)

tail = [(0,.327,.669),(0,.407,.597),(0,.473,.481),
        (0,.536,.384),(0,.603,.321),(0,.693,.286),(0,.78,.257)]
for i in range(6):
    bone('tail_%02d'%(i+1),tail[i],tail[i+1], 'pelvis' if i==0 else 'tail_%02d'%i,'tail')

arm = bpy.data.armatures.new('InfectedDog_Meshy_FittedSkeleton')
rig = bpy.data.objects.new('RIG_'+VERSION, arm)
scene.collection.objects.link(rig)
rig.show_in_front = True
arm.display_type = 'OCTAHEDRAL'
bpy.context.view_layer.objects.active = rig
rig.select_set(True)
obj.select_set(False)
bpy.ops.object.mode_set(mode='EDIT')
for s in spec:
    b = arm.edit_bones.new(s['name'])
    b.head, b.tail = s['head'], s['tail']
    b.use_deform = s['deform']
    if s['parent']:
        b.parent = arm.edit_bones[s['parent']]
        b.use_connect = (b.head-b.parent.tail).length < 1e-5
    # Consistent local roll, with a non-parallel reference for sideways chains.
    d = (b.tail-b.head).normalized()
    b.align_roll(Vector((1,0,0)) if abs(d.x)<.8 else Vector((0,0,1)))
bpy.ops.object.mode_set(mode='OBJECT')

for title, prefix in [('Body','body'),('Head and Neck','head'),('Forelimbs','front'),('Hindlimbs','rear'),('Tail','tail')]:
    col = arm.collections.new(title)
    for s in spec:
        region=s['region']
        if region.startswith(prefix) or (prefix=='head' and (region.startswith('ear') or region=='neck')):
            col.assign(arm.bones[s['name']])

log('Fitted skeleton authored; calculating bone heat weights on the quad mesh')
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
deforms = [s for s in spec if s['deform']]
names = [s['name'] for s in deforms]
idx = {name:i for i,name in enumerate(names)}
weights = np.zeros((n,len(names)),dtype=np.float64)
group_to_bone = {g.index:idx[g.name] for g in obj.vertex_groups if g.name in idx}
for point in obj.data.vertices:
    for group in point.groups:
        if group.group in group_to_bone:
            weights[point.index,group_to_bone[group.group]] = group.weight
heat_unassigned=int(np.sum(weights.sum(axis=1)<1e-8))
if heat_unassigned:
    # A failed heat solve must not silently masquerade as a completed binding.
    raise RuntimeError('Bone heat left %d vertices unassigned; source retained for repair'%heat_unassigned)
log('Bone heat completed; applying anatomical weight isolation and joint smoothing')

x,y,z=v.T
allowed=np.ones_like(weights)
for j,s in enumerate(deforms):
    region=s['region']
    if region.startswith(('front_','rear_','ear_')):
        sign=1 if region.endswith('L') else -1
        # A center transition is reserved for the shoulder/ear root. Distal
        # left/right limbs never pull the opposing leg even if they touch.
        side=smoothstep(-.008,.045,x*sign)
        if region.startswith('front_'):
            allowed[:,j]=side*(1-smoothstep(-.18,-.09,y))*(1-smoothstep(.68,.76,z))
        elif region.startswith('rear_'):
            allowed[:,j]=side*smoothstep(.045,.14,y)*(1-smoothstep(.70,.78,z))
        else:
            allowed[:,j]=side*smoothstep(.84,.89,z)*(1-smoothstep(-.48,-.43,y))
    elif region=='head':
        allowed[:,j]=(1-smoothstep(-.46,-.33,y))*smoothstep(.54,.68,z)
    elif region=='neck':
        allowed[:,j]=(1-smoothstep(-.31,-.16,y))*smoothstep(.41,.56,z)
    elif region=='tail':
        allowed[:,j]=smoothstep(.29,.41,y)
        # The tail passes close to the hocks, but above them in this rest pose.
        height_boundary=np.interp(y,[.3,.4,.5,.6,.8],[.55,.48,.39,.26,.19])
        allowed[:,j]*=smoothstep(-.035,.025,z-height_boundary)
        allowed[:,j]*=(1-smoothstep(.07,.105,np.abs(x)))
    else:
        allowed[:,j]=smoothstep(.27,.43,z)

# Mature head/nose region stays rigid to Head rather than receiving a tail,
# chest, or upper-leg contribution from the global automatic solve.
head_lock=(1-smoothstep(-.635,-.52,y))*smoothstep(.62,.70,z)*(1-smoothstep(.85,.895,z))
weights*=1-head_lock[:,None]
weights[:,idx['head']]+=head_lock

# Distal paw/toe pads move as coherent contact surfaces. A broad wrist/hock
# blend remains above each pad instead of hard weighting the whole lower leg.
for side,sign in [('L',1),('R',-1)]:
    for kind, ym in [('front',y<-.23),('rear',y>.32)]:
        m=(x*sign>.025)&ym&(z<.072)
        blend=(1-smoothstep(.025,.067,z))*m
        weights*=1-blend[:,None]
        weights[:,idx[kind+'_toes.'+side]]+=blend

weights*=allowed
def normalize(w):
    total=w.sum(axis=1)
    if np.any(total<=1e-12):
        raise RuntimeError('Anatomy mask has unsupported vertices; correct authoring masks')
    w/=total[:,None]
normalize(weights)

# Surface adjacency smooths each joint without averaging across nearby but
# separate legs. FBX quad topology already joins the UV islands geometrically.
edges=np.array([list(e.vertices) for e in obj.data.edges],dtype=np.int32)
a=np.concatenate([edges[:,0],edges[:,1]])
b=np.concatenate([edges[:,1],edges[:,0]])
edge_len=np.linalg.norm(v[a]-v[b],axis=1)
edge_w=1/np.maximum(edge_len,.0015)
degree=np.bincount(a,weights=edge_w,minlength=n)
for iteration in range(8):
    neighbor=np.zeros_like(weights)
    for j in range(weights.shape[1]):
        neighbor[:,j]=np.bincount(a,weights=weights[b,j]*edge_w,minlength=n)/np.maximum(degree,1e-12)
    weights=(.72*weights+.28*neighbor)*allowed
    normalize(weights)

# The remaining possible positional duplicates get an identical binding so
# texture seams cannot open under deformation. No UV or polygon edit is made.
_, seam_inverse, seam_counts=np.unique(np.round(v,6),axis=0,return_inverse=True,return_counts=True)
if np.any(seam_counts>1):
    sums=np.zeros((len(seam_counts),len(names)))
    np.add.at(sums,seam_inverse,weights)
    weights=(sums/seam_counts[:,None])[seam_inverse]

# Four influences per point for the game export; keep the strongest local
# chains and normalize after trimming. Save the pre-trim editable fields too.
np.savez_compressed(OUT/'weights_full_precision.npz',weights=weights.astype(np.float32),bones=np.array(names))
order=np.argsort(weights,axis=1)[:,-4:]
trimmed=np.zeros_like(weights)
rows=np.arange(n)[:,None]
trimmed[rows,order]=weights[rows,order]
trimmed[trimmed<1e-5]=0
normalize(trimmed)
weights=trimmed
obj.vertex_groups.clear()
for j,name in enumerate(names):
    g=obj.vertex_groups.new(name=name)
    for vi in np.flatnonzero(weights[:,j]):
        g.add([int(vi)],float(weights[vi,j]),'REPLACE')
modifier=next(m for m in obj.modifiers if m.type=='ARMATURE')
modifier.name='Canine Skinning - Four Influences'
modifier.use_deform_preserve_volume=False # Match standard game linear skinning.

obj['source_remesh_task']='01a0d363-3cb2-7671-bb86-23d29502718e'
obj['binding_method']='Fitted canine anatomy + bone heat + anatomical masks + surface smoothing'
obj['closed_mouth']='Head-rigid closed mouth; no independent jaw or internal mouth geometry'
rig['authoring_height_m']=1.0
rig['forward_axis']='-Y (Blender); +Z (glTF export)'
rig['animation_compatibility']='Own bind pose. Requires retargeting from Wolf; do not assign old skeleton directly.'
rig['testing_status']='Not animation tested or rendered. No UE import performed.'

# Keep every texture available both packed in the .blend and beside the FBX.
texture_dir=OUT/'Textures'
texture_dir.mkdir(exist_ok=True)
image_paths=[]
for node in material.node_tree.nodes:
    if node.type=='TEX_IMAGE' and node.image:
        img=node.image
        label=img.name.replace('.png','').replace(' ','_')
        path=texture_dir/(label+'.png')
        img.filepath_raw=str(path)
        img.file_format='PNG'
        img.save()
        img.pack()
        img.filepath='//Textures/'+path.name
        image_paths.append(str(path.relative_to(OUT)))

# Remove the unused import material and its unresolved FBX texture placeholders
# from this newly created scene before packing the authoring file.
bpy.data.orphans_purge(do_recursive=True)

map_names={
    'Wolf_':'root','Wolf_ Pelvis':'pelvis','Wolf_ Spine':'spine_01','Wolf_ Spine1':'chest',
    'Wolf_ Neck':'neck_01','Wolf_ Neck1':'neck_02','Wolf_ Neck2':'neck_03','Wolf_ Head':'head'}
for side in ['L','R']:
    for source,target in [('Clavicle','scapula'),('UpperArm','upperarm'),('Forearm','forearm'),('Hand','carpus'),('Finger0','front_toes'),('Thigh','thigh'),('Calf','calf'),('HorseLink','hock'),('Foot','hindfoot')]:
        map_names['Wolf_ '+side+' '+source]=target+'.'+side
for i in range(6):map_names['Wolf_ Tail'+(str(i) if i else '')]='tail_%02d'%(i+1)
mapping=dict(source_skeleton='/Game/AnimalVarietyPack/Wolf/Meshes/SK_Wolf_Skeleton',
             note='Semantic mapping only; no retargeted animation assets have been authored.',
             source_blender_to_target=map_names,
             unmapped_source={'Wolf_ Ponytail1':'Unconfirmed head accessory; not guessed as a jaw'},
             additional_target=['spine_02','ear_base.L','ear_tip.L','ear_base.R','ear_tip.R','rear_toes.L','rear_toes.R'])
(OUT/'wolf_retarget_map.json').write_text(json.dumps(mapping,indent=2),encoding='utf-8')

log('Skin weights authored; saving editable Blender and bound GLB/FBX')
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True);rig.select_set(True)
bpy.context.view_layer.objects.active=rig
# Opening the authoring file presents the bind mesh and skeleton, not a test pose.
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_distance=2.5
            area.spaces.active.region_3d.view_location=(0,0,.5)
            area.spaces.active.shading.type='MATERIAL'
blend=OUT/(VERSION+'.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(blend))

# Preserve the service's original baked triangulation for delivery. Its GLB
# seam-split vertices share positions with the editable quad mesh; propagate
# the authored weights to those vertices, without re-triangulating ngons and
# losing the tangent basis. The .blend above keeps the editable quad surface.
before=set(scene.objects)
bpy.ops.import_scene.gltf(filepath=str(SOURCE/'model.glb'))
export_obj=next(o for o in scene.objects if o not in before and o.type=='MESH')
export_obj.name='SK_'+VERSION+'_Export'
export_transform=Matrix.Scale(height_scale,4) @ Matrix.Translation(offset) @ export_obj.matrix_world
export_normals=[Vector(q.vector) for q in export_obj.data.corner_normals]
export_normal_matrix=export_transform.to_3x3().inverted().transposed()
export_obj.data.transform(export_transform)
export_obj.matrix_world=Matrix.Identity(4)
export_obj.data.normals_split_custom_set([(export_normal_matrix@q).normalized() for q in export_normals])
export_obj.data.materials.clear()
export_obj.data.materials.append(material)
kd=KDTree(n)
for vi,co in enumerate(v):kd.insert(co,vi)
kd.balance()
vertex_map=[]
for point in export_obj.data.vertices:
    _,vi,distance=kd.find(point.co)
    if distance>1e-5:
        raise RuntimeError('Service export surface does not match the authored quad surface')
    vertex_map.append(vi)
export_weights=weights[np.array(vertex_map)]
for j,name in enumerate(names):
    g=export_obj.vertex_groups.new(name=name)
    for vi in np.flatnonzero(export_weights[:,j]):
        g.add([int(vi)],float(export_weights[vi,j]),'REPLACE')
export_obj.parent=rig
export_modifier=export_obj.modifiers.new('Canine Skinning - Four Influences','ARMATURE')
export_modifier.object=rig
export_modifier.use_deform_preserve_volume=False
bpy.ops.object.select_all(action='DESELECT')
export_obj.select_set(True);rig.select_set(True)
bpy.context.view_layer.objects.active=rig
fbx=OUT/('SK_'+VERSION+'.fbx')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,
    object_types={'ARMATURE','MESH'},add_leaf_bones=False,bake_anim=False,
    use_armature_deform_only=False,axis_forward='-Y',axis_up='Z',
    apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
    use_mesh_modifiers=False,mesh_smooth_type='OFF',path_mode='COPY',embed_textures=True)
glb=OUT/('SK_'+VERSION+'.glb')
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
    export_animations=False,export_skins=True,export_all_influences=False,
    export_def_bones=True,export_yup=True,export_normals=True,export_tangents=True,
    export_morph=False,export_materials='EXPORT',export_extras=True)

receipt=dict(stage='local_rig_and_weights_saved',name=VERSION,
    source_fbx=str(SOURCE/'model.fbx'),source_task='01a0d363-3cb2-7671-bb86-23d29502718e',
    bone_count=len(spec),deform_bone_count=len(deforms),
    bones=spec,vertices=n,polygons=len(obj.data.polygons),
    quad_faces=sum(len(p.vertices)==4 for p in obj.data.polygons),
    export_vertices=len(export_obj.data.vertices),export_triangles=len(export_obj.data.polygons),
    export_surface='Original Meshy GLB triangulation, normals, UV seam positions; weights transferred by matching positions',
    height_m=1.0,ground_z=0,bind_pose='closed-mouth neutral standing',
    weight_method=obj['binding_method'],smoothing_iterations=8,max_influences=4,
    uv_layers=[u.name for u in obj.data.uv_layers],
    preserved=['source quad topology','source UV atlas','source corner normals','source material and embedded PBR images'],
    material_images=image_paths,
    authoring_transform=[list(r) for r in transform],
    boundary=dict(ue_imported=False,animation_retargeted=False,animation_tested=False,acceptance_rendered=False,
                  independent_jaw=False,mouth_interior=False,original_UE_V2_retained=True),
    files=[dict(path=str(p.relative_to(OUT)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [blend,fbx,glb]])
(OUT/'authoring_receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False),encoding='utf-8')
log('SAVED '+json.dumps({k:receipt[k] for k in ['bone_count','deform_bone_count','vertices','polygons','quad_faces','files']}))
