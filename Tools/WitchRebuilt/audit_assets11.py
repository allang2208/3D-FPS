"""Read-only asset snapshot for the user's accepted Witch review."""
import json
from pathlib import Path
import unreal as u

OUT = Path('D:/FPS3D/FPSGAME/SourceAssets/WitchRebuilt20260921/Revision11')
OUT.mkdir(exist_ok=True)
BASE = '/Game/Monsters/WitchRebuilt'
mesh = u.load_asset(BASE + '/SK_WitchRebuilt')
skeletal_tools = u.get_editor_subsystem(u.SkeletalMeshEditorSubsystem)
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report = {'mesh': mesh.get_path_name(), 'skeleton': mesh.skeleton.get_path_name(),
          'physics': mesh.physics_asset.get_path_name(), 'bounds': str(mesh.get_bounds()),
          'lod_count': skeletal_tools.get_lod_count(mesh),
          'lod0_vertices': skeletal_tools.get_num_verts(mesh, 0) if not world else None,
          'lod0_sections': skeletal_tools.get_num_sections(mesh, 0) if not world else None,
          'lod_counts_note': 'Editor section/vertex API is unavailable during PIE' if world else None,
          'materials': [], 'animations': [], 'cloth': []}
for slot in mesh.materials:
    mat = slot.material_interface
    report['materials'].append({'slot': str(slot.get_editor_property('imported_material_slot_name')),
                               'material': mat.get_path_name() if mat else None})
for name in ('Idle', 'Walk', 'CastPoison', 'ThrowPoisonBottle', 'DeathBackward', 'Hit', 'TurnLeft', 'TurnRight'):
    clip = u.load_asset(BASE + '/Animations/A_WitchRebuilt_' + name)
    report['animations'].append({'role': name, 'asset': clip.get_path_name() if clip else None,
        'skeleton': clip.get_editor_property('skeleton').get_path_name() if clip else None,
        'length_s': clip.get_play_length() if clip else None})
for cloth in mesh.get_editor_property('mesh_clothing_assets'):
    configs = []
    for config in cloth.get_editor_property('cloth_configs').values():
        fields = {}
        for key in ('IterationCount', 'MaxIterationCount', 'SubdivisionCount', 'bUseSelfCollisions',
                    'bUseSelfCollisionSpheres', 'bUseCCD', 'CollisionThickness'):
            try:
                fields[key] = config.get_editor_property(key)
            except Exception:
                pass
        configs.append({'class': config.get_class().get_name(), 'values': fields})
    report['cloth'].append({'name': cloth.get_name(), 'configs': configs})
material = u.load_asset(BASE + '/Materials/M_WitchRebuilt_Fabric09')
report['fabric'] = {key: str(material.get_editor_property(key)) for key in ('blend_mode', 'two_sided')}
lib = u.MaterialEditingLibrary
report['fabric_graph'] = []
for expression in lib.get_material_expressions(material):
    report['fabric_graph'].append({'name': expression.get_name(), 'class': expression.get_class().get_name(),
        'pins': list(lib.get_material_expression_input_names(expression)),
        'inputs': [x.get_name() if x else None for x in lib.get_inputs_for_material_expression(material, expression)]})
report['dirty_packages'] = [p.get_path_name() for p in list(u.EditorLoadingAndSavingUtils.get_dirty_content_packages()) + list(u.EditorLoadingAndSavingUtils.get_dirty_map_packages())]
defaults = u.get_default_object(u.DevelopmentSpawnComponent)
report['witch_entries'] = [str(row) for row in defaults.get_editor_property('monsters') if 'Witch' in str(row)]
world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_game_world()
report['world'] = world.get_path_name() if world else None
report['active_witches'] = [a.get_path_name() for a in u.GameplayStatics.get_all_actors_of_class(world, u.WitchRebuiltMonster)] if world else []
report['physics_reference_snapshot_ok'] = u.WitchRebuiltMonster.prepare_rebuilt_physics(mesh, False)
(OUT / 'asset_audit.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False))
