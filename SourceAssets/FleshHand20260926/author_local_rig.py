"""Bind the generated green hand to a fitted custom hand skeleton in background.

Keeps the Meshy quad surface, UVs, corner normals and material. Does not author
combat animation, launch Unreal, render previews or run deformation tests.
"""
from pathlib import Path
import json
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT/'Meshy/candidate01/downloads'
OUT = ROOT/'LocalRig'
OUT.mkdir(parents=True, exist_ok=True)
CONFIG = json.loads((OUT/'rig_definition.json').read_text(encoding='utf-8'))
VERSION = 'FleshHand_Green_LocalRigV1'

def log(message):
    print('FLESHHAND_AUTHOR: '+message,flush=True)

def smoothstep(a,b,value):
    t=np.clip((value-a)/(b-a),0,1)
    return t*t*(3-2*t)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene
scene.unit_settings.system='METRIC'
scene.unit_settings.scale_length=1.0
bpy.ops.import_scene.gltf(filepath=str(SOURCE/'model.glb'))
material=next(o for o in scene.objects if o.type=='MESH').data.materials[0]
material.name='M_FleshHand_GreenSkin'
for ob in list(scene.objects):
    bpy.data.objects.remove(ob,do_unlink=True)
bpy.ops.import_scene.fbx(filepath=str(SOURCE/'model.fbx'),use_custom_normals=True)
obj=next(o for o in scene.objects if o.type=='MESH')
obj.name='SK_'+VERSION
obj.data.name='FleshHand_EditableQuadSurface'
obj.data.materials.clear()
obj.data.materials.append(material)
for p in obj.data.polygons:
    p.material_index=0

world=obj.matrix_world.copy()
vv=np.array([list(world@p.co) for p in obj.data.vertices])
lo,hi=vv.min(axis=0),vv.max(axis=0)
height=CONFIG['authoring_height_m']
scale=height/(hi[2]-lo[2])
offset=Vector((-(hi[0]+lo[0])/2,-(hi[1]+lo[1])/2,-lo[2]))
transform=Matrix.Scale(scale,4)@Matrix.Translation(offset)@world
normal_matrix=transform.to_3x3().inverted().transposed()
corner_normals=[(normal_matrix@Vector(n.vector)).normalized() for n in obj.data.corner_normals]
obj.data.transform(transform)
obj.matrix_world=Matrix.Identity(4)
obj.data.normals_split_custom_set(corner_normals)
v=np.array([list(p.co) for p in obj.data.vertices],dtype=np.float64)
vn=v/height
n=len(v)
spec=CONFIG['bones']

arm=bpy.data.armatures.new('FleshHand_CustomSkeleton')
rig=bpy.data.objects.new('RIG_'+VERSION,arm)
scene.collection.objects.link(rig)
rig.show_in_front=True
arm.display_type='OCTAHEDRAL'
bpy.ops.object.select_all(action='DESELECT')
rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
for item in spec:
    bone=arm.edit_bones.new(item['name'])
    bone.head=Vector(item['head'])*height
    bone.tail=Vector(item['tail'])*height
    bone.use_deform=item.get('deform',True)
    if item.get('parent'):
        bone.parent=arm.edit_bones[item['parent']]
        bone.use_connect=(bone.head-bone.parent.tail).length<1e-6
    bone.align_roll(Vector(CONFIG['palm_outward_axis']))
bpy.ops.object.mode_set(mode='OBJECT')
for label in ('body','thumb','index','middle','ring','little'):
    collection=arm.collections.new(label.title())
    for item in spec:
        if item['region']==label:
            collection.assign(arm.bones[item['name']])

log('Creating initial heat weights on the quad surface')
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.object.parent_set(type='ARMATURE_AUTO')
deforms=[item for item in spec if item.get('deform',True)]
names=[s['name'] for s in deforms]
name_index={name:i for i,name in enumerate(names)}
weights=np.zeros((n,len(names)),dtype=np.float64)
group_map={g.index:name_index[g.name] for g in obj.vertex_groups if g.name in name_index}
for point in obj.data.vertices:
    for group in point.groups:
        if group.group in group_map:
            weights[point.index,group_map[group.group]]=group.weight
if np.any(weights.sum(axis=1)<1e-10):
    raise RuntimeError('Heat solver did not bind the whole surface; production binding needs repair.')

