"""Read current world-body visibility and hand poses; never change the held scene."""
import json
from pathlib import Path
import unreal as u
R=Path('D:/FPS3D/FPSGAME/SourceAssets/BlueMageRobe20261018/WristContinuity20261020')
R.mkdir(parents=True,exist_ok=True)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report=dict(pie=bool(world),read_only=True,parts=[])
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Pawn):
        if not actor.is_locally_controlled():continue
        for part in actor.get_components_by_class(u.SkeletalMeshComponent):
            mesh=part.get_skeletal_mesh_asset()
            if not mesh:continue
            parent=part.get_attach_parent()
            if not ('ModularOutfit' in [str(t) for t in part.component_tags] or part.get_name()=='CharacterMesh0'):continue
            if part.get_editor_property('only_owner_see'):continue
            leader=part.get_editor_property('leader_pose_component')
            row=dict(component=part.get_name(),mesh=mesh.get_path_name(),
                parent=parent.get_name() if parent else None,leader=leader.get_name() if leader else None,
                visible=part.is_visible(),hidden=part.get_editor_property('hidden_in_game'),
                owner_no_see=part.get_editor_property('owner_no_see'),materials=[],bones={})
            for i,slot in enumerate(mesh.get_editor_property('materials')):
                mat=part.get_material(i)
                row['materials'].append(dict(index=i,slot=str(slot.material_slot_name),
                    shown=part.is_material_section_shown(i,0),
                    material=mat.get_path_name() if mat else None))
            for side in ('l','r'):
                for stem in ('lowerarm','hand','middle_01'):
                    name=stem+'_'+side
                    p=part.get_socket_transform(name,u.RelativeTransformSpace.RTS_COMPONENT).translation
                    row['bones'][name]=[p.x,p.y,p.z]
            report['parts'].append(row)
(R/'live-world-before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report),flush=True)
