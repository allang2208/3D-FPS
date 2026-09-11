# 枪口配件发射起点检查（2026-09-11）

当前 M4 已有按配件前端包围盒出口求世界坐标的 GetEffectiveMuzzleLocation，飞行弹道与枪口火光、烟雾共用此入口。此次修正 FireShot 的取样顺序：在重启射击动画前同时读取瞄具方向和有效枪口坐标，避免发射方向与起点来自不同姿态时机。没有修改配件安装变换、枪管长度、弹速或后坐力。

新增 LastLaunchStart 供审计读取真正传入弹道组件的发射坐标。新进程加载 UnrealEditor-FPSGAME-9111534.dll，通过 61 项检查、0 失败。覆盖三种配件出口平面、实际发射坐标、拆卸恢复、既有 ADS 连射着弹及命中提示。

相对原枪口沿枪管向前的位移：消音器 13.7637 cm，制退器 1.9637 cm，钛合金制退器 2.4137 cm。实际发射位置与开火前配件出口一致（0.001 cm 容差）。本轮为 M4 运行检查，未运行 AKM 配件回归。

日志 Saved/BallisticPresentationAudit-20260911121929.log；四张实际开火截图 Saved/BallisticPresentationAudit/07-muzzle-{true,brake,titanium_brake,false}.png。消音器截图已查看，火光出现在配件前端。原本已存在出口同步逻辑，不能将本次取样顺序修正声称为已确认的所有视觉偏移根因；已打开的旧编辑器需重启以加载当前模块。
