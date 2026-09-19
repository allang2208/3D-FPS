"""Read source sky material graphs/presets for the hills authoring task; no map loads."""
import json
from pathlib import Path
import unreal as u

OUT=Path('D:/FPS3D/FPSGAME/Saved/HillsHDRSky20260915')
OUT.mkdir(exist_ok=True)
LIB=u.MaterialEditingLibrary
report={'materials':[], 'blueprints':[], 'graphs':[]}
for name in ('MI_Sky_Sunshine','MI_Sky_Sunrise','MI_Sky_Sunset','MI_HDR_Night_Sky','MI_Night_Sky'):
    m=u.load_asset('/Game/PWL_Light_Manager/Shader/'+name)
    entry={'path':m.get_path_name(),'parent':m.get_editor_property('parent').get_path_name()}
    entry['scalars']={str(n):LIB.get_material_instance_scalar_parameter_value(m,n) for n in LIB.get_scalar_parameter_names(m)}
    entry['vectors']={str(n):str(LIB.get_material_instance_vector_parameter_value(m,n)) for n in LIB.get_vector_parameter_names(m)}
    entry['textures']={str(n):str(LIB.get_material_instance_texture_parameter_value(m,n)) for n in LIB.get_texture_parameter_names(m)}
    report['materials'].append(entry)
master=u.load_asset('/Game/PWL_Light_Manager/Shader/M_Cubemap_Sky_Material')
report['master']={name:str(master.get_editor_property(name)) for name in ('shading_model','two_sided','is_sky','blend_mode')}
seen=set()
def walk(node):
    if not node or node.get_path_name() in seen:return
    seen.add(node.get_path_name())
    row={'name':node.get_name(),'type':node.get_class().get_name(),
         'pins':[str(n) for n in LIB.get_material_expression_input_names(node)]}
    for prop in ('parameter_name','default_value','r','g','b','a','texture','const_a','const_b','function','material_function','code','collection'):
        try:row[prop]=str(node.get_editor_property(prop))
        except Exception:pass
    inputs=LIB.get_inputs_for_material_expression(master,node)
    row['inputs']=[i.get_name() if i else None for i in inputs]
    report['graphs'].append(row)
    for i in inputs:walk(i)
walk(LIB.get_material_property_input_node(master,u.MaterialProperty.MP_EMISSIVE_COLOR))
for path in ('/Game/Lighting/BP_FPS_DayNightManager',
             '/Game/PWL_Light_Manager/Blueprint/BP_Lighting_Manager',
             '/Game/PWL_Light_Manager/Blueprint/LS_HDR_Sunshine',
             '/Game/PWL_Light_Manager/Blueprint/LS_HDR_Sunshine_02',
             '/Game/PWL_Light_Manager/Data/LD_Sky'):
    bp=u.load_asset(path)
    if not bp:continue
    row={'path':path,'type':bp.get_class().get_name()}
    task=u.AssetExportTask()
    task.set_editor_property('object',bp)
    task.set_editor_property('filename',str(OUT/(bp.get_name()+'.copy')))
    task.set_editor_property('automated',True)
    task.set_editor_property('prompt',False)
    row['source_exported']=u.Exporter.run_asset_export_task(task)
    report['blueprints'].append(row)
(OUT/'sources.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
u.log('DAYNIGHT_SKY_SOURCES_READ')
