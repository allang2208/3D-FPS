"""Reconcile current M07 production metadata from its actual save receipt."""
import json
from pathlib import Path

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
SOURCE = ROOT/'RecoveryOriginalV06'
receipt = json.loads((SOURCE/'ue_original_delivery_v06.json').read_text(encoding='utf-8'))
anatomy = json.loads((SOURCE/'anatomy_delivery.json').read_text(encoding='utf-8'))
if not receipt['saved']:
    raise RuntimeError('OriginalV06 is not saved; current delivery metadata cannot be activated.')
for name in ('production_status.json', 'gameplay_delivery.json'):
    path = ROOT/name
    record = json.loads(path.read_text(encoding='utf-8-sig'))
    record.update({
        'stage': receipt['stage'], 'revision': 'OriginalV06',
        'development_route': 'Original Meshy body and gill surfaces, fresh original-fitted skeleton and skin, hidden 3D cloth proxies and collision, clean-source motion',
        'mesh': receipt['mesh'], 'skeleton': receipt['skeleton'],
        'source_faces_preserved': True,
        'source_faces_preserved_scope': 'All 1745634 original triangles, UV and PBR retained in the high master; game display is a reduced copy of these original surfaces',
        'display_triangles': anatomy['display_triangles'],
        'original_visible_body_preserved': True, 'donor_display_body_used': False,
        'six_mantle_leaves_geometry_reconstructed': False,
        'game_surface_reduced_from_original': True, 'static_high_detail_mesh_not_decimated': False,
        'editable_source_revision': str(SOURCE),
        'editable_source': 'RecoveryOriginalV06/M07_Original_Skinned_Master_V06.blend',
        'combined_editable_source': 'RecoveryOriginalV06/M07_Original_Skinned_Master_V06.blend',
        'active_authoring_source': 'RecoveryOriginalV06/M07_Original_Skinned_Master_V06.blend',
        'display_export': 'RecoveryOriginalV06/SK_M07_Display_OriginalV06.fbx',
        'cloth_construction_export': 'RecoveryOriginalV06/SK_M07_ClothBuildSource_OriginalV06.fbx',
        'ue_save_receipt': 'RecoveryOriginalV06/ue_original_delivery_v06.json',
        'body_physics_receipt': 'RecoveryOriginalV06/ue_original_delivery_v06.json',
        'interacting_gills_receipt': 'RecoveryOriginalV06/ue_original_delivery_v06.json',
        'body_physics': receipt['body_physics'], 'interacting_gills': receipt['cloth'],
        'cloth_captured_display_vertices': receipt['cloth']['cloth_captured_display_vertices'],
        'skin_only_display_vertices': receipt['cloth']['skin_only_display_vertices'],
        'reference_units': receipt['reference_units'],
        'rig_stage': '81 original-fitted centimeter bones; armature scale 1; common frame-zero reference',
        'skin_weights_stage': 'Original-surface anatomical/digit restricted weights and surface diffusion; shared seam weights; untested candidate',
        'animation_stage': '12 fresh OriginalV06 source-reference actions saved',
        'blender_surface_deform_bindings': anatomy['blender_surface_deform_bindings'],
        'blender_body_collision_capsules_authored': anatomy['blender_body_collision_count'],
        'blender_cloth_authoring_mode_default': False,
        'blender_cloth_binding_receipt': 'RecoveryOriginalV06/anatomy_delivery.json',
        'cloth_simulation_played': False,
        'editor_build': {'result': 'Succeeded', 'log': 'Saved/BuildEditor/m07-FPSGAMEEditor-20261002-115811.log'},
        'game_build': {'result': 'Succeeded', 'log': 'Saved/BuildEditor/m07-FPSGAME-20261002-120530.log'},
        'final_import_log': 'Saved/Logs/M07Import-20261002-120134.log',
        'original_v06_saved': True, 'anatomy_v05_rejected_by_user': True,
        'tested': False, 'runtime_tested': False, 'visual_tested': False,
        'user_accepted_model': False, 'user_review_pending': True,
        'claimed_visual_fix': False,
    })
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
receipt['editor_build'] = {'result': 'Succeeded', 'log': 'Saved/BuildEditor/m07-FPSGAMEEditor-20261002-115811.log'}
receipt['game_build'] = {'result': 'Succeeded', 'log': 'Saved/BuildEditor/m07-FPSGAME-20261002-120530.log'}
(SOURCE/'ue_original_delivery_v06.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('OriginalV06 current source and actual saved asset metadata recorded; untested', flush=True)
