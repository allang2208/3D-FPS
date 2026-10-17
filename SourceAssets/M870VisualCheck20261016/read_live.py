import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
def tr(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
out={'game_world':w.get_path_name() if w else None,'actors':[]}
if w:
 for a in u.GameplayStatics.get_all_actors_of_class(w,u.Character):
  if 'FPSGAME' not in a.get_class().get_name():continue
  cs=a.get_components_by_class(u.SkeletalMeshComponent)
  src=next((c for c in cs if c.get_name()=='AKMViewmodel'),None)
  cams=a.get_components_by_class(u.CameraComponent)
  if not src:continue
  anim=src.get_anim_instance();row={'actor':a.get_path_name(),'source':tr(src.get_world_transform()),'camera':tr(cams[0].get_world_transform()) if cams else None,'bones':{},'components':[],'anim':{}}
  for n in ('upperarm_l','lowerarm_l','lowerarm_aux_l','lowerarm_twist_01_l','lowerarm_twist_02_l','hand_l','WPN_root','WPN_bolt','WPN_RearSight','WPN_FrontSight'):
   row['bones'][n]=tr(src.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT))
  for prop in ('idle_clip','aim_clip','action_clip','action_time','action_alpha','aim_alpha'):
   try:
    v=anim.get_editor_property(prop);row['anim'][prop]=v.get_path_name() if isinstance(v,u.Object) else v
   except Exception as e:row['anim'][prop]=str(e)
  for c in cs:
   if c==src or c.get_editor_property('leader_pose_component')==src:
    row['components'].append({'name':c.get_name(),'mesh':c.get_skeletal_mesh_asset().get_path_name() if c.get_skeletal_mesh_asset() else None,'visible':c.is_visible()})
  out['actors'].append(row)
(O/'live_state.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
