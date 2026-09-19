"""User-requested mesh / socket / live component size diagnosis. Read-only."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent;S=u.ModelingService
def vec(v):return [v.x,v.y,v.z]
def trans(t):return {'location':vec(t.translation),'scale':vec(t.scale3d),'rotation':str(t.rotation)}
report={'assets':{},'actors':[]}
for kind in ('laser','flashlight'):
    paths={'donor':'/Game/Weapons/TacticalDevices20260913'+('/HunyuanV3' if kind=='flashlight' else '')+'/M4/'+kind+'/SM_TacticalDevice',
           'ash':'/Game/Weapons/ASH12/TacticalDevices20260920/'+kind+'/SM_ASH12_'+kind}
    for label,path in paths.items():
        m=u.load_asset(path);b=m.get_bounding_box();h=S.load_mesh_from_static_mesh(path).handle
        try:
            info=S.get_mesh_info(h)
            report['assets'][kind+'_'+label]={'asset':path,'bounds_min':vec(b.min),'bounds_max':vec(b.max),
                'size_cm':vec(b.max-b.min),'info':str(info),'sockets':{n:vec(m.find_socket(n).relative_location) for n in ('Emitter','AimGuide')}}
        finally:S.release_mesh(h)
es=u.get_editor_subsystem(u.UnrealEditorSubsystem)
worlds=[w for w in (es.get_game_world(),es.get_editor_world()) if w]
for world in worlds:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.FPSGAMECharacter):
        meshes=actor.get_components_by_class(u.SkeletalMeshComponent)
        host=next((m for m in meshes if m.get_name()=='AKMViewmodel'),None)
        if not host:continue
        skeletal=host.get_skeletal_mesh_asset()
        entry={'world':world.get_path_name(),'actor':actor.get_path_name(),'mesh':skeletal.get_path_name() if skeletal else None,
               'host_transform':trans(host.get_component_transform()),'root_socket_world':trans(host.get_socket_transform('WPN_root')),
               'root_socket_component':trans(host.get_socket_transform('WPN_root',u.RelativeTransformSpace.RTS_COMPONENT)),
               'devices':[]}
        for c in actor.get_components_by_class(u.StaticMeshComponent):
            m=c.static_mesh
            if not m or 'Tactical' not in m.get_path_name():continue
            b=m.get_bounding_box()
            entry['devices'].append({'component':c.get_name(),'mesh':m.get_path_name(),'visible':c.is_visible(),
                'relative':trans(c.get_relative_transform()),'world':trans(c.get_component_transform()),
                'mesh_size_cm':vec(b.max-b.min),'world_axis_size_cm':vec((b.max-b.min)*c.get_world_scale())})
        report['actors'].append(entry)
(O/'scale_before.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
