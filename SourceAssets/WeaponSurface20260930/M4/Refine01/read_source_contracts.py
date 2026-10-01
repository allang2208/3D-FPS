import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
C=json.loads((O/'Input/current.json').read_text())
L=u.MaterialEditingLibrary
result={'functions':{},'textures':{},'pie':bool(u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world())}
for path in C['graphs']:
 if '/Characters/' in path:continue
 m=u.load_asset(path)
 for n in L.get_material_expressions(m):
  if isinstance(n,u.MaterialExpressionMaterialFunctionCall):
   f=n.get_editor_property('material_function');result['functions'][f.get_path_name()]=str(L.get_material_expression_input_names(n))
  if isinstance(n,u.MaterialExpressionTextureSample):
   t=n.get_editor_property('texture')
   if t:result['textures'][t.get_path_name()]={'srgb':t.srgb,'compression':str(t.compression_settings)}
(O/'Input/source_contracts.json').write_text(json.dumps(result,indent=2))
print('WEAPON_SURFACE_M4_SOURCE_CONTRACTS',result['functions'],'PIE',result['pie'])
