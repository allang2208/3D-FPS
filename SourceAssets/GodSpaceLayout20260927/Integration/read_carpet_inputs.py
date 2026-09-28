"""Read the existing carpet sources and hub binding for material authoring."""
import json
from pathlib import Path
import unreal as u

root=Path(__file__).parent
out=root/'CarpetSources';out.mkdir(exist_ok=True)
L=u.MaterialEditingLibrary
report={'textures':{},'materials':{},'exported':[]}
tex_root='/Game/SubstrateMaterials/Textures/02_Upholstery/Textiles/'
for variant in ['01','02']:
    for channel in ['BC','N','R']:
        name='T_Carpet_'+variant+'_'+channel
        tex=u.load_asset(tex_root+name)
        if not tex:raise RuntimeError('Existing texture missing '+name)
        report['textures'][name]={'path':tex.get_path_name(),'width':tex.blueprint_get_size_x(),
            'height':tex.blueprint_get_size_y(),'srgb':tex.get_editor_property('srgb'),
            'compression':str(tex.get_editor_property('compression_settings'))}
        if channel=='BC':
            task=u.AssetExportTask();task.object=tex;task.filename=str(out/(name+'.tga'))
            task.exporter=u.TextureExporterTGA();task.automated=True;task.prompt=False;task.replace_identical=True
            if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Cannot read source pixels '+name)
            report['exported'].append(task.filename)
for path in [
    '/Game/SubstrateMaterials/Materials/02_Upholstery/0_Templates/MTP_Carpet',
    '/Game/SubstrateMaterials/Materials/02_Upholstery/5_Carpet/MI_Carpet_Gray_OPBR',
    '/Game/Props/GodSpaceLayout20260927/Materials/M_GodSpaceBlueStone']:
    mat=u.load_asset(path)
    if not mat:raise RuntimeError('Material missing '+path)
    data={'class':mat.get_class().get_name()}
    if isinstance(mat,u.MaterialInstanceConstant):
        data['parent']=mat.get_editor_property('parent').get_path_name()
        for p in ['scalar_parameter_values','vector_parameter_values','texture_parameter_values']:
            data[p]=str(mat.get_editor_property(p))
    elif isinstance(mat,u.Material):
        data['shading_model']=str(mat.get_editor_property('shading_model'))
        data['nodes']=[]
        for node in L.get_material_expressions(mat):
            n={'class':node.get_class().get_name(),'desc':node.get_editor_property('desc')}
            for prop in ['parameter_name','default_value','texture','material_function']:
                try:
                    v=node.get_editor_property(prop)
                    n[prop]=v.get_path_name() if isinstance(v,u.Object) else str(v)
                except Exception:pass
            data['nodes'].append(n)
    report['materials'][path]=data
mesh=u.load_asset('/Game/Props/GodSpaceLayout20260927/Meshes/SM_GodSpaceStructure')
report['structure_slots']=[{'slot':str(s.get_editor_property('material_slot_name')),'imported_slot':str(s.get_editor_property('imported_material_slot_name')),
    'material':s.get_editor_property('material_interface').get_path_name() if s.get_editor_property('material_interface') else None} for s in mesh.get_editor_property('static_materials')]
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
if editor:
    report['editor_world']=str(editor.get_editor_world())
    report['game_world']=str(editor.get_game_world())
report['dirty_content']=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
(root/'Receipts/carpet-inputs.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('CARPET_AUTHORING_INPUTS '+json.dumps({'textures':report['textures'],'structure_slots':report['structure_slots'],
    'editor_world':report.get('editor_world'),'game_world':report.get('game_world'),'exported':report['exported']}))
