"""Read configured whirlwind poses and current weapon mount; no gameplay changes."""
import json
from pathlib import Path
import unreal as u

root = Path('D:/FPS3D/FPSGAME')
out = root / 'SourceAssets/ThirdPersonWhirlwindFacing20261010'
out.mkdir(exist_ok=True)
cfg = json.loads((root / 'Content/ColdSteelData/player_body.json').read_text(encoding='utf-8-sig'))
skills = json.loads((root / 'Content/ColdSteelData/skills.json').read_text(encoding='utf-8-sig'))
mesh = u.load_asset(cfg['body_mesh'])
options = u.AnimPoseEvaluationOptions()
options.optional_skeletal_mesh = mesh
options.evaluation_type = u.AnimDataEvalType.COMPRESSED
def pack(t):
    return [t.translation.x,t.translation.y,t.translation.z,t.rotation.x,t.rotation.y,t.rotation.z,t.rotation.w,
            t.scale3d.x,t.scale3d.y,t.scale3d.z]
report = {'clips': {}, 'live': []}
# The current Tang Dao uses a blade mesh plus a catalog-local half turn.
# Read imported vertices as well: Blender's source axes alone cannot establish
# which edge is actually facing forward in Unreal.
tang = json.loads((root / 'Content/ColdSteelData/tang-dao-modules.json').read_text(encoding='utf-8-sig'))
blade_path = tang['slots']['blade_1']['yanling_edge']['mesh']
blade = u.load_asset(blade_path)
dm, status = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(blade,u.DynamicMesh(),
    u.GeometryScriptCopyMeshFromAssetOptions(),u.GeometryScriptMeshReadLOD())
if status != u.GeometryScriptOutcomePins.SUCCESS: raise RuntimeError('Cannot read current Tang Dao blade')
_, vertices, _ = u.GeometryScript_MeshQueries.get_all_vertex_positions(dm,False)
vertices = u.GeometryScript_List.convert_vector_list_to_array(vertices)
report['tang_dao'] = {'blade': blade_path, 'bone_mount': tang['bone_mount'],
    'vertices': [[v.x,v.y,v.z] for v in vertices]}
for phase in ('Start','Loop','End'):
    key = 'Melee.FullBody.Whirlwind.' + phase
    path = cfg['clips'][key]
    clip = u.load_asset(path)
    row = {'path': path, 'source_hash': u.EditorAssetLibrary.get_metadata_tag(clip,'GripSourceHash'),
        'duration': clip.get_play_length(), 'samples': []}
    for fraction in (0., .25, .5, .75, 1.):
        pose = u.AnimPoseExtensions.get_anim_pose_at_time(clip, fraction*clip.get_play_length(), options)
        row['samples'].append({'fraction': fraction,
            'roll': u.AnimPoseExtensions.get_curve_weight(pose, 'SwordGripRoll'),
            'world': {n: pack(u.AnimPoseExtensions.get_bone_pose(pose,n,u.AnimPoseSpaces.WORLD)) for n in
                ('pelvis','spine_01','spine_03','upperarm_l','lowerarm_l','hand_l','upperarm_r','lowerarm_r','hand_r')}})
    report['clips'][phase] = row
for world in u.EditorLevelLibrary.get_pie_worlds(True)[:1]:
    for actor in u.GameplayStatics.get_all_actors_of_class(world,u.Character):
        body = actor.get_component_by_class(u.FPSPlayerBodyComponent)
        if not body: continue
        state = body.get_body_state()
        row = {'actor': actor.get_name(), 'weapon': str(state.weapon), 'action': str(state.action), 'parts': []}
        for comp in actor.get_components_by_class(u.StaticMeshComponent):
            if not comp.static_mesh or 'Blade' not in comp.static_mesh.get_path_name(): continue
            host = comp.get_attach_parent()
            while host and 'FPSBodyWeaponMeshComponent' not in host.get_name(): host=host.get_attach_parent()
            if not host: continue
            wp=host.get_socket_transform('WPN_root',u.RelativeTransformSpace.RTS_WORLD)
            wp.scale3d=u.Vector(1,1,1)
            transform=comp.get_world_transform()
            local=transform.make_relative(wp)
            row['parts'].append({'asset': comp.static_mesh.get_path_name(), 'visible':comp.is_visible(),
                'in_weapon':pack(local)})
        report['live'].append(row)
(out/'asset-and-mount.json').write_text(json.dumps(report,indent=2))
print('WHIRLWIND_FACING_READ '+json.dumps({'assets':{k:v['path'] for k,v in report['clips'].items()},'live':report['live']}))
