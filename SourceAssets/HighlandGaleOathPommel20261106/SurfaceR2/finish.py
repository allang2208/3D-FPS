"""Procedural precious-metal finish, production PBR baking and static-mesh export."""
import json
import bpy
import numpy as np

def material(name,color,metal,rough,grain=True):
    m=bpy.data.materials.new(name);m.use_nodes=True;m.diffuse_color=(*color,1)
    n,l=m.node_tree.nodes,m.node_tree.links
    p=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    p.inputs['Base Color'].default_value=(*color,1);p.inputs['Metallic'].default_value=metal;p.inputs['Roughness'].default_value=rough
    if grain:
        tc=n.new('ShaderNodeTexCoord')
        noise=n.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=8400;noise.inputs['Detail'].default_value=2
        l.new(tc.outputs['Object'],noise.inputs['Vector'])
        remap=n.new('ShaderNodeMapRange');remap.inputs['To Min'].default_value=rough-.025;remap.inputs['To Max'].default_value=rough+.025
        l.new(noise.outputs['Fac'],remap.inputs['Value']);l.new(remap.outputs['Result'],p.inputs['Roughness'])
        bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.12;bump.inputs['Distance'].default_value=.000012
        l.new(noise.outputs['Fac'],bump.inputs['Height']);l.new(bump.outputs['Normal'],p.inputs['Normal'])
        tint=n.new('ShaderNodeMixRGB');tint.blend_type='MULTIPLY';tint.inputs[0].default_value=.055;tint.inputs[1].default_value=(*color,1)
        l.new(noise.outputs['Fac'],tint.inputs[2]);l.new(tint.outputs[0],p.inputs['Base Color'])
    return m

def make_materials():
    return (material('GaleOath_SatinSilver',(.43,.455,.48),.96,.31),
        material('GaleOath_PolishedSilver',(.55,.57,.59),.97,.235),
        material('GaleOath_DarkGunmetal',(.055,.064,.072),.90,.42),
        material('GaleOath_AgedBronze',(.29,.215,.125),.90,.32),
        material('GaleOath_PaleBlueEnamel',(.135,.28,.35),.0,.20,False))

