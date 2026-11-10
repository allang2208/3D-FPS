"""Read only the renderer/material inputs used by hammer visibility tuning."""
import json
import sys
from pathlib import Path
import unreal as u

ROOT = Path('D:/FPS3D/FPSGAME')
sys.path.insert(0, str(ROOT/'Tools/Fluids'))
from author_flame_armor_v2 import API, LIB, ref
system = u.load_asset('/Game/Skills/FlameArmor20261109/HammerSurfaceV13/NS_FlameArmorHammer')
renderer = json.loads(API.call_method('GetRendererData', (ref(system, 'HammerContactV13', renderer=0),)).get_editor_property('property_values'))
result = {'renderer': {k:v for k,v in renderer.items() if 'Binding' in k or k in ('Material','SubImageSize','FacingMode','PivotInUVSpace')}}
path = renderer['Material']
if isinstance(path, dict): path = path['refPath']
material = u.load_asset(path)
result['material'] = {'path':path, 'blend':str(material.get_editor_property('blend_mode')), 'nodes':[]}
for node in LIB.get_material_expressions(material):
    row = {'name':node.get_name(),'class':node.get_class().get_name(),'desc':node.get_editor_property('desc')}
    if isinstance(node,u.MaterialExpressionDepthFade):
        row['distance'] = node.get_editor_property('fade_distance_default')
    elif isinstance(node,u.MaterialExpressionConstant):
        row['r'] = node.get_editor_property('r')
    elif isinstance(node,u.MaterialExpressionDynamicParameter):
        row['param_names'] = [str(x) for x in node.get_editor_property('param_names')]
    elif isinstance(node,u.MaterialExpressionCustom):
        row['code'] = node.get_editor_property('code')
    elif isinstance(node,u.MaterialExpressionMultiply):
        row['constants'] = [node.get_editor_property('const_a'),node.get_editor_property('const_b')]
    elif isinstance(node,u.MaterialExpressionPower):
        row['exponent'] = node.get_editor_property('const_exponent')
    elif isinstance(node,u.MaterialExpressionScalarParameter):
        row['parameter'] = str(node.get_editor_property('parameter_name'))
        row['value'] = node.get_editor_property('default_value')
    if isinstance(node,u.MaterialExpressionTextureSample):
        texture=node.get_editor_property('texture')
        row['texture'] = texture.get_path_name() if texture else None
    row['inputs'] = [n.get_name() if n else None for n in LIB.get_inputs_for_material_expression(material,node)]
    row['input_channels'] = [str(LIB.get_input_node_output_name_for_material_expression(node,n)) if n else None for n in LIB.get_inputs_for_material_expression(material,node)]
    result['material']['nodes'].append(row)
if '-run=' not in u.SystemLibrary.get_command_line().lower():
    result['pie'] = u.get_editor_subsystem(u.LevelEditorSubsystem).is_in_play_in_editor()
Path(__file__).with_suffix('.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('HAMMER_VISIBILITY_INPUTS_READ',json.dumps(result['renderer']))
