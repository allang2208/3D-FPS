"""Update the active terrain outputs without rebuilding unrelated hill surfaces."""
from pathlib import Path
import runpy
import unreal as u

L=u.MaterialEditingLibrary
m=u.load_asset('/Game/WorldGeneration/TemperateHills/PebbleShore/M_PebbleShoreGround')
props=('BASE_COLOR','NORMAL','ROUGHNESS','AMBIENT_OCCLUSION')
outputs={}
for name in props:
    prop=getattr(u.MaterialProperty,'MP_'+name)
    value=L.get_material_property_input_node(m,prop)
    if value and str(value.get_editor_property('desc'))=='OldChapel.'+name:
        pins=L.get_material_expression_input_names(value)
        inputs=L.get_inputs_for_material_expression(m,value)
        upstream=inputs[list(map(str,pins)).index('Base')]
        channel=L.get_input_node_output_name_for_material_expression(value,upstream)
        outputs[name]=(upstream,channel if isinstance(channel,str) else (channel[-1] if channel else ''))
    else:
        if not value:raise RuntimeError('Terrain output missing '+name)
        outputs[name]=(value,L.get_material_property_input_node_output_name(m,prop))
layer=runpy.run_path(str(Path(__file__).with_name('chapel_ground_materials.py')))['road_layer']
result=layer(m,outputs)
for name in props:
    if not L.connect_material_property(result[name],'',getattr(u.MaterialProperty,'MP_'+name)):
        raise RuntimeError('Could not connect '+name)
errors=L.recompile_material(m)
if errors:raise RuntimeError(str(errors))
if not u.EditorAssetLibrary.save_loaded_asset(m,False):raise RuntimeError('Terrain save failed')
u.log('OLD_CHAPEL_TERRAIN_SAVED '+m.get_path_name())
