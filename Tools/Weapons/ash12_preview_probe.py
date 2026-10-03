"""Read-only diagnosis of the current ASH preview and imported mesh sizes."""
import unreal as u,json
from pathlib import Path
O=Path(u.Paths.project_saved_dir())/'ASH12PreviewFix';O.mkdir(exist_ok=True)
out={'assets':{},'actors':[]}
root='/Game/Weapons/ASH12/UniversalAttachments20260919/Meshes/SM_ASH12_'
for key in ('vertical','canted','prism','angled','holographic','panoramic_red_dot','prism_scope_2x','lpvo_1_6x','lpvo_ring'):
 m=u.load_asset(root+key)
 out['assets'][key]={'loaded':bool(m)}
 if m:
  b=m.get_bounding_box();out['assets'][key].update({'min':str(b.min),'max':str(b.max),'bounds':str(m.get_bounds()),'triangles':m.get_num_triangles(0)})
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if world:
 for actor in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
  a={'actor':actor.get_path_name(),'ash':actor.get_editor_property('bUseASH12'),'components':[]}
  for c in actor.get_components_by_class(u.MeshComponent):
   mesh=c.get_editor_property('static_mesh') if isinstance(c,u.StaticMeshComponent) else c.get_skinned_asset() if isinstance(c,u.SkinnedMeshComponent) else None
   a['components'].append({'name':c.get_name(),'mesh':mesh.get_path_name() if mesh else None,'visible':c.is_visible(),'transform':str(c.get_world_transform()),'relative':str(c.get_relative_transform()),'socket':str(c.get_attach_socket_name())})
  out['actors'].append(a)
(O/'before.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
