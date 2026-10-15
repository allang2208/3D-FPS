# 暴风雪：法杖限定的高级魔法

按用户 2026-10-14 要求，暴风雪归为高级寒冰魔法，必须当前装备法杖才能凝聚和释放。`skills.json:blizzard.requiresStaff` 与原生默认值均设为 true，技能介绍、卡片分类和详细操作说明同步；旧“无需法杖”口径由本条替代。

- 无法杖时，快捷槽变暗并提示“需要法杖”，按键拒绝施法，不进入排队或支付魔法。
- 排队、凝聚、持有云团、释放动作到接触点均按当前装备执行限制；尚未发出权威释放请求时切走法杖，沿用 `CancelPending` 清理云／预览、退还实际付款并清除预留冷却。
- 联机服务端现有 `BeginBlizzardCast` 与 `NetCommitZone` 使用服务端快照和装备校验，随配置启用限制。已发出的释放请求仍由原回执决定提交／退款，避免客户端重复退蓝。
- 已成功释放的区域继续原有生命周期。保留伤害、消耗、冷却、等级成长、修炼、立体范围、遮挡与云雪特效。

修改范围：`Content/ColdSteelData/skills.json`，`BlizzardTypes.h`，`ColdSteelSkillRules.cpp`，`FPSBlizzardComponent.cpp`，`ColdSteelQuickSlot.cpp`，`ColdSteelSkillPage.cpp`，技能与参考文档。进行必要后台构建，不自动打开 UE，不运行游戏、联机或界面测试。

## 本轮构建

- Game Development 完整构建成功：`Saved/BuildEditor/blizzard-staff-game-20261014.log`，160 个构建动作，`Result: Succeeded`；产物为 `Binaries/Win64/FPSGAME.exe`。
- 项目编辑器和另一个后台 commandlet 正在运行，保留其现场，未覆盖被占用的 Editor DLL；Editor 目标仍需关闭占用后完成常规构建，不能把 Game 构建视为当前编辑器已加载改动。
- 未运行游戏、界面或主客机测试，交由用户测试。
