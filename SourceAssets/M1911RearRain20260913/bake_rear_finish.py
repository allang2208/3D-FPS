"""Rebake the rear steel islands in place, preserving the accepted UVs and rig."""
import bpy,ast,json
from pathlib import Path
from mathutils import Matrix
O=Path(__file__).parent;T=O/'Textures';T.mkdir(exist_ok=True)
bpy.context.preferences.filepaths.save_version=0
try:bpy.ops.wm.open_mainfile(filepath=str(O.parent/'M1911ReloadTiming20260913/M1911_ReloadReady_Editable.blend'))
except RuntimeError as exc:
    if 'Missing library override hierarchy root data' not in str(exc) or 'SK_M1911_Manny' not in bpy.data.objects:raise
rig=bpy.data.objects['SK_M1911_Manny'];rig.data.pose_position='REST';root=rig.data.bones['WPN_root'].matrix_local.copy()
manifest=json.loads((O.parent/'M1911Hero20260913/textures.json').read_text())['Steel']
targets={'M1911_Hammer','M1911_ThumbSafety','M1911_LanyardLoop','M1911_Detail23','M1911_Detail24','M1911_Detail26','M1911_Detail27','M1911_Detail30','M1911_Detail31','M1911_Detail32','M1911_Detail34','M1911_Detail35','M1911_Detail37','M1911_Detail38','M1911_GripScrew_17','M1911_GripScrew_18','M1911_GripScrew_19','M1911_GripScrew_20'}
source=(O.parent/'M1911Hero20260913/build.py').read_text(encoding='utf-8')
fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='shader')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'<accepted M1911 slide coating>','exec'))
coat=shader('UnifiedRearBluing',(.022,.028,.036),.26,.88)
old=bpy.data.materials[manifest['material']];n=old.node_tree.nodes
bc=next(x for x in n if x.type=='TEX_IMAGE' and x.image and 'BaseColor' in x.image.name).image
orm=next(x for x in n if x.type=='TEX_IMAGE' and x.image and '_ORM' in x.image.name).image
def image_node(material,image):
    node=material.node_tree.nodes.new('ShaderNodeTexImage');node.image=image;return node
cn=coat.node_tree.nodes;cl=coat.node_tree.links;oldorm=image_node(coat,orm);sep=cn.new('ShaderNodeSeparateColor');cl.new(oldorm.outputs[0],sep.inputs[0]);cl.new(sep.outputs[0],cn[coat['orm_node']].inputs[0])
raw=bpy.data.materials.new('UnchangedSteelAtlas');raw.use_nodes=True
rawbc=image_node(raw,bc);raworm=image_node(raw,orm)
copies=[]
for name in manifest['objects']:
    src=bpy.data.objects[name];ob=bpy.data.objects.new('RearBake_'+name,src.data.copy());bpy.context.scene.collection.objects.link(ob)
    ob.data.transform(root.inverted());ob.data.materials.clear();ob.data.materials.append(coat if name in targets else raw)
    for face in ob.data.polygons:face.material_index=0
    copies.append(ob)
bpy.ops.object.select_all(action='DESELECT')
for ob in copies:ob.select_set(True)
bpy.context.view_layer.objects.active=copies[0];bpy.ops.object.join();mesh=bpy.context.object
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=8;s.render.bake.use_selected_to_active=False;s.render.bake.margin=8;s.render.bake.use_clear=True
mesh.hide_render=False;maps={}
for kind in ['BaseColor','ORM']:
    im=bpy.data.images.new('T_M1911_RearUnified_'+kind,width=2048,height=2048,alpha=False);im.colorspace_settings.name='sRGB' if kind=='BaseColor' else 'Non-Color'
    for mat in [coat,raw]:
        ns=mat.node_tree.nodes;ls=mat.node_tree.links;out=next(x for x in ns if x.type=='OUTPUT_MATERIAL');emit=ns.new('ShaderNodeEmission');ls.new(emit.outputs[0],out.inputs['Surface'])
        src=ns[coat['base_node']].outputs[coat['base_socket']] if mat==coat and kind=='BaseColor' else ns[coat['orm_node']].outputs[0] if mat==coat else (rawbc if kind=='BaseColor' else raworm).outputs[0]
        ls.new(src,emit.inputs['Color']);target=image_node(mat,im);ns.active=target
    bpy.ops.object.bake(type='EMIT');im.filepath_raw=str(T/(im.name+'.png'));im.file_format='PNG';im.save();maps[kind]=im
    print('M1911_REAR_ATLAS_BAKED',kind,flush=True)
bpy.data.objects.remove(mesh,do_unlink=True)
finished=old.copy();finished.name='M_M1911_RearUnified_Steel'
for node in finished.node_tree.nodes:
    if node.type=='TEX_IMAGE' and node.image:
        if 'BaseColor' in node.image.name:node.image=maps['BaseColor']
        elif '_ORM' in node.image.name:node.image=maps['ORM']
for name in manifest['objects']:
    ob=bpy.data.objects[name];ob.data.materials.clear();ob.data.materials.append(finished)
    for f in ob.data.polygons:f.material_index=0
rig.data.pose_position='POSE'
(O/'rear_finish.json').write_text(json.dumps({'targets':sorted(targets),'textures':{k:v.filepath_raw for k,v in maps.items()},'preserved':'Original steel-island UVs, structural normal, AO, barrel/chamber finish, bore cavities, accepted mesh and animations'},indent=2),encoding='utf-8')
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(O/'M1911_RearFinish_Editable.blend'))
print('M1911_REAR_FINISH_AUTHORED',flush=True)
