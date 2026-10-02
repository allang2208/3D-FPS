"""Record actual saved assets/builds without running tests or changing gameplay."""
from pathlib import Path
import json

HERE = Path(__file__).resolve().parent
ACTIVE = HERE.parent
PROJECT = ACTIVE.parents[1]

def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))

def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

saved = read(HERE / "Wrist/installed.json")
manifest = read(HERE / "Wrist/Authored/authoring.json")
if len(saved) != len(manifest["patches"]):
    raise RuntimeError("Keep pending integration state; not every authored mesh has been saved")
thumb = read(HERE / "Thumb/thumb-rotations.json")
editable = read(ACTIVE / "editable-source.json")
receipt = dict(
    revision=2026100209, date="2026-10-02", status="authored_assets_saved_and_normal_builds_complete",
    source_table="Source/FPSGAME/Movement/DoorPushAuthored20261002.h",
    pose_source="SourceAssets/DoorPush20261002/full-pose.json",
    editable_source="SourceAssets/DoorPush20261002/DoorPush_LeftFist_V7_20261002.blend",
    editable_take=editable["take"],
    wrist_editable_source="Wrist/Editable/M16_BareArmsV7WristWeightPartition20261002.blend",
    thumb_local_bones=thumb["bone_names"],
    thumb_native_joint_parameters_degrees=thumb["native_joint_parameters_degrees"],
    previous_thumb_axis_roll_degrees=thumb["previous_cmc_axis_roll_degrees"],
    mesh_packages_saved=len(saved),
    edited_skin_weight_vertices=sum(value["edited_weight_vertex_count"] for value in saved.values()),
    geometry_positions_changed=False, wrist_or_helper_rotations_changed=False,
    bone_lengths_scales_changed=False, shared_skeleton_changed=False,
    existing_animation_assets_changed=False, audio_changed=False,
    hold_seconds=.3, contact_seconds=.36, duration_seconds=.557,
    game_build="normal_build_succeeded", editor_build="normal_build_succeeded",
    logs_directory="Saved/DoorPushGuardWristThumbV8_20261002",
    background_asset_commandlet=True, interactive_editor_started=False,
    game_tested=False, rendered=False, audio_auditioned=False,
)
write(HERE / "integration-completion.json", receipt)
integration = read(ACTIVE / "integration-completion.json")
integration.update(revision=2026100209,
    editable_action=editable["take"],
    fist_reuse="Existing four-finger fist and complete neutral wrist/arm; revised thumb CMC opposition and MP/IP curl",
    game_build="normal_guard_wrist_thumb_v8_build_succeeded",
    editor_build="normal_guard_wrist_thumb_v8_build_succeeded",
    current_work="guard_wrist_thumb_v8_skin_partition_and_normal_builds_complete",
    guard_wrist_thumb_integration="SourceAssets/DoorPush20261002/GuardWristThumbV8_20261002/integration-completion.json",
    editor_build_note="V8 local thumb motion and proximal M16 thumb weights saved; normal Game/Editor builds complete. No interactive editor restarted or runtime test.",
    tested=False, rendered=False,
)
write(ACTIVE / "integration-completion.json", integration)
source = read(ACTIVE / "authored-source-completion.json")
source.update(status="guard_thumb_v8_and_editable_blend_saved",
    backup="SourceAssets/DoorPush20261002/GuardWristThumbV8_20261002/BeforeAuthored",
    thumb_patch="SourceAssets/DoorPush20261002/GuardWristThumbV8_20261002/Thumb/thumb-rotations.json",
    game_build="normal_build_succeeded", editor_build="normal_build_succeeded")
write(ACTIVE / "authored-source-completion.json", source)
doc = PROJECT / "Docs/Gameplay/sprint-door-push-20261002.md"
text = doc.read_text(encoding="utf-8-sig").rstrip()
text += "\n\n## 护拳腕掌与拇指 V8（当前，2026-10-02）\n\n"
text += "保留现有完整腕臂和中立腕骨，只调整护拳三根拇指局部旋转：减小根部过量轴向拧转，沿原生关节屈曲使指腹贴靠食指／中指外侧。M16 的 9 个网格同步收回腕侧过量拇指权重，平滑过渡到真实拇指根部；不改几何、UV、材质、骨长、缩放、公共 Skeleton 或其他动作。保留 0.30 s 停顿、轻摆、0.36 s 开门反馈和本轮用户 MP3。\n\n"
text += "腕掌权重资产已通过后台 commandlet 实际保存，完整动作表、Blend 源及正常 Game／Editor 构建已落盘。制作与接入记录位于 `SourceAssets/DoorPush20261002/GuardWristThumbV8_20261002/`。未运行游戏或验收渲染，手型由用户测试。\n"
doc.write_text(text, encoding="utf-8")
print("Guard wrist/thumb V8 saved-asset and build records completed.")
