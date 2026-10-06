"""Capture the exact shared optics and RSH rail authoring inputs, without play."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;P=O.parents[1];OUT=O/'Sources';OUT.mkdir(exist_ok=True)
L=u.MaterialEditingLibrary
paths={k:'/Game/Weapons/AttachmentFinish20260913/M4/Meshes/'+n for k,n in (
 ('holographic','SM_M4_Holographic'),('panoramic_red_dot','SM_PanoramicRedDot'),
 ('prism_scope_2x','SM_PrismScope2X'),('lpvo_1_6x','SM_LPVO1to6X'),('lpvo_ring','SM_LPVORing'))}
paths['eoth_holographic']='/Game/Weapons/CommonHK41620260930/Meshes/SM_Common_eoth_holographic'
report=dict(meshes={},materials={},graphs={},weather={})
def describe(mat):
    path=mat.get_path_name()
    if path in report['materials']:return
    base=mat.get_base_material();params={}
    for kind in ('scalar','vector','texture'):
        params[kind]={}
        for name in getattr(L,'get_'+kind+'_parameter_names')(base):
            prefix='get_material_instance_' if isinstance(mat,u.MaterialInstanceConstant) else 'get_material_default_'
            v=getattr(L,prefix+kind+'_parameter_value')(mat,name)
            params[kind][str(name)]=(v.get_path_name() if v else None) if kind=='texture' else ([v.r,v.g,v.b,v.a] if kind=='vector' else v)
    report['materials'][path]=dict(base=base.get_path_name(),parameters=params,blend=str(base.blend_mode))
    if base.get_path_name() in report['graphs']:return
    nodes=[]
    for n in L.get_material_expressions(base):
        row=dict(name=n.get_name(),cls=n.get_class().get_name())
        for key in ('description','code','parameter_name','r','constant','default_value','coordinate_index'):
            try:
                v=n.get_editor_property(key);row[key]=v if isinstance(v,(str,int,float,bool)) else str(v)
            except Exception:pass
        if isinstance(n,u.MaterialExpressionCustom):row['inputs']=[str(i.get_editor_property('input_name')) for i in n.get_editor_property('inputs')]
        row['connections']=[v.get_name() if v else None for v in L.get_inputs_for_material_expression(base,n)]
        nodes.append(row)
    outputs={}
    for c in ('BASE_COLOR','ROUGHNESS','METALLIC','NORMAL','AMBIENT_OCCLUSION'):
        prop=getattr(u.MaterialProperty,'MP_'+c);node=L.get_material_property_input_node(base,prop)
        outputs[c]=[node.get_name() if node else None,str(L.get_material_property_input_node_output_name(base,prop))]
    report['graphs'][base.get_path_name()]=dict(nodes=nodes,outputs=outputs)
for key,path in paths.items():
    mesh=u.load_asset(path)
    if not mesh:raise RuntimeError('Missing shared optic '+path)
    task=u.AssetExportTask();task.object=mesh;task.filename=str(OUT/(key+'.fbx'));task.automated=True;task.prompt=False
    task.exporter=u.StaticMeshExporterFBX();task.options=u.FbxExportOption();task.options.level_of_detail=False
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Export '+key)
    slots=[]
    for s in mesh.static_materials:
        slots.append(dict(slot=str(s.material_slot_name),material=s.material_interface.get_path_name()))
        describe(s.material_interface)
    sockets={}
    for name in ('SightRear','SightFront','SightUp','AimCenter','ZoomRing'):
        s=mesh.find_socket(name)
        if s:sockets[name]=[s.relative_location.x,s.relative_location.y,s.relative_location.z]
    report['meshes'][key]=dict(source=path,fbx=task.filename,slots=slots,sockets_cm=sockets)
describe(u.load_asset('/Game/Weapons/RSH12/Materials/MI_RSH12_SourcePBR'))
for path in ('/Game/Weather/RainVisibility/DA_WeatherPresentation','/Game/Weapons/RSH12/Materials/DA_RSH12_WetMaterials','/Game/Weapons/HK416/Reworked20260930/DA_HK416_WetMaterials'):
    table=u.load_asset(path)
    if table:
        report['weather'].update({str(k):v.get_path_name() for k,v in table.get_editor_property('wet_materials').items() if v})
for path in list(report['materials']):
    if report['weather'].get(path):describe(u.load_asset(report['weather'][path]))
(O/'inputs.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('RSH_OPTIC_INPUTS_CAPTURED',len(report['meshes']),len(report['materials']),flush=True)