# Label the four separate digits above their web by mesh connectivity. This
# prevents opposing fingers pulling one another across small spatial gaps.
edges=np.array([list(e.vertices) for e in obj.data.edges],dtype=np.int32)
allowed=np.ones_like(weights)
parent=np.arange(n,dtype=np.int32)
def find(a):
    while parent[a]!=a:
        parent[a]=parent[parent[a]]
        a=parent[a]
    return a
cut=CONFIG['finger_isolation_cut']
mask=vn[:,2]>cut
for a,b in edges[mask[edges[:,0]]&mask[edges[:,1]]]:
    a,b=find(a),find(b)
    if a!=b:
        parent[b]=a
groups={}
for i in np.flatnonzero(mask):
    groups.setdefault(int(find(i)),[]).append(int(i))
finger_specs=[s for s in deforms if s['name'].endswith('_03') and s['region']!='thumb']
component_info=[]
for ids in groups.values():
    pts=vn[ids]
    if len(ids)<15 or pts[:,2].max()<CONFIG['finger_tip_min_z']:
        continue
    top=pts[pts[:,2]>np.quantile(pts[:,2],.9)].mean(axis=0)
    nearest=min(finger_specs,key=lambda s:np.linalg.norm(top-np.array(s['tail'])))
    region=nearest['region']
    blend=smoothstep(cut,cut+.045,vn[ids,2])
    for j,item in enumerate(deforms):
        if item['region']!=region:
            allowed[ids,j]*=1-blend
    component_info.append({'region':region,'vertices':len(ids)})

# The thumb projects laterally from the palm. Its anatomical separation plane
# is fitted from this generated hand; distal thumb and four-finger regions
# remain independent while the thenar pad retains a broad blended root.
thumb_plane=CONFIG['thumb_isolation_plane']
signed=vn[:,0]*thumb_plane[0]+vn[:,2]*thumb_plane[1]+thumb_plane[2]
thumb_lock=smoothstep(0,.045,signed)*smoothstep(.23,.36,vn[:,2])
for j,item in enumerate(deforms):
    if item['region']!='thumb':
        allowed[:,j]*=1-thumb_lock
    elif item['name']!='thumb_01':
        allowed[:,j]*=(1-smoothstep(-.06,.005,-signed))*smoothstep(.22,.34,vn[:,2])

weights*=allowed
def normalize(w):
    sums=w.sum(axis=1)
    if np.any(sums<1e-12):
        raise RuntimeError('Anatomical weight region has an unsupported point; adjust its boundary.')
    w/=sums[:,None]
normalize(weights)

a=np.concatenate([edges[:,0],edges[:,1]])
b=np.concatenate([edges[:,1],edges[:,0]])
edge_weights=1/np.maximum(np.linalg.norm(v[a]-v[b],axis=1),height*.0015)
degree=np.bincount(a,weights=edge_weights,minlength=n)
for iteration in range(6):
    neighbors=np.zeros_like(weights)
    for j in range(len(names)):
        neighbors[:,j]=np.bincount(a,weights=weights[b,j]*edge_weights,minlength=n)/np.maximum(degree,1e-12)
    weights=(.75*weights+.25*neighbors)*allowed
    normalize(weights)

_,seam_inverse,seam_counts=np.unique(np.round(vn,6),axis=0,return_inverse=True,return_counts=True)
seam_sums=np.zeros((len(seam_counts),len(names)))
np.add.at(seam_sums,seam_inverse,weights)
weights=(seam_sums/seam_counts[:,None])[seam_inverse]
np.savez_compressed(OUT/'weights_editable.npz',weights=weights.astype(np.float32),bones=np.array(names))
order=np.argsort(weights,axis=1)[:,-4:]
trimmed=np.zeros_like(weights)
rows=np.arange(n)[:,None]
trimmed[rows,order]=weights[rows,order]
trimmed[trimmed<1e-5]=0
normalize(trimmed)
weights=trimmed

def apply_weights(mesh,values):
    mesh.vertex_groups.clear()
    for j,name in enumerate(names):
        group=mesh.vertex_groups.new(name=name)
        for vi in np.flatnonzero(values[:,j]):
            group.add([int(vi)],float(values[vi,j]),'REPLACE')
    mesh.parent=rig
    modifier=next((m for m in mesh.modifiers if m.type=='ARMATURE'),None)
    if modifier is None:
        modifier=mesh.modifiers.new('Hand Skinning - Four Influences','ARMATURE')
    modifier.object=rig
    modifier.use_deform_preserve_volume=False

