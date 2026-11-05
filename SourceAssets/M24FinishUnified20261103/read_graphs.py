import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent;D=json.loads((O/'materials_before.json').read_text());L=u.MaterialEditingLibrary;R={}
for key,index in [('eoth_holographic',0),('kv_scope_4x',0),('thermal_scope',0),('ReceiverStock_Advanced',1)]:
    source=D['meshes'][key]['slots'][index]['material'];m=u.load_asset(source).get_base_material()
    row={'path':m.get_path_name(),'outputs':{},'nodes':{}}
    for prop in ['BASE_COLOR','METALLIC','ROUGHNESS','NORMAL','AMBIENT_OCCLUSION']:
        p=getattr(u.MaterialProperty,'MP_'+prop);n=L.get_material_property_input_node(m,p)
        row['outputs'][prop]=[n.get_name() if n else None,str(L.get_material_property_input_node_output_name(m,p))]
    for n in L.get_material_expressions(m):
        data={'type':n.get_class().get_name(),'inputs':[x.get_name() if x else None for x in L.get_inputs_for_material_expression(m,n)]}
        for prop in ['parameter_name','texture','default_value','constant','r','g','b','a','const_a','const_b','const_alpha','coordinate_index']:
            try:v=n.get_editor_property(prop)
            except Exception:continue
            if isinstance(v,u.Object):v=v.get_path_name()
            elif isinstance(v,u.LinearColor):v=[v.r,v.g,v.b,v.a]
            data[prop]=v
        row['nodes'][n.get_name()]=data
    R[key]=row
(O/'graphs_before.json').write_text(json.dumps(R,indent=2,default=str),encoding='utf-8')
print('M24_GRAPHS_READ',len(R),flush=True)
