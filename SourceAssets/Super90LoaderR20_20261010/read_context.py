"""Read only the currently running Super90 viewmodel and clothing context."""
import unreal as u, json
from pathlib import Path
O=Path(__file__).parent
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
out={'game_world':bool(world),'components':[]}
def vec(v):return [v.x,v.y,v.z]
if world:
    pawn=u.GameplayStatics.get_player_pawn(world,0)
    if pawn:
        out['pawn']=pawn.get_path_name()
        for c in pawn.get_components_by_class(u.CameraComponent):
            out['camera']={'name':c.get_name(),'location':vec(c.get_world_location()),'rotation':str(c.get_world_rotation()),'fov':c.field_of_view}
            for key in ('first_person_field_of_view','first_person_scale','enable_first_person_field_of_view','enable_first_person_scale'):
                try:out['camera'][key]=str(c.get_editor_property(key))
                except Exception:pass
        for c in pawn.get_components_by_class(u.SkeletalMeshComponent):
            asset=c.get_skeletal_mesh_asset()
            if not asset:continue
            row={'name':c.get_name(),'mesh':asset.get_path_name(),'visible':c.is_visible(),'relative_location':vec(c.get_editor_property('relative_location')),'relative_rotation':str(c.get_editor_property('relative_rotation'))}
            if 'Super90' in row['mesh'] or 'Chainmail' in row['mesh'] or 'chainmail' in row['mesh']:
                row['bones']={}
                for b in ('clavicle_l','upperarm_l','lowerarm_l','hand_l'):
                    if c.get_bone_index(b)>=0:
                        t=c.get_socket_transform(b,u.RelativeTransformSpace.RTS_COMPONENT)
                        q=t.rotation
                        row['bones'][b]={'position':vec(t.translation),'rotation':[q.x,q.y,q.z,q.w]}
            out['components'].append(row)
(O/'runtime_context.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
print('SUPER90_CONTEXT_SAVED',len(out['components']),flush=True)
