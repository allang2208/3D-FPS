"""Read the existing PIE pose and equipment identities; do not drive gameplay."""
import json
from pathlib import Path
import unreal as u

out = Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonSwordLeftContact20261010')
out.mkdir(parents=True, exist_ok=True)
worlds = u.EditorLevelLibrary.get_pie_worlds(True)
report = {'pie_active': bool(worlds), 'bodies': []}
def pack(t):
    return [t.translation.x, t.translation.y, t.translation.z, t.rotation.x, t.rotation.y, t.rotation.z, t.rotation.w,
            t.scale3d.x, t.scale3d.y, t.scale3d.z]
for world in worlds[:1]:
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Character):
        component = actor.get_component_by_class(u.FPSPlayerBodyComponent)
        if not component:
            continue
        body = component.get_body_mesh()
        if not body:
            continue
        anim = body.get_anim_instance()
        state = component.get_body_state()
        row = {'actor': actor.get_name(), 'body': body.skeletal_mesh_asset.get_path_name(),
               'state': {key: str(state.get_editor_property(key)) for key in
                   ('family', 'weapon', 'action', 'action_variant', 'action_progress', 'action_weight')},
               'grip_slide': anim.get_curve_value('SwordGripSlide'), 'grip_roll': anim.get_curve_value('SwordGripRoll'), 'bones': {}, 'meshes': []}
        for i in range(body.get_num_bones()):
            name = body.get_bone_name(i)
            row['bones'][str(name)] = pack(body.get_socket_transform(name, u.RelativeTransformSpace.RTS_WORLD))
        config = json.loads(Path('D:/FPS3D/FPSGAME/Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
        row['configured_clips'] = {k: v for k, v in config['clips'].items()
                        if k in ('Melee.FullBody.Overhead', 'Melee.FullBody.DashOverhead')}
        for mesh in actor.get_components_by_class(u.SkeletalMeshComponent):
            if not mesh.skeletal_mesh_asset:
                continue
            item = {'name': mesh.get_name(), 'asset': mesh.skeletal_mesh_asset.get_path_name(),
                    'visible': mesh.is_visible(), 'hidden': mesh.get_editor_property('hidden_in_game'),
                    'component': pack(mesh.get_world_transform()), 'bones': {}}
            for name in ('hand_r', 'hand_l', 'WPN_root'):
                if mesh.get_bone_index(name) >= 0:
                    item['bones'][name] = pack(mesh.get_socket_transform(name, u.RelativeTransformSpace.RTS_WORLD))
            row['meshes'].append(item)
        report['bodies'].append(row)
(out / 'live-pair.json').write_text(json.dumps(report, indent=2))
print('LEFT_CONTACT_LIVE ' + str(len(report['bodies'])) + ' bodies; PIE=' + str(report['pie_active']))

import json
from pathlib import Path
import unreal as u
out=Path('D:/FPS3D/FPSGAME/SourceAssets/ThirdPersonSwordLeftContact20261010')
rows=[]
for world in u.EditorLevelLibrary.get_pie_worlds(True)[:1]:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        for comp in actor.get_components_by_class(u.StaticMeshComponent):
            parent=comp.get_attach_parent()
            if not comp.static_mesh or '_Grip_' not in comp.static_mesh.get_path_name():continue
            while parent and 'FPSBodyWeaponMeshComponent' not in parent.get_name():parent=parent.get_attach_parent()
            if not parent:continue
            wp=parent.get_socket_transform('WPN_root',u.RelativeTransformSpace.RTS_WORLD)
            wp.scale3d=u.Vector(1,1,1)
            dm,status=u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(comp.static_mesh,u.DynamicMesh(),u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
            if status!=u.GeometryScriptOutcomePins.SUCCESS:raise RuntimeError(comp.static_mesh.get_path_name())
            _,pv,_=u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
            pv=u.GeometryScript_List.convert_vector_list_to_array(pv)
            t=comp.get_world_transform()
            vals=[wp.inverse_transform_location(t.transform_location(v)) for v in pv]
            rows.append({'asset':comp.static_mesh.get_path_name(),'component':comp.get_name(),'visible':comp.is_visible(),
                'min':[min(getattr(v,k) for v in vals) for k in ('x','y','z')],
                'max':[max(getattr(v,k) for v in vals) for k in ('x','y','z')]})
(out/'handle-parts.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows))
