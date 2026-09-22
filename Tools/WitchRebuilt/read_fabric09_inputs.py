import unreal as u,json
from pathlib import Path
root=Path('D:/FPS3D/FPSGAME');out=root/'SourceAssets/WitchRebuilt20260921/Revision09';out.mkdir(exist_ok=True)
if Path(u.Paths.convert_relative_path_to_full(u.Paths.get_project_file_path())).resolve()!=root/'FPSGAME.uproject':raise RuntimeError('Wrong editor project')
mesh=u.load_asset('/Game/Monsters/WitchRebuilt/SK_WitchRebuilt');result={'slots':[]}
for s in mesh.materials:
 name=str(s.get_editor_property('imported_material_slot_name'));m=s.material_interface
 item={'slot':name,'material':m.get_path_name() if m else None}
 if m and ('Robe' in name or 'Lining' in name):
  item['textures']=[n.texture.get_path_name() for n in u.MaterialEditingLibrary.get_material_expressions(m) if isinstance(n,u.MaterialExpressionTextureSample) and n.texture]
  item['blend_mode']=str(m.get_editor_property('blend_mode'))
 result['slots'].append(item)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
result['play_world']=world.get_path_name() if world else None
result['dirty_target_packages']=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name().startswith('/Game/Monsters/WitchRebuilt')]
(out/'material_inputs.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
