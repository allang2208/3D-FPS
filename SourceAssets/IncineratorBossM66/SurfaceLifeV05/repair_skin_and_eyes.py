"""Repair the right oral wall's limb-driven skin and add seven local eye controls."""
import bpy,json,math
import numpy as np
from pathlib import Path
from mathutils import Vector
ROOT=Path('D:/FPS3D/FPSGAME/SourceAssets/IncineratorBossM66/SurfaceLifeV05')
for folder in ('Authoring','Export','Records'):(ROOT/folder).mkdir(parents=True,exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(ROOT.parent/'MeshyRigV01/Authoring/M66_back_completed_v01.blend'))
mesh=bpy.data.objects['M66_Body'];rig=bpy.data.objects['M66_Rig']
factor=json.loads((ROOT.parent/'MeshyRigV01/Records/rig_completion.json').read_text())['uniform_scale']
surface=json.loads((ROOT/'Records/source_surface.json').read_text())
pos=np.array([v.co[:] for v in mesh.data.vertices])/factor
names=[g.name for g in mesh.vertex_groups]
original=[{names[g.group]:g.weight for g in v.groups if g.weight>1e-7} for v in mesh.data.vertices]
result=[dict(w) for w in original]
def smooth(a,b,x):
    q=max(0,min(1,(x-a)/(b-a)));return q*q*(3-2*q)
def blend(a,b,t):
    out={n:v*(1-t) for n,v in a.items()}
    for n,v in b.items():out[n]=out.get(n,0)+v*t
    return out
# UV charts are physically distinct here: oral plates must not inherit the
# small hand lying over the abdomen. Select the actual right oral-wall charts.
parent=list(range(len(pos)))
def find(a):
    while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
    return a
for edge in mesh.data.edges:
    a,b=(find(int(i)) for i in edge.vertices)
    if a!=b:parent[b]=a
charts={}
for i in range(len(pos)):charts.setdefault(find(i),[]).append(i)
oral_charts=set()
for ids in charts.values():
    points=pos[ids];lo=points.min(axis=0);hi=points.max(axis=0)
    if len(ids)>20 and lo[0]>-.225 and hi[0]<.075 and lo[2]>.71 and hi[2]<1.39 and hi[1]<-.13:
        oral_charts.update(ids)
mouth=[];removed_leg=removed_arm=0.
for i,(x,y,z) in enumerate(pos):
    mask=smooth(-.235,-.175,x)*(1-smooth(.055,.105,x))
    mask*=1-smooth(-.215,-.125,y)
    mask*=smooth(.68,.78,z)*(1-smooth(1.17,1.31,z))
    if i in oral_charts:mask=max(mask,smooth(.71,.78,z)*(1-smooth(1.20,1.39,z)))
    # Keep the small palm and fingers themselves, even where they cross the mouth.
    small_hand=sum(v for n,v in original[i].items() if n.startswith('Bone_') and 38<=int(n[-3:])<=53)
    if small_hand>.25 and i not in oral_charts:continue
    if mask<1e-5:continue
    upper=smooth(.76,1.12,z)
    target={'Bone_001':1-upper,'Bone_007':upper*.25,'Bone_006':upper*.75}
    result[i]=blend(original[i],target,mask);mouth.append(i)
    removed_leg+=mask*sum(v for n,v in original[i].items() if n in ['Bone_%03d'%j for j in range(8,18)])
    removed_arm+=mask*sum(v for n,v in original[i].items() if n in ['Bone_%03d'%j for j in range(24,38)])

