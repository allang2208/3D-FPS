"""Requested read-only review of the current G18 optic mounting assets."""
import hashlib
import json
from pathlib import Path
import unreal as u

OUT = Path(__file__).parent
ROOT = '/Game/Weapons/G18/Integrated20260929'
report = {'scope': 'G18 optic seat only; read-only', 'optics': {}, 'live_components': []}
for variant in ('holographic', 'panoramic_red_dot'):
    mesh = u.load_asset(ROOT + '/Attachments/SM_G18_' + variant)
    source = OUT.parent / 'G18AttachmentRepair20260930/Exports' / ('SM_G18_' + variant + '.fbx')
    stamp = u.EditorAssetLibrary.get_metadata_tag(mesh, 'G18SourceSHA256')
    report['optics'][variant] = {
        'asset': mesh.get_path_name(),
        'import_sources': list(mesh.get_editor_property('asset_import_data').extract_filenames()),
        'repair_metadata': u.EditorAssetLibrary.get_metadata_tag(mesh, 'G18AttachmentRepair'),
        'source_sha256_matches_repaired_fbx': bool(stamp) and stamp == hashlib.sha256(source.read_bytes()).hexdigest(),
        'materials': {str(s.material_slot_name): s.material_interface.get_path_name() for s in mesh.static_materials},
        'aim_center_cm': list(mesh.find_socket('AimCenter').relative_location.to_tuple()),
    }
host = u.load_asset(ROOT + '/Single/SK_G18_Manny')
report['host'] = {'asset': host.get_path_name(),
                  'import_sources': list(host.get_editor_property('asset_import_data').extract_filenames())}
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report['game_world'] = world.get_path_name() if world else None
if world:
    for actor in u.GameplayStatics.get_all_actors_of_class(world, u.Character):
        for component in actor.get_components_by_class(u.StaticMeshComponent):
            mesh = component.get_editor_property('static_mesh')
            if mesh and mesh.get_path_name().startswith(ROOT + '/Attachments/SM_G18_holographic'):
                report['live_components'].append({
                    'component': component.get_path_name(),
                    'parent': component.get_attach_parent().get_path_name(),
                    'socket': str(component.get_attach_socket_name()),
                    'relative_location': list(component.relative_location.to_tuple()),
                    'relative_rotation': list(component.relative_rotation.to_tuple()),
                    'relative_scale': list(component.relative_scale3d.to_tuple()),
                })
(OUT / 'current_assets.json').write_text(json.dumps(report, indent=2), encoding='utf8')
print(json.dumps(report), flush=True)
