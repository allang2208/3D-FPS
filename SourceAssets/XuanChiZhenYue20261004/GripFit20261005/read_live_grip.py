"""Read the active sword mount and all hand-bone transforms without changing play."""
import json
from pathlib import Path
import unreal as u
P=Path(__file__).resolve().parent
def vec(v):return [float(v.x),float(v.y),float(v.z)]
def tf(t):
    q=t.rotation
    return {'location':vec(t.translation),'rotation':[float(q.x),float(q.y),float(q.z),float(q.w)],'scale':vec(t.scale3d)}
def path(o):return o.get_path_name() if o else None
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report={'game_world':path(world),'swords':[]}
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Actor):
        components=actor.get_components_by_class(u.StaticMeshComponent)
        matches=[c for c in components if c.static_mesh and 'SM_XuanChi_Blade_V3' in c.static_mesh.get_path_name()]
        for blade in matches:
            parent=blade.get_attach_parent()
            row={'component':path(blade),'world':tf(blade.get_world_transform()),
                'relative':{'location':vec(blade.relative_location),'rotation':str(blade.relative_rotation),'scale':vec(blade.relative_scale3d)},
                'parent':path(parent),'socket':str(blade.get_attach_socket_name()),'parts':[]}
            if isinstance(parent,u.SkeletalMeshComponent):
                row['arms_asset']=path(parent.get_skeletal_mesh_asset())
                row['arms_world']=tf(parent.get_world_transform())
                row['bones']={str(parent.get_bone_name(i)):tf(parent.get_socket_transform(parent.get_bone_name(i),u.RelativeTransformSpace.RTS_COMPONENT)) for i in range(parent.get_num_bones())}
                row['weapon_bone_world']=tf(parent.get_socket_transform(blade.get_attach_socket_name(),u.RelativeTransformSpace.RTS_WORLD))
                row['hand_sword_local']={n:vec(blade.get_world_transform().inverse_transform_location(parent.get_socket_location(n))) for n in ['hand_r','hand_l','index_01_r','thumb_01_r','index_01_l','thumb_01_l']}
            for c in components:
                if c.static_mesh and 'XuanChi' in c.static_mesh.get_path_name():
                    row['parts'].append({'mesh':path(c.static_mesh),'component':path(c),'world':tf(c.get_world_transform()),'visible':c.is_visible()})
            report['swords'].append(row)
(P/'live_grip_before.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'world':report['game_world'],'swords':[{k:v for k,v in r.items() if k not in ['bones','parts']} for r in report['swords']]}))
