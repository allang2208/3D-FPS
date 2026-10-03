"""Reconcile current M07 production metadata from its actual save receipt."""
import json
import argparse
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--editor-log', required=True)
parser.add_argument('--game-log', required=True)
parser.add_argument('--import-log', required=True)
args = parser.parse_args()

ROOT = Path('D:/FPS3D/FPSGAME/SourceAssets/BlindSupplicantM07Meshy20261001')
SOURCE = ROOT/'RecoveryOriginalV08'
receipt = json.loads((SOURCE/'ue_original_delivery_v08.json').read_text(encoding='utf-8'))
anatomy = json.loads((SOURCE/'anatomy_delivery.json').read_text(encoding='utf-8'))
navigation = json.loads((SOURCE/'navigation/navigation_delivery_original_v08.json').read_text(encoding='utf-8'))
if not receipt['saved']:
    raise RuntimeError('OriginalV08 is not saved; current delivery metadata cannot be activated.')
if not navigation.get('saved'):
    raise RuntimeError('OriginalV08 navigation map was not saved; navigation metadata cannot be activated.')
for name in ('production_status.json', 'gameplay_delivery.json'):
    path = ROOT/name
    record = json.loads(path.read_text(encoding='utf-8-sig'))
    record.pop('hindleg_anatomy', None)
    record.update({
        'stage': receipt['stage'], 'revision': 'OriginalV08',
        'development_route': 'Original Meshy body and locally separated gill surfaces, original-UV PBR restored, human palm/digit anatomy, original biped reference and corrected leg control, hidden cloth and collision',
        'mesh': receipt['mesh'], 'skeleton': receipt['skeleton'],
        'source_faces_preserved': True,
        'source_faces_preserved_scope': 'Original GLB and V06 frozen master retained unchanged. V08 high master retains all original triangle topology and UV with the saved V07 organic-layer separation; game display is a reduced copy.',
        'display_triangles': anatomy['display_triangles'],
        'original_visible_body_preserved': True, 'donor_display_body_used': False,
        'six_mantle_leaves_geometry_reconstructed': False,
        'game_surface_reduced_from_original': True, 'static_high_detail_mesh_not_decimated': False,
        'editable_source_revision': str(SOURCE),
        'editable_source': 'RecoveryOriginalV08/M07_Original_Skinned_Master_V08.blend',
        'combined_editable_source': 'RecoveryOriginalV08/M07_Original_Skinned_Master_V08.blend',
        'active_authoring_source': 'RecoveryOriginalV08/M07_Original_Skinned_Master_V08.blend',
        'display_export': 'RecoveryOriginalV08/SK_M07_Display_OriginalV08.fbx',
        'cloth_construction_export': 'RecoveryOriginalV08/SK_M07_ClothBuildSource_OriginalV08.fbx',
        'ue_save_receipt': 'RecoveryOriginalV08/ue_original_delivery_v08.json',
        'body_physics_receipt': 'RecoveryOriginalV08/ue_original_delivery_v08.json',
        'interacting_gills_receipt': 'RecoveryOriginalV08/ue_original_delivery_v08.json',
        'body_physics': receipt['body_physics'], 'interacting_gills': receipt['cloth'],
        'cloth_captured_display_vertices': receipt['cloth']['cloth_captured_display_vertices'],
        'skin_only_display_vertices': receipt['cloth']['skin_only_display_vertices'],
        'reference_units': receipt['reference_units'],
        'rig_stage': str(anatomy['bone_count'])+' original-fitted centimeter bones; human metacarpals and original thigh/calf/foot/ball legs; armature scale 1; common frame-zero reference',
        'skin_weights_stage': 'Surface-branch isolated human hand weights; original biped knee/ankle/toe fields; shared original body/gill attachments; untested candidate',
        'materials': receipt['materials'],
        'navigation': navigation,
        'hand_anatomy': receipt['hand_anatomy'], 'biped_leg_authoring': receipt['biped_leg_authoring'],
        'gill_surface_recipe': receipt['gill_surface_recipe'],
        'animation_stage': '12 fresh OriginalV08 source-reference actions saved',
        'blender_surface_deform_bindings': anatomy['blender_surface_deform_bindings'],
        'blender_body_collision_capsules_authored': anatomy['blender_body_collision_count'],
        'blender_cloth_authoring_mode_default': False,
        'blender_cloth_binding_receipt': 'RecoveryOriginalV08/anatomy_delivery.json',
        'cloth_simulation_played': False,
        'editor_build': {'result': 'Succeeded', 'log': args.editor_log},
        'game_build': {'result': 'Succeeded', 'log': args.game_log},
        'final_import_log': args.import_log,
        'original_v08_saved': True, 'anatomy_v05_rejected_by_user': True,
        'tested': False, 'runtime_tested': False, 'visual_tested': False,
        'user_accepted_model': False, 'user_review_pending': True,
        'claimed_visual_fix': False,
    })
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
receipt['editor_build'] = {'result': 'Succeeded', 'log': args.editor_log}
receipt['game_build'] = {'result': 'Succeeded', 'log': args.game_log}
receipt['final_import_log'] = args.import_log
receipt['navigation'] = navigation
(SOURCE/'ue_original_delivery_v08.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
print('OriginalV08 current source and actual saved asset metadata recorded; untested', flush=True)
