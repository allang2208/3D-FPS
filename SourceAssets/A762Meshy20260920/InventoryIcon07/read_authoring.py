import bpy,json
from pathlib import Path
O=Path(__file__).parent
bpy.ops.wm.open_mainfile(filepath=str(O.parent/'Accessories05/A762_AccessoryReady_Editable.blend'))
r={'layers':[{'name':x.name,'override':x.material_override.name if x.material_override else None} for x in bpy.context.scene.view_layers],'sights':[],'materials':{}}
for ob in bpy.data.objects:
    if ob.name.startswith('SM_A762_'):
        r['sights'].append({'name':ob.name,'data':ob.data.name,'min':[min(v.co[i] for v in ob.data.vertices) for i in range(3)],'max':[max(v.co[i] for v in ob.data.vertices) for i in range(3)]})
for name in ['M_A762_UpperReceiver03','M_A762_FactoryStock_Rubber04','M_A762_Rail']:
    m=bpy.data.materials[name];r['materials'][name]={'use_nodes':m.use_nodes,'diffuse':list(m.diffuse_color),'nodes':[]}
    for n in m.node_tree.nodes:
        e={'type':n.type,'name':n.name}
        if n.type=='BSDF_PRINCIPLED':e.update(color=list(n.inputs['Base Color'].default_value),metal=n.inputs['Metallic'].default_value,rough=n.inputs['Roughness'].default_value)
        r['materials'][name]['nodes'].append(e)
(O/'authoring_input.json').write_text(json.dumps(r,indent=2),encoding='utf-8')
