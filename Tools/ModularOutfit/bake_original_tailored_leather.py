"""Bake the accepted fingerless material onto tactical glove UVs in Blender."""
import sys
import json
from pathlib import Path
import bpy
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from original_leather_gloves import PROJECT as P, read, write
import build_tailored_fingerless_candidate as leather

R = P/'SourceAssets/ModularOutfit20260927/OriginalLeatherV2'


def bake(name):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    d = read(R/'Authoring'/f'{name}.json')
    folder = R/'Textures'/name; folder.mkdir(parents=True, exist_ok=True)
    leather.T = folder
    material, color, roughness, bsdf, output = leather.authored_material()
    material.use_fake_user = True
    # Full fingers have no finger-root openings. Source pattern images clamp
    # beyond the palm instead of repeating the wrist-tab pattern on fingertips.
    for node in material.node_tree.nodes:
        if node.type == 'TEX_IMAGE' and node.image and node.image.name.startswith('Tailoring'):
            node.extension = 'EXTEND'
    obj = leather.make_mesh(d, material); obj.name = name+'_OriginalLeatherV2'
    layer = obj.data.uv_layers.new(name='BakedTailoringUV'); obj.data.uv_layers.active = layer; layer.active_render = True
    if name == 'M4':
        for face, coords in zip(obj.data.polygons, d['target_uv']):
            for loop, (u,v) in zip(face.loop_indices, coords): layer.data[loop].uv = (u,1-v)
    else:
        bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=1.25, island_margin=.008, area_weight=.25, correct_aspect=True)
        bpy.ops.object.mode_set(mode='OBJECT'); layer = obj.data.uv_layers['BakedTailoringUV']; layer.active_render = True
    scene = bpy.context.scene; scene.render.engine = 'CYCLES'; scene.cycles.samples = 16; scene.cycles.device = 'CPU'
    scene.cycles.use_denoising = False; scene.render.bake.margin = 12; scene.render.bake.use_selected_to_active = False
    maps = {}; nt = material.node_tree; size = 4096 if name == 'M4' else 2048
    for channel, kind, space in [('BaseColor','EMIT','sRGB'),('Roughness','ROUGHNESS','Non-Color'),('Normal','NORMAL','Non-Color')]:
        im = bpy.data.images.new('T_OriginalLeather_'+channel, width=size, height=size, alpha=False)
        im.colorspace_settings.name = space
        target = nt.nodes.new('ShaderNodeTexImage'); target.image = im; target.select = True; nt.nodes.active = target
        if kind == 'EMIT':
            emission = nt.nodes.new('ShaderNodeEmission'); nt.links.new(color,emission.inputs[0]); nt.links.new(emission.outputs[0],output.inputs[0])
        else: nt.links.new(bsdf.outputs[0],output.inputs[0])
        print('ORIGINAL_TAILORED_BAKE_BEGIN', name, channel, flush=True)
        bpy.ops.object.bake(type=kind, uv_layer=layer.name, normal_space='TANGENT')
        im.filepath_raw = str(folder/('T_OriginalLeather_'+channel+'.png')); im.file_format = 'PNG'; im.save()
        maps[channel] = im; target.select = False
    nt.links.new(bsdf.outputs[0],output.inputs[0])
    baked = leather.baked_material(maps); baked.name = 'M_OriginalLeatherV2_'+name
    obj.data.materials.clear(); obj.data.materials.append(baked)
    d['uv'] = [[(layer.data[i].uv.x,1-layer.data[i].uv.y) for i in face.loop_indices] for face in obj.data.polygons]
    d.pop('target_uv',None)
    for key in ('uv1','uv2','uv3'): d.pop(key,None)
    write(R/'Baked'/f'{name}.json',d)
    leather.rig(obj,d)
    bpy.ops.wm.save_as_mainfile(filepath=str(R/(name+'_OriginalLeatherV2.blend')))
    print('ORIGINAL_TAILORED_BAKED',name,flush=True)


def icon_and_pickup():
    # Keep the user's current full-finger silhouette, camera and empty shell.
    # Replace the display material with the exact same baked maps used in UE.
    bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/ModularOutfit20260927/OriginalLeatherV1/OriginalLeather_Icon.blend'))
    obj = next(o for o in bpy.data.objects if o.type == 'MESH')
    obj.data.uv_layers[0].name = 'BakedTailoringUV'
    maps = {channel: leather.image(R/'Textures/M4'/('T_OriginalLeather_'+channel+'.png'), 'sRGB' if channel=='BaseColor' else 'Non-Color') for channel in ('BaseColor','Roughness','Normal')}
    mat = leather.baked_material(maps); mat.name = 'M_OriginalLeatherV2_M4'
    obj.data.materials[0] = mat
    # Empty inner leather uses a darker instance of the same baked source.
    lining = mat.copy(); lining.name = 'OriginalLeatherV2_Lining'
    nodes, links = lining.node_tree.nodes, lining.node_tree.links; bs = nodes.get('Principled BSDF')
    old = bs.inputs['Base Color'].links[0].from_socket
    mult = nodes.new('ShaderNodeMixRGB'); mult.blend_type = 'MULTIPLY'; mult.inputs[0].default_value = 1
    mult.inputs[2].default_value = (.55,.55,.55,1); links.new(old,mult.inputs[1]); links.new(mult.outputs[0],bs.inputs['Base Color'])
    obj.data.materials[1] = lining
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=str(R/'SM_OriginalLeatherGlovesV2_Pickup.fbx'),use_selection=True,object_types={'MESH'},apply_unit_scale=True,bake_anim=False,use_mesh_modifiers=True,add_leaf_bones=False,mesh_smooth_type='FACE',path_mode='STRIP')
    scene = bpy.context.scene
    # Reuse the accepted fingerless icon exposure and studio lighting contract.
    scene.view_settings.view_transform = 'AgX'; scene.view_settings.look = 'AgX - Medium High Contrast'; scene.view_settings.exposure = -.65
    from mathutils import Vector
    for name,loc,energy,size in [('Key',(-.45,.25,.55),18,.30),('Fill',(.45,-.05,.40),5,.40),('Rim',(.10,.4,.10),8,.20)]:
        light = bpy.data.objects[name]; light.location = loc; light.data.energy = energy; light.data.size = size
        light.rotation_euler = (-Vector(loc)).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath = str(R/'ue_original_gloves.png')
    bpy.ops.wm.save_as_mainfile(filepath=str(R/'OriginalLeatherV2_Icon.blend'))
    bpy.ops.render.render(write_still=True)
    write(R/'artwork.json',dict(texture_groups=['M4','Body'],first_person_texture_size=4096,body_texture_size=2048,
          icon=str(R/'ue_original_gloves.png'),same_baked_maps_in_icon_and_game=True,geometry_changed=False,runtime_tested=False))
    print('ORIGINAL_TAILORED_ARTWORK_SAVED',flush=True)


if __name__ == '__main__':
    for name in ('M4','Body'): bake(name)
    icon_and_pickup()
