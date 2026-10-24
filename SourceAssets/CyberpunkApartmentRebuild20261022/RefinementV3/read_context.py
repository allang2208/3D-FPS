from pathlib import Path
import json
import unreal as u
root=Path(__file__).resolve().parent
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
w=ed.get_editor_world() if ed else None
r={'world':w.get_path_name() if w else None,'playing':bool(ed and ed.get_game_world()),
   'dirty_maps':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()], 'skies':[]}
for name in ('MI_HDR_Night_Sky','MI_Night_Sky','MI_Sky_Sunset'):
 m=u.load_asset('/Game/PWL_Light_Manager/Shader/'+name)
 if not m:continue
 cube=u.MaterialEditingLibrary.get_material_instance_texture_parameter_value(m,'Sky Cubemap')
 r['skies'].append({'material':m.get_path_name(),'cube':cube.get_path_name() if cube else None,
   'scalars':{str(n):u.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(m,n) for n in u.MaterialEditingLibrary.get_scalar_parameter_names(m)}})
(root/'context.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(r,ensure_ascii=False))
