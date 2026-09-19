"""Author a 50k-class low mesh and bake color/MR/normal; no test or preview run."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix
P=Path(__file__).resolve().parent
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.open_mainfile(filepath=str(P/'SkeletonStock_Repaired_Master.blend'))
high=bpy.data.objects['SkeletonStock_Repaired_Master'];source=bpy.data.objects['Frozen_5080_Texture_Source']
for i,m in enumerate(high.data.materials):
    if m is None:high.data.materials[i]=source.data.materials[0]

def active(o):
    bpy.ops.object.select_all(action='DESELECT');o.hide_set(False);o.select_set(True);bpy.context.view_layer.objects.active=o

# Restore exact source corners on retained triangles. Boolean-created patches
# and locally relaxed geometry keep their new normals and projected source UVs.
def coord(v):return tuple(round(a,7) for a in v.co)
old={};source.data.calc_loop_triangles();suv=source.data.uv_layers[0]
sn=[n.vector.copy() for n in source.data.corner_normals]
for tri in source.data.loop_triangles:
    corners={coord(source.data.vertices[source.data.loops[i].vertex_index]):(suv.data[i].uv.copy(),sn[i]) for i in tri.loops}
    old[tuple(sorted(corners))]=corners
normals=[n.vector.copy() for n in high.data.corner_normals];uv=high.data.uv_layers[0];restored=0
for f in high.data.polygons:
    keys=[coord(high.data.vertices[high.data.loops[i].vertex_index]) for i in f.loop_indices]
    ref=old.get(tuple(sorted(keys)))
    if ref:
        for i,key in zip(f.loop_indices,keys):uv.data[i].uv=ref[key][0];normals[i]=ref[key][1]
        restored+=1
high.data.normals_split_custom_set(normals)
high.data.uv_layers.active_index=0;high.data.uv_layers[0].active_render=True
for m in dict.fromkeys(high.data.materials):
    if not m or not m.node_tree:continue
    n=m.node_tree.nodes.new('ShaderNodeUVMap');n.uv_map=uv.name
    for t in list(m.node_tree.nodes):
        if t.type=='TEX_IMAGE':m.node_tree.links.new(n.outputs['UV'],t.inputs['Vector'])
active(high);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'SkeletonStock_Repaired_Master.blend'))
print('SOURCE_CORNERS_RETAINED',restored,flush=True)

low=high.copy();low.data=high.data.copy();bpy.context.collection.objects.link(low);low.name='SkeletonStock_Game_Low'
active(low);low.data.calc_loop_triangles();mod=low.modifiers.new('Game low geometry','DECIMATE');mod.ratio=min(1.,49500/len(low.data.loop_triangles));mod.use_collapse_triangulate=True
bpy.ops.object.modifier_apply(modifier=mod.name)
# Source UV0 is retained. A new non-overlapping channel owns the baked images.
low.data.uv_layers.new(name='GameBakeUV1');low.data.uv_layers.active_index=1;low.data.uv_layers[1].active_render=True
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.002,area_weight=.5,correct_aspect=True);bpy.ops.object.mode_set(mode='OBJECT')
target=bpy.data.materials.new('Baking_Target');target.use_nodes=True;low.data.materials.clear();low.data.materials.append(target)
for f in low.data.polygons:f.material_index=0
node=target.node_tree.nodes.new('ShaderNodeTexImage');target.node_tree.nodes.active=node
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=8
scene.render.bake.use_selected_to_active=True;scene.render.bake.cage_extrusion=.003;scene.render.bake.max_ray_distance=.012;scene.render.bake.margin=12;scene.render.bake.use_clear=False
texdir=P/'Textures';texdir.mkdir(exist_ok=True);baked={}
source_links=[]
for mat in dict.fromkeys(high.data.materials):
    nt=mat.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');out=next(n for n in nt.nodes if n.type=='OUTPUT_MATERIAL')
    base=next(l.from_node for l in bs.inputs['Base Color'].links)
    separate=next(l.from_node for l in bs.inputs['Metallic'].links)
    mr=next(l.from_node for l in separate.inputs['Color'].links)
    em=nt.nodes.new('ShaderNodeEmission');source_links.append((nt,bs,out,base,mr,em))

for key in ['BaseColor','MetalRough','Normal']:
    im=bpy.data.images.new('T_SkeletonStock_'+key,4096,4096,alpha=False)
    im.colorspace_settings.name='sRGB' if key=='BaseColor' else 'Non-Color'
    im.generated_color=(.5,.5,1.,1.) if key=='Normal' else (.02,.02,.02,1.) if key=='BaseColor' else (0,.6,0,1.)
    node.image=im;target.node_tree.nodes.active=node
    for nt,bs,out,base,mr,em in source_links:
        if key=='Normal':nt.links.new(bs.outputs['BSDF'],out.inputs['Surface'])
        else:
            nt.links.new((base if key=='BaseColor' else mr).outputs['Color'],em.inputs['Color']);nt.links.new(em.outputs[0],out.inputs['Surface'])
    active(low);high.hide_set(False);high.hide_render=False;high.select_set(True)
    print('BAKE_START',key,flush=True);bpy.ops.object.bake(type='NORMAL' if key=='Normal' else 'EMIT')
    im.filepath_raw=str(texdir/(key+'.png'));im.file_format='PNG';im.save();baked[key]=im
    print('BAKE_SAVED',key,flush=True)
for nt,bs,out,base,mr,em in source_links:nt.links.new(bs.outputs['BSDF'],out.inputs['Surface'])

# Save a practical working material on the low mesh; per-rifle metal variants
# will sample the current receiver finish, preserving this structural normal.
nt=target.node_tree;bs=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED');nt.nodes.remove(node)
uvnode=nt.nodes.new('ShaderNodeUVMap');uvnode.uv_map='GameBakeUV1'
for key,im in baked.items():
    t=nt.nodes.new('ShaderNodeTexImage');t.image=im;nt.links.new(uvnode.outputs['UV'],t.inputs['Vector'])
    if key=='BaseColor':nt.links.new(t.outputs['Color'],bs.inputs['Base Color'])
    elif key=='MetalRough':
        sep=nt.nodes.new('ShaderNodeSeparateColor');nt.links.new(t.outputs['Color'],sep.inputs['Color']);nt.links.new(sep.outputs['Green'],bs.inputs['Roughness']);nt.links.new(sep.outputs['Blue'],bs.inputs['Metallic'])
    else:
        nm=nt.nodes.new('ShaderNodeNormalMap');nm.uv_map='GameBakeUV1';nt.links.new(t.outputs['Color'],nm.inputs['Color']);nt.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
low['uv_channels']='SourceProjectionUV: original source; GameBakeUV1: new baked atlas'
high.hide_render=True;high.hide_set(True);source.hide_render=True;source.hide_set(True);active(low)
low.data.calc_loop_triangles();bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(P/'SkeletonStock_Game_Low_Editable.blend'))
(P/'low_authoring.json').write_text(json.dumps({'source_master':'SkeletonStock_Repaired_Master.blend','restored_original_triangles':restored,'triangles':len(low.data.loop_triangles),'target_triangles':49500,'textures':list(baked),'size':4096,'uv_source':0,'uv_bakes':1,'bake_ray_distance_generator_units':.012,'bake_cage_generator_units':.003,'tested':False,'rendered_preview':False},indent=2))
print('LOW_MESH_SAVED',flush=True)
