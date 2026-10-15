# 战锤上挑 V6：蓄势握柄倾斜与右臂收势避让

用户认可 V5 的整体右下撤出位移，要求蓄势握柄按画面逆时针转 30°，双手重新匹配，并处理出手后右臂肩侧开口进入画面的问题。

## 动作修改

- 保留 V5 共同位移：右移 15 cm、前送 2 cm、下沉 13 cm，仍在源时间 0.18–1.00 秒进行；左手保持较高的后握点。
- 以左手握点为支点旋转整组握持关系。根据透视投影求解画面中的逆时针 30°；对应本姿态的三维视线轴转角约为 -22.734°。直接在该偏心握点上转三维 30°会使屏幕倾斜过量，因此没有混淆两种角度。
- 双手保持原生握柄接触，左右臂均基于固定待机解剖参考求解肘平面及前臂轴向旋转。沿现有蒙皮站点分配旋转，保持骨段长度和原握指形态。
- V5 在源时间 1.05 秒后直接使用 V1 的旧姿态。该段右肩向前升起，带出肩口。本版继续处理右臂支撑，稳定锁骨参考；高位收势相对旧版向身体回收 8 cm、下移 12 cm，平滑恢复待机。正前方出手交接点保持源时间 1.05 秒。
- 使用作者源中 V7 右肩 61 顶点开口环及实际骨骼权重进行姿态适配。肩口随锁骨和上臂辅助骨共同运动；没有缩放手臂、改双面材质或隐藏网格。
- 更新实际烘焙锤头轨迹 `WarhammerUppercutArc.h`。上挑的快速播放时钟、音效时机、伤害与距离配置沿用现有版本。

## 制作与接入

- 源目录：`SourceAssets/SteelWarhammer20261014/UppercutTiltClearanceV6/`。
- Blender：`Warhammer_Uppercut_TiltClearance_Editable.blend`。
- FBX：`Export/A_Warhammer_Uppercut.fbx`。
- 正式动画：`/Game/Weapons/SteelWarhammer20261014/UppercutV1/A_Warhammer_Uppercut`。
- 修订：`TiltClearanceV6_20261015`。修改前动画、V5 脚本和轨迹保留在 `Before/`。
- 已通过无界面 commandlet 导入并保存正式动画，`import_receipt.json` 为 `complete=true`；commandlet 正常退出，exit 0。
- 最终 `FPSGAMEEditor Win64 Development` 构建返回 exit 0、`Result: Succeeded`，UBT 确认目标已是最新（6.39 秒）。制作、导入和轨迹重导出入口已指向 V6，完成状态记录于 `delivery.json`。

仅完成后台制作、导入保存与必要构建；未运行游戏、预览渲染或测试。肩口源几何适配不等于用户当前换装、视角和运行时画面验收，最终效果由用户体验。

> 后续用户反馈上挑出手后的右肘／前臂仍扭曲；已保留本版武器与左手轨迹，继续制作至 [右臂解剖支撑 V7](steel-warhammer-uppercut-right-anatomy-v7-20261015.md)。本版源 Blend 和作者脚本保留为 V7 输入，当前导入入口指向 V7。
