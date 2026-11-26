"""Assemble the fitted in-game vertices and combined Meshy texture on the editable clothed R4."""
import bpy
import gzip
import json
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from pathlib import Path

base=Path(__file__).resolve().parents[2]/'SourceAssets/VillageBlacksmithNPC20261118'
head_data=base/'HeadHair'
body_data=base/'BodyOutfit'
bpy.ops.wm.open_mainfile(filepath=str(body_data/'Smith_Body_Workwear.blend'))
bpy.context.preferences.filepaths.save_version=0
s=bpy.context.scene
d=json.loads(gzip.decompress((head_data/'face.json.gz').read_bytes()))
v=np.asarray(d['p'])*.01
t=np.asarray(d['tri'])[:,::-1].copy()
me=bpy.data.meshes.new('Meshy smith head with integral hair and beard')
me.from_pydata(v.tolist(),[],t.tolist())
me.update()
obj=bpy.data.objects.new('SK_Smith_Head',me)
s.collection.objects.link(obj)
me.polygons.foreach_set('use_smooth',[True]*len(t))
me.polygons.foreach_set('material_index',np.asarray(d['m'],dtype=np.int32))
uv=np.asarray(d['uv'],dtype=np.float32)
uv[:,1]=1-uv[:,1]
me.uv_layers.new(name='UVMap').data.foreach_set('uv',uv[t].ravel())
def make_skin(name,color,normal=None,rough=None,neck_tint=None):
    mat=bpy.data.materials.new(name)
    mat.use_nodes=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links
    bsdf=nodes.get('Principled BSDF')
    bsdf.inputs['Roughness'].default_value=.60
    bsdf.inputs['Specular IOR Level'].default_value=.32
    def texture(path,linear=False):
        n=nodes.new('ShaderNodeTexImage')
        n.image=bpy.data.images.load(str(path),check_existing=True)
        if linear:n.image.colorspace_settings.name='Non-Color'
        return n
    base_color=texture(color).outputs['Color']
    if neck_tint is not None:
        coordinates=nodes.new('ShaderNodeTexCoord')
        z=nodes.new('ShaderNodeSeparateXYZ')
        links.new(coordinates.outputs['Object'],z.inputs[0])
        fade=nodes.new('ShaderNodeMapRange');fade.interpolation_type='SMOOTHSTEP';fade.clamp=True
        fade.inputs['From Min'].default_value=1.504;fade.inputs['From Max'].default_value=1.553
        links.new(z.outputs['Z'],fade.inputs['Value'])
        mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY'
        links.new(fade.outputs[0],mix.inputs[0]);links.new(base_color,mix.inputs[1])
        mix.inputs[2].default_value=(*neck_tint,1);base_color=mix.outputs[0]
    links.new(base_color,bsdf.inputs['Base Color'])
    if normal and normal.is_file():
        nm=nodes.new('ShaderNodeNormalMap');links.new(texture(normal,True).outputs['Color'],nm.inputs['Color'])
        links.new(nm.outputs['Normal'],bsdf.inputs['Normal'])
    if rough and rough.is_file():links.new(texture(rough,True).outputs['Color'],bsdf.inputs['Roughness'])
    return mat
tex=head_data/'Textures'
me.materials.append(make_skin('Smith | Meshy face, hair and beard',tex/'T_Smith_Face_BC.png',tex/'T_Smith_Face_N.png',tex/'T_Smith_Face_R.png'))
fit=json.loads((head_data/'fit.json').read_text())
me.materials.append(make_skin('Smith | Native neck',body_data/'Textures/T_Smith_Skin_head_BC.png',neck_tint=fit['neck_tint_upper_linear']))
me.polygons.foreach_set('material_index',np.asarray(d['m'],dtype=np.int32))
rig=bpy.data.objects['Jason_NativeSkeleton']
bones=json.loads((body_data/'outfit.json').read_text())['bones']
for b in bones:obj.vertex_groups.new(name=b['name'])
by_bone={}
for i,row in enumerate(d['w']):
    if len(row)==1 and abs(row[0][1]-1)<1e-5:by_bone.setdefault(row[0][0],[]).append(i)
    else:
        for k,a in row:obj.vertex_groups[k].add([i],a,'REPLACE')
