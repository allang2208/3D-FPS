# 手枪＋书 V4 姿势

用户已认可这版整体双臂方向；随后要求仅转左手，让书朝下。追加调整前的 `BeforeBookDown` 候选已归档至 `trash/animation-handoff-retired-20261021/SourceAssets/PistolBookPoseV4_20261020/BeforeBookDown`。最后一轮改变 `left_hand_roll_degrees`，肩、肘、腕位置与右手布局不变。当前 V4 作者源及 Blend 仍为 V5 拇指制作输入，保留原位；运行时未瞄准恢复原持书，仅 ADS 使用新姿势。

- `pose_controls.json`：可编辑的厘米制作者控制，X 前／Y 右／Z 上。
- `read_authoring_source.py`：只读既有 M1911 Contact 场景，提取原生绑定、机械骨和实际枪体表面。
- `author_poses.py`：原生 V9 左右臂、固定骨长、双肘分向、100%／50% 前臂扭转，保持现有指形与握点；产生 `candidate.json` 和表面数据。
- `render_candidate.py`：后台 Blender 输出固定玩家眼点的 `hip.png`、`aim.png` 和单独斜侧的 `aim-detail.png`。
- `PistolBook_V4_StaticCandidate.blend`：两帧静态姿势、实际网格、贴图和骨点参考。Shape Key 仅保存两个终点，不能当作完整动画过渡播放。

运行时接入见 `Source/FPSGAME/Weapons/Spellbook/SpellbookPistolSupport.cpp`、`SpellbookPistolSupportTuning.h`、`SpellbookPistolArmSolver.h`；必要构建记录在 `Saved/PistolBookPoseV4_20261020`。C++ 过渡使用秒制分段抬升／靠近路径，书始终挂在最终手骨上。

预览属于本轮授权的作者模型展示，使用 Blender 灯光与材质表达；没有启动 UE 或游戏。动态、衣物和游戏画面的自然度由用户体验，不能由静态预览或编译结果宣称通过。
