"""Record completed production after the root's normal Game/Editor builds."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ACTIVE = HERE.parent
PROJECT = ACTIVE.parents[1]
REVISION = 2026100211


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def finish():
    authored = read(ACTIVE / 'full-pose.json')
    editable = read(ACTIVE / 'editable-source.json')
    coverage = {
        'rifles_machine_guns_and_single_pistols': 'existing common native left-arm layer',
        'dual_pistols_and_staff_offhand_pistol': 'existing left-side owner; left weapon and attachments stow during the gesture',
        'swords': 'existing native sword mesh evaluates its base before the common left-arm layer',
        'staves': 'existing staff left arm or offhand pistol is the single pose owner',
        'axes_and_pickaxes': 'existing production tool native arm layer',
        'unarmed_idle_walk_run': 'existing unarmed base before common left-arm layer; right fist continues its base motion',
        'bows': 'dedicated same-clock stow/return; retain ready state and keep original bow pose sampling for fallback recovery',
        'static_tools_without_arms_including_shovel': 'canonical V7 fallback; enter and recover below frame from the existing authored empty-hand example',
    }
    completed = dict(
        revision=REVISION, date='2026-10-02',
        status='authored_runtime_table_and_editable_source_saved_normal_builds_complete',
        feedback=dict(camera_amplitude_multiplier=1.6, duration_seconds=.18,
            peak_seconds=.018, backward_cm=1.28, downward_cm=.40,
            pitch_degrees=1.12, roll_degrees=.32,
            left_arm_sway_multiplier=2.0, guard_sway=authored['guard_sway']),
        action=dict(prepare_seconds=.06, hold_seconds=.30, contact_seconds=.36,
            recovery_seconds=.197, duration_seconds=.557,
            existing_fist_and_wrist_preserved=True, forward_push=False),
        coverage=coverage,
        handoff=dict(native_entry='captured complete current left chain',
            native_recovery='current live base pose, not frozen entry',
            no_native_arms_entry_recovery='authored empty-hand idle example lowered 6cm and retracted 2cm',
            weapon_bone_subtrees_excluded=True,
            fallback_outfit_preloaded=True, door_uses_reload_action_framing=False),
        editable_source=editable['source'], editable_take=editable['take'],
        editable_frames=editable['frames_including_endpoint'],
        editable_fps=editable['fps'], ue_animation_asset_import_required=False,
        native_builds=dict(game='normal_build_succeeded', editor='normal_build_succeeded',
            logs_directory='Saved/DoorPushFeedbackAllWeaponsV10_20261002'),
        build_blocker_repair=dict(source='Source/FPSGAME/Monsters/BlindSupplicantMonster.cpp',
            compiler_error='C4458 local Controller hides APawn::Controller',
            repair='rename the local variable and its one use to ViewerController; behavior unchanged',
            first_failure_log='Saved/DoorPushFeedbackAllWeaponsV10_20261002/FPSGAME-first-build-failure.log'),
        user_audio_changed=False, skin_materials_or_weights_changed=False,
        source_assets_changed=True, interactive_editor_started=False,
        runtime_tested=False, rendered=False, auditioned=False,
        acceptance='user tests in game')
    write(HERE / 'completion.json', completed)
    integration = read(ACTIVE / 'integration-completion.json')
    integration.update(revision=REVISION, editable_action=editable['take'],
        feedback_all_weapons_integration='SourceAssets/DoorPush20261002/FeedbackAllWeaponsV10_20261002/completion.json',
        weapon_coverage=coverage, current_guard_sway=authored['guard_sway'],
        latest_revision_build=dict(game_build='normal_build_succeeded',
            editor_build='normal_build_succeeded',
            logs_directory='Saved/DoorPushFeedbackAllWeaponsV10_20261002',
            runtime_tested=False, rendered=False))
    integration['impact_feedback'].update(backward_cm=1.28, downward_cm=.40,
        pitch_degrees=1.12, roll_degrees=.32, amplitude_multiplier_from_previous=1.6)
    write(ACTIVE / 'integration-completion.json', integration)
    print('DOOR_PUSH_V10_SOURCE_AND_BUILD_COMPLETION_RECORDED')


if __name__ == '__main__':
    finish()
