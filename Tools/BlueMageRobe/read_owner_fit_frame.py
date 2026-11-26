"""Read current transforms and material uniforms only; no mesh/pose conversion."""
import json
from pathlib import Path
import unreal as u
R=Path('D:/FPS3D/FPSGAME/SourceAssets/BlueMageRobe20261018')
world=u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
if not world:raise RuntimeError('The held gameplay frame is no longer available')
def xyz(v):return [v.x,v.y,v.z]
def frame(t):return dict(position=xyz(t.translation),axes=[xyz(t.transform_location(v)-t.translation) for v in (u.Vector(1,0,0),u.Vector(0,1,0),u.Vector(0,0,1))])
names=list(json.loads((R/'HemContinuity20261019/Read/Jason_5b5a780d8268.json').read_text())['bones'])
report=dict(read_only=True,parts=[])
camera=u.GameplayStatics.get_player_camera_manager(world,0)
report['camera']=dict(position=xyz(camera.get_camera_location()),rotation=str(camera.get_camera_rotation()),fov=camera.get_fov_angle())
for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Pawn):
    if not actor.is_locally_controlled():continue
    for part in actor.get_components_by_class(u.SkeletalMeshComponent):
        parent=part.get_attach_parent();mesh=part.get_skeletal_mesh_asset()
        if not parent or parent.get_name()!='FirstPersonSharedBody' or not mesh:continue
        if not part.is_visible() or part.get_editor_property('hidden_in_game'):continue
        row=dict(component=part.get_name(),mesh=mesh.get_path_name(),transform=frame(part.get_world_transform()),bones={n:frame(part.get_socket_transform(n,u.RelativeTransformSpace.RTS_COMPONENT)) for n in names},materials=[])
        for i,slot in enumerate(mesh.get_editor_property('materials')):
            material=part.get_material(i);m=dict(index=i,slot=str(slot.material_slot_name),shown=part.is_material_section_shown(i,0))
            if isinstance(material,u.MaterialInstanceDynamic):
                def vector(n):v=material.get_vector_parameter_value(n);return [v.r,v.g,v.b,v.a]
                m.update(strength=material.get_scalar_parameter_value('RobeHemStrength'),shape=vector('RobeHemShape'),points=[vector('RobeHemPoint'+str(k))[:3] for k in range(64)])
            row['materials'].append(m)
        report['parts'].append(row)
(R/'OwnerLayerRepair20261020/held-fit-frame.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print('ROBE_HELD_FRAME_READ',len(report['parts']),flush=True)
