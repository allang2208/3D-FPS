"""Blender production adaptation of owned TRELLIS masters; no preview or test.

Keep each source GLB untouched. Normalize dimensions and pivots, preserve UVs,
reduce game mesh face count, export real PBR textures and editable .blend files.
"""
import bpy
import json
import re
from pathlib import Path
from mathutils import Vector, Matrix

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'assets.json').read_text(encoding='utf-8'))

def upstream_image(socket,visited=None):
    visited=set() if visited is None else visited
    for link in socket.links:
        node=link.from_node
        if node in visited:continue
        visited.add(node)
        if node.type=='TEX_IMAGE':return node.image
        for pin in node.inputs:
            image=upstream_image(pin,visited)
            if image:return image
    return None

for prop in CFG['props']:
    folder=ROOT/'Generated'/prop['id'];source=folder/'textured_master.glb'
    if not source.exists():
        print('WAITING_MASTER',prop['id'],flush=True);continue
    output=folder/'Game';output.mkdir(exist_ok=True)
    if (output/'asset-manifest.json').exists() and json.loads((output/'asset-manifest.json').read_text()) .get('adaptation_version')==2:
        print('ALREADY_ADAPTED',prop['id'],flush=True);continue
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    points=[o.matrix_world@Vector(v) for o in meshes for v in o.bound_box]
    lo=Vector([min(p[i] for p in points) for i in range(3)])
    hi=Vector([max(p[i] for p in points) for i in range(3)])
    center=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    target=Vector(prop['target_size_cm'])/100
    factors=Vector([target[i]/(hi[i]-lo[i]) for i in range(3)])
    # Bake world transform into each mesh before setting the shared ground pivot.
    for obj in meshes:
        world=obj.matrix_world.copy()
        for vertex in obj.data.vertices:
            p=world@vertex.co-center;vertex.co=Vector([p[i]*factors[i] for i in range(3)])
        obj.parent=None;obj.matrix_world=Matrix.Identity(4)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes:obj.select_set(True)
    bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join();obj=bpy.context.object
    obj.name='SM_Room_'+prop['id'];obj.data.calc_loop_triangles();original=len(obj.data.loop_triangles)
    high=obj.copy();high.data=obj.data.copy();bpy.context.collection.objects.link(high)
    high.name=prop['id']+'_SourceHigh'
    budget=90000
    if original>budget:
        mod=obj.modifiers.new('Game density with original UVs','DECIMATE');mod.ratio=budget/original;mod.use_collapse_triangulate=True
        bpy.ops.object.modifier_apply(modifier=mod.name)
    # Keep source UVs and material partitions. No blanket remesh/fill-holes.
    materials={};texture_paths={}
    for slot in obj.material_slots:
        mat=slot.material
        if not mat:continue
        mat.name='Room_'+prop['id']+'_'+re.sub(r'[^A-Za-z0-9_]','_',mat.name)
        bsdf=next((n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None)
        if not bsdf:raise RuntimeError('No source PBR material: '+mat.name)
        channels={}
        for channel,pin,component in [('BaseColor','Base Color','RGB'),('Roughness','Roughness','G'),('Metallic','Metallic','B')]:
            image=upstream_image(bsdf.inputs[pin])
            if not image:raise RuntimeError('Missing generated PBR image '+prop['id']+' '+channel)
            key=image.as_pointer()
            if key not in texture_paths:
                dest=output/('T_'+prop['id']+'_'+str(len(texture_paths))+'.png')
                image.filepath_raw=str(dest);image.file_format='PNG';image.save();texture_paths[key]=str(dest)
            channels[channel]={'filename':texture_paths[key],'channel':component}
        materials[mat.name]=channels
    # Production tangent normal bake transfers the master's sculpted relief to
    # the reduced game mesh. This is texture authoring, not a scene preview.
    normal=bpy.data.images.new('T_'+prop['id']+'_Normal',2048,2048,alpha=False)
    normal.colorspace_settings.name='Non-Color'
    for slot in obj.material_slots:
        mat=slot.material
        node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=normal
        for n in mat.node_tree.nodes:n.select=False
        node.select=True;mat.node_tree.nodes.active=node
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=1
    scene.render.bake.use_selected_to_active=True;scene.render.bake.cage_extrusion=.025
    scene.render.bake.max_ray_distance=.10;scene.render.bake.margin=8
    bpy.ops.object.select_all(action='DESELECT');high.select_set(True);obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    bpy.ops.object.bake(type='NORMAL')
    normal_path=output/('T_'+prop['id']+'_Normal.png')
    normal.filepath_raw=str(normal_path);normal.file_format='PNG';normal.save()
    for slot in obj.material_slots:
        mat=slot.material;bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
        tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=normal
        bump=mat.node_tree.nodes.new('ShaderNodeNormalMap')
        mat.node_tree.links.new(tex.outputs['Color'],bump.inputs['Color'])
        mat.node_tree.links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
        materials[mat.name]['Normal']={'filename':str(normal_path),'channel':'RGB'}
    high.select_set(False);high.hide_render=True;high.hide_set(True)
    fbx=output/(obj.name+'.fbx')
    bpy.ops.wm.save_as_mainfile(filepath=str(output/(prop['id']+'_Editable.blend')))
    bpy.ops.export_scene.fbx(filepath=str(fbx),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',
                            bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    result={'id':prop['id'],'name':obj.name,'source':str(source),'fbx':str(fbx),'materials':materials,
            'target_cm':prop['target_size_cm'],'source_triangles':original,'game_budget':budget,
            'pivot':'horizontal center, bottom at Z=0','adaptation_version':2,'tests_run':False}
    (output/'asset-manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print('GENERATED_ASSET_ADAPTED',prop['id'],flush=True)
