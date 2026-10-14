"""Read authoring sources only; no world, simulation, screenshot or asset save."""
import json
import sys
from pathlib import Path
import unreal as u

root=Path(u.Paths.convert_relative_path_to_full(u.Paths.project_dir()))
sys.path.insert(0,str(root/'Tools/Skills'))
from build_fireball_assets import API,LIB,ref,emitters
s=u.load_asset('/Game/Props/RomanColumn20260915/NS_TorchFlame')
report={'system':s.get_path_name(),'emitters':[]}
for name in emitters(s):
    top=API.call_method('GetEmitterTopology',(ref(s,name),))
    row={'name':name,'renderer':json.loads(API.call_method('GetRendererData',(ref(s,name,renderer=0),)).get_editor_property('property_values')),'modules':{}}
    for phase in ('emitter_update_script','particle_spawn_script','particle_update_script'):
        row['modules'][phase]=[str(m.get_editor_property('module_name')) for m in top.get_editor_property(phase).get_editor_property('modules')]
    material=row['renderer'].get('Material')
    if isinstance(material,dict):material=material.get('refPath')
    row['material']=material
    if isinstance(material,str):
        mat=u.load_asset(material)
        if isinstance(mat,u.MaterialInstanceConstant):
            row['material_parent']=mat.get_editor_property('parent').get_path_name()
            row['scalars']={str(k):LIB.get_material_instance_scalar_parameter_value(mat,k) for k in LIB.get_scalar_parameter_names(mat)}
        if mat:
            base=mat.get_base_material()
            row['refraction_method']=str(base.get_editor_property('refraction_method'))
            row['refraction_input']=str(LIB.get_material_property_input_node(base,u.MaterialProperty.MP_REFRACTION))
    if name.startswith('NE_Flame_'):
        row['sprite_scale']=u.RainAssetEditor.read_input(s,name,'ParticleUpdateScript','ScaleSpriteSize','Uniform Curve Scale')
    report['emitters'].append(row)
out=root/'SourceAssets/Campfire20261012/flame-source-read.json'
out.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
print('CAMPFIRE_FLAME_SOURCE',out)
