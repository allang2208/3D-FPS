from pathlib import Path
import unreal as u,json
O=Path(__file__).resolve().parent;meta=json.loads((O/'current.json').read_text());L=u.MaterialEditingLibrary;report={}
for k,row in meta.items():
    ob=u.load_asset(row['path']);t=u.AssetExportTask();t.object=ob;t.filename=str(O/'Inputs'/('Current_'+k+'.fbx'));t.exporter=u.StaticMeshExporterFBX();t.options=u.FbxExportOption();t.options.level_of_detail=False;t.options.collision=False;t.automated=True;t.prompt=False;t.replace_identical=True
    if not u.Exporter.run_asset_export_task(t):raise RuntimeError('Export '+k)
    mi=u.load_asset(row['slots']['CS_Receiver']);mat=mi.get_base_material();nodes=L.get_material_expressions(mat)
    r={'instance':mi.get_path_name(),'master':mat.get_path_name(),'scalars':{},'textures':{},'normal_nodes':[]}
    for n in nodes:
        try:pn=str(n.get_editor_property('parameter_name'))
        except Exception:continue
        if isinstance(n,u.MaterialExpressionScalarParameter):r['scalars'][pn]=L.get_material_instance_scalar_parameter_value(mi,pn)
        if isinstance(n,(u.MaterialExpressionTextureSampleParameter2D,u.MaterialExpressionTextureObjectParameter)):
            tex=L.get_material_instance_texture_parameter_value(mi,pn);r['textures'][pn]=tex.get_path_name() if tex else None
    todo=[L.get_material_property_input_node(mat,u.MaterialProperty.MP_NORMAL)];done=set()
    while todo:
        n=todo.pop()
        if not n or n.get_name() in done:continue
        done.add(n.get_name());data={'name':n.get_name(),'type':n.get_class().get_name()}
        for p in ('parameter_name','code','texture','coordinate_index'):
            try:v=n.get_editor_property(p);data[p]=v.get_path_name() if isinstance(v,u.Object) else v
            except Exception:pass
        r['normal_nodes'].append(data);todo.extend(L.get_inputs_for_material_expression(mat,n))
    report[k]=r
(O/'shading.json').write_text(json.dumps(report,indent=2,default=str));print('M24_SHADING_SOURCES_CAPTURED')
