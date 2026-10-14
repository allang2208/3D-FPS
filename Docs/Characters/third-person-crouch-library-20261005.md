# 第三人称蹲姿与蹲移动：复用 GASP 动画

## 来源与落盘

- 本地库：`D:/FPS3D/游戏动画示例/Content/Characters/UEFN_Mannequin/Animations`。
- 来源：Epic Game Animation Sample，既有 Fab 库获取记录见 `Docs/gasp-traversal-20260910.md`；不新增外部下载或公开发布二进制资源。
- 原动作骨架：UEFN Mannequin；重定向目标：当前 `SK_Jason_Base`。
- 保存目录：`/Game/Characters/JasonPlayer20261003/CrouchGASP20261005`，独立的 IK Rig、Retargeter 和 13 段动画。
- `SourceAssets/ThirdPersonCrouch20261005/donors.json` 记录复制来源与散列；`assets-saved.json` 记录已保存资产、脚步标记与运行时映射。
- 当前编辑器处于游玩状态，编辑器内保存被拒绝。随后改用独立新目录，在 `UnrealEditor-Cmd -run=pythonscript -nullrhi` 后台完成重定向和保存，未结束现有游玩。

## 已接入与候选

`Content/ColdSteelData/player_body.json` 新增以下 9 个键，原有站立、武器、跳跃和动作库保留：

| 运行时键 | GASP 原动作 |
| --- | --- |
| Crouch.Idle | M_Neutral_Crouch_Idle_Loop |
| Crouch.Walk.Fwd | M_Neutral_Crouch_Loop_F |
| Crouch.Walk.Fwd_Right | M_Neutral_Crouch_Loop_FR |
| Crouch.Walk.Right | M_Neutral_Crouch_Loop_RR |
| Crouch.Walk.Bwd_Right | M_Neutral_Crouch_Loop_BR |
| Crouch.Walk.Bwd | M_Neutral_Crouch_Loop_B |
| Crouch.Walk.Bwd_Left | M_Neutral_Crouch_Loop_BL |
| Crouch.Walk.Left | M_Neutral_Crouch_Loop_LL |
| Crouch.Walk.Fwd_Left | M_Neutral_Crouch_Loop_FL |

另外保存了 `RL`、`LR` 两种侧移变体和 `Stand_to_Crouch`、`Crouch_to_Stand` 两段过渡；这 4 段仅为候选，当前状态机未播放。站蹲切换继续使用既有平滑权重。

新增动画目录已加入 `DefaultGame.ini` 的 `DirectoriesToAlwaysCook`。

## 动作处理调整

原代码把站立走路的骨盆下移约 40 cm、缩短步幅，同时把踝/趾转回站姿，并用固定前方膝盖目标重新求解双腿。这会覆盖原动作的膝盖弯曲面，移动和转向时几种校正互相影响。

普通下蹲现由真实蹲姿/蹲行动画驱动骨盆和完整双腿，不再叠加这套站姿改蹲姿的处理。滑铲、闪避、翻越仍沿用原特殊动作逻辑。持枪时保留原武器上半身动作，地形适配继续使用动作本身的膝盖弯曲面和可达距离约束。

蹲行每段包含 4 个步态周期，依据源动作脚踝停驻时刻补入 L/R 接触标记；八方向共享步态相位，播放速度使用重定向片段的根位移速度。蹲姿保留源动画脚跟抬起和脚踝弯曲，不再强行套用站姿脚掌压平修正。

制作脚本依次为 `prepare_crouch_sources.py`、`read_crouch_sources.py`、`retarget_crouch_jason.py`、`publish_crouch_jason.py`，位于 `Tools/PlayerBody`。重定向脚本创建新资产，不能对同名已存资产直接重复创建；发布脚本只更新 crouch 映射。

## 首轮交付状态（20:45）

- 后台重定向 commandlet 完成，13 段资产已保存；9 段动作已写入配置并接入 C++ 动画图。
- 原编辑器仍在运行，未执行热补丁、关闭或重启；Editor 常规模块需要关闭现有 UE 后构建。
- `FPSGAME Win64 Development` 构建成功（132/132 步骤，退出码 0），已生成 `Binaries/Win64/FPSGAME.exe`；记录见 `SourceAssets/ThirdPersonCrouch20261005/build-game.log`。此产物不替代仍运行中的 Editor 模块。
- 未运行游戏、截图或视觉验收，由用户测试最终蹲姿、八方向移动和转向表现。

## 同日反馈：移动时关节仍扭曲

用户反馈后只读检查当前会话与已保存片段：运行中的 UE 进程 41012 仅加载基础 `UnrealEditor-FPSGAME.dll`（20:11），没有加载后续补丁；上一轮蹲行动画图源码在 20:31 修改，20:45 完成的是 `FPSGAME.exe`。因此当前编辑器尚未执行上一轮蹲行替换。游戏目标构建不能代替 Editor 目标构建。

`Tools/PlayerBody/inspect_crouch_joints.py` 读取了 9 段已保存片段的 44 个腿部骨骼及当前角色姿态，输出为 `SourceAssets/ThirdPersonCrouch20261005/joint-diagnosis.json`。按各片段 33 个采样点，与原动作同时间对齐，膝盖弯曲角差最大约 2.2 度；这是骨骼数据排查，不代表蒙皮或游戏画面已验收。

同时修正普通转身校正的固定膝盖目标：捕获源动作的髋—膝—踝平面，与骨盆一起旋转，再根据实际足部目标求解。避免蹲姿转向和原地转身向移动淡出期间，再次被固定前方目标覆盖。近战、击退和眩晕的专用动作目标保留。

用户随后保存并关闭 UE，授权继续编译。Game 增量构建成功（41/41），记录为 `SourceAssets/ThirdPersonCrouch20261005/build-turn-knee-game.log`；常规 Editor 构建也已成功（168/168，退出码 0），`UnrealEditor-FPSGAME.dll` 和依赖模块已更新，记录为 `Saved/BuildEditor/build-20261005-213042.log`。

当前交付包含两轮蹲姿修正的正式 Editor 模块，下一次打开 UE 即可加载。构建后保持 UE 关闭，未启动游戏或执行视觉验收。
