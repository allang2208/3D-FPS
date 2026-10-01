# 百目炉渣：真实长臂动作源接入待办

2026-10-01。用户明确判定 ApeRecoveryV7 的大右手打击力度、抬臂幅度和关节仍不合格，要求取得真实参照后调整。V7 已保存不代表质量合格；本轮不从它继续创作一套自拟攻击。

后续状态：用户已下载并导入 Rampage 到主工程。已取得真实动画及蒙皮，并完成 RampageV8 的适配、导出和无界面导入保存；详情见 [RampageV8 制作记录](hundred-eyed-slag-rampage-v8-20261001.md)。以下为取得源文件之前的阶段记录，不代表当前仍缺文件。

## 本轮实际完成

- 查阅 [Epic Paragon: Rampage 官方产品页](https://www.fab.com/listings/0807cf74-08fd-4a33-8c8d-f33c9439fb1f)：免费 UE 包，含角色、动画和动画蓝图；作为待取得的长臂怪物动作供体候选。
- 本机 `D:/FPS3D/VaultCache/FabLibrary/_______-0807cf74` 为空。Fab 数据库只存在下载元数据，`path` 为空、`downloaded_at` 为 0；不能当成模型或动画已下载。
- 新建独立内容工程 `D:/FPS3D/RampageReference/RampageReference.uproject`，使用已有 Launcher 工程搜索根目录，未启动编辑器。
- 保存后台动画源导出脚本 `SourceAssets/HundredEyedSlagMeshy20260930/RampageReferenceIntake/export_source.py`。尚未执行；没有生成导出、重定向或游戏替换资产。

## 阻塞及后续

[Fab 官方下载说明](https://dev.epicgames.com/documentation/fab/exporting-assets-from-fab-in-launcher?lang=en-US)要求 UE 内容通过 Launcher 的“添加到工程”等入口取得。当前会话没有可调用的 Launcher 控制运行时，无法完成已登录 Launcher 中的操作。需用户将免费 Rampage 加入上述参考工程，之后继续后台制作。

取得源文件后先读取实际完整关节链，选择挥击和抬臂重击，而非只提取手掌方向或套用通用关键帧。目标是保留源动作的蓄力、身体移重、肩肘协调、落击与收势；大右臂关节轴、权重过渡与必要的局部拓扑根据实际供体和目标结构适配。攻击时长和伤害窗口随选定动作同步修改，不预先硬套 V7 时序。

本轮没有改动运行网格、蒙皮、动画或游戏数值。实际修复尚未完成；没有测试、渲染或验收。
