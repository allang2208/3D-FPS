# 缚群十足移动动画 V2

> 历史阶段记录。2026-10-08 用户否定整体衣物并暂停；V18、V19 均未获认可。当前状态、最新参数和已归档证据的取回位置以[暂停与发布记录](bound-congregate-paused-publication-20261008.md)为准。

## 动作制作

用户要求制作移动动画。沿用原 Meshy 主体、56 骨骼绑定、现有衣物与已修好的材质，新增三段原地循环：`A_BoundCongregate_WalkV2`、`A_BoundCongregate_TurnLeftV2`、`A_BoundCongregate_TurnRightV2`。

- 每段 1.6 秒，30 fps，包含第 1～49 帧的循环端点。所有主身和触手曲线按同一个周期构造。
- 前进动画标定速度 50 cm/s；现有游戏移动速度 60 cm/s 对应 1.2 倍播放速度。动画不驱动角色位移，仍由 CharacterMovement 和现有导航负责。
- 同侧脚相位每条错开 0.2 周期，右侧相对左侧错开 0.5 周期；十足形成从后往前的支撑波。支撑段占 72%，回收段占 28%。
- 单足有效步幅 57.6 cm；按捐献肢体分别设置 9～13.5 cm 的抬脚高度，脚掌／手掌在回收时翻抬，略向外绕开，落地后恢复支撑朝向。
- 身体下压 5.5 cm 建立屈曲余量，叠加受力起伏与轻微左右重心转移；前后肉团、巨口、悬臂、嗅探部位和触手使用不同延迟。
- 左右原地转身采用弧形落点，标定角速度 14°/s。掌端朝向与弧形落点同步，避免仅挪脚踝而手掌持续扭转。

两段 IK 按各条肢体的原始关节平面求解，最大伸展限制为原总长的 97.5%。保留每只手脚自己的参考高度、长度和弯曲方向。摆动纵向轨迹在两端延续支撑段速度，避免抬脚和落脚瞬间突然反向。制作脚本只导出骨骼动画，不重导主体和衣物网格。

## 接入改动

`BoundCongregateAnimInstance` 使用同源生成的十足相位和支撑时长；按实际线速度／角速度选择动作和播放速率。前进与转身切换延续步态相位，并在过渡期间继续采样上一循环；起停阈值采用小幅迟滞，减少导航微小修正造成的反复切片。复制的 Crawl/Idle 状态不再强制先重置到 Idle。

原缚群使用未设置 Behavior Tree 的原生 MonsterAIController。接入脚本将它改为现有 `/Game/Monsters/AI/BP_MonsterAIController`，沿用已配置的共享树；不改共享 AI 树、攻击数值、刷怪池或其他怪物。

## 交付路径和重建

- 参数：`Tools/BoundCongregate/locomotion_v2.json`。
- 制作：Blender 后台执行 `Tools/BoundCongregate/author_locomotion_v2.py`。
- 源文件和 FBX：`SourceAssets/BoundCongregateMeshy20261006/LocomotionV2/BoundCongregate_LocomotionV2.blend` 及该目录三个动画 FBX。
- 同源脚锁参数：`Source/FPSGAME/Monsters/BoundCongregateGait.h`，由动作制作脚本生成。
- 编译与导入：编辑器关闭后执行 `Tools/BoundCongregate/finish_locomotion_v2.ps1`。
- 仅导入：`import_locomotion_v2.py`，在当前编辑器未运行 PIE 时经既有桥，或在编辑器关闭后的 commandlet 中执行。只写新动画、原骨架的动画导入数据和缚群蓝图。
- 完整模型重导会在 V2 文件存在时恢复这些新动画引用及共享控制器，保留旧动作作为制作历史。

## 当前状态

2026-10-07 用户保存并关闭 UE 后，已完成 FPSGAMEEditor 和 FPSGAME 两个正常目标构建，均为 `Result: Succeeded`。随后通过无界面 commandlet 实际导入并保存三段 V2 动画、原骨架及 `BP_BoundCongregate`，后台流程退出码为 0，`LocomotionV2/ue_delivery.json` 为 `complete: true`。

蓝图移动动画标定速度已设为 50 cm/s，现有游戏移速保持 60 cm/s；控制器引用为共享 `BP_MonsterAIController`，使用 `BT_Monster`。F6 → 缚群继续使用同一个蓝图入口。未启动或重启交互编辑器。

按用户规则，本轮未进行播放检查、游戏测试、预览渲染或性能验收。