apply_weights(obj,weights)
obj['binding_method']='Fitted hand bone heat, connected digit isolation, thumb region, adjacency smoothing, four influences'
obj['source_task']=json.loads((ROOT/'Meshy/candidate01/task.json').read_text())['task_id']
rig['authoring_height_m']=height
rig['game_scale']='One-metre canonical authoring height; final monster world size is a later gameplay setting'
rig['animation_status']='Bind and weights only; original gamedev attack animation is not authored yet'
rig['testing_status']='Not rendered or deformation/game tested; no UE import'
texture_dir=OUT/'Textures'
texture_dir.mkdir(exist_ok=True)
image_paths=[]
for node in material.node_tree.nodes:
    if node.type=='TEX_IMAGE' and node.image:
        img=node.image
        path=texture_dir/(Path(img.name).stem.replace(' ','_')+'.png')
        img.filepath_raw=str(path)
        img.file_format='PNG'
        img.save()
        img.pack()
        img.filepath='//Textures/'+path.name
        image_paths.append(str(path.relative_to(OUT)))
bpy.data.orphans_purge(do_recursive=True)
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active=rig
blend=OUT/(VERSION+'.blend')
bpy.ops.wm.save_as_mainfile(filepath=str(blend))

# Export the service's baked triangle ordering, preserving its normals/UVs;
# map weights from the corresponding quad surface by exact spatial match.
before=set(scene.objects)
bpy.ops.import_scene.gltf(filepath=str(SOURCE/'model.glb'))
export_obj=next(o for o in scene.objects if o not in before and o.type=='MESH')
export_obj.name='SK_'+VERSION+'_Export'
export_transform=Matrix.Scale(scale,4)@Matrix.Translation(offset)@export_obj.matrix_world
nm=export_transform.to_3x3().inverted().transposed()
normals=[(nm@Vector(q.vector)).normalized() for q in export_obj.data.corner_normals]
export_obj.data.transform(export_transform)
export_obj.matrix_world=Matrix.Identity(4)
export_obj.data.normals_split_custom_set(normals)
export_obj.data.materials.clear()
export_obj.data.materials.append(material)
kd=KDTree(n)
for vi,co in enumerate(v):
    kd.insert(co,vi)
kd.balance()
mapping=[]
for point in export_obj.data.vertices:
    _,vi,distance=kd.find(point.co)
    if distance>height*1e-4:
        raise RuntimeError('GLB and FBX do not share the same surface; weight transfer needs reprojection.')
    mapping.append(vi)
apply_weights(export_obj,weights[np.array(mapping)])
bpy.ops.object.select_all(action='DESELECT')
export_obj.select_set(True)
rig.select_set(True)
bpy.context.view_layer.objects.active=rig
fbx=OUT/('SK_'+VERSION+'.fbx')
glb=OUT/('SK_'+VERSION+'.glb')
log('Saving bound FBX and GLB')
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE','MESH'},
    add_leaf_bones=False,bake_anim=False,use_armature_deform_only=False,
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',
    use_mesh_modifiers=False,mesh_smooth_type='OFF',path_mode='COPY',embed_textures=True)
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
    export_animations=False,export_skins=True,export_all_influences=False,
    export_def_bones=True,export_yup=True,export_normals=True,export_tangents=True,
    export_morph=False,export_materials='EXPORT',export_extras=True)
receipt={'stage':'local_custom_hand_bind_saved','source_task':obj['source_task'],
    'bone_count':len(spec),'deform_bones':len(deforms),'quad_vertices':n,
    'quad_polygons':len(obj.data.polygons),'quad_faces':sum(len(p.vertices)==4 for p in obj.data.polygons),
    'export_triangles':len(export_obj.data.polygons),'material_slots':len(export_obj.data.materials),
    'max_influences':4,'authoring_height_m':height,'components':component_info,
    'textures':image_paths,'files':[str(p.relative_to(ROOT)) for p in (blend,fbx,glb)],
    'animation_authored':False,'ue_imported':False,'rendered':False,'tested':False}
(OUT/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
log(json.dumps(receipt))
