"""Read the current RSH component/gear/animation binding without playing or changing it."""
import unreal as u,json
from pathlib import Path
O=Path(__file__).parent
world=u.EditorLevelLibrary.get_game_world()
out={'pie':bool(world),'actors':[]}
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        meshes=[]
        for mesh in actor.get_components_by_class(u.SkeletalMeshComponent):
            asset=mesh.get_editor_property('skeletal_mesh_asset')
            if not asset:continue
            path=asset.get_path_name()
            if not any(s in path for s in ('RSH12','DW715')):continue
            row=dict(component=mesh.get_name(),mesh=path,parent=mesh.get_attach_parent().get_name() if mesh.get_attach_parent() else '',materials=[str(mesh.get_material(i).get_path_name()) for i in range(mesh.get_num_materials()) if mesh.get_material(i)])
            anim=mesh.get_anim_instance()
            if anim:
                row['anim_class']=anim.get_class().get_name();row['anim']={}
                for prop in ('aim_alpha','action_alpha','action_time','idle_clip','aim_clip','action_clip','grip_profile'):
                    try:
                        value=anim.get_editor_property(prop);row['anim'][prop]=value.get_path_name() if isinstance(value,u.Object) else value
                    except Exception:pass
            meshes.append(row)
        if meshes:out['actors'].append(dict(actor=actor.get_name(),meshes=meshes))
(O/'active_state.json').write_text(json.dumps(out,indent=2),encoding='utf8')
print(json.dumps(out))
