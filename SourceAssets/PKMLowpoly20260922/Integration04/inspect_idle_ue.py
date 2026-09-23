import unreal as u,json
from pathlib import Path
out={};editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
for label,world in [('editor',editor.get_editor_world()),('game',editor.get_game_world())]:
 if not world:continue
 chars=[]
 for a in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
  meshes=[]
  for m in a.get_components_by_class(u.SkeletalMeshComponent):
   asset=m.get_editor_property('skeletal_mesh_asset')
   if not asset or 'PKMLowpoly' not in asset.get_path_name():continue
   anim=m.get_anim_instance();props={}
   for key in ['idle_clip','action_clip','action_time','action_alpha','aim_clip','sprint_clip','sprint_alpha','base_time']:
    try:
     val=anim.get_editor_property(key);props[key]=val.get_path_name() if hasattr(val,'get_path_name') else str(val)
    except Exception as e:props[key]=str(e)
   bones={n:str(m.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)) for n in ['WPN_root','PKM_Cover','PKM_Box','PKM_BoxLid','New_PKM_Box']}
   meshes.append({'mesh':asset.get_path_name(),'anim':props,'bones':bones})
  if meshes:chars.append({'actor':a.get_path_name(),'meshes':meshes})
 out[label]=chars
Path(__file__).with_name('idle_ue_inspection.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
