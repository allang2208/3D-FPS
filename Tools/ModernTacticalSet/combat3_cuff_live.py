"""Read the current outfit instance and wrist pose; do not change the game."""
import json
from pathlib import Path
import unreal as u
R=Path('D:/FPS3D/FPSGAME/SourceAssets/ModernTacticalSet20261113/CombatShirtR3/CuffRepairR1');R.mkdir(exist_ok=True)
def vec(v):return [v.x,v.y,v.z]
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world();report=dict(playing=bool(world),components=[])
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Pawn):
        if not actor.is_player_controlled():continue
        for c in actor.get_components_by_class(u.SkeletalMeshComponent):
            mesh=c.get_editor_property('skeletal_mesh_asset')
            if not mesh:continue
            leader=c.get_editor_property('leader_pose_component');row=dict(actor=actor.get_name(),component=c.get_name(),mesh=mesh.get_path_name(),visible=c.is_visible(),hidden=c.get_editor_property('hidden_in_game'),owner_only=c.get_editor_property('only_owner_see'),tags=[str(t) for t in c.component_tags],leader=leader.get_name() if leader else None,lod=c.get_predicted_lod_level(),materials=[c.get_material(i).get_path_name() if c.get_material(i) else None for i in range(c.get_num_materials())],bones={})
            for bi in range(c.get_num_bones()):
                name=str(c.get_bone_name(bi));t=c.get_socket_transform(name,u.RelativeTransformSpace.RTS_COMPONENT);row['bones'][name]=dict(position=vec(t.translation),axes=[vec(t.transform_location(v)-t.translation) for v in [u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1)]])
            report['components'].append(row)
(R/'live-before.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print('CUFF_CURRENT_INSTANCE_READ',report['playing'],[(r['component'],r['mesh'],r['lod']) for r in report['components']],flush=True)
