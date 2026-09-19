"""Preserve accepted ASH-12 geometry/rig; author normals, bolt skin and PBR maps.

Source normals come from the original FBX through each part's fitted affine
transform, not from recalculating smoothing. Normal TGA alpha is packed data:
never premultiply RGB by alpha (the earlier PNG conversion did that).
No animations are authored or replaced. No preview/test render is performed.
"""
import bpy, bmesh, json, math, sys
import numpy as np
from pathlib import Path
from mathutils import Matrix, Vector

O=Path(__file__).parent
T=O/'Textures'; T.mkdir(exist_ok=True)
OLD=O.parent/'ASH1220260917'
SRC=Path('D:/FPS3D/资产/oden先辈')
PARTS={'Upper':('upper',.45,.70),'Lower':('lower',.47,.70),
       'Front':('frontend',.45,.70),'Sights':('sights',.50,.65),
       'Flash_Hider':('flashhider02',.32,.90),'Magazine':('xmag',.60,.05),
       'Magazine_Base':('mag',.62,.05)}
bpy.ops.wm.open_mainfile(filepath=str(OLD/'ASH12_Editable.blend'))
scene=bpy.context.scene
rig=bpy.data.objects['SK_M4_Infima']; gun=bpy.data.objects['ASH12_Export']
hands=bpy.data.objects['SK_Manny_Arms_Export']
rig.animation_data.action=bpy.data.actions['ASH12_idle']
if rig.animation_data.action.slots:rig.animation_data.action_slot=rig.animation_data.action.slots[0]
scene.frame_set(0);bpy.context.view_layer.update()
before=set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=str(SRC/'fbx/weapon.FBX'),use_custom_normals=True)
source=next(o for o in bpy.data.objects if o not in before and o.type=='MESH')
src=source.data; me=gun.data
deferred={'12 - Default','15 - Default','16 - Default'}
faces=[p for p in src.polygons if src.materials[p.material_index].name.split('.')[0] not in deferred]
used=sorted({v for p in faces for v in p.vertices}); remap={v:i for i,v in enumerate(used)}
if len(used)!=len(me.vertices) or len(faces)!=len(me.polygons):
    raise RuntimeError(f'Authoring source topology changed: {len(used)}/{len(me.vertices)} vertices, {len(faces)}/{len(me.polygons)} faces')
# Original connected-part identities, shared with the first ASH-12 author.
bm=bmesh.new();bm.from_mesh(src);bm.verts.ensure_lookup_table()
seen=set();components=[]
for v in bm.verts:
    if v.index in seen:continue
    stack=[v];seen.add(v.index);members=[]
    while stack:
        cur=stack.pop();members.append(cur.index)
        for e in cur.link_edges:
            other=e.other_vert(cur)
            if other.index not in seen:seen.add(other.index);stack.append(other)
    components.append(members)
bm.free()
component_for={v:i for i,vs in enumerate(components) for v in vs}
bone_for={v.index:gun.vertex_groups[max(v.groups,key=lambda g:g.weight).group].name for v in me.vertices}
# Keep the existing receiver pose. Bind the original closed bolt insert to
# its existing bone without moving any pivot or changing the shared skeleton.
rest={b.name:b.matrix_local.copy() for b in rig.data.bones}
pose={b.name:b.matrix.copy() for b in rig.pose.bones}
bolt=gun.vertex_groups.get('WPN_bolt') or gun.vertex_groups.new(name='WPN_bolt')
bolt_members=[remap[v] for v in components[79] if v in remap]
rebind=rest['WPN_bolt'] @ pose['WPN_bolt'].inverted() @ pose['WPN_root'] @ rest['WPN_root'].inverted()
for vi in bolt_members:
    me.vertices[vi].co=rebind @ me.vertices[vi].co
    for g in list(me.vertices[vi].groups):gun.vertex_groups[g.group].remove([vi])
    bolt.add([vi],1.,'REPLACE');bone_for[vi]='WPN_bolt'
# Fit source positions to the already accepted bind-space positions separately
# for each rigid part. This includes the accepted body-roll/ADS correction.
normal_matrices={};affines={}
for bone in sorted(set(bone_for.values())):
    ids=[i for i,b in bone_for.items() if b==bone]
    a=np.array([list(src.vertices[used[i]].co)+[1.] for i in ids],dtype=np.float64)
    b=np.array([list(me.vertices[i].co) for i in ids],dtype=np.float64)
    x=np.linalg.lstsq(a,b,rcond=None)[0]
    linear=Matrix(x[:3,:].T.tolist())
    normal_matrices[bone]=linear.inverted().transposed()
    affines[bone]=x.tolist()
