"""Bake high-to-game normals and PBR, then export only the new 201 parts."""
import bpy,json
from pathlib import Path
from mathutils import Vector,Matrix

O=Path(__file__).parent;T=O/'Textures';T.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'LMG201_Video26_HighLow.blend'),use_scripts=False)
bpy.context.preferences.filepaths.save_version=0
sc=bpy.context.scene;sc.render.engine='CYCLES';sc.cycles.device='CPU';sc.cycles.samples=16
sc.render.threads_mode='FIXED';sc.render.threads=8
sc.render.bake.use_selected_to_active=True;sc.render.bake.cage_extrusion=.00025
sc.render.bake.max_ray_distance=.0007;sc.render.bake.margin=12
sc.render.bake.normal_space='TANGENT';sc.render.bake.normal_r='POS_X'
sc.render.bake.normal_g='POS_Y';sc.render.bake.normal_b='POS_Z'
for ob in sc.objects:
    if ob.type=='MESH':ob.hide_render=True
receipt={'revision':'Video26','texture_bakes':{},'exports':[],'rendered_preview':False,'runtime_tested':False}

def record():(O/'bake_export.json').write_text(json.dumps(receipt,indent=2))

def select(obs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in obs:ob.hide_set(False);ob.select_set(True)
    bpy.context.view_layer.objects.active=obs[-1]

def bsdf(mat):return next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')

def link_socket(mat,source,dest):
    if source.is_linked:mat.node_tree.links.new(source.links[0].from_socket,dest)
    else:dest.default_value=source.default_value

def source_pass(mat,kind):
    n=mat.node_tree.nodes;l=mat.node_tree.links;b=bsdf(mat)
    out=next(x for x in n if x.type=='OUTPUT_MATERIAL')
    if kind=='Normal':l.new(b.outputs[0],out.inputs['Surface']);return
    emit=n.new('ShaderNodeEmission');emit.name='V26_BakeEmission';emit.inputs['Strength'].default_value=1
    if kind=='BaseColor':link_socket(mat,b.inputs['Base Color'],emit.inputs['Color'])
    else:
        combine=n.new('ShaderNodeCombineColor');combine.mode='RGB'
        ao=n.new('ShaderNodeAmbientOcclusion');ao.samples=16;ao.inside=False;ao.only_local=True
        ao.inputs['Distance'].default_value=.008
        l.new(ao.outputs['AO'],combine.inputs[0])
        link_socket(mat,b.inputs['Roughness'],combine.inputs[1]);link_socket(mat,b.inputs['Metallic'],combine.inputs[2])
        l.new(combine.outputs[0],emit.inputs['Color'])
    l.new(emit.outputs[0],out.inputs['Surface'])

for group,size in [('Body',2048),('FrontSight',1024),('RearSight',1024)]:
    lo=bpy.data.objects['G26_'+group];hi=bpy.data.objects['H26_'+group]
    lo.hide_render=False;hi.hide_render=False
    target=bpy.data.materials.new('M_LMG201_Video26_'+group);target.use_nodes=True
    lo.data.materials.clear();lo.data.materials.append(target)
    for p in lo.data.polygons:p.material_index=0
    shaders=list({m for m in hi.data.materials if m})
    paths={};images={}
    for kind in ['Normal','BaseColor','ORM']:
        image=bpy.data.images.new('T_LMG201_V26_'+group+'_'+kind,width=size,height=size,alpha=False,float_buffer=False)
        image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
        image.generated_color=(.5,.5,1,1) if kind=='Normal' else (0,0,0,1)
        node=target.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
        for n in target.node_tree.nodes:n.select=False
        node.select=True;target.node_tree.nodes.active=node
        for mat in shaders:source_pass(mat,kind)
        select([hi,lo]);bpy.ops.object.bake(type='NORMAL' if kind=='Normal' else 'EMIT',use_clear=True)
        path=T/(image.name+'.png');image.filepath_raw=str(path);image.file_format='PNG';image.save()
        paths[kind]=str(path);images[kind]=image
        receipt['texture_bakes'][group]=paths.copy();record()
        print('VIDEO26_BAKED',group,kind,flush=True)
    # Restore high-poly PBR so the source remains editable after emission baking.
    for mat in shaders:source_pass(mat,'Normal')
    nodes=target.node_tree.nodes;links=target.node_tree.links;b=bsdf(target)
    color=next(n for n in nodes if n.type=='TEX_IMAGE' and n.image==images['BaseColor'])
    normal=next(n for n in nodes if n.type=='TEX_IMAGE' and n.image==images['Normal'])
    orm=next(n for n in nodes if n.type=='TEX_IMAGE' and n.image==images['ORM'])
    links.new(color.outputs['Color'],b.inputs['Base Color'])
    separate=nodes.new('ShaderNodeSeparateColor');separate.mode='RGB';links.new(orm.outputs['Color'],separate.inputs[0])
    links.new(separate.outputs[1],b.inputs['Roughness']);links.new(separate.outputs[2],b.inputs['Metallic'])
    nm=nodes.new('ShaderNodeNormalMap');links.new(normal.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs[0],b.inputs['Normal'])
    hi.hide_render=True;hi.hide_set(True)

rig=bpy.data.objects['SK_M4_Infima'];rig.animation_data_clear();rig.data.pose_position='REST'
root=rig.data.bones['WPN_root'].matrix_local.copy()
body=bpy.data.objects['G26_Body']
ns=[root.to_3x3()@n.vector for n in body.data.corner_normals]
body.data.transform(root);body.data.normals_split_custom_set(ns)
body.parent=rig;body.matrix_parent_inverse=Matrix.Identity(4);body.matrix_basis=Matrix.Identity(4)
body.modifiers.new('Existing201Rig','ARMATURE').object=rig
select([body,rig]);path=O/'Exports/SK_LMG201_Video26_Parts.fbx'
bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH','ARMATURE'},
    axis_forward='-Y',axis_up='Z',add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE')
receipt['exports'].append(str(path))
for group,hinge in [('FrontSight',(.0008,-.54212,.0648)),('RearSight',(.0008,.04252,.0855))]:
    lo=bpy.data.objects['G26_'+group]
    lo.data.transform(Matrix.Translation(-Vector(hinge)))
    lo.matrix_world=Matrix.Identity(4);select([lo]);path=O/'Exports'/('SM_LMG201_'+group+'.fbx')
    bpy.ops.export_scene.fbx(filepath=str(path),use_selection=True,object_types={'MESH'},
        axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE')
    lo.matrix_world=root@Matrix.Translation(Vector(hinge))
    receipt['exports'].append(str(path))
for group in ['Body','FrontSight','RearSight']:
    hi=bpy.data.objects['H26_'+group]
    hi.data.transform(root)
    hi.hide_set(True);hi.hide_render=True
bpy.ops.wm.save_as_mainfile(filepath=str(O/'LMG201_Video26_Editable.blend'))
receipt['status']='high_poly_baked_and_game_parts_exported';record()
import runpy
runpy.run_path(str(O/'finalize_source.py'))
print('VIDEO26_EXPORTS_SAVED',flush=True)
