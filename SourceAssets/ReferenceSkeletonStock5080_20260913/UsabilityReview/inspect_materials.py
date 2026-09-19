import bpy, json
from pathlib import Path
root=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(root/'seed_91379/SkeletonStock_5080_Candidate_Editable.blend'))
report={'materials':[], 'images':[], 'objects':[], 'overrides':[]}
for m in bpy.data.materials:
    d={'name':m.name,'use_nodes':m.use_nodes,'nodes':[],'links':[]}
    if m.node_tree:
        for n in m.node_tree.nodes:
            nd={'type':n.type,'name':n.name}
            if n.type=='TEX_IMAGE': nd['image']=n.image.name if n.image else None
            if n.type=='BSDF_PRINCIPLED':
                nd['inputs']={k: list(n.inputs[k].default_value) if k=='Base Color' else n.inputs[k].default_value for k in ['Base Color','Roughness','Metallic']}
            d['nodes'].append(nd)
        d['links']=[{'from':f'{l.from_node.name}.{l.from_socket.name}','to':f'{l.to_node.name}.{l.to_socket.name}'} for l in m.node_tree.links]
    report['materials'].append(d)
for im in bpy.data.images:
    report['images'].append({'name':im.name,'path':im.filepath,'size':list(im.size),'color_space':im.colorspace_settings.name,'packed_bytes':len(im.packed_file.data) if im.packed_file else 0,'sample_rgba':list(im.pixels[:4])})
for ob in bpy.context.scene.objects:
    if ob.type=='MESH': report['objects'].append({'name':ob.name,'materials':[m.name for m in ob.data.materials],'active_material':ob.active_material.name if ob.active_material else None})
report['overrides']=[{'name':v.name,'override':v.material_override.name if v.material_override else None} for v in bpy.context.scene.view_layers]
(Path(__file__).resolve().parent/'material_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2),flush=True)
