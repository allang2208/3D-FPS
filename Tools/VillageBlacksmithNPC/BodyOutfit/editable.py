"""Make the body and workwear editable in their common R4 rest space."""
import bpy,json,numpy as np
from pathlib import Path
P=Path('D:/FPS3D/FPSGAME');O=P/'SourceAssets/VillageBlacksmithNPC20261118/BodyOutfit'
bpy.ops.wm.open_mainfile(filepath=str(P/'SourceAssets/JasonStrong20261117/R4_PoseRefined/Jason_StrongTall_R4.blend'))
bpy.context.preferences.filepaths.save_version=0
body=bpy.data.objects['Jason_StrongTall_R4'];rig=bpy.data.objects['Jason_NativeSkeleton']
for ob in list(bpy.context.scene.objects):
    if ob not in [body,rig] and ob.name!='R4 joint angle components':bpy.data.objects.remove(ob,do_unlink=True)
body.location.x=rig.location.x=0;body.name='SK_Smith_Body';body['UE_asset']='/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Body'
body['skin']='Jason UV with warm weathered skin albedo'
for m in body.data.materials:
    if not m or not m.use_nodes:continue
    for n in m.node_tree.nodes:
        if n.type=='TEX_IMAGE' and n.image:
            nm=n.image.name.split('.')[0]
            if nm in ('T_Jason_body','T_Jason_head'):
                part=nm.split('_')[-1]
                n.image=bpy.data.images.load(str(O/'Textures'/('T_Smith_Skin_'+part+'_BC.png')),check_existing=True)
hidden=bpy.data.materials.new('M_Smith_Covered');hidden.use_nodes=True;hidden.node_tree.nodes.clear()
a=hidden.node_tree.nodes.new('ShaderNodeBsdfTransparent');o=hidden.node_tree.nodes.new('ShaderNodeOutputMaterial')
hidden.node_tree.links.new(a.outputs[0],o.inputs['Surface'])
for i in range(4,len(body.data.materials)):
    if i!=5:body.data.materials[i]=hidden
def material(slot):
    mat=bpy.data.materials.new('M_Smith_'+slot);mat.use_nodes=True
    n,l=mat.node_tree.nodes,mat.node_tree.links;n.clear();sh=n.new('ShaderNodeBsdfPrincipled');output=n.new('ShaderNodeOutputMaterial');l.new(sh.outputs[0],output.inputs['Surface'])
    for kind in ['BC','N','ORM']:
        t=n.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(O/'Textures'/('T_Smith_'+slot+'_'+kind+'.png')))
        if kind!='BC':t.image.colorspace_settings.name='Non-Color'
        if kind=='BC':l.new(t.outputs['Color'],sh.inputs['Base Color'])
        if kind=='N':
            sep=n.new('ShaderNodeSeparateColor');comb=n.new('ShaderNodeCombineColor');inv=n.new('ShaderNodeMath');inv.operation='SUBTRACT';inv.inputs[0].default_value=1.
            l.new(t.outputs[0],sep.inputs[0]);l.new(sep.outputs[0],comb.inputs[0]);l.new(sep.outputs[1],inv.inputs[1]);l.new(inv.outputs[0],comb.inputs[1]);l.new(sep.outputs[2],comb.inputs[2])
            nm=n.new('ShaderNodeNormalMap');l.new(comb.outputs[0],nm.inputs[1]);l.new(nm.outputs[0],sh.inputs['Normal'])
        if kind=='ORM':
            sep=n.new('ShaderNodeSeparateColor');l.new(t.outputs[0],sep.inputs[0]);l.new(sep.outputs[1],sh.inputs['Roughness']);l.new(sep.outputs[2],sh.inputs['Metallic'])
    return mat
d=json.loads((O/'outfit.json').read_text());mats=[material(s) for s in d['material_slots']]
me=bpy.data.meshes.new('SK_Smith_Outfit');me.from_pydata((np.array(d['positions'])*.01).tolist(),[],[tri[::-1] for tri in d['triangles']]);me.update()
ob=bpy.data.objects.new(me.name,me);bpy.context.collection.objects.link(ob)
for mat in mats:me.materials.append(mat)
tex=me.uv_layers.new(name='UVMap')
coords=np.array(d['uv'],dtype=np.float32)[:,::-1,:].copy();coords[:,:,1]=1-coords[:,:,1]
tex.data.foreach_set('uv',coords.ravel())
me.polygons.foreach_set('material_index',d['triangle_materials']);me.polygons.foreach_set('use_smooth',[True]*len(me.polygons))
ns=np.array(d['normals'],dtype=np.float32)[:,::-1,:].reshape(-1,3)
me.normals_split_custom_set(ns.tolist());me.update()
for b in d['bones']:ob.vertex_groups.new(name=b['name'])
for i,ww in enumerate(d['weights']):
    for j,w in ww:
        if w>0:ob.vertex_groups[j].add([i],w,'REPLACE')
mod=ob.modifiers.new('Jason R4 native weights','ARMATURE');mod.object=rig
for key,(start,_,end,_) in d['parts'].items():
    g=ob.vertex_groups.new(name='Pattern | '+key);g.add(list(range(start,end)),1,'REPLACE')
ob['UE_asset']='/Game/Characters/VillageBlacksmithNPC20261118/SK_Smith_Outfit'
bpy.context.scene['preview_note']='R4 smith body and tailored workwear. The textured Meshy head includes hair and beard.'
bpy.context.view_layer.objects.active=ob;ob.select_set(True)
for area in bpy.context.screen.areas:
    if area.type=='VIEW_3D':
        area.spaces.active.region_3d.view_distance=2.7;area.spaces.active.region_3d.view_location=(0,0,.84)
bpy.ops.wm.save_as_mainfile(filepath=str(O/'Smith_Body_Workwear.blend'),relative_remap=True)
print('SMITH_EDITABLE_WORKWEAR_SAVED')
