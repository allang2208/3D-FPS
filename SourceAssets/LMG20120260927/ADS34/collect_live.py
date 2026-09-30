"""Read the existing ADS instance without changing play, equipment or camera."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
def tr(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
def prop(o,k):
 try:
  v=o.get_editor_property(k)
  if isinstance(v,u.Object):return v.get_path_name()
  return v if isinstance(v,(int,float,str,bool)) or v is None else str(v)
 except Exception:return None
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
out={'pie':bool(w),'components':[],'dirty':[p.get_path_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()]}
if w:
 pawn=u.GameplayStatics.get_player_pawn(w,0)
 if pawn:
  out['pawn']=pawn.get_path_name()
  for c in pawn.get_components_by_class(u.SceneComponent):
   if not isinstance(c,(u.MeshComponent,u.CameraComponent)):continue
   d={'name':c.get_name(),'class':c.get_class().get_name(),'world':tr(c.get_world_transform()),'relative':tr(c.get_relative_transform()),'parent':c.get_attach_parent().get_name() if c.get_attach_parent() else None,'socket':str(c.get_attach_socket_name()),'visible':c.is_visible()}
   for k in ['hidden_in_game','only_owner_see','owner_no_see','first_person_primitive_type','component_tags','leader_pose_component']:d[k]=prop(c,k)
   if isinstance(c,u.SkeletalMeshComponent):
    m=c.get_skeletal_mesh_asset();d['mesh']=m.get_path_name() if m else None
    if m and c.is_visible():
     d['bones']={str(c.get_bone_name(i)):tr(c.get_socket_transform(c.get_bone_name(i),u.RelativeTransformSpace.RTS_COMPONENT)) for i in range(c.get_num_bones())}
     d['materials']=[{'slot':str(s.material_slot_name),'mat':c.get_material(i).get_path_name() if c.get_material(i) else None,'shown':c.is_material_section_shown(i,0)} for i,s in enumerate(m.materials)]
     inst=c.get_anim_instance();d['anim']={k:prop(inst,k) for k in ['aim_alpha','action_alpha','idle_clip','aim_clip','action_clip']} if inst else None
   if isinstance(c,u.StaticMeshComponent):d['mesh']=c.static_mesh.get_path_name() if c.static_mesh else None
   if isinstance(c,u.CameraComponent):d.update(fov=c.field_of_view,active=c.is_active())
   out['components'].append(d)
 pcm=u.GameplayStatics.get_player_camera_manager(w,0)
 if pcm:out['camera']={'position':list(pcm.get_camera_location().to_tuple()),'rotation':list(pcm.get_camera_rotation().to_tuple()),'fov':pcm.get_fov_angle()}
(O/'live.json').write_text(json.dumps(out,indent=2,default=str))
print('ADS34_LIVE',json.dumps({'pie':out['pie'],'dirty':out['dirty'],'components':[{k:c.get(k) for k in ['name','mesh','visible','parent','leader_pose_component','anim']} for c in out['components'] if c['visible']]},default=str),flush=True)
