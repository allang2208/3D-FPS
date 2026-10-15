# 陨星熔核：震荡扩散

> 2026-10-15 整理：本文为制作阶段记录；Before 快照已带散列移入 trash。最终发布状态和恢复入口见[整理说明](../../../../Docs/Publication/WarhammerMods20261015/README.md)。

2026-10-15，按用户要求增加“重击／冲刺攻击冲击波范围 +50%”。以线性半径乘以 1.5 实现：当前基础半径 300 cm，安装陨星熔核后为 450 cm。

正式文案：**震荡扩散｜重击与冲刺攻击的冲击波范围增加50%。** 显示在现有改造详情的特效说明及已安装改造的物品浮窗中；原有物理伤害 +40%、攻击速度 −15%、攻击体力消耗 +25%、韧性伤害 +40% 保持原值。

## 接入

- `BuildV1/catalog.py` 与 `Content/ColdSteelData/warhammer-gunsmith.json` 的 `meteor_core` 使用 `shockwave_radius_mult: 1.5`；特效文案从同一倍率生成。
- `WarhammerCombat::ShockwaveRadius` 从当前已加载的专属目录及实际已安装锤头读取倍率。普通／共享锤头回到基础半径。数值只在工具属性刷新、出手准备时读取，不新增逐帧读文件或改变近战通用距离倍率。
- `ProductionToolComponent::ApplyToolStats` 将计算结果写入现有 `BluntWaveRadius`。本地主机和远端玩家的服务端攻击提交均沿用该属性入口，充满重击与冲刺砸地在触地时共用 `BeginBluntShockwave`。
- 权威冲击波以该半径判定目标，并通过已有复制字段 `AWarhammerShockwave::MaxRadius` 同步客户端；可见波纹、尘土扩散和地裂贴花继续消费同一半径。
- 普攻扇形距离、旋风／升龙范围与攻击伤害系数未接入该倍率。未找到有效地面时沿用现有直接接触处理。

这次修改现有函数并新增局部查询函数，没有改变反射布局、存档结构或网络参数。效果目录仍按原有游戏实例加载流程读取，已运行的实例在重新载入目录后读取新配置。

`apply_effect.py` 只更新本选项的冲击波倍率和特效文案；`Before/` 保存本轮改动前副本，`effect_receipt.json` 记录配置写入。

Game Development 构建成功：7 个动作、65.04 秒，见 `game-build-receipt.json`。现有编辑器经共享批次桥执行 Live Coding，返回 `Result: Success` 与 `Live coding succeeded`，见 `livecoding-result.txt`；只更新当前编辑器会话，基础 Editor DLL 仍需在编辑器关闭后运行 `build.ps1 -Target FPSGAMEEditor`。本轮没有关闭、重启或新开编辑器，没有运行游戏、联机或视觉测试。当前游戏实例需重新加载目录后读取新增倍率与文案。

后续完成：2026-10-15 的 双棱尖头锤 BalanceV2 常规 Editor 构建（本机文件 `SourceAssets/CommonHammerSpecialHeads20261014/PointedHammer/BalanceV2/editor-build-receipt.json`，不随 Git 发布） 已包含本改动并更新基础 DLL；上述 Editor 构建待办已补齐。原始热编译回执作为历史保留。
