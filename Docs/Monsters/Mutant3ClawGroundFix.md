# 突变体-3：爪形与飞扑接地修订（2026-09-23）

当前版本与恢复顺序见 [突变体发布入口](Mutant3FeralPublication20260923.md)。本文保留阶段记录；其中 before/baseline 快照及已退役独立手臂求解已按归档清单移至 trash。

当前修订使用 `KhaimeraV2` 资产，解决用户反馈的手指张开和飞扑落地浮空。原 V1、原 Meshy 模型及其 Skeleton 保留。

后续的[动作过渡修订](Mutant3Transitions.md)将落地全身硬切改为“下身保持贴地、上身短暂混合”，并修订跑步、连击和受击衔接；模型与本页所述 V2 动画资产继续使用。

用户随后否定本页的轻弯手型，现按[用户照片的张开爪形](Mutant3OpenClawReference.md)重新制作双手，并在同一 V2 资产路径更新。本页手指角度仅保留为上一版制作记录。

## 手部检查与修改

原 Blender 蒙皮有 34 根骨，导入 UE 后另含 `Mutant3Root` 容器根。手部有 `Left/RightHand` 和整段 `Hand_End` 权重，没有独立五指骨链；原长指权重分布不均，直接旋转 `Hand_End` 无法一致地形成爪形。

此次为每只手的五指各补三节骨，共 30 根新增手指骨，并按实际手指几何分配局部权重。原有身体骨层级保持，手掌/前臂衔接保留，修改了 678 个手部顶点；手部之外的顶点坐标变化为零。Blender 应用中性姿态后的原骨矩阵最大数值误差为约 `1.4e-6`，未宣称浮点数逐位相同。

中性爪形保留指间张开：食指/中指/无名指三节分别约 8°/16°/10°，小指 10°/18°/10°，拇指 8°/10°/4°。弯曲朝掌心，不做合拢握拳；将这套轻微内弯作为新手指的中性姿态，因此原本没有手指动画轨道的跑步、攻击、受击和死亡也可保持该手型。

新模型：`/Game/Monsters/Mutant3Meshy/KhaimeraV2/SK_Mutant3_Claw`。

新 Skeleton 单独保存，允许使用原 Skeleton 的兼容动画；原死亡/受击动画继续使用。材质槽和 PhysicsAsset 沿用原模型。未修改原 Skeleton，不需要让其他旧角色一起更换绑定。

## 浮空原因与修复

1. V1 制作脚本仅在骨骼存在父骨时传递 Hips 平移，但 Blender 的 `Hips` 正是顶层骨。UE 的 `Mutant3Root` 来自导出的 Armature 对象，不能据此把 Blender Hips 当成固定容器根。这使骨盆保持在约 96.3 cm，屈膝时脚底被抬高。
2. V1 仅使用 `max(0, correction)` 抬起穿地模型，没有向下消除悬空，也未以实际脚底作为支撑点。
3. UE 导出的动画 FBX 的静止骨架与动画世界平移在 Blender 中呈现不同的单位尺度。修订时使用已经换算后的动画世界平移和目标真实绑定位置，避免错误的绑定差值再加入约一米高度。

修复后，骨盆随动作屈伸；待机、爪击、蓄力和落地按脚底蒙皮的最低支撑点做有符号的上下修正。腾空阶段保留腿部蜷收，由 CharacterMovement 完成飞行位移；首尾与地面动作衔接。

角色移动更新后，只对模型补偿 UE 胶囊和支撑地面之间的原生间隙，胶囊继续由 CharacterMovement 处理碰撞。补偿采用增量，保留原台阶视觉平滑；腾空撤销此补偿，尸体不再跟随胶囊调整。实际 `Landed()` 到达时立即采用贴地的落地下身姿势；后续过渡修订允许上身缓冲，不再将离地的腾空腿部快照混入地面支撑。

## 本次针对性排查结果

| 项目 | V1 | V2 |
|---|---:|---:|
| 待机脚底最低点高度 | 10.42–11.20 cm | 约 0.30 cm |
| 蓄力脚底最低点高度 | 9.73–46.74 cm | 约 0.30 cm |
| 落地脚底最低点高度 | 11.15–53.87 cm | 约 0.30 cm |

上表来自最终 Blender 蒙皮逐帧采样，坐标为角色局部地面，不是游戏运行截图。UE 导入后的动画采样也保留了骨盆平移：蓄力骨盆约 49.82–86.83 cm、落地骨盆约 42.69–85.40 cm，不再锁定原来的高度。这里只排查用户指定的手部权重和落地问题，未启动游戏或进行其他玩法回归。

## 可编辑源与正式接入

作者目录：`SourceAssets/Mutant3Khaimera20260923/hand_ground_fix/`。

- `author_claw_skin.py`、`Mutant3_Claw_Source.blend`、`SK_Mutant3_Claw.fbx`：手指骨、权重和中性爪形。
- `author_fixed.py`、`Mutant3_Khaimera_ClawGrounded.blend`、`final/`：九段修订动画。
- `import_fixed.py`：后台导入新模型、新 Skeleton 和动画；设置旧死亡/受击动画的骨架兼容关系。
- `source_inspection.json`、`fixed_source_inspection.json`、`claw_skin.json`：原始与修订后的手部/接地排查记录。
- `grounding_bake.json`、`import_delivery.json`：烘焙修正量及 UE 导入采样。

模型、新 Skeleton 和九个动画已保存到正式 `Content/Monsters/Mutant3Meshy/KhaimeraV2`。`Mutant3.cpp` 构造默认引用已切换到 V2；`Mutant3Feral.cpp` 保留原跳劈式飞扑时序及伤害，只修改接地姿态交接。

恢复正确骨盆位移后，播放速度参考随重新烘焙的支撑脚轨迹更新为普通跑 343.7 cm/s、高速跑 642.4 cm/s；角色追击速度仍为 560 cm/s。

构建状态：`FPSGAME Win64 Development` 与 `FPSGAMEEditor Win64 Development` 均已成功，Game 可执行文件与 Editor 模块已落盘。日志位于作者目录 `build-game.log`、`build-editor.log`。未打开交互式 UE 编辑器，未启动游戏；游戏内表现交由用户通过原 F6“怪物生成 → 突变体-3”入口重新生成后确认。

Game 构建额外暴露 `FPSWeatherManager.h` 的 `TWeakFieldPtr<FProperty>` 不完整类型错误，已仅补入 `UObject/WeakFieldPtr.h` 编译依赖，未修改天气逻辑。