def bake_and_export(scene,parts,body,grip,P,spec):
    bpy.ops.object.select_all(action='DESELECT')
    for o in parts:o.hide_set(False);o.select_set(True)
    bpy.context.view_layer.objects.active=body;bpy.ops.object.join()
    game=bpy.context.object;game.name=spec['mesh'];game.data.name=spec['mesh']
    tri=game.modifiers.new('Production triangles','TRIANGULATE');tri.keep_custom_normals=True
    bpy.ops.object.modifier_apply(modifier=tri.name)
    if not game.data.uv_layers:game.data.uv_layers.new(name='GaleOathAtlas')
    game.data.uv_layers.active=game.data.uv_layers[0]
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.13,island_margin=.0025,area_weight=.8)
    bpy.ops.object.mode_set(mode='OBJECT')
    scene.render.engine='CYCLES';scene.cycles.samples=20
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type='OPTIX';prefs.get_devices()
        devices=[d for d in prefs.devices if d.type=='OPTIX']
        for d in prefs.devices:d.use=d in devices
        if devices:scene.cycles.device='GPU'
    except Exception:pass
    scene.render.bake.use_selected_to_active=False;scene.render.bake.margin=12
    scene.render.bake.use_clear=True;scene.render.bake.normal_space='TANGENT'
    mats=list(game.data.materials);size=4096
    def new_image(name,color=False):
        im=bpy.data.images.new(name,width=size,height=size,alpha=False)
        im.colorspace_settings.name='sRGB' if color else 'Non-Color'
        return im
    def save_image(im):
        im.filepath_raw=str(P/'Textures'/(im.name+'.png'));im.file_format='PNG';im.save()
    def bake(kind,name,channel=None,color=False):
        im=new_image(name,color);restore=[]
        for mat in mats:
            n,l=mat.node_tree.nodes,mat.node_tree.links
            target=n.new('ShaderNodeTexImage');target.image=im;n.active=target
            output=next(x for x in n if x.type=='OUTPUT_MATERIAL');original=output.inputs['Surface'].links[0].from_socket
            em=None
            if channel:
                p=next(x for x in n if x.type=='BSDF_PRINCIPLED');inp=p.inputs[channel]
                em=n.new('ShaderNodeEmission')
                if inp.is_linked:l.new(inp.links[0].from_socket,em.inputs['Color'])
                else:
                    v=inp.default_value;em.inputs['Color'].default_value=tuple(v) if channel=='Base Color' else (v,v,v,1)
                l.new(em.outputs[0],output.inputs['Surface'])
            restore.append((mat,target,em,original,output))
        bpy.ops.object.bake(type=kind)
        for mat,target,em,original,output in restore:
            if em:mat.node_tree.links.new(original,output.inputs['Surface']);mat.node_tree.nodes.remove(em)
            mat.node_tree.nodes.remove(target)
        save_image(im);print('GALE_OATH_BAKED '+name,flush=True);return im
    base=bake('EMIT','T_GaleOath_BaseColor','Base Color',True)
    rough=bake('EMIT','T_GaleOath_Roughness','Roughness')
    metal=bake('EMIT','T_GaleOath_Metallic','Metallic')
    normal=bake('NORMAL','T_GaleOath_NormalGL')
    ao=bake('AO','T_GaleOath_AO')
    packed=np.ones((size*size,4),np.float32)
    values=np.empty(size*size*4,np.float32)
    for ch,im in enumerate((ao,rough,metal)):
        im.pixels.foreach_get(values);packed[:,ch]=values.reshape(-1,4)[:,0]
    orm=new_image('T_GaleOath_ORM');orm.pixels.foreach_set(packed.ravel());save_image(orm)
    del packed,values
    bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_GaleOath_BakeSource.blend'))
    mat=bpy.data.materials.new('M_GaleOath_PBR');mat.use_nodes=True
    n,l=mat.node_tree.nodes,mat.node_tree.links;p=next(x for x in n if x.type=='BSDF_PRINCIPLED')
    for im,pin in ((base,'Base Color'),(rough,'Roughness'),(metal,'Metallic')):
        tex=n.new('ShaderNodeTexImage');tex.image=im;l.new(tex.outputs['Color'],p.inputs[pin])
    tex=n.new('ShaderNodeTexImage');tex.image=normal;nm=n.new('ShaderNodeNormalMap')
    l.new(tex.outputs['Color'],nm.inputs['Color']);l.new(nm.outputs['Normal'],p.inputs['Normal'])
    game.data.materials.clear();game.data.materials.append(mat)
    for f in game.data.polygons:f.material_index=0
    game['interface']='highland_hilt_v1';game['socket_origin']='native factory pommel local Z=0'
    game['design']='Gale Oath, approved Western fantasy concept; model-only candidate'
    fbx=P/'Export'/(spec['mesh']+'.fbx');glb=fbx.with_suffix('.glb')
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
        add_leaf_bones=False,bake_anim=False,mesh_smooth_type='FACE',use_tspace=False)
    bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,
        export_texcoords=True,export_normals=True,export_materials='EXPORT')
    bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'Highland_GaleOath_GameModel.blend'))
    game.data.calc_loop_triangles()
    spec.update(fbx=str(fbx),glb=str(glb),source_editable=str(P/'Highland_GaleOath_Editable.blend'),
        game_blend=str(P/'Highland_GaleOath_GameModel.blend'),
        materials=['M_GaleOath_PBR'],textures={'size':size,'normal_convention':'OpenGL +Y; flip green once on UE import',
        'orm':'R baked AO / G roughness / B metallic','ao_baked':True},
        topology={'vertices':len(game.data.vertices),'triangles':len(game.data.loop_triangles)},
        status='authored and exported; model-only independent import pending')
    (P/'authoring.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
    print('GALE_OATH_MODEL_EXPORTED '+str(fbx),flush=True)
