"""Read owned explosion authoring inputs; no playback or asset changes."""
import json, sys
from pathlib import Path
import unreal as u
root=Path(u.Paths.project_dir());out=root/'SourceAssets/FireballImpactRealistic20260914'
sys.path.insert(0,str(root/'Tools/Skills'))
from build_fireball_assets import API,LIB,ref,emitters
result={}
for path in ['/Game/NiagaraExamples/Materials/MI_Explosion_8x8','/Game/NiagaraExamples/Materials/MI_ExplosionRoil_8x8']:
    m=u.load_asset(path)
    result[path]={'parent':m.get_editor_property('parent').get_path_name(),
        'scalars':{str(k):LIB.get_material_instance_scalar_parameter_value(m,k) for k in LIB.get_scalar_parameter_names(m)},
        'switches':{str(k):LIB.get_material_instance_static_switch_parameter_value(m,k) for k in LIB.get_static_switch_parameter_names(m)},
        'textures':{str(k):str(LIB.get_material_instance_texture_parameter_value(m,k)) for k in LIB.get_texture_parameter_names(m)}}
s=u.load_asset('/Game/NiagaraExamples/FX_Explosions/NS_Explosion_Small')
result['emitters']=emitters(s)
e='Explosion'
result['lifecycle']={key:u.RainAssetEditor.read_input(s,e,'EmitterUpdateScript','EmitterState',key) for key in ['Life Cycle Mode','Loop Behavior','Loop Duration']}
result['renderer']=json.loads(API.call_method('GetRendererData',(ref(s,e,renderer=0),)).get_editor_property('property_values'))
(out/'sources.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
u.log('FIREBALL_IMPACT_SOURCES_READ')
