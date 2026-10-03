# 快速近战蓄势抬臂（2026-09-26）

按用户要求，近战武器快速近战的双手和剑柄蓄势最高点在现有动作上再抬高 **10 cm**。运行时对当前已采样的 V7 手模姿态施加此调整，默认柄和长柄沿用各自动画中的真实握距。

`RuneSwordMeshComponent.cpp` 在发布骨骼和挂点之前，以剑根、双手为同一持握组向上移动。原翻转中段开始渐入，抬臂顶点到出手前维持最高点；砸出段平滑消退，在原接触姿态（源时间 0.92 秒）完全归零。包络使用五次平滑曲线，并先于原入场混合计算，保留从当前姿态起手的衔接。

肩部小幅跟随抬升，双骨 IK 保持上臂与前臂长度。前臂旋转共同传递给上臂后再对齐肘方向，避免两段独立转向新增肘部轴向扭差；twist 辅助骨、手指跟随完整层级，手掌朝向和指型保留。剑根及其子部件只移动一次。

此调整仅用于快速近战技能，普通连击第四段配重锤动作沿用原姿态。0.20 秒基础蓄势、0.28 秒基础接触、0.96 秒基础完整周期、攻速倍率、recover、体力和伤害数值保持既有设置。

本轮修改运行时姿态代码，不替换网格、蒙皮或共享动画资产；无类布局变更。未运行测试、PIE、截图或渲染，实际观感由用户测试。

## 必要构建修正

编译共享模块时，另有两处 C++ 错误阻止整个模块生成：`VoxelBuildWorldCasting.cpp` 的局部 `Owner` 与 Actor 成员重名，已改为 `AssignedFurnace`；`HumanoidKnockdownComponent.cpp` 的条件表达式混用了裸指针和 `TObjectPtr`，已对 `FallClip` 显式调用 `.Get()`。两项仅修正编译写法，不改玩法行为，修改前文件保存在 `Saved/TaskBackups/QuickMeleeRaise20260926/`。

## 当前接入状态

**常规 Editor 构建已成功，抬臂调整已生成到 `Binaries/Win64/UnrealEditor-FPSGAME.dll`，下次打开 UE 即可加载。** `RuneSwordMeshComponent.cpp` 在首轮常规构建中编译为目标文件，随后增量构建完成整个模块链接。

此前两轮热编译分别因共享模块正在落盘的文件／声明以及上述 C++ 错误失败；补编译时 UBT 返回 `LiveCodingLimitError`：当时共享模块累计 **204 项**编译，超过 Live Coding 的 **100 项**上限，因此编译被取消。用户随后关闭 UE，改为常规构建。

最终通过 `Tools/Build/Build-Editor.ps1` 完成 `FPSGAMEEditor Win64 Development` 构建，共 24 项、21.82 秒，返回 `Result: Succeeded`。日志为 `Saved/BuildEditor/build-20260926-185053.log`，控制台记录为 `Saved/QuickMeleeRaise20260926/editor-build-console-03.log`。常规构建期间的 `SmeltingCasting.cpp` 局部变量重名已在共享源码中修复，本次未再修改该文件。

早前失败记录保留在 `Saved/QuickMeleeRaise20260926/compile-first-ubt.log`、`compile-second-ubt.log`、`compile-livecoding-limit.log` 和 `compile-result-final.txt`。本次没有打开 UE、运行游戏或测试，实际观感由用户测试。
