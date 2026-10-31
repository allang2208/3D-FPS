"""Read only current editor state and reflected Python APIs; no scene mutation."""
from pathlib import Path
import json,traceback
import unreal as u
R=Path(__file__).resolve().parent
try:
    ss=u.get_engine_subsystem(u.SubobjectDataSubsystem)
    editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
    level=u.get_editor_subsystem(u.LevelEditorSubsystem)
    ew=editor.get_editor_world() if editor else None
    out={'stage':'reflection_read','game_run':bool(editor and editor.get_game_world()),'pie':level.is_in_play_in_editor(),'dirty_maps':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],'editor_world':ew.get_path_name() if ew else None,'subsystem':str(ss),'methods':{},'world':{},'attachments':{},'structs':{}}
    for cls,names in [(ss,['k2_gather_subobject_data_for_instance','k2_find_subobject_data_from_handle','find_handle_for_object','add_new_subobject','attach_subobject','k2_delete_subobject_from_instance']),(u.SubobjectDataBlueprintFunctionLibrary,['get_associated_object','get_parent_handle','get_object'])]:
        for name in names:
            fn=getattr(cls,name,None);out['methods'][name]=str(fn.__doc__) if fn else None
    out['world']['gameplay_actors']=str(u.GameplayStatics.get_all_actors_of_class.__doc__)
    out['world']['subsystem_actors']=str(u.EditorActorSubsystem.get_all_level_actors.__doc__)
    for name in ['AttachmentRules','AttachmentRule','AddNewSubobjectParams','KBoxElem','Transform']:
        cls=getattr(u,name,None);out['structs'][name]={'present':bool(cls),'doc':str(cls.__doc__) if cls else None}
    for expr in ['u.AttachmentRules(u.AttachmentRule.KEEP_WORLD,u.AttachmentRule.KEEP_WORLD,u.AttachmentRule.KEEP_WORLD,False)','u.AddNewSubobjectParams()','u.KBoxElem(1,2,3,4,5,6)','u.Transform()']:
        try:out['attachments'][expr]=str(eval(expr))
        except Exception as e:out['attachments'][expr]=repr(e)
    out['dirty_api']={'Object':hasattr(u.Object,'mark_package_dirty'),'Package':hasattr(u.Package,'mark_package_dirty')}
    out['status']='complete'
except Exception:
    out={'stage':'failed','error':traceback.format_exc()}
(R/'probe-reflection.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out))
