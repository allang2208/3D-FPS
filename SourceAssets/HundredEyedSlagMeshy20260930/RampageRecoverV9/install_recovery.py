"""Save only the recovery-repaired slam at the existing game's asset path."""
import json
import re
import shutil
import sys
from pathlib import Path

import unreal as u

OUT = Path(__file__).resolve().parent
ROOT = OUT.parent
PROJECT = OUT.parents[2]
BASE = '/Game/Monsters/HundredEyedSlag'
CLIP_PATH = BASE + '/V1/Animations/A_HundredEyedSlag_AttackSlam_R'
SKELETON_PATH = BASE + '/V1/SK_HundredEyedSlag_V1_Skeleton'
MESH_PATH = BASE + '/PolishV2/SK_HundredEyedSlag_V2'
LIB = u.EditorAssetLibrary
REVISION = 'HundredEyedSlagRampageRecoverV9_20261001'

if Path(u.Paths.project_dir()).resolve() != PROJECT.resolve():
    raise RuntimeError('Wrong project; no assets replaced')
if u.EditorLevelLibrary.get_game_world() is not None:
    raise RuntimeError('PIE must end before replacing the running attack asset')
dirty_before = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
conflicts = dirty_before.intersection({CLIP_PATH, SKELETON_PATH})
if conflicts:
    raise RuntimeError('Unsaved target assets preserved: ' + str(sorted(conflicts)))
for path in [CLIP_PATH, SKELETON_PATH]:
    for suffix in ['.uasset', '.uexp', '.ubulk']:
        source = PROJECT / 'Content' / (path.removeprefix('/Game/') + suffix)
        backup = OUT / 'Before' / (path.removeprefix('/Game/') + suffix)
        if source.exists() and not backup.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)

skeleton = u.load_asset(SKELETON_PATH)
mesh = u.load_asset(MESH_PATH)
if skeleton is None or mesh is None:
    raise RuntimeError('Saved V8 skeleton and mesh required')
op = u.FbxImportUI()
op.automated_import_should_detect_type = False
op.override_full_name = True
op.mesh_type_to_import = u.FBXImportType.FBXIT_ANIMATION
op.import_as_skeletal = True
op.import_mesh = False
op.import_animations = True
op.import_materials = False
op.import_textures = False
op.skeleton = skeleton
op.anim_sequence_import_data.set_editor_property('use_default_sample_rate', False)
op.anim_sequence_import_data.set_editor_property('custom_sample_rate', 30)
task = u.AssetImportTask()
task.filename = str(OUT / 'Delivery/Animations/A_HundredEyedSlag_AttackSlam_R_RampageRecoverV9.fbx')
task.destination_path, task.destination_name = CLIP_PATH.rsplit('/', 1)
task.automated = True
task.save = False
task.replace_existing = True
task.replace_existing_settings = True
task.options = op
variable = 'Interchange.FeatureFlags.Import.FBX'
previous_importer = u.SystemLibrary.get_console_variable_int_value(variable)
u.SystemLibrary.execute_console_command(None, variable + ' 0')
try:
    u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    clip = u.load_asset(CLIP_PATH)
    imported = [p.split('.')[0] for p in task.imported_object_paths]
    if clip is None or CLIP_PATH not in imported:
        raise RuntimeError('Animation replacement did not complete: ' + str(imported))
    sys.path.insert(0, str(PROJECT / 'Tools/InfectedDog'))
    from meshy_animation_units import match_bind_root_scale
    units = match_bind_root_scale(clip, mesh)
    clip.set_preview_skeletal_mesh(mesh)
    LIB.set_metadata_tag(clip, 'HundredEyedSlag.Revision', REVISION)
    LIB.set_metadata_tag(clip, 'HundredEyedSlag.RecoveryOnly', 'V8 keys 1-32 retained; V9 recovery keys 33-55')
    if not LIB.save_loaded_asset(clip, False):
        raise RuntimeError('Could not save the repaired slam')
    skeleton_saved = False
    dirty_after = {p.get_name() for p in u.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if SKELETON_PATH in dirty_after:
        if not LIB.save_loaded_asset(skeleton, True):
            raise RuntimeError('Could not save the importer-updated existing skeleton')
        skeleton_saved = True
finally:
    u.SystemLibrary.execute_console_command(None, variable + ' ' + str(previous_importer))

mode = ('background_commandlet' if '-run=pythonscript' in u.SystemLibrary.get_command_line().lower()
        else 'existing_editor_bridge')
completion = dict(revision='RampageRecoverV9', base_revision='RampageV8', assets_saved=True,
    animation_assets_saved=1, animation_path=clip.get_path_name(), seconds=clip.get_play_length(),
    mesh_assets_saved=0, skeleton_saved=skeleton_saved,
    total_assets_saved=1 + int(skeleton_saved), execution_mode=mode, units=units,
    authored_preserved_key_frames=[1, 32], authored_recovery_key_frames=[33, 55],
    sweep_reimported=False, weights_changed=False, new_bones=0,
    native_hit_window_s=[.84, 1.00], native_code_changed=False, native_build_required=False,
    runtime_paths_preserved=True, runtime_tested=False, preview_rendered=False,
    user_accepted_recovery=False, ue_editor_started_by_this_task=False)
(OUT / 'installation_complete.json').write_text(json.dumps(completion, indent=2), encoding='utf-8')

status_path = ROOT / 'production_status.json'
status = json.loads(status_path.read_text(encoding='utf-8-sig'))
status.update(active_revision='RampageRecoverV9', working_revision='RampageRecoverV9',
    stage='slam_recovery_saved', delivery='RampageRecoverV9/Delivery',
    mesh_revision='RampageV8', sweep_revision='RampageV8', slam_revision='RampageRecoverV9',
    recovery_installation='RampageRecoverV9/installation_complete.json',
    targeted_animation_roles=['AttackSlam_R'], revision_saved_asset_count=completion['total_assets_saved'],
    pending_ue_animation_installation=False, native_code_changed=False, native_build_required=False,
    tested=False, animation_tested=False, runtime_tested=False, pie_tested=False, preview_rendered=False,
    user_accepted_animation=False, user_accepted_sweep_revision='RampageV8',
    user_accepted_slam_strike_revision='RampageV8', user_accepted_slam_recovery=False,
    ue_editor_started_by_this_task=False)
status.pop('current_installation_blocker', None)
status.pop('candidate_delivery', None)
status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding='utf-8')

