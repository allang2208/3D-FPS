"""Fade low foliage WPO between 20 and 35 metres; trees retain the original wind."""
import runpy
from pathlib import Path
import unreal as u
H=runpy.run_path(str(Path('D:/FPS3D/FPSGAME/Tools/WorldGeneration/temperate_render_budget.py')))
L=u.MaterialEditingLibrary
TAG='HillsLowWindBudget20261114'

def apply(mat):
    if any(n.get_editor_property('desc')==TAG for n in L.get_material_expressions(mat)):return
    H['backup'](mat)
    attributes=mat.get_editor_property('use_material_attributes')
    prop=u.MaterialProperty.MP_MATERIAL_ATTRIBUTES if attributes else u.MaterialProperty.MP_WORLD_POSITION_OFFSET
    original=L.get_material_property_input_node(mat,prop)
    if not original:return
    out=L.get_material_property_input_node_output_name(mat,prop)
    def node(cls):
        n=L.create_material_expression(mat,cls);n.set_editor_property('desc',TAG);return n
    wire=H['wire']
    source=original;channel=out
    if attributes:
        source=node(u.MaterialExpressionGetMaterialAttributes)
        idx=u.TemperateForestAuthoringLibrary.add_wind_offset_pin(source)
        if idx<0:raise RuntimeError('Wind attribute reader')
        wire(original,source,L.get_material_expression_input_names(source)[0],out)
        channel=L.get_material_expression_output_names(source)[idx]
    p=node(u.MaterialExpressionWorldPosition)
    p.set_editor_property('world_position_shader_offset',u.WorldPositionIncludedOffsets.WPT_EXCLUDE_ALL_SHADER_OFFSETS)
    enabled=node(u.MaterialExpressionScalarParameter);enabled.set_editor_property('parameter_name','HillsNearFadeEnabled');enabled.set_editor_property('default_value',0.)
    damp=node(u.MaterialExpressionCustom);damp.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT3)
    damp.set_editor_property('code','return W*lerp(1.0,1.0-smoothstep(2000.0,3500.0,distance(P,C)),saturate(E));')
    values={'W':(source,channel),'P':(p,''),'C':(node(u.MaterialExpressionCameraPositionWS),''),'E':(enabled,'')}
    pins=[]
    for name in values:
        pin=u.CustomInput();pin.set_editor_property('input_name',name);pins.append(pin)
    damp.set_editor_property('inputs',pins)
    for name,(value,output) in values.items():wire(value,damp,name,output)
    result=damp
    if attributes:
        result=node(u.MaterialExpressionSetMaterialAttributes)
        idx=u.TemperateForestAuthoringLibrary.add_wind_offset_pin(result)
        names=L.get_material_expression_input_names(result)
        wire(original,result,names[0],out);wire(damp,result,names[idx])
    if not L.connect_material_property(result,'',prop):raise RuntimeError('Wind output')
    L.recompile_material(mat);H['save'](mat)

def main():
    # Only masters already participating in the owned low-foliage coverage path.
    import json
    task=H['TASK']
    report=json.loads((task/'near-foliage-saved.json').read_text(encoding='utf-8'))
    mats=set(report['saved'])
    mats.update(u.EditorAssetLibrary.list_assets(H['DEST'],False,False))
    for asset in sorted(mats):
        mat=u.load_asset(asset)
        if not isinstance(mat,u.Material):continue
        if any(n.get_editor_property('desc')==H['TAG'] for n in L.get_material_expressions(mat)):apply(mat)
    (task/'wind-saved.json').write_text(json.dumps({'saved':H['REPORT']['saved']},indent=2),encoding='utf-8')

if __name__=='__main__':main()
