from pathlib import Path
import json, unreal as u
R=Path(__file__).resolve().parent
ed=u.get_editor_subsystem(u.UnrealEditorSubsystem)
w=ed.get_editor_world();g=ed.get_game_world()
out=dict(editor_world=w.get_path_name() if w else None,game_world=g.get_path_name() if g else None,
 dirty_maps=[x.get_path_name() for x in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()],actors={})
if not w or w.get_path_name().split('.')[0]!='/Game/GameMaps/L_CyberpunkApartment':
 w=u.load_asset('/Game/GameMaps/L_CyberpunkApartment');out['source']='saved_map_asset'
else:out['source']='live_editor_map'
for a in u.GameplayStatics.get_all_actors_of_class(w,u.Actor):
 n=a.get_actor_label()
 if n!='BAY_NearBank' and not n.startswith(('AP11_Tower_','PlayerStart_','NB28_')):continue
 p,e=a.get_actor_bounds(False,True)
 row=dict(path=a.get_path_name(),min=list((p-e).to_tuple()),max=list((p+e).to_tuple()),transform=str(a.get_actor_transform()),components=[])
 for c in a.get_components_by_class(u.StaticMeshComponent):
  if c.static_mesh:row['components'].append(dict(mesh=c.static_mesh.get_path_name(),materials=[m.get_path_name() if m else None for m in c.get_materials()],slots=[str(s.material_slot_name) for s in c.static_mesh.static_materials]))
 out['actors'][n]=row
(R/'context.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print('NEARBANK_CONTEXT',out['source'],out['editor_world'],out['game_world'],out['dirty_maps'],len(out['actors']))
