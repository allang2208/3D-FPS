"""Read active SVD sources and any existing play camera for this requested inspection."""
import json,os,hashlib
from pathlib import Path
import unreal as u
O=Path(__file__).parent;P=O.parents[1]
auth=json.loads((O.parent/'SVDChargeGrip20260924/authoring.json').read_text())
out={'pid':os.getpid(),'clips':{},'runtime':[]}
mesh=u.load_asset('/Game/Weapons/SVDDragunov20260922/StockAdapter20260923/SK_SVD_ModularStock')
out['mesh']={'path':mesh.get_path_name()}
out['dirty_targets']=[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages() if p.get_path_name() in [a['path'] for a in auth.values()]]
def tr(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
for k,a in auth.items():
 anim=u.load_asset(a['path']);disk=P/'Content'/Path(a['path'].removeprefix('/Game/')+'.uasset')
 out['clips'][k]={'path':a['path'],'source':anim.get_editor_property('asset_import_data').get_first_filename(),'duration':anim.get_play_length(),'sha256':hashlib.sha256(disk.read_bytes()).hexdigest()}
editor=u.get_editor_subsystem(u.UnrealEditorSubsystem);world=editor.get_game_world() if editor else None;out['PIE_active']=bool(world)
if world:
 for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
  for comp in actor.get_components_by_class(u.SkeletalMeshComponent):
   if not comp.get_skinned_asset() or comp.get_skinned_asset()!=mesh:continue
   row={'actor':actor.get_name(),'component':comp.get_name(),'relative':tr(comp.get_relative_transform()),'cameras':[]}
   for cam in actor.get_components_by_class(u.CameraComponent):row['cameras'].append({'name':cam.get_name(),'fov':cam.field_of_view,'relative':tr(cam.get_relative_transform())})
   out['runtime'].append(row)
(O/'runtime_before.json').write_text(json.dumps(out,indent=2));print('SVD_GRASP_INPUT',json.dumps(out))
