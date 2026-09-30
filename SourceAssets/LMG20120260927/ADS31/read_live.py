"""Read only the current 201/ADS instance, without starting or changing play."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;O.mkdir(exist_ok=True)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
out={'pie':bool(world),'actors':[]}
def tr(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
def prop(ob,name):
 try:
  x=ob.get_editor_property(name)
  if isinstance(x,u.Object):return x.get_path_name()
  if isinstance(x,(int,float,bool,str)) or x is None:return x
  return str(x)
 except Exception:return None
if world:
 pc=u.GameplayStatics.get_player_controller(world,0)
 pawn=u.GameplayStatics.get_player_pawn(world,0)
 if pawn:
  item={'actor':pawn.get_path_name(),'props':{},'components':[]}
  for name in ['weapon_ads_factor','active_inventory_weapon_definition','aim_animation','gunplay_animation']:
   item['props'][name]=prop(pawn,name)
  for c in pawn.get_components_by_class(u.SceneComponent):
   if not isinstance(c,(u.MeshComponent,u.CameraComponent)):continue
   d={'name':c.get_name(),'class':c.get_class().get_name(),'world':tr(c.get_world_transform()),'relative':tr(c.get_relative_transform()),
      'parent':c.get_attach_parent().get_name() if c.get_attach_parent() else None,'socket':str(c.get_attach_socket_name()),'visible':c.is_visible()}
   if isinstance(c,u.CameraComponent):d.update(fov=c.field_of_view,active=c.is_active())
   if isinstance(c,u.SkeletalMeshComponent):
    m=c.get_skeletal_mesh_asset();d['mesh']=m.get_path_name() if m else None
    if m and '/LMG201/' in m.get_path_name():
     d['bones']={b:tr(c.get_socket_transform(b,u.RelativeTransformSpace.RTS_COMPONENT)) for b in ['WPN_root','WPN_ChargingHandle','WPN_BoltCatch','WPN_Trigger','LMG201_Cover']}
     d['materials']=[{'slot':str(s.material_slot_name),'mat':c.get_material(i).get_path_name() if c.get_material(i) else None,'shown':c.is_material_section_shown(i,0)} for i,s in enumerate(m.materials)]
     anim=c.get_anim_instance();d['anim']={n:prop(anim,n) for n in ['aim_alpha','action_alpha','idle_clip','aim_clip','action_clip']} if anim else None
   if isinstance(c,u.StaticMeshComponent):d['mesh']=c.static_mesh.get_path_name() if c.static_mesh else None
   item['components'].append(d)
  out['actors'].append(item)
 pcm=u.GameplayStatics.get_player_camera_manager(world,0)
 if pcm:out['camera']={'position':list(pcm.get_camera_location().to_tuple()),'rotation':list(pcm.get_camera_rotation().to_tuple()),'fov':pcm.get_fov_angle()}
mesh=u.load_asset('/Game/Weapons/LMG201/Cover10/SK_LMG201_Cover10')
out['installed_metadata']={str(k):str(v) for k,v in u.EditorAssetLibrary.get_metadata_tag_values(mesh).items()}
(O/'live.json').write_text(json.dumps(out,indent=2,default=str))
print('ADS31_CONTEXT',json.dumps(out,default=str),flush=True)
