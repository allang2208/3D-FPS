"""Author the in-game green/red placement ghost; does not run a game or render a preview."""
from pathlib import Path
import json
import unreal as u

dest='/Game/Building/Voxels/Rounded'
name='M_Voxel_PlacementPreview'
eal=u.EditorAssetLibrary
lib=u.MaterialEditingLibrary
tools=u.AssetToolsHelpers.get_asset_tools()
eal.make_directory(dest)
u.log_warning('VOXEL_PREVIEW_AUTHOR begin material')
mat=u.load_asset(dest+'/'+name) if eal.does_asset_exist(dest+'/'+name) else tools.create_asset(name,dest,u.Material,u.MaterialFactoryNew())
lib.delete_all_material_expressions(mat)
mat.set_editor_property('blend_mode',u.BlendMode.BLEND_TRANSLUCENT)
mat.set_editor_property('shading_model',u.MaterialShadingModel.MSM_UNLIT)
mat.set_editor_property('two_sided',True)
# An invalid candidate may overlap a wall. Keep the small tool volume visible
# in that case instead of hiding the red feedback behind the wall's depth.
mat.set_editor_property('disable_depth_test',True)

def node(cls):return lib.create_material_expression(mat,cls)
def vector(name,value):
    result=node(u.MaterialExpressionVectorParameter)
    result.set_editor_property('parameter_name',name)
    result.set_editor_property('default_value',value)
    return result

tint=vector('Tint',u.LinearColor(.06,1,.15,1))
origin=vector('PreviewOrigin',u.LinearColor(0,0,0,0))
position=node(u.MaterialExpressionWorldPosition)
normal=node(u.MaterialExpressionVertexNormalWS)
opacity=node(u.MaterialExpressionCustom)
opacity.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT1)
opacity.set_editor_property('code','''float3 a=abs(N); float3 p=P-Origin;
float2 uv=(a.z>0.5?p.xy:(a.x>0.5?p.yz:p.xz))/20.0;
float2 f=frac(uv); float e=min(min(f.x,1-f.x),min(f.y,1-f.y));
return lerp(0.28,0.85,1-smoothstep(0.018,0.05,e));''')
inputs={'P':position,'N':normal,'Origin':origin}
pins=[]
for pin_name in inputs:
    pin=u.CustomInput();pin.set_editor_property('input_name',pin_name);pins.append(pin)
opacity.set_editor_property('inputs',pins)
for pin_name,source in inputs.items():lib.connect_material_expressions(source,'',opacity,pin_name)
lib.connect_material_property(tint,'',u.MaterialProperty.MP_EMISSIVE_COLOR)
lib.connect_material_property(opacity,'',u.MaterialProperty.MP_OPACITY)
u.log_warning('VOXEL_PREVIEW_AUTHOR compile material')
lib.recompile_material(mat)
u.log_warning('VOXEL_PREVIEW_AUTHOR save material')
if not eal.save_loaded_asset(mat,False):raise RuntimeError('Could not save placement preview material')
out=Path('D:/FPS3D/FPSGAME/Saved/VoxelPlacementSupport20260913')
out.mkdir(parents=True,exist_ok=True)
(out/'preview-authoring.json').write_text(json.dumps({'material':mat.get_path_name(),'runtime_tested':False},indent=2),encoding='utf-8')
u.log('VOXEL_PLACEMENT_PREVIEW_AUTHORED '+mat.get_path_name())
