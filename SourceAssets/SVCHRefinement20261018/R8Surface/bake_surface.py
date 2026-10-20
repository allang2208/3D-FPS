"""Production baking: structural tangent normals, local AO and part roughness.
No camera renders, pose edits or skin processing.
"""
import bpy,json,math
from pathlib import Path
O=Path(__file__).parent;T=O/'Textures';T.mkdir(exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=str(O/'SVCH_R8Surface.blend'))
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=12
s.render.threads_mode='FIXED';s.render.threads=8
s.render.bake.use_selected_to_active=False;s.render.bake.use_clear=True;s.render.bake.normal_space='TANGENT'
s.render.bake.margin=12;s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB'
s.view_settings.view_transform='Standard';s.view_settings.look='None';s.view_settings.exposure=0;s.view_settings.gamma=1
objects=[ob for ob in bpy.context.scene.objects if ob.type=='MESH' and ob.name.startswith('SM_SVCH_')]
for ob in bpy.context.scene.objects:
    if ob.type=='MESH':ob.hide_render=True
receipt={'complete':False,'normal_convention':'Blender OpenGL tangent space; UE flips green once',
    'ao':'Local to each rigid component; no moving-part shadows or skin shadows baked','objects':{}}
for ob in objects:
    part=ob.name.removeprefix('SM_SVCH_');res=4096 if part=='Body' else 2048 if part=='Magazine' else 1024 if part=='BoltCarrier' else 512
    ob.hide_render=False
    for mod in list(ob.modifiers):ob.modifiers.remove(mod)
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    slots=[m.name for m in ob.data.materials];density={};ob.data.calc_loop_triangles();uv=ob.data.uv_layers[0]
    for tri in ob.data.loop_triangles:
        a,b,c=[uv.data[i].uv for i in tri.loops];ua=abs((b.x-a.x)*(c.y-a.y)-(b.y-a.y)*(c.x-a.x))*.5
        d=density.setdefault(slots[tri.material_index],[0.,0.]);d[0]+=tri.area;d[1]+=ua
    record={'normal_size':res,'mask_size':max(256,res//2),'slots':slots,'cm_per_uv':{k:100*math.sqrt(a/max(b,1e-12)) for k,(a,b) in density.items()},'outputs':{}}
    materials=[]
    for mat in list(ob.data.materials):
        copy=bpy.data.materials.new('Bake_'+mat.name);copy.use_nodes=True;materials.append(copy)
    ob.data.materials.clear()
    for mat in materials:ob.data.materials.append(mat)
    for kind in ('Normal','AO','Roughness'):
        size=res if kind=='Normal' else max(256,res//2)
        path=T/f'T_SVCH_R8_{part}_{kind}.png'
        if path.exists():
            record['outputs'][kind]=str(path);continue
        img=bpy.data.images.new('BakeTarget',width=size,height=size,alpha=False,float_buffer=False)
        img.colorspace_settings.name='Non-Color'
        for mat in materials:
            nodes=mat.node_tree.nodes;nodes.clear();links=mat.node_tree.links
            out=nodes.new('ShaderNodeOutputMaterial');target=nodes.new('ShaderNodeTexImage');target.image=img;nodes.active=target;target.select=True
            if kind=='Normal':
                bs=nodes.new('ShaderNodeBsdfPrincipled');bevel=nodes.new('ShaderNodeBevel');bevel.samples=8
                bevel.inputs['Radius'].default_value=.00018
                links.new(bevel.outputs['Normal'],bs.inputs['Normal']);links.new(bs.outputs['BSDF'],out.inputs['Surface'])
            else:
                emission=nodes.new('ShaderNodeEmission');links.new(emission.outputs[0],out.inputs['Surface'])
                if kind=='AO':
                    ao=nodes.new('ShaderNodeAmbientOcclusion');ao.samples=16;ao.only_local=True;ao.inputs['Distance'].default_value=.012
                    links.new(ao.outputs['AO'],emission.inputs['Color'])
                else:
                    attribute=nodes.new('ShaderNodeAttribute');attribute.attribute_name='R8Roughness'
                    links.new(attribute.outputs['Fac'],emission.inputs['Color'])
        print('SVCH_BAKE_BEGIN',part,kind,size,flush=True)
        bpy.ops.object.bake(type='NORMAL' if kind=='Normal' else 'EMIT')
        img.filepath_raw=str(path);img.file_format='PNG';img.save()
        record['outputs'][kind]=str(path);bpy.data.images.remove(img)
        print('SVCH_BAKE_SAVED',part,kind,flush=True)
    ob.hide_render=True;receipt['objects'][part]=record
    (O/'bake_receipt.json').write_text(json.dumps(receipt,indent=2))
receipt['complete']=True;(O/'bake_receipt.json').write_text(json.dumps(receipt,indent=2))
print('SVCH_R8_TEXTURE_BAKES_COMPLETE',flush=True)
