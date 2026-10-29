# 单刀旋风第一人称方向修正（2026-10-26）

用户要求保留第三人称模型和动作，仅反转单手持剑时第一人称的旋转方向。本次针对尼泊尔弯刀的非双刀状态。

现有 `KukriWhirlwindRhythm` 驱动控制器及世界身体旋转 +720°。保留这条链路、第三人称动画及其配置，由 `GetWhirlwindFirstPersonYawOffset()` 按同一技能相位向第一人称相机追加 −2θ，使视角及挂接手臂的世界转角变为 −θ。

修正叠加在 `AFPSGAMECharacter::UpdateCamera()` 的表现朝向上，绕世界竖直轴旋转，保留俯仰角；不经过镜头晃动强度缩放，避免关闭晃动或调整强度后方向失效。蓄势、命中停顿、减速和收势沿用原时钟，完整两圈后的修正归零。单刀镜头侧倾和接触阻力随新的观察方向调整。

双刀状态及 F6 第三人称观察不应用反向修正。控制器、Pawn 朝向、伤害扫掠、服务端判定、第三人称片段和 `player_body.json` 均未修改。没有重导入动画资产。

本次源码涉及 `KukriWeaponComponent.h`、`KukriWhirlwind.cpp` 和 `FPSGAMECharacter.cpp`。编译操作通过已经运行的编辑器及 `Tools/AssetPipeline/mcp_call_codex.ps1` 的互斥通道提交，记录位于 `Saved/KukriFirstPersonWhirlwindDirection20261026/`。

2026-10-26 21:05，`compile-result.json` 返回 `Result: Success`、`Live coding succeeded`，修改已通过热编译应用于现有编辑器。源码已保存；没有关闭或重启编辑器，基础 Editor DLL 尚未进行关闭编辑器后的常规构建，也没有重新打包。按用户规则不启动游戏，不追加测试、截图或预览；动作体验由用户测试。
