"""User-requested A762 optic binding and material graph inspection; no PIE."""
import unreal as u, json
from pathlib import Path
O=Path(__file__).parent; O.mkdir(exist_ok=True)
L=u.MaterialEditingLibrary
report={'meshes':{},'materials':{},'textures':{},'game_tested':False,'rendered':False}
def serial(v):
    if isinstance(v,u.Object):return v.get_path_name()
    if isinstance(v,u.LinearColor):return [v.r,v.g,v.b,v.a]
    if isinstance(v,(str,int,float,bool)) or v is None:return v
    return str(v)
def material(m):
    p=m.get_path_name()
    if p in report['materials']:return p
    b=m.get_base_material(); d={'base':b.get_path_name(),'class':m.get_class().get_name(),'parameters':{},'nodes':{},'outputs':{}}
    report['materials'][p]=d
    for kind in ['scalar','vector','texture','static_switch']:
        method='get_material_instance_' if isinstance(m,u.MaterialInstanceConstant) else 'get_material_default_'
        d['parameters'][kind]={str(n):serial(getattr(L,method+kind+'_parameter_value')(m,n)) for n in getattr(L,'get_'+kind+'_parameter_names')(b)}
    for prop in ['blend_mode','two_sided','shading_model']:
        try:d[prop]=serial(b.get_editor_property(prop))
        except Exception:pass
    for n in L.get_material_expressions(b):
        e={'class':n.get_class().get_name(),'inputs':[serial(x) for x in L.get_inputs_for_material_expression(b,n)],'input_names':list(map(str,L.get_material_expression_input_names(n)))}
        for prop in ['texture','coordinate_index','parameter_name','default_value','r','constant','const_a','const_b','const_alpha','const_min','const_max','material_function']:
            try:e[prop]=serial(n.get_editor_property(prop))
            except Exception:pass
        t=e.get('texture')
        if t and t not in report['textures']:
            tex=u.load_asset(t)
            report['textures'][t]={'srgb':tex.get_editor_property('srgb'),'compression':str(tex.get_editor_property('compression_settings')),'sources':list(tex.get_editor_property('asset_import_data').extract_filenames())}
        d['nodes'][n.get_path_name()]=e
    for name in ['BASE_COLOR','ROUGHNESS','METALLIC','SPECULAR','NORMAL','AMBIENT_OCCLUSION','OPACITY','OPACITY_MASK','EMISSIVE_COLOR']:
        prop=getattr(u.MaterialProperty,'MP_'+name)
        d['outputs'][name]={'node':serial(L.get_material_property_input_node(b,prop)),'pin':str(L.get_material_property_input_node_output_name(b,prop))}
    return p
for key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring']:
    mesh=u.load_asset('/Game/Weapons/A762/Accessories05/Meshes/SM_A762_'+key)
    report['meshes'][key]={'path':mesh.get_path_name(),'slots':[{'slot':str(s.material_slot_name),'material':material(s.material_interface)} for s in mesh.static_materials]}
body=u.load_asset('/Game/Weapons/A762/Integrated20260920/SK_A762_Manny')
report['meshes']['body']={'path':body.get_path_name(),'slots':[{'slot':str(s.material_slot_name),'material':s.material_interface.get_path_name()} for s in body.materials]}
for s in body.materials:
    if any(x in str(s.material_slot_name).lower() for x in ['receiver','metal03','metal04','rail','sight']):material(s.material_interface)
sources=json.loads((O.parent/'Accessories05/sources.json').read_text())
for key in ['holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring']:
    for s in sources['meshes'][key]['materials']:
        if any(x in s['slot'].lower() for x in ['body','holosight']):material(u.load_asset(s['path']))
(O/'before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
u.log('A762_OPTIC_FINISH_INSPECTED '+str(len(report['materials']))+' materials')
