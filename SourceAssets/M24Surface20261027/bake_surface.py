"""Bake a restrained edge radius into the existing structural normal/UV basis.
No changes to geometry, UVs, weights, morphs or animations of the runtime source.
"""
import bpy,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).resolve().parent;T=O/'Textures';T.mkdir(exist_ok=True)
S=O.parent/'M24CustomScope20261026/Original/GLTF/textures'
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M24ActionLayout20261027/M24_ActionLayout_Editable.blend'),use_scripts=False)
s=bpy.context.scene;r=bpy.data.objects['M24_V9_Rig'];r.animation_data_clear()
for pb in r.pose.bones:pb.matrix_basis=Matrix.Identity(4)
s.frame_set(0);bpy.context.view_layer.update()
for o in s.objects:o.hide_render=o.type!='MESH' or not o.name.startswith('M24_') or 'Arms' in o.name
s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=16
s.render.bake.margin=12;s.render.bake.use_selected_to_active=False;s.render.bake.normal_space='TANGENT'
report={}
for group,stem,size,radius in [('Body','sniper',2048,.00015),('Scope','Scope.002',4096,.00012)]:
    obs=[o for o in s.objects if o.type=='MESH' and any(m and m.name=='M24_'+group for m in o.data.materials)]
    src=bpy.data.images.load(str(S/(stem+'_normal.png')),check_existing=True);src.colorspace_settings.name='Non-Color'
    image=bpy.data.images.new('T_M24_'+group+'_Refined_N',width=size,height=size,alpha=False);image.colorspace_settings.name='Non-Color';image.generated_color=(.5,.5,1,1)
    m=bpy.data.materials.new('Bake_'+group);m.use_nodes=True;n=m.node_tree.nodes;links=m.node_tree.links
    p=next((x for x in n if x.type=='BSDF_PRINCIPLED'),None) or n.new('ShaderNodeBsdfPrincipled')
    out=next((x for x in n if x.type=='OUTPUT_MATERIAL'),None) or n.new('ShaderNodeOutputMaterial')
    links.new(p.outputs['BSDF'],out.inputs['Surface'])
    tex=n.new('ShaderNodeTexImage');tex.image=src
    norm=n.new('ShaderNodeNormalMap');norm.uv_map=obs[0].data.uv_layers[0].name;links.new(tex.outputs['Color'],norm.inputs['Color'])
    bevel=n.new('ShaderNodeBevel');bevel.inputs['Radius'].default_value=radius;bevel.samples=4
    links.new(norm.outputs['Normal'],bevel.inputs['Normal']);links.new(bevel.outputs['Normal'],p.inputs['Normal'])
    target=n.new('ShaderNodeTexImage');target.image=image;n.active=target
    bpy.ops.object.select_all(action='DESELECT')
    for o in obs:
        o.hide_set(False);o.hide_render=False;o.select_set(True);o.data.materials.clear();o.data.materials.append(m)
    bpy.context.view_layer.objects.active=obs[0]
    bpy.ops.object.bake(type='NORMAL',use_clear=True)
    file=T/(image.name+'.png');image.filepath_raw=str(file);image.file_format='PNG';image.save()
    report[group]={'normal':str(file),'source':str(S/(stem+'_normal.png')),'radius_mm':radius*1000,'size':size,'convention':'OpenGL +Y; UE flips green once','uv':0}
    print('M24_NORMAL_BAKED',group,flush=True)
(O/'bake_receipt.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
