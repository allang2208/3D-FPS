"""Adapt the generated icicle into +X centimetre-ready UE meshes. Asset baking only."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
P=Path('D:/FPS3D/FPSGAME/SourceAssets/IceSpike5080_20260915');OUT=P/'Game';OUT.mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.gltf(filepath=str(P/'seed_91571/textured_master_00001_.glb'))
parts=[o for o in bpy.context.scene.objects if o.type=='MESH']
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=parts[0]
if len(parts)>1:bpy.ops.object.join()
high=bpy.context.object;high.name='IceSpike_TRELLIS_Master'
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
lo=[min(v.co[i] for v in high.data.vertices) for i in range(3)];hi=[max(v.co[i] for v in high.data.vertices) for i in range(3)]
axis=max(range(3),key=lambda i:hi[i]-lo[i]);other=[i for i in range(3) if i!=axis]
center=Vector([(lo[i]+hi[i])/2 for i in range(3)]);extent=hi[axis]-lo[axis]
def end_width(upper):
    points=[v.co for v in high.data.vertices if ((v.co[axis]-lo[axis])/extent>.9 if upper else (v.co[axis]-lo[axis])/extent<.1)]
    return sum(max(p[i] for p in points)-min(p[i] for p in points) for i in other)
sign=1 if end_width(True)<end_width(False) else -1
scale=.54/extent
direction=Vector((0,0,0));direction[axis]=sign
rotation=direction.rotation_difference(Vector((1,0,0)))
for v in high.data.vertices:v.co=rotation@((v.co-center)*scale)
for p in high.data.polygons:p.use_smooth=True
high.data.update()
# Store generated textures as authored inputs, before assigning the UE ice shader.
principled=next(n for n in high.active_material.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
base=principled.inputs['Base Color'].links[0].from_node.image
base.filepath_raw=str(OUT/'Ice_BaseColor.png');base.file_format='PNG';base.save()
for idx,img in enumerate([n.image for n in high.active_material.node_tree.nodes if n.type=='TEX_IMAGE' and n.image!=base]):
    img.filepath_raw=str(OUT/f'Ice_MasterMap_{idx}.png');img.file_format='PNG';img.save()
master_faces=len(high.data.polygons)
low=high.copy();low.data=high.data.copy();bpy.context.collection.objects.link(low);low.name='SM_IceSpike_01'
bpy.ops.object.select_all(action='DESELECT');low.select_set(True);bpy.context.view_layer.objects.active=low
dec=low.modifiers.new('GameGeometry','DECIMATE');dec.ratio=min(1,18000/max(1,master_faces));dec.use_collapse_triangulate=True
bpy.ops.object.modifier_apply(modifier=dec.name)
mat=bpy.data.materials.new('Ice_Game_Bake');mat.use_nodes=True;low.data.materials.clear();low.data.materials.append(mat)
for poly in low.data.polygons:poly.material_index=0;poly.use_smooth=True
normal=bpy.data.images.new('Ice_Normal',2048,2048,alpha=False);normal.colorspace_settings.name='Non-Color'
target=mat.node_tree.nodes.new('ShaderNodeTexImage');target.image=normal;mat.node_tree.nodes.active=target
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16
scene.render.threads_mode='FIXED';scene.render.threads=8
scene.render.bake.use_selected_to_active=True;scene.render.bake.cage_extrusion=.006;scene.render.bake.max_ray_distance=.016;scene.render.bake.margin=12
high.select_set(True);low.select_set(True);bpy.context.view_layer.objects.active=low
bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT')
normal.filepath_raw=str(OUT/'Ice_Normal.png');normal.file_format='PNG';normal.save()
# Keep the Blender authoring material editable with the generated base and baked normals.
bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
bc=mat.node_tree.nodes.new('ShaderNodeTexImage');bc.image=base;mat.node_tree.links.new(bc.outputs['Color'],bsdf.inputs['Base Color'])
nm=mat.node_tree.nodes.new('ShaderNodeNormalMap');mat.node_tree.links.new(target.outputs['Color'],nm.inputs['Color']);mat.node_tree.links.new(nm.outputs['Normal'],bsdf.inputs['Normal'])
bsdf.inputs['Roughness'].default_value=.16;bsdf.inputs['Transmission Weight'].default_value=.2;bsdf.inputs['IOR'].default_value=1.31
variants=[low]
for i in (2,3):
    ob=low.copy();ob.data=low.data.copy();bpy.context.collection.objects.link(ob);ob.name=f'SM_IceSpike_{i:02d}'
    for v in ob.data.vertices:
        t=(v.co.x+.27)/.54
        v.co.y*=.94 if i==2 else 1.04
        v.co.z*=1.035 if i==2 else .94
        v.co.y+=math.sin(t*math.pi)*(.004 if i==2 else -.003)
        v.co.z+=math.sin(t*math.pi)*(-.003 if i==2 else .005)
    variants.append(ob)
report={'source':'seed_91571/textured_master_00001_.glb','source_axis':axis,'source_tip_sign':sign,'master_faces':master_faces,'length_cm':54,'export_axis':'+X points to tip','textures':'generated base and source maps, 2K tangent normal baked master to game mesh','variants':[],'rendered':False,'game_tested':False}
for ob in variants:
    color=ob.data.color_attributes.new(name='IceLength',type='BYTE_COLOR',domain='CORNER')
    for loop in ob.data.loops:
        v=ob.data.vertices[loop.vertex_index].co;color.data[loop.index].color=(max(0,min(1,(v.x+.27)/.54)),0,0,1)
    ob.data.color_attributes.active_color=color
    bpy.ops.object.select_all(action='DESELECT');ob.select_set(True);bpy.context.view_layer.objects.active=ob
    bpy.ops.export_scene.fbx(filepath=str(OUT/(ob.name+'.fbx')),use_selection=True,object_types={'MESH'},axis_forward='-Y',axis_up='Z',bake_anim=False,mesh_smooth_type='FACE',use_tspace=True,add_leaf_bones=False)
    report['variants'].append({'name':ob.name,'faces':len(ob.data.polygons)})
high.hide_render=True;high.hide_set(True)
for ob in variants[1:]:ob.hide_render=True;ob.hide_set(True)
bpy.ops.wm.save_as_mainfile(filepath=str(P/'IceSpike5080_Editable.blend'))
(P/'geometry-authoring.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('ICE_SPIKE_GAME_MESHES_EXPORTED',json.dumps(report),flush=True)
