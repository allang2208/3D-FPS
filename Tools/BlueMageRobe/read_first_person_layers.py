"""Read the user's current PIE layers without moving, hiding or posing anything."""
import json
from pathlib import Path
import unreal as u
R=Path('D:/FPS3D/FPSGAME/SourceAssets/BlueMageRobe20261018/OwnerLayerRepair20261020');R.mkdir(parents=True,exist_ok=True)
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report=dict(pie=bool(world),read_only=True,parts=[])
def xyz(v):return [v.x,v.y,v.z]
def rgba(v):return [v.r,v.g,v.b,v.a]
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Pawn):
        if not actor.is_locally_controlled():continue
        for part in actor.get_components_by_class(u.SkeletalMeshComponent):
            mesh=part.get_skeletal_mesh_asset()
            if not mesh:continue
            tags=[str(t) for t in part.component_tags]
            if not ('ModularOutfit' in tags or 'FirstPersonLowerBody' in tags or 'WorldBody' in part.get_name()):continue
            parent=part.get_attach_parent();leader=part.get_editor_property('leader_pose_component')
            row=dict(component=part.get_name(),mesh=mesh.get_path_name(),tags=tags,parent=parent.get_name() if parent else None,leader=leader.get_name() if leader else None,visible=part.is_visible(),hidden=part.get_editor_property('hidden_in_game'),owner_no_see=part.get_editor_property('owner_no_see'),only_owner_see=part.get_editor_property('only_owner_see'),render_type=str(part.get_editor_property('first_person_primitive_type')),location=xyz(part.get_world_location()),scale=xyz(part.get_world_scale()),materials=[])
            if 'OutfitRobeDrape' in tags:
                row.update(cloth_suspended=part.is_clothing_simulation_suspended(),cloth_blend=part.get_editor_property('cloth_blend_weight'))
            row['evaluate_wpo']=part.get_editor_property('evaluate_world_position_offset')
            row['wpo_disable_distance']=part.get_editor_property('world_position_offset_disable_distance')
            if 'BlueMageRobe' in mesh.get_path_name() or 'FirstPersonLowerBody' in tags:
                row['bones']={n:xyz(part.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT).translation) for n in ('pelvis','thigh_l','thigh_r','calf_l','calf_r','foot_l','foot_r')}
            for i,slot in enumerate(mesh.get_editor_property('materials')):
                material=part.get_material(i)
                m=dict(index=i,slot=str(slot.material_slot_name),material=material.get_path_name() if material else None,shown=part.is_material_section_shown(i,0))
                if isinstance(material,u.MaterialInstanceDynamic):
                    m['strength']=material.get_scalar_parameter_value('RobeHemStrength')
                    m['hem']={name:rgba(material.get_vector_parameter_value(name)) for name in ['RobeHemShape']+['RobeHemPoint'+str(i) for i in range(64)]}
                row['materials'].append(m)
            report['parts'].append(row)
(R/'live-layers-before.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
summary=[dict(component=r['component'],mesh=r['mesh'],parent=r['parent'],visible=r['visible'],hidden=r['hidden'],owner_no_see=r['owner_no_see'],only_owner_see=r['only_owner_see'],materials=[dict(slot=m['slot'],shown=m['shown'],strength=m.get('strength')) for m in r['materials']]) for r in report['parts'] if r['only_owner_see'] and r['parent']=='FirstPersonSharedBody']
print(json.dumps(dict(pie=report['pie'],parts=summary)),flush=True)
