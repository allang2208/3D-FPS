import unreal as u,json
from pathlib import Path
O=Path('D:/FPS3D/FPSGAME/SourceAssets/Saiga12KInspectClearance20261018')
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();p=u.GameplayStatics.get_player_character(w,0) if w else None
r={'world':w.get_path_name() if w else None,'pawn':p.get_path_name() if p else None,'meshes':[]}
if p:
 for c in p.get_components_by_class(u.SkeletalMeshComponent):
  mesh=c.get_skeletal_mesh_asset()
  if not mesh or '/Saiga12K/' not in mesh.get_path_name():continue
  a=c.get_anim_instance();row={'component':c.get_name(),'mesh':mesh.get_path_name(),'animation':{},'anim_instance':a.get_class().get_path_name() if a else None}
  if a:
   for name in ('GripProfile','ActionGripProfile','ActionClip'):
    try:
     v=a.get_editor_property(name);row['animation'][name]=v.get_path_name() if hasattr(v,'get_path_name') else v
    except Exception as ex:row['animation'][name]=str(ex)
  r['meshes'].append(row)
 r['attachments']=[c.static_mesh.get_path_name() for c in p.get_components_by_class(u.StaticMeshComponent) if c.static_mesh]
(O/'Inputs/live-binding.json').write_text(json.dumps(r,indent=2),encoding='utf8');print(json.dumps(r))
