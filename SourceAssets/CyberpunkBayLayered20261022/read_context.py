from pathlib import Path
import json
import unreal as u
root=Path(__file__).resolve().parent
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
world=editor.get_editor_world() if editor else None
result={'world':world.get_path_name() if world else None,
        'pie':bool(editor and editor.get_game_world()),
        'dirty_maps':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],
        'water':[]}
for path in ['/Game/Clearwater/MI_ClearwaterWater','/Game/Clearwater/M_ClearwaterWater_Native']:
    obj=u.load_asset(path)
    result['water'].append({'path':path,'class':obj.get_class().get_name() if obj else None,
        'parent':obj.get_editor_property('parent').get_path_name() if isinstance(obj,u.MaterialInstanceConstant) else None})
(root/'editor_context.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
