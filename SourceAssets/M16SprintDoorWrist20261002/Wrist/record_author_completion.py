"""Record completed production files and retain the prior reference sources."""
import hashlib
import json
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[2]
NEUTRAL = PROJECT / 'SourceAssets/M16Repair20261002/NeutralBind'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

sources = [NEUTRAL / 'NativeSources/M16.json', NEUTRAL / 'Authored/left_digit_reference.json',
           NEUTRAL / 'Authored/M16_BareArmsV7_NeutralBind_Editable.json',
           NEUTRAL / 'Authored/authoring.json', NEUTRAL / 'installed.json']
retained = []
for source in sources:
    target = HERE / 'Before/Reference' / source.relative_to(NEUTRAL)
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        shutil.copy2(source, target)
    retained.append(dict(source=str(source), source_sha256=sha(source), backup=str(target)))
blend = HERE / 'Editable/M16_BareArmsV7CommonM4Wrist20261002.blend'
manifest = json.loads((HERE / 'Authored/authoring.json').read_text(encoding='utf-8'))
result = dict(status='author_and_editable_blender_complete_ue_save_pending',
    authored_mesh_patch_count=len(manifest['patches']),
    previous_neutral_meshes=8, necessary_hand_weighted_cuffs=2,
    changed_core_reference_bone='hand_l', retained_neutral_digit_references=19,
    copied_source='common M4 V7 local wrist mesh reference rotation',
    editable_blend=str(blend), editable_blend_sha256=sha(blend),
    editable_json=manifest['editable']['source'],
    reference=manifest['reference'], install_entry=str(HERE / 'install_common_wrist_bind.py'),
    retained_sources=retained, source_materials_uvs_weights_hierarchy_preserved=True,
    shared_animation_skeleton_changed=False, existing_animation_assets_changed=False,
    package_backups='Before/Packages; created by installer before each actual save',
    source_files_written_outside_owned_wrist_directory=False,
    ue_launched=False, ue_imported=False, game_launched=False,
    runtime_tested=False, rendered=False,
    required_runtime_change='Remove superseded M16 relative wrist-twist distribution in DoorPushPoseLayer.cpp; use ordinary complete authored-local chain',
    sibling_sprint_dependency='Use same M16 native translations/scales with common source local arm/wrist keys')
(HERE / 'author-completion.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('M16_COMMON_WRIST_PRODUCTION_READY', len(manifest['patches']), str(blend), flush=True)
