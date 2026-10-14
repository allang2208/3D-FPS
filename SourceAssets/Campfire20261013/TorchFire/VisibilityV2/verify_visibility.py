import unreal as u
import json,sys
from pathlib import Path
OUT=Path(__file__).resolve().parent
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/Skills')
from build_fireball_assets import API,ref,emitters,LIB
H=getattr(u,'CampfireAssetTools',getattr(u,'RainAssetEditor',None));assert H
base='/Game/Building/Campfire20261013/TorchFire';s=u.load_asset(base+'/NS_CampfireTorchFire');m=u.load_asset(base+'/M_CampfireTorchFire')
assert s and m and H.compile_rain(s)
assert set(emitters(s))=={'Fire','Smoke','Sparks'}
rows={}
for name in emitters(s):
    top=API.call_method('GetEmitterTopology',(ref(s,name),))
    classes=[str(x) for x in top.get_editor_property('renderer_classes')]
    assert len(classes)==1 and 'SpriteRenderer' in classes[0]
    dat=json.loads(API.call_method('GetEmitterData',(ref(s,name),)).get_editor_property('property_values'))
    assert dat['bLocalSpace'] and dat['CalculateBoundsMode']=='Fixed'
    rows[name]={'renderers':classes,'local_space':dat['bLocalSpace'],'bounds':dat['FixedBounds'],'rate':H.read_input(s,name,'EmitterUpdateScript','SpawnRate','SpawnRate')}
assert rows['Fire']['rate']=='(Value=16.000000)'
alpha=H.read_input(s,'Fire','ParticleUpdateScript','ScaleColor','Scale Alpha')
dissolve=H.read_input(s,'Fire','ParticleUpdateScript','DynamicMaterialParameters','Index 0 Param 2')
assert '.65' in alpha and '.95' in alpha and '.9+.4' in dissolve
nodes=LIB.get_material_expressions(m);eye=[n for n in nodes if isinstance(n,u.MaterialExpressionEyeAdaptationInverse)]
assert len(eye)==1 and LIB.get_material_property_input_node(m,u.MaterialProperty.MP_EMISSIVE_COLOR)==eye[0]
gain=next(n for n in nodes if n.get_name()=='MaterialExpressionMultiply_0').get_editor_property('const_b')
assert abs(gain-.12)<.0001
system=json.loads(API.call_method('GetSystemData',(s,)).get_editor_property('property_values'));assert system['bFixedBounds']
report={'loaded_from_saved_packages':True,'niagara_valid':True,'emitters':rows,'alpha':alpha,'dissolve':dissolve,'eye_adaptation_inverse_nodes':len(eye),'emissive_gain':gain,'fixed_bounds':system['FixedBounds'],'runtime_tested':False,'visual_preview_performed':False,'gpu_render_validation':False}
(OUT/'visibility-verified.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('CAMPFIRE_VISIBILITY_DISK_VERIFIED')
