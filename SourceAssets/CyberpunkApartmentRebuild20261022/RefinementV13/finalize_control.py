"""Final front-facing UV convention for the shared physical power panel."""
from pathlib import Path
from datetime import datetime
import unreal as u,json
R=Path(__file__).resolve().parent;L=u.MaterialEditingLibrary;E=u.EditorAssetLibrary
m=u.load_asset('/Game/Props/CyberpunkApartmentRebuild20261022/RefinementV13/Materials/M_AP13_Control')
if E.get_metadata_tag(m,'AP13.FrontUV')!='1':
 expressions=list(L.get_material_expressions(m))
 uv=next(n for n in expressions if isinstance(n,u.MaterialExpressionTextureCoordinate) and n.get_editor_property('coordinate_index')==1)
 flip=L.create_material_expression(m,u.MaterialExpressionCustom);flip.set_editor_property('code','return float2(1-UV.x,UV.y);');flip.set_editor_property('output_type',u.CustomMaterialOutputType.CMOT_FLOAT2)
 pin=u.CustomInput();pin.set_editor_property('input_name','UV');flip.set_editor_property('inputs',[pin])
 if not L.connect_material_expressions(uv,'',flip,'UV'):raise RuntimeError('Panel UV input')
 for n in expressions:
  if isinstance(n,u.MaterialExpressionTextureSample):
   if not L.connect_material_expressions(flip,'',n,'UVs'):raise RuntimeError('Panel sample UV input')
 E.set_metadata_tag(m,'AP13.FrontUV','1')
errors=list(L.recompile_material(m))
if errors:raise RuntimeError(str(errors))
shader=L.get_statistics(m)
if shader.get_editor_property('num_pixel_shader_instructions')<=0:raise RuntimeError('Panel shader compilation incomplete')
if not E.save_loaded_asset(m,False):raise RuntimeError('Panel material save failed')
(R/'control-finalized.json').write_text(json.dumps(dict(stage='material_saved',material=m.get_path_name(),front_axis='local -Y; visible horizontal axis -X',game_run=False,rendered=False,saved_at=datetime.now().astimezone().isoformat()),indent=2),encoding='utf8')
print('AP13_CONTROL_MATERIAL_SAVED')
