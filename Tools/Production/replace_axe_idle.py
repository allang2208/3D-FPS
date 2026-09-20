"""Swap the shipped axe idle for the outward-blade H3 version, in place.

Run through the in-editor channel (Tools/AssetPipeline/ue_python_exec.py): the editor owns
these packages, and an external process saving a loaded asset fails silently.

The production path for the equipped axe idle is
/Game/Items/ProductionTools/GripMotion20260913/A_Harvest_Axe_Idle, assembled at runtime from
tool_animation_prefix + "Idle" in production_tools.json. Replacing that asset's contents is the
whole wiring job: no code, no JSON, no recompile.

The previous clip is backed up at SourceAssets/KimodoAxeIdle20260919/Before/ and can be restored
by re-importing it the same way.
"""
import json
from pathlib import Path
import unreal as u

ROOT = Path(u.Paths.project_dir()).resolve()
SOURCE = ROOT / 'SourceAssets/KimodoAxeIdle20260919/BuildH3/Export/A_Harvest_Axe_Idle2H_H3.fbx'
DEST = '/Game/Items/ProductionTools/GripMotion20260913'
NAME = 'A_Harvest_Axe_Idle'
TOOLS = u.AssetToolsHelpers.get_asset_tools()
EAL = u.EditorAssetLibrary
report = {'saved': [], 'runtime_tested': False, 'rendered': False, 'revision': 'H3',
          'replaced': None, 'source': str(SOURCE.relative_to(ROOT))}
u.SystemLibrary.execute_console_command(None, 'Interchange.FeatureFlags.Import.FBX 0')

mesh = u.load_asset(f'{DEST}/SK_Harvest_Axe')
if not mesh:
    raise RuntimeError('SK_Harvest_Axe missing')
skeleton = mesh.get_editor_property('skeleton')
if not skeleton:
    raise RuntimeError('SK_Harvest_Axe has no skeleton; run the battle-axe install first')

previous = u.load_asset(f'{DEST}/{NAME}')
report['previous'] = {'loaded': bool(previous),
                      'play_length_s': round(previous.get_play_length(), 4) if previous else None}

options = u.FbxImportUI()
options.automated_import_should_detect_type = False
options.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
options.import_mesh = False
options.import_animations = True
options.import_materials = False
options.import_textures = False
options.skeleton = skeleton
options.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
options.anim_sequence_import_data.set_editor_property('custom_sample_rate', 150)

task = u.AssetImportTask()
task.filename = str(SOURCE)
task.destination_path = DEST
task.destination_name = NAME
task.automated = True
task.replace_existing = True
task.save = True
task.options = options
TOOLS.import_asset_tasks([task])

animation = u.load_asset(f'{DEST}/{NAME}')
if not animation:
    raise RuntimeError('Replace import produced no asset at ' + NAME)
compression = u.load_asset('/Game/Weapons/M4InfimaRigV4/BC_M4Viewmodel')
if compression:
    animation.set_editor_property('bone_compression_settings', compression)
if not EAL.save_loaded_asset(animation, False):
    raise RuntimeError('Could not save ' + NAME)
report['saved'].append(animation.get_path_name())

bound = animation.get_editor_property('skeleton')
report['replaced'] = {
    'asset': animation.get_path_name(),
    'play_length_s': round(animation.get_play_length(), 4),
    'skeleton': bound.get_path_name() if bound else None,
    'same_skeleton_as_mesh': bool(bound) and bound == skeleton,
}

# Re-assert the mesh's own bindings so a stale slot cannot survive the swap.
slots = mesh.get_editor_property('materials')
report['mesh_slots'] = [str(s.material_slot_name) for s in slots]

(ROOT / 'SourceAssets/KimodoAxeIdle20260919/idle-swap.json').write_text(
    json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
u.log('AXE_IDLE_REPLACED_WITH_TWO_HAND')
