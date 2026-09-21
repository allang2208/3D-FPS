import json,sys
from pathlib import Path
import unreal as u
out=Path(u.Paths.project_dir()).resolve()/'SourceAssets/FireMagicRealistic20260922'
out.mkdir(parents=True,exist_ok=True)
lib=u.MaterialEditingLibrary
data={'systems':{},'materials':{}}
paths=['/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Fire/P_Fire_Small',
       '/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Fire/P_flamethrower',
       '/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Explosion/P_Molotov',
       '/Game/Realistic_Starter_VFX_Pack_Vol2/Particles/Explosion/P_Explosion_Big_A',
       '/Game/MilitaryTrench/Particles/P_Fire']
for path in paths:
    a=u.load_asset(path)
    task=u.AssetExportTask();task.object=a;task.filename=str(out/(a.get_name()+'.t3d'))
    task.exporter=u.ObjectExporterT3D();task.automated=True;task.prompt=False;task.replace_identical=True
    data['systems'][path]={'class':a.get_class().get_name(),'exported':u.Exporter.run_asset_export_task(task)}
for path in ['/Game/Realistic_Starter_VFX_Pack_Vol2/Materials/'+n for n in ['M_Fire_B','M_Fire_C','M_Fire_Splat','M_Explosion_B','M_Smoke_C']]+['/Game/MilitaryTrench/Particles/Materials/M_Fire_SubUV']:
    m=u.load_asset(path)
    row={'blend':str(m.get_editor_property('blend_mode')),'nodes':[]}
    for n in lib.get_material_expressions(m):
        item={'name':n.get_name(),'class':n.get_class().get_name(),'inputs':[v.get_name() if v else None for v in lib.get_inputs_for_material_expression(m,n)]}
        for key in ['parameter_name','default_value','constant','code','blend','sampler_type','const_a','const_b','const_exponent','const_period','period']:
            try:item[key]=str(n.get_editor_property(key))
            except Exception:pass
        try:
            t=n.get_editor_property('texture')
            if t:item['texture']={'path':t.get_path_name(),'srgb':t.get_editor_property('srgb')}
        except Exception:pass
        row['nodes'].append(item)
    for prop in ['MP_EMISSIVE_COLOR','MP_OPACITY']:
        n=lib.get_material_property_input_node(m,getattr(u.MaterialProperty,prop))
        row[prop]=n.get_name() if n else None
    data['materials'][path]=row
(out/'source-settings.json').write_text(json.dumps(data,indent=2),encoding='utf8')
print(json.dumps({'systems':data['systems'],'materials':{p:{'blend':v['blend'],'textures':[n['texture'] for n in v['nodes'] if 'texture' in n],'types':sorted(set(n['class'] for n in v['nodes']))} for p,v in data['materials'].items()}},indent=2))
