import unreal as u,json
from pathlib import Path
O=Path(__file__).resolve().parent
def value(ob,k):
    try:
        v=ob.get_editor_property(k)
        return v.get_path_name() if isinstance(v,u.Object) else str(v)
    except Exception:return None
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
data={'world':world.get_path_name() if world else None,'actors':[]}
if world:
    for a in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        if 'FPSGAMECharacter' not in a.get_class().get_name():continue
        row={'actor':a.get_path_name(),'props':{k:value(a,k) for k in ('active_inventory_weapon_definition','weapon_state','idle_animation','aim_animation','fire_animation','reload_animation','active_action_animation','viewmodel_scale','hip_viewmodel_location','m4_action_viewmodel_location')},'components':[]}
        for c in a.get_components_by_class(u.SkeletalMeshComponent):
            mesh=c.get_editor_property('skeletal_mesh_asset')
            if not mesh or '/Weapons/M24/' not in mesh.get_path_name():continue
            anim=c.get_anim_instance()
            row['components'].append({'name':c.get_name(),'asset':mesh.get_path_name(),'visible':c.is_visible(),'relative':str(c.get_relative_transform()),'world':str(c.get_world_transform()),
              'anim':{k:value(anim,k) for k in ('idle_clip','aim_clip','action_clip','grip_profile','action_grip_profile')} if anim else None,
              'bones':{n:str(c.get_socket_transform(n,u.RelativeTransformSpace.RTS_WORLD)) for n in ('WPN_root','hand_l','hand_r')}})
        for c in a.get_components_by_class(u.CameraComponent):row['camera']={'world':str(c.get_world_transform()),'fov':c.field_of_view}
        data['actors'].append(row)
(O/'runtime_before.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
print('M24_RUNTIME_READ',json.dumps(data),flush=True)
