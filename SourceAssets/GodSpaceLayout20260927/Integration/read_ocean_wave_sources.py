"""Source inspection for the reported streaking; no game/render or asset edits."""
import json
from pathlib import Path
import unreal as u
root=Path(__file__).parent/'OceanWaveSources';root.mkdir(exist_ok=True)
L=u.MaterialEditingLibrary;report={'textures':{},'materials':{}}
names=['T_Ocean_Waves01_Normals','T_Ocean_Waves02_Normals','T_Water_Normal','T_Water_Normal_Large','T_Water_Normal_Subtle']
for name in names:
    t=u.load_asset('/Game/WaterMaterials/Textures/'+name)
    report['textures'][name]={'size':[t.blueprint_get_size_x(),t.blueprint_get_size_y()],**{p:str(t.get_editor_property(p)) for p in ['srgb','compression_settings','lod_group','address_x','address_y']}}
    task=u.AssetExportTask();task.object=t;task.filename=str(root/(name+'.png'));task.exporter=u.TextureExporterPNG()
    task.automated=True;task.prompt=False;task.replace_identical=True
    if not u.Exporter.run_asset_export_task(task):raise RuntimeError('Texture source export failed '+name)
for name in ['M_Ocean','M_Ocean_Cheaper','M_Ocean_Distance']:
    m=u.load_asset('/Game/WaterMaterials/Materials/'+name);rows=[]
    for n in L.get_material_expressions(m):
        row={'class':n.get_class().get_name(),'desc':str(n.get_editor_property('desc'))}
        if isinstance(n,u.MaterialExpressionTextureSample):row.update(texture=str(n.get_editor_property('texture')),sampler=str(n.get_editor_property('sampler_type')))
        if isinstance(n,u.MaterialExpressionMaterialFunctionCall):row['function']=str(n.get_editor_property('material_function'))
        if isinstance(n,u.MaterialExpressionCustom):row['code']=n.get_editor_property('code')
        if isinstance(n,(u.MaterialExpressionScalarParameter,u.MaterialExpressionVectorParameter)):
            row.update(parameter=str(n.get_editor_property('parameter_name')),value=str(n.get_editor_property('default_value')))
        if len(row)>2:rows.append(row)
    report['materials'][name]=rows
(root/'sources.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print('OCEAN_WAVE_SOURCES '+json.dumps(report['textures']))
