"""Live editor probe: can a component accept the viewmodel meshes and evaluate clips?

Read-only: creates transient objects only, never touches the level or saves anything.
"""
import unreal as u

GRIP = '/Game/Items/ProductionTools/GripMotion20260913'


def probe(label, mesh_path, anim_path):
    mesh = u.load_asset(mesh_path)
    anim = u.load_asset(anim_path)
    skeleton = mesh.get_editor_property('skeleton') if mesh else None
    out = [f'{label}: mesh={"ok" if mesh else "MISSING"}',
           f'  skeleton={skeleton.get_path_name() if skeleton else None}',
           f'  anim={"ok" if anim else "MISSING"} '
           f'skeleton={anim.get_editor_property("skeleton").get_path_name() if anim and anim.get_editor_property("skeleton") else None}']
    component = u.new_object(u.SkeletalMeshComponent) if mesh else None
    if component:
        component.set_editor_property('skeletal_mesh_asset', mesh)
        accepted = component.get_editor_property('skeletal_mesh_asset')
        out.append(f'  component_accepted={bool(accepted)}')
        if accepted and anim:
            ref_pose = component.get_editor_property('skeletal_mesh_asset').get_editor_property('skeleton')
            try:
                component.play_animation(anim, False)
                component.set_play_rate(0.0)
                component.set_position(0.4, False)
                component.tick_animation(0.0, False)
                component.refresh_bone_transforms()
                index = component.get_editor_property('skeletal_mesh_asset').get_editor_property('skeleton') and None
                bone = component.get_bone_name(1)
                transform = component.get_bone_transform(bone, u.BoneSpaces.WORLD_SPACE)
                out.append(f'  bone[1]={bone} world_loc=({transform.translation.x:.3f},{transform.translation.y:.3f},{transform.translation.z:.3f})')
                out.append('  ANIM_EVALUATED')
            except Exception as error:
                out.append(f'  ANIM_FAILED {error}')
    for line in out:
        print(line)
    return out


probe('AXE', f'{GRIP}/SK_Harvest_Axe', f'{GRIP}/A_Harvest_Axe_Idle')
probe('PICKAXE', f'{GRIP}/SK_Harvest_Pickaxe', f'{GRIP}/A_Harvest_Pickaxe_Idle')
print('LIVE_COMPONENT_PROBE_DONE')