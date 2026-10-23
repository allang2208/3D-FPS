# 符文战锤制作源

当前运行配方：`Content/ColdSteelData/runebound-warhammer-{gunsmith,modules}.json`。`ModulesV1` 保留五栏模块的真实接口和作者基表；原装外观、Swift / Destruction 符文、StarOath / FinalToll 两款互斥锤头分别维护制作源。当前能量条为 `HudSymmetricCapsV3`。

保留 `Original` 用户提供 GLB、根目录及各模型可编辑 Blend、导出模型、PBR、正式图标母图和完整动作输入。它们是本机恢复资料，当前没有核准原资产再分发许可，不随公开源码提交。

V3 HUD 仍读取 `PassiveV1` 的 V2 HLSL、`HudMotesV2` 安装脚本及苍龙 HudV10 输入；这些旧版属于有效依赖。星誓模型脚本也是镇魂钟制作辅助源，不按日期或版本号清除。

2026-10-23 整理：修改前快照、旧错误图标、一次性初版改码器/结束PIE脚本及重复 `AuthorHost` 已移入本机 `trash/RuneboundWarhammer20261023`，逐文件原路径和 SHA-256 记录在其 `manifest.json`。已安装 UE 资产及正式作者源保留。脚本重建时会重新生成导入宿主，现有成功回执中的旧宿主路径属于历史记录。

复查见 `Docs/Weapons/runebound-network-review-20261023.md`；公开源、共享接入补丁、授权资产恢复与 Git 范围见 `Docs/Publication/RuneboundWarhammer20261023/README.md`。整理与技能维护没有重跑游戏测试。
