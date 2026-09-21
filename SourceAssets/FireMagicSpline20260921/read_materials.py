import json,sys
from pathlib import Path
import unreal as u
sys.path.insert(0,'D:/FPS3D/FPSGAME/Tools/Skills')
from build_fireball_assets import API,LIB,ref
out=Path(u.Paths.project_dir()).resolve()/'SourceAssets/FireMagicSpline20260921'
system=u.load_asset('/Game/_SplineVFX/NS/NS_Spline_Fire')
data={}
for name in ['Fire_A','Fire_B','FireBackUp','FireAdd','Smoke']:
    d=json.loads(API.call_method('GetRendererData',(ref(system,name,renderer=0),)).get_editor_property('property_values'))
    mi=u.load_asset(d['Material']['refPath'])
    row={'material':mi.get_path_name(),'parent':mi.get_editor_property('parent').get_path_name(),'scalars':{},'vectors':{},'textures':{},'nodes':[],'lifecycle':{}}
    for x in LIB.get_scalar_parameter_names(mi):row['scalars'][str(x)]=LIB.get_material_instance_scalar_parameter_value(mi,x)
    for x in LIB.get_vector_parameter_names(mi):row['vectors'][str(x)]=str(LIB.get_material_instance_vector_parameter_value(mi,x))
    for x in LIB.get_texture_parameter_names(mi):
        t=LIB.get_material_instance_texture_parameter_value(mi,x);row['textures'][str(x)]=t.get_path_name() if t else None
    for e in LIB.get_material_expressions(mi.get_editor_property('parent')):
        row['nodes'].append({'name':e.get_name(),'class':e.get_class().get_name()})
    for x in ['Life Cycle Mode','Loop Behavior','Loop Duration','Inactive Response']:
        row['lifecycle'][x]=u.RainAssetEditor.read_input(system,name,'EmitterUpdateScript','EmitterState',x)
    data[name]=row
(out/'spline-fire-materials.json').write_text(json.dumps(data,indent=2),encoding='utf8')
print(json.dumps({k:{q:v[q] for q in ['material','parent','scalars','textures','lifecycle']} for k,v in data.items()},indent=2))