uv=np.array([v.uv[:] for v in mesh.data.uv_layers.active.data]);vertices=np.array([v.vertex_index for v in mesh.data.loops])
pixels=np.column_stack((uv[:,0]*2048,(1-uv[:,1])*2048))
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode='EDIT')
eyes=[]
for eye in surface['eyes']:
    name='M66_Eye_%02d'%eye['index'];center=Vector(eye['sphere_center_source'])
    x,y,radius=eye['uv_pixel'];d=np.linalg.norm((pixels-[x,y])/radius,axis=1)
    ids=np.unique(vertices[d<.65]);front=Vector(np.mean(pos[ids],axis=0))-center;front.normalize()
    bone=rig.data.edit_bones.new(name);bone.head=center*factor;bone.tail=(center+front*.035)*factor
    bone.parent=rig.data.edit_bones['Bone_020'];bone.use_deform=True;bone.align_roll(Vector((0,0,1)))
    eyes.append({**eye,'bone':name,'forward_source':list(front)})
bpy.ops.object.mode_set(mode='OBJECT')
eye_vertices=set()
for eye in eyes:
    name=eye['bone'];mesh.vertex_groups.new(name=name)
    x,y,radius=eye['uv_pixel'];distance=np.linalg.norm((pixels-[x,y])/radius,axis=1)
    masks={}
    for loop in np.flatnonzero(distance<1.12):
        i=int(vertices[loop]);mask=1-smooth(.72,1.12,float(distance[loop]))
        masks[i]=max(masks.get(i,0),mask)
    for i,mask in masks.items():result[i]=blend(result[i],{name:1.},mask);eye_vertices.add(i)
    eye['weighted_vertices']=len(masks)

# Retain the original split topology and normals, but keep skin identical on
# coincident boundary vertices touched by either repair.
_,inverse=np.unique(np.rint(pos/1e-6).astype(np.int64),axis=0,return_inverse=True)
seams={}
for i,key in enumerate(inverse):seams.setdefault(int(key),[]).append(i)
changed=set(mouth)|eye_vertices
for ids in seams.values():
    if len(ids)<2 or not any(i in changed for i in ids):continue
    mean={}
    for i in ids:
        for name,value in result[i].items():mean[name]=mean.get(name,0)+value/len(ids)
    for i in ids:result[i]=dict(mean);changed.add(i)
for i in changed:
    values=sorted(((n,v) for n,v in result[i].items() if v>1e-6),key=lambda p:-p[1])[:8]
    total=sum(v for _,v in values)
    for group in list(mesh.data.vertices[i].groups):mesh.vertex_groups[group.group].remove([i])
    for name,value in values:mesh.vertex_groups[name].add([i],value/total,'REPLACE')
rig['stage']='V05 local oral-wall skin repair; seven independent eye controls'
mesh['M66_surface_repair']='Right oral wall and tooth attachments follow pelvis/spine, not walking legs or swinging arms'
bpy.context.scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'Authoring/M66_surface_life_v05.blend'))
fbx=ROOT/'Export/SK_M66_SurfaceLife_V05.fbx'
bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'ARMATURE','MESH'},
    add_leaf_bones=False,use_armature_deform_only=False,bake_anim=False,use_mesh_modifiers=False,
    axis_forward='-Y',axis_up='Z',apply_unit_scale=True,apply_scale_options='FBX_SCALE_NONE',mesh_smooth_type='OFF',path_mode='AUTO')
report={'source':'MeshyRigV01/Authoring/M66_back_completed_v01.blend','fbx':str(fbx),
    'mouth_vertices':len(mouth),'eye_vertices':len(eye_vertices),'edited_vertices':len(changed),
    'removed_leg_influence_sum':removed_leg,'removed_arm_influence_sum':removed_arm,
    'eyes':eyes,'bones':len(rig.data.bones),'vertices':len(pos),'triangles':sum(len(p.vertices)-2 for p in mesh.data.polygons),
    'mesh_geometry_modified':False,'uv_modified':False,'runtime_tested':False}
(ROOT/'Records/rig_completion.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('M66_SURFACE_REPAIRED '+json.dumps({k:report[k] for k in ('mouth_vertices','eye_vertices','edited_vertices','bones','removed_leg_influence_sum','removed_arm_influence_sum')}))