normals=[]
for p in faces:
    for li in p.loop_indices:
        vi=remap[src.loops[li].vertex_index]
        normals.append((normal_matrices[bone_for[vi]] @ src.corner_normals[li].vector).normalized())
for p in me.polygons:p.use_smooth=True
me.normals_split_custom_set(normals);me.update()
# R = polymer/rubber, G = bare bolt steel, B = muzzle interior.
mask=me.color_attributes.get('SurfaceRegions') or me.color_attributes.new(name='SurfaceRegions',type='BYTE_COLOR',domain='CORNER')
for dst,p in zip(me.polygons,faces):
    center=sum((src.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)
    cid=component_for[p.vertices[0]]
    polymer=cid==82 or (cid==104 and center.x>-4.5 and center.z<-1.05)
    steel=cid==79
    radial=Vector((0,center.y,center.z-.58))
    inner=src.materials[p.material_index].name.split('.')[0]=='07 - Default' and radial.length>1e-5 and p.normal.dot(radial.normalized())<-.55
    for li in dst.loop_indices:mask.data[li].color=(float(polymer),float(steel),float(inner),1.)
me.color_attributes.active_color=mask
bpy.data.objects.remove(source,do_unlink=True)

def rgba_image(name, pixels, filename):
    h,w=pixels.shape[:2]
    im=bpy.data.images.new(name,width=w,height=h,alpha=True)
    im.colorspace_settings.name='Non-Color'; im.alpha_mode='CHANNEL_PACKED'
    im.pixels.foreach_set(pixels.astype(np.float32).ravel())
    im.filepath_raw=str(filename); im.file_format='PNG';im.save()
    return im

# Read straight RGB from original packed TGA, keep it opaque on export. Source
# tangent normals are DirectX; Blender's working material flips Y once only.
norm_images={}; arrays={}
for part,(stem,rough,metal) in PARTS.items():
    im=bpy.data.images.load(str(SRC/'natga'/f'{stem}_n.tga'),check_existing=False)
    im.colorspace_settings.name='Non-Color';im.alpha_mode='CHANNEL_PACKED'
    a=np.empty(len(im.pixels),dtype=np.float32);im.pixels.foreach_get(a)
    a=a.reshape(im.size[1],im.size[0],4)
    n=a[:,:,:3]*2-1;n/=np.maximum(np.linalg.norm(n,axis=2,keepdims=True),1e-6)
    a[:,:,:3]=n*.5+.5;a[:,:,3]=1
    norm_images[part]=rgba_image('T_ASH12_'+part+'_NormalDX',a,T/f'T_ASH12_{part}_NormalDX.png')
    arrays[part]=a.copy()

# Bake local geometric cavity per material region, excluding hands and other
# moving parts. Small radius avoids encoding broad lighting into the surface.
scene.render.engine='CYCLES';scene.cycles.samples=12
scene.render.bake.margin=8;scene.render.bake.use_clear=True
scene.render.bake.use_selected_to_active=False
scene.world=bpy.data.worlds.new('ASH12_BakeWorld')
for obj in scene.objects:obj.hide_render=True
deps=bpy.context.evaluated_depsgraph_get()
posed=bpy.data.meshes.new_from_object(gun.evaluated_get(deps),depsgraph=deps)
receipt={'source_blend':str(OLD/'ASH12_Editable.blend'),'bolt_source_component':79,
         'bolt_author_vertices':len(bolt_members),'normal_affines':affines,'textures':{},
         'state':'Authored and imported; no runtime or visual test'}
for slot,material in enumerate(me.materials):
    part=material.name.removeprefix('M_ASH12_')
    if part not in PARTS:continue
    ps=[p for p in posed.polygons if p.material_index==slot]
    ids=sorted({vi for p in ps for vi in p.vertices});vm={old:new for new,old in enumerate(ids)}
    mesh=bpy.data.meshes.new('Bake_'+part)
    mesh.from_pydata([posed.vertices[i].co for i in ids],[],[[vm[i] for i in p.vertices] for p in ps]);mesh.update()
    uv=mesh.uv_layers.new(name='UVMap');k=0
    for p in ps:
        for li in p.loop_indices:
            uv.data[k].uv=posed.uv_layers.active.data[li].uv;k+=1
    obj=bpy.data.objects.new('Bake_'+part,mesh);scene.collection.objects.link(obj)
    mat=bpy.data.materials.new('BakeAO_'+part);mat.use_nodes=True;mesh.materials.append(mat)
    nodes=mat.node_tree.nodes;nodes.clear();ao=nodes.new('ShaderNodeAmbientOcclusion')
    ao.inputs['Distance'].default_value=.007;ao.only_local=True;ao.samples=16
    emission=nodes.new('ShaderNodeEmission');out=nodes.new('ShaderNodeOutputMaterial')
    mat.node_tree.links.new(ao.outputs['AO'],emission.inputs['Color']);mat.node_tree.links.new(emission.outputs[0],out.inputs['Surface'])
    h,w=arrays[part].shape[:2];im=bpy.data.images.new('AO_'+part,width=w,height=h,alpha=False)
    im.colorspace_settings.name='Non-Color'
    image_node=nodes.new('ShaderNodeTexImage');image_node.image=im;nodes.active=image_node
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    bpy.ops.object.bake(type='EMIT')
    px=np.empty(len(im.pixels),dtype=np.float32);im.pixels.foreach_get(px);px=px.reshape(h,w,4)
    cavity=np.clip(px[:,:,0],.4,1.)
    # Gentle finish variation follows existing structural detail, with very
    # fine grain; no color repaint and no random low-frequency blotches.
    n=arrays[part][:,:,:3]*2-1
    fine=np.random.default_rng(612+slot).uniform(-1,1,(h,w)).astype(np.float32)
    rough,metal=PARTS[part][1:]
    roughmap=np.clip(rough+.055*(1-cavity)+.014*(1-n[:,:,2])+.008*fine,.1,.85)
    packed=np.dstack((cavity,roughmap,np.full((h,w),metal),np.ones((h,w))))
    orm=rgba_image('T_ASH12_'+part+'_ORM',packed,T/f'T_ASH12_{part}_ORM.png')
    receipt['textures'][part]={'normal':str(T/f'T_ASH12_{part}_NormalDX.png'),'orm':str(T/f'T_ASH12_{part}_ORM.png'),'size':[w,h]}
    bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
    # Working material remains editable and uses the same original UV0.
    bsdf=next(n for n in material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    tex=material.node_tree.nodes.new('ShaderNodeTexImage');tex.image=norm_images[part]
    sep=material.node_tree.nodes.new('ShaderNodeSeparateColor');comb=material.node_tree.nodes.new('ShaderNodeCombineColor')
    inv=material.node_tree.nodes.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1
    links=material.node_tree.links;links.new(tex.outputs['Color'],sep.inputs[0]);links.new(sep.outputs[1],inv.inputs[1])
    links.new(sep.outputs[0],comb.inputs[0]);links.new(inv.outputs[0],comb.inputs[1]);links.new(sep.outputs[2],comb.inputs[2])
    nm=material.node_tree.nodes.new('ShaderNodeNormalMap');nm.uv_map='UVMap';links.new(comb.outputs[0],nm.inputs['Color']);links.new(nm.outputs[0],bsdf.inputs['Normal'])
    texorm=material.node_tree.nodes.new('ShaderNodeTexImage');texorm.image=orm
    ch=material.node_tree.nodes.new('ShaderNodeSeparateColor');links.new(texorm.outputs['Color'],ch.inputs[0]);links.new(ch.outputs[1],bsdf.inputs['Roughness']);links.new(ch.outputs[2],bsdf.inputs['Metallic'])
    print('ASH12_SURFACE_AUTHORED',part,flush=True)
bpy.data.meshes.remove(posed)
sys.path.insert(0,str(O))
from working_materials import apply_regions
apply_regions(gun)
for obj in (gun,hands,rig):obj.hide_render=False
bpy.ops.object.select_all(action='DESELECT')
for obj in (gun,hands,rig):obj.select_set(True)
bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.fbx(filepath=str(O/'SK_ASH12_Surface.fbx'),use_selection=True,object_types={'MESH','ARMATURE'},axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=True)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'ASH12_Surface_Editable.blend'))
(O/'authoring.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print('ASH12_SURFACE_AUTHOR_COMPLETE',flush=True)
