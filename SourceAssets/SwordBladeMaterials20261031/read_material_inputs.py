from pathlib import Path
import json,unreal as u
P=Path(__file__).resolve().parent;L=u.MaterialEditingLibrary
report={}
def read(m):
    if m.get_path_name() in report:return
    r={'class':m.get_class().get_name()};report[m.get_path_name()]=r
    if isinstance(m,u.MaterialInstanceConstant):
        parent=m.get_editor_property('parent');r['parent']=parent.get_path_name();read(parent);return
    r['outputs']={}
    for field in ('MP_FRONT_MATERIAL','MP_BASE_COLOR','MP_NORMAL','MP_ROUGHNESS','MP_METALLIC'):
        node=L.get_material_property_input_node(m,getattr(u.MaterialProperty,field))
        r['outputs'][field]=node.get_name() if node else None
    r['nodes']=[]
    for n in L.get_material_expressions(m):
        entry={'node':n.get_name(),'class':n.get_class().get_name(),'inputs':{}}
        for name,source in zip(L.get_material_expression_input_names(n),L.get_inputs_for_material_expression(m,n)):
            if source:entry['inputs'][str(name)]=[source.get_name(),L.get_input_node_output_name_for_material_expression(n,source)]
        if isinstance(n,u.MaterialExpressionTextureSample):entry['texture']=n.texture.get_path_name() if n.texture else None
        if isinstance(n,u.MaterialExpressionScalarParameter):entry['parameter']=str(n.get_editor_property('parameter_name'))
        r['nodes'].append(entry)
for path in ('/Game/Weapons/AzureRunesword20260913/M_AzureRunesword','/Game/Weapons/AzureRunesword20260913/NativeRuneGold20260922/MI_AzureRunesword_NativeGold','/Game/Weapons/AzureRunesword20260913/SilverRune20261030/MI_AzureRunesword_NativeSilver'):read(u.load_asset(path))
(P/'material-inputs.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print('BLADE_MATERIAL_INPUTS',[(k,v.get('outputs',v.get('parent'))) for k,v in report.items()])
