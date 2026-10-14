import json,sys
from pathlib import Path
import unreal as u
ROOT=Path('D:/FPS3D/FPSGAME')
OUT=ROOT/'SourceAssets/DragonBreath20261013/FlameRestoreR3'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools/Skills'))
import build_dragon_breath as a
report={'game_world':str(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()),'assets':{}}
paths=[a.SOURCE+'/Essentials/Materials/M_Smoke',a.SOURCE+'/Essentials/Materials/M_MasterSpriteMat',a.SOURCE+'/VFX/Materials/MI_TrailSmoke',a.SOURCE+'/VFX/Materials/MI_Particles',a.DEST+'/M_DragonFlame',a.DEST+'/MI_DragonFlame']
for path in paths:
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    name=obj.get_name();row={'class':obj.get_class().get_name()}
    task=u.AssetExportTask();task.object=obj;task.filename=str(OUT/(name+'.t3d'));task.automated=True;task.prompt=False;task.replace_identical=True;task.exporter=u.ObjectExporterT3D()
    row['exported']=u.Exporter.run_asset_export_task(task)
    if isinstance(obj,u.MaterialInstanceConstant):
        row['parent']=obj.get_editor_property('parent').get_path_name()
        for kind in ['scalar','vector','texture','static_switch']:
            names=getattr(a.LIB,'get_'+kind+'_parameter_names')(obj)
            row[kind]={str(n):str(getattr(a.LIB,'get_material_instance_'+kind+'_parameter_value')(obj,n)) for n in names}
    elif isinstance(obj,u.Material):
        row['properties']={p:str(obj.get_editor_property(p)) for p in ['blend_mode','shading_model','use_material_attributes']}
        row['outputs']={str(p):str(a.LIB.get_material_property_input_node(obj,p)) for p in [u.MaterialProperty.MP_EMISSIVE_COLOR,u.MaterialProperty.MP_OPACITY,u.MaterialProperty.MP_MATERIAL_ATTRIBUTES]}
    report['assets'][path]=row
(OUT/'materials.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('DRAGON_MATERIALS '+json.dumps(report))