readme = ROOT / 'README.md'
current = '''## 当前交付

当前运行组合为 `RampageV8` 网格、蒙皮与横扫，配合 `RampageRecoverV9` 下劈。用户已认可 V8 的横扫、下劈攻击主体，同时指出下劈 recover 大右手仍扭曲；这次仅修订下劈收势，新收势尚待用户体验。

V9 复制 V8 下劈动作，保留第 1–32 帧（0–1.033 秒）的原始动画键，重写第 33–55 帧的收势。继续使用实际 Epic Rampage `Ability_GroundSmash_End` 的回撤轨迹，将肩肘腕作为连续的固定长度臂链回到既有待机姿态；肘平面、上臂与前臂的扭转辅助骨、肘腕体积支撑同步回位。末段躯干与其他三肢支撑由源 End 连续过渡到 Idle，取消 1.55 秒时突然更换源姿态的处理。

已在原 `/Game/Monsters/HundredEyedSlag/V1/Animations/A_HundredEyedSlag_AttackSlam_R` 路径导入并保存。未重新导入横扫或网格，未重做蒙皮、LOD、材质或物理资产；攻击总时长 1.8 秒、伤害窗口 0.84–1.00 秒及 F6 百目炉渣入口沿用现有配置，无需 C++ 构建。

制作与保存记录见 `RampageRecoverV9/authoring_receipt.json`、`installation_complete.json` 和工程 `Docs/Monsters/hundred-eyed-slag-rampage-recovery-v9-20261001.md`。未启动游戏、PIE、渲染或测试，新收势效果由用户测试。

'''
old = readme.read_text(encoding='utf-8-sig')
readme.write_text(re.sub(r'## 当前交付\n.*?(?=- References/V2/)', lambda _: current, old, count=1, flags=re.S), encoding='utf-8')
document = PROJECT / 'Docs/Monsters/hundred-eyed-slag-rampage-recovery-v9-20261001.md'
text = document.read_text(encoding='utf-8')
text = text.replace('当前：Blender 与单条下劈 FBX 已制作；资产保存以 `RampageRecoverV9/installation_complete.json` 为准。',
                    '当前：Blender 与单条下劈 FBX 已制作，并已导入、保存至原运行资产路径。保存方式为 `' + mode + '`；完成记录见 `RampageRecoverV9/installation_complete.json`。')
document.write_text(text, encoding='utf-8')
print('RAMPAGE_RECOVER_V9_SLAM_SAVED', flush=True)
