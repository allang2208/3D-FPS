"""Read only the user's current HK416 presentation, if it is already running."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
w=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report={'running':bool(w)}
def tr(t):return {'p':list(t.translation.to_tuple()),'q':[t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w],'s':list(t.scale3d.to_tuple())}
if w:
    actors=u.GameplayStatics.get_all_actors_of_class(w,u.Actor)
    for a in actors:
        if a.get_class().get_name()!='FPSGAMECharacter':continue
        meshes=a.get_components_by_class(u.SkeletalMeshComponent);src=next((c for c in meshes if c.get_name()=='AKMViewmodel'),None)
        if not src:continue
        mesh=src.get_skeletal_mesh_asset();report['weapon_mesh']=mesh.get_path_name() if mesh else None
        if not mesh or '/Weapons/HK416/' not in mesh.get_path_name():continue
        cam=a.get_components_by_class(u.CameraComponent)[0]
        report.update(camera=tr(cam.get_world_transform()),source=tr(src.get_world_transform()),bones={str(n):tr(src.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)) for n in ['WPN_root','WPN_RearSight','WPN_FrontSight']})
        report['camera_properties']={}
        for key in ['field_of_view','enable_first_person_field_of_view','first_person_field_of_view','enable_first_person_scale','first_person_scale']:
            try:report['camera_properties'][key]=cam.get_editor_property(key)
            except:pass
        anim=src.get_anim_instance();report['animation']={}
        for key in ['aim_clip','aim_alpha','action_alpha']:
            try:
                value=anim.get_editor_property(key);report['animation'][key]=value.get_path_name() if isinstance(value,u.Object) else value
            except:pass
        report['visible_parts']=[c.get_name() for c in a.get_components_by_class(u.StaticMeshComponent) if c.is_visible()]
        u.SystemLibrary.execute_console_command(w,'HighResShot 1 filename="D:/FPS3D/FPSGAME/SourceAssets/HK416ADS20260930/live_before.png"')
        break
(O/'live_before.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
