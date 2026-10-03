import json,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/Skills')
from build_fireball_assets import API,LIB,ref,emitters
out=Path(u.Paths.project_dir()).resolve()/'SourceAssets/FireMagicSplineBlackFix20260921'
out.mkdir(parents=True,exist_ok=True)
base='/Game/Skills/FireMagic20260921/SplineV4/'
data={'materials':{},'renderers':{}}
for path in [base+'M_SplineFireSoft',base+'MI_SplineFireFlame',base+'MI_SplineFireFury',base+'MI_SplineSmoke','/Game/Skills/Fireball/TorchBurn20260921/M_FireballTorchErosion']:
    obj=u.load_asset(path)
    if not obj:raise RuntimeError('Missing '+path)
    mi=isinstance(obj,u.MaterialInstanceConstant)
    parent=obj.get_editor_property('parent') if mi else obj
    row={'parent':parent.get_path_name(),'blend':str(parent.get_editor_property('blend_mode')),'shading':str(parent.get_editor_property('shading_model')),'scalars':{},'textures':{},'nodes':[]}
    if mi:
        for p in LIB.get_scalar_parameter_names(obj):row['scalars'][str(p)]=LIB.get_material_instance_scalar_parameter_value(obj,p)
        for p in LIB.get_texture_parameter_names(obj):
            t=LIB.get_material_instance_texture_parameter_value(obj,p)
            row['textures'][str(p)]={'path':t.get_path_name(),'srgb':t.get_editor_property('srgb'),'compression':str(t.get_editor_property('compression_settings'))} if t else None
    for p in ['MP_EMISSIVE_COLOR','MP_OPACITY']:
        node=LIB.get_material_property_input_node(parent,getattr(u.MaterialProperty,p))
        row[p]=node.get_name() if node else None
    for n in LIB.get_material_expressions(parent):
        item={'name':n.get_name(),'class':n.get_class().get_name()}
        for key in ['parameter_name','default_value','code','sampler_type','blend']:
            try:item[key]=str(n.get_editor_property(key))
            except Exception:pass
        item['inputs']=[x.get_name() if x else None for x in LIB.get_inputs_for_material_expression(parent,n)]
        row['nodes'].append(item)
    data['materials'][path]=row
for name in ['NS_ArmorSplineFire','NS_MeteorSplineWake']:
    s=u.load_asset(base+name)
    data['renderers'][name]={e:json.loads(API.call_method('GetRendererData',(ref(s,e,renderer=0),)).get_editor_property('property_values')) for e in emitters(s)}
(out/'before.json').write_text(json.dumps(data,indent=2),encoding='utf8')
print(json.dumps({k:{'blend':v['blend'],'shading':v['shading'],'scalars':v['scalars'],'textures':v['textures'],'exposure_nodes':[n['class'] for n in v['nodes'] if 'EyeAdaptation' in n['class']],'emissive':v['MP_EMISSIVE_COLOR']} for k,v in data['materials'].items()},indent=2))
