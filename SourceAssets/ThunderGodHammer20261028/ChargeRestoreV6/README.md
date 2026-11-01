# 雷神之锤蓄力恢复 V6，2026-10-29

用户要求蓄力阶段取消换握、恢复原来的举起手势，其余保持不变；随后明确选择允许接顺投掷起始的一小段。

- 蓄力整条恢复 `ThrowRefineV3` 的连续双手握柄抬举，不再使用 V4/V5 的分手松开、翻掌和绕行换握。
- 投掷仅在开始的 0–0.12 秒从原举起姿势接至 V5；0.12 秒之后直接保留 V5 的源姿态，包括分指放行、左手撤离、离手及收势。
- 蓄力和投掷的武器驱动轨迹、原生骨架、240 fps、0.24 秒离手时点和动作时长沿用原输入。
- 没有修改飞行旋转、抛物线提示、雷击/伤害、召回、接锤、镜头反馈及任何 C++ 文件。

制作源：`author_motion.py`、`ThunderHammer_ChargeRestoreV6_Editable.blend`；导出：`Export/`。

接入仍使用现有 `/Game/Weapons/ThunderGodHammer20261028/ThunderThrowV1/A_ThunderHammer_ThrowCharge` 与 `A_ThunderHammer_ThrowRelease`。`import_receipt.json` 记录实际保存结果，`BeforeImport-*` 保存本次写入前的两条动画。后续继续制作以 V6 为当前组合基线，不要重跑 V5 作者脚本把换握写回来。

按用户默认规则，本轮未运行游戏、测试或验收渲染。没有新增源码构建需求；动画保存与实机动作效果分别记录。
