"""Selected-to-active transfer of V2 leather and physical stitches to V3 UVs."""
import bpy, bmesh, json, time
from pathlib import Path
P=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(P/'StaticField_Design.blend'))
bpy.context.preferences.filepaths.save_version=0
runtime=bpy.data.objects['03_SkivedOverlappingLeather']
low=runtime.copy(); low.data=runtime.data.copy()
bpy.context.scene.collection.objects.link(low); low.name='BAKE_LowLeather'
# Bake the cylindrical UV island only; hidden end caps use overlapping planar UVs.
bm=bmesh.new();bm.from_mesh(low.data)
bmesh.ops.delete(bm,geom=[f for f in bm.faces if len(f.verts)>4],context='FACES')
bm.to_mesh(low.data);bm.free()
bake_mat=bpy.data.materials.new('BAKE_Target');bake_mat.use_nodes=True
low.data.materials.clear();low.data.materials.append(bake_mat)
target=bake_mat.node_tree.nodes.new('ShaderNodeTexImage')
bake_mat.node_tree.nodes.active=target

with bpy.data.libraries.load(str(P.parent/'StaticFieldGripV2/StaticField_Design.blend'),link=False) as (src,dst):
    dst.objects=[n for n in src.objects if n.startswith(('03_SkivedOverlappingLeather','05_TwoPlyStitch_'))]
high=list(dst.objects)
for ob in high: bpy.context.scene.collection.objects.link(ob)
for ob in bpy.context.scene.objects:
    ob.select_set(False)
    ob.hide_render = ob not in high and ob != low
    ob.hide_set(False)
for ob in high: ob.select_set(True)
bpy.context.view_layer.objects.active=high[0]
bpy.ops.object.join(); source=bpy.context.object;source.name='BAKE_V2LeatherAndStitches'
source.select_set(True);low.select_set(True);bpy.context.view_layer.objects.active=low

scene=bpy.context.scene
scene.render.engine='CYCLES';scene.cycles.samples=16
scene.render.bake.use_selected_to_active=True
scene.render.bake.use_cage=False
scene.render.bake.cage_extrusion=.0012
scene.render.bake.max_ray_distance=.003
scene.render.bake.margin=12
scene.render.bake.use_clear=True
scene.render.bake.normal_space='TANGENT'
prefs=bpy.context.preferences.addons['cycles'].preferences
try:
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    for dev in prefs.devices:dev.use=dev.type=='OPTIX'
    if any(d.use for d in prefs.devices):scene.cycles.device='GPU'
except Exception:scene.cycles.device='CPU'

receipt=dict(complete=False,source=str(P.parent/'StaticFieldGripV2/StaticField_Design.blend'),
             target=str(P/'StaticField_Design.blend'),size=[4096,8192],
             projection='selected-to-active; original geometry, micro normals and two-ply stitches',maps=[])
def record():
    (P/'bake_receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
def bake(kind,bake_type):
    image=bpy.data.images.new('Baked_'+kind,width=4096,height=8192,alpha=False,float_buffer=False)
    image.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
    target.image=image
    print('BAKE_START',kind,flush=True)
    bpy.ops.object.bake(type=bake_type)
    image.filepath_raw=str(P/'Textures'/('T_StaticField_Leather_'+kind+'.png'))
    image.file_format='PNG';image.save()
    receipt['maps'].append(dict(kind=kind,path=image.filepath_raw));record()
    bpy.data.images.remove(image)
    print('BAKE_SAVED',kind,flush=True)

# Cycles NORMAL includes the source high mesh's material normal, plus cord geometry.
bake('Normal','NORMAL')
# Emission transfer avoids lighting and preserves exact albedo and packed ORM values.
for kind in ('BaseColor','ORM'):
    for mat in source.data.materials:
        nodes=mat.node_tree.nodes;links=mat.node_tree.links
        out=next(n for n in nodes if n.type=='OUTPUT_MATERIAL')
        emission=nodes.new('ShaderNodeEmission');emission.inputs['Strength'].default_value=1
        sample=next((n for n in nodes if n.type=='TEX_IMAGE' and n.image and '_'+kind in n.image.name),None)
        if sample:links.new(sample.outputs['Color'],emission.inputs['Color'])
        else:emission.inputs['Color'].default_value=(.038,.025,.016,1) if kind=='BaseColor' else (1,.78,0,1)
        links.new(emission.outputs[0],out.inputs['Surface'])
    bake(kind,'EMIT')
receipt['complete']=True;record()
print('V3_LEATHER_BAKE_COMPLETE',flush=True)