for k,ids in by_bone.items():obj.vertex_groups[k].add(ids,1,'REPLACE')
mod=obj.modifiers.new('Jason R4 weights','ARMATURE')
mod.object=rig
me.normals_split_custom_set_from_vertices(d['n'])
obj['UE_asset']='/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Head'
library=json.loads((base.parent/'BackpackHarnessRebuild20261020/Inputs/poses.json').read_text())
idle=library['clips']['Unarmed.Idle']
if idle['asset']!='/Game/Characters/JasonPlayer20261003/Animations/J_MM_Idle.J_MM_Idle':raise ValueError('Unknown idle source')
frame=idle['frames'][0]
def transform(v):
    rotation=Quaternion((v[6],v[3],v[4],v[5])).to_matrix()
    m=np.eye(4);m[:3,:3]=np.asarray(rotation)@np.diag(v[7:10]);m[:3,3]=v[:3]
    return m
reference=np.array([transform(library['reference'][b['name']]) for b in bones])
sample=np.array([transform(frame['bones'][b['name']]) for b in bones])
bind=np.repeat(np.eye(4)[None,:,:],len(bones),axis=0)
for i,b in enumerate(bones):
    bind[i,:3,:3]=np.asarray(b['axes']).T
    bind[i,:3,3]=b['position']
posed=sample.copy()
for i,b in enumerate(bones):
    parent=b['parent']
    if parent>=0:
        local=np.linalg.solve(sample[parent],sample[i])
        local[:3,3]+=(np.linalg.solve(bind[parent],bind[i])-np.linalg.solve(reference[parent],reference[i]))[:3,3]
        posed[i]=posed[parent]@local
targets={}
for i,b in enumerate(bones):
    name=b['name'];pb=rig.pose.bones.get(name)
    if not pb:continue
    change=posed[i]@np.linalg.inv(bind[i]);change[:3,3]*=.01
    rest=pb.bone.matrix_local
    goal=Matrix(change.tolist())@rest
    targets[name]=goal
    if pb.parent and pb.parent.name in targets:
        local=pb.parent.bone.matrix_local.inverted_safe()@rest
        basis=local.inverted_safe()@targets[pb.parent.name].inverted_safe()@goal
    else:basis=rest.inverted_safe()@goal
    pb.rotation_mode='QUATERNION'
    pb.matrix_basis=basis
bpy.context.view_layer.update()
s['preview_note']='Integrated Meshy face and hair, fitted R4 and workwear posed from the J_MM_Idle sample at '+str(frame['time'])+' seconds.'
s.render.engine='CYCLES';s.cycles.samples=24;s.cycles.use_denoising=True
s.render.resolution_x=760;s.render.resolution_y=980;s.render.resolution_percentage=100
world=bpy.data.worlds.new('Smith studio');s.world=world;world.use_nodes=True
bg=world.node_tree.nodes.get('Background');bg.inputs[0].default_value=(.32,.35,.39,1);bg.inputs[1].default_value=.44
def aim(ob,pt):ob.rotation_euler=(Vector(pt)-ob.location).to_track_quat('-Z','Y').to_euler()
def area(name,pt,power,size,rgb):
    data=bpy.data.lights.new(name,'AREA');data.shape='DISK';data.size=size;data.energy=power;data.color=rgb
    ob=bpy.data.objects.new(name,data);s.collection.objects.link(ob);ob.location=pt;aim(ob,(0,0,1.1))
area('Softbox',(-2.3,3.2,3.5),330,3,(1,.94,.86))
area('Sky fill',(2.7,2.5,2.5),190,2.8,(.89,.93,1))
area('Rim',(.6,-2,3.1),270,2,(1,.96,.92))
camdata=bpy.data.cameras.new('Smith source camera');camdata.type='ORTHO';camdata.ortho_scale=2.10
cam=bpy.data.objects.new(camdata.name,camdata);s.collection.objects.link(cam);s.camera=cam
cam.location=(1.50,5.4,1.15);aim(cam,(0,0,.89))
s.render.filepath=str(base/'Smith_assembled.png')
bpy.ops.wm.save_as_mainfile(filepath=str(base/'VillageBlacksmith_R4.blend'),relative_remap=True)
bpy.ops.render.render(write_still=True)
evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
bounds=[evaluated.matrix_world@Vector(v) for v in evaluated.bound_box]
target=Vector(tuple((min(v[i] for v in bounds)+max(v[i] for v in bounds))*.5 for i in range(3)))
target.z+=.004
cam.location=target+Vector((.38,2.50,.06));aim(cam,target)
camdata.ortho_scale=.49
s.render.resolution_x=860;s.render.resolution_y=820
s.render.filepath=str(base/'Smith_fitted_portrait.png')
bpy.ops.render.render(write_still=True)

