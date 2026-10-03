"""Consolidate saved authoring receipts; never launches an application or a test."""
import json
from pathlib import Path

PROJECT = Path('D:/FPS3D/FPSGAME')
ROOT = PROJECT/'SourceAssets/BlindSupplicantM07Meshy20261001'


def read(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))


def write(name, value):
    (ROOT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


gameplay = read('gameplay_delivery.json')
# These are production save receipts, not runtime acceptance assertions.
if not gameplay.get('gameplay_integrated'):
    raise RuntimeError('Finish the gameplay save operation before finalizing the records.')
physics = gameplay['body_physics']
physics['caller_must_save_packages'] = not physics['saved']
gameplay['production_repair'] = 'Six-section shared cloth rebinding and navigation construction/save completed; user manual test pending.'
write('Authoring/body_physics_delivery.json', physics)
write('gameplay_delivery.json', gameplay)

status = read('production_status.json')
status.update({
    'stage': 'complete local M07 authoring and UE gameplay assets saved; awaiting user manual test',
    'inter_panel_collision': gameplay['interacting_gills']['inter_panel_collision'],
    'cloth_runtime_class': '/Script/FPSGAME.M07InteractingClothingAsset',
    'rig_stage': 'whole body and six gill chains bound; first-pass deformation awaiting user review',
    'animation_stage': '12 gameplay actions and phase-offset gill breathing saved',
    'gameplay_animation_count': len(gameplay['animations']['clips']),
    'body_motion_retargeted': True,
    'body_physics_saved': physics['saved'],
    'body_physics_receipt': 'Authoring/body_physics_delivery.json',
    'interacting_gills_receipt': 'Authoring/interacting_gills_delivery.json',
    'gameplay_integrated': gameplay['gameplay_integrated'],
    'f6_registered': gameplay['f6_registered'],
    'f6': gameplay['f6'],
    'ai_controller': gameplay['character_blueprint']['controller_class'],
    'navigation_built_and_saved': gameplay['navigation']['navigation_built'] and gameplay['navigation']['saved'],
    'navigation_final_save_pending': False,
    'navigation_map': gameplay['navigation']['map'],
    'wall_listen_and_mimic_authored': True,
    'temporary_internal_wall_mimic_voice': True,
    'gameplay_save_receipt': 'gameplay_delivery.json',
    'tested': False,
    'runtime_tested': False,
    'visual_tested': False,
    'user_accepted_model': False,
    'ue_editor_opened': False,
    'pie_started_by_this_task': False,
    'static_high_detail_mesh_not_decimated': True,
})
write('production_status.json', status)

source = read('ue_delivery.json')
source.update({
    'stage': 'M07 source display/PBR/breath assets saved; later gameplay and shared cloth authoring also saved',
    'original_six_cloth_stage_is_historical': True,
    'current_shared_cloth_receipt': 'Authoring/interacting_gills_delivery.json',
    'inter_panel_collision': True,
    'gameplay_integrated': True,
    'f6_registered': True,
    'current_gameplay_receipt': 'gameplay_delivery.json',
    'runtime_tested': False,
    'visual_tested': False,
})
write('ue_delivery.json', source)

authoring = read('Authoring/authoring_delivery.json')
authoring.update({
    'stage': 'editable source, whole-body actions, cloth and UE gameplay packages saved; awaiting user test',
    'gameplay_motion_source': 'Motion/M07_GameplayMotion.blend',
    'control_motion_source': 'Motion/M07_ControlMotion.blend',
    'gameplay_motion_manifest': 'Motion/motion_manifest.json',
    'control_motion_manifest': 'Motion/control_motion_manifest.json',
    'gameplay_save_receipt': 'gameplay_delivery.json',
    'current_interacting_cloth_receipt': 'Authoring/interacting_gills_delivery.json',
    'semantic_seams_user_accepted': False,
    'runtime_tested': False,
    'visual_tested': False,
})
write('Authoring/authoring_delivery.json', authoring)

audio = read('Audio/audio_production.json')
audio.update({'engine_imported': True, 'engine_asset': gameplay['audio']['asset'], 'engine_asset_saved': True})
write('Audio/audio_production.json', audio)
print('M07 saved source/gameplay delivery records consolidated; user testing remains pending.')
