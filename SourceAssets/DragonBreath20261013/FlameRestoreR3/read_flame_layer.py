import json,sys
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME');OUT=ROOT/'SourceAssets/DragonBreath20261013/FlameRestoreR3'
lib=u.MaterialEditingLibrary
report={}
for name in ['M_RadialBurnDecal','M_RadialBurnDecalBlack']:
    m=u.load_asset('/Game/RPG-FlameAttackVFX/Essentials/Materials/'+name)
    task=u.AssetExportTask();task.object=m;task.filename=str(OUT/(name+'.t3d'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.ObjectExporterT3D()
    u.Exporter.run_asset_export_task(task)
    report[name]={'domain':str(m.get_editor_property('material_domain')),'emission':str(lib.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)),'nodes':[]}
    for n in lib.get_material_expressions(m):
        row={'name':n.get_name(),'class':n.get_class().get_name(),'inputs':[str(x.get_name()) if x else None for x in lib.get_inputs_for_material_expression(m,n)]}
        for p in ['parameter_name','default_value','texture','material_function','code']:
            try:row[p]=str(n.get_editor_property(p))
            except Exception:pass
        report[name]['nodes'].append(row)
tex=u.load_asset('/Game/RPG-FlameAttackVFX/Essentials/Textures/T_TiledFire')
task=u.AssetExportTask();task.object=tex;task.filename=str(OUT/'T_TiledFire.tga');task.automated=True;task.prompt=False;task.replace_identical=True
report['texture_exported']=u.Exporter.run_asset_export_task(task)
registry=u.AssetRegistryHelpers.get_asset_registry()
report['map_dependencies']=[str(x) for x in registry.get_dependencies('/Game/RPG-FlameAttackVFX/Map/L_RPG-FlameAttackVFX',u.AssetRegistryDependencyOptions(include_soft_package_references=True,include_hard_package_references=True))]
(OUT/'flame-layer.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('FLAME_LAYER '+json.dumps(report))
