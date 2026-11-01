# 雷神之锤特殊改造品质

用户将雷息配重、雷鸣符文和回响符文统一指定为特殊改造；本次确认“共鸣符文”指雷神专属回响符文，而非减少技能冷却的通用共鸣符文。

三个运行目录选项及其生成源均已写明 `tier: special`。本次补齐 `ColdSteelModification::Tier` 对雷神之锤 `rune` 槽 `lei_ming_rune`、`hui_xiang_rune` 的运行时判定；`pommel / lei_xi_pommel` 已有对应判定。改造卡片和相关品质标签统一使用特殊改造分支。

效果、数值、部件 ID、模型和图标沿用既有配置。贯雷、疾雷仍为传说改造。无需重新导入资产或迁移已有装备实例。

初始编辑器在运行，准备通过现有 MCP 批次执行热编译；接入前编辑器关闭，桥返回无可连接节点，未执行热编译。随后转为后台常规 `FPSGAMEEditor` 构建，回执位于 `SourceAssets/ThunderGodHammer20261028/SpecialTier20261030`。不启动编辑器，不运行游戏测试或验收。

后台构建已成功：7 个构建动作完成，包含改造栏、总览和基础 `UnrealEditor-FPSGAME.dll` 链接。未执行游戏测试。
