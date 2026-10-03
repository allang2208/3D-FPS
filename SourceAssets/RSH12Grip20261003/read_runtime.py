import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
out={};world=u.EditorLevelLibrary.get_game_world()
if world:
 actor=u.GameplayStatics.get_player_character(world,0)
 if actor:
  out['actor']=actor.get_path_name();out['properties']={}
  for name in ('active_inventory_weapon_definition','hip_viewmodel_location','revolver_hip_viewmodel_location','viewmodel_rotation','viewmodel_scale','base_vertical_field_of_view','ads_rear_eye_distance','ads_vertical_field_of_view','akm_viewmodel'):
   try:
    v=actor.get_editor_property(name)
    if isinstance(v,u.Object):v=v.get_path_name()
    out['properties'][name]=str(v)
   except Exception as ex:out['properties'][name]='Unavailable: '+str(ex)
  components=actor.get_components_by_class(u.SkeletalMeshComponent)
  out['components']=[]
  for mesh in components:
   asset=mesh.skeletal_mesh
   if not asset or 'RSH12' not in asset.get_path_name():continue
   anim=mesh.get_anim_instance();entry=dict(asset=asset.get_path_name(),relative_location=str(mesh.relative_location),relative_rotation=str(mesh.relative_rotation),relative_scale=str(mesh.relative_scale3d),animation={})
   if anim:
    for n in ('idle_clip','aim_clip','action_clip','action_time','action_alpha','aim_alpha','grip_profile'):
     try:
      v=anim.get_editor_property(n);entry['animation'][n]=v.get_path_name() if isinstance(v,u.Object) else str(v)
     except Exception:pass
   out['components'].append(entry)
out['game_world_present']=bool(world)
(O/'runtime_before.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out,indent=2))
